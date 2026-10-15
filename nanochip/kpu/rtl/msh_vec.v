// msh_vec.v -- vector unit: norms, LUT evals, softmax-mix, router top-k,
// elementwise ops, MAC-with-weight, alpha-arg, causal depthwise conv.
//
// Part of msh_chip_top. Every op matches
// rtl/selfmodel/fxmodel.py BIT-EXACTLY; all arithmetic is exact integer and
// every precision-losing shift is round-half-up: (v + 2^(r-1)) >>> r
// (arithmetic), mirroring FxModel._rs_np.
//
// Ops (op_valid/op_ready; op_done pulses at completion; fields code/len/
// src1/src2/dst/wbase/aux):
//   0  V_RMSNORM  rmsnorm(x, W[wbase..]) with PER-OP inv_d24: d = op_len,
//                 inv_d24 = round(2^24/d) = (2^24 + d/2) div d computed by an
//                 internal 25-iteration shift-subtract divider at op start
//                 (exact for all d in 2..2048, verified vs Python round()).
//                 aux[11:0] = src_off, aux[23:12] = dst_off (element offsets
//                 within the src/dst buffers; unaligned offsets handled,
//                 whole-vector ops pass aux = 0). Two passes over x: exact
//                 80-bit sumsq (4 lanes/cycle), then apply (1 elem/cycle,
//                 WBUF-bandwidth limited): rg = (r*(8192+w) + 2^12) >> 13,
//                 y = sat32((rs_np(x,4)*rg + 2^19) >> 20),
//                 r = rsqrt_eval((ss*inv_d24 + 2^43)>>44 + 42950, 40).
//   1  V_L2NORM   same offset scheme; v = (ss + 2^19) >> 20, eps = 4295,
//                 gain = 1 (implemented as rg with w = 0, which is exact).
//   2  V_SIG      elementwise LUTs (sx = 26): idx = clip((x>>>18) + 4096,
//   3  V_ALPHA    0, N), frac = x[17:0], y = t[idx] + ((d[idx]*frac + 2^17)
//   4  V_SILU     >> 18); N = 8192 sig/alpha, 4096 exp. SILU: y =
//                 sat32((x*sig(x) + 2^25) >> 26). 4 lanes/cycle.
//   5  V_MULZ     dst = sat32((src1*src2 + 2^25) >> 26), 4 lanes/cycle.
//   6  V_ADD      dst = sat32(src1 + src2), 4 lanes/cycle.
//   7  V_MACW     dst[i] = sat32(src1[i] + rs(src2[i]*wsel, 26)); wsel =
//                 int32 element aux[3:0] of XBUF buffer aux[8:4], read once
//                 at op start (fxmodel.moe expert accumulation, w Q0.26).
//   8  V_DOT      acc = sum(x[i]*w[i]) int64 -> LOG[aux[1:0]] (idx in
//                 aux[3:0], 4 entries) + dot_val/dot_valid.
//   9  V_SMIX     softmax-mix over ncand = aux[3:0] (2..4) candidates with
//                 EXPLICIT buffer ids aux[8:4]=b0, aux[13:9]=b1,
//                 aux[18:14]=b2, aux[23:19]=b3 and logits in LOG[]:
//                 e_i = exp_lut(clip(rs_np(LOG_i - max, 11), -2^30, 0)),
//                 rec = recip_eval(sum e_i, 46),
//                 y = sat32((rs_np(sum_i cand_i*e_i, 24)*rec + 2^21) >> 22).
//   10 V_TOPK     E = len scores (src1) + bias (WBUF wbase): metric =
//                 score + (bias << 15); k = aux[3:0] strictly-greater
//                 max-scans (lowest-index tie) with used marking; writes k
//                 int32 indices to SRC2 buffer and k renormalized weights
//                 wsel = sat32((s*ROUTER_Q26 + ssum/2) // ssum) (EXACT floor
//                 division) to DST buffer. After op_done, drains the k
//                 selected ids on dot_val/dot_valid (one per cycle,
//                 selection order) holding op_ready low until done
//                 (vc_res channel, SEQ_SPEC A.2/A.5). ROUTER_Q26 =
//                 round(2.828*2^26) = 189783867 (fxmodel.py normative).
//                 Assumes scores >= 0 (sigmoid outputs).
//   11 V_PREALPHA arg[i] = sat32(rs(A[i/dh]*(f[i] + (dtb[i] << 15)), 8)):
//                 A = WBUF[wbase + i/dh] UNSIGNED Q8.8 (zero-extended;
//                 generated A in [128,1024] so sign is moot), dtb =
//                 WBUF[aux[14:0] + i] signed Q4.11, dh = aux[23:16],
//                 f = src1 (fxmodel.kda alpha arg). 2 cycles/element.
//   12 V_CONV     causal depthwise conv K=4 + SiLU with INTERNAL history:
//                 hist RAM 3 layers x 3 streams x 3 vectors x 512 words
//                 (slot-rotating, no copies), cleared at reset; aux[5:2] =
//                 layer, aux[1:0] = stream; win = [h0,h1,h2,x(src1)],
//                 y[j] = sum_t win[t][j]*W[wbase + j*4 + t] (int64),
//                 out = sat32((rs_np(y,16)*sig(y,37) + 2^20) >> 21); then
//                 hist <= [h1, h2, x] (fxmodel.conv).
//   13 V_EXP      elementwise expneg LUT (kept at 13 for completeness).
//
// Memories (external): XBUF 32 x 512 words x 128b shared buffer, two
// 1-cycle read ports + one masked write port; WBUF int16 param buffer,
// one 1-cycle read port. XBUF address = {buf[4:0], word[8:0]} (14 bits).
// op_len is in ELEMENTS; op_len <= 2048, and off + len <= 2048.
// Element tails (len not a multiple of 4) are handled with xw_mask.
//
// ROMs: per-lane sigmoid/alpha/expneg pairs (4 lanes) + scalar
// rsqrt/recip/expneg pairs in the shared evaluator, all loaded from
// rtl/roms/*.hex ($readmemh for memory init; yosys-accepted).
//
// Reset policy (randreset gate): every control flop is reset; the conv
// history RAM is explicitly cleared by a 13824-cycle write loop after
// reset (state S_CLR, op_ready low). The only unreset storage is the
// top-k metric RAM, which is always written before it is read within an
// op, so outputs are deterministic under random initial state (verified
// with +verilator+rand+reset+2).

