import torch
import triton
import triton.language as tl


@triton.jit
def max_pool3d_kernel(
    input_ptr,
    output_ptr,
    N, C, D, H, W,  # Input dimensions
    OD, OH, OW,  # Output dimensions
    kernel_size: tl.constexpr,
    stride: tl.constexpr,
    padding: tl.constexpr,
    dilation: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
):
    """
    Fused 3D Max Pooling kernel.
    Each program handles one output element.
    """
    # Get program ID - we flatten all output elements
    pid = tl.program_id(0)
    
    # Total number of output elements
    total_outputs = N * C * OD * OH * OW
    
    # Process BLOCK_SIZE elements per program
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
    
    # Compute input starting positions (with padding offset)
    d_start = od * stride - padding
    h_start = oh * stride - padding
    w_start = ow * stride - padding
    
    # Initialize max value to negative infinity
    max_val = tl.full([BLOCK_SIZE], float('-inf'), dtype=tl.float32)
    
    # Iterate over the pooling window
    for kd in range(kernel_size):
        d_in = d_start + kd * dilation
        d_valid = (d_in >= 0) & (d_in < D)
        
        for kh in range(kernel_size):
            h_in = h_start + kh * dilation
            h_valid = (h_in >= 0) & (h_in < H)
            
            for kw in range(kernel_size):
                w_in = w_start + kw * dilation
                w_valid = (w_in >= 0) & (w_in < W)
                
                # Combined validity check
                valid = mask & d_valid & h_valid & w_valid
                
                # Compute input index: n * (C*D*H*W) + c * (D*H*W) + d_in * (H*W) + h_in * W + w_in
                input_idx = n * (C * D * H * W) + c * (D * H * W) + d_in * (H * W) + h_in * W + w_in
                
                # Load input value
                val = tl.load(input_ptr + input_idx, mask=valid, other=float('-inf'))
                val = val.to(tl.float32)
                
                # Update max
                max_val = tl.maximum(max_val, val)
    
    # Store result
    tl.store(output_ptr + offs, max_val, mask=mask)


def kernel_function(x, kernel_size=2, stride=2, padding=0, dilation=1):
    """
    3D Max Pooling wrapper function.
    
    Args:
        x: Input tensor of shape (N, C, D, H, W)
        kernel_size: Size of the pooling window
        stride: Stride of the pooling window
        padding: Padding added to input
        dilation: Spacing between kernel elements
    
    Returns:
        Output tensor after max pooling
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
    
    # Get input dimensions
    N, C, D, H, W = x.shape
    
    # Calculate output dimensions
    OD = (D + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    OH = (H + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    OW = (W + 2 * padding - dilation * (kernel_size - 1) - 1) // stride + 1
    
    # Allocate output tensor
    output = torch.empty((N, C, OD, OH, OW), device=x.device, dtype=x.dtype)
    
    # Total number of output elements
    total_outputs = N * C * OD * OH * OW
    
    # Launch configuration
    BLOCK_SIZE = 256
    grid = (triton.cdiv(total_outputs, BLOCK_SIZE),)
    
    # Ensure input is contiguous
    x = x.contiguous()
    
    # Launch kernel
    max_pool3d_kernel[grid](
        x,
        output,
        N, C, D, H, W,
        OD, OH, OW,
        kernel_size=kernel_size,
        stride=stride,
        padding=padding,
        dilation=dilation,
        BLOCK_SIZE=BLOCK_SIZE,
    )
    
    return output