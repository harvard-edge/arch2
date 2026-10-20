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
    BLOCK_SIZE: tl.constexpr,
):
    """
    Optimized depthwise 2D convolution - 1D tiling along flattened output.
    Each program handles BLOCK_SIZE consecutive output elements.
    """
    pid = tl.program_id(0)
    pid_nc = tl.program_id(1)
    
    c = pid_nc % C
    n = pid_nc // C
    
    # Flattened output indices
    out_idx = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    
    # Convert to 2D coordinates
    out_h = out_idx // W_OUT
    out_w = out_idx % W_OUT
    
    # Mask for valid outputs
    mask = (out_h < H_OUT) & (out_w < W_OUT)
    
    # Input starting coordinates (top-left of receptive field)
    in_h_base = out_h * STRIDE - PADDING
    in_w_base = out_w * STRIDE - PADDING
    
    # Base pointers
    x_base = x_ptr + n * X_STRIDE_N + c * X_STRIDE_C
    w_base = w_ptr + c * W_STRIDE_C
    
    # Load all 9 weights
    w00 = tl.load(w_base + 0 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w01 = tl.load(w_base + 0 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w02 = tl.load(w_base + 0 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w10 = tl.load(w_base + 1 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w11 = tl.load(w_base + 1 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w12 = tl.load(w_base + 1 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w20 = tl.load(w_base + 2 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w21 = tl.load(w_base + 2 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w22 = tl.load(w_base + 2 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    
    # Accumulator
    acc = tl.zeros([BLOCK_SIZE], dtype=tl.float32)
    
    # Process 3x3 kernel - unrolled for efficiency
    # Row 0
    ih = in_h_base + 0
    valid_h = (ih >= 0) & (ih < H)
    
    iw = in_w_base + 0
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w00
    
    iw = in_w_base + 1
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w01
    
    iw = in_w_base + 2
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w02
    
    # Row 1
    ih = in_h_base + 1
    valid_h = (ih >= 0) & (ih < H)
    
    iw = in_w_base + 0
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w10
    
    iw = in_w_base + 1
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w11
    
    iw = in_w_base + 2
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w12
    
    # Row 2
    ih = in_h_base + 2
    valid_h = (ih >= 0) & (ih < H)
    
    iw = in_w_base + 0
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w20
    
    iw = in_w_base + 1
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w21
    
    iw = in_w_base + 2
    valid = mask & valid_h & (iw >= 0) & (iw < W)
    x_off = ih * X_STRIDE_H + iw * X_STRIDE_W
    x_val = tl.load(x_base + x_off, mask=valid, other=0.0).to(tl.float32)
    acc += x_val * w22
    
    if HAS_BIAS:
        b_val = tl.load(b_ptr + c).to(tl.float32)
        acc += b_val
    
    # Store output - coalesced along W dimension
    y_base = y_ptr + n * Y_STRIDE_N + c * Y_STRIDE_C
    y_off = out_h * Y_STRIDE_H + out_w * Y_STRIDE_W
    tl.store(y_base + y_off, acc.to(tl.bfloat16), mask=mask)


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

    BLOCK_SIZE = 512
    total_outputs = H_out * W_out
    
    grid = (
        triton.cdiv(total_outputs, BLOCK_SIZE),
        N * C,
    )

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
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=4,
        num_stages=3,
    )

    return y