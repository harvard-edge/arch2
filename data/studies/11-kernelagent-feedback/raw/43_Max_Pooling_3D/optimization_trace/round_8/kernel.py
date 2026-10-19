import torch
import triton
import triton.language as tl


@triton.jit
def max_pool3d_kernel_optimized(
    input_ptr,
    output_ptr,
    N, C, D, H, W,
    OD, OH, OW,
    stride_n, stride_c, stride_d, stride_h, stride_w,
    kernel_size: tl.constexpr,
    pool_stride: tl.constexpr,
    padding: tl.constexpr,
    dilation: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
):
    """
    Optimized 3D Max Pooling kernel.
    Uses vectorized processing along the W dimension for better coalescing.
    """
    pid = tl.program_id(0)
    
    # Total number of output elements
    total_outputs = N * C * OD * OH * OW
    
    # Process BLOCK_SIZE elements per program
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < total_outputs
    
    # Decompose linear index to (n, c, od, oh, ow)
    # Keep ow as innermost for coalesced access
    ow = offs % OW
    tmp = offs // OW
    oh = tmp % OH
    tmp = tmp // OH
    od = tmp % OD
    tmp = tmp // OD
    c = tmp % C
    n = tmp // C
    
    # Compute input starting positions
    d_start = od * pool_stride - padding
    h_start = oh * pool_stride - padding
    w_start = ow * pool_stride - padding
    
    # Base offset for each element
    base_offset = n * stride_n + c * stride_c
    
    # Initialize max values to -inf
    max_val = tl.full([BLOCK_SIZE], float('-inf'), dtype=tl.float32)
    
    # Unrolled loops for common kernel sizes
    # Process kw in innermost loop for better memory access pattern
    for kd in tl.static_range(kernel_size):
        d_in = d_start + kd * dilation
        d_valid = (d_in >= 0) & (d_in < D)
        d_offset = d_in * stride_d
        
        for kh in tl.static_range(kernel_size):
            h_in = h_start + kh * dilation
            h_valid = (h_in >= 0) & (h_in < H)
            h_offset = h_in * stride_h
            
            # Pre-compute combined validity and offset for this (kd, kh) pair
            dh_valid = mask & d_valid & h_valid
            dh_offset = base_offset + d_offset + h_offset
            
            for kw in tl.static_range(kernel_size):
                w_in = w_start + kw * dilation
                w_valid = (w_in >= 0) & (w_in < W)
                
                # Combined validity check
                valid = dh_valid & w_valid
                
                # Compute input indices - w_in varies across threads for coalescing
                input_idx = dh_offset + w_in * stride_w
                
                # Load input values with masking
                val = tl.load(input_ptr + input_idx, mask=valid, other=float('-inf'))
                val = val.to(tl.float32)
                
                # Update max
                max_val = tl.maximum(max_val, val)
    
    # Store results - coalesced write since ow varies across threads
    tl.store(output_ptr + offs, max_val, mask=mask)


def kernel_function(x, kernel_size=2, stride=2, padding=0, dilation=1):
    """
    3D Max Pooling wrapper function.
    """
    # Handle tuple/list parameters
    if isinstance(kernel_size, (tuple, list)):
        kernel_size = kernel_size[0]
    if isinstance(stride, (tuple, list)):
        stride = stride[0]
    if isinstance(padding, (tuple, list)):
        padding = padding[0]
    if isinstance(dilation, (tuple, list)):
        dilation = dilation[0]
    
    # Ensure input is contiguous
    x = x.contiguous()
    
    # Get input dimensions
    N, C, D, H, W = x.shape
    
    # Get strides
    stride_n, stride_c, stride_d, stride_h, stride_w = x.stride()
    
    # Calculate output dimensions
    OD = (D + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    OH = (H + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    OW = (W + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    
    # Allocate output tensor
    output = torch.empty((N, C, OD, OH, OW), device=x.device, dtype=x.dtype)
    
    # Total number of output elements
    total_outputs = N * C * OD * OH * OW
    
    # Use larger block size for better occupancy
    BLOCK_SIZE = 512
    grid = (triton.cdiv(total_outputs, BLOCK_SIZE),)
    
    # Launch kernel
    max_pool3d_kernel_optimized[grid](
        x,
        output,
        N, C, D, H, W,
        OD, OH, OW,
        stride_n, stride_c, stride_d, stride_h, stride_w,
        kernel_size=kernel_size,
        pool_stride=stride,
        padding=padding,
        dilation=dilation,
        BLOCK_SIZE=BLOCK_SIZE,
    )
    
    return output