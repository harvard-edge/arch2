import torch
import triton
import triton.language as tl


@triton.jit
def matvec_kernel(
    A_ptr,      # Pointer to matrix A [M, K]
    x_ptr,      # Pointer to vector x [K]
    C_ptr,      # Pointer to output vector C [M]
    M,          # Number of rows in A
    K,          # Number of columns in A (and elements in x)
    stride_am,  # Stride for rows of A
    stride_ak,  # Stride for columns of A
    BLOCK_SIZE_K: tl.constexpr,  # Block size for K dimension
):
    """
    Matrix-vector multiplication kernel: C = A @ x
    Each program handles one row of the output.
    
    Fused operation: single kernel computes full dot product per row.
    """
    pid_m = tl.program_id(0)
    
    if pid_m >= M:
        return
    
    # Initialize scalar accumulator in float32 for precision
    acc = 0.0
    
    # Base pointer for this row
    a_row_ptr = A_ptr + pid_m * stride_am
    
    # Iterate over K dimension in blocks
    num_k_blocks = tl.cdiv(K, BLOCK_SIZE_K)
    for k_block in range(num_k_blocks):
        k_start = k_block * BLOCK_SIZE_K
        k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offsets < K
        
        # Load x vector elements [BLOCK_SIZE_K]
        x_vals = tl.load(x_ptr + k_offsets, mask=k_mask, other=0.0)
        
        # Load A matrix elements for this row [BLOCK_SIZE_K]
        a_vals = tl.load(a_row_ptr + k_offsets * stride_ak, mask=k_mask, other=0.0)
        
        # Compute element-wise product in float32 for precision
        prod = a_vals.to(tl.float32) * x_vals.to(tl.float32)
        
        # Sum the products and add to accumulator
        block_sum = tl.sum(prod, axis=0)
        acc += block_sum
    
    # Store result - acc is now a scalar, cast to output dtype
    tl.store(C_ptr + pid_m, acc.to(tl.bfloat16))


def kernel_function(A: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """
    Wrapper for matrix-vector multiplication: C = A @ x
    
    Args:
        A: Matrix of shape [M, K]
        x: Vector of shape [K] or [K, 1]
    
    Returns:
        C: Result vector of shape [M] or [M, 1] (matching x's shape)
    """
    # Handle x being [K, 1] shape
    x_squeezed = x.squeeze() if x.dim() > 1 else x
    x_contig = x_squeezed.contiguous()
    A_contig = A.contiguous()
    
    M, K = A_contig.shape
    assert x_contig.shape[0] == K, f"Dimension mismatch: A has {K} columns but x has {x_contig.shape[0]} elements"
    
    # Allocate output
    C = torch.empty(M, device=A.device, dtype=A.dtype)
    
    # Choose block size - use power of 2 for efficiency
    BLOCK_SIZE_K = 1024
    
    # Launch one program per row
    grid = (M,)
    
    matvec_kernel[grid](
        A_contig, x_contig, C,
        M, K,
        A_contig.stride(0), A_contig.stride(1),
        BLOCK_SIZE_K=BLOCK_SIZE_K,
    )
    
    # Match output shape to input x shape
    if x.dim() > 1 and x.shape[-1] == 1:
        return C.unsqueeze(-1)
    return C