import torch
import triton
import triton.language as tl


@triton.jit
def _rmsnorm_nchw_vectorized_kernel(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_nx, stride_cx, stride_hx, stride_wx,
    stride_ny, stride_cy, stride_hy, stride_wy,
    eps,
    BLOCK_W: tl.constexpr,
    C_CONST: tl.constexpr,
):
    """
    RMSNorm kernel with vectorized memory access.
    Each thread processes multiple width positions for better coalescing.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh % H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    # Base offset for this (n, h) position
    base_x = n * stride_nx + h * stride_hx
    base_y = n * stride_ny + h * stride_hy

    # Channel offsets
    offs_c = tl.arange(0, C_CONST)
    mask_c = offs_c < C
    
    # Compute 2D offsets [C_CONST, BLOCK_W]
    x_offsets = base_x + offs_c[:, None] * stride_cx + offs_w[None, :] * stride_wx
    mask_2d = mask_c[:, None] & mask_w[None, :]
    
    # Load with vectorized pattern - threads access contiguous W positions
    x_vals = tl.load(x_ptr + x_offsets, mask=mask_2d, other=0.0)
    x_f32 = x_vals.to(tl.float32)
    
    # Compute sum of squares across channels
    sq = x_f32 * x_f32
    sum_sq = tl.sum(sq, axis=0)  # [BLOCK_W]
    
    # Compute inverse RMS
    c_f32 = C.to(tl.float32)
    mean_sq = sum_sq / c_f32
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    # Normalize
    y_f32 = x_f32 * inv_rms[None, :]
    y_vals = y_f32.to(x_vals.dtype)
    
    # Store results
    y_offsets = base_y + offs_c[:, None] * stride_cy + offs_w[None, :] * stride_wy
    tl.store(y_ptr + y_offsets, y_vals, mask=mask_2d)


@triton.jit
def _rmsnorm_nchw_wide_kernel(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_nx, stride_cx, stride_hx, stride_wx,
    stride_ny, stride_cy, stride_hy, stride_wy,
    eps,
    BLOCK_W: tl.constexpr,
    C_CONST: tl.constexpr,
):
    """
    Wide kernel processing more W elements per block for better memory utilization.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh % H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    base_x = n * stride_nx + h * stride_hx
    base_y = n * stride_ny + h * stride_hy

    offs_c = tl.arange(0, C_CONST)
    mask_c = offs_c < C
    
    x_offsets = base_x + offs_c[:, None] * stride_cx + offs_w[None, :] * stride_wx
    mask_2d = mask_c[:, None] & mask_w[None, :]
    
    x_vals = tl.load(x_ptr + x_offsets, mask=mask_2d, other=0.0)
    x_f32 = x_vals.to(tl.float32)
    
    sq = x_f32 * x_f32
    sum_sq = tl.sum(sq, axis=0)
    
    c_f32 = C.to(tl.float32)
    mean_sq = sum_sq / c_f32
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    y_f32 = x_f32 * inv_rms[None, :]
    y_vals = y_f32.to(x_vals.dtype)
    
    y_offsets = base_y + offs_c[:, None] * stride_cy + offs_w[None, :] * stride_wy
    tl.store(y_ptr + y_offsets, y_vals, mask=mask_2d)


def kernel_function(x, *args, **kwargs):
    """
    RMSNorm for NCHW tensors.
    Normalizes across the channel dimension: y = x / sqrt(mean(x^2) + eps)
    """
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
    
    y = torch.empty_like(x)

    sx0, sx1, sx2, sx3 = x.stride()
    sy0, sy1, sy2, sy3 = y.stride()

    # Optimized configuration for C=64, W=512
    # Use wider BLOCK_W for better memory coalescing and throughput
    if C <= 64:
        C_CONST = 64
        BLOCK_W = 256  # Wider block for better memory utilization
        num_warps = 8
        num_stages = 3
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_wide_kernel[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            sy0, sy1, sy2, sy3,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=num_warps,
            num_stages=num_stages,
        )
    elif C <= 128:
        C_CONST = 128
        BLOCK_W = 128
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_vectorized_kernel[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            sy0, sy1, sy2, sy3,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=3,
        )
    else:
        C_CONST = 256
        BLOCK_W = 64
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_vectorized_kernel[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            sy0, sy1, sy2, sy3,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=2,
        )

    return y