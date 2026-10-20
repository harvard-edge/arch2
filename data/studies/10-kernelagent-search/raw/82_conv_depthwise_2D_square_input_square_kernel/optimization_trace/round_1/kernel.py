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
    K: tl.constexpr,
    STRIDE: tl.constexpr,
    PADDING: tl.constexpr,
    HAS_BIAS: tl.constexpr,
    BLOCK_H: tl.constexpr,
    BLOCK_W: tl.constexpr,
):
    """
    Optimized depthwise 2D convolution kernel with 2D tiling for better memory access patterns.
    Uses vectorized loads and improved cache utilization.
    """
    pid_w = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_nc = tl.program_id(2)

    c = pid_nc % C
    n = pid_nc // C

    # Output coordinates covered by this program
    offs_x = pid_w * BLOCK_W + tl.arange(0, BLOCK_W)
    offs_y = pid_h * BLOCK_H + tl.arange(0, BLOCK_H)
    
    mask_x = offs_x < W_OUT
    mask_y = offs_y < H_OUT

    # Map output coords to input coords (with stride, padding)
    ix0 = offs_x * STRIDE - PADDING
    iy0 = offs_y * STRIDE - PADDING

    # Base pointers
    x_base = x_ptr + n * X_STRIDE_N + c * X_STRIDE_C

    # Accumulator - 2D tile
    acc = tl.zeros([BLOCK_H, BLOCK_W], dtype=tl.float32)

    # Preload weights into registers
    w_base = w_ptr + c * W_STRIDE_C
    
    # Convolution loop over kernel window (KxK)
    for ky in range(0, K):
        iy = iy0[:, None] + ky  # [BLOCK_H, 1]
        valid_y = (iy >= 0) & (iy < H)
        
        for kx in range(0, K):
            ix = ix0[None, :] + kx  # [1, BLOCK_W]
            valid_x = (ix >= 0) & (ix < W)
            
            # Combined mask
            m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
            
            # Compute input pointer offsets
            x_offs = iy * X_STRIDE_H + ix * X_STRIDE_W
            x_ptrs = x_base + x_offs
            
            # Load input values
            x_vals = tl.load(x_ptrs, mask=m, other=0.0).to(tl.float32)

            # Weight is scalar per (c, ky, kx)
            w_ptr_curr = w_base + ky * W_STRIDE_KH + kx * W_STRIDE_KW
            w_val = tl.load(w_ptr_curr).to(tl.float32)

            acc += x_vals * w_val

    if HAS_BIAS:
        b_val = tl.load(b_ptr + c).to(tl.float32)
        acc += b_val

    # Store output
    y_base = y_ptr + n * Y_STRIDE_N + c * Y_STRIDE_C
    y_offs = offs_y[:, None] * Y_STRIDE_H + offs_x[None, :] * Y_STRIDE_W
    y_ptrs = y_base + y_offs
    store_mask = mask_y[:, None] & mask_x[None, :]
    
    tl.store(y_ptrs, acc.to(tl.bfloat16), mask=store_mask)


