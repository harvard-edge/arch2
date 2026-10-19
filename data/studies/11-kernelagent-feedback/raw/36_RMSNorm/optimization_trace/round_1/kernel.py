import torch
import triton
import triton.language as tl


@triton.jit
def _rmsnorm_nchw_kernel_fused(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_nx, stride_cx, stride_hx, stride_wx,
    stride_ny, stride_cy, stride_hy, stride_wy,
    eps,
    BLOCK_W: tl.constexpr,
    BLOCK_C: tl.constexpr,
):
    """
    Single-pass RMSNorm kernel that reads input only once.
    Each thread block processes a tile of [BLOCK_C, BLOCK_W] elements.
    We accumulate partial sums across all C channels in registers,
    then normalize and write output in the same pass.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh - n * H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    # Cast to int64 for address arithmetic
    stride_nx = tl.full([], stride_nx, tl.int64)
    stride_cx = tl.full([], stride_cx, tl.int64)
    stride_hx = tl.full([], stride_hx, tl.int64)
    stride_wx = tl.full([], stride_wx, tl.int64)
    stride_ny = tl.full([], stride_ny, tl.int64)
    stride_cy = tl.full([], stride_cy, tl.int64)
    stride_hy = tl.full([], stride_hy, tl.int64)
    stride_wy = tl.full([], stride_wy, tl.int64)

    n = n.to(tl.int64)
    h = h.to(tl.int64)
    offs_w_i64 = offs_w.to(tl.int64)

    base_nh_x = n * stride_nx + h * stride_hx
    base_nh_y = n * stride_ny + h * stride_hy

    # Accumulator for sum of squares
    acc = tl.zeros([BLOCK_W], dtype=tl.float32)
    
    # First pass: load all channels, compute sum of squares, store in shared memory
    # We'll use a blocked approach to reduce register pressure
    num_c_blocks = tl.cdiv(C, BLOCK_C)
    
    # Allocate storage for channel values - we'll process in blocks
    for c_block in range(num_c_blocks):
        c_start = c_block * BLOCK_C
        offs_c = c_start + tl.arange(0, BLOCK_C)
        mask_c = offs_c < C
        
        # Load block of channels
        for c_idx in range(BLOCK_C):
            c = c_start + c_idx
            if c < C:
                c_i64 = tl.full([], c, tl.int64)
                x_offsets = base_nh_x + c_i64 * stride_cx + offs_w_i64 * stride_wx
                x_vals = tl.load(x_ptr + x_offsets, mask=mask_w, other=0.0)
                x_f32 = x_vals.to(tl.float32)
                acc += x_f32 * x_f32

    # Compute inverse RMS
    c_f32 = tl.full([1], C, dtype=tl.float32)
    mean = acc / c_f32
    inv_rms = tl.math.rsqrt(mean + eps)

    # Second pass: normalize and store
    for c in range(C):
        c_i64 = tl.full([], c, tl.int64)
        x_offsets = base_nh_x + c_i64 * stride_cx + offs_w_i64 * stride_wx
        y_offsets = base_nh_y + c_i64 * stride_cy + offs_w_i64 * stride_wy
        x_vals = tl.load(x_ptr + x_offsets, mask=mask_w, other=0.0)
        x_f32 = x_vals.to(tl.float32)
        y_f32 = x_f32 * inv_rms
        y_vals = y_f32.to(x_vals.dtype)
        tl.store(y_ptr + y_offsets, y_vals, mask=mask_w)


@triton.jit
def _rmsnorm_nchw_kernel_single_pass(
    x_ptr, y_ptr,
    N, C, H, W,
    stride_nx, stride_cx, stride_hx, stride_wx,
    stride_ny, stride_cy, stride_hy, stride_wy,
    eps,
    BLOCK_W: tl.constexpr,
    C_CONST: tl.constexpr,
):
    """
    Single-pass RMSNorm kernel optimized for small C (fits in registers).
    Loads all C channels once, computes sum of squares, normalizes, and stores.
    """
    pid_w = tl.program_id(axis=0)
    pid_nh = tl.program_id(axis=1)

    n = pid_nh // H
    h = pid_nh - n * H

    start_w = pid_w * BLOCK_W
    offs_w = start_w + tl.arange(0, BLOCK_W)
    mask_w = offs_w < W

    # Cast to int64 for address arithmetic
    stride_nx = tl.full([], stride_nx, tl.int64)
    stride_cx = tl.full([], stride_cx, tl.int64)
    stride_hx = tl.full([], stride_hx, tl.int64)
    stride_wx = tl.full([], stride_wx, tl.int64)
    stride_ny = tl.full([], stride_ny, tl.int64)
    stride_cy = tl.full([], stride_cy, tl.int64)
    stride_hy = tl.full([], stride_hy, tl.int64)
    stride_wy = tl.full([], stride_wy, tl.int64)

    n = n.to(tl.int64)
    h = h.to(tl.int64)
    offs_w_i64 = offs_w.to(tl.int64)

    base_nh_x = n * stride_nx + h * stride_hx
    base_nh_y = n * stride_ny + h * stride_hy

    # Load all channels into registers and compute sum of squares
    offs_c = tl.arange(0, C_CONST)
    mask_c = offs_c < C
    
    # Create 2D offset grid [C_CONST, BLOCK_W]
    offs_c_i64 = offs_c.to(tl.int64)
    
    # Compute all offsets at once: [C_CONST, BLOCK_W]
    x_offsets_2d = base_nh_x + offs_c_i64[:, None] * stride_cx + offs_w_i64[None, :] * stride_wx
    mask_2d = mask_c[:, None] & mask_w[None, :]
    
    # Load all values at once
    x_vals_2d = tl.load(x_ptr + x_offsets_2d, mask=mask_2d, other=0.0)
    x_f32_2d = x_vals_2d.to(tl.float32)
    
    # Sum of squares across channels (axis=0)
    sq_2d = x_f32_2d * x_f32_2d
    acc = tl.sum(sq_2d, axis=0)
    
    # Compute inverse RMS
    c_f32 = tl.full([1], C, dtype=tl.float32)
    mean = acc / c_f32
    inv_rms = tl.math.rsqrt(mean + eps)
    
    # Normalize and store
    y_f32_2d = x_f32_2d * inv_rms[None, :]
    y_vals_2d = y_f32_2d.to(x_vals_2d.dtype)
    
    y_offsets_2d = base_nh_y + offs_c_i64[:, None] * stride_cy + offs_w_i64[None, :] * stride_wy
    tl.store(y_ptr + y_offsets_2d, y_vals_2d, mask=mask_2d)


def _parse_kernel_args(x, args, kwargs):
    eps = kwargs.pop("eps", None)
    num_features = kwargs.pop("num_features", None)
    if "features" in kwargs and num_features is None:
        num_features = kwargs.pop("features")
    out = kwargs.pop("out", None)
    if out is None:
        out = kwargs.pop("output", None)
    if out is None:
        out = kwargs.pop("y", None)
    if out is None:
        out = kwargs.pop("dst", None)

    if len(args) == 1:
        a0 = args[0]
        if isinstance(a0, (int,)) and num_features is None:
            num_features = int(a0)
        else:
            if eps is None:
                eps = float(a0)
    elif len(args) == 2:
        a0, a1 = args
        if isinstance(a0, (float,)) or not isinstance(a0, (int,)):
            if eps is None:
                eps = float(a0)
            if num_features is None and isinstance(a1, (int,)):
                num_features = int(a1)
        else:
            if num_features is None:
                num_features = int(a0)
            if eps is None:
                eps = float(a1)

    if eps is None:
        eps = 1e-5
    return eps, num_features, out


def kernel_function(x, *args, **kwargs):
    if not isinstance(x, torch.Tensor):
        raise TypeError("x must be a torch.Tensor")
    if x.device.type != "cuda":
        raise ValueError("x must be on CUDA device")
    if x.ndim != 4:
        raise ValueError(f"Expected 4D NCHW tensor, got shape {tuple(x.shape)}")
    if x.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        raise ValueError(f"Unsupported dtype: {x.dtype}. Use float16, bfloat16, or float32.")

    eps, num_features, out = _parse_kernel_args(x, args, kwargs)

    N, C, H, W = x.shape
    if num_features is not None and int(num_features) != C:
        raise ValueError(f"num_features ({num_features}) does not match input channels ({C}).")

    if out is None:
        y = x
    else:
        if not isinstance(out, torch.Tensor):
            raise TypeError("Provided output must be a torch.Tensor")
        if out.shape != x.shape or out.device != x.device or out.dtype != x.dtype:
            raise ValueError("Output tensor must match input in shape, device, and dtype.")
        y = out

    sx0, sx1, sx2, sx3 = x.stride()
    sy0, sy1, sy2, sy3 = y.stride()

    # For C=64, we can use the single-pass kernel that loads all channels at once
    # This reduces memory traffic by 2x
    if C <= 128:
        # Use power of 2 for C_CONST
        C_CONST = 64 if C <= 64 else 128
        BLOCK_W = 128
        
        grid = (triton.cdiv(W, BLOCK_W), N * H)
        
        _rmsnorm_nchw_kernel_single_pass[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            sy0, sy1, sy2, sy3,
            float(eps),
            BLOCK_W=BLOCK_W,
            C_CONST=C_CONST,
            num_warps=4,
            num_stages=2,
        )
    else:
        # Fall back to two-pass for large C
        BLOCK_W = 256
        BLOCK_C = 64
        grid = (triton.cdiv(W, BLOCK_W), N * H)

        _rmsnorm_nchw_kernel_fused[grid](
            x, y,
            N, C, H, W,
            sx0, sx1, sx2, sx3,
            sy0, sy1, sy2, sy3,
            float(eps),
            BLOCK_W=BLOCK_W,
            BLOCK_C=BLOCK_C,
            num_warps=4,
            num_stages=2,
        )

    return y