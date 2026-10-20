import torch
import triton
import triton.language as tl


@triton.jit
def _conv_transpose3d_fwd_kernel_v2(
    x_ptr,
    w_ptr,
    b_ptr,
    y_ptr,
    N, Cin, Cout,
    Di, Hi, Wi,
    Do, Ho, Wo,
    stride_d, stride_h, stride_w,
    pad_d, pad_h, pad_w,
    dil_d, dil_h, dil_w,
    sx_n, sx_c, sx_d, sx_h, sx_w,
    sw_ci, sw_co, sw_kd, sw_kh, sw_kw,
    sy_n, sy_c, sy_d, sy_h, sy_w,
    HoWo,
    K_D: tl.constexpr,
    K_H: tl.constexpr,
    K_W: tl.constexpr,
    BLOCK_S: tl.constexpr,
    BLOCK_OC: tl.constexpr,
    BLOCK_CIN: tl.constexpr,
    BIAS: tl.constexpr,
):
    pid_s = tl.program_id(0)
    pid_oc = tl.program_id(1)
    pid_n = tl.program_id(2)

    S_total = Do * Ho * Wo
    s_base = pid_s * BLOCK_S
    s_offsets = s_base + tl.arange(0, BLOCK_S)
    s_mask = s_offsets < S_total

    # Compute output positions
    od = s_offsets // HoWo
    tmp = s_offsets % HoWo
    oh = tmp // Wo
    ow = tmp % Wo

    oc_base = pid_oc * BLOCK_OC
    oc_offsets = oc_base + tl.arange(0, BLOCK_OC)
    oc_mask = oc_offsets < Cout

    acc = tl.zeros((BLOCK_S, BLOCK_OC), dtype=tl.float32)

    if BIAS:
        b = tl.load(b_ptr + oc_offsets, mask=oc_mask, other=0.0).to(tl.float32)
        acc += b[None, :]

    x_base_n = x_ptr + pid_n * sx_n

    # Loop over input channels in tiles
    for cin_start in range(0, Cin, BLOCK_CIN):
        cin_offsets = cin_start + tl.arange(0, BLOCK_CIN)
        cin_mask = cin_offsets < Cin

        # Loop over kernel dimensions
        for kd in range(K_D):
            tmpd = od + pad_d - kd * dil_d
            valid_d = (tmpd >= 0) & ((tmpd % stride_d) == 0)
            id_val = tmpd // stride_d
            valid_d = valid_d & (id_val >= 0) & (id_val < Di)

            for kh in range(K_H):
                tmph = oh + pad_h - kh * dil_h
                valid_h = (tmph >= 0) & ((tmph % stride_h) == 0)
                ih_val = tmph // stride_h
                valid_h = valid_h & (ih_val >= 0) & (ih_val < Hi)

                valid_dh = valid_d & valid_h

                for kw in range(K_W):
                    tmpw = ow + pad_w - kw * dil_w
                    valid_w = (tmpw >= 0) & ((tmpw % stride_w) == 0)
                    iw_val = tmpw // stride_w
                    valid_w = valid_w & (iw_val >= 0) & (iw_val < Wi)

                    valid_dhw = valid_dh & valid_w & s_mask

                    # Load input tile - shape [BLOCK_S, BLOCK_CIN]
                    x_spatial = id_val * sx_d + ih_val * sx_h + iw_val * sx_w
                    x_ptrs = x_base_n + x_spatial[:, None] + cin_offsets[None, :] * sx_c
                    x_tile = tl.load(x_ptrs, mask=valid_dhw[:, None] & cin_mask[None, :], other=0.0)

                    # Load weight tile - shape [BLOCK_CIN, BLOCK_OC]
                    w_k_off = kd * sw_kd + kh * sw_kh + kw * sw_kw
                    w_ptrs = w_ptr + cin_offsets[:, None] * sw_ci + oc_offsets[None, :] * sw_co + w_k_off
                    w_tile = tl.load(w_ptrs, mask=cin_mask[:, None] & oc_mask[None, :], other=0.0)

                    # Accumulate
                    acc = tl.dot(x_tile, w_tile, acc, allow_tf32=True)

    # Store output
    y_base = y_ptr + pid_n * sy_n
    y_spatial = od * sy_d + oh * sy_h + ow * sy_w
    y_ptrs = y_base + y_spatial[:, None] + oc_offsets[None, :] * sy_c
    tl.store(y_ptrs, acc.to(tl.bfloat16), mask=s_mask[:, None] & oc_mask[None, :])


def _normalize_triple(v, name):
    if isinstance(v, int):
        return (v, v, v)
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return tuple(int(x) for x in v)
    raise TypeError(f"{name} must be int or 3-tuple of ints")


def _compute_conv_transpose3d_output_size(Di, Hi, Wi, kD, kH, kW, sD, sH, sW, pD, pH, pW, dD, dH, dW):
    Do = (Di - 1) * sD - 2 * pD + dD * (kD - 1) + 1
    Ho = (Hi - 1) * sH - 2 * pH + dH * (kH - 1) + 1
    Wo = (Wi - 1) * sW - 2 * pW + dW * (kW - 1) + 1
    return Do, Ho, Wo


def kernel_function(x, weight, bias=None, stride=1, padding=0, dilation=1):
    sD, sH, sW = _normalize_triple(stride, "stride")
    pD, pH, pW = _normalize_triple(padding, "padding")
    dD, dH, dW = _normalize_triple(dilation, "dilation")

    if x.dtype != torch.bfloat16:
        x = x.to(torch.bfloat16)
    if weight.dtype != torch.bfloat16:
        weight = weight.to(torch.bfloat16)
    if bias is not None and bias.dtype != torch.bfloat16:
        bias = bias.to(torch.bfloat16)

    N, Cin, Di, Hi, Wi = x.shape
    Cin_w, Cout, kD, kH, kW = weight.shape

    Do, Ho, Wo = _compute_conv_transpose3d_output_size(Di, Hi, Wi, kD, kH, kW, sD, sH, sW, pD, pH, pW, dD, dH, dW)
    y = torch.empty((N, Cout, Do, Ho, Wo), device=x.device, dtype=x.dtype)

    S_total = Do * Ho * Wo
    HoWo = Ho * Wo

    BLOCK_CIN = Cin
    BLOCK_OC = 64
    BLOCK_S = 64

    grid = (triton.cdiv(S_total, BLOCK_S), triton.cdiv(Cout, BLOCK_OC), N)

    _conv_transpose3d_fwd_kernel_v2[grid](
        x, weight, (bias if bias is not None else y), y,
        N, Cin, Cout,
        Di, Hi, Wi,
        Do, Ho, Wo,
        sD, sH, sW,
        pD, pH, pW,
        dD, dH, dW,
        x.stride(0), x.stride(1), x.stride(2), x.stride(3), x.stride(4),
        weight.stride(0), weight.stride(1), weight.stride(2), weight.stride(3), weight.stride(4),
        y.stride(0), y.stride(1), y.stride(2), y.stride(3), y.stride(4),
        HoWo,
        K_D=kD, K_H=kH, K_W=kW,
        BLOCK_S=BLOCK_S,
        BLOCK_OC=BLOCK_OC,
        BLOCK_CIN=BLOCK_CIN,
        BIAS=(bias is not None),
        num_warps=4,
        num_stages=3,
    )
    return y