`default_nettype none

module msh_vec (
    input  wire         clk,
    input  wire         rst_n,
    // op interface
    input  wire         op_valid,
    output wire         op_ready,
    input  wire [4:0]   op_code,
    input  wire [11:0]  op_len,         // element count (<= 2048)
    input  wire [4:0]   op_src1,
    input  wire [4:0]   op_src2,
    input  wire [4:0]   op_dst,
    input  wire [14:0]  op_wbase,       // WBUF base address
    input  wire [31:0]  op_aux,
    output reg          op_done,
    // XBUF read port A (1-cycle latency)
    output reg  [13:0]  xa_addr,        // {buf[4:0], word[8:0]}
    input  wire [127:0] xa_data,
    // XBUF read port B (1-cycle latency)
    output reg  [13:0]  xb_addr,
    input  wire [127:0] xb_data,
    // XBUF write port (lane-masked)
    output reg          xw_we,
    output reg  [13:0]  xw_addr,
    output reg  [127:0] xw_data,
    output reg  [3:0]   xw_mask,
    // WBUF read port (int16 params, 1-cycle latency)
    output reg  [14:0]  w_addr,
    input  wire [15:0]  w_data,
    // second WBUF read port (conv 2-tap pairs; wbuf port b, mirrored)
    output reg  [14:0]  w2_addr,
    input  wire [15:0]  w2_data,
    // V_DOT result / V_TOPK selected-id drain (vc_res channel)
    output reg  [63:0]  dot_val,
    output reg          dot_valid
);

    // ---------------- op codes ----------------
    localparam [4:0] OP_RMSNORM  = 5'd0,
                     OP_L2NORM   = 5'd1,
                     OP_SIG      = 5'd2,
                     OP_ALPHA    = 5'd3,
                     OP_SILU     = 5'd4,
                     OP_MULZ     = 5'd5,
                     OP_ADD      = 5'd6,
                     OP_MACW     = 5'd7,
                     OP_DOT      = 5'd8,
                     OP_SMIX     = 5'd9,
                     OP_TOPK     = 5'd10,
                     OP_PREALPHA = 5'd11,
                     OP_CONV     = 5'd12,
                     OP_EXP      = 5'd13;

    // ---------------- states ----------------
    localparam [4:0] S_CLR    = 5'd0,   // post-reset history-RAM clear
                     S_IDLE   = 5'd1,
                     S_INVD   = 5'd2,   // rmsnorm: inv_d24 divider
                     S_SSQ    = 5'd3,   // norms: sum-of-squares pass
                     S_VAR    = 5'd4,   // norms: variance + eps
                     S_RSQ    = 5'd5,   // norms: rsqrt eval
                     S_NORM2  = 5'd6,   // norms: apply pass
                     S_EW     = 5'd7,   // elementwise stream
                     S_MWLD   = 5'd8,   // macw: wsel preload
                     S_DOT    = 5'd9,
                     S_SM_EA  = 5'd10,  // smix: per-candidate exp argument
                     S_SM_EXP = 5'd11,  // smix: exp LUT
                     S_SM_REC = 5'd12,  // smix: reciprocal
                     S_SM_MAC = 5'd13,  // smix: weighted sum
                     S_SM_FIN = 5'd14,  // smix: finalize word
                     S_TK_MET = 5'd15,  // topk: metric build
                     S_TK_SCN = 5'd16,  // topk: max scan
                     S_TK_MRK = 5'd17,  // topk: mark used / fetch score
                     S_TK_SC2 = 5'd18,  // topk: score capture
                     S_TK_DIV = 5'd19,  // topk: divisions
                     S_TK_WR  = 5'd20,  // topk: write idx/wsel
                     S_TK_DR  = 5'd21,  // topk: id drain on dot_val
                     S_PA     = 5'd22,  // prealpha
                     S_CV_LD  = 5'd23,  // conv: load window words
                     S_CV_RUN = 5'd24,  // conv: MAC + sigmoid pipeline
                     S_CV_FIN = 5'd25,  // conv: word boundary
                     S_CV_DR  = 5'd26,  // conv: drain
                     S_DONE   = 5'd27;

    localparam [31:0] ROUTER_Q26 = 32'd189783867;  // round(2.828*2^26)

    // ---------------- helpers ----------------
    function automatic [31:0] sat32f(input signed [63:0] v);
        if (v > 64'sd2147483647)       sat32f = 32'h7fffffff;
        else if (v < -64'sd2147483648) sat32f = 32'h80000000;
        else                           sat32f = v[31:0];
    endfunction

    // ---------------- registered op fields ----------------
    reg  [4:0]  state;
    reg  [4:0]  oc;
    reg  [11:0] olen;
    reg  [4:0]  osrc1, osrc2, odst;
    reg  [14:0] owbase;
    reg  [31:0] oaux;
    reg  [10:0] nwords_r;
    reg  [23:0] invd24_r;
    reg  [3:0]  ncand_r;
    reg  [3:0]  k_r;
    reg  [11:0] soff_r, doff_r;         // norm element offsets
    reg  [7:0]  dh_r;                   // prealpha dh

    assign op_ready = (state == S_IDLE);

    wire [13:0] acc_nw14 = ({2'b0, op_len} + 14'd3) >> 2;
    wire [10:0] acc_nw   = acc_nw14[10:0];
    wire [3:0]  tail_m   = (olen[1:0] == 2'd1) ? 4'b0001
                         : (olen[1:0] == 2'd2) ? 4'b0011
                         : (olen[1:0] == 2'd3) ? 4'b0111 : 4'b1111;

    // norm offset address computation
    wire [12:0] n2_e13  = {1'b0, soff_r} + {1'b0, cnt};     // src element
    wire [11:0] n2_e    = n2_e13[11:0];
    wire [12:0] dd13    = {1'b0, doff_r} - {1'b0, soff_r};
    wire [11:0] dd_r    = dd13[11:0];
    wire [12:0] ed13    = {1'b0, is_i2} + {1'b0, dd_r};     // dst element
    wire [11:0] ed_c    = ed13[11:0];
    wire [12:0] n2l13   = {1'b0, soff_r} + {1'b0, olen} - 13'd1;
    wire [11:0] n2_last = n2l13[11:0];
    // dst-write lane mask from absolute dst range
    wire [13:0] dw_b   = {2'b0, ed_c[11:2], 2'b00};
    wire [13:0] dw_end = {2'b0, doff_r} + {2'b0, olen};
    wire [3:0]  dw_m   = {((dw_b + 14'd3 >= {2'b0, doff_r}) && (dw_b + 14'd3 < dw_end)),
                          ((dw_b + 14'd2 >= {2'b0, doff_r}) && (dw_b + 14'd2 < dw_end)),
                          ((dw_b + 14'd1 >= {2'b0, doff_r}) && (dw_b + 14'd1 < dw_end)),
                          ((dw_b         >= {2'b0, doff_r}) && (dw_b         < dw_end))};

    // ---------------- shared issue pipeline ----------------
    // Read ports have 1-cycle latency and address outputs are registered,
    // so data addressed at issue cycle c is valid 2 edges later.
    reg  [11:0] cnt;
    reg         is_v1, is_v2;
    reg  [11:0] is_i1, is_i2;
    // shared-LUT service counter (free-running): elementwise captures
    // land at serv==3 and lane k of the captured word is served by the
    // shared ROM set at serv==k (one lookup/cycle; area-driven sharing)
    reg  [1:0]  serv;

    // ============================================================
    // Conv internal history RAM: 27 slots x 512 words x 128b, sync
    // read/write, cleared at reset. Slot = (layer*3 + stream)*3 + phys,
    // phys = (base + logical) mod 3 (pointer rotation, no copies).
    // ============================================================
    reg  [13:0]  h_addr;
    reg          h_we;
    reg  [127:0] h_wdata;
    wire [127:0] h_dout;
    reg  [17:0]  hist_base;
    reg  [13:0]  clr_cnt;

    msh_sram #(.DEPTH(512), .WIDTH(128)) u_hist (
        .clk(clk), .we(h_we),
        .waddr({h_addr[13:9], h_addr[3:0]}),
        .wdata(h_wdata), .wstrb(16'hFFFF),
        .re(1'b1), .raddr({h_addr[13:9], h_addr[3:0]}), .rdata(h_dout));

    wire [7:0] cv_ls8 = ({4'b0, oaux[5:2]} + {3'b0, oaux[5:2], 1'b0})
                      + {6'b0, oaux[1:0]};        // layer*3 + stream
    wire [5:0] cv_ls  = cv_ls8[5:0];
    wire [1:0] cv_bs  = hist_base[2*cv_ls[3:0] +: 2];
    wire [1:0] ph0    = cv_bs;
    wire [1:0] ph1    = (cv_bs == 2'd2) ? 2'd0 : (cv_bs + 2'd1);
    wire [1:0] ph2    = (cv_bs == 2'd0) ? 2'd2 : (cv_bs - 2'd1);
    wire [1:0] cv_nbs = (cv_bs == 2'd2) ? 2'd0 : (cv_bs + 2'd1);
    wire [7:0] ls3    = {cv_ls, 1'b0} + {2'b0, cv_ls};   // (layer*3+stream)*3
    wire [7:0] sl0    = ls3 + {6'b0, ph0};
    wire [7:0] sl1    = ls3 + {6'b0, ph1};
    wire [7:0] sl2    = ls3 + {6'b0, ph2};

    // ============================================================
    // Lane LUT units (4 lanes): sigmoid/alpha/expneg ROM pairs with
    // full-fraction interpolation. Lane 0 is shared with V_CONV (sh=29).
    // Stage 1: ll_val capture. Stage 2: ROM read. Stage 3: interp -> ll_y.
    // ============================================================
    wire [127:0] ll_y_flat;
    wire         ew_cap = (state == S_EW) && is_v2;
    wire [1:0]   ew_tbl = (oc == OP_ALPHA) ? 2'd1
                        : (oc == OP_EXP)   ? 2'd2 : 2'd0;
    // ops that need the shared LUT (throttled to the serv grid); plain
    // arithmetic ops run the ew pipeline at full rate
    wire         ew_lut  = (oc == OP_SIG) || (oc == OP_ALPHA)
                        || (oc == OP_EXP) || (oc == OP_SILU);

    // conv -> lane-0 LUT request (driven by the conv FSM below)
    reg                cv_lut_req;
    reg  signed [63:0] cv_lut_val;

    // Flat buses expose the per-lane stage-1 registers to the
    // shared ROM set (below the generate)
    wire [255:0] lane_val_flat;
    wire [3:0]   lane_sh29_flat;
    wire [7:0]   lane_tbl_flat;

    genvar gl;
    generate
    for (gl = 0; gl < 4; gl = gl + 1) begin : lane
        // stage 1: input value + mode
        reg signed [63:0] ll_val;
        reg               ll_sh29;
        reg  [1:0]        ll_tbl;
        // stage 2: ROM data + fraction (captured when the shared ROM
        // set serves this lane, serv == gl)
        reg  [26:0]       ll_t;
        reg  [19:0]       ll_d;
        reg  [28:0]       ll_frac;
        reg               ll_sh29_r;
        // stage 3: interpolated result
        reg  signed [31:0] ll_y;

        // stage-2 combinational interpolation (per lane, own regs;
        // result fits ±2^19; operands at true widths: 20b x 30b)
        wire signed [49:0] dp    = $signed(ll_d)
                                 * $signed({1'b0, ll_frac});
        wire signed [49:0] dpr   = dp + (ll_sh29_r ? 50'sd268435456
                                                   : 50'sd131072);
        wire signed [49:0] itp   = ll_sh29_r ? (dpr >>> 29) : (dpr >>> 18);
        wire unused_lane = &{1'b1, itp[49:20]};

        always @(posedge clk) begin
            if (!rst_n) begin
                ll_val    <= 64'sd0;
                ll_sh29   <= 1'b0;
                ll_tbl    <= 2'd0;
                ll_t      <= 27'd0;
                ll_d      <= 20'd0;
                ll_frac   <= 29'd0;
                ll_sh29_r <= 1'b0;
                ll_y      <= 32'sd0;
            end else begin
                // stage 1 capture
                if (cv_lut_req && (gl == 0)) begin
                    ll_val  <= cv_lut_val;
                    ll_sh29 <= 1'b1;
                    ll_tbl  <= 2'd0;
                end else if (ew_cap) begin
                    ll_val  <= {{32{xa_data[32*gl+31]}}, xa_data[32*gl +: 32]};
                    ll_sh29 <= 1'b0;
                    ll_tbl  <= ew_tbl;
                end
                // stage 2: capture when served by the shared ROM set
                // (during conv, lane 0 is served EVERY cycle: 1 elem/cyc
                // sigmoid throughput vs 1 elem/4cyc on the serv grid)
                if ((serv == 2'(gl)) || (cv_active && (gl == 0))) begin
                    case (ll_tbl)
                        2'd0: begin
                            ll_t <= shm_sig_t[26:0];
                            ll_d <= shm_sig_d[19:0];
                        end
                        2'd1: begin
                            ll_t <= shm_alp_t[26:0];
                            ll_d <= shm_alp_d[19:0];
                        end
                        default: begin
                            ll_t <= shm_exp_t[26:0];
                            ll_d <= shm_exp_d[19:0];
                        end
                    endcase
                    ll_frac   <= sv_sh29 ? sv_val[28:0]
                                         : {11'b0, sv_val[17:0]};
                    ll_sh29_r <= sv_sh29;
                end
                // stage 3: interpolated output
                ll_y <= $signed({5'b0, ll_t}) + {{12{itp[19]}}, itp[19:0]};
            end
        end

        assign ll_y_flat[32*gl +: 32]    = ll_y;
        assign lane_val_flat[64*gl +: 64] = ll_val;
        assign lane_sh29_flat[gl]        = ll_sh29;
        assign lane_tbl_flat[2*gl +: 2]  = ll_tbl;
    end
    endgenerate

    // ============================================================
    // Shared lane LUT set: ONE sigmoid/alpha/expneg ROM pair
    // time-multiplexed across the 4 lanes by the serv counter (area:
    // 2.62 Mbit of per-lane ROMs -> 0.65 Mbit shared). The LUTs are
    // value endpoints only; the interpolation delta is tab[idx+1] -
    // tab[idx] on the second read port — bit-identical to the former
    // _d tables (init files carry a duplicated final row).
    // ============================================================
    wire signed [63:0] sv_val  = cv_active ? lane_val_flat[63:0]
                                           : lane_val_flat[64*serv +: 64];
    wire               sv_sh29 = cv_active ? lane_sh29_flat[0]
                                           : lane_sh29_flat[serv];
    wire [1:0]         sv_tbl  = cv_active ? lane_tbl_flat[1:0]
                                           : lane_tbl_flat[2*serv +: 2];

    // served lane's combinational index/fraction
    wire signed [63:0] b_c  = sv_sh29 ? (sv_val >>> 29) : (sv_val >>> 18);
    wire signed [63:0] i0_c = b_c + 64'sd4096;
    wire [13:0]        nmax_c = (sv_tbl == 2'd2) ? 14'd4096 : 14'd8192;
    wire signed [63:0] nmax_s = {50'b0, nmax_c};
    wire [13:0]        sv_idx = (i0_c < 64'sd0)  ? 14'd0
                              : (i0_c > nmax_s)  ? nmax_c : i0_c[13:0];
    wire [13:0]        sv_idx_p1 = sv_idx + 14'd1;
    wire [31:0] shm_sig_t, shm_sig_t1, shm_alp_t, shm_alp_t1,
                shm_exp_t, shm_exp_t1;
    msh_rom #(.DEPTH(8194), .WIDTH(32),
              .INIT_FILE("rtl/roms/sigmoid_msh.hex")) u_rom_sig (
        .raddr1(sv_idx),    .rdata1(shm_sig_t),
        .raddr2(sv_idx_p1), .rdata2(shm_sig_t1));
    msh_rom #(.DEPTH(8194), .WIDTH(32),
              .INIT_FILE("rtl/roms/alpha_msh.hex")) u_rom_alp (
        .raddr1(sv_idx),    .rdata1(shm_alp_t),
        .raddr2(sv_idx_p1), .rdata2(shm_alp_t1));
    msh_rom #(.DEPTH(4098), .WIDTH(32),
              .INIT_FILE("rtl/roms/expneg_msh.hex")) u_rom_exp (
        .raddr1(sv_idx[12:0]),    .rdata1(shm_exp_t),
        .raddr2(sv_idx_p1[12:0]), .rdata2(shm_exp_t1));
    wire signed [32:0] shm_sig_d = $signed(shm_sig_t1)
                                 - $signed(shm_sig_t);
    wire signed [32:0] shm_alp_d = $signed(shm_alp_t1)
                                 - $signed(shm_alp_t);
    wire signed [32:0] shm_exp_d = $signed(shm_exp_t1)
                                 - $signed(shm_exp_t);
    wire unused_shm = &{1'b1, shm_sig_d[32:20], shm_alp_d[32:20],
                        shm_exp_d[32:20]};

    // ============================================================
    // Scalar evaluator: norm20 + rsqrt/recip ROMs (for norms and
    // softmax-mix) + scalar expneg ROM (softmax-mix per-candidate exp).
    // Same msh_rom macro pattern as the lane LUTs (value + dup-last-row;
    // delta = t[idx+1]-t[idx]).
    // ============================================================
    wire [11:0] n_idx_p1 = n_idx + 12'd1;
    wire [39:0] scm_rsq_t, scm_rsq_t1;
    wire [23:0] scm_rec_t, scm_rec_t1;
    wire [31:0] scm_sexp_t, scm_sexp_t1;
    msh_rom #(.DEPTH(2050), .WIDTH(40),
              .INIT_FILE("rtl/roms/rsqrt_msh.hex")) u_rom_rsq (
        .raddr1(n_idx),    .rdata1(scm_rsq_t),
        .raddr2(n_idx_p1), .rdata2(scm_rsq_t1));
    msh_rom #(.DEPTH(2050), .WIDTH(24),
              .INIT_FILE("rtl/roms/recip_msh.hex")) u_rom_rec (
        .raddr1(n_idx),    .rdata1(scm_rec_t),
        .raddr2(n_idx_p1), .rdata2(scm_rec_t1));
    wire [12:0] eidx_p1 = eidx_c + 13'd1;
    msh_rom #(.DEPTH(4098), .WIDTH(32),
              .INIT_FILE("rtl/roms/expneg_msh.hex")) u_rom_sexp (
        .raddr1(eidx_c),  .rdata1(scm_sexp_t),
        .raddr2(eidx_p1), .rdata2(scm_sexp_t1));
    wire signed [40:0] scm_rsq_d = $signed(scm_rsq_t1) - $signed(scm_rsq_t);
    wire signed [24:0] scm_rec_d = $signed(scm_rec_t1) - $signed(scm_rec_t);
    wire signed [32:0] scm_sexp_d = $signed(scm_sexp_t1)
                                  - $signed(scm_sexp_t);

    // eval input mux: rsqrt(u) for norms, recip(se) for smix
    reg  [63:0] u_r;
    reg  [28:0] se_r;
    wire [63:0] nu = (state == S_RSQ) ? u_r : {35'b0, se_r};

    // norm20: v = (m_q/512) * 2^E9 with m_q in [2^20, 2^21)
    wire        nb5 = |nu[63:32];
    wire [31:0] nv4 = nb5 ? nu[63:32] : nu[31:0];
    wire        nb4 = |nv4[31:16];
    wire [15:0] nv3 = nb4 ? nv4[31:16] : nv4[15:0];
    wire        nb3 = |nv3[15:8];
    wire [7:0]  nv2 = nb3 ? nv3[15:8] : nv3[7:0];
    wire        nb2 = |nv2[7:4];
    wire [3:0]  nv1 = nb2 ? nv2[7:4] : nv2[3:0];
    wire        nb1 = |nv1[3:2];
    wire [1:0]  nv0 = nb1 ? nv1[3:2] : nv1[1:0];
    wire        nb0 = nv0[1];
    wire [5:0]  n_e = {nb5, nb4, nb3, nb2, nb1, nb0};
    wire signed [8:0]  n_E  = $signed({3'b0, n_e}) - 9'sd20;
    wire [5:0]         n_sl = 6'd20 - n_e;              // -E when E < 0
    wire [63:0]        n_mq64 = n_E[8] ? (nu << n_sl) : (nu >> n_E[5:0]);
    wire [11:0]        n_idx  = n_mq64[20:9] - 12'd2048;
    wire [8:0]         n_frac = n_mq64[8:0];
    wire signed [8:0]  n_E9   = n_E + 9'sd9;

    // scalar eval pipeline registers (shared by rsqrt/recip/exp)
    reg        sc_st;
    reg [32:0] sc_t;
    reg [19:0] sc_d;
    reg [17:0] sc_frac;
    reg signed [8:0] sc_E9;

    // rsqrt/recip finalize (mirrors fxluts.rsqrt_eval_i / recip_eval_i)
    wire signed [24:0] sc_dp  = $signed(sc_d)
                              * $signed({1'b0, sc_frac[8:0]});
    wire signed [25:0] sc_ip  = ($signed({sc_dp[24], sc_dp}) + 26'sd256) >>> 9;
    wire signed [33:0] r0_c   = $signed({1'b0, sc_t})
                              + $signed({{8{sc_ip[25]}}, sc_ip});
    wire signed [63:0] r0x_c  = {{30{r0_c[33]}}, r0_c};
    wire signed [8:0]  E9b_f  = sc_E9[0] ? (sc_E9 + 9'sd1) : sc_E9;
    wire signed [63:0] r1_c   = sc_E9[0]
                              ? (($signed(r0x_c[33:0]) * 20'sd370728
                                  + 64'sd131072) >>> 18)
                              : r0x_c;
    wire signed [6:0]  E9h_c  = E9b_f[7:1];               // E9b >>> 1
    wire signed [6:0]  sh_c   = 7'sd8 - E9h_c;            // sy = 40
    wire [5:0]         nsh_c  = 6'd0 - sh_c[5:0];
    wire [63:0]        rnd_c  = 64'd1 << (nsh_c - 6'd1);
    wire signed [63:0] r_c    = sh_c[6]
                              ? ((r1_c + $signed(rnd_c)) >>> nsh_c)
                              : (r1_c << sh_c[5:0]);
    wire signed [6:0]  sh2_c  = 7'sd16 - sc_E9[6:0];      // sy = 46
    wire [5:0]         nsh2_c = 6'd0 - sh2_c[5:0];
    wire [63:0]        rnd2_c = 64'd1 << (nsh2_c - 6'd1);
    wire signed [63:0] rec_c  = sh2_c[6]
                              ? ((r0x_c + $signed(rnd2_c)) >>> nsh2_c)
                              : (r0x_c << sh2_c[5:0]);

    // exp finalize for smix (sh = 18 path)
    wire signed [37:0] exp_dp = $signed(sc_d)
                              * $signed({1'b0, sc_frac[17:0]});
    wire signed [37:0] exp_y  = $signed({11'b0, sc_t[26:0]})
                              + ((exp_dp + 38'sd131072) >>> 18);
    wire [26:0]        e_c    = exp_y[26:0];

    // exp index from ea_r (clip to [-2^30, 0] already applied)
    reg  signed [31:0] ea_r;
    wire signed [31:0] eb_c   = ea_r >>> 18;
    wire signed [31:0] ei0_c  = eb_c + 32'sd4096;
    wire [12:0]        eidx_c = (ei0_c < 32'sd0)      ? 13'd0
                              : (ei0_c > 32'sd4096)   ? 13'd4096
                              :                         ei0_c[12:0];

    // ============================================================
    // Norm datapath
    // ============================================================
    reg  [79:0] ss_acc;
    reg  signed [63:0] rsq_r;

    // inv_d24 divider: q = (2^24 + d/2) div d, 25 iterations
    reg  [24:0] id_n;
    reg  [11:0] id_d;
    reg  [10:0] id_rem;
    reg  [23:0] id_q;
    reg  [4:0]  id_b;
    // inv_d24 memo: every RMSNORM in a config shares d = op_len (cfg_d),
    // so the exact quotient is computed once and reused (bit-identical;
    // a changed d re-runs the divider)
    reg  [11:0] idm_d;
    reg  [23:0] idm_q;
    wire [12:0] id_trial = {1'b0, id_rem, id_n[id_b]};
    wire        id_ge    = id_trial >= {1'b0, id_d};
    wire [12:0] id_rem_n = id_ge ? (id_trial - {1'b0, id_d}) : id_trial;
    wire [23:0] id_qn    = id_q | (id_ge ? (24'd1 << id_b) : 24'd0);

    // sum-of-squares: 4 squares per word, masked to [soff, soff+len)
    wire [13:0] sq_wl14   = ({2'b0, soff_r} + {2'b0, olen} - 14'd1) >> 2;
    wire [11:0] sq_wlast  = sq_wl14[11:0];
    wire [13:0] sq_b  = {is_i2, 2'b00};               // 4*word
    wire [13:0] sq_e  = {2'b0, soff_r} + {2'b0, olen};
    wire        sq_v0 = (sq_b         >= {2'b0, soff_r}) && (sq_b         < sq_e);
    wire        sq_v1 = (sq_b + 14'd1 >= {2'b0, soff_r}) && (sq_b + 14'd1 < sq_e);
    wire        sq_v2 = (sq_b + 14'd2 >= {2'b0, soff_r}) && (sq_b + 14'd2 < sq_e);
    wire        sq_v3 = (sq_b + 14'd3 >= {2'b0, soff_r}) && (sq_b + 14'd3 < sq_e);
    wire signed [63:0] sq_l0 = {{32{xa_data[31]}},  xa_data[31:0]};
    wire signed [63:0] sq_l1 = {{32{xa_data[63]}},  xa_data[63:32]};
    wire signed [63:0] sq_l2 = {{32{xa_data[95]}},  xa_data[95:64]};
    wire signed [63:0] sq_l3 = {{32{xa_data[127]}}, xa_data[127:96]};
    wire signed [63:0] sq_p0 = sq_l0 * sq_l0;
    wire signed [63:0] sq_p1 = sq_l1 * sq_l1;
    wire signed [63:0] sq_p2 = sq_l2 * sq_l2;
    wire signed [63:0] sq_p3 = sq_l3 * sq_l3;
    wire [65:0] sq_a01 = {2'b0, (sq_v0 ? sq_p0 : 64'sd0)}
                       + {2'b0, (sq_v1 ? sq_p1 : 64'sd0)};
    wire [65:0] sq_a23 = {2'b0, (sq_v2 ? sq_p2 : 64'sd0)}
                       + {2'b0, (sq_v3 ? sq_p3 : 64'sd0)};
    wire [66:0] sq_all = {1'b0, sq_a01} + {1'b0, sq_a23};

    // variance: rmsnorm v = (ss*inv_d24 + 2^43) >> 44; l2norm v = (ss+2^19)>>20
    wire [103:0] var_prod = {24'b0, ss_acc} * {80'b0, invd24_r};
    wire [104:0] var_pr   = {1'b0, var_prod} + 105'd8796093022208;
    wire [60:0]  var_rms  = var_pr[104:44];
    wire [80:0]  var_l2s  = {1'b0, ss_acc} + 81'd524288;
    wire [60:0]  var_l2   = var_l2s[80:20];
    wire [60:0]  var_c    = (oc == OP_L2NORM) ? var_l2 : var_rms;
    wire [63:0]  eps_c    = (oc == OP_L2NORM) ? 64'd4295 : 64'd42950;

    // apply pass: rg = (r*(8192+w) + 2^12) >> 13 (w = 0 for l2norm);
    // y = sat32((rs_np(x,4)*rg + 2^19) >> 20). Lane select by the
    // absolute SRC element index carried in is_i2.
    wire [1:0]  n2_lane = is_i2[1:0];
    wire [31:0] n2_x32  = (n2_lane == 2'd0) ? xa_data[31:0]
                        : (n2_lane == 2'd1) ? xa_data[63:32]
                        : (n2_lane == 2'd2) ? xa_data[95:64]
                        :                     xa_data[127:96];
    wire signed [63:0] n2_x   = {{32{n2_x32[31]}}, n2_x32};
    wire signed [16:0] n2_g   = (oc == OP_L2NORM)
                              ? 17'sd8192
                              : (17'sd8192 + $signed({w_data[15], w_data}));
    wire signed [63:0] n2_g64 = {{47{n2_g[16]}}, n2_g};
    wire signed [63:0] n2_rg  = ($signed(rsq_r[39:0])
                                  * $signed(n2_g64[16:0])
                                  + 64'sd4096) >>> 13;
    wire signed [63:0] n2_xs  = (n2_x + 64'sd8) >>> 4;
    wire signed [63:0] n2_yf  = ($signed(n2_xs[31:0])
                                  * $signed(n2_rg[43:0])
                                  + 64'sd524288) >>> 20;
    wire [31:0]        n2_y   = sat32f(n2_yf);

    // dot: acc += x*w (same issue pipeline / lane select as norms)
    wire signed [63:0] dt_prod = $signed(n2_x[31:0]) * $signed(w_data);
    reg  signed [63:0] acc_r;
    wire signed [63:0] dt_acc  = acc_r + dt_prod;

    // topk metric: score + (bias << 15), 33-bit signed
    wire signed [32:0] tk_sc  = {n2_x32[31], n2_x32};
    wire signed [32:0] tk_bs  = {{2{w_data[15]}}, w_data, 15'b0};
    wire signed [32:0] tk_met = tk_sc + tk_bs;

    // ============================================================
    // Softmax-mix datapath
    // ============================================================
    reg  [255:0] log_r_v;
    reg  [107:0] e_r_v;
    reg  [20:0]        rec_r;
    reg  [255:0] acc_l_v;
    reg  [2:0]         cand_i;

    wire signed [63:0] mx01  = ($signed(log_r_v[64*(0) +: 64]) > $signed(log_r_v[64*(1) +: 64])) ? $signed(log_r_v[64*(0) +: 64]) : $signed(log_r_v[64*(1) +: 64]);
    wire signed [63:0] mx23  = ($signed(log_r_v[64*(2) +: 64]) > $signed(log_r_v[64*(3) +: 64])) ? $signed(log_r_v[64*(2) +: 64]) : $signed(log_r_v[64*(3) +: 64]);
    wire signed [63:0] mx_c  = (ncand_r == 4'd3)
                             ? (($signed(log_r_v[64*(2) +: 64]) > mx01) ? $signed(log_r_v[64*(2) +: 64]) : mx01)
                             : (ncand_r == 4'd4)
                             ? ((mx01 > mx23) ? mx01 : mx23)
                             : mx01;
    wire signed [63:0] ea_d   = $signed(log_r_v[64*(cand_i[1:0]) +: 64]) - mx_c;
    wire signed [63:0] ea_s   = (ea_d + 64'sd1024) >>> 11;
    wire signed [31:0] ea_clip = (ea_s < -64'sd1073741824)
                               ? -32'sd1073741824
                               : ((ea_s > 64'sd0) ? 32'sd0 : ea_s[31:0]);

    // explicit candidate buffer ids from aux fields
    wire [4:0] sm_buf = (cand_i == 3'd0) ? oaux[8:4]
                      : (cand_i == 3'd1) ? oaux[13:9]
                      : (cand_i == 3'd2) ? oaux[18:14] : oaux[23:19];

    wire signed [63:0] mac_e   = {37'b0, e_r_v[27*(is_i2[1:0]) +: 27]};
    wire signed [63:0] mac_l0  = {{32{xa_data[31]}},  xa_data[31:0]};
    wire signed [63:0] mac_l1  = {{32{xa_data[63]}},  xa_data[63:32]};
    wire signed [63:0] mac_l2  = {{32{xa_data[95]}},  xa_data[95:64]};
    wire signed [63:0] mac_l3  = {{32{xa_data[127]}}, xa_data[127:96]};
    wire signed [63:0] mac_p0  = $signed(mac_l0[31:0])
                                 * $signed({1'b0, mac_e[26:0]});
    wire signed [63:0] mac_p1  = $signed(mac_l1[31:0])
                                 * $signed({1'b0, mac_e[26:0]});
    wire signed [63:0] mac_p2  = $signed(mac_l2[31:0])
                                 * $signed({1'b0, mac_e[26:0]});
    wire signed [63:0] mac_p3  = $signed(mac_l3[31:0])
                                 * $signed({1'b0, mac_e[26:0]});

    wire signed [63:0] fin_ys0 = ($signed(acc_l_v[64*(0) +: 64]) + 64'sd8388608) >>> 24;
    wire signed [63:0] fin_ys1 = ($signed(acc_l_v[64*(1) +: 64]) + 64'sd8388608) >>> 24;
    wire signed [63:0] fin_ys2 = ($signed(acc_l_v[64*(2) +: 64]) + 64'sd8388608) >>> 24;
    wire signed [63:0] fin_ys3 = ($signed(acc_l_v[64*(3) +: 64]) + 64'sd8388608) >>> 24;
    wire [31:0] fin_y0 = sat32f(($signed(fin_ys0[39:0])
                                   * $signed({1'b0, rec_r})
                                   + 64'sd2097152) >>> 22);
    wire [31:0] fin_y1 = sat32f(($signed(fin_ys1[39:0])
                                   * $signed({1'b0, rec_r})
                                   + 64'sd2097152) >>> 22);
    wire [31:0] fin_y2 = sat32f(($signed(fin_ys2[39:0])
                                   * $signed({1'b0, rec_r})
                                   + 64'sd2097152) >>> 22);
    wire [31:0] fin_y3 = sat32f(($signed(fin_ys3[39:0])
                                   * $signed({1'b0, rec_r})
                                   + 64'sd2097152) >>> 22);

    // ============================================================
    // Top-k datapath
    // ============================================================
    reg  [263:0] met_ram_v;
    reg  [511:0] order_r_v;
    reg  [511:0] ssel_r_v;
    reg  [511:0] wsel_r_v;
    reg  signed [32:0] best_r;
    reg  [11:0]        best_i;
    reg  [11:0]        scan_i;
    reg  [3:0]         sel_i;
    reg  [31:0]        ssum_r;
    reg                div_run;
    reg  [59:0]        div_d;
    reg  [30:0]        div_rem;
    reg  [59:0]        div_q;
    reg  [5:0]         div_b;

    wire [60:0] dvd_c   = {29'b0, ssel_r_v[32*(sel_i) +: 32]} * {29'b0, ROUTER_Q26}
                        + {30'b0, ssum_r[31:1]};      // + ssum // 2
    wire [31:0] trial_c = {div_rem, div_d[div_b]};
    wire        ge_c    = {1'b0, trial_c} >= {1'b0, ssum_r};
    wire [59:0] q_c     = div_q | (ge_c ? (60'd1 << div_b) : 60'd0);
    wire [31:0] div_rem_n = ge_c ? (trial_c - ssum_r) : trial_c;

    // score readback lane (read issued in S_TK_MRK with best_i)
    wire [1:0]  tk_sl = best_i[1:0];
    wire [31:0] tk_score32 = (tk_sl == 2'd0) ? xa_data[31:0]
                           : (tk_sl == 2'd1) ? xa_data[63:32]
                           : (tk_sl == 2'd2) ? xa_data[95:64]
                           :                   xa_data[127:96];

    wire [9:0]  nw_tk   = ({6'b0, k_r} + 10'd3) >> 2;   // words per side
    wire [11:0] tk_total = {2'b0, nw_tk} << 1;          // both sides
    wire [5:0]  tk_j0   = {1'b0, cnt[3:1], 2'b00};
    wire        tk_side = cnt[0];
    wire [31:0] tk_v0   = ({26'b0, tk_j0} < {28'b0, k_r})
                        ? (tk_side ? wsel_r_v[32*(tk_j0[3:0]) +: 32]
                                   : order_r_v[32*(tk_j0[3:0]) +: 32]) : 32'd0;
    wire [31:0] tk_v1   = ({26'b0, tk_j0} + 32'd1 < {28'b0, k_r})
                        ? (tk_side ? wsel_r_v[32*({2'b0, tk_j0[3:0]} + 6'd1) +: 32]
                                   : order_r_v[32*({2'b0, tk_j0[3:0]} + 6'd1) +: 32]) : 32'd0;
    wire [31:0] tk_v2   = ({26'b0, tk_j0} + 32'd2 < {28'b0, k_r})
                        ? (tk_side ? wsel_r_v[32*({2'b0, tk_j0[3:0]} + 6'd2) +: 32]
                                   : order_r_v[32*({2'b0, tk_j0[3:0]} + 6'd2) +: 32]) : 32'd0;
    wire [31:0] tk_v3   = ({26'b0, tk_j0} + 32'd3 < {28'b0, k_r})
                        ? (tk_side ? wsel_r_v[32*({2'b0, tk_j0[3:0]} + 6'd3) +: 32]
                                   : order_r_v[32*({2'b0, tk_j0[3:0]} + 6'd3) +: 32]) : 32'd0;
    wire        tk_lastw = (cnt[11:1] == {1'b0, nw_tk} - 11'd1);
    wire [3:0]  tk_mask  = (tk_lastw && (k_r[1:0] != 2'd0))
                         ? ((k_r[1:0] == 2'd1) ? 4'b0001
                          : (k_r[1:0] == 2'd2) ? 4'b0011 : 4'b0111)
                         : 4'b1111;

    // ============================================================
    // Elementwise final stage (SIG/ALPHA/EXP/SILU/ADD/MULZ/MACW)
    // ============================================================
    reg  [127:0] ew_x1, ew_x2, ew_x3, ew_x4, ew_x5, ew_x6;
    reg  [127:0] ew_b1, ew_b2, ew_b3, ew_b4, ew_b5, ew_b6;
    reg          ew_v2, ew_v3, ew_v4, ew_v5, ew_v6, ew_v7;
    reg  [11:0]  ew_w3, ew_w4, ew_w5, ew_w6, ew_w7, ew_w8;
    reg  [31:0]  mw_wsel;
    wire [127:0] ew_y_flat;

    genvar gf;
    generate
    for (gf = 0; gf < 4; gf = gf + 1) begin : ewf
        wire signed [63:0] a  = {{32{ew_x6[32*gf+31]}}, ew_x6[32*gf +: 32]};
        wire signed [63:0] b  = {{32{ew_b6[32*gf+31]}}, ew_b6[32*gf +: 32]};
        wire signed [63:0] sg = {37'b0, ll_y_flat[32*gf +: 27]};
        wire signed [63:0] ws = {{32{mw_wsel[31]}}, mw_wsel};
        wire signed [63:0] ps = a * sg;
        wire signed [63:0] pm = a * b;
        wire signed [63:0] pw = b * ws;
        assign ew_y_flat[32*gf +: 32] =
            (oc == OP_SILU) ? sat32f((ps + 64'sd33554432) >>> 26)
          : (oc == OP_ADD)  ? sat32f(a + b)
          : (oc == OP_MULZ) ? sat32f((pm + 64'sd33554432) >>> 26)
          : (oc == OP_MACW) ? sat32f(a + ((pw + 64'sd33554432) >>> 26))
          :                   ll_y_flat[32*gf +: 32];
    end
    endgenerate

    // ============================================================
    // Prealpha datapath (element-serial, 2 WBUF reads per element)
    // ============================================================
    reg         pa_t;                 // 0: dtb+x issue, 1: A issue
    reg         pa_d1, pa_d2, pa_d3;  // pipeline valids
    reg  [11:0] pa_i1, pa_i2, pa_i3;
    reg  [7:0]  pa_h;                 // running head index i/dh
    reg  [11:0] pa_hc;                // running count within head
    reg  [15:0] dtb_r;
    reg  [127:0] fx_r;

    wire [1:0]  pa_lane = pa_i3[1:0];
    wire [31:0] pa_f32  = (pa_lane == 2'd0) ? fx_r[31:0]
                        : (pa_lane == 2'd1) ? fx_r[63:32]
                        : (pa_lane == 2'd2) ? fx_r[95:64]
                        :                     fx_r[127:96];
    wire signed [33:0] pa_fx  = {{2{pa_f32[31]}}, pa_f32};
    wire signed [33:0] pa_dt  = {{18{dtb_r[15]}}, dtb_r} <<< 15;
    wire signed [33:0] pa_sum = pa_fx + pa_dt;
    wire signed [63:0] pa_prod = $signed({{1'b0, w_data}})
                                 * $signed(pa_sum);
    wire [31:0]        pa_arg  = sat32f((pa_prod + 64'sd128) >>> 8);

    // ============================================================
    // Conv datapath
    // ============================================================
    reg  [127:0] win0, win1, win2, win3;
    reg  [1:0]   cv_ld;
    reg          cv_first;
    reg          cv_wait;
    reg  [1:0]   cv_l, cv_t;
    reg  signed [63:0] cv_y, cv_yq;
    // element-sum delay line matching the cv_sv[2] output stage (the
    // push cadence is 2 cycles with 2-tap pairs, faster than the
    // cv_yq->output delay, so the sum must travel with the request)
    reg  signed [63:0] cv_yq1, cv_yq2;
    reg  [2:0]   cv_sv;
    reg  [1:0]   cv_si0, cv_si1, cv_si2;
    reg  [8:0]   cv_wi0, cv_wi1, cv_wi2;
    reg          cv_last0, cv_last1, cv_last2;

    wire        cv_active = (state == S_CV_LD)  || (state == S_CV_RUN)
                         || (state == S_CV_FIN) || (state == S_CV_DR);
    // MAC capture is aligned to the shared 2-cycle read pipeline (is_v2);
    // the element/tap being captured travels in is_i2[3:0].
    wire [1:0]   cap_ml   = is_i2[3:2];
    wire [1:0]   cap_mt   = is_i2[1:0];
    wire [127:0] win_word = (cap_mt == 2'd0) ? win0
                          : (cap_mt == 2'd1) ? win1
                          : (cap_mt == 2'd2) ? win2 : win3;
    wire [31:0]  win_x32  = (cap_ml == 2'd0) ? win_word[31:0]
                          : (cap_ml == 2'd1) ? win_word[63:32]
                          : (cap_ml == 2'd2) ? win_word[95:64]
                          :                    win_word[127:96];
    wire signed [63:0] win_lane = {{32{win_x32[31]}}, win_x32};
    // second tap of the pair (t+1): next window word, same lane
    wire [127:0] win_word2 = (cap_mt == 2'd0) ? win1 : win3;
    wire [31:0]  win2_x32  = (cap_ml == 2'd0) ? win_word2[31:0]
                           : (cap_ml == 2'd1) ? win_word2[63:32]
                           : (cap_ml == 2'd2) ? win_word2[95:64]
                           :                    win_word2[127:96];
    wire signed [63:0] cv_prod  = $signed(win_lane[31:0])
                                * $signed(w_data);
    wire signed [63:0] cv_prod2 = $signed(win2_x32)
                                * $signed(w2_data);
    // 2-tap pairs (cap_mt in {0,2}): both taps of the pair accumulate
    // in the same cycle; the pair starting at tap 0 sets the sum
    wire signed [63:0] cv_yfin  = (cap_mt == 2'd0)
                                ? (cv_prod + cv_prod2)
                                : (cv_y + cv_prod + cv_prod2);
    wire signed [63:0] cv_y1    = (cv_yq2 + 64'sd32768) >>> 16;
    wire [31:0]        cv_out   = sat32f(($signed(cv_y1[47:0])
                                            * $signed({{1'b0, ll_y_flat[26:0]}})
                                          + 64'sd1048576) >>> 21);
    wire [15:0]        cv_wa16  = {1'b0, owbase} + {2'b0, cnt[9:0], 4'b0000}
                                                + {12'b0, cv_l, 2'b00}
                                                + {14'b0, cv_t};
    wire [14:0]        cv_wa    = cv_wa16[14:0];
    wire        cv_push = cv_active && is_v2 && (cap_mt == 2'd2);

    // ============================================================
    // Main FSM
    // ============================================================
    reg [95:0]  yw;
    integer ri;

    always @(posedge clk) begin
        if (!rst_n) begin
            state      <= S_CLR;
            oc         <= 5'd0;
            olen       <= 12'd0;
            osrc1      <= 5'd0;
            osrc2      <= 5'd0;
            odst       <= 5'd0;
            owbase     <= 15'd0;
            oaux       <= 32'd0;
            nwords_r   <= 11'd0;
            invd24_r   <= 24'd0;
            idm_d      <= 12'd0;
            idm_q      <= 24'd0;
            ncand_r    <= 4'd0;
            k_r        <= 4'd0;
            soff_r     <= 12'd0;
            doff_r     <= 12'd0;
            dh_r       <= 8'd0;
            op_done    <= 1'b0;
            cnt        <= 12'd0;
            is_v1      <= 1'b0;
            is_v2      <= 1'b0;
            is_i1      <= 12'd0;
            is_i2      <= 12'd0;
            xa_addr    <= 14'd0;
            xb_addr    <= 14'd0;
            xw_we      <= 1'b0;
            xw_addr    <= 14'd0;
            xw_data    <= 128'd0;
            xw_mask    <= 4'd0;
            w_addr     <= 15'd0;
            w2_addr    <= 15'd0;
            dot_val    <= 64'd0;
            dot_valid  <= 1'b0;
            ss_acc     <= 80'd0;
            u_r        <= 64'd0;
            rsq_r      <= 64'sd0;
            id_n       <= 25'd0;
            id_d       <= 12'd0;
            id_rem     <= 11'd0;
            id_q       <= 24'd0;
            id_b       <= 5'd0;
            sc_st      <= 1'b0;
            sc_t       <= 33'd0;
            sc_d       <= 20'd0;
            sc_frac    <= 18'd0;
            sc_E9      <= 9'sd0;
            acc_r      <= 64'sd0;
            ea_r       <= 32'sd0;
            se_r       <= 29'd0;
            rec_r      <= 21'd0;
            cand_i     <= 3'd0;
            best_r     <= 33'sd0;
            best_i     <= 12'd0;
            scan_i     <= 12'd0;
            sel_i      <= 4'd0;
            ssum_r     <= 32'd0;
            div_run    <= 1'b0;
            div_d      <= 60'd0;
            div_rem    <= 31'd0;
            div_q      <= 60'd0;
            div_b      <= 6'd0;
            yw         <= 96'd0;
            ew_x1      <= 128'd0;
            ew_x2      <= 128'd0;
            ew_x3      <= 128'd0;
            ew_x4      <= 128'd0;
            ew_x5      <= 128'd0;
            ew_x6      <= 128'd0;
            ew_b1      <= 128'd0;
            ew_b2      <= 128'd0;
            ew_b3      <= 128'd0;
            ew_b4      <= 128'd0;
            ew_b5      <= 128'd0;
            ew_b6      <= 128'd0;
            ew_v2      <= 1'b0;
            ew_v3      <= 1'b0;
            ew_v4      <= 1'b0;
            ew_v5      <= 1'b0;
            ew_v6      <= 1'b0;
            ew_v7      <= 1'b0;
            ew_w3      <= 12'd0;
            ew_w4      <= 12'd0;
            ew_w5      <= 12'd0;
            ew_w6      <= 12'd0;
            ew_w7      <= 12'd0;
            ew_w8      <= 12'd0;
            serv       <= 2'd0;
            mw_wsel    <= 32'd0;
            pa_t       <= 1'b0;
            pa_d1      <= 1'b0;
            pa_d2      <= 1'b0;
            pa_d3      <= 1'b0;
            pa_i1      <= 12'd0;
            pa_i2      <= 12'd0;
            pa_i3      <= 12'd0;
            pa_h       <= 8'd0;
            pa_hc      <= 12'd0;
            dtb_r      <= 16'd0;
            fx_r       <= 128'd0;
            win0       <= 128'd0;
            win1       <= 128'd0;
            win2       <= 128'd0;
            win3       <= 128'd0;
            cv_ld      <= 2'd0;
            cv_first   <= 1'b0;
            cv_wait    <= 1'b0;
            cv_l       <= 2'd0;
            cv_t       <= 2'd0;
            cv_y       <= 64'sd0;
            cv_yq      <= 64'sd0;
            cv_yq1     <= 64'sd0;
            cv_yq2     <= 64'sd0;
            cv_lut_req <= 1'b0;
            cv_lut_val <= 64'sd0;
            cv_sv      <= 3'd0;
            cv_si0     <= 2'd0;
            cv_si1     <= 2'd0;
            cv_si2     <= 2'd0;
            cv_wi0     <= 9'd0;
            cv_wi1     <= 9'd0;
            cv_wi2     <= 9'd0;
            cv_last0   <= 1'b0;
            cv_last1   <= 1'b0;
            cv_last2   <= 1'b0;
            hist_base  <= 18'd0;
            clr_cnt    <= 14'd0;
            h_addr     <= 14'd0;
            h_we       <= 1'b0;
            h_wdata    <= 128'd0;
            for (ri = 0; ri < 4; ri = ri + 1) begin
                log_r_v[64*(ri) +: 64] <= 64'sd0;
                e_r_v[27*(ri) +: 27]   <= 27'd0;
                acc_l_v[64*(ri) +: 64] <= 64'sd0;
            end
            for (ri = 0; ri < 16; ri = ri + 1) begin
                order_r_v[32*(ri) +: 32] <= 32'd0;
                ssel_r_v[32*(ri) +: 32]  <= 32'd0;
                wsel_r_v[32*(ri) +: 32]  <= 32'd0;
            end
        end else begin
            // defaults / free-running shifts
            op_done    <= 1'b0;
            dot_valid  <= 1'b0;
            xw_we      <= 1'b0;
            h_we       <= 1'b0;
            cv_lut_req <= 1'b0;
            is_v1      <= 1'b0;
            is_v2      <= is_v1;
            is_i2      <= is_i1;
            serv       <= serv + 2'd1;
            if (cv_active) begin
                cv_sv    <= {cv_sv[1:0], cv_lut_req};
                cv_si1   <= cv_si0;
                cv_si2   <= cv_si1;
                cv_wi1   <= cv_wi0;
                cv_wi2   <= cv_wi1;
                cv_last1 <= cv_last0;
                cv_last2 <= cv_last1;
                cv_yq1   <= cv_yq;
                cv_yq2   <= cv_yq1;
            end
            // conv output stage (runs in every conv state)
            if (cv_active && cv_sv[2]) begin
`ifdef MSH_DEBUG
                $display("[vec] xw si=%0d wi=%0d out=%08x yq=%016x ll_y=%08x last=%0d",
                         cv_si2, cv_wi2, cv_out, cv_yq, ll_y_flat[31:0], cv_last2);
