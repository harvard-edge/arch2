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
    ELEMENTS_PER_THREAD: tl.constexpr,
):
    """
    Optimized 3D Max Pooling kernel with increased arithmetic intensity.
    Each thread processes multiple output elements to amortize loop overhead.
    """
    pid = tl.program_id(0)
    
    total_outputs = N * C * OD * OH * OW
    
    # Each program processes BLOCK_SIZE * ELEMENTS_PER_THREAD elements
    base_idx = pid * BLOCK_SIZE * ELEMENTS_PER_THREAD
    
    # Process ELEMENTS_PER_THREAD elements per thread
    for elem in tl.static_range(ELEMENTS_PER_THREAD):
        offs = base_idx + elem * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
        mask = offs < total_outputs
        
        # Decompose linear index to (n, c, od, oh, ow)
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
        
        # Iterate over the pooling window
        for kd in tl.static_range(kernel_size):
            d_in = d_start + kd * dilation
            d_valid = (d_in >= 0) & (d_in < D)
            d_offset = d_in * stride_d
            
            for kh in tl.static_range(kernel_size):
                h_in = h_start + kh * dilation
                h_valid = (h_in >= 0) & (h_in < H)
                dh_valid = d_valid & h_valid
                h_offset = h_in * stride_h
                dh_offset = d_offset + h_offset
                
                for kw in tl.static_range(kernel_size):
                    w_in = w_start + kw * dilation
                    w_valid = (w_in >= 0) & (w_in < W)
                    
                    # Combined validity check
                    valid = mask & dh_valid & w_valid
                    
                    # Compute input indices
                    input_idx = base_offset + dh_offset + w_in * stride_w
                    
                    # Load input values with masking
                    val = tl.load(input_ptr + input_idx, mask=valid, other=float('-inf'))
                    val = val.to(tl.float32)
                    
                    # Update max
                    max_val = tl.maximum(max_val, val)
        
        # Store results
        tl.store(output_ptr + offs, max_val, mask=mask)


@triton.jit
def max_pool3d_kernel_vectorized(
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
    Optimized 3D Max Pooling kernel with better register utilization.
    """
    pid = tl.program_id(0)
    
    total_outputs = N * C * OD * OH * OW
    
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < total_outputs
    
    # Decompose linear index to (n, c, od, oh, ow)
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
    
    # Base offset for each element - compute once
    base_offset = n * stride_n + c * stride_c
    
    # Initialize max values
    max_val = tl.full([BLOCK_SIZE], float('-inf'), dtype=tl.float32)
    
    # Precompute d offsets and validity
    for kd in tl.static_range(kernel_size):
        d_in = d_start + kd * dilation
        d_valid = (d_in >= 0) & (d_in < D)
        d_offset = d_in * stride_d
        
        for kh in tl.static_range(kernel_size):
            h_in = h_start + kh * dilation
            h_valid = (h_in >= 0) & (h_in < H)
            dh_valid = d_valid & h_valid
            dh_offset = base_offset + d_offset + h_in * stride_h
            
            for kw in tl.static_range(kernel_size):
                w_in = w_start + kw * dilation
                w_valid = (w_in >= 0) & (w_in < W)
                valid = mask & dh_valid & w_valid
                
                input_idx = dh_offset + w_in * stride_w
                val = tl.load(input_ptr + input_idx, mask=valid, other=float('-inf'))
                max_val = tl.maximum(max_val, val.to(tl.float32))
    
    tl.store(output_ptr + offs, max_val, mask=mask)


def kernel_function(x, kernel_size=2, stride=2, padding=0, dilation=1):
    """
    3D Max Pooling wrapper function.
    """
    if isinstance(kernel_size, (tuple, list)):
        kernel_size = kernel_size[0]
    if isinstance(stride, (tuple, list)):
        stride = stride[0]
    if isinstance(padding, (tuple, list)):
        padding = padding[0]
    if isinstance(dilation, (tuple, list)):
        dilation = dilation[0]
    
    x = x.contiguous()
    
    N, C, D, H, W = x.shape
    stride_n, stride_c, stride_d, stride_h, stride_w = x.stride()
    
    OD = (D + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    OH = (H + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    OW = (W + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    
    output = torch.empty((N, C, OD, OH, OW), device=x.device, dtype=x.dtype)
    
    total_outputs = N * C * OD * OH * OW
    
    # Use larger block size for better occupancy
    BLOCK_SIZE = 512
    ELEMENTS_PER_THREAD = 4
    
    grid = (triton.cdiv(total_outputs, BLOCK_SIZE * ELEMENTS_PER_THREAD),)
    
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
        ELEMENTS_PER_THREAD=ELEMENTS_PER_THREAD,
    )
    
    return output