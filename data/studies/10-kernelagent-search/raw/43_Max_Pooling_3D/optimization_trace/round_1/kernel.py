import torch
import triton
import triton.language as tl


@triton.jit
def _maxpool3d_kernel_optimized(
    x_ptr,
    y_ptr,
    N, C, D, H, W,
    OD, OH, OW,
    strideN, strideC, strideD, strideH, strideW,
    ostrideN, ostrideC, ostrideD, ostrideH, ostrideW,
    KERNEL_SIZE: tl.constexpr,
    STRIDE: tl.constexpr,
    PADDING: tl.constexpr,
    DILATION: tl.constexpr,
    BLOCK_OW: tl.constexpr,
    BLOCK_OH: tl.constexpr,
):
    # Program IDs
    pid_ow = tl.program_id(axis=0)
    pid_oh = tl.program_id(axis=1)
    pid_z = tl.program_id(axis=2)  # flattened (N * C * OD)

    # Decode pid_z
    od = pid_z % OD
    nc = pid_z // OD
    c = nc % C
    n = nc // C

    # Compute output coordinates
    ow_start = pid_ow * BLOCK_OW
    oh_start = pid_oh * BLOCK_OH

    ow_offsets = ow_start + tl.arange(0, BLOCK_OW)
    oh_offsets = oh_start + tl.arange(0, BLOCK_OH)

    # Create 2D grid
    ow_2d = ow_offsets[None, :]  # [1, BLOCK_OW]
    oh_2d = oh_offsets[:, None]  # [BLOCK_OH, 1]

    ow_mask = ow_2d < OW
    oh_mask = oh_2d < OH
    out_mask = ow_mask & oh_mask  # [BLOCK_OH, BLOCK_OW]

    # Base input coordinates
    d_base = od * STRIDE - PADDING
    h_base = oh_2d * STRIDE - PADDING  # [BLOCK_OH, 1]
    w_base = ow_2d * STRIDE - PADDING  # [1, BLOCK_OW]

    # Accumulator
    acc = tl.full([BLOCK_OH, BLOCK_OW], -float("inf"), dtype=tl.float32)

    # Base offset for (n, c)
    base_nc = n * strideN + c * strideC

    # Iterate over pooling window
    for kd in tl.static_range(0, KERNEL_SIZE):
        d_idx = d_base + kd * DILATION
        valid_d = (d_idx >= 0) & (d_idx < D)
        d_idx_safe = tl.where(valid_d, d_idx, 0)
        base_d = base_nc + d_idx_safe * strideD

        for kh in tl.static_range(0, KERNEL_SIZE):
            h_idx = h_base + kh * DILATION  # [BLOCK_OH, 1]
            valid_h = (h_idx >= 0) & (h_idx < H)
            valid_dh = valid_d & valid_h
            h_idx_safe = tl.where(valid_h, h_idx, 0)
            base_dh = base_d + h_idx_safe * strideH  # [BLOCK_OH, 1]

            for kw in tl.static_range(0, KERNEL_SIZE):
                w_idx = w_base + kw * DILATION  # [1, BLOCK_OW]
                valid_w = (w_idx >= 0) & (w_idx < W)
                valid_dhw = valid_dh & valid_w & out_mask
                w_idx_safe = tl.where(valid_w, w_idx, 0)

                ptrs = x_ptr + base_dh + w_idx_safe * strideW  # [BLOCK_OH, BLOCK_OW]

                vals = tl.load(ptrs, mask=valid_dhw, other=-float("inf"))
                vals_f32 = vals.to(tl.float32)
                acc = tl.maximum(acc, vals_f32)

    # Store results
    out_base = y_ptr + n * ostrideN + c * ostrideC + od * ostrideD
    out_ptrs = out_base + oh_2d * ostrideH + ow_2d * ostrideW
    tl.store(out_ptrs, acc, mask=out_mask)


