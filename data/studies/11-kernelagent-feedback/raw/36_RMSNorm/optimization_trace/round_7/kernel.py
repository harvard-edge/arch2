import torch
import triton
import triton.language as tl


@triton.jit
def _rmsnorm_nchw_vectorized_kernel(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_n, stride_c, stride_h, stride_w,
    eps,
    HW: tl.constexpr,
    BLOCK_HW: tl.constexpr,
    C_BLOCK: tl.constexpr,
):
    """
    Optimized RMSNorm kernel with better memory coalescing.
    Each program handles a tile of spatial positions for one batch element.
    """
    pid = tl.program_id(0)
    num_hw_blocks = tl.cdiv(HW, BLOCK_HW)
    
    n = pid // num_hw_blocks
    hw_block_id = pid % num_hw_blocks
    
    hw_start = hw_block_id * BLOCK_HW
    hw_offs = hw_start + tl.arange(0, BLOCK_HW)
    hw_mask = hw_offs < HW
    
    # Convert linear hw index to h, w coordinates
    h_idx = hw_offs // W
    w_idx = hw_offs % W
    
    # Compute sum of squares across channels
    sum_sq = tl.zeros([BLOCK_HW], dtype=tl.float32)
    
    for c_start in range(0, C, C_BLOCK):
        c_offs = c_start + tl.arange(0, C_BLOCK)
        c_mask = c_offs < C
        
        # Compute offsets: [C_BLOCK, BLOCK_HW]
        offsets = (n * stride_n + 
                   c_offs[:, None] * stride_c + 
                   h_idx[None, :] * stride_h + 
                   w_idx[None, :] * stride_w)
        
        mask = c_mask[:, None] & hw_mask[None, :]
        
        x_vals = tl.load(x_ptr + offsets, mask=mask, other=0.0)
        x_f32 = x_vals.to(tl.float32)
        
        sum_sq += tl.sum(x_f32 * x_f32, axis=0)
    
    # Compute inverse RMS
    mean_sq = sum_sq / C
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    # Second pass: normalize and store
    for c_start in range(0, C, C_BLOCK):
        c_offs = c_start + tl.arange(0, C_BLOCK)
        c_mask = c_offs < C
        
        offsets = (n * stride_n + 
                   c_offs[:, None] * stride_c + 
                   h_idx[None, :] * stride_h + 
                   w_idx[None, :] * stride_w)
        
        mask = c_mask[:, None] & hw_mask[None, :]
        
        x_vals = tl.load(x_ptr + offsets, mask=mask, other=0.0)
        x_f32 = x_vals.to(tl.float32)
        
        y_f32 = x_f32 * inv_rms[None, :]
        y_vals = y_f32.to(x_vals.dtype)
        
        tl.store(y_ptr + offsets, y_vals, mask=mask)


@triton.jit
def _rmsnorm_nchw_fused_kernel(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_n, stride_c, stride_h, stride_w,
    eps,
    HW: tl.constexpr,
    BLOCK_HW: tl.constexpr,
    C_CONST: tl.constexpr,
):
    """
    Fused single-load kernel for small C that fits in registers.
    """
    pid = tl.program_id(0)
    num_hw_blocks = tl.cdiv(HW, BLOCK_HW)
    
    n = pid // num_hw_blocks
    hw_block_id = pid % num_hw_blocks
    
    hw_start = hw_block_id * BLOCK_HW
    hw_offs = hw_start + tl.arange(0, BLOCK_HW)
    hw_mask = hw_offs < HW
    
    h_idx = hw_offs // W
    w_idx = hw_offs % W
    
    c_offs = tl.arange(0, C_CONST)
    c_mask = c_offs < C
    
    # Load all channels at once: [C_CONST, BLOCK_HW]
    offsets = (n * stride_n + 
               c_offs[:, None] * stride_c + 
               h_idx[None, :] * stride_h + 
               w_idx[None, :] * stride_w)
    
    mask = c_mask[:, None] & hw_mask[None, :]
    
    x_vals = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    x_f32 = x_vals.to(tl.float32)
    
    # Compute sum of squares across channels
    sq = x_f32 * x_f32
    sum_sq = tl.sum(sq, axis=0)
    
    # Compute inverse RMS
    mean_sq = sum_sq / C
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    # Normalize
    y_f32 = x_f32 * inv_rms[None, :]
    y_vals = y_f32.to(x_vals.dtype)
    
    tl.store(y_ptr + offsets, y_vals, mask=mask)


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
    HW = H * W
    
    y = torch.empty_like(x)

    stride_n, stride_c, stride_h, stride_w = x.stride()

    if C <= 64:
        C_CONST = 64
        BLOCK_HW = 256
        
        num_hw_blocks = triton.cdiv(HW, BLOCK_HW)
        grid = (N * num_hw_blocks,)
        
        _rmsnorm_nchw_fused_kernel[grid](
            x, y,
            N, C, H, W,
            stride_n, stride_c, stride_h, stride_w,
            float(eps),
            HW=HW,
            BLOCK_HW=BLOCK_HW,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=2,
        )
    elif C <= 128:
        C_CONST = 128
        BLOCK_HW = 128
        
        num_hw_blocks = triton.cdiv(HW, BLOCK_HW)
        grid = (N * num_hw_blocks,)
        
        _rmsnorm_nchw_fused_kernel[grid](
            x, y,
            N, C, H, W,
            stride_n, stride_c, stride_h, stride_w,
            float(eps),
            HW=HW,
            BLOCK_HW=BLOCK_HW,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=2,
        )
    else:
        C_BLOCK = 64
        BLOCK_HW = 256
        
        num_hw_blocks = triton.cdiv(HW, BLOCK_HW)
        grid = (N * num_hw_blocks,)
        
        _rmsnorm_nchw_vectorized_kernel[grid](
            x, y,
            N, C, H, W,
            stride_n, stride_c, stride_h, stride_w,
            float(eps),
            HW=HW,
            BLOCK_HW=BLOCK_HW,
            C_BLOCK=C_BLOCK,
            num_warps=8,
            num_stages=4,
        )

    return y