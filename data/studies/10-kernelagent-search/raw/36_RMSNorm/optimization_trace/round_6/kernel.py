import torch
import triton
import triton.language as tl


@triton.jit
def _rmsnorm_nchw_fused_kernel(
    x_ptr, y_ptr,
    N, C, H, W,
    HW,  # H * W precomputed
    eps,
    BLOCK_HW: tl.constexpr,
    C_BLOCK: tl.constexpr,
):
    """
    Fused RMSNorm kernel with improved memory access patterns.
    Each program handles one batch element and a block of spatial positions.
    """
    pid = tl.program_id(axis=0)
    num_hw_blocks = tl.cdiv(HW, BLOCK_HW)
    
    n = pid // num_hw_blocks
    hw_block_id = pid % num_hw_blocks
    
    # Spatial position offsets within this block
    hw_start = hw_block_id * BLOCK_HW
    offs_hw = hw_start + tl.arange(0, BLOCK_HW)
    mask_hw = offs_hw < HW
    
    # Base pointer for this batch element
    base_n = n * C * HW
    
    # First pass: compute sum of squares across all channels
    sum_sq = tl.zeros([BLOCK_HW], dtype=tl.float32)
    
    for c in range(0, C, C_BLOCK):
        offs_c = c + tl.arange(0, C_BLOCK)
        mask_c = offs_c < C
        
        # Load x[n, c, hw] - contiguous in HW dimension
        # Offset = n * C * HW + c * HW + hw
        offsets = base_n + offs_c[:, None] * HW + offs_hw[None, :]
        mask = mask_c[:, None] & mask_hw[None, :]
        
        x_vals = tl.load(x_ptr + offsets, mask=mask, other=0.0)
        x_f32 = x_vals.to(tl.float32)
        
        # Accumulate squared values
        sum_sq += tl.sum(x_f32 * x_f32, axis=0)
    
    # Compute inverse RMS
    c_f32 = C.to(tl.float32)
    mean_sq = sum_sq / c_f32
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    # Second pass: normalize and store
    for c in range(0, C, C_BLOCK):
        offs_c = c + tl.arange(0, C_BLOCK)
        mask_c = offs_c < C
        
        offsets = base_n + offs_c[:, None] * HW + offs_hw[None, :]
        mask = mask_c[:, None] & mask_hw[None, :]
        
        x_vals = tl.load(x_ptr + offsets, mask=mask, other=0.0)
        x_f32 = x_vals.to(tl.float32)
        
        # Normalize
        y_f32 = x_f32 * inv_rms[None, :]
        y_vals = y_f32.to(x_vals.dtype)
        
        tl.store(y_ptr + offsets, y_vals, mask=mask)


@triton.jit
def _rmsnorm_nchw_single_pass_kernel(
    x_ptr, y_ptr,
    N, C, HW,
    eps,
    BLOCK_HW: tl.constexpr,
    C_CONST: tl.constexpr,
):
    """
    Single-tile RMSNorm for small channel counts.
    Loads all channels at once for better register utilization.
    """
    pid = tl.program_id(axis=0)
    num_hw_blocks = tl.cdiv(HW, BLOCK_HW)
    
    n = pid // num_hw_blocks
    hw_block_id = pid % num_hw_blocks
    
    hw_start = hw_block_id * BLOCK_HW
    offs_hw = hw_start + tl.arange(0, BLOCK_HW)
    mask_hw = offs_hw < HW
    
    base_n = n * C * HW
    
    offs_c = tl.arange(0, C_CONST)
    mask_c = offs_c < C
    
    # Load all channels at once [C_CONST, BLOCK_HW]
    offsets = base_n + offs_c[:, None] * HW + offs_hw[None, :]
    mask = mask_c[:, None] & mask_hw[None, :]
    
    x_vals = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    x_f32 = x_vals.to(tl.float32)
    
    # Compute sum of squares across channels
    sq = x_f32 * x_f32
    sum_sq = tl.sum(sq, axis=0)
    
    # Compute inverse RMS
    c_f32 = C.to(tl.float32)
    mean_sq = sum_sq / c_f32
    inv_rms = tl.math.rsqrt(mean_sq + eps)
    
    # Normalize and store
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
    
    # Ensure contiguous for optimal memory access
    x_contig = x.contiguous()
    y = torch.empty_like(x_contig)

    if C <= 64:
        C_CONST = 64
        BLOCK_HW = 256
        
        grid = (N * triton.cdiv(HW, BLOCK_HW),)
        
        _rmsnorm_nchw_single_pass_kernel[grid](
            x_contig, y,
            N, C, HW,
            float(eps),
            BLOCK_HW=BLOCK_HW,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=3,
        )
    elif C <= 128:
        C_CONST = 128
        BLOCK_HW = 128
        
        grid = (N * triton.cdiv(HW, BLOCK_HW),)
        
        _rmsnorm_nchw_single_pass_kernel[grid](
            x_contig, y,
            N, C, HW,
            float(eps),
            BLOCK_HW=BLOCK_HW,
            C_CONST=C_CONST,
            num_warps=8,
            num_stages=2,
        )
    else:
        C_BLOCK = 64
        BLOCK_HW = 256
        
        grid = (N * triton.cdiv(HW, BLOCK_HW),)
        
        _rmsnorm_nchw_fused_kernel[grid](
            x_contig, y,
            N, C, H, W,
            HW,
            float(eps),
            BLOCK_HW=BLOCK_HW,
            C_BLOCK=C_BLOCK,
            num_warps=8,
            num_stages=3,
        )

    return y