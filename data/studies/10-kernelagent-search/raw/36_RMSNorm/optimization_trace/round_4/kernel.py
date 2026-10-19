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
):
    """
    Optimized RMSNorm kernel using vectorized memory access.
    Each program handles one (n, h, w_block) tile across all channels.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh % H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    # Base offset for this (n, h) position
    base_offset = n * stride_n + h * stride_h

    # Accumulate sum of squares across all channels
    sum_sq = tl.zeros([BLOCK_W], dtype=tl.float32)
    
    # First pass: compute sum of squares
    for c in range(C_CONST):
        c_mask = c < C
        x_ptrs = x_ptr + base_offset + c * stride_c + offs_w * stride_w
        x_vals = tl.load(x_ptrs, mask=mask_w & c_mask, other=0.0)
        x_f32 = x_vals.to(tl.float32)
        sum_sq += x_f32 * x_f32
    
    # Compute inverse RMS
    c_f32 = C.to(tl.float32)
    mean_sq = sum_sq / c_f32
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    # Second pass: normalize and store
    for c in range(C_CONST):
        c_mask = c < C
        x_ptrs = x_ptr + base_offset + c * stride_c + offs_w * stride_w
        x_vals = tl.load(x_ptrs, mask=mask_w & c_mask, other=0.0)
        x_f32 = x_vals.to(tl.float32)
        y_f32 = x_f32 * inv_rms
        y_vals = y_f32.to(x_vals.dtype)
        y_ptrs = y_ptr + base_offset + c * stride_c + offs_w * stride_w
        tl.store(y_ptrs, y_vals, mask=mask_w & c_mask)


@triton.jit
def _rmsnorm_nchw_fused_kernel(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_n, stride_c, stride_h, stride_w,
    eps,
    BLOCK_W: tl.constexpr,
    BLOCK_C: tl.constexpr,
):
    """
    Fused RMSNorm kernel with register tiling for small C.
    Loads all C channels into registers, computes norm, and stores.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh % H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    base_offset = n * stride_n + h * stride_h
    
    offs_c = tl.arange(0, BLOCK_C)
    mask_c = offs_c < C
    
    # Load all channels for this W block [BLOCK_C, BLOCK_W]
    x_offsets = base_offset + offs_c[:, None] * stride_c + offs_w[None, :] * stride_w
    mask_2d = mask_c[:, None] & mask_w[None, :]
    
    x_vals = tl.load(x_ptr + x_offsets, mask=mask_2d, other=0.0)
    x_f32 = x_vals.to(tl.float32)
    
    # Compute sum of squares across channels
    sq = x_f32 * x_f32
    sum_sq = tl.sum(sq, axis=0)
    
    # Compute inverse RMS
    c_f32 = C.to(tl.float32)
    mean_sq = sum_sq / c_f32
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    # Normalize
    y_f32 = x_f32 * inv_rms[None, :]
    y_vals = y_f32.to(x_vals.dtype)
    
    # Store
    tl.store(y_ptr + x_offsets, y_vals, mask=mask_2d)


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

    if C <= 64:
        # Use fused kernel with all channels in registers
        BLOCK_C = 64
        BLOCK_W = 256  # Larger W block for better memory coalescing
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_fused_kernel[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            float(eps),
            BLOCK_W=BLOCK_W,
            BLOCK_C=BLOCK_C,
            num_warps=8,
            num_stages=4,
        )
    elif C <= 128:
        BLOCK_C = 128
        BLOCK_W = 128
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_fused_kernel[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            float(eps),
            BLOCK_W=BLOCK_W,
            BLOCK_C=BLOCK_C,
            num_warps=8,
            num_stages=3,
        )
    else:
        # For larger C, use loop-based kernel
        C_CONST = C
        BLOCK_W = 256
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_vectorized_kernel[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=4,
        )

    return y