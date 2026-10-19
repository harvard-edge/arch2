import torch
import triton
import triton.language as tl


@triton.jit
def _conv_transpose3d_fwd_kernel_opt(
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

    HoWo = Ho * Wo
    S_total = Do * HoWo
    
    s_base = pid_s * BLOCK_S
    s_offsets = s_base + tl.arange(0, BLOCK_S)
    s_mask = s_offsets < S_total

    od = s_offsets // HoWo
    rem = s_offsets - od * HoWo
    oh = rem // Wo
    ow = rem - oh * Wo

    oc_base = pid_oc * BLOCK_OC
    oc_offsets = oc_base + tl.arange(0, BLOCK_OC)
    oc_mask = oc_offsets < Cout

    acc = tl.zeros((BLOCK_S, BLOCK_OC), dtype=tl.float32)

    if BIAS:
        b = tl.load(b_ptr + oc_offsets, mask=oc_mask, other=0.0).to(tl.float32)
        acc += b[None, :]

    x_base_n = x_ptr + pid_n * sx_n
    cin_offsets = tl.arange(0, BLOCK_CIN)
    
    w_base_oc = w_ptr + oc_offsets * sw_co

    for kd in range(K_D):
        tmpd = od + pad_d - kd * dil_d
        id_val = tmpd // stride_d
        valid_d = (tmpd >= 0) & ((tmpd % stride_d) == 0) & (id_val < Di)

        for kh in range(K_H):
            tmph = oh + pad_h - kh * dil_h
            ih_val = tmph // stride_h
            valid_dh = valid_d & (tmph >= 0) & ((tmph % stride_h) == 0) & (ih_val < Hi)

            for kw in range(K_W):
                tmpw = ow + pad_w - kw * dil_w
                iw_val = tmpw // stride_w
                valid_dhw = valid_dh & (tmpw >= 0) & ((tmpw % stride_w) == 0) & (iw_val < Wi) & s_mask

                x_offset = id_val * sx_d + ih_val * sx_h + iw_val * sx_w
                x_ptrs = x_base_n + x_offset[:, None] + cin_offsets[None, :] * sx_c
                x_load_mask = valid_dhw[:, None] & (cin_offsets[None, :] < Cin)
                x_tile = tl.load(x_ptrs, mask=x_load_mask, other=0.0).to(tl.bfloat16)

                w_k_offset = kd * sw_kd + kh * sw_kh + kw * sw_kw
                w_ptrs = w_base_oc[None, :] + cin_offsets[:, None] * sw_ci + w_k_offset
                w_load_mask = (cin_offsets[:, None] < Cin) & oc_mask[None, :]
                w_tile = tl.load(w_ptrs, mask=w_load_mask, other=0.0).to(tl.bfloat16)

                acc = tl.dot(x_tile, w_tile, acc)

    y_base = y_ptr + pid_n * sy_n
    y_offset = od * sy_d + oh * sy_h + ow * sy_w
    y_ptrs = y_base + y_offset[:, None] + oc_offsets[None, :] * sy_c
    out_mask = s_mask[:, None] & oc_mask[None, :]
    tl.store(y_ptrs, acc.to(tl.bfloat16), mask=out_mask)


def _normalize_triple(v, name):
    if isinstance(v, int):
        return (v, v, v)
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return tuple(int(x) for x in v)
    raise TypeError(f"{name} must be int or 3-tuple of ints")


def _compute_conv_transpose3d_output_size(Di, Hi, Wi, kD, kH, kW, sD, sH, sW, pD, pH, pW, dD, dH, dW, out_pad=(0, 0, 0)):
    Do = (Di - 1) * sD - 2 * pD + dD * (kD - 1) + out_pad[0] + 1
    Ho = (Hi - 1) * sH - 2 * pH + dH * (kH - 1) + out_pad[1] + 1
    Wo = (Wi - 1) * sW - 2 * pW + dW * (kW - 1) + out_pad[2] + 1
    return Do, Ho, Wo


def kernel_function(x, *args, **kwargs):
    weight = None
    bias = None
    stride = None
    padding = None
    dilation = None

    if len(args) == 1 and isinstance(args[0], dict):
        params = args[0]
        weight = params.get('weight', None)
        bias = params.get('bias', None)
        stride = params.get('stride', 1)
        padding = params.get('padding', 0)
        dilation = params.get('dilation', 1)
    else:
        if len(args) >= 1:
            weight = args[0]
        if len(args) == 4:
            stride, padding, dilation = args[1], args[2], args[3]
        elif len(args) == 5:
            bias, stride, padding, dilation = args[1], args[2], args[3], args[4]
        elif len(args) == 3:
            stride, padding, dilation = args[1], args[2], kwargs.get('dilation', kwargs.get('d', 1))

        weight = kwargs.get('weight', weight)
        bias = kwargs.get('bias', bias)
        stride = kwargs.get('stride', stride)
        padding = kwargs.get('padding', padding)
        dilation = kwargs.get('dilation', dilation)

    if weight is None:
        raise TypeError("weight must be provided")
    stride = stride if stride is not None else 1
    padding = padding if padding is not None else 0
    dilation = dilation if dilation is not None else 1

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

    sx_n, sx_c, sx_d, sx_h, sx_w = x.stride()
    sy_n, sy_c, sy_d, sy_h, sy_w = y.stride()
    sw_ci, sw_co, sw_kd, sw_kh, sw_kw = weight.stride()

    S_total = Do * Ho * Wo

    BLOCK_CIN = 32
    BLOCK_OC = 32
    BLOCK_S = 64

    grid = (
        triton.cdiv(S_total, BLOCK_S),
        triton.cdiv(Cout, BLOCK_OC),
        N,
    )

    _conv_transpose3d_fwd_kernel_opt[grid](
        x, weight, (bias if bias is not None else y), y,
        N, Cin, Cout,
        Di, Hi, Wi,
        Do, Ho, Wo,
        sD, sH, sW,
        pD, pH, pW,
        dD, dH, dW,
        sx_n, sx_c, sx_d, sx_h, sx_w,
        sw_ci, sw_co, sw_kd, sw_kh, sw_kw,
        sy_n, sy_c, sy_d, sy_h, sy_w,
        K_D=kD, K_H=kH, K_W=kW,
        BLOCK_S=BLOCK_S,
        BLOCK_OC=BLOCK_OC,
        BLOCK_CIN=BLOCK_CIN,
        BIAS=(bias is not None),
        num_warps=4,
        num_stages=2,
    )
    return y