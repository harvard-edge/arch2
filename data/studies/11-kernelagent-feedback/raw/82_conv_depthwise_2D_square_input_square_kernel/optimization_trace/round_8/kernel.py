import torch
import triton
import triton.language as tl


@triton.jit
def _dwconv2d_kernel_v2(
    x_ptr, w_ptr, b_ptr, y_ptr,
    N, C, H, W,
    H_OUT, W_OUT,
    X_STRIDE_N, X_STRIDE_C, X_STRIDE_H, X_STRIDE_W,
    W_STRIDE_C, W_STRIDE_KH, W_STRIDE_KW,
    Y_STRIDE_N, Y_STRIDE_C, Y_STRIDE_H, Y_STRIDE_W,
    STRIDE: tl.constexpr,
    PADDING: tl.constexpr,
    HAS_BIAS: tl.constexpr,
    BLOCK_H: tl.constexpr,
    BLOCK_W: tl.constexpr,
):
    """
    Optimized depthwise 2D convolution kernel.
    Each program processes a BLOCK_H x BLOCK_W tile of output.
    """
    pid_w = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_nc = tl.program_id(2)

    c = pid_nc % C
    n = pid_nc // C

    # Output coordinates
    h_start = pid_h * BLOCK_H
    w_start = pid_w * BLOCK_W
    
    offs_w = w_start + tl.arange(0, BLOCK_W)
    
    # Base pointers
    x_base = x_ptr + n * X_STRIDE_N + c * X_STRIDE_C
    w_base = w_ptr + c * W_STRIDE_C
    y_base = y_ptr + n * Y_STRIDE_N + c * Y_STRIDE_C

    # Load all 9 weights into registers
    w00 = tl.load(w_base + 0 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w01 = tl.load(w_base + 0 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w02 = tl.load(w_base + 0 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w10 = tl.load(w_base + 1 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w11 = tl.load(w_base + 1 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w12 = tl.load(w_base + 1 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w20 = tl.load(w_base + 2 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w21 = tl.load(w_base + 2 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w22 = tl.load(w_base + 2 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)

    bias_val = tl.load(b_ptr + c).to(tl.float32) if HAS_BIAS else 0.0

    # Precompute input x coordinates
    ix0 = offs_w * STRIDE - PADDING
    ix1 = ix0 + 1
    ix2 = ix0 + 2
    
    mask_w = offs_w < W_OUT
    valid_x0 = (ix0 >= 0) & (ix0 < W)
    valid_x1 = (ix1 >= 0) & (ix1 < W)
    valid_x2 = (ix2 >= 0) & (ix2 < W)

    # Process BLOCK_H rows
    for h_idx in tl.static_range(BLOCK_H):
        h_out = h_start + h_idx
        
        if h_out < H_OUT:
            iy_base = h_out * STRIDE - PADDING
            
            acc = tl.zeros([BLOCK_W], dtype=tl.float32)
            
            # Unrolled 3x3 convolution
            iy0 = iy_base
            iy1 = iy_base + 1
            iy2 = iy_base + 2
            
            # Row 0
            valid_y0 = (iy0 >= 0) & (iy0 < H)
            if valid_y0:
                row_ptr = x_base + iy0 * X_STRIDE_H
                x0 = tl.load(row_ptr + ix0, mask=mask_w & valid_x0, other=0.0).to(tl.float32)
                x1 = tl.load(row_ptr + ix1, mask=mask_w & valid_x1, other=0.0).to(tl.float32)
                x2 = tl.load(row_ptr + ix2, mask=mask_w & valid_x2, other=0.0).to(tl.float32)
                acc += x0 * w00 + x1 * w01 + x2 * w02
            
            # Row 1
            valid_y1 = (iy1 >= 0) & (iy1 < H)
            if valid_y1:
                row_ptr = x_base + iy1 * X_STRIDE_H
                x0 = tl.load(row_ptr + ix0, mask=mask_w & valid_x0, other=0.0).to(tl.float32)
                x1 = tl.load(row_ptr + ix1, mask=mask_w & valid_x1, other=0.0).to(tl.float32)
                x2 = tl.load(row_ptr + ix2, mask=mask_w & valid_x2, other=0.0).to(tl.float32)
                acc += x0 * w10 + x1 * w11 + x2 * w12
            
            # Row 2
            valid_y2 = (iy2 >= 0) & (iy2 < H)
            if valid_y2:
                row_ptr = x_base + iy2 * X_STRIDE_H
                x0 = tl.load(row_ptr + ix0, mask=mask_w & valid_x0, other=0.0).to(tl.float32)
                x1 = tl.load(row_ptr + ix1, mask=mask_w & valid_x1, other=0.0).to(tl.float32)
                x2 = tl.load(row_ptr + ix2, mask=mask_w & valid_x2, other=0.0).to(tl.float32)
                acc += x0 * w20 + x1 * w21 + x2 * w22
            
            if HAS_BIAS:
                acc += bias_val
            
            # Store output
            y_offs = h_out * Y_STRIDE_H + offs_w * Y_STRIDE_W
            tl.store(y_base + y_offs, acc.to(tl.bfloat16), mask=mask_w)


def kernel_function(input, weight, bias=None, stride=1, padding=0):
    assert input.is_cuda and weight.is_cuda
    device = input.device

    stride_val = int(stride) if isinstance(stride, int) else int(stride[0])
    pad_val = int(padding) if isinstance(padding, int) else int(padding[0])

    N, C, H, W = input.shape

    if weight.dim() == 4:
        w3 = weight.view(C, weight.shape[2], weight.shape[3]).contiguous()
    else:
        w3 = weight.contiguous()

    K = w3.shape[1]
    H_out = (H + 2 * pad_val - K) // stride_val + 1
    W_out = (W + 2 * pad_val - K) // stride_val + 1

    y = torch.empty((N, C, H_out, W_out), device=device, dtype=input.dtype)

    XsN, XsC, XsH, XsW = input.stride()
    WsC, WsKH, WsKW = w3.stride()
    YsN, YsC, YsH, YsW = y.stride()

    has_bias = bias is not None

    BLOCK_W = 128
    BLOCK_H = 8

    grid = (
        triton.cdiv(W_out, BLOCK_W),
        triton.cdiv(H_out, BLOCK_H),
        N * C
    )

    _dwconv2d_kernel_v2[grid](
        input, w3, bias if has_bias else y, y,
        N, C, H, W,
        H_out, W_out,
        XsN, XsC, XsH, XsW,
        WsC, WsKH, WsKW,
        YsN, YsC, YsH, YsW,
        STRIDE=stride_val,
        PADDING=pad_val,
        HAS_BIAS=has_bias,
        BLOCK_H=BLOCK_H,
        BLOCK_W=BLOCK_W,
        num_warps=4,
        num_stages=3,
    )

    return y