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
    BLOCK_SIZE_M: tl.constexpr,  # Block size for M dimension
    BLOCK_SIZE_K: tl.constexpr,  # Block size for K dimension
):
    """
    Optimized matrix-vector multiplication kernel.
    Computes C = A @ x where A is [M, K] and x is [K].
    
    Uses vectorized loads and larger K blocks for better memory bandwidth.
    """
    # Get the program ID - each program handles BLOCK_SIZE_M rows
    pid_m = tl.program_id(0)
    
    # Compute row indices this program is responsible for
    row_start = pid_m * BLOCK_SIZE_M
    row_offsets = row_start + tl.arange(0, BLOCK_SIZE_M)
    row_mask = row_offsets < M
    
    # Initialize accumulator for the dot product (one per row)
    acc = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    # Iterate over the K dimension in blocks
    for k_start in range(0, K, BLOCK_SIZE_K):
        k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offsets < K
        
        # Load x vector elements for this block [BLOCK_SIZE_K]
        x_vals = tl.load(x_ptr + k_offsets, mask=k_mask, other=0.0)
        
        # Load A matrix elements for this block [BLOCK_SIZE_M, BLOCK_SIZE_K]
        a_ptrs = A_ptr + row_offsets[:, None] * stride_am + k_offsets[None, :] * stride_ak
        combined_mask = row_mask[:, None] & k_mask[None, :]
        a_vals = tl.load(a_ptrs, mask=combined_mask, other=0.0)
        
        # Compute partial dot product and accumulate
        acc += tl.sum(a_vals.to(tl.float32) * x_vals.to(tl.float32)[None, :], axis=1)
    
    # Store the result
    c_ptrs = C_ptr + row_offsets
    tl.store(c_ptrs, acc.to(tl.bfloat16), mask=row_mask)


def kernel_function(A: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """
    Wrapper for matrix-vector multiplication: C = A @ x
    
    Args:
        A: Matrix of shape [M, K]
        x: Vector of shape [K] or [K, 1]
    
    Returns:
        C: Vector of shape [M] or [M, 1] depending on input x shape
    """
    # Handle input shape
    x_squeezed = x.squeeze() if x.dim() > 1 else x
    
    # Get dimensions
    M, K = A.shape
    assert x_squeezed.shape[0] == K, f"Dimension mismatch: A has {K} columns but x has {x_squeezed.shape[0]} elements"
    
    # Allocate output
    C = torch.empty(M, device=A.device, dtype=A.dtype)
    
    # Optimized block sizes:
    # - Keep BLOCK_SIZE_M moderate (64) for good parallelism
    # - Use larger BLOCK_SIZE_K (1024) to improve memory bandwidth and reduce loop overhead
    # - This increases data reuse for the x vector across rows
    BLOCK_SIZE_M = 64
    BLOCK_SIZE_K = 1024
    
    # Calculate grid
    grid = (triton.cdiv(M, BLOCK_SIZE_M),)
    
    # Launch kernel with num_warps=4 for balanced occupancy
    matvec_kernel[grid](
        A, x_squeezed, C,
        M, K,
        A.stride(0), A.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        num_warps=4,
        num_stages=2,
    )
    
    # Match output shape to input x shape
    if x.dim() > 1 and x.shape[-1] == 1:
        return C.unsqueeze(-1)
    return C