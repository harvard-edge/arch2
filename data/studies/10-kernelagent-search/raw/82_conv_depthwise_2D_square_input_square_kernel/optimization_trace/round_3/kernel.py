import torch
import triton
import triton.language as tl


@triton.jit
def _dwconv2d_kernel_optimized(
    x_ptr, w_ptr, b_ptr, y_ptr,
    N, C, H, W,
    H_OUT, W_OUT,
    X_STRIDE_N, X_STRIDE_C, X_STRIDE_H, X_STRIDE_W,
    W_STRIDE_C, W_STRIDE_KH, W_STRIDE_KW,
    Y_STRIDE_N, Y_STRIDE_C, Y_STRIDE_H, Y_STRIDE_W,
    STRIDE: tl.constexpr,
    PADDING: tl.constexpr,
    HAS_BIAS: tl.constexpr,
    BLOCK_W: tl.constexpr,
):
    """Optimized depthwise 3x3 conv with row-based loading and register reuse."""
    pid_w = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_nc = tl.program_id(2)

    c = pid_nc % C
    n = pid_nc // C
    
    # Output position - single row, BLOCK_W columns
    out_h = pid_h
    offs_w = pid_w * BLOCK_W + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W_OUT
    
    if out_h >= H_OUT:
        return

    # Input coordinates
    in_h_base = out_h * STRIDE - PADDING
    in_w_base = offs_w * STRIDE - PADDING

    x_base = x_ptr + n * X_STRIDE_N + c * X_STRIDE_C
    w_base = w_ptr + c * W_STRIDE_C

    # Load all 9 weights
    w00 = tl.load(w_base).to(tl.float32)
    w01 = tl.load(w_base + W_STRIDE_KW).to(tl.float32)
    w02 = tl.load(w_base + 2 * W_STRIDE_KW).to(tl.float32)
    w10 = tl.load(w_base + W_STRIDE_KH).to(tl.float32)
    w11 = tl.load(w_base + W_STRIDE_KH + W_STRIDE_KW).to(tl.float32)
    w12 = tl.load(w_base + W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w20 = tl.load(w_base + 2 * W_STRIDE_KH).to(tl.float32)
    w21 = tl.load(w_base + 2 * W_STRIDE_KH + W_STRIDE_KW).to(tl.float32)
    w22 = tl.load(w_base + 2 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)

    acc = tl.zeros([BLOCK_W], dtype=tl.float32)

    # Process row 0
    in_h0 = in_h_base
    valid_h0 = (in_h0 >= 0) & (in_h0 < H)
    row0_base = x_base + in_h0 * X_STRIDE_H
    
    in_w0 = in_w_base
    in_w1 = in_w_base + 1
    in_w2 = in_w_base + 2
    
    valid_w0 = (in_w0 >= 0) & (in_w0 < W)
    valid_w1 = (in_w1 >= 0) & (in_w1 < W)
    valid_w2 = (in_w2 >= 0) & (in_w2 < W)
    
    m00 = mask_w & valid_h0 & valid_w0
    m01 = mask_w & valid_h0 & valid_w1
    m02 = mask_w & valid_h0 & valid_w2
    
    x00 = tl.load(row0_base + in_w0 * X_STRIDE_W, mask=m00, other=0.0).to(tl.float32)
    x01 = tl.load(row0_base + in_w1 * X_STRIDE_W, mask=m01, other=0.0).to(tl.float32)
    x02 = tl.load(row0_base + in_w2 * X_STRIDE_W, mask=m02, other=0.0).to(tl.float32)
    
    acc += x00 * w00 + x01 * w01 + x02 * w02

    # Process row 1
    in_h1 = in_h_base + 1
    valid_h1 = (in_h1 >= 0) & (in_h1 < H)
    row1_base = x_base + in_h1 * X_STRIDE_H
    
    m10 = mask_w & valid_h1 & valid_w0
    m11 = mask_w & valid_h1 & valid_w1
    m12 = mask_w & valid_h1 & valid_w2
    
    x10 = tl.load(row1_base + in_w0 * X_STRIDE_W, mask=m10, other=0.0).to(tl.float32)
    x11 = tl.load(row1_base + in_w1 * X_STRIDE_W, mask=m11, other=0.0).to(tl.float32)
    x12 = tl.load(row1_base + in_w2 * X_STRIDE_W, mask=m12, other=0.0).to(tl.float32)
    
    acc += x10 * w10 + x11 * w11 + x12 * w12

    # Process row 2
    in_h2 = in_h_base + 2
    valid_h2 = (in_h2 >= 0) & (in_h2 < H)
    row2_base = x_base + in_h2 * X_STRIDE_H
    
    m20 = mask_w & valid_h2 & valid_w0
    m21 = mask_w & valid_h2 & valid_w1
    m22 = mask_w & valid_h2 & valid_w2
    
    x20 = tl.load(row2_base + in_w0 * X_STRIDE_W, mask=m20, other=0.0).to(tl.float32)
    x21 = tl.load(row2_base + in_w1 * X_STRIDE_W, mask=m21, other=0.0).to(tl.float32)
    x22 = tl.load(row2_base + in_w2 * X_STRIDE_W, mask=m22, other=0.0).to(tl.float32)
    
    acc += x20 * w20 + x21 * w21 + x22 * w22

    if HAS_BIAS:
        b_val = tl.load(b_ptr + c).to(tl.float32)
        acc += b_val

    # Store output
    y_base = y_ptr + n * Y_STRIDE_N + c * Y_STRIDE_C + out_h * Y_STRIDE_H
    y_ptrs = y_base + offs_w * Y_STRIDE_W
    tl.store(y_ptrs, acc.to(tl.bfloat16), mask=mask_w)


def kernel_function(input, weight, bias=None, stride=1, padding=0):
    assert input.is_cuda and weight.is_cuda
    device = input.device

    stride_val = int(stride) if isinstance(stride, int) else int(stride[0])
    pad_val = int(padding) if isinstance(padding, int) else int(padding[0])

    N, C, H, W = input.shape

    if weight.dim() == 4:
        K = weight.shape[2]
        w3 = weight.view(C, K, K).contiguous()
    else:
        K = weight.shape[1]
        w3 = weight.contiguous()

    H_out = (H + 2 * pad_val - K) // stride_val + 1
    W_out = (W + 2 * pad_val - K) // stride_val + 1

    y = torch.empty((N, C, H_out, W_out), device=device, dtype=input.dtype)

    XsN, XsC, XsH, XsW = input.stride()
    WsC, WsKH, WsKW = w3.stride()
    YsN, YsC, YsH, YsW = y.stride()

    has_bias = bias is not None

    BLOCK_W = 256

    grid = (triton.cdiv(W_out, BLOCK_W), H_out, N * C)

    _dwconv2d_kernel_optimized[grid](
        input, w3, bias if has_bias else y, y,
        N, C, H, W,
        H_out, W_out,
        XsN, XsC, XsH, XsW,
        WsC, WsKH, WsKW,
        YsN, YsC, YsH, YsW,
        STRIDE=stride_val,
        PADDING=pad_val,
        HAS_BIAS=has_bias,
        BLOCK_W=BLOCK_W,
        num_warps=4,
        num_stages=2,
    )

    return y