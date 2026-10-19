import torch
import triton
import triton.language as tl


@triton.jit
def _dwconv2d_kernel_optimized(
    x_ptr, w_ptr, b_ptr, y_ptr,
    N, C, H, W,
    H_OUT, W_OUT,
    X_STRIDE_N, X_STRIDE_C, X_STRIDE_H, X_STRIDE_W,
    W_STRIDE_C, W_STRIDE_KH, W_STRIDE_KW,
    Y_STRIDE_N, Y_STRIDE_C, Y_STRIDE_H, Y_STRIDE_W,
    STRIDE: tl.constexpr,
    PADDING: tl.constexpr,
    HAS_BIAS: tl.constexpr,
    BLOCK_M: tl.constexpr,  # Number of output rows per block
    BLOCK_N: tl.constexpr,  # Number of output cols per block
):
    """
    Optimized depthwise 2D convolution kernel.
    Focus on register-based computation with minimal overhead.
    """
    # Grid: (num_col_blocks, num_row_blocks, N * C)
    pid_n = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_nc = tl.program_id(2)

    c = pid_nc % C
    n = pid_nc // C

    # Output coordinates
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)  # rows
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)  # cols
    
    # Base pointers
    x_base = x_ptr + n * X_STRIDE_N + c * X_STRIDE_C
    w_base = w_ptr + c * W_STRIDE_C

    # Load all 9 weights into registers (3x3 kernel)
    w00 = tl.load(w_base + 0 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w01 = tl.load(w_base + 0 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w02 = tl.load(w_base + 0 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w10 = tl.load(w_base + 1 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w11 = tl.load(w_base + 1 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w12 = tl.load(w_base + 1 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)
    w20 = tl.load(w_base + 2 * W_STRIDE_KH + 0 * W_STRIDE_KW).to(tl.float32)
    w21 = tl.load(w_base + 2 * W_STRIDE_KH + 1 * W_STRIDE_KW).to(tl.float32)
    w22 = tl.load(w_base + 2 * W_STRIDE_KH + 2 * W_STRIDE_KW).to(tl.float32)

    # Input coordinates (for stride=1, padding=0)
    # Input position = output position (since stride=1, padding=0)
    iy = offs_m * STRIDE - PADDING  # [BLOCK_M]
    ix = offs_n * STRIDE - PADDING  # [BLOCK_N]

    # Accumulator
    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

    # Compute masks once for output bounds
    mask_m = offs_m < H_OUT  # [BLOCK_M]
    mask_n = offs_n < W_OUT  # [BLOCK_N]
    out_mask = mask_m[:, None] & mask_n[None, :]

    # For each kernel position, load input and accumulate
    # Unrolled 3x3 kernel computation
    for kh in tl.static_range(3):
        for kw in tl.static_range(3):
            # Input coordinates for this kernel position
            iy_k = iy + kh  # [BLOCK_M]
            ix_k = ix + kw  # [BLOCK_N]
            
            # Validity masks for input bounds
            valid_y = (iy_k >= 0) & (iy_k < H)  # [BLOCK_M]
            valid_x = (ix_k >= 0) & (ix_k < W)  # [BLOCK_N]
            load_mask = out_mask & valid_y[:, None] & valid_x[None, :]
            
            # Compute input offsets
            x_offs = iy_k[:, None] * X_STRIDE_H + ix_k[None, :] * X_STRIDE_W
            
            # Load input values
            x_vals = tl.load(x_base + x_offs, mask=load_mask, other=0.0).to(tl.float32)
            
            # Get the corresponding weight
            if kh == 0 and kw == 0:
                w = w00
            elif kh == 0 and kw == 1:
                w = w01
            elif kh == 0 and kw == 2:
                w = w02
            elif kh == 1 and kw == 0:
                w = w10
            elif kh == 1 and kw == 1:
                w = w11
            elif kh == 1 and kw == 2:
                w = w12
            elif kh == 2 and kw == 0:
                w = w20
            elif kh == 2 and kw == 1:
                w = w21
            else:
                w = w22
            
            acc += x_vals * w

    # Add bias if present
    if HAS_BIAS:
        b_val = tl.load(b_ptr + c).to(tl.float32)
        acc += b_val

    # Store output
    y_base = y_ptr + n * Y_STRIDE_N + c * Y_STRIDE_C
    y_offs = offs_m[:, None] * Y_STRIDE_H + offs_n[None, :] * Y_STRIDE_W
    tl.store(y_base + y_offs, acc.to(tl.bfloat16), mask=out_mask)


def kernel_function(input, weight, bias=None, stride=1, padding=0):
    assert input.is_cuda and weight.is_cuda
    device = input.device

    stride_val = int(stride) if isinstance(stride, int) else int(stride[0])
    pad_val = int(padding) if isinstance(padding, int) else int(padding[0])

    N, C, H, W = input.shape

    if weight.dim() == 4:
        w3 = weight.view(C, weight.shape[2], weight.shape[3]).contiguous()
    else:
        w3 = weight.contiguous()

    K = w3.shape[1]
    H_out = (H + 2 * pad_val - K) // stride_val + 1
    W_out = (W + 2 * pad_val - K) // stride_val + 1

    y = torch.empty((N, C, H_out, W_out), device=device, dtype=input.dtype)

    XsN, XsC, XsH, XsW = input.stride()
    WsC, WsKH, WsKW = w3.stride()
    YsN, YsC, YsH, YsW = y.stride()

    has_bias = bias is not None

    # Tile sizes optimized for H100
    BLOCK_M = 4   # rows per block
    BLOCK_N = 64  # cols per block (power of 2 for coalescing)

    grid = (
        triton.cdiv(W_out, BLOCK_N),
        triton.cdiv(H_out, BLOCK_M),
        N * C
    )

    _dwconv2d_kernel_optimized[grid](
        input, w3, bias if has_bias else y, y,
        N, C, H, W,
        H_out, W_out,
        XsN, XsC, XsH, XsW,
        WsC, WsKH, WsKW,
        YsN, YsC, YsH, YsW,
        STRIDE=stride_val,
        PADDING=pad_val,
        HAS_BIAS=has_bias,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=3,
    )

    return y