@triton.jit
def _maxpool3d_kernel_vectorized(
    x_ptr,
    y_ptr,
    N, C, D, H, W,
    OD, OH, OW,
    strideN, strideC, strideD, strideH, strideW,
    ostrideN, ostrideC, ostrideD, ostrideH, ostrideW,
    KERNEL_SIZE: tl.constexpr,
    STRIDE: tl.constexpr,
    PADDING: tl.constexpr,
    DILATION: tl.constexpr,
    BLOCK_C: tl.constexpr,
    BLOCK_OW: tl.constexpr,
):
    # Process multiple channels together for better memory coalescing
    pid_ow = tl.program_id(axis=0)
    pid_c = tl.program_id(axis=1)
    pid_z = tl.program_id(axis=2)  # flattened (N * OD * OH)

    # Decode pid_z
    oh = pid_z % OH
    n_od = pid_z // OH
    od = n_od % OD
    n = n_od // OD

    # Channel and OW offsets
    c_start = pid_c * BLOCK_C
    ow_start = pid_ow * BLOCK_OW

    c_offsets = c_start + tl.arange(0, BLOCK_C)
    ow_offsets = ow_start + tl.arange(0, BLOCK_OW)

    c_2d = c_offsets[:, None]  # [BLOCK_C, 1]
    ow_2d = ow_offsets[None, :]  # [1, BLOCK_OW]

    c_mask = c_2d < C
    ow_mask = ow_2d < OW
    out_mask = c_mask & ow_mask

    # Base coordinates
    d_base = od * STRIDE - PADDING
    h_base = oh * STRIDE - PADDING
    w_base = ow_2d * STRIDE - PADDING  # [1, BLOCK_OW]

    # Accumulator
    acc = tl.full([BLOCK_C, BLOCK_OW], -float("inf"), dtype=tl.float32)

    # Base offset for n
    base_n = n * strideN

    for kd in tl.static_range(0, KERNEL_SIZE):
        d_idx = d_base + kd * DILATION
        valid_d = (d_idx >= 0) & (d_idx < D)
        d_idx_safe = tl.where(valid_d, d_idx, 0)
        base_d = base_n + d_idx_safe * strideD

        for kh in tl.static_range(0, KERNEL_SIZE):
            h_idx = h_base + kh * DILATION
            valid_h = (h_idx >= 0) & (h_idx < H)
            valid_dh = valid_d & valid_h
            h_idx_safe = tl.where(valid_h, h_idx, 0)
            base_dh = base_d + h_idx_safe * strideH

            for kw in tl.static_range(0, KERNEL_SIZE):
                w_idx = w_base + kw * DILATION  # [1, BLOCK_OW]
                valid_w = (w_idx >= 0) & (w_idx < W)
                valid_dhw = valid_dh & valid_w & out_mask
                w_idx_safe = tl.where(valid_w, w_idx, 0)

                # Compute pointers: base_dh + c*strideC + w*strideW
                ptrs = x_ptr + base_dh + c_2d * strideC + w_idx_safe * strideW

                vals = tl.load(ptrs, mask=valid_dhw, other=-float("inf"))
                vals_f32 = vals.to(tl.float32)
                acc = tl.maximum(acc, vals_f32)

    # Store results
    out_base = y_ptr + n * ostrideN + od * ostrideD + oh * ostrideH
    out_ptrs = out_base + c_2d * ostrideC + ow_2d * ostrideW
    tl.store(out_ptrs, acc, mask=out_mask)


def _compute_out_dim(L_in: int, kernel: int, stride: int, padding: int, dilation: int) -> int:
    return (L_in + 2 * padding - dilation * (kernel - 1) - 1) // stride + 1


def kernel_function(x: torch.Tensor, kernel_size: int, stride: int, padding: int, dilation: int):
    if not x.is_cuda:
        raise ValueError("Input must be a CUDA tensor.")
    if x.ndim != 5:
        raise ValueError(f"Expected 5D input (N, C, D, H, W), got shape {tuple(x.shape)}")

    N, C, D, H, W = x.shape
    K = kernel_size
    S = stride
    P = padding
    Di = dilation

    OD = _compute_out_dim(D, K, S, P, Di)
    OH = _compute_out_dim(H, K, S, P, Di)
    OW = _compute_out_dim(W, K, S, P, Di)
    
    if OD <= 0 or OH <= 0 or OW <= 0:
        raise ValueError("Computed non-positive output dimension(s).")

    y = torch.empty((N, C, OD, OH, OW), device=x.device, dtype=x.dtype)

    strideN, strideC, strideD, strideH, strideW = x.stride()
    ostrideN, ostrideC, ostrideD, ostrideH, ostrideW = y.stride()

    # Use vectorized kernel with channel blocking for better memory access patterns
    BLOCK_C = 8
    BLOCK_OW = 32

    def grid(meta):
        return (
            triton.cdiv(OW, meta["BLOCK_OW"]),
            triton.cdiv(C, meta["BLOCK_C"]),
            N * OD * OH
        )

    _maxpool3d_kernel_vectorized[grid](
        x, y,
        N, C, D, H, W,
        OD, OH, OW,
        strideN, strideC, strideD, strideH, strideW,
        ostrideN, ostrideC, ostrideD, ostrideH, ostrideW,
        KERNEL_SIZE=K,
        STRIDE=S,
        PADDING=P,
        DILATION=Di,
        BLOCK_C=BLOCK_C,
        BLOCK_OW=BLOCK_OW,
        num_warps=8,
        num_stages=3,
    )

    return y