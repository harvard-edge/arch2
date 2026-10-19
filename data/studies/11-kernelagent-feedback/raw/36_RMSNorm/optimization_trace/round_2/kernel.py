import torch
import triton
import triton.language as tl


@triton.jit
def _rmsnorm_nchw_kernel_vectorized(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_nx, stride_cx, stride_hx, stride_wx,
    stride_ny, stride_cy, stride_hy, stride_wy,
    eps,
    BLOCK_W: tl.constexpr,
    C_CONST: tl.constexpr,
):
    """
    Optimized RMSNorm kernel with vectorized loads for better memory throughput.
    RMSNorm normalizes across the channel dimension for each spatial location.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh % H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    # Base offsets for this (n, h) position
    base_nh_x = n * stride_nx + h * stride_hx
    base_nh_y = n * stride_ny + h * stride_hy

    # Load all channels into registers and compute sum of squares
    offs_c = tl.arange(0, C_CONST)
    mask_c = offs_c < C
    
    # Create 2D offset grid [C_CONST, BLOCK_W]
    x_offsets_2d = base_nh_x + offs_c[:, None] * stride_cx + offs_w[None, :] * stride_wx
    mask_2d = mask_c[:, None] & mask_w[None, :]
    
    # Load all values at once
    x_vals_2d = tl.load(x_ptr + x_offsets_2d, mask=mask_2d, other=0.0)
    x_f32_2d = x_vals_2d.to(tl.float32)
    
    # Sum of squares across channels (axis=0)
    sq_2d = x_f32_2d * x_f32_2d
    acc = tl.sum(sq_2d, axis=0)
    
    # Compute inverse RMS
    c_f32 = C.to(tl.float32)
    mean = acc / c_f32
    inv_rms = tl.math.rsqrt(mean + eps)
    
    # Normalize and store
    y_f32_2d = x_f32_2d * inv_rms[None, :]
    y_vals_2d = y_f32_2d.to(x_vals_2d.dtype)
    
    y_offsets_2d = base_nh_y + offs_c[:, None] * stride_cy + offs_w[None, :] * stride_wy
    tl.store(y_ptr + y_offsets_2d, y_vals_2d, mask=mask_2d)


@triton.jit
def _rmsnorm_nchw_kernel_large_c(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_nx, stride_cx, stride_hx, stride_wx,
    stride_ny, stride_cy, stride_hy, stride_wy,
    eps,
    BLOCK_W: tl.constexpr,
    BLOCK_C: tl.constexpr,
):
    """
    RMSNorm kernel for larger C values, using blocked accumulation.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh % H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    base_nh_x = n * stride_nx + h * stride_hx
    base_nh_y = n * stride_ny + h * stride_hy

    # Accumulator for sum of squares
    acc = tl.zeros([BLOCK_W], dtype=tl.float32)
    
    offs_c_base = tl.arange(0, BLOCK_C)
    
    # First pass: accumulate sum of squares in blocks
    for c_start in range(0, C, BLOCK_C):
        offs_c = c_start + offs_c_base
        mask_c = offs_c < C
        
        x_offsets_2d = base_nh_x + offs_c[:, None] * stride_cx + offs_w[None, :] * stride_wx
        mask_2d = mask_c[:, None] & mask_w[None, :]
        
        x_vals_2d = tl.load(x_ptr + x_offsets_2d, mask=mask_2d, other=0.0)
        x_f32_2d = x_vals_2d.to(tl.float32)
        
        sq_2d = x_f32_2d * x_f32_2d
        acc += tl.sum(sq_2d, axis=0)

    # Compute inverse RMS
    c_f32 = C.to(tl.float32)
    mean = acc / c_f32
    inv_rms = tl.math.rsqrt(mean + eps)

    # Second pass: normalize and store
    for c_start in range(0, C, BLOCK_C):
        offs_c = c_start + offs_c_base
        mask_c = offs_c < C
        
        x_offsets_2d = base_nh_x + offs_c[:, None] * stride_cx + offs_w[None, :] * stride_wx
        mask_2d = mask_c[:, None] & mask_w[None, :]
        
        x_vals_2d = tl.load(x_ptr + x_offsets_2d, mask=mask_2d, other=0.0)
        x_f32_2d = x_vals_2d.to(tl.float32)
        
        y_f32_2d = x_f32_2d * inv_rms[None, :]
        y_vals_2d = y_f32_2d.to(x_vals_2d.dtype)
        
        y_offsets_2d = base_nh_y + offs_c[:, None] * stride_cy + offs_w[None, :] * stride_wy
        tl.store(y_ptr + y_offsets_2d, y_vals_2d, mask=mask_2d)


def kernel_function(x, *args, **kwargs):
    if not isinstance(x, torch.Tensor):
        raise TypeError("x must be a torch.Tensor")
    if x.device.type != "cuda":
        raise ValueError("x must be on CUDA device")
    if x.ndim != 4:
        raise ValueError(f"Expected 4D NCHW tensor, got shape {tuple(x.shape)}")

    eps = kwargs.get("eps", 1e-5)
    
    if len(args) >= 1 and isinstance(args[0], float):
        eps = args[0]

    N, C, H, W = x.shape

    # Allocate output tensor
    y = torch.empty_like(x)

    sx0, sx1, sx2, sx3 = x.stride()
    sy0, sy1, sy2, sy3 = y.stride()

    if C <= 64:
        C_CONST = 64
        BLOCK_W = 256
        num_warps = 8
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_kernel_vectorized[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            sy0, sy1, sy2, sy3,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=num_warps,
            num_stages=3,
        )
    elif C <= 128:
        C_CONST = 128
        BLOCK_W = 128
        num_warps = 8
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_kernel_vectorized[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            sy0, sy1, sy2, sy3,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=num_warps,
            num_stages=2,
        )
    else:
        BLOCK_W = 128
        BLOCK_C = 64
        num_warps = 8
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)

        _rmsnorm_nchw_kernel_large_c[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            sy0, sy1, sy2, sy3,
            float(eps),
            BLOCK_W=BLOCK_W,
            BLOCK_C=BLOCK_C,
            num_warps=num_warps,
            num_stages=2,
        )

    return y