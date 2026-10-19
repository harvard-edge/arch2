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
    BLOCK_OW: tl.constexpr,
    BLOCK_OH: tl.constexpr,
):
    """
    Optimized 3D Max Pooling kernel with coalesced memory access.
    Each program handles a tile of output elements along OH and OW dimensions.
    """
    # Program IDs for different dimensions
    pid_ow = tl.program_id(0)  # Block along OW
    pid_oh = tl.program_id(1)  # Block along OH
    pid_ncd = tl.program_id(2)  # Combined N, C, OD
    
    # Decompose pid_ncd
    od = pid_ncd % OD
    tmp = pid_ncd // OD
    c = tmp % C
    n = tmp // C
    
    # Output positions for this block
    ow_base = pid_ow * BLOCK_OW
    oh_base = pid_oh * BLOCK_OH
    
    # Create offsets for the tile
    ow_offs = ow_base + tl.arange(0, BLOCK_OW)
    oh_offs = oh_base + tl.arange(0, BLOCK_OH)
    
    # Masks for valid positions
    ow_mask = ow_offs < OW
    oh_mask = oh_offs < OH
    
    # Compute input starting positions
    d_start = od * stride - padding
    h_starts = oh_offs * stride - padding  # [BLOCK_OH]
    w_starts = ow_offs * stride - padding  # [BLOCK_OW]
    
    # Base pointer for this (n, c) slice
    base_ptr = input_ptr + n * stride_n + c * stride_c
    
    # Initialize max values for the tile [BLOCK_OH, BLOCK_OW]
    max_vals = tl.full([BLOCK_OH, BLOCK_OW], float('-inf'), dtype=tl.float32)
    
    # Iterate over the 3D pooling window
    for kd in range(kernel_size):
        d_in = d_start + kd * dilation
        d_valid = (d_in >= 0) & (d_in < D)
        
        if d_valid:
            d_offset = d_in * stride_d
            
            for kh in range(kernel_size):
                # h positions for all OH elements in block [BLOCK_OH]
                h_in = h_starts + kh * dilation
                h_valid = (h_in >= 0) & (h_in < H)  # [BLOCK_OH]
                
                for kw in range(kernel_size):
                    # w positions for all OW elements in block [BLOCK_OW]
                    w_in = w_starts + kw * dilation
                    w_valid = (w_in >= 0) & (w_in < W)  # [BLOCK_OW]
                    
                    # Compute full validity mask [BLOCK_OH, BLOCK_OW]
                    valid_2d = (h_valid[:, None] & w_valid[None, :] & 
                               oh_mask[:, None] & ow_mask[None, :])
                    
                    # Compute input indices [BLOCK_OH, BLOCK_OW]
                    h_offsets = h_in[:, None] * stride_h  # [BLOCK_OH, 1]
                    w_offsets = w_in[None, :] * stride_w  # [1, BLOCK_OW]
                    
                    input_idx = base_ptr + d_offset + h_offsets + w_offsets
                    
                    # Load values with coalesced access along W dimension
                    vals = tl.load(input_idx, mask=valid_2d, other=float('-inf'))
                    vals = vals.to(tl.float32)
                    
                    # Update max
                    max_vals = tl.maximum(max_vals, vals)
    
    # Compute output indices [BLOCK_OH, BLOCK_OW]
    out_base = output_ptr + n * (C * OD * OH * OW) + c * (OD * OH * OW) + od * (OH * OW)
    out_h_offs = oh_offs[:, None] * OW  # [BLOCK_OH, 1]
    out_w_offs = ow_offs[None, :]  # [1, BLOCK_OW]
    out_idx = out_base + out_h_offs + out_w_offs
    
    # Store results with coalesced access
    out_mask = oh_mask[:, None] & ow_mask[None, :]
    tl.store(out_idx, max_vals, mask=out_mask)


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
    
    # Get strides for input tensor
    stride_n = x.stride(0)
    stride_c = x.stride(1)
    stride_d = x.stride(2)
    stride_h = x.stride(3)
    stride_w = x.stride(4)
    
    # Block sizes - optimized for H100
    BLOCK_OW = 32  # Coalesced along W dimension
    BLOCK_OH = 4   # Small block along H for register pressure
    
    # Grid dimensions
    grid = (
        triton.cdiv(OW, BLOCK_OW),
        triton.cdiv(OH, BLOCK_OH),
        N * C * OD,
    )
    
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
        BLOCK_OW=BLOCK_OW,
        BLOCK_OH=BLOCK_OH,
    )
    
    return output