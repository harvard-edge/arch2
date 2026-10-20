import torch
import triton
import triton.language as tl


@triton.jit
def _dwconv2d_kernel_coalesced(
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
    Optimized depthwise 2D convolution kernel with improved memory coalescing.
    Uses wider tiles and vectorized access patterns for H100.
    """
    pid_w = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_nc = tl.program_id(2)

    c = pid_nc % C
    n = pid_nc // C

    # Output coordinates - use wider tiles for better coalescing
    offs_w = pid_w * BLOCK_W + tl.arange(0, BLOCK_W)
    offs_h = pid_h * BLOCK_H + tl.arange(0, BLOCK_H)
    
    mask_w = offs_w < W_OUT
    mask_h = offs_h < H_OUT

    # Input starting coordinates
    ix_base = offs_w * STRIDE - PADDING
    iy_base = offs_h * STRIDE - PADDING

    # Base pointers
    x_base = x_ptr + n * X_STRIDE_N + c * X_STRIDE_C
    w_base = w_ptr + c * W_STRIDE_C

    # Preload all 9 weights for 3x3 kernel into registers
    w00 = tl.load(w_base + 0 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w01 = tl.load(w_base + 0 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w02 = tl.load(w_base + 0 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w10 = tl.load(w_base + 1 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w11 = tl.load(w_base + 1 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w12 = tl.load(w_base + 1 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w20 = tl.load(w_base + 2 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w21 = tl.load(w_base + 2 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w22 = tl.load(w_base + 2 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)

    # Accumulator - 2D tile
    acc = tl.zeros([BLOCK_H, BLOCK_W], dtype=tl.float32)

    # Process each kernel row - compute row validity once
    # Row 0 of kernel
    iy0 = iy_base[:, None] + 0
    valid_y0 = (iy0 >= 0) & (iy0 < H)
    row0_offset = iy0 * X_STRIDE_H
    
    ix = ix_base[None, :] + 0
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y0 & valid_x
    x_vals = tl.load(x_base + row0_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w00
    
    ix = ix_base[None, :] + 1
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y0 & valid_x
    x_vals = tl.load(x_base + row0_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w01
    
    ix = ix_base[None, :] + 2
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y0 & valid_x
    x_vals = tl.load(x_base + row0_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w02

    # Row 1 of kernel
    iy1 = iy_base[:, None] + 1
    valid_y1 = (iy1 >= 0) & (iy1 < H)
    row1_offset = iy1 * X_STRIDE_H
    
    ix = ix_base[None, :] + 0
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y1 & valid_x
    x_vals = tl.load(x_base + row1_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w10
    
    ix = ix_base[None, :] + 1
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y1 & valid_x
    x_vals = tl.load(x_base + row1_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w11
    
    ix = ix_base[None, :] + 2
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y1 & valid_x
    x_vals = tl.load(x_base + row1_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w12

    # Row 2 of kernel
    iy2 = iy_base[:, None] + 2
    valid_y2 = (iy2 >= 0) & (iy2 < H)
    row2_offset = iy2 * X_STRIDE_H
    
    ix = ix_base[None, :] + 0
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y2 & valid_x
    x_vals = tl.load(x_base + row2_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w20
    
    ix = ix_base[None, :] + 1
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y2 & valid_x
    x_vals = tl.load(x_base + row2_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w21
    
    ix = ix_base[None, :] + 2
    valid_x = (ix >= 0) & (ix < W)
    m = mask_h[:, None] & mask_w[None, :] & valid_y2 & valid_x
    x_vals = tl.load(x_base + row2_offset + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w22

    if HAS_BIAS:
        b_val = tl.load(b_ptr + c).to(tl.float32)
        acc += b_val

    # Store output with coalesced writes
    y_base = y_ptr + n * Y_STRIDE_N + c * Y_STRIDE_C
    y_offs = offs_h[:, None] * Y_STRIDE_H + offs_w[None, :] * Y_STRIDE_W
    y_ptrs = y_base + y_offs
    store_mask = mask_h[:, None] & mask_w[None, :]
    
    tl.store(y_ptrs, acc.to(tl.bfloat16), mask=store_mask)


def kernel_function(input, weight, bias=None, stride=1, padding=0):
    assert input.is_cuda and weight.is_cuda
    device = input.device

    stride_h = stride_w = int(stride) if isinstance(stride, int) else (int(stride[0]), int(stride[1]))[1]
    pad_h = pad_w = int(padding) if isinstance(padding, int) else (int(padding[0]), int(padding[1]))[1]

    N, C, H, W = input.shape

    if weight.dim() == 4:
        w3 = weight.view(C, weight.shape[2], weight.shape[3]).contiguous()
    else:
        w3 = weight.contiguous()

    K = w3.shape[1]
    H_out = (H + 2 * pad_h - K) // stride_h + 1
    W_out = (W + 2 * pad_w - K) // stride_w + 1

    y = torch.empty((N, C, H_out, W_out), device=device, dtype=input.dtype)

    XsN, XsC, XsH, XsW = input.stride()
    WsC, WsKH, WsKW = w3.stride()
    YsN, YsC, YsH, YsW = y.stride()

    has_bias = bias is not None

    BLOCK_H = 8
    BLOCK_W = 128

    grid = (
        triton.cdiv(W_out, BLOCK_W),
        triton.cdiv(H_out, BLOCK_H),
        N * C
    )

    _dwconv2d_kernel_coalesced[grid](
        input, w3, bias if has_bias else y, y,
        N, C, H, W,
        H_out, W_out,
        XsN, XsC, XsH, XsW,
        WsC, WsKH, WsKW,
        YsN, YsC, YsH, YsW,
        STRIDE=stride_w,
        PADDING=pad_w,
        HAS_BIAS=has_bias,
        BLOCK_H=BLOCK_H,
        BLOCK_W=BLOCK_W,
        num_warps=8,
        num_stages=4,
    )

    return y