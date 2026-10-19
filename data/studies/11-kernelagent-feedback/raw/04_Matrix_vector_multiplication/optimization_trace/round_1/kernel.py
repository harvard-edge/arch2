import triton
import triton.language as tl
import torch


@triton.jit
def _matvec_kernel(
    a_ptr, b_ptr, c_ptr,
    M, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    # Program id along the M dimension (each program computes a block of rows)
    pid_m = tl.program_id(0)

    # Row indices this program handles
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    # Initialize FP32 accumulator for BLOCK_M rows
    acc = tl.zeros((BLOCK_M,), dtype=tl.float32)

    # Iterate over K dimension in chunks of BLOCK_K
    for k0 in range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)
        k_mask = offs_k < K

        # Load B vector tile [BLOCK_K]
        b_ptrs = b_ptr + offs_k * stride_bk
        b = tl.load(b_ptrs, mask=k_mask, other=0.0).to(tl.float32)

        # Process each row individually to reduce register pressure
        for i in tl.static_range(BLOCK_M):
            row_idx = pid_m * BLOCK_M + i
            if row_idx < M:
                # Load A row tile [BLOCK_K]
                a_ptrs = a_ptr + row_idx * stride_am + offs_k * stride_ak
                a_row = tl.load(a_ptrs, mask=k_mask, other=0.0).to(tl.float32)
                # Accumulate dot product
                acc = tl.where(tl.arange(0, BLOCK_M) == i, 
                              acc + tl.sum(a_row * b), 
                              acc)

    # Convert accumulator to BF16 and store to C[:, 0]
    out = acc.to(tl.bfloat16)
    c_ptrs = c_ptr + offs_m * stride_cm
    tl.store(c_ptrs, out, mask=m_mask)


@triton.jit
def _matvec_kernel_v2(
    a_ptr, b_ptr, c_ptr,
    M, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_K: tl.constexpr,
):
    # Each program computes one output row
    pid_m = tl.program_id(0)
    
    if pid_m >= M:
        return

    # Initialize FP32 accumulator
    acc = tl.zeros((1,), dtype=tl.float32)

    # Iterate over K dimension in chunks of BLOCK_K
    for k0 in range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)
        k_mask = offs_k < K

        # Load A row tile [BLOCK_K]
        a_ptrs = a_ptr + pid_m * stride_am + offs_k * stride_ak
        a_row = tl.load(a_ptrs, mask=k_mask, other=0.0).to(tl.float32)

        # Load B vector tile [BLOCK_K]
        b_ptrs = b_ptr + offs_k * stride_bk
        b = tl.load(b_ptrs, mask=k_mask, other=0.0).to(tl.float32)

        # Accumulate dot product
        acc += tl.sum(a_row * b)

    # Convert accumulator to BF16 and store
    out = acc.to(tl.bfloat16)
    c_ptr_out = c_ptr + pid_m * stride_cm
    tl.store(c_ptr_out, out)


@triton.jit
def _matvec_kernel_v3(
    a_ptr, b_ptr, c_ptr,
    M, K,
    stride_am, stride_ak,
    stride_bk,
    stride_cm,
    BLOCK_K: tl.constexpr,
    NUM_ROWS: tl.constexpr,
):
    # Each program computes NUM_ROWS output rows
    pid = tl.program_id(0)
    
    # Row indices for this program
    row_start = pid * NUM_ROWS
    
    # Initialize accumulators for NUM_ROWS rows
    acc0 = 0.0
    acc1 = 0.0
    acc2 = 0.0
    acc3 = 0.0

    # Iterate over K dimension
    for k0 in range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)
        k_mask = offs_k < K

        # Load B vector tile [BLOCK_K]
        b_ptrs = b_ptr + offs_k * stride_bk
        b = tl.load(b_ptrs, mask=k_mask, other=0.0).to(tl.float32)

        # Load and accumulate for each row
        if row_start + 0 < M:
            a_ptrs0 = a_ptr + (row_start + 0) * stride_am + offs_k * stride_ak
            a0 = tl.load(a_ptrs0, mask=k_mask, other=0.0).to(tl.float32)
            acc0 += tl.sum(a0 * b)
        
        if row_start + 1 < M:
            a_ptrs1 = a_ptr + (row_start + 1) * stride_am + offs_k * stride_ak
            a1 = tl.load(a_ptrs1, mask=k_mask, other=0.0).to(tl.float32)
            acc1 += tl.sum(a1 * b)
        
        if row_start + 2 < M:
            a_ptrs2 = a_ptr + (row_start + 2) * stride_am + offs_k * stride_ak
            a2 = tl.load(a_ptrs2, mask=k_mask, other=0.0).to(tl.float32)
            acc2 += tl.sum(a2 * b)
        
        if row_start + 3 < M:
            a_ptrs3 = a_ptr + (row_start + 3) * stride_am + offs_k * stride_ak
            a3 = tl.load(a_ptrs3, mask=k_mask, other=0.0).to(tl.float32)
            acc3 += tl.sum(a3 * b)

    # Store results
    if row_start + 0 < M:
        tl.store(c_ptr + (row_start + 0) * stride_cm, acc0.to(tl.bfloat16))
    if row_start + 1 < M:
        tl.store(c_ptr + (row_start + 1) * stride_cm, acc1.to(tl.bfloat16))
    if row_start + 2 < M:
        tl.store(c_ptr + (row_start + 2) * stride_cm, acc2.to(tl.bfloat16))
    if row_start + 3 < M:
        tl.store(c_ptr + (row_start + 3) * stride_cm, acc3.to(tl.bfloat16))


def kernel_function(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Compute C = A @ B using a single Triton kernel.
    """
    # Validate device and dtype
    if not A.is_cuda or not B.is_cuda:
        raise ValueError("A and B must be CUDA tensors.")
    if A.dtype != torch.bfloat16 or B.dtype != torch.bfloat16:
        raise ValueError("A and B must be torch.bfloat16 tensors.")

    if A.ndim != 2:
        raise ValueError("A must be 2D [M, K].")
    M, K = A.shape

    # Accept B as [K] or [K, 1]
    if B.ndim == 1:
        if B.shape[0] != K:
            raise ValueError(f"When B is 1D, expected shape [K]={K}, but got {tuple(B.shape)}")
        Bv = B.view(K, 1)
    elif B.ndim == 2:
        if B.shape[0] != K or B.shape[1] != 1:
            raise ValueError(f"B must be [K, 1], got {tuple(B.shape)} (K must match A.shape[1])")
        Bv = B
    else:
        raise ValueError("B must be 1D [K] or 2D [K, 1].")

    # Allocate output C [M, 1]
    C = torch.empty((M, 1), device=A.device, dtype=A.dtype)

    # Extract strides (in elements, not bytes)
    stride_am, stride_ak = A.stride()
    stride_bk, stride_bn = Bv.stride()
    stride_cm, stride_cn = C.stride()

    # Use smaller BLOCK_K to reduce register pressure
    BLOCK_K = 512
    NUM_ROWS = 4

    # Grid: one program per NUM_ROWS rows
    grid = (triton.cdiv(M, NUM_ROWS),)

    _matvec_kernel_v3[grid](
        A, Bv, C,
        M, K,
        stride_am, stride_ak,
        stride_bk,
        stride_cm,
        BLOCK_K=BLOCK_K,
        NUM_ROWS=NUM_ROWS,
        num_warps=4,
        num_stages=4,
    )

    return C