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
    Matrix-vector multiplication kernel: C = A @ x
    Each program handles BLOCK_SIZE_M rows of the output.
    """
    pid_m = tl.program_id(0)
    
    row_start = pid_m * BLOCK_SIZE_M
    row_offsets = row_start + tl.arange(0, BLOCK_SIZE_M)
    row_mask = row_offsets < M
    
    # Initialize accumulator
    acc = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    # Iterate over K dimension
    for k_start in range(0, K, BLOCK_SIZE_K):
        k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offsets < K
        
        # Load x vector elements [BLOCK_SIZE_K]
        x_vals = tl.load(x_ptr + k_offsets, mask=k_mask, other=0.0)
        
        # Load A matrix elements [BLOCK_SIZE_M, BLOCK_SIZE_K]
        a_ptrs = A_ptr + row_offsets[:, None] * stride_am + k_offsets[None, :] * stride_ak
        combined_mask = row_mask[:, None] & k_mask[None, :]
        a_vals = tl.load(a_ptrs, mask=combined_mask, other=0.0)
        
        # Compute partial dot product
        acc += tl.sum(a_vals.to(tl.float32) * x_vals.to(tl.float32)[None, :], axis=1)
    
    # Store result
    c_ptrs = C_ptr + row_offsets
    tl.store(c_ptrs, acc.to(tl.bfloat16), mask=row_mask)


def kernel_function(A: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """
    Wrapper for matrix-vector multiplication: C = A @ x
    """
    x_squeezed = x.squeeze() if x.dim() > 1 else x
    
    M, K = A.shape
    assert x_squeezed.shape[0] == K, f"Dimension mismatch: A has {K} columns but x has {x_squeezed.shape[0]} elements"
    
    C = torch.empty(M, device=A.device, dtype=A.dtype)
    
    # Use moderate BLOCK_SIZE_M for parallelism and data reuse
    # Use larger BLOCK_SIZE_K to reduce loop iterations and improve vectorization
    # More warps to hide memory latency on the long K dimension
    BLOCK_SIZE_M = 64
    BLOCK_SIZE_K = 1024
    
    grid = (triton.cdiv(M, BLOCK_SIZE_M),)
    
    # Use num_stages=2 for moderate pipelining
    # Use num_warps=8 to improve memory latency hiding
    matvec_kernel[grid](
        A, x_squeezed, C,
        M, K,
        A.stride(0), A.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        num_stages=2,
        num_warps=8,
    )
    
    if x.dim() > 1 and x.shape[-1] == 1:
        return C.unsqueeze(-1)
    return C