`endif
                case (cv_si2)
                    2'd0: yw[31:0]  <= cv_out;
                    2'd1: yw[63:32] <= cv_out;
                    2'd2: yw[95:64] <= cv_out;
                    default: ;
                endcase
                if (cv_si2 == 2'd3) begin
                    xw_we   <= 1'b1;
                    xw_addr <= {odst, cv_wi2};
                    xw_mask <= (cv_last2 && (olen[1:0] != 2'd0))
                             ? tail_m : 4'b1111;
                    xw_data <= {cv_out, yw[95:0]};
                end
            end

            case (state)
                // ----------------------------------------------------
                S_CLR: begin
                    h_we    <= 1'b1;
                    h_addr  <= {clr_cnt[8:4], 5'b00000, clr_cnt[3:0]};
                    h_wdata <= 128'd0;
                    if (clr_cnt == 14'd511) begin
                        state <= S_IDLE;
                    end else begin
                        clr_cnt <= clr_cnt + 14'd1;
                    end
                end
                // ----------------------------------------------------
                S_IDLE: begin
                    if (op_valid) begin
                        oc       <= op_code;
                        olen     <= op_len;
                        osrc1    <= op_src1;
                        osrc2    <= op_src2;
                        odst     <= op_dst;
                        owbase   <= op_wbase;
                        oaux     <= op_aux;
                        nwords_r <= acc_nw;
                        ncand_r  <= op_aux[3:0];
                        k_r      <= op_aux[3:0];
                        soff_r   <= op_aux[11:0];
                        doff_r   <= op_aux[23:12];
                        dh_r     <= op_aux[23:16];
                        cnt      <= 12'd0;
                        case (op_code)
                            OP_RMSNORM: begin
                                ss_acc <= 80'd0;
                                if (op_len == idm_d) begin
                                    // memoized quotient: skip the divider
                                    invd24_r <= idm_q;
                                    cnt    <= {2'b0, op_aux[11:2]};
                                    state  <= S_SSQ;
                                end else begin
                                    id_n   <= 25'd16777216
                                            + {14'b0, op_len[11:1]};
                                    id_d   <= op_len;
                                    id_rem <= 11'd0;
                                    id_q   <= 24'd0;
                                    id_b   <= 5'd24;
                                    state  <= S_INVD;
                                end
                            end
                            OP_L2NORM: begin
                                ss_acc <= 80'd0;
                                cnt    <= {2'b0, op_aux[11:2]};
                                state  <= S_SSQ;
                            end
                            OP_SIG, OP_ALPHA, OP_EXP,
                            OP_SILU, OP_ADD, OP_MULZ: begin
                                ew_v2 <= 1'b0;
                                ew_v3 <= 1'b0;
                                ew_v4 <= 1'b0;
                                state <= S_EW;
                            end
                            OP_MACW: begin
                                ew_v2 <= 1'b0;
                                ew_v3 <= 1'b0;
                                ew_v4 <= 1'b0;
                                state <= S_MWLD;
                            end
                            OP_DOT: begin
                                acc_r <= 64'sd0;
                                state <= S_DOT;
                            end
                            OP_SMIX: begin
                                cand_i <= 3'd0;
                                se_r   <= 29'd0;
                                state  <= S_SM_EA;
                            end
                            OP_TOPK: begin
                                ssum_r <= 32'd0;
                                state  <= S_TK_MET;
                            end
                            OP_PREALPHA: begin
                                pa_t  <= 1'b0;
                                pa_d1 <= 1'b0;
                                pa_d2 <= 1'b0;
                                pa_d3 <= 1'b0;
                                pa_h  <= 8'd0;
                                pa_hc <= 12'd0;
                                state <= S_PA;
                            end
                            OP_CONV: begin
                                cv_ld <= 2'd0;
                                state <= S_CV_LD;
                            end
                            default: state <= S_DONE;
                        endcase
`ifdef MSH_DEBUG
                        $display("[vec] op %0d len %0d s1 %0d s2 %0d dst %0d",
                                 op_code, op_len, op_src1, op_src2, op_dst);
