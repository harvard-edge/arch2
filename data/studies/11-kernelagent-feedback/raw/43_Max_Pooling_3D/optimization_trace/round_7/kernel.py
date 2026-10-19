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
    out_stride_n, out_stride_c, out_stride_d, out_stride_h, out_stride_w,
    kernel_size: tl.constexpr,
    pool_stride: tl.constexpr,
    padding: tl.constexpr,
    dilation: tl.constexpr,
    BLOCK_OW: tl.constexpr,
    BLOCK_OH: tl.constexpr,
):
    """
    Optimized 3D Max Pooling kernel.
    Each program handles a tile of output elements along OH and OW dimensions.
    This ensures coalesced memory access patterns for both reads and writes.
    """
    # Program IDs for different dimensions
    pid_ow = tl.program_id(0)  # Block along OW
    pid_oh = tl.program_id(1)  # Block along OH
    pid_ncd = tl.program_id(2)  # Combined N, C, OD
    
    # Decompose pid_ncd into n, c, od
    od = pid_ncd % OD
    tmp = pid_ncd // OD
    c = tmp % C
    n = tmp // C
    
    # Compute output positions for this block
    ow_base = pid_ow * BLOCK_OW
    oh_base = pid_oh * BLOCK_OH
    
    # Offsets within the block
    ow_offs = ow_base + tl.arange(0, BLOCK_OW)
    oh_offs = oh_base + tl.arange(0, BLOCK_OH)
    
    # Masks for valid output positions
    ow_mask = ow_offs < OW
    oh_mask = oh_offs < OH
    
    # Compute input starting positions for depth
    d_start = od * pool_stride - padding
    
    # Base offset for this (n, c) slice
    base_input = n * stride_n + c * stride_c
    base_output = n * out_stride_n + c * out_stride_c + od * out_stride_d
    
    # Process each (oh, ow) position in the tile
    for oh_idx in range(BLOCK_OH):
        oh = oh_base + oh_idx
        if oh >= OH:
            continue
            
        h_start = oh * pool_stride - padding
        
        for ow_idx in range(BLOCK_OW):
            ow = ow_base + ow_idx
            if ow >= OW:
                continue
                
            w_start = ow * pool_stride - padding
            
            # Initialize max value
            max_val = float('-inf')
            
            # Iterate over the pooling window
            for kd in tl.static_range(kernel_size):
                d_in = d_start + kd * dilation
                if d_in >= 0 and d_in < D:
                    d_offset = d_in * stride_d
                    
                    for kh in tl.static_range(kernel_size):
                        h_in = h_start + kh * dilation
                        if h_in >= 0 and h_in < H:
                            h_offset = h_in * stride_h
                            
                            for kw in tl.static_range(kernel_size):
                                w_in = w_start + kw * dilation
                                if w_in >= 0 and w_in < W:
                                    # Compute input index
                                    input_idx = base_input + d_offset + h_offset + w_in * stride_w
                                    
                                    # Load and update max
                                    val = tl.load(input_ptr + input_idx).to(tl.float32)
                                    max_val = tl.maximum(max_val, val)
            
            # Store result
            output_idx = base_output + oh * out_stride_h + ow * out_stride_w
            tl.store(output_ptr + output_idx, max_val)


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
    Vectorized 3D Max Pooling kernel with improved memory access patterns.
    """
    pid = tl.program_id(0)
    
    # Each program processes BLOCK_SIZE consecutive output elements along OW
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    total_outputs = N * C * OD * OH * OW
    mask = offs < total_outputs
    
    # Decompose linear index - OW is innermost for coalesced access
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
    
    # Initialize max values
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
            
            for kw in tl.static_range(kernel_size):
                w_in = w_start + kw * dilation
                w_valid = (w_in >= 0) & (w_in < W)
                
                valid = mask & dh_valid & w_valid
                
                input_idx = base_offset + d_offset + h_offset + w_in * stride_w
                
                val = tl.load(input_ptr + input_idx, mask=valid, other=float('-inf'))
                max_val = tl.maximum(max_val, val.to(tl.float32))
    
    tl.store(output_ptr + offs, max_val, mask=mask)


def kernel_function(x, kernel_size=2, stride=2, padding=0, dilation=1):
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
    BLOCK_SIZE = 512
    grid = (triton.cdiv(total_outputs, BLOCK_SIZE),)
    
    max_pool3d_kernel_vectorized[grid](
        x, output,
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