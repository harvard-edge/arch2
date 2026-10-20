import torch
import triton
import triton.language as tl


@triton.jit
def matvec_kernel(
    A_ptr,
    x_ptr,
    C_ptr,
    M,
    K,
    stride_am,
    stride_ak,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    """
    Matrix-vector multiplication kernel: C = A @ x
    Optimized for large K dimension with better memory access patterns.
    """
    pid_m = tl.program_id(0)
    
    row_start = pid_m * BLOCK_SIZE_M
    row_offsets = row_start + tl.arange(0, BLOCK_SIZE_M)
    row_mask = row_offsets < M
    
    # Initialize accumulator in float32 for precision
    acc = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    # Iterate over K dimension with larger blocks for better x reuse
    for k_start in range(0, K, BLOCK_SIZE_K):
        k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offsets < K
        
        # Load x vector elements - these are reused across all rows
        x_vals = tl.load(x_ptr + k_offsets, mask=k_mask, other=0.0)
        
        # Load A matrix elements with coalesced access pattern
        # Each row loads BLOCK_SIZE_K consecutive elements
        a_ptrs = A_ptr + row_offsets[:, None] * stride_am + k_offsets[None, :] * stride_ak
        combined_mask = row_mask[:, None] & k_mask[None, :]
        a_vals = tl.load(a_ptrs, mask=combined_mask, other=0.0)
        
        # Compute partial dot product - broadcast x across rows
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
    
    # Keep BLOCK_SIZE_M at 32 for good parallelism across M
    # Increase BLOCK_SIZE_K to 1024 for better x vector reuse
    # This reduces loop iterations and maximizes data reuse
    BLOCK_SIZE_M = 64
    BLOCK_SIZE_K = 1024
    
    grid = (triton.cdiv(M, BLOCK_SIZE_M),)
    
    # Use num_stages=2 for software pipelining to hide memory latency
    # Use num_warps=8 for more parallelism within each block
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