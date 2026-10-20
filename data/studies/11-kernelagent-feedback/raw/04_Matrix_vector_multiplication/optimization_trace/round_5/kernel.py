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
    stride_am: tl.constexpr,
    stride_ak: tl.constexpr,
    stride_x: tl.constexpr,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    """
    Matrix-vector multiplication: C = A @ x
    A is [M, K], x is [K] or [K, 1], C is [M] or [M, 1]

    Fused operation: single kernel performs full matvec with reduction over K.
    """
    pid_m = tl.program_id(0)

    # Each program handles BLOCK_SIZE_M rows
    row_start = pid_m * BLOCK_SIZE_M
    row_offsets = row_start + tl.arange(0, BLOCK_SIZE_M)
    row_mask = row_offsets < M

    # Initialize accumulator in float32 for numerical stability
    acc = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)

    # Iterate over K dimension in blocks
    for k_start in range(0, K, BLOCK_SIZE_K):
        k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offsets < K

        # Load x vector elements [BLOCK_SIZE_K]
        # Use stride_x to handle both [K] and [K, 1] cases
        x_vals = tl.load(x_ptr + k_offsets * stride_x, mask=k_mask, other=0.0)

        # Load A matrix block [BLOCK_SIZE_M, BLOCK_SIZE_K]
        a_ptrs = (
            A_ptr + row_offsets[:, None] * stride_am + k_offsets[None, :] * stride_ak
        )
        combined_mask = row_mask[:, None] & k_mask[None, :]
        a_vals = tl.load(a_ptrs, mask=combined_mask, other=0.0)

        # Convert to float32 for accumulation
        a_vals_f32 = a_vals.to(tl.float32)
        x_vals_f32 = x_vals.to(tl.float32)

        # Compute element-wise product and sum over K dimension
        product = a_vals_f32 * x_vals_f32[None, :]
        acc += tl.sum(product, axis=1)

    # Store result - convert back to output dtype
    c_ptrs = C_ptr + row_offsets
    acc_out = acc.to(tl.bfloat16)
    tl.store(c_ptrs, acc_out, mask=row_mask)


def kernel_function(A: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """
    Matrix-vector multiplication: C = A @ x

    Args:
        A: Matrix of shape [M, K]
        x: Vector of shape [K] or [K, 1]

    Returns:
        C: Vector of shape [M] or [M, 1] (matches x's dimensionality)
    """
    M, K = A.shape

    # Determine x's stride along the K dimension
    # For [K, 1] shape, stride(0) gives the stride between elements
    # For [K] shape, stride(0) also gives the stride between elements
    if x.dim() > 1:
        assert x.shape[0] == K, f"Shape mismatch: A is [{M}, {K}], x is {x.shape}"
        stride_x = x.stride(0)
    else:
        assert x.shape[0] == K, f"Shape mismatch: A is [{M}, {K}], x is [{x.shape[0]}]"
        stride_x = x.stride(0)

    # Allocate output with same dtype as input
    C = torch.empty(M, device=A.device, dtype=A.dtype)

    # Block sizes for good performance
    BLOCK_SIZE_M = 64
    BLOCK_SIZE_K = 128

    grid = (triton.cdiv(M, BLOCK_SIZE_M),)

    matvec_kernel[grid](
        A,
        x,
        C,
        M,
        K,
        A.stride(0),
        A.stride(1),
        stride_x,
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        num_warps=4,
        num_stages=2,
    )

    # Return with same shape as input x
    if x.dim() > 1 and x.shape[-1] == 1:
        return C.unsqueeze(-1)
    return C
