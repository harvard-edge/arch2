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
    ELEMENTS_PER_THREAD: tl.constexpr,
):
    """
    Optimized depthwise 2D convolution kernel with improved ILP.
    Each thread processes multiple output elements for better instruction-level parallelism.
    """
    pid = tl.program_id(0)
    pid_nc = tl.program_id(1)
    
    c = pid_nc % C
    n = pid_nc // C
    
    # Calculate total output elements and this block's range
    total_out = H_OUT * W_OUT
    block_start = pid * BLOCK_SIZE * ELEMENTS_PER_THREAD
    
    # Base pointers
    x_base = x_ptr + n * X_STRIDE_N + c * X_STRIDE_C
    w_base = w_ptr + c * W_STRIDE_C
    y_base = y_ptr + n * Y_STRIDE_N + c * Y_STRIDE_C
    
    # Preload all 9 weights for 3x3 kernel
    w00 = tl.load(w_base + 0 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w01 = tl.load(w_base + 0 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w02 = tl.load(w_base + 0 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w10 = tl.load(w_base + 1 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w11 = tl.load(w_base + 1 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w12 = tl.load(w_base + 1 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w20 = tl.load(w_base + 2 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w21 = tl.load(w_base + 2 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w22 = tl.load(w_base + 2 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    
    # Load bias if present
    bias_val = tl.load(b_ptr + c).to(tl.float32) if HAS_BIAS else 0.0
    
    # Process ELEMENTS_PER_THREAD elements per thread
    offs = tl.arange(0, BLOCK_SIZE)
    
    for i in tl.static_range(ELEMENTS_PER_THREAD):
        idx = block_start + i * BLOCK_SIZE + offs
        mask = idx < total_out
        
        # Convert linear index to 2D output coordinates
        oh = idx // W_OUT
        ow = idx % W_OUT
        
        # Input starting coordinates
        ih_base = oh * STRIDE - PADDING
        iw_base = ow * STRIDE - PADDING
        
        # Accumulator
        acc = tl.zeros([BLOCK_SIZE], dtype=tl.float32)
        
        # Unrolled 3x3 convolution
        # Row 0
        ih = ih_base + 0
        valid_h = (ih >= 0) & (ih < H)
        row_offset = ih * X_STRIDE_H
        
        iw = iw_base + 0
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w00
        
        iw = iw_base + 1
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w01
        
        iw = iw_base + 2
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w02
        
        # Row 1
        ih = ih_base + 1
        valid_h = (ih >= 0) & (ih < H)
        row_offset = ih * X_STRIDE_H
        
        iw = iw_base + 0
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w10
        
        iw = iw_base + 1
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w11
        
        iw = iw_base + 2
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w12
        
        # Row 2
        ih = ih_base + 2
        valid_h = (ih >= 0) & (ih < H)
        row_offset = ih * X_STRIDE_H
        
        iw = iw_base + 0
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w20
        
        iw = iw_base + 1
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w21
        
        iw = iw_base + 2
        valid = mask & valid_h & (iw >= 0) & (iw < W)
        x_val = tl.load(x_base + row_offset + iw * X_STRIDE_W, mask=valid, other=0.0).to(tl.float32)
        acc += x_val * w22
        
        if HAS_BIAS:
            acc += bias_val
        
        # Store output
        y_offs = oh * Y_STRIDE_H + ow * Y_STRIDE_W
        tl.store(y_base + y_offs, acc.to(tl.bfloat16), mask=mask)


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

    BLOCK_SIZE = 256
    ELEMENTS_PER_THREAD = 4
    
    total_elements = H_out * W_out
    num_blocks = triton.cdiv(total_elements, BLOCK_SIZE * ELEMENTS_PER_THREAD)

    grid = (num_blocks, N * C)

    _dwconv2d_kernel_optimized[grid](
        input, w3, bias if has_bias else input, y,
        N, C, H, W,
        H_out, W_out,
        XsN, XsC, XsH, XsW,
        WsC, WsKH, WsKW,
        YsN, YsC, YsH, YsW,
        STRIDE=stride_val,
        PADDING=pad_val,
        HAS_BIAS=has_bias,
        BLOCK_SIZE=BLOCK_SIZE,
        ELEMENTS_PER_THREAD=ELEMENTS_PER_THREAD,
        num_warps=8,
        num_stages=3,
    )

    return y