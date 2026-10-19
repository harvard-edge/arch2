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
    stride: tl.constexpr,
    padding: tl.constexpr,
    dilation: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
    ELEMENTS_PER_THREAD: tl.constexpr,
):
    """
    Optimized 3D Max Pooling kernel with improved compute efficiency.
    """
    pid = tl.program_id(0)
    
    total_outputs = N * C * OD * OH * OW
    
    # Each program processes ELEMENTS_PER_THREAD elements
    base_idx = pid * BLOCK_SIZE * ELEMENTS_PER_THREAD
    
    for elem in range(ELEMENTS_PER_THREAD):
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
        d_start = od * stride - padding
        h_start = oh * stride - padding
        w_start = ow * stride - padding
        
        # Base input offset for (n, c)
        base_offset = n * stride_n + c * stride_c
        
        # Initialize max value
        max_val = tl.full([BLOCK_SIZE], float('-inf'), dtype=tl.float32)
        
        # Unrolled pooling window iteration for common kernel_size=3
        if kernel_size == 3:
            # Manually unroll for kernel_size=3
            for kd in tl.static_range(3):
                d_in = d_start + kd * dilation
                d_valid = (d_in >= 0) & (d_in < D)
                d_offset = d_in * stride_d
                
                for kh in tl.static_range(3):
                    h_in = h_start + kh * dilation
                    h_valid = (h_in >= 0) & (h_in < H)
                    h_offset = h_in * stride_h
                    
                    for kw in tl.static_range(3):
                        w_in = w_start + kw * dilation
                        w_valid = (w_in >= 0) & (w_in < W)
                        
                        valid = mask & d_valid & h_valid & w_valid
                        
                        input_idx = base_offset + d_offset + h_offset + w_in
                        val = tl.load(input_ptr + input_idx, mask=valid, other=float('-inf'))
                        max_val = tl.maximum(max_val, val.to(tl.float32))
        else:
            # Generic path for other kernel sizes
            for kd in range(kernel_size):
                d_in = d_start + kd * dilation
                d_valid = (d_in >= 0) & (d_in < D)
                d_offset = d_in * stride_d
                
                for kh in range(kernel_size):
                    h_in = h_start + kh * dilation
                    h_valid = (h_in >= 0) & (h_in < H)
                    h_offset = h_in * stride_h
                    
                    for kw in range(kernel_size):
                        w_in = w_start + kw * dilation
                        w_valid = (w_in >= 0) & (w_in < W)
                        
                        valid = mask & d_valid & h_valid & w_valid
                        
                        input_idx = base_offset + d_offset + h_offset + w_in
                        val = tl.load(input_ptr + input_idx, mask=valid, other=float('-inf'))
                        max_val = tl.maximum(max_val, val.to(tl.float32))
        
        # Store result
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
    
    # Calculate output dimensions
    OD = (D + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    OH = (H + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    OW = (W + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    
    # Allocate output tensor
    output = torch.empty((N, C, OD, OH, OW), device=x.device, dtype=x.dtype)
    
    # Get strides for efficient indexing
    stride_n = x.stride(0)
    stride_c = x.stride(1)
    stride_d = x.stride(2)
    stride_h = x.stride(3)
    stride_w = x.stride(4)
    
    # Total number of output elements
    total_outputs = N * C * OD * OH * OW
    
    # Launch configuration - optimized for H100
    BLOCK_SIZE = 128
    ELEMENTS_PER_THREAD = 4
    
    grid = (triton.cdiv(total_outputs, BLOCK_SIZE * ELEMENTS_PER_THREAD),)
    
    # Launch kernel
    max_pool3d_kernel_optimized[grid](
        x,
        output,
        N, C, D, H, W,
        OD, OH, OW,
        stride_n, stride_c, stride_d, stride_h, stride_w,
        kernel_size=kernel_size,
        stride=stride,
        padding=padding,
        dilation=dilation,
        BLOCK_SIZE=BLOCK_SIZE,
        ELEMENTS_PER_THREAD=ELEMENTS_PER_THREAD,
    )
    
    return output