`endif
                    end
                end
                // ----------------------------------------------------
                S_INVD: begin
                    id_rem <= id_rem_n[10:0];
                    id_q   <= id_qn;
                    if (id_b == 5'd0) begin
                        invd24_r <= id_qn;
                        idm_d    <= id_d;
                        idm_q    <= id_qn;
                        cnt      <= {2'b0, soff_r[11:2]};
                        state    <= S_SSQ;
                    end else begin
                        id_b <= id_b - 5'd1;
                    end
                end
                // ----------------------------------------------------
                S_SSQ: begin
                    if (cnt <= sq_wlast) begin
                        xa_addr <= {osrc1, cnt[8:0]};
                        cnt     <= cnt + 12'd1;
                        is_v1   <= 1'b1;
                        is_i1   <= cnt;
                    end
                    if (is_v2) begin
                        ss_acc <= ss_acc + {13'b0, sq_all};
                        if (is_i2 == sq_wlast) state <= S_VAR;
`ifdef MSH_DEBUG
                        $display("[vec] SSQ i=%0d x=%032x", is_i2, xa_data);
`endif
                    end
                end
                // ----------------------------------------------------
                S_VAR: begin
                    u_r   <= {3'b0, var_c} + eps_c;
                    sc_st <= 1'b0;
                    state <= S_RSQ;
                end
                // ----------------------------------------------------
                S_RSQ: begin
                    if (!sc_st) begin
                        sc_t    <= scm_rsq_t[32:0];
                        sc_d    <= {{4{scm_rsq_d[15]}},
                                    scm_rsq_d[15:0]};
                        sc_frac <= {9'b0, n_frac};
                        sc_E9   <= n_E9;
                        sc_st   <= 1'b1;
                    end else begin
                        rsq_r <= r_c;
                        cnt   <= 12'd0;
                        state <= S_NORM2;
                    end
                end
                // ----------------------------------------------------
                S_NORM2: begin
                    if (cnt < olen) begin
                        if (oc == OP_RMSNORM)
                            w_addr <= owbase + {3'b0, cnt};
                        xa_addr <= {osrc1, n2_e[10:2]};
                        cnt     <= cnt + 12'd1;
                        is_v1   <= 1'b1;
                        is_i1   <= n2_e;
                    end
                    if (is_v2) begin
                        case (ed_c[1:0])
                            2'd0: yw[31:0]  <= n2_y;
                            2'd1: yw[63:32] <= n2_y;
                            2'd2: yw[95:64] <= n2_y;
                            default: ;
                        endcase
`ifdef MSH_DEBUG
                        $display("[vec] N2 i=%0d x=%08x w=%04x rg=%0d y=%08x",
                                 is_i2, n2_x32, w_data, n2_rg, n2_y);
