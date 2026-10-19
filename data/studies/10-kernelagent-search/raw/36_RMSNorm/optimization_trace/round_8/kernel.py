import torch
import triton
import triton.language as tl


@triton.jit
def _rmsnorm_nchw_vectorized_kernel(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_n, stride_c, stride_h, stride_w,
    eps,
    BLOCK_W: tl.constexpr,
    C_CONST: tl.constexpr,
    VECTOR_SIZE: tl.constexpr,
):
    """
    Optimized RMSNorm kernel using vectorized loads for better memory bandwidth.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh % H

    # Process BLOCK_W width positions, with VECTOR_SIZE elements per vector load
    start_w = pid_w * BLOCK_W
    
    # Base offset for this (n, h) position
    base_offset = n * stride_n + h * stride_h
    
    # Channel offsets
    offs_c = tl.arange(0, C_CONST)
    mask_c = offs_c < C
    
    # Width offsets within this block
    offs_w = tl.arange(0, BLOCK_W)
    w_positions = start_w + offs_w
    mask_w = w_positions < W
    
    # Compute offsets for 2D tile [C_CONST, BLOCK_W]
    # Each element at (c, w) has offset: base + c * stride_c + w * stride_w
    offsets_2d = base_offset + offs_c[:, None] * stride_c + w_positions[None, :] * stride_w
    mask_2d = mask_c[:, None] & mask_w[None, :]
    
    # Load with cache hints for better L2 utilization
    x_vals = tl.load(x_ptr + offsets_2d, mask=mask_2d, other=0.0, eviction_policy="evict_last")
    x_f32 = x_vals.to(tl.float32)
    
    # Compute sum of squares across channels (axis=0)
    sq = x_f32 * x_f32
    sum_sq = tl.sum(sq, axis=0)  # [BLOCK_W]
    
    # Compute inverse RMS: 1 / sqrt(mean(x^2) + eps)
    c_f32 = C.to(tl.float32)
    mean_sq = sum_sq / c_f32
    inv_rms = tl.math.rsqrt(mean_sq + eps)  # [BLOCK_W]
    
    # Normalize: y = x * inv_rms
    y_f32 = x_f32 * inv_rms[None, :]
    y_vals = y_f32.to(x_vals.dtype)
    
    # Store results
    tl.store(y_ptr + offsets_2d, y_vals, mask=mask_2d)


@triton.jit
def _rmsnorm_nchw_large_tile_kernel(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_n, stride_c, stride_h, stride_w,
    eps,
    BLOCK_W: tl.constexpr,
    C_CONST: tl.constexpr,
):
    """
    RMSNorm with larger tiles for better data reuse.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh % H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    base_offset = n * stride_n + h * stride_h

    offs_c = tl.arange(0, C_CONST)
    mask_c = offs_c < C
    
    # 2D offsets [C_CONST, BLOCK_W]
    offsets_2d = base_offset + offs_c[:, None] * stride_c + offs_w[None, :] * stride_w
    mask_2d = mask_c[:, None] & mask_w[None, :]
    
    # Load all values with eviction policy for better cache behavior
    x_vals = tl.load(x_ptr + offsets_2d, mask=mask_2d, other=0.0, eviction_policy="evict_last")
    x_f32 = x_vals.to(tl.float32)
    
    # Compute sum of squares across channels
    sq = x_f32 * x_f32
    sum_sq = tl.sum(sq, axis=0)
    
    # Inverse RMS
    c_f32 = C.to(tl.float32)
    mean_sq = sum_sq / c_f32
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    # Normalize and store
    y_f32 = x_f32 * inv_rms[None, :]
    y_vals = y_f32.to(x_vals.dtype)
    
    tl.store(y_ptr + offsets_2d, y_vals, mask=mask_2d)


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

    stride_n, stride_c, stride_h, stride_w = x.stride()

    # For C=64, use larger BLOCK_W for better memory throughput
    if C <= 64:
        C_CONST = 64
        BLOCK_W = 256  # Larger block for better bandwidth utilization
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_large_tile_kernel[grid](
            x, y,
            N, C, H, W,
            stride_n, stride_c, stride_h, stride_w,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=4,
        )
    elif C <= 128:
        C_CONST = 128
        BLOCK_W = 128
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_large_tile_kernel[grid](
            x, y,
            N, C, H, W,
            stride_n, stride_c, stride_h, stride_w,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=4,
        )
    elif C <= 256:
        C_CONST = 256
        BLOCK_W = 64
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_large_tile_kernel[grid](
            x, y,
            N, C, H, W,
            stride_n, stride_c, stride_h, stride_w,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=3,
        )
    else:
        C_CONST = 64
        BLOCK_W = 128
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_vectorized_kernel[grid](
            x, y,
            N, C, H, W,
            stride_n, stride_c, stride_h, stride_w,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            VECTOR_SIZE=4,
            num_warps=8,
            num_stages=4,
        )

    return y