@triton.jit
def _dwconv2d_kernel_k3(
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
    Specialized kernel for K=3 with unrolled loops for better performance.
    """
    pid_w = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_nc = tl.program_id(2)

    c = pid_nc % C
    n = pid_nc // C

    offs_x = pid_w * BLOCK_W + tl.arange(0, BLOCK_W)
    offs_y = pid_h * BLOCK_H + tl.arange(0, BLOCK_H)
    
    mask_x = offs_x < W_OUT
    mask_y = offs_y < H_OUT

    ix0 = offs_x * STRIDE - PADDING
    iy0 = offs_y * STRIDE - PADDING

    x_base = x_ptr + n * X_STRIDE_N + c * X_STRIDE_C
    w_base = w_ptr + c * W_STRIDE_C

    acc = tl.zeros([BLOCK_H, BLOCK_W], dtype=tl.float32)

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

    # Row 0
    iy = iy0[:, None] + 0
    valid_y = (iy >= 0) & (iy < H)
    
    ix = ix0[None, :] + 0
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w00
    
    ix = ix0[None, :] + 1
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w01
    
    ix = ix0[None, :] + 2
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w02

    # Row 1
    iy = iy0[:, None] + 1
    valid_y = (iy >= 0) & (iy < H)
    
    ix = ix0[None, :] + 0
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w10
    
    ix = ix0[None, :] + 1
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w11
    
    ix = ix0[None, :] + 2
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w12

    # Row 2
    iy = iy0[:, None] + 2
    valid_y = (iy >= 0) & (iy < H)
    
    ix = ix0[None, :] + 0
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w20
    
    ix = ix0[None, :] + 1
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w21
    
    ix = ix0[None, :] + 2
    valid_x = (ix >= 0) & (ix < W)
    m = mask_y[:, None] & mask_x[None, :] & valid_y & valid_x
    x_vals = tl.load(x_base + iy * X_STRIDE_H + ix * X_STRIDE_W, mask=m, other=0.0).to(tl.float32)
    acc += x_vals * w22

    if HAS_BIAS:
        b_val = tl.load(b_ptr + c).to(tl.float32)
        acc += b_val

    y_base = y_ptr + n * Y_STRIDE_N + c * Y_STRIDE_C
    y_offs = offs_y[:, None] * Y_STRIDE_H + offs_x[None, :] * Y_STRIDE_W
    y_ptrs = y_base + y_offs
    store_mask = mask_y[:, None] & mask_x[None, :]
    
    tl.store(y_ptrs, acc.to(tl.bfloat16), mask=store_mask)


def kernel_function(input, weight, bias=None, stride=1, padding=0):
    """
    Depthwise 2D convolution implemented in Triton with optimized 2D tiling.
    """
    assert input.is_cuda, "Input must be on CUDA device"
    assert weight.is_cuda, "Weight must be on CUDA device"
    device = input.device

    if isinstance(stride, (list, tuple)):
        assert len(stride) == 2, "stride must be int or pair of ints"
        stride_h, stride_w = int(stride[0]), int(stride[1])
    else:
        stride_h = stride_w = int(stride)

    if isinstance(padding, (list, tuple)):
        assert len(padding) == 2, "padding must be int or pair of ints"
        pad_h, pad_w = int(padding[0]), int(padding[1])
    else:
        pad_h = pad_w = int(padding)

    N, C, H, W = input.shape

    if weight.dim() == 4:
        assert weight.shape[0] == C and weight.shape[1] == 1
        K_h = weight.shape[2]
        K_w = weight.shape[3]
        w3 = weight.view(C, K_h, K_w).contiguous()
    elif weight.dim() == 3:
        assert weight.shape[0] == C
        K_h = weight.shape[1]
        K_w = weight.shape[2]
        w3 = weight.contiguous()
    else:
        raise ValueError("weight must be 3D (C,K,K) or 4D (C,1,K,K)")

    assert K_h == K_w, "Only square kernels are supported"
    K = K_h

    H_out = (H + 2 * pad_h - K) // stride_h + 1
    W_out = (W + 2 * pad_w - K) // stride_w + 1
    assert H_out > 0 and W_out > 0, "Invalid output dimensions"

    y = torch.empty((N, C, H_out, W_out), device=device, dtype=input.dtype)

    XsN, XsC, XsH, XsW = input.stride()
    WsC, WsKH, WsKW = w3.stride()
    YsN, YsC, YsH, YsW = y.stride()

    has_bias = bias is not None
    if has_bias:
        assert bias.is_cuda and bias.shape == (C,)
        assert bias.dtype == input.dtype

    # 2D tiling configuration
    BLOCK_H = 4
    BLOCK_W = 64

    def grid(meta):
        return (
            triton.cdiv(W_out, meta["BLOCK_W"]),
            triton.cdiv(H_out, meta["BLOCK_H"]),
            N * C
        )

    if K == 3:
        _dwconv2d_kernel_k3[grid](
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
            num_warps=4,
            num_stages=3,
        )
    else:
        _dwconv2d_kernel_optimized[grid](
            input, w3, bias if has_bias else y, y,
            N, C, H, W,
            H_out, W_out,
            XsN, XsC, XsH, XsW,
            WsC, WsKH, WsKW,
            YsN, YsC, YsH, YsW,
            K=K,
            STRIDE=stride_w,
            PADDING=pad_w,
            HAS_BIAS=has_bias,
            BLOCK_H=BLOCK_H,
            BLOCK_W=BLOCK_W,
            num_warps=4,
            num_stages=3,
        )

    return y