`endif
                        if ((ed_c[1:0] == 2'd3) || (is_i2 == n2_last)) begin
                            xw_we   <= 1'b1;
                            xw_addr <= {odst, ed_c[10:2]};
                            xw_mask <= dw_m;
                            case (ed_c[1:0])
                                2'd0: xw_data <= {96'd0, n2_y};
                                2'd1: xw_data <= {64'd0, n2_y, yw[31:0]};
                                2'd2: xw_data <= {32'd0, n2_y, yw[63:0]};
                                default: xw_data <= {n2_y, yw[95:0]};
                            endcase
                        end
                        if (is_i2 == n2_last) state <= S_DONE;
                    end
                end
                // ----------------------------------------------------
                S_EW: begin
                    // one word per 4 cycles for LUT ops (issue at serv==1
                    // -> capture at serv==3, values valid at serv==0,
                    // lane k served by the shared ROM at serv==k); plain
                    // arithmetic ops (ADD/MULZ/MACW) issue every cycle —
                    // their chain is data-only and ll_y is unused
                    if ((cnt < {1'b0, nwords_r})
                        && ((serv == 2'd1) || !ew_lut)) begin
                        xa_addr <= {osrc1, cnt[8:0]};
                        xb_addr <= {osrc2, cnt[8:0]};
                        cnt     <= cnt + 12'd1;
                        is_v1   <= 1'b1;
                        is_i1   <= cnt;
                    end
                    // pipeline shifts (stage1 capture is in the lane LUTs)
                    ew_v2 <= is_v2;
                    ew_v3 <= ew_v2;
                    ew_v4 <= ew_v3;
                    ew_v5 <= ew_v4;
                    ew_v6 <= ew_v5;
                    ew_v7 <= ew_v6;
                    ew_w3 <= is_i2;
                    ew_w4 <= ew_w3;
                    ew_w5 <= ew_w4;
                    ew_w6 <= ew_w5;
                    ew_w7 <= ew_w6;
                    ew_w8 <= ew_w7;
                    ew_x1 <= xa_data;
                    ew_x2 <= ew_x1;
                    ew_x3 <= ew_x2;
                    ew_x4 <= ew_x3;
                    ew_x5 <= ew_x4;
                    ew_x6 <= ew_x5;
                    ew_b1 <= xb_data;
                    ew_b2 <= ew_b1;
                    ew_b3 <= ew_b2;
                    ew_b4 <= ew_b3;
                    ew_b5 <= ew_b4;
                    ew_b6 <= ew_b5;
                    if (ew_v7) begin
                        xw_we   <= 1'b1;
                        xw_addr <= {odst, ew_w8[8:0]};
                        xw_data <= ew_y_flat;
                        xw_mask <= ((ew_w8 == {1'b0, nwords_r} - 12'd1)
                                    && (olen[1:0] != 2'd0))
                                 ? tail_m : 4'b1111;
                        if (ew_w8 == {1'b0, nwords_r} - 12'd1) state <= S_DONE;
                    end
                end
                // ----------------------------------------------------
                S_MWLD: begin
                    // read wsel = XBUF[aux[8:4]] element aux[3:0], once
                    if (cnt == 12'd0) begin
                        xa_addr <= {oaux[8:4], 7'b0, oaux[3:2]};
                        is_v1   <= 1'b1;
                        is_i1   <= {8'b0, oaux[3:0]};
                        cnt     <= 12'd1;
                    end
                    if (is_v2) begin
                        mw_wsel <= n2_x32;
                        cnt     <= 12'd0;
                        state   <= S_EW;
                    end
                end
                // ----------------------------------------------------
                S_DOT: begin
                    if (cnt < olen) begin
                        w_addr  <= owbase + {3'b0, cnt};
                        xa_addr <= {osrc1, cnt[10:2]};
                        cnt     <= cnt + 12'd1;
                        is_v1   <= 1'b1;
                        is_i1   <= cnt;
                    end
                    if (is_v2) begin
                        acc_r <= dt_acc;
                        if (is_i2 == olen - 12'd1) begin
                            log_r_v[64*(oaux[1:0]) +: 64] <= dt_acc;
                            dot_val          <= dt_acc;
                            dot_valid        <= 1'b1;
                            state            <= S_DONE;
                        end
                    end
                end
                // ----------------------------------------------------
                S_SM_EA: begin
                    ea_r  <= ea_clip;
                    sc_st <= 1'b0;
                    state <= S_SM_EXP;
                end
                // ----------------------------------------------------
                S_SM_EXP: begin
                    if (!sc_st) begin
                        sc_t    <= {6'b0, scm_sexp_t[26:0]};
                        sc_d    <= scm_sexp_d[19:0];
                        sc_frac <= ea_r[17:0];
                        sc_st   <= 1'b1;
                    end else begin
                        e_r_v[27*(cand_i[1:0]) +: 27] <= e_c;
                        se_r             <= se_r + {2'b0, e_c};
                        if (cand_i == ncand_r[2:0] - 3'd1) begin
                            sc_st <= 1'b0;
                            state <= S_SM_REC;
                        end else begin
                            cand_i <= cand_i + 3'd1;
                            state  <= S_SM_EA;
                        end
                    end
                end
                // ----------------------------------------------------
                S_SM_REC: begin
                    if (!sc_st) begin
                        sc_t    <= {13'b0, scm_rec_t[19:0]};
                        sc_d    <= {{4{scm_rec_d[15]}},
                                    scm_rec_d[15:0]};
                        sc_frac <= {9'b0, n_frac};
                        sc_E9   <= n_E9;
                        sc_st   <= 1'b1;
                    end else begin
                        rec_r  <= rec_c[20:0];
                        cnt    <= 12'd0;
                        cand_i <= 3'd0;
                        for (ri = 0; ri < 4; ri = ri + 1)
                            acc_l_v[64*(ri) +: 64] <= 64'sd0;
                        state  <= S_SM_MAC;
                    end
                end
                // ----------------------------------------------------
                S_SM_MAC: begin
                    if (cand_i < ncand_r[2:0]) begin
                        xa_addr <= {sm_buf, cnt[8:0]};
                        is_v1   <= 1'b1;
                        is_i1   <= {9'b0, cand_i};
                        cand_i  <= cand_i + 3'd1;
                    end
                    if (is_v2) begin
                        acc_l_v[64*(0) +: 64] <= acc_l_v[64*(0) +: 64] + mac_p0;
                        acc_l_v[64*(1) +: 64] <= acc_l_v[64*(1) +: 64] + mac_p1;
                        acc_l_v[64*(2) +: 64] <= acc_l_v[64*(2) +: 64] + mac_p2;
                        acc_l_v[64*(3) +: 64] <= acc_l_v[64*(3) +: 64] + mac_p3;
                        if (is_i2[2:0] == ncand_r[2:0] - 3'd1)
                            state <= S_SM_FIN;
                    end
                end
                // ----------------------------------------------------
                S_SM_FIN: begin
                    xw_we   <= 1'b1;
                    xw_addr <= {odst, cnt[8:0]};
                    xw_data <= {fin_y3, fin_y2, fin_y1, fin_y0};
                    xw_mask <= ((cnt == {1'b0, nwords_r} - 12'd1)
                                && (olen[1:0] != 2'd0))
                             ? tail_m : 4'b1111;
                    if (cnt == {1'b0, nwords_r} - 12'd1) begin
                        state <= S_DONE;
                    end else begin
                        cnt    <= cnt + 12'd1;
                        cand_i <= 3'd0;
                        for (ri = 0; ri < 4; ri = ri + 1)
                            acc_l_v[64*(ri) +: 64] <= 64'sd0;
                        state  <= S_SM_MAC;
                    end
                end
                // ----------------------------------------------------
                S_TK_MET: begin
                    if (cnt < olen) begin
                        w_addr  <= owbase + {3'b0, cnt};
                        xa_addr <= {osrc1, cnt[10:2]};
                        cnt     <= cnt + 12'd1;
                        is_v1   <= 1'b1;
                        is_i1   <= cnt;
                    end
                    if (is_v2) begin
                        met_ram_v[33*(is_i2[2:0]) +: 33] <= tk_met;
                        if (is_i2 == olen - 12'd1) begin
                            best_r <= {1'b1, 32'd0};
                            scan_i <= 12'd0;
                            sel_i  <= 4'd0;
                            state  <= S_TK_SCN;
                        end
                    end
                end
                // ----------------------------------------------------
                S_TK_SCN: begin
                    if ($signed(met_ram_v[33*(scan_i[2:0]) +: 33]) > best_r) begin
                        best_r <= $signed(met_ram_v[33*(scan_i[2:0]) +: 33]);
                        best_i <= scan_i;
                    end
                    if (scan_i == olen - 12'd1) begin
                        state <= S_TK_MRK;
                    end else begin
                        scan_i <= scan_i + 12'd1;
                    end
                end
                // ----------------------------------------------------
                S_TK_MRK: begin
                    order_r_v[32*(sel_i[3:0]) +: 32]      <= {20'b0, best_i};
                    met_ram_v[33*(best_i[2:0]) +: 33]    <= {1'b1, 32'd0};
                    xa_addr                  <= {osrc1, best_i[10:2]};
                    is_v1                    <= 1'b1;
                    state                    <= S_TK_SC2;
                end
                // ----------------------------------------------------
                S_TK_SC2: begin
                    if (is_v2) begin
                        ssel_r_v[32*(sel_i[3:0]) +: 32] <= tk_score32;   // scores >= 0
                        ssum_r             <= ssum_r + tk_score32;
                        if (sel_i == k_r - 4'd1) begin
                            sel_i   <= 4'd0;
                            div_run <= 1'b0;
                            state   <= S_TK_DIV;
                        end else begin
                            sel_i  <= sel_i + 4'd1;
                            best_r <= {1'b1, 32'd0};
                            scan_i <= 12'd0;
                            state  <= S_TK_SCN;
                        end
                    end
                end
                // ----------------------------------------------------
                S_TK_DIV: begin
                    if (!div_run) begin
                        if (ssum_r == 32'd0) begin
                            wsel_r_v[32*(sel_i[3:0]) +: 32] <= 32'd0;
                            if (sel_i == k_r - 4'd1) begin
                                cnt   <= 12'd0;
                                state <= S_TK_WR;
                            end else sel_i <= sel_i + 4'd1;
                        end else begin
                            div_d   <= dvd_c[59:0];
                            div_rem <= 31'd0;
                            div_q   <= 60'd0;
                            div_b   <= 6'd59;
                            div_run <= 1'b1;
                        end
                    end else begin
                        div_rem <= div_rem_n[30:0];
                        div_q   <= q_c;
                        if (div_b == 6'd0) begin
                            div_run <= 1'b0;
                            wsel_r_v[32*(sel_i[3:0]) +: 32] <= (|q_c[59:31])
                                                ? 32'h7fffffff
                                                : {1'b0, q_c[30:0]};
                            if (sel_i == k_r - 4'd1) begin
                                cnt   <= 12'd0;
                                state <= S_TK_WR;
                            end else sel_i <= sel_i + 4'd1;
                        end else begin
                            div_b <= div_b - 6'd1;
                        end
                    end
                end
                // ----------------------------------------------------
                S_TK_WR: begin
                    // order ids -> SRC2 buffer; wsel -> DST buffer
                    xw_we   <= 1'b1;
                    xw_addr <= {(tk_side ? odst : osrc2), 5'b0, cnt[4:1]};
                    xw_data <= {tk_v3, tk_v2, tk_v1, tk_v0};
                    xw_mask <= tk_mask;
                    if (cnt == tk_total - 12'd1) begin
                        state <= S_DONE;
                    end else begin
                        cnt <= cnt + 12'd1;
                    end
                end
                // ----------------------------------------------------
                S_TK_DR: begin
                    // drain selected ids on dot_val/dot_valid (vc_res)
                    dot_valid <= 1'b1;
                    dot_val   <= {32'b0, order_r_v[32*(cnt[3:0]) +: 32]};
                    if (cnt == {8'b0, k_r} - 12'd1) begin
                        state <= S_IDLE;
                    end else begin
                        cnt <= cnt + 12'd1;
                    end
                end
                // ----------------------------------------------------
                S_PA: begin
                    pa_d1 <= 1'b0;
                    // issue: 2 cycles per element (dtb+x, then A)
                    if (cnt < olen) begin
                        if (!pa_t) begin
                            w_addr  <= oaux[14:0] + {3'b0, cnt};
                            xa_addr <= {osrc1, cnt[10:2]};
                            pa_t    <= 1'b1;
                            pa_d1   <= 1'b1;
                            pa_i1   <= cnt;
                        end else begin
                            w_addr <= owbase + {7'b0, pa_h};
                            pa_t   <= 1'b0;
                            cnt    <= cnt + 12'd1;
                            if (pa_hc == {4'b0, dh_r} - 12'd1) begin
                                pa_hc <= 12'd0;
                                pa_h  <= pa_h + 8'd1;
                            end else begin
                                pa_hc <= pa_hc + 12'd1;
                            end
                        end
                    end
                    pa_d2 <= pa_d1;
                    pa_d3 <= pa_d2;
                    pa_i2 <= pa_i1;
                    pa_i3 <= pa_i2;
                    if (pa_d2) begin
                        dtb_r <= w_data;
                        fx_r  <= xa_data;
                    end
                    if (pa_d3) begin
                        case (pa_lane)
                            2'd0: yw[31:0]  <= pa_arg;
                            2'd1: yw[63:32] <= pa_arg;
                            2'd2: yw[95:64] <= pa_arg;
                            default: ;
                        endcase
                        if ((pa_lane == 2'd3) || (pa_i3 == olen - 12'd1)) begin
                            xw_we   <= 1'b1;
                            xw_addr <= {odst, pa_i3[10:2]};
                            xw_mask <= ((pa_i3 == olen - 12'd1)
                                        && (olen[1:0] != 2'd0))
                                     ? tail_m : 4'b1111;
                            case (pa_lane)
                                2'd0: xw_data <= {96'd0, pa_arg};
                                2'd1: xw_data <= {64'd0, pa_arg, yw[31:0]};
                                2'd2: xw_data <= {32'd0, pa_arg, yw[63:0]};
                                default: xw_data <= {pa_arg, yw[95:0]};
                            endcase
                        end
                        if (pa_i3 == olen - 12'd1) state <= S_DONE;
                    end
                end
                // ----------------------------------------------------
                S_CV_LD: begin
                    if (cv_ld == 2'd0) begin
                        h_addr <= {sl0[4:0], cnt[8:0]};
                        cv_ld  <= 2'd1;
                    end else if (cv_ld == 2'd1) begin
                        h_addr  <= {sl1[4:0], cnt[8:0]};
                        xa_addr <= {osrc1, cnt[8:0]};
                        cv_ld   <= 2'd2;
                    end else if (cv_ld == 2'd2) begin
                        h_addr <= {sl2[4:0], cnt[8:0]};
                        win0   <= h_dout;
                        cv_ld  <= 2'd3;
                    end else begin
                        win1     <= h_dout;
                        win3     <= xa_data;
                        cv_l     <= 2'd0;
                        cv_t     <= 2'd0;
                        cv_first <= 1'b1;
                        state    <= S_CV_RUN;
                    end
                end
                // ----------------------------------------------------
                S_CV_RUN: begin
                    if (cv_first) begin
                        // One-shot per word: capture win2 (mem[sl2],
                        // valid ONLY this cycle before h_addr moves to
                        // the writeback address) and write current x
                        // into the oldest physical slot (rotation
                        // target). Then hold the MAC loop in cv_wait
                        // until aligned to the shared-LUT service grid
                        // (loop starts at serv==1 -> cv_lut_req at
                        // serv==3, lane-0 value valid+read at serv==0,
                        // ll_y ready for the cv_sv[2] output stage).
                        win2     <= h_dout;
                        h_we     <= 1'b1;
                        h_addr   <= {sl0[4:0], cnt[8:0]};
                        h_wdata  <= win3;
                        cv_first <= 1'b0;
                        if (serv != 2'd0) cv_wait <= 1'b1;
                    end else if (cv_wait) begin
                        if (serv == 2'd0) cv_wait <= 1'b0;
                    end else begin
                        // issue two weight reads per cycle (element
                        // cv_l, tap pair (cv_t, cv_t+1) on ports a/b;
                        // cv_t in {0,2})
                        w_addr  <= cv_wa;
                        w2_addr <= cv_wa + 15'd1;
                        is_v1  <= 1'b1;
                        is_i1  <= {8'b0, cv_l, cv_t};
                        if (cv_t == 2'd2) begin
                            cv_t <= 2'd0;
                            if (cv_l == 2'd3) begin
                                state <= S_CV_FIN;
                            end else begin
                                cv_l <= cv_l + 2'd1;
                            end
                        end else begin
                            cv_t <= cv_t + 2'd2;
                        end
                        // capture aligned to the read pipeline (is_v2)
                        if (is_v2) begin
                            cv_y <= cv_yfin;
                            if (cv_push) begin
                                cv_yq      <= cv_yfin;
                                cv_lut_req <= 1'b1;
                                cv_lut_val <= cv_yfin;
                                cv_si0     <= cap_ml;
                                cv_wi0     <= cnt[8:0];
                                cv_last0   <= (cnt == {1'b0, nwords_r} - 12'd1)
                                              && (cap_ml == 2'd3);
                            end
                        end
                    end
                end
                // ----------------------------------------------------
                S_CV_FIN: begin
                    // drain the final tap of the last element of the word
                    if (is_v2) begin
                        cv_y <= cv_yfin;
                        if (cv_push) begin
                            cv_yq      <= cv_yfin;
                            cv_lut_req <= 1'b1;
                            cv_lut_val <= cv_yfin;
                            cv_si0     <= cap_ml;
                            cv_wi0     <= cnt[8:0];
                            cv_last0   <= (cnt == {1'b0, nwords_r} - 12'd1)
                                          && (cap_ml == 2'd3);
                        end
                    end
                    if (!is_v2) begin
                        if (cnt == {1'b0, nwords_r} - 12'd1) begin
                            state <= S_CV_DR;
                        end else begin
                            cnt   <= cnt + 12'd1;
                            cv_ld <= 2'd0;
                            state <= S_CV_LD;
                        end
                    end
                end
                // ----------------------------------------------------
                S_CV_DR: begin
                    if (cv_sv[2] && cv_last2 && (cv_si2 == 2'd3)) begin
                        hist_base[2*cv_ls[3:0] +: 2] <= cv_nbs;
                        state <= S_DONE;
                    end
                end
                // ----------------------------------------------------
                S_DONE: begin
                    op_done <= 1'b1;
                    if (oc == OP_TOPK) begin
                        cnt   <= 12'd0;
                        state <= S_TK_DR;
                    end else begin
                        state <= S_IDLE;
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end

    // consume intentionally-unused input/computed bits (lint cleanliness)
    // h_addr[8:4]: word-in-slot high bits (nano conv uses 16 of 512
    // words per slot; the clear loop drives these bits to 0). The
    // sliced multiplier operands leave the source wires' upper bits
    // unused (values always fit the used slices).
    wire unused_ok = &{1'b1, op_aux[31:24], oaux[31:24],
                       E9b_f[8], E9b_f[0], sc_E9[8:7], n_E[7:6],
                       n_mq64[63:21], var_pr[43:0], var_l2s[19:0],
                       exp_y[37:27], dvd_c[60], div_rem_n[31],
                       rec_c[63:21], nv0[0], acc_nw14[13:11],
                       sl0[7:5], sl1[7:5], sl2[7:5], dd13[12],
                       n2_e13[12], n2l13[12], ed13[12], id_rem_n[12:11],
                       sq_wl14[13:12], cv_wa16[15], cv_ls8[7:6],
                       h_addr[8:4], rsq_r[63:40], n2_g64[63:17],
                       n2_rg[63:44], n2_xs[63:32], mac_e[63:27],
                       mac_l0[63:32], mac_l1[63:32], mac_l2[63:32],
                       mac_l3[63:32], win_lane[63:32], cv_y1[63:48],
                       fin_ys0[63:40], fin_ys1[63:40], fin_ys2[63:40],
                       fin_ys3[63:40],
                       scm_rsq_d[40:16], scm_rec_d[24:16],
                       scm_sexp_d[32:20]};

`ifdef MSH_DEBUG
    always @(posedge clk) begin
        if (xw_we) $display("[vec] xw a=%04x d=%032x m=%x", xw_addr, xw_data, xw_mask);
        if (state == S_TK_MET && is_v2) $display("[vec] tkmet i=%0d met=%0d", is_i2, tk_met);
        if (state == S_TK_SCN) $display("[vec] tkscn i=%0d best=%0d bi=%0d", scan_i, best_r, best_i);
        if (state == S_TK_MRK) $display("[vec] tkmrk sel=%0d bi=%0d", sel_i, best_i);
        if (state == S_TK_SC2 && is_v2) $display("[vec] tksc2 sel=%0d score=%0d ssum=%0d", sel_i, tk_score32, ssum_r);
        if (state == S_TK_DIV && div_run && (div_b == 6'd0)) $display("[vec] tkdiv sel=%0d q=%08x", sel_i, q_c[30:0]);
        if (state == S_TK_DR) $display("[vec] tkdr id=%0d", dot_val[8:0]);
    end
`endif

endmodule

`default_nettype wire
