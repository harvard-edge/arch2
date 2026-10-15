// msh_seq.v -- top-level sequencer FSM for msh_chip_top.
//
// Drives the whole computation in the C-model's exact order (the Python
// model in rtl/selfmodel/fxmodel.py is the executable golden model of
// this FSM's action stream).
//
// Structure: one flat FSM with nested counters
//   t      token index          (S_TSTART .. S_TNEXT loop)
//   li     layer index          (S_LAY / S_LFIN)
//   st     per-layer stage      (resmix/norm/mixer/moe/add program)
//   mx     mixer op index       (KDA: 0..20, MLA: 0..8)
//   ci/hi/ex_i  candidate / head / routed-expert loops
//   ex     per-op execute sub-FSM (desc reads -> seg pushes -> job -> done)
// v1: engines are fully serialized (issue, wait done, next); only msh_fetch
// runs ahead autonomously. Weight segments are pushed in consumption order
// (s, z, q per tensor) immediately before each GEMV job; a queued-pointer
// discipline is unnecessary because pushes block on seg_ready and each
// GEMV consumes exactly what was pushed for it.
//
// Startup (all from the header, nothing baked in):
//   RUN -> HDR (256 B, 32 config words) -> DESC table -> cache emb/head
//   descriptor addresses -> TOK -> canonical p16 walk into WBUF (records
//   per-layer WBUF offsets + mixer/router/shared/expert descriptor bases)
//   -> head.s/head.z into HS/HZ -> c_att/c_dh by exact integer binary
//   search for round(2^16/sqrt(d)) (see SEQ_SPEC startup step 6).
//
// Byte-stream ownership: bs_owner = 0 during startup loads (the sequencer
// parses the stream into DESC/TOK/WBUF/HS/HZ) and 1 while a GEMV job is
// active (msh_gemv consumes it). The top level muxes bs_ready accordingly.
//
// Writes: per token, the logits row (vocab/4 16B beats read back from the
// LG buffer the head-mode GEMV filled), one argmax beat (4 ids share a
// 16B region, wstrb on the token's lane), then finally the status word
// 0x600DD00D (wstrb 0x000F) and rsp DONE 0x0000D0DE.
//
// Buffer map (XBUF ids, 4-bit — 16-entry XBUF; mirrored by
// seq_emulator.py). Aliases are phase-shared (verified safe):
//   0 x, 1 h1/order, 2 h2, 3 vn/lat/g, 4 q/u, 5 k/expert-out,
//   6 v/kda-o, 7 f1/z, 8 f/alpha/act, 9 beta/wsel,
//   10 core/ctx/moe-acc, 11 a, 12 prefix, 13 rin/scores, 14 blk0, 15 blk1
// Block snapshots are pointer-tracked (no copies): the layer-final V_ADD
// targets 14+blk_idx when the next layer is a boundary; the emb DEQ
// writes buf14 directly. Head-mode GEMV y targets the LG RAM by mode at
// the top level (ybuf value unused, driven as 0).
//
// Reset policy (randreset gate): every flop is reset. On-chip memories are
// written before being read (DESC/TOK/WBUF/HS/HZ loaded at startup, LG
// fully written by the head GEMV before readback), so outputs are
// deterministic under random initial state.
//
// Verilog-2005 subset for Verilator 5.044 + Yosys 0.62. $display only
// under `ifdef MSH_DEBUG.

`default_nettype none

module msh_seq (
    input  wire         clk,
    input  wire         rst_n,
    // command / response streams
    input  wire [31:0]  cmd_data,
    input  wire         cmd_valid,
    output wire         cmd_ready,
    output wire [31:0]  rsp_data,
    output wire         rsp_valid,
    input  wire         rsp_ready,
    // msh_fetch segment queue
    output wire         seg_valid,
    input  wire         seg_ready,
    output wire [35:0]  seg_addr,
    output wire [31:0]  seg_len,
    output wire [3:0]   seg_tag,
    // msh_fetch byte stream (sequencer owns it during startup loads)
    input  wire         bs_valid,
    output wire         bs_ready,
    input  wire [127:0] bs_data,
    input  wire         bs_first,
    input  wire         bs_last,
    input  wire [3:0]   bs_tag,
    input  wire [3:0]   bs_shift,
    input  wire [4:0]   bs_count,
    output reg          bs_owner,       // 0 = seq, 1 = gemv
    // head-q shadow residency (from msh_fetch): once the whole head
    // weight segment is resident, the head job's own q push is skipped
    input  wire         hq_fill_done,
    // rewind the fetch's shadow reader at each head job issue
    output wire         hq_rewind,
    // msh_fetch posted-write channel
    output wire         wr_valid,
    input  wire         wr_ready,
    output wire [35:0]  wr_addr,
    output wire [127:0] wr_data,
    output wire [15:0]  wr_wstrb,
    // msh_gemv job channel
    output wire         gv_valid,
    input  wire         gv_ready,
    output wire [1:0]   gv_mode,        // 0 row, 1 head, 2 deq
    output wire [35:0]  gv_q_addr,
    output wire [15:0]  gv_K,
    output wire [17:0]  gv_N,
    output wire [3:0]   gv_ng,
    output wire [15:0]  gv_gsz,
    output wire [35:0]  gv_s_addr,
    output wire [35:0]  gv_z_addr,
    output wire [7:0]   gv_R,
    output wire [4:0]   gv_xbuf,
    output wire [4:0]   gv_ybuf,
    input  wire         gv_done,
    input  wire [31:0]  gv_am_val,
    input  wire [17:0]  gv_am_idx,
    input  wire         gv_gready,
    input  wire         gv_dready,
    // msh_vec op channel
    output wire         vc_valid,
    input  wire         vc_ready,
    output wire [4:0]   vc_code,
    output wire [11:0]  vc_len,
    output wire [4:0]   vc_src1,
    output wire [4:0]   vc_src2,
    output wire [4:0]   vc_dst,
    output wire [14:0]  vc_wbase,
    output wire [31:0]  vc_aux,
    input  wire         vc_done,
    input  wire         vc_res_valid,   // V_TOPK result beats (expert ids)
    input  wire [31:0]  vc_res_data,
    // msh_kda job channel
    output wire         kd_valid,
    input  wire         kd_ready,
    output wire [2:0]   kd_layer,
    output wire [9:0]   kd_dh,
    output wire [3:0]   kd_H,
    output wire [16:0]  kd_cdh,
    output wire [4:0]   kd_q,
    output wire [4:0]   kd_k,
    output wire [4:0]   kd_v,
    output wire [4:0]   kd_beta,
    output wire [4:0]   kd_alpha,
    output wire [4:0]   kd_o,
    input  wire         kd_done,
    // msh_mla job channel
    output wire         ml_valid,
    input  wire         ml_ready,
    output wire [9:0]   ml_pos,
    output wire [9:0]   ml_dqk,
    output wire [9:0]   ml_dk,
    output wire [9:0]   ml_dv,
    output wire [3:0]   ml_H,
    output wire [16:0]  ml_catt,
    output wire [4:0]   ml_qc,
    output wire [4:0]   ml_qr,
    output wire [4:0]   ml_kc,
    output wire [4:0]   ml_kr,
    output wire [4:0]   ml_v,
    output wire [4:0]   ml_ctx,
    input  wire         ml_done,
    // shared memories (sequencer is the sole writer of these)
    output reg  [14:0]  desc_raddr,
    input  wire [127:0] desc_rdata,
    output wire         desc_we,
    output wire [14:0]  desc_waddr,
    output wire [127:0] desc_wdata,
    output wire [8:0]   tok_raddr,
    input  wire [31:0]  tok_rdata,
    output wire         tok_we,
    output wire [8:0]   tok_waddr,
    output wire [31:0]  tok_wdata,
    output wire         wb_we,
    output wire [14:0]  wb_waddr,
    output wire [15:0]  wb_wdata,
    output wire         hs_we,
    output wire [18:0]  hs_waddr,
    output wire [15:0]  hs_wdata,
    output wire         hz_we,
    output wire [18:0]  hz_waddr,
    output wire [7:0]   hz_wdata,
    // LG logits buffer read port (128b words, 1-cycle read)
    output wire [15:0]  lg_raddr,
    input  wire [127:0] lg_rdata
);

    // ------------------------------------------------------------
    // constants
    // ------------------------------------------------------------
    localparam [31:0] CMD_RUN      = 32'h0000_0001;
    localparam [31:0] RSP_DONE     = 32'h0000_D0DE;
    localparam [31:0] STATUS_MAGIC = 32'h600D_D00D;
    localparam [31:0] HDR_MAGIC    = 32'h4B44_4143;

    // segment tags
    localparam [3:0] TG_HDR = 4'd1, TG_DESC = 4'd2, TG_TOK = 4'd3,
                     TG_WBUF = 4'd4, TG_HS = 4'd5, TG_HZ = 4'd6,
                     TG_GS = 4'd7, TG_GZ = 4'd8, TG_GQ = 4'd9;

    // vec op codes
    localparam [4:0] OP_RMSNORM = 5'd0, OP_L2NORM = 5'd1, OP_SIG = 5'd2,
                     OP_ALPHA = 5'd3, OP_SILU = 5'd4, OP_MULZ = 5'd5,
                     OP_ADD = 5'd6, OP_MACW = 5'd7, OP_DOT = 5'd8,
                     OP_SMIX = 5'd9, OP_TOPK = 5'd10, OP_PREALPHA = 5'd11,
                     OP_CONV = 5'd12;

    // op kinds (execute sub-FSM dispatch)
    localparam [1:0] KD_GEMV = 2'd0, KD_VEC = 2'd1, KD_KDA = 2'd2,
                     KD_MLA = 2'd3;

    // XBUF buffer ids (16-entry XBUF; aliases are phase-shared, see
    // (software-pipeline overlap: pass1 reads while pass2 writes)
    localparam [4:0] B_X = 5'd0, B_H1 = 5'd1, B_H2 = 5'd2, B_LAT = 5'd3,
                     B_Q = 5'd4, B_K = 5'd5, B_V = 5'd6, B_F1 = 5'd7,
                     B_F = 5'd8, B_BETA = 5'd9, B_CORE = 5'd10, B_A = 5'd11,
                     B_PREF = 5'd12, B_RIN = 5'd13, B_B0 = 5'd14,
                     B_ORD = 5'd1, B_WSEL = 5'd9, B_O = 5'd6, B_G = 5'd3,
                     B_U = 5'd4, B_Z = 5'd7, B_EX = 5'd5, B_ACT = 5'd8,
                     B_MOE = 5'd10, B_LG = 5'd0;

    // GEMV modes / output shifts
    localparam [1:0] GM_ROW = 2'd0, GM_HEAD = 2'd1, GM_DEQ = 2'd2;
    localparam [7:0] R_ROW = 8'd12, R_HEAD = 8'd10, R_DEQ = 8'd0;

    // per-layer stages
    localparam [4:0] ST_RATTN = 5'd0, ST_NORM1 = 5'd1, ST_MIX = 5'd2,
                     ST_PADD = 5'd3, ST_RMLP = 5'd4, ST_NORM2 = 5'd5,
                     ST_ROUT = 5'd6, ST_SIGR = 5'd7, ST_TOPK = 5'd8,
                     ST_SHG = 5'd9, ST_SHU = 5'd10, ST_SILU = 5'd11,
                     ST_MULZ = 5'd12, ST_SHD = 5'd13, ST_EXG = 5'd14,
                     ST_EXU = 5'd15, ST_SILUE = 5'd16, ST_MULZE = 5'd17,
                     ST_EXD = 5'd18, ST_MACW = 5'd19, ST_FADD = 5'd20,
                     ST_RMOUT = 5'd21, ST_FNORM = 5'd22, ST_HEAD = 5'd23;

    // top-level states
    localparam [5:0] S_IDLE = 6'd0, S_HDR_PUSH = 6'd1, S_HDR_DRAIN = 6'd2,
                     S_DESC_PUSH = 6'd3, S_DESC_DRAIN = 6'd4, S_CACHE = 6'd5,
                     S_TOK_PUSH = 6'd6, S_TOK_DRAIN = 6'd7, S_WALK = 6'd8,
                     S_HS_PUSH = 6'd9, S_HS_DRAIN = 6'd10,
                     S_HZ_PUSH = 6'd11, S_HZ_DRAIN = 6'd12, S_CATT = 6'd13,
                     S_TSTART = 6'd14, S_EMB_PUSH = 6'd15, S_EMB_JOB = 6'd16,
                     S_EMB_WAIT = 6'd17, S_LAY = 6'd18, S_LFIN = 6'd19,
                     S_LGWR = 6'd20, S_AMWR = 6'd21, S_TNEXT = 6'd22,
                     S_STATUS = 6'd23, S_DONE = 6'd24, S_ERR = 6'd25,
                     S_WCLR = 6'd26;

    // ------------------------------------------------------------
    // small shift-add multiply (dims are runtime values from the
    // header; all products needed are a <= 2^18 times b <= 2^9)
    // ------------------------------------------------------------
    function [35:0] mul9(input [17:0] a, input [8:0] b);
        mul9 = (b[0] ? {18'b0, a}        : 36'd0)
             + (b[1] ? {17'b0, a, 1'b0}  : 36'd0)
             + (b[2] ? {16'b0, a, 2'b0}  : 36'd0)
             + (b[3] ? {15'b0, a, 3'b0}  : 36'd0)
             + (b[4] ? {14'b0, a, 4'b0}  : 36'd0)
             + (b[5] ? {13'b0, a, 5'b0}  : 36'd0)
             + (b[6] ? {12'b0, a, 6'b0}  : 36'd0)
             + (b[7] ? {11'b0, a, 7'b0}  : 36'd0)
             + (b[8] ? {10'b0, a, 8'b0}  : 36'd0);
    endfunction

    // ------------------------------------------------------------
    // configuration registers (parsed from the header)
    // ------------------------------------------------------------
    reg [3:0]  cfg_L;
    reg [15:0] cfg_d;
    reg [3:0]  cfg_nh;
    reg [9:0]  cfg_dk, cfg_dr, cfg_dv, cfg_dc;
    reg [3:0]  cfg_kh;
    reg [9:0]  cfg_dh;
    reg [9:0]  cfg_E;
    reg [3:0]  cfg_tk;
    reg [9:0]  cfg_ff;
    reg [3:0]  cfg_B;
    reg [17:0] cfg_V;
    reg [9:0]  cfg_SL;
    reg [8:0]  cfg_gs;
    reg [7:0]  cfg_lt;
    reg [14:0] cfg_NT;
    reg [35:0] cfg_desc_addr, cfg_tokens_addr, cfg_logits_addr;
    reg [35:0] cfg_argmax_addr, cfg_status_addr;
    reg [31:0] cfg_stride;

    // derived dims (combinational from cfg)
    wire [35:0] mP   = mul9({8'b0, cfg_dh}, {5'b0, cfg_kh});
    wire [35:0] mhdk = mul9({8'b0, cfg_dk}, {5'b0, cfg_nh});
    wire [35:0] mhdr = mul9({8'b0, cfg_dr}, {5'b0, cfg_nh});
    wire [35:0] mhdv = mul9({8'b0, cfg_dv}, {5'b0, cfg_nh});
    wire [35:0] mE9  = mul9({8'b0, cfg_E}, 9'd9);
    wire [17:0] w_P    = mP[17:0];                 // kda_heads * kda_dim
    wire [17:0] w_dqk  = {8'b0, cfg_dk} + {8'b0, cfg_dr};
    wire [17:0] w_hdk  = mhdk[17:0];
    wire [17:0] w_hdr  = mhdr[17:0];
    wire [17:0] w_hdv  = mhdv[17:0];
    wire [15:0] w_d    = cfg_d;
    wire [15:0] w_P16  = w_P[15:0];
    wire [15:0] w_dh16 = {6'b0, cfg_dh};
    wire [15:0] w_dc16 = {6'b0, cfg_dc};
    wire [15:0] w_ff16 = {6'b0, cfg_ff};
    wire [15:0] w_E16  = {6'b0, cfg_E};
    wire [15:0] w_kh16 = {12'b0, cfg_kh};
    wire [15:0] w_dr16 = {6'b0, cfg_dr};

    // emb/head quant geometry
    wire [15:0] w_gsz_d = (cfg_d < {7'b0, cfg_gs}) ? cfg_d : {7'b0, cfg_gs};
    wire [15:0] w_ng_sh = (cfg_gs == 9'd128) ? ((cfg_d + 16'd127) >> 7)
                                             : ((cfg_d + 16'd63) >> 6);
    wire [3:0]  w_ng_e  = (w_gsz_d == cfg_d) ? 4'd1 : w_ng_sh[3:0];
    wire [8:0]  w_d_half = cfg_d[9:1];             // d/2 (d even)

    // ------------------------------------------------------------
    // startup bookkeeping
    // ------------------------------------------------------------
    reg [5:0]  state;
    reg [3:0]  hcnt;            // header beat counter
    reg [14:0] dcnt;            // DESC word counter
    reg [2:0]  cc;              // S_CACHE desc-read counter
    // cached descriptor addresses
    reg [35:0] emb_q_base, emb_s_base, emb_z_base;
    reg [35:0] head_q_addr, head_s_addr, head_z_addr;
    reg [31:0] head_q_len, head_s_len, head_z_len;
    // canonical p16 walk
    reg [4:0]  wst;             // walk stage (0..18)
    reg [2:0]  wli;             // walk layer
    reg [2:0]  ws;              // walk sub-step
    reg [14:0] didx;            // running descriptor index
    reg [14:0] wb_off;          // running WBUF word offset
    reg [35:0] walk_addr;
    reg [31:0] walk_len;
    wire [14:0] walk_words = walk_len[15:1];   // p16: 2 bytes/word
    // per-layer captured offsets / indices
    reg [59:0] wb_rattn_nw_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_rattn_pw_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_norm1_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_knorm_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_qconv_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_kconv_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_vconv_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_A_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_dtb_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_onorm_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_rmlp_nw_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_rmlp_pw_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_norm2_v;   // packed 4x15b (no $mem)
    reg [59:0] wb_bias_v;   // packed 4x15b (no $mem)
    reg [59:0] ix_mixer_v;   // packed 4x15b (no $mem)
    reg [59:0] ix_router_v;   // packed 4x15b (no $mem)
    reg [59:0] ix_shared_v;   // packed 4x15b (no $mem)
    reg [59:0] ix_e0_v;   // packed 4x15b (no $mem)
    reg [14:0] wb_ro_nw, wb_ro_pw, wb_final;
    // c_att / c_dh binary search
    reg        cs;
    reg [4:0]  bs_it;
    reg [17:0] bs_lo, bs_hi;
    reg [16:0] c_att, c_dh;
    wire [19:0] bs_dcur = cs ? {10'b0, cfg_dh} : {2'b0, w_dqk};
    wire [18:0] bs_mid  = ({1'b0, bs_lo} + {1'b0, bs_hi} + 19'd1) >> 1;
    wire [19:0] bs_t    = ({1'b0, bs_mid} << 1) - 20'd1;
    wire [63:0] bs_tt   = {44'b0, bs_t} * {44'b0, bs_t};
    wire [63:0] bs_prod = bs_tt * {44'b0, bs_dcur};

    // ------------------------------------------------------------
    // stream-to-memory staging (startup loads)
    // ------------------------------------------------------------
    reg [127:0] ld_flat;
    reg [4:0]   ld_fill;
    reg         ld_seen_last;
    reg [8:0]   tok_wcnt;
    reg [14:0]  wb_wcnt;
    reg [18:0]  hs_wcnt, hz_wcnt;
    wire [127:0] beat_al = bs_data >> {bs_shift, 3'b000};

    wire in_tok_drain = (state == S_TOK_DRAIN);
    wire in_wb_drain  = (state == S_WALK) && (ws == 3'd4);
    wire in_hs_drain  = (state == S_HS_DRAIN);
    wire in_hz_drain  = (state == S_HZ_DRAIN);
    wire in_ldrain    = in_tok_drain || in_wb_drain || in_hs_drain
                     || in_hz_drain;
    wire ld_emit      = in_ldrain && (ld_fill != 5'd0);
    wire ld_done      = in_ldrain && ld_seen_last && (ld_fill == 5'd0);

    // ------------------------------------------------------------
    // token / layer counters
    // ------------------------------------------------------------
    reg [9:0]  t;
    reg [35:0] lg_row;          // running logits row address
    reg [17:0] tok_val;
    reg [2:0]  li;
    reg [3:0]  blk_idx;         // blocks appended so far
    reg [3:0]  blkcnt;          // layers since last boundary
    reg [4:0]  st, mx;
    reg [1:0]  rs2;             // resmix sub-step
    reg [3:0]  ci;              // resmix candidate index
    reg [3:0]  hi;              // head index
    reg [3:0]  ex_i;            // routed-expert index
    reg [3:0]  ex;              // execute sub-FSM
    reg [71:0] eid_v;          // V_TOPK results (packed 8x9b)       // V_TOPK results
    reg [3:0]  res_cnt;
    reg [17:0] amx;             // head argmax result
    reg [15:0] lg_beat;
    reg        lw;              // logits-write sub-step
    reg        ts;              // token-start sub-step
    reg [1:0]  ep;              // emb push counter

    // latched GEMV segment descriptors
    reg [35:0] pl_qaddr, pl_saddr, pl_zaddr;
    reg [31:0] pl_qlen, pl_slen, pl_zlen;

    // prefetch state (next GEMV jobs' segments, pushed during ex=9 wait)
    reg  [2:0]  pf_state;
    // per-segment record of what the prefetch actually pushed (s/z/q),
    // one mask per lookahead level (A = next job, B = next+1); the
    // prefetched job's own pushes are suppressed for exactly these.
    // haveA/haveB mark fully-stocked levels; partial stocks (early
    // gv_done) stay consistent because the FSM skips masked segments.
    reg  [2:0]  pf_maskA, pf_maskB;
    reg         haveA, haveB;
    reg         pf_tgt;          // 0 = level A (next job), 1 = level B
    // descriptor handover: the prefetch already read the next jobs'
    // descriptors; hd_* carry them per level so a prefetched job
    // skips the ex=1..4 descriptor reads (never set for head targets)
    reg  [35:0] hd_qaddr, hd_saddr, hd_zaddr;
    reg  [31:0] hd_qlen, hd_slen, hd_zlen;
    reg         hd_valid;
    reg  [35:0] hd2_qaddr, hd2_saddr, hd2_zaddr;
    reg  [31:0] hd2_qlen, hd2_slen, hd2_zlen;
    reg         hd2_valid;

    // ------------------------------------------------------------
    // layer-program derived wires
    // ------------------------------------------------------------
    wire        is_F     = cfg_lt[li[2:0]];
    wire        boundary = (blkcnt == 4'd0);
    wire [4:0]  xbuf_li  = boundary ? (5'd14 + {1'b0, blk_idx}) : B_X;
    wire [4:0]  prefix_buf = boundary ? B_A : B_PREF;
    wire        rattn_skip = (blk_idx == 4'd0);
    wire [3:0]  nblk     = blk_idx + {3'b0, boundary};
    wire        fadd_isblk = (({2'b0, li} + 5'd1) < {1'b0, cfg_L})
                          && (blkcnt + 4'd1 == cfg_B);
    wire [4:0]  fadd_dst = fadd_isblk
                         ? (5'd14 + {1'b0, blk_idx} + {4'b0, boundary})
                         : B_X;

    // resmix decode (st == ST_RATTN / ST_RMLP / ST_RMOUT)
    wire [3:0] rm_ncand = (st == ST_RMLP) ? (nblk + 4'd1)
                        :                   (blk_idx + 4'd1);
    wire [4:0] rm_last  = (st == ST_RATTN) ? xbuf_li
                        : (st == ST_RMLP)  ? prefix_buf
                        :                    B_X;
    wire [14:0] rm_nw = (st == ST_RATTN) ? wb_rattn_nw_v[15*(li[1:0]) +: 15]
                      : (st == ST_RMLP)  ? wb_rmlp_nw_v[15*(li[1:0]) +: 15]
                      :                    wb_ro_nw;
    wire [14:0] rm_pw = (st == ST_RATTN) ? wb_rattn_pw_v[15*(li[1:0]) +: 15]
                      : (st == ST_RMLP)  ? wb_rmlp_pw_v[15*(li[1:0]) +: 15]
                      :                    wb_ro_pw;
    wire [4:0] rm_cand = ({1'b0, ci} < (rm_ncand - 4'd1))
                       ? (5'd14 + {1'b0, ci}) : rm_last;
    wire [4:0] rm_b0 = (rm_ncand > 4'd1) ? 5'd14 : rm_last;
    wire [4:0] rm_b1 = (rm_ncand > 4'd2) ? 5'd15
                     : (rm_ncand == 4'd2) ? rm_last : 5'd0;
    wire [4:0] rm_b2 = (rm_ncand > 4'd3) ? 5'd16
                     : (rm_ncand == 4'd3) ? rm_last : 5'd0;
    wire [4:0] rm_b3 = (rm_ncand == 4'd4) ? rm_last : 5'd0;
    wire [11:0] head_off = mhoff[11:0];            // hi * dh
    wire [35:0] mhoff = mul9({14'b0, hi}, cfg_dh[8:0]);

    // expert descriptor base for the current routed expert
    wire [35:0] ex_mul = mul9({9'b0, eid_v[9*(ex_i[2:0]) +: 9]}, 9'd9);
    wire [14:0] ex_base = ix_e0_v[15*(li[1:0]) +: 15] + ex_mul[14:0];

    // ------------------------------------------------------------
    // the program: combinational decode of the current op
    // ------------------------------------------------------------
    reg [1:0]  dec_kind;
    reg        dec_skip;
    reg [4:0]  dec_code;
    reg [11:0] dec_len;
    reg [4:0]  dec_s1, dec_s2, dec_dst;
    reg [14:0] dec_wb;
    reg [31:0] dec_aux;
    reg [14:0] dec_qidx;
    reg [15:0] dec_K;
    reg [17:0] dec_N;
    reg [4:0]  dec_xb, dec_yb;
    reg [1:0]  dec_mode;
    reg [7:0]  dec_R;
    reg        dec_pre;         // addresses precomputed (no DESC reads)
    reg        dec_nseg1;       // head mode: only the q segment

    always @* begin
        dec_kind = KD_VEC;
        dec_skip = 1'b0;
        dec_code = OP_RMSNORM;
        dec_len  = 12'd0;
        dec_s1   = 5'd0;
        dec_s2   = 5'd0;
        dec_dst  = 5'd0;
        dec_wb   = 15'd0;
        dec_aux  = 32'd0;
        dec_qidx = 15'd0;
        dec_K    = 16'd0;
        dec_N    = 18'd0;
        dec_xb   = 5'd0;
        dec_yb   = 5'd0;
        dec_mode = GM_ROW;
        dec_R    = R_ROW;
        dec_pre  = 1'b0;
        dec_nseg1 = 1'b0;
        case (st)
            // ---- residual mixing (per candidate: RMSNORM+DOT, then SMIX)
            ST_RATTN, ST_RMLP, ST_RMOUT: begin
                dec_skip = (st == ST_RATTN) && rattn_skip;
                if (rs2 == 2'd0) begin
                    dec_code = OP_RMSNORM;
                    dec_len  = cfg_d[11:0];
                    dec_s1   = rm_cand;
                    dec_dst  = B_G;
                    dec_wb   = rm_nw;
                end else if (rs2 == 2'd1) begin
                    dec_code = OP_DOT;
                    dec_len  = cfg_d[11:0];
                    dec_s1   = B_G;
                    dec_wb   = rm_pw;
                    dec_aux  = {28'b0, ci};
                end else begin
                    dec_code = OP_SMIX;
                    dec_len  = cfg_d[11:0];
                    // non-boundary layers: keep x_entry in B_X for the
                    // prefix ADD (prefix = x_entry + a, NOT mix + a), so
                    // the res_attn mix lands in the (free) prefix buffer
                    dec_dst  = ((st == ST_RATTN) && !boundary) ? B_PREF
                             : B_X;
                    dec_aux  = {8'b0, rm_b3, rm_b2, rm_b1, rm_b0, rm_ncand};
                end
            end
            // ---- h1 = rmsnorm(x, norm1.w)
            ST_NORM1: begin
                dec_code = OP_RMSNORM;
                dec_len  = cfg_d[11:0];
                // after a non-boundary res_attn the mix is in B_PREF
                // (B_X still holds x_entry); boundary layers mix in B_X
                dec_s1   = rattn_skip ? xbuf_li
                         : (boundary ? B_X : B_PREF);
                dec_dst  = B_H1;
                dec_wb   = wb_norm1_v[15*(li[1:0]) +: 15];
            end
            // ---- token mixer
            ST_MIX: begin
                if (is_F) begin
                    case (mx)
                        5'd0: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15];
                            dec_K = w_d; dec_N = {2'b0, w_dc16};
                            dec_xb = B_H1; dec_yb = B_LAT;
                        end
                        5'd1: begin
                            dec_code = OP_RMSNORM;
                            dec_len  = {2'b0, cfg_dc};
                            dec_s1   = B_LAT; dec_dst = B_LAT;
                            dec_wb   = wb_knorm_v[15*(li[1:0]) +: 15];
                        end
                        5'd2: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd3;
                            dec_K = w_d; dec_N = w_hdk;
                            dec_xb = B_H1; dec_yb = B_Q;
                        end
                        5'd3: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd6;
                            dec_K = w_d; dec_N = w_hdr;
                            dec_xb = B_H1; dec_yb = B_K;
                        end
                        5'd4: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd9;
                            dec_K = w_dc16; dec_N = w_hdk;
                            dec_xb = B_LAT; dec_yb = B_V;
                        end
                        5'd5: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd12;
                            dec_K = w_d; dec_N = {2'b0, w_dr16};
                            dec_xb = B_H1; dec_yb = B_F1;
                        end
                        5'd6: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd15;
                            dec_K = w_dc16; dec_N = w_hdv;
                            dec_xb = B_LAT; dec_yb = B_F;
                        end
                        5'd7: dec_kind = KD_MLA;
                        5'd8: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd18;
                            dec_K = w_hdv[15:0]; dec_N = {2'b0, w_d};
                            dec_xb = B_CORE; dec_yb = B_A;
                        end
                        default: dec_skip = 1'b1;
                    endcase
                end else begin
                    case (mx)
                        5'd0: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15];
                            dec_K = w_d; dec_N = w_P;
                            dec_xb = B_H1; dec_yb = B_Q;
                        end
                        5'd1: begin
                            dec_code = OP_CONV;
                            dec_len  = w_P[11:0];
                            dec_s1   = B_Q; dec_dst = B_Q;
                            dec_wb   = wb_qconv_v[15*(li[1:0]) +: 15];
                            dec_aux  = {27'b0, li, 2'b00};
                        end
                        5'd2: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd3;
                            dec_K = w_d; dec_N = w_P;
                            dec_xb = B_H1; dec_yb = B_K;
                        end
                        5'd3: begin
                            dec_code = OP_CONV;
                            dec_len  = w_P[11:0];
                            dec_s1   = B_K; dec_dst = B_K;
                            dec_wb   = wb_kconv_v[15*(li[1:0]) +: 15];
                            dec_aux  = {27'b0, li, 2'b01};
                        end
                        5'd4: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd6;
                            dec_K = w_d; dec_N = w_P;
                            dec_xb = B_H1; dec_yb = B_V;
                        end
                        5'd5: begin
                            dec_code = OP_CONV;
                            dec_len  = w_P[11:0];
                            dec_s1   = B_V; dec_dst = B_V;
                            dec_wb   = wb_vconv_v[15*(li[1:0]) +: 15];
                            dec_aux  = {27'b0, li, 2'b10};
                        end
                        5'd6: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd9;
                            dec_K = w_d; dec_N = {2'b0, w_kh16};
                            dec_xb = B_H1; dec_yb = B_BETA;
                        end
                        5'd7: begin
                            dec_code = OP_SIG;
                            dec_len  = {8'b0, cfg_kh};
                            dec_s1   = B_BETA; dec_dst = B_BETA;
                        end
                        5'd8: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd12;
                            dec_K = w_d; dec_N = {2'b0, w_dh16};
                            dec_xb = B_H1; dec_yb = B_F1;
                        end
                        5'd9: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd15;
                            dec_K = w_dh16; dec_N = w_P;
                            dec_xb = B_F1; dec_yb = B_F;
                        end
                        5'd10: begin
                            dec_code = OP_PREALPHA;
                            dec_len  = w_P[11:0];
                            dec_s1   = B_F; dec_dst = B_F;
                            dec_wb   = wb_A_v[15*(li[1:0]) +: 15];
                            dec_aux  = {6'b0, cfg_dh, 1'b0, wb_dtb_v[15*(li[1:0]) +: 15]};
                        end
                        5'd11: begin
                            dec_code = OP_ALPHA;
                            dec_len  = w_P[11:0];
                            dec_s1   = B_F; dec_dst = B_F;
                        end
                        5'd12: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd18;
                            dec_K = w_d; dec_N = {2'b0, w_dh16};
                            dec_xb = B_H1; dec_yb = B_F1;
                        end
                        5'd13: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd21;
                            dec_K = w_dh16; dec_N = w_P;
                            dec_xb = B_F1; dec_yb = B_Z;
                        end
                        5'd14: begin
                            dec_code = OP_SIG;
                            dec_len  = w_P[11:0];
                            dec_s1   = B_Z; dec_dst = B_Z;
                        end
                        5'd15: begin
                            dec_code = OP_L2NORM;
                            dec_len  = {2'b0, cfg_dh};
                            dec_s1   = B_Q; dec_dst = B_Q;
                            dec_aux  = {8'b0, head_off, head_off};
                        end
                        5'd16: begin
                            dec_code = OP_L2NORM;
                            dec_len  = {2'b0, cfg_dh};
                            dec_s1   = B_K; dec_dst = B_K;
                            dec_aux  = {8'b0, head_off, head_off};
                        end
                        5'd17: dec_kind = KD_KDA;
                        5'd18: begin
                            dec_code = OP_RMSNORM;
                            dec_len  = {2'b0, cfg_dh};
                            dec_s1   = B_O; dec_dst = B_O;
                            dec_wb   = wb_onorm_v[15*(li[1:0]) +: 15];
                            dec_aux  = {8'b0, head_off, head_off};
                        end
                        5'd19: begin
                            dec_code = OP_MULZ;
                            dec_len  = w_P[11:0];
                            dec_s1   = B_O; dec_s2 = B_Z; dec_dst = B_CORE;
                        end
                        5'd20: begin
                            dec_kind = KD_GEMV;
                            dec_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + 15'd24;
                            dec_K = w_P16; dec_N = {2'b0, w_d};
                            dec_xb = B_CORE; dec_yb = B_A;
                        end
                        default: dec_skip = 1'b1;
                    endcase
                end
            end
            // ---- prefix = prefix + a (skipped at block boundaries)
            ST_PADD: begin
                dec_skip = boundary;
                dec_code = OP_ADD;
                dec_len  = cfg_d[11:0];
                dec_s1   = xbuf_li; dec_s2 = B_A; dec_dst = B_PREF;
            end
            // ---- h2 = rmsnorm(x, norm2.w)
            ST_NORM2: begin
                dec_code = OP_RMSNORM;
                dec_len  = cfg_d[11:0];
                dec_s1   = B_X; dec_dst = B_H2;
                dec_wb   = wb_norm2_v[15*(li[1:0]) +: 15];
            end
            // ---- MoE router + top-k
            ST_ROUT: begin
                dec_kind = KD_GEMV;
                dec_qidx = ix_router_v[15*(li[1:0]) +: 15];
                dec_K = w_d; dec_N = {2'b0, w_E16};
                dec_xb = B_H2; dec_yb = B_RIN;
            end
            ST_SIGR: begin
                dec_code = OP_SIG;
                dec_len  = {2'b0, cfg_E};
                dec_s1   = B_RIN; dec_dst = B_RIN;
            end
            ST_TOPK: begin
                dec_code = OP_TOPK;
                dec_len  = {2'b0, cfg_E};
                dec_s1   = B_RIN; dec_s2 = B_ORD; dec_dst = B_WSEL;
                dec_wb   = wb_bias_v[15*(li[1:0]) +: 15];
                dec_aux  = {28'b0, cfg_tk};
            end
            // ---- shared expert SwiGLU
            ST_SHG: begin
                dec_kind = KD_GEMV;
                dec_qidx = ix_shared_v[15*(li[1:0]) +: 15];
                dec_K = w_d; dec_N = {2'b0, w_ff16};
                dec_xb = B_H2; dec_yb = B_G;
            end
            ST_SHU: begin
                dec_kind = KD_GEMV;
                dec_qidx = ix_shared_v[15*(li[1:0]) +: 15] + 15'd3;
                dec_K = w_d; dec_N = {2'b0, w_ff16};
                dec_xb = B_H2; dec_yb = B_U;
            end
            ST_SILU: begin
                dec_code = OP_SILU;
                dec_len  = {2'b0, cfg_ff};
                dec_s1   = B_G; dec_dst = B_G;
            end
            ST_MULZ: begin
                dec_code = OP_MULZ;
                dec_len  = {2'b0, cfg_ff};
                dec_s1   = B_G; dec_s2 = B_U; dec_dst = B_ACT;
            end
            ST_SHD: begin
                dec_kind = KD_GEMV;
                dec_qidx = ix_shared_v[15*(li[1:0]) +: 15] + 15'd6;
                dec_K = w_ff16; dec_N = {2'b0, w_d};
                dec_xb = B_ACT; dec_yb = B_MOE;
            end
            // ---- routed expert i (SwiGLU + weighted accumulate)
            ST_EXG: begin
                dec_kind = KD_GEMV;
                dec_qidx = ex_base;
                dec_K = w_d; dec_N = {2'b0, w_ff16};
                dec_xb = B_H2; dec_yb = B_G;
            end
            ST_EXU: begin
                dec_kind = KD_GEMV;
                dec_qidx = ex_base + 15'd3;
                dec_K = w_d; dec_N = {2'b0, w_ff16};
                dec_xb = B_H2; dec_yb = B_U;
            end
            ST_SILUE: begin
                dec_code = OP_SILU;
                dec_len  = {2'b0, cfg_ff};
                dec_s1   = B_G; dec_dst = B_G;
            end
            ST_MULZE: begin
                dec_code = OP_MULZ;
                dec_len  = {2'b0, cfg_ff};
                dec_s1   = B_G; dec_s2 = B_U; dec_dst = B_ACT;
            end
            ST_EXD: begin
                dec_kind = KD_GEMV;
                dec_qidx = ex_base + 15'd6;
                dec_K = w_ff16; dec_N = {2'b0, w_d};
                dec_xb = B_ACT; dec_yb = B_EX;
            end
            ST_MACW: begin
                dec_code = OP_MACW;
                dec_len  = cfg_d[11:0];
                dec_s1   = B_MOE; dec_s2 = B_EX; dec_dst = B_MOE;
                dec_aux  = {23'b0, B_WSEL, ex_i};
            end
            // ---- x = prefix + m
            ST_FADD: begin
                dec_code = OP_ADD;
                dec_len  = cfg_d[11:0];
                dec_s1   = prefix_buf; dec_s2 = B_MOE; dec_dst = fadd_dst;
            end
            // ---- hn = rmsnorm(x, final_norm.w)
            ST_FNORM: begin
                dec_code = OP_RMSNORM;
                dec_len  = cfg_d[11:0];
                dec_s1   = B_X; dec_dst = B_H1;
                dec_wb   = wb_final;
            end
            // ---- head GEMV (logits)
            ST_HEAD: begin
                dec_kind  = KD_GEMV;
                dec_pre   = 1'b1;
                dec_nseg1 = 1'b1;
                dec_mode  = GM_HEAD;
                dec_K     = w_d;
                dec_N     = cfg_V;
                dec_R     = R_HEAD;
                dec_xb    = B_H1;
                dec_yb    = B_LG;
            end
            default: dec_skip = 1'b1;
        endcase
    end

    wire [15:0] dec_gsz = (dec_K < {7'b0, cfg_gs}) ? dec_K
                                                   : {7'b0, cfg_gs};
    wire [15:0] dec_ng_sh = (cfg_gs == 9'd128) ? ((dec_K + 16'd127) >> 7)
                                               : ((dec_K + 16'd63) >> 6);
    wire [3:0]  dec_ng  = (dec_gsz == dec_K) ? 4'd1 : dec_ng_sh[3:0];

    // ------------------------------------------------------------
    // next-GEMV predictor (2-deep): the stage sequence is
    // deterministic, so the next gemv job and the one after it are
    // known while the current one runs. pf_step() walks the stage
    // chain one gemv-to-gemv step (interleaved vec/KDA/MLA jobs push
    // no segments and are transparent to the byte stream); pf_qidx()
    // maps a predicted state back to its descriptor index.
    // State encoding: 0=ST_MIX(mx), 1=ROUT, 2=SHG, 3=SHU, 4=SHD,
    // 5=EXG, 6=EXU, 7=EXD (expert states carry the expert index).
    // ------------------------------------------------------------
    localparam [2:0] PX_MIX = 3'd0, PX_ROUT = 3'd1, PX_SHG = 3'd2,
                     PX_SHU = 3'd3, PX_SHD = 3'd4, PX_EXG = 3'd5,
                     PX_EXU = 3'd6, PX_EXD = 3'd7;

    function [12:0] pf_step(input [2:0] f_st, input [4:0] f_mx,
                            input [3:0] f_ex);
        // {valid, nst[2:0], nmx[4:0], nex[3:0]}: the next gemv job
        begin
            pf_step = 13'd0;                 // default: no next job
            if (f_st == PX_MIX) begin
                // both layer types interleave gemv/vec the same way:
                // MLA 0,2,3,4,5,6,8 | KDA 0,2,4,6,8,9,12,13,20, then ROUT
                case (f_mx)
                    5'd0:  pf_step = {1'b1, PX_MIX, 5'd2, 4'd0};
                    5'd2:  pf_step = {1'b1, PX_MIX,
                                      is_F ? 5'd3 : 5'd4, 4'd0};
                    5'd3:  pf_step = {1'b1, PX_MIX, 5'd4, 4'd0};
                    5'd4:  pf_step = {1'b1, PX_MIX,
                                      is_F ? 5'd5 : 5'd6, 4'd0};
                    5'd5:  pf_step = {1'b1, PX_MIX, 5'd6, 4'd0};
                    5'd6:  pf_step = {1'b1, PX_MIX, 5'd8, 4'd0};
                    5'd8:  pf_step = {1'b1,
                                      is_F ? PX_ROUT : PX_MIX,
                                      is_F ? 5'd0 : 5'd9, 4'd0};
                    5'd9:  pf_step = {1'b1, PX_MIX, 5'd12, 4'd0};
                    5'd12: pf_step = {1'b1, PX_MIX, 5'd13, 4'd0};
                    5'd13: pf_step = {1'b1, PX_MIX, 5'd20, 4'd0};
                    5'd20: pf_step = {1'b1, PX_ROUT, 5'd0, 4'd0};
                    default: pf_step = 13'd0;
                endcase
            end else if (f_st == PX_ROUT) begin
                pf_step = {1'b1, PX_SHG, 5'd0, 4'd0};
            end else if (f_st == PX_SHG) begin
                pf_step = {1'b1, PX_SHU, 5'd0, 4'd0};
            end else if (f_st == PX_SHU) begin
                pf_step = {1'b1, PX_SHD, 5'd0, 4'd0};
            end else if (f_st == PX_SHD) begin
                pf_step = {1'b1, PX_EXG, 5'd0, 4'd0};
            end else if (f_st == PX_EXG) begin
                pf_step = {1'b1, PX_EXU, 5'd0, f_ex};
            end else if (f_st == PX_EXU) begin
                pf_step = {1'b1, PX_EXD, 5'd0, f_ex};
            end else if (f_st == PX_EXD) begin
                if (f_ex + 4'd1 < cfg_tk)
                    pf_step = {1'b1, PX_EXG, 5'd0, f_ex + 4'd1};
                else
                    pf_step = 13'd0;   // head (dec_pre) or next token
            end
        end
    endfunction

    /* verilator lint_off UNUSEDSIGNAL */
    function [14:0] pf_qidx(input [2:0] f_st, input [4:0] f_mx,
                            input [3:0] f_ex);
        // (f_ex[3] and em[35:15] are beyond the used space: cfg_tk <= 8
        // experts and 9-bit expert ids * 9 < 2^13)
        reg [5:0]  off;
        reg [35:0] em;
        begin
            pf_qidx = 15'd0;
            off     = 6'd0;
            em      = 36'd0;
            if (f_st == PX_MIX) begin
                // descriptor offsets within the mixer block
                case (f_mx)
                    5'd0:  off = 6'd0;
                    5'd2:  off = 6'd3;
                    5'd3:  off = is_F ? 6'd6 : 6'd0;
                    5'd4:  off = is_F ? 6'd9 : 6'd6;
                    5'd5:  off = 6'd12;
                    5'd6:  off = is_F ? 6'd15 : 6'd9;
                    5'd8:  off = is_F ? 6'd18 : 6'd12;
                    5'd9:  off = 6'd15;
                    5'd12: off = 6'd18;
                    5'd13: off = 6'd21;
                    5'd20: off = 6'd24;
                    default: off = 6'd0;
                endcase
                pf_qidx = ix_mixer_v[15*(li[1:0]) +: 15] + {9'b0, off};
            end else if (f_st == PX_ROUT) begin
                pf_qidx = ix_router_v[15*(li[1:0]) +: 15];
            end else if ((f_st == PX_SHG) || (f_st == PX_SHU)
                         || (f_st == PX_SHD)) begin
                pf_qidx = ix_shared_v[15*(li[1:0]) +: 15]
                        + ((f_st == PX_SHU) ? 15'd3
                         : (f_st == PX_SHD) ? 15'd6 : 15'd0);
            end else begin
                // expert states: ex_base for eid[f_ex] + G/U/D offset
                em = mul9({9'b0, eid_v[9*(f_ex[2:0]) +: 9]}, 9'd9);
                pf_qidx = ix_e0_v[15*(li[1:0]) +: 15] + em[14:0]
                        + ((f_st == PX_EXU) ? 15'd3
                         : (f_st == PX_EXD) ? 15'd6 : 15'd0);
            end
        end
    endfunction
    /* verilator lint_on UNUSEDSIGNAL */

    wire        pf_ok = (st == ST_MIX) || (st == ST_ROUT)
                      || (st == ST_SHG) || (st == ST_SHU)
                      || (st == ST_SHD) || (st == ST_EXG)
                      || (st == ST_EXU) || (st == ST_EXD);
    wire [12:0] pf_s1  = pf_step((st == ST_MIX)  ? PX_MIX
                               : (st == ST_ROUT) ? PX_ROUT
                               : (st == ST_SHG)  ? PX_SHG
                               : (st == ST_SHU)  ? PX_SHU
                               : (st == ST_SHD)  ? PX_SHD
                               : (st == ST_EXG)  ? PX_EXG
                               : (st == ST_EXU)  ? PX_EXU
                               :                   PX_EXD, mx, ex_i);
    wire [12:0] pf_s2  = pf_step(pf_s1[11:9], pf_s1[8:4], pf_s1[3:0]);
    wire        nx_last_ex = (st == ST_EXD) && (ex_i + 4'd1 >= cfg_tk);
    wire        nx_to_nl   = nx_last_ex
                           && (({2'b0, li} + 5'd1) < {1'b0, cfg_L});
    wire        nx_valid   = pf_ok && (pf_s1[12] || nx_to_nl);
    wire [14:0] nx_qidx    = nx_to_nl
                           ? ix_mixer_v[15*({1'b0, li[1:0]} + 3'd1) +: 15]
                           : pf_qidx(pf_s1[11:9], pf_s1[8:4], pf_s1[3:0]);
    wire        nx2_valid  = pf_ok && pf_s1[12] && pf_s2[12]
                           && !nx_last_ex;
    wire [14:0] nx2_qidx   = pf_qidx(pf_s2[11:9], pf_s2[8:4], pf_s2[3:0]);

    // ------------------------------------------------------------
    // prefetch FSM: while the current GEMV job runs (ex==9, waiting
    // for gv_done), read the next job's descriptors and push its
    // s/z/q segments into the fetch queue. The fetch engine streams
    // them in the background, so the next job's first beat is already
    // on-chip when it starts (~24 cycles of DRAM latency hidden).
    // pf drives desc_raddr / seg_* only while ex==9; the main FSM
    // drives them otherwise.
    // ------------------------------------------------------------
    localparam [2:0] PF_IDLE = 3'd0, PF_Q = 3'd1, PF_S = 3'd2,
                     PF_Z = 3'd3, PF_PS = 3'd4, PF_PZ = 3'd5,
                     PF_PQ = 3'd6, PF_DONE = 3'd7;
    reg [35:0] pf_qaddr, pf_saddr, pf_zaddr;
    reg [31:0] pf_qlen, pf_slen, pf_zlen;
    wire       pf_wantA  = !haveA && nx_valid;
    wire       pf_wantB  = !haveB && nx2_valid;
    wire [14:0] pf_tqidx = pf_tgt ? nx2_qidx : nx_qidx;
    wire [2:0]  pf_cmask = pf_tgt ? pf_maskB : pf_maskA;
    wire       pf_active = (state == S_LAY) && (ex == 4'd9)
                         && (pf_state != PF_DONE)
                         && (pf_state != PF_IDLE);

    // ------------------------------------------------------------
    // output channel drives (combinational valids + payloads)
    // ------------------------------------------------------------
    wire ex_is_gemv = (state == S_LAY) && (dec_kind == KD_GEMV);
    wire ex_is_vec  = (state == S_LAY) && (dec_kind == KD_VEC);
    wire ex_is_kda  = (state == S_LAY) && (dec_kind == KD_KDA);
    wire ex_is_mla  = (state == S_LAY) && (dec_kind == KD_MLA);

    wire push_s = ex_is_gemv && (ex == 4'd5) && !dec_nseg1 && !pf_maskA[0];
    wire push_z = ex_is_gemv && (ex == 4'd6) && !pf_maskA[1];
    wire push_q = ex_is_gemv && (ex == 4'd7) && !pf_maskA[2]
                && !(dec_pre && hq_fill_done);
    // one-shot head-q shadow push (first gemv job of the run; the head
    // weight tensor is token-independent, so it is fetched only once)
    reg         hq_pushed;
    wire push_hq = ex_is_gemv && (ex == 4'd8) && gv_ready && !hq_pushed;
    // rewind the shadow reader when a head job is issued (each token
    // re-reads the same resident segment)
    assign hq_rewind = ex_is_gemv && (ex == 4'd8) && gv_ready
                     && (st == ST_HEAD);

    wire pf_pushing = pf_active
                    && (((pf_state == PF_PS) && !pf_cmask[0])
                        || ((pf_state == PF_PZ) && !pf_cmask[1])
                        || ((pf_state == PF_PQ) && !pf_cmask[2]));
    assign seg_valid = (state == S_HDR_PUSH) || (state == S_DESC_PUSH)
                     || (state == S_TOK_PUSH) || (state == S_HS_PUSH)
                     || (state == S_HZ_PUSH) || (state == S_EMB_PUSH)
                     || ((state == S_WALK) && (ws == 3'd3))
                     || push_s || push_z || push_q || pf_pushing || push_hq;
    assign seg_addr  = (state == S_HDR_PUSH)  ? 36'd0
                     : (state == S_DESC_PUSH) ? cfg_desc_addr
                     : (state == S_TOK_PUSH)  ? cfg_tokens_addr
                     : (state == S_HS_PUSH)   ? head_s_addr
                     : (state == S_HZ_PUSH)   ? head_z_addr
                     : (state == S_WALK)      ? walk_addr
                     : (state == S_EMB_PUSH)  ? emb_seg_addr
                     : push_s                 ? pl_saddr
                     : push_z                 ? pl_zaddr
                     : push_hq                ? head_q_addr
                     : push_q                 ? pl_qaddr
                     : (pf_state == PF_PS)    ? pf_saddr
                     : (pf_state == PF_PZ)    ? pf_zaddr
                     : pf_active              ? pf_qaddr
                     :                          pl_qaddr;
    assign seg_len   = (state == S_HDR_PUSH)  ? 32'd256
                     : (state == S_DESC_PUSH) ? {13'b0, cfg_NT, 4'b0000}
                     : (state == S_TOK_PUSH)  ? {20'b0, cfg_SL, 2'b00}
                     : (state == S_HS_PUSH)   ? head_s_len
                     : (state == S_HZ_PUSH)   ? head_z_len
                     : (state == S_WALK)      ? walk_len
                     : (state == S_EMB_PUSH)  ? emb_seg_len
                     : push_s                 ? pl_slen
                     : push_z                 ? pl_zlen
                     : push_hq                ? head_q_len
                     : push_q                 ? pl_qlen
                     : (pf_state == PF_PS)    ? pf_slen
                     : (pf_state == PF_PZ)    ? pf_zlen
                     : pf_active              ? pf_qlen
                     :                          pl_qlen;
    assign seg_tag   = (state == S_HDR_PUSH)  ? TG_HDR
                     : (state == S_DESC_PUSH) ? TG_DESC
                     : (state == S_TOK_PUSH)  ? TG_TOK
                     : (state == S_HS_PUSH)   ? TG_HS
                     : (state == S_HZ_PUSH)   ? TG_HZ
                     : (state == S_WALK)      ? TG_WBUF
                     : (state == S_EMB_PUSH && ep == 2'd0) ? TG_GS
                     : (state == S_EMB_PUSH && ep == 2'd1) ? TG_GZ
                     : (state == S_EMB_PUSH) ? TG_GQ
                     : push_s                ? TG_GS
                     : push_z                ? TG_GZ
                     : push_hq               ? 4'd10
                     : push_q                ? TG_GQ
                     : (pf_state == PF_PS)   ? TG_GS
                     : (pf_state == PF_PZ)   ? TG_GZ
                     : pf_active             ? TG_GQ
                     :                         TG_GQ;

    // emb row addresses for the current token
    wire [35:0] emb_sz_off = mul9(tok_val, {5'b0, w_ng_e});
    wire [35:0] emb_q_off  = mul9(tok_val, w_d_half);
    wire [35:0] emb_s_row  = emb_s_base + {emb_sz_off[34:0], 1'b0};
    wire [35:0] emb_z_row  = emb_z_base + emb_sz_off;
    wire [35:0] emb_q_row  = emb_q_base + emb_q_off;
    wire [35:0] emb_seg_addr = (ep == 2'd0) ? emb_s_row
                             : (ep == 2'd1) ? emb_z_row
                             :                emb_q_row;
    wire [31:0] emb_seg_len  = (ep == 2'd0) ? {27'b0, w_ng_e, 1'b0}
                             : (ep == 2'd1) ? {28'b0, w_ng_e}
                             :                {23'b0, w_d_half};

    // byte-stream intake
    assign bs_ready = (state == S_HDR_DRAIN) || (state == S_DESC_DRAIN)
                    || (in_ldrain && (ld_fill == 5'd0));
    wire bs_fire = bs_valid && bs_ready;

    // staged word emit (write ports)
    assign tok_we    = ld_emit && in_tok_drain;
    assign tok_waddr = tok_wcnt;
    assign tok_wdata = ld_flat[31:0];
    assign wb_we     = ld_emit && in_wb_drain;
    assign wb_waddr  = wb_wcnt;
    assign wb_wdata  = ld_flat[15:0];
    assign hs_we     = ld_emit && in_hs_drain;
    assign hs_waddr  = hs_wcnt;
    assign hs_wdata  = ld_flat[15:0];
    assign hz_we     = ld_emit && in_hz_drain;
    assign hz_waddr  = hz_wcnt;
    assign hz_wdata  = ld_flat[7:0];
    wire [2:0] ld_wbytes = in_tok_drain ? 3'd4 : in_hz_drain ? 3'd1 : 3'd2;

    // DESC direct write (aligned 16B beats)
    assign desc_we    = (state == S_DESC_DRAIN) && bs_valid;
    assign desc_waddr = dcnt;
    assign desc_wdata = bs_data;

    // GEMV job channel
    assign gv_valid  = (state == S_EMB_JOB)
                     || (ex_is_gemv && (ex == 4'd8));
    assign gv_mode   = (state == S_EMB_JOB) ? GM_DEQ : dec_mode;
    assign gv_q_addr = (state == S_EMB_JOB) ? emb_q_row : pl_qaddr;
    assign gv_s_addr = (state == S_EMB_JOB) ? emb_s_row : pl_saddr;
    assign gv_z_addr = (state == S_EMB_JOB) ? emb_z_row : pl_zaddr;
    assign gv_K      = (state == S_EMB_JOB) ? cfg_d : dec_K;
    assign gv_N      = (state == S_EMB_JOB) ? {2'b0, cfg_d} : dec_N;
    assign gv_ng     = (state == S_EMB_JOB) ? w_ng_e : dec_ng;
    assign gv_gsz    = (state == S_EMB_JOB) ? w_gsz_d : dec_gsz;
    assign gv_R      = (state == S_EMB_JOB) ? R_DEQ : dec_R;
    assign gv_xbuf   = (state == S_EMB_JOB) ? B_X : dec_xb;
    assign gv_ybuf   = (state == S_EMB_JOB) ? B_B0 : dec_yb;

    // vec op channel
    assign vc_valid = ex_is_vec && (ex == 4'd1);
    assign vc_code  = dec_code;
    assign vc_len   = dec_len;
    assign vc_src1  = dec_s1;
    assign vc_src2  = dec_s2;
    assign vc_dst   = dec_dst;
    assign vc_wbase = dec_wb;
    assign vc_aux   = dec_aux;

    // kda / mla job channels (fields fixed by construction)
    assign kd_valid = ex_is_kda && (ex == 4'd1);
    assign kd_layer = li;
    assign kd_dh    = cfg_dh;
    assign kd_H     = cfg_kh;
    assign kd_cdh   = c_dh;
    assign kd_q     = B_Q;
    assign kd_k     = B_K;
    assign kd_v     = B_V;
    assign kd_beta  = B_BETA;
    assign kd_alpha = B_F;
    assign kd_o     = B_O;

    assign ml_valid = ex_is_mla && (ex == 4'd1);
    assign ml_pos   = t;
    assign ml_dqk   = w_dqk[9:0];
    assign ml_dk    = cfg_dk;
    assign ml_dv    = cfg_dv;
    assign ml_H     = cfg_nh;
    assign ml_catt  = c_att;
    assign ml_qc    = B_Q;
    assign ml_qr    = B_K;
    assign ml_kc    = B_V;
    assign ml_kr    = B_F1;
    assign ml_v     = B_F;
    assign ml_ctx   = B_CORE;

    // write channel
    wire wr_logits = (state == S_LGWR) && lw;
    assign wr_valid  = wr_logits || (state == S_AMWR)
                     || (state == S_STATUS);
    assign wr_addr   = wr_logits          ? (lg_row + {16'b0, lg_beat, 4'b0000})
                     : (state == S_AMWR)  ? (cfg_argmax_addr
                                             + {24'b0, t[9:2], 4'b0000})
                     :                      cfg_status_addr;
    assign wr_data   = wr_logits          ? lg_rdata
                     : (state == S_AMWR)  ? {4{{14'b0, amx}}}
                     :                      {96'b0, STATUS_MAGIC};
    assign wr_wstrb  = wr_logits          ? 16'hFFFF
                     : (state == S_AMWR)  ? (16'h000F << {t[1:0], 2'b00})
                     :                      16'h000F;
    wire wr_fire = wr_valid && wr_ready;

    // lg buffer read is synchronous: present the NEXT beat's address in
    // the fire cycle so the drain sustains 1 beat/cycle (was 2)
    assign lg_raddr  = lg_beat + {15'b0, (wr_logits && wr_ready)};
    assign tok_raddr = t[8:0];

    assign cmd_ready = (state == S_IDLE);
    assign rsp_valid = (state == S_DONE);
    assign rsp_data  = RSP_DONE;

    // consume intentionally-unused inputs (lint cleanliness)
`ifdef MSH_DEBUG
    always @(posedge clk) begin
        if (seg_valid && seg_ready)
            $display("[seq] SEG push addr=%h len=%0d tag=%0d st=%0d pf=%0d",
                     seg_addr, seg_len, seg_tag, st, pf_pushing);
        if ((state == S_LAY) && (ex == 4'd9) && (pf_state == PF_IDLE)
            && (pf_wantA || pf_wantB))
            $display("[seq] PF start cyc=%0d nxq=%0d nx2q=%0d",
                     dbg_cyc, nx_qidx, nx2_qidx);
    end
`endif
    wire _unused = &{1'b0, bs_first, bs_tag, gv_am_val, vc_res_data[31:9],
                     desc_rdata[31:0], desc_rdata[127:96], tok_rdata[31:18],
                     w_P16[15:10], ex_mul[35:15], emb_q_off[35:26],
                     mP[35:18], mhdk[35:18], mhdr[35:18], mhdv[35:18],
                     mE9[35:15], mhoff[35:12], w_ng_sh[15:4],
                     dec_ng_sh[15:4], walk_len[31:16]};

    // ------------------------------------------------------------
    // sequential FSM
    // ------------------------------------------------------------
    integer i, l;
    reg [5:0]  widx;            // header word index
    reg [31:0] bw;              // header word lane
    reg        adv;             // advance pulse (blocking temp)

`ifdef MSH_DEBUG
    reg [31:0] dbg_cyc;
    always @(posedge clk) begin
        if (!rst_n) dbg_cyc <= 32'd0;
        else        dbg_cyc <= dbg_cyc + 32'd1;
    end
    // alive trace: every 65536 cycles while not idle, plus every state
    // change — pinpoints startup hangs without flooding the log
    reg [6:0]  dbg_state_d;
    reg        dbg_alive;
    always @(posedge clk) begin
        if (!rst_n) begin
            dbg_state_d <= 7'd0;
            dbg_alive   <= 1'b0;
        end else begin
            dbg_state_d <= state;
            if (state != dbg_state_d)
                $display("[seq] cyc=%0d STATE %0d -> %0d (widx=%0d walk=%0d seg_rdy=%0d bs_v=%0d)",
                         dbg_cyc, dbg_state_d, state, widx, walk_len,
                         seg_ready, bs_valid);
            else if (dbg_cyc[15:0] == 16'hffff && state != S_IDLE)
                $display("[seq] cyc=%0d ALIVE state=%0d widx=%0d walk=%0d ex=%0d st=%0d seg_rdy=%0d bs_v=%0d bs_owner=%0d",
                         dbg_cyc, state, widx, walk_len, ex, st,
                         seg_ready, bs_valid, bs_owner);
        end
    end
`endif

    always @(posedge clk) begin
        if (!rst_n) begin
            state       <= S_IDLE;
            bs_owner    <= 1'b0;
            cfg_L       <= 4'd0;
            cfg_d       <= 16'd0;
            cfg_nh      <= 4'd0;
            cfg_dk      <= 10'd0;
            cfg_dr      <= 10'd0;
            cfg_dv      <= 10'd0;
            cfg_dc      <= 10'd0;
            cfg_kh      <= 4'd0;
            cfg_dh      <= 10'd0;
            cfg_E       <= 10'd0;
            cfg_tk      <= 4'd0;
            cfg_ff      <= 10'd0;
            cfg_B       <= 4'd0;
            cfg_V       <= 18'd0;
            cfg_SL      <= 10'd0;
            cfg_gs      <= 9'd0;
            cfg_lt      <= 8'd0;
            cfg_NT      <= 15'd0;
            cfg_desc_addr   <= 36'd0;
            cfg_tokens_addr <= 36'd0;
            cfg_logits_addr <= 36'd0;
            cfg_argmax_addr <= 36'd0;
            cfg_status_addr <= 36'd0;
            cfg_stride  <= 32'd0;
            hcnt        <= 4'd0;
            dcnt        <= 15'd0;
            cc          <= 3'd0;
            emb_q_base  <= 36'd0;
            emb_s_base  <= 36'd0;
            emb_z_base  <= 36'd0;
            head_q_addr <= 36'd0;
            head_s_addr <= 36'd0;
            head_z_addr <= 36'd0;
            head_q_len  <= 32'd0;
            head_s_len  <= 32'd0;
            head_z_len  <= 32'd0;
            wst         <= 5'd0;
            wli         <= 3'd0;
            ws          <= 3'd0;
            didx        <= 15'd0;
            wb_off      <= 15'd0;
            walk_addr   <= 36'd0;
            walk_len    <= 32'd0;
            pf_state    <= PF_IDLE;
            pf_maskA    <= 3'd0;
            pf_maskB    <= 3'd0;
            haveA       <= 1'b0;
            haveB       <= 1'b0;
            pf_tgt      <= 1'b0;
            hq_pushed   <= 1'b0;
            hd_qaddr    <= 36'd0;
            hd_saddr    <= 36'd0;
            hd_zaddr    <= 36'd0;
            hd_qlen     <= 32'd0;
            hd_slen     <= 32'd0;
            hd_zlen     <= 32'd0;
            hd_valid    <= 1'b0;
            hd2_qaddr   <= 36'd0;
            hd2_saddr   <= 36'd0;
            hd2_zaddr   <= 36'd0;
            hd2_qlen    <= 32'd0;
            hd2_slen    <= 32'd0;
            hd2_zlen    <= 32'd0;
            hd2_valid   <= 1'b0;
            for (i = 0; i < 4; i = i + 1) begin
                wb_rattn_nw_v[15*(i) +: 15] <= 15'd0;
                wb_rattn_pw_v[15*(i) +: 15] <= 15'd0;
                wb_norm1_v[15*(i) +: 15]    <= 15'd0;
                wb_knorm_v[15*(i) +: 15]    <= 15'd0;
                wb_qconv_v[15*(i) +: 15]    <= 15'd0;
                wb_kconv_v[15*(i) +: 15]    <= 15'd0;
                wb_vconv_v[15*(i) +: 15]    <= 15'd0;
                wb_A_v[15*(i) +: 15]        <= 15'd0;
                wb_dtb_v[15*(i) +: 15]      <= 15'd0;
                wb_onorm_v[15*(i) +: 15]    <= 15'd0;
                wb_rmlp_nw_v[15*(i) +: 15]  <= 15'd0;
                wb_rmlp_pw_v[15*(i) +: 15]  <= 15'd0;
                wb_norm2_v[15*(i) +: 15]    <= 15'd0;
                wb_bias_v[15*(i) +: 15]     <= 15'd0;
                ix_mixer_v[15*(i) +: 15]    <= 15'd0;
                ix_router_v[15*(i) +: 15]   <= 15'd0;
                ix_shared_v[15*(i) +: 15]   <= 15'd0;
                ix_e0_v[15*(i) +: 15]       <= 15'd0;
            end
            wb_ro_nw    <= 15'd0;
            wb_ro_pw    <= 15'd0;
            wb_final    <= 15'd0;
            cs          <= 1'b0;
            bs_it       <= 5'd0;
            bs_lo       <= 18'd0;
            bs_hi       <= 18'd0;
            c_att       <= 17'd0;
            c_dh        <= 17'd0;
            ld_flat     <= 128'd0;
            ld_fill     <= 5'd0;
            ld_seen_last <= 1'b0;
            tok_wcnt    <= 9'd0;
            wb_wcnt     <= 15'd0;
            hs_wcnt     <= 19'd0;
            hz_wcnt     <= 19'd0;
            t           <= 10'd0;
            lg_row      <= 36'd0;
            tok_val     <= 18'd0;
            li          <= 3'd0;
            blk_idx     <= 4'd0;
            blkcnt      <= 4'd0;
            st          <= 5'd0;
            mx          <= 5'd0;
            rs2         <= 2'd0;
            ci          <= 4'd0;
            hi          <= 4'd0;
            ex_i        <= 4'd0;
            ex          <= 4'd0;
            for (i = 0; i < 8; i = i + 1) eid_v[9*(i) +: 9] <= 9'd0;
            res_cnt     <= 4'd0;
            amx         <= 18'd0;
            lg_beat     <= 16'd0;
            lw          <= 1'b0;
            ts          <= 1'b0;
            ep          <= 2'd0;
            pl_qaddr    <= 36'd0;
            pl_saddr    <= 36'd0;
            pl_zaddr    <= 36'd0;
            pl_qlen     <= 32'd0;
            pl_slen     <= 32'd0;
            pl_zlen     <= 32'd0;
            desc_raddr  <= 15'd0;
        end else begin
            /* verilator lint_off BLKSEQ */
            adv  = 1'b0;
            widx = 6'd0;
            bw   = 32'd0;

            // ---- staged stream-to-memory writes (all *_DRAIN states)
            if (bs_fire && in_ldrain) begin
                for (i = 0; i < 16; i = i + 1) begin
                    if ({1'b0, i[3:0]} < bs_count)
                        ld_flat[8*i +: 8] <= beat_al[8*i +: 8];
                    else
                        ld_flat[8*i +: 8] <= 8'd0;
                end
                ld_fill <= bs_count;
                if (bs_last) ld_seen_last <= 1'b1;
            end else if (ld_emit) begin
                ld_flat <= ld_flat >> {ld_wbytes, 3'b000};
                ld_fill <= ld_fill - {2'b0, ld_wbytes};
                if (in_tok_drain)      tok_wcnt <= tok_wcnt + 9'd1;
                else if (in_wb_drain)  wb_wcnt  <= wb_wcnt + 15'd1;
                else if (in_hs_drain)  hs_wcnt  <= hs_wcnt + 19'd1;
                else                   hz_wcnt  <= hz_wcnt + 19'd1;
            end

            case (state)
                // ---------------- startup ----------------
                S_IDLE: begin
                    if (cmd_valid && cmd_data == CMD_RUN) state <= S_HDR_PUSH;
                end
                S_HDR_PUSH: begin
                    if (seg_ready) begin
                        state <= S_HDR_DRAIN;
                        hcnt  <= 4'd0;
                    end
                end
                S_HDR_DRAIN: begin
                    if (bs_fire) begin
                        for (l = 0; l < 4; l = l + 1) begin
                            widx = {hcnt, 2'b00} + {4'b0, l[1:0]};
                            bw   = bs_data[32*l +: 32];
                            case (widx)
                                6'd2:  cfg_L   <= bw[3:0];
                                6'd3:  cfg_d   <= bw[15:0];
                                6'd4:  cfg_nh  <= bw[3:0];
                                6'd5:  cfg_dk  <= bw[9:0];
                                6'd6:  cfg_dr  <= bw[9:0];
                                6'd7:  cfg_dv  <= bw[9:0];
                                6'd8:  cfg_dc  <= bw[9:0];
                                6'd9:  cfg_kh  <= bw[3:0];
                                6'd10: cfg_dh  <= bw[9:0];
                                6'd12: cfg_E   <= bw[9:0];
                                6'd13: cfg_tk  <= bw[3:0];
                                6'd15: cfg_ff  <= bw[9:0];
                                6'd16: cfg_B   <= bw[3:0];
                                6'd17: cfg_V   <= bw[17:0];
                                6'd19: cfg_SL  <= bw[9:0];
                                6'd20: cfg_gs  <= bw[8:0];
                                6'd21: cfg_lt  <= bw[7:0];
                                6'd22: cfg_NT  <= bw[14:0];
                                6'd23: cfg_desc_addr   <= {4'b0, bw};
                                6'd24: cfg_tokens_addr <= {4'b0, bw};
                                6'd25: cfg_logits_addr <= {4'b0, bw};
                                6'd26: cfg_argmax_addr <= {4'b0, bw};
                                6'd27: cfg_status_addr <= {4'b0, bw};
                                6'd30: cfg_stride <= bw;
                                default: ; // reserved / unused words
                            endcase
                        end
                        if (hcnt == 4'd0 && bs_data[31:0] != HDR_MAGIC)
                            state <= S_ERR;
                        else if (hcnt == 4'd15) begin
                            // NT bound = DESC RAM depth (20480 words);
                            // full config needs 18638 entries
                            if (cfg_L > 4'd4 || cfg_V > 18'd163840
                                || cfg_SL > 10'd512
                                || cfg_NT > 15'd20480)
                                state <= S_ERR;
                            else
                                state <= S_DESC_PUSH;
                        end else
                            hcnt <= hcnt + 4'd1;
                    end
                end
                S_DESC_PUSH: begin
                    if (seg_ready) begin
                        state <= S_DESC_DRAIN;
                        dcnt  <= 15'd0;
                    end
                end
                S_DESC_DRAIN: begin
                    if (bs_fire) begin
                        dcnt <= dcnt + 15'd1;
`ifdef MSH_DEBUG
                        if (bs_shift != 4'd0)
                            $display("[seq] WARN: unaligned DESC beat");
`endif
                        if (bs_last) begin
                            state <= S_CACHE;
                            cc    <= 3'd0;
                        end
                    end
                end
                // cache emb.q/s/z + head.q/s/z descriptor addresses
                S_CACHE: begin
                    case (cc)
                        3'd0: begin desc_raddr <= 15'd0;        cc <= 3'd1; end
                        3'd1: begin desc_raddr <= 15'd1;        cc <= 3'd2; end
                        3'd2: begin
                            emb_q_base <= {4'b0, desc_rdata[63:32]};
                            desc_raddr <= 15'd2;
                            cc <= 3'd3;
                        end
                        3'd3: begin
                            emb_s_base <= {4'b0, desc_rdata[63:32]};
                            desc_raddr <= cfg_NT - 15'd3;
                            cc <= 3'd4;
                        end
                        3'd4: begin
                            emb_z_base <= {4'b0, desc_rdata[63:32]};
                            desc_raddr <= cfg_NT - 15'd2;
                            cc <= 3'd5;
                        end
                        3'd5: begin
                            head_q_addr <= {4'b0, desc_rdata[63:32]};
                            head_q_len  <= desc_rdata[95:64];
                            desc_raddr  <= cfg_NT - 15'd1;
                            cc <= 3'd6;
                        end
                        3'd6: begin
                            head_s_addr <= {4'b0, desc_rdata[63:32]};
                            head_s_len  <= desc_rdata[95:64];
                            cc <= 3'd7;
                        end
                        3'd7: begin
                            head_z_addr <= {4'b0, desc_rdata[63:32]};
                            head_z_len  <= desc_rdata[95:64];
                            state <= S_TOK_PUSH;
                        end
                        default: state <= S_ERR;
                    endcase
                end
                S_TOK_PUSH: begin
                    if (seg_ready) begin
                        state        <= S_TOK_DRAIN;
                        ld_fill      <= 5'd0;
                        ld_seen_last <= 1'b0;
                        tok_wcnt     <= 9'd0;
                    end
                end
                S_TOK_DRAIN: begin
                    if (ld_done) begin
                        state   <= S_WALK;
                        wst     <= 5'd0;
                        wli     <= 3'd0;
                        ws      <= 3'd0;
                        didx    <= 15'd3;
                        wb_off  <= 15'd0;
                        wb_wcnt <= 15'd0;
                    end
                end
                // canonical p16 walk (see SEQ_SPEC / seq_emulator.startup)
                S_WALK: begin
                    case (ws)
                        3'd0: begin
                            // skip steps need no DESC read
                            if (wst == 5'd3) begin
                                ix_mixer_v[15*(wli[1:0]) +: 15] <= didx;
                                didx <= didx
                                      + (cfg_lt[wli[2:0]] ? 15'd21 : 15'd27);
                                wst  <= 5'd4;
                            end else if (wst == 5'd13) begin
                                ix_router_v[15*(wli[1:0]) +: 15] <= didx;
                                didx <= didx + 15'd3;
                                wst  <= 5'd14;
                            end else if (wst == 5'd15) begin
                                ix_shared_v[15*(wli[1:0]) +: 15] <= didx;
                                ix_e0_v[15*(wli[1:0]) +: 15]     <= didx + 15'd9;
                                didx <= didx + 15'd9 + mE9[14:0];
                                if (({2'b0, wli} + 5'd1) < {1'b0, cfg_L}) begin
                                    wli <= wli + 3'd1;
                                    wst <= 5'd0;
                                end else begin
                                    wst <= 5'd16;
                                end
                            end else begin
                                desc_raddr <= didx;
                                ws         <= 3'd1;
                            end
                        end
                        3'd1: ws <= 3'd2;
                        3'd2: begin
                            walk_addr <= {4'b0, desc_rdata[63:32]};
                            walk_len  <= desc_rdata[95:64];
                            ws        <= 3'd3;
                        end
                        3'd3: begin
                            if (seg_ready) begin
                                ws           <= 3'd4;
                                ld_fill      <= 5'd0;
                                ld_seen_last <= 1'b0;
                            end
                        end
                        3'd4: begin
                            if (ld_done) begin
                                // record this tensor's WBUF offset
                                case (wst)
                                    5'd0:  wb_rattn_nw_v[15*(wli[1:0]) +: 15] <= wb_off;
                                    5'd1:  wb_rattn_pw_v[15*(wli[1:0]) +: 15] <= wb_off;
                                    5'd2:  wb_norm1_v[15*(wli[1:0]) +: 15]    <= wb_off;
                                    5'd4: begin
                                        if (cfg_lt[wli[2:0]])
                                            wb_knorm_v[15*(wli[1:0]) +: 15] <= wb_off;
                                        else
                                            wb_qconv_v[15*(wli[1:0]) +: 15] <= wb_off;
                                    end
                                    5'd5:  wb_kconv_v[15*(wli[1:0]) +: 15]  <= wb_off;
                                    5'd6:  wb_vconv_v[15*(wli[1:0]) +: 15]  <= wb_off;
                                    5'd7:  wb_A_v[15*(wli[1:0]) +: 15]      <= wb_off;
                                    5'd8:  wb_dtb_v[15*(wli[1:0]) +: 15]    <= wb_off;
                                    5'd9:  wb_onorm_v[15*(wli[1:0]) +: 15]  <= wb_off;
                                    5'd10: wb_rmlp_nw_v[15*(wli[1:0]) +: 15] <= wb_off;
                                    5'd11: wb_rmlp_pw_v[15*(wli[1:0]) +: 15] <= wb_off;
                                    5'd12: wb_norm2_v[15*(wli[1:0]) +: 15]  <= wb_off;
                                    5'd14: wb_bias_v[15*(wli[1:0]) +: 15]   <= wb_off;
                                    5'd16: wb_ro_nw <= wb_off;
                                    5'd17: wb_ro_pw <= wb_off;
                                    5'd18: wb_final <= wb_off;
                                    default: ;
                                endcase
                                wb_off <= wb_off + walk_words;
                                didx   <= didx + 15'd1;
                                ws     <= 3'd0;
                                case (wst)
                                    5'd4: begin
                                        if (cfg_lt[wli[2:0]]) wst <= 5'd10;
                                        else                  wst <= 5'd5;
                                    end
                                    5'd18: begin
                                        state   <= S_HS_PUSH;
                                        hs_wcnt <= 19'd0;
                                    end
                                    default: wst <= wst + 5'd1;
                                endcase
                            end
                        end
                        default: ws <= 3'd0;
                    endcase
                end
                S_HS_PUSH: begin
                    if (seg_ready) begin
                        state        <= S_HS_DRAIN;
                        ld_fill      <= 5'd0;
                        ld_seen_last <= 1'b0;
                    end
                end
                S_HS_DRAIN: begin
                    if (ld_done) begin
                        state   <= S_HZ_PUSH;
                        hz_wcnt <= 19'd0;
                    end
                end
                S_HZ_PUSH: begin
                    if (seg_ready) begin
                        state        <= S_HZ_DRAIN;
                        ld_fill      <= 5'd0;
                        ld_seen_last <= 1'b0;
                    end
                end
                S_HZ_DRAIN: begin
                    if (ld_done) begin
                        state <= S_CATT;
                        cs    <= 1'b0;
                        bs_it <= 5'd0;
                        bs_lo <= 18'd1;
                        bs_hi <= 18'h20000;
                    end
                end
                // c_att = round(2^16/sqrt(dqk)), c_dh = round(2^16/sqrt(dh))
                // exact integer binary search (no ties for ladder dims)
                S_CATT: begin
                    if (bs_it < 5'd18) begin
                        if (bs_prod <= 64'h0000_0004_0000_0000)
                            bs_lo <= bs_mid[17:0];
                        else
                            bs_hi <= bs_mid[17:0];
                        bs_it <= bs_it + 5'd1;
                    end else if (!cs) begin
                        c_att <= bs_lo[16:0];
                        cs    <= 1'b1;
                        bs_it <= 5'd0;
                        bs_lo <= 18'd1;
                        bs_hi <= 18'h20000;
                    end else begin
                        c_dh    <= bs_lo[16:0];
                        state   <= S_WCLR;
                        t       <= 10'd0;
                        lg_row  <= cfg_logits_addr;
                    end
                end
                // ---------------- per-token flow ----------------
                // wait for every engine to finish its reset clear sweep
                // (vec conv history, kda S, mla KV) before computing; the
                // sweeps would otherwise re-zero freshly stored state.
                S_WCLR: begin
                    if (vc_ready && kd_ready && ml_ready
                        && gv_gready && gv_dready)
                        state <= S_TSTART;
                end
                S_TSTART: begin
                    // cycle 1: tok_raddr driven (registered read);
                    // cycle 2: capture the token id
                    if (!ts) begin
                        ts <= 1'b1;
                    end else begin
                        tok_val <= tok_rdata[17:0];
                        ep      <= 2'd0;
                        ts      <= 1'b0;
                        state   <= S_EMB_PUSH;
                    end
                end
                S_EMB_PUSH: begin
                    if (seg_ready) begin
                        if (ep == 2'd2) state <= S_EMB_JOB;
                        else            ep    <= ep + 2'd1;
                    end
                end
                S_EMB_JOB: begin
                    if (gv_ready) begin
                        bs_owner <= 1'b1;
                        state    <= S_EMB_WAIT;
                    end
                end
                S_EMB_WAIT: begin
                    if (gv_done) begin
                        bs_owner <= 1'b0;
                        li       <= 3'd0;
                        blk_idx  <= 4'd0;
                        blkcnt   <= 4'd0;
                        st       <= ST_RATTN;
                        mx       <= 5'd0;
                        rs2      <= 2'd0;
                        ci       <= 4'd0;
                        hi       <= 4'd0;
                        ex_i     <= 4'd0;
                        ex       <= 4'd0;
                        state    <= S_LAY;
                    end
                end
                // ---------------- layer program ----------------
                S_LAY: begin
                    if (ex == 4'd0) begin
                        pf_state <= PF_IDLE;
                        if (dec_skip) begin
                            adv = 1'b1;
                        end else if (dec_kind == KD_GEMV) begin
                            if (dec_pre) begin
                                pl_qaddr <= head_q_addr;
                                pl_qlen  <= head_q_len;
                                pl_saddr <= 36'd0;
                                pl_slen  <= 32'd0;
                                pl_zaddr <= 36'd0;
                                pl_zlen  <= 32'd0;
                                ex       <= 4'd5;
                            end else if (hd_valid) begin
                                // descriptors already read by the
                                // prefetch: skip the ex=1..4 reads
                                pl_qaddr <= hd_qaddr;
                                pl_qlen  <= hd_qlen;
                                pl_saddr <= hd_saddr;
                                pl_slen  <= hd_slen;
                                pl_zaddr <= hd_zaddr;
                                pl_zlen  <= hd_zlen;
                                ex       <= 4'd5;
                            end else begin
                                desc_raddr <= dec_qidx;
                                ex         <= 4'd1;
                            end
                        end else begin
                            ex <= 4'd1;      // VEC / KDA / MLA: issue
                        end
                    end else if (dec_kind == KD_GEMV) begin
                        case (ex)
                            4'd1: begin
                                desc_raddr <= dec_qidx + 15'd1;
                                ex         <= 4'd2;
                            end
                            4'd2: begin
                                pl_qaddr   <= {4'b0, desc_rdata[63:32]};
                                pl_qlen    <= desc_rdata[95:64];
                                desc_raddr <= dec_qidx + 15'd2;
                                ex         <= 4'd3;
                            end
                            4'd3: begin
                                pl_saddr <= {4'b0, desc_rdata[63:32]};
                                pl_slen  <= desc_rdata[95:64];
                                ex       <= 4'd4;
                            end
                            4'd4: begin
                                pl_zaddr <= {4'b0, desc_rdata[63:32]};
                                pl_zlen  <= desc_rdata[95:64];
                                ex       <= 4'd5;
                            end
                            4'd5: begin
                                if (dec_nseg1)   ex <= 4'd7;
                                else if (pf_maskA[0] || seg_ready) ex <= 4'd6;
                            end
                            4'd6: if (pf_maskA[1] || seg_ready) ex <= 4'd7;
                            4'd7: if (pf_maskA[2] || seg_ready) ex <= 4'd8;
                            4'd8: begin
                                if (gv_ready && (hq_pushed || seg_ready)) begin
`ifdef MSH_DEBUG
                                $display("[seq] cyc=%0d GEMV mode=%0d q=%09x K=%0d N=%0d ng=%0d gsz=%0d s=%09x z=%09x R=%0d xb=%0d yb=%0d", dbg_cyc, gv_mode, gv_q_addr, gv_K, gv_N, gv_ng, gv_gsz, gv_s_addr, gv_z_addr, gv_R, gv_xbuf, gv_ybuf);
`endif
                                    bs_owner <= 1'b1;
                                    ex       <= 4'd9;
                                    hq_pushed <= hq_pushed
                                               || (push_hq && seg_ready);
                                    // level-B stock becomes level-A for
                                    // the job that starts next
                                    pf_maskA <= pf_maskB;
                                    pf_maskB <= 3'd0;
                                    haveA    <= haveB;
                                    haveB    <= 1'b0;
                                    hd_qaddr  <= hd2_qaddr;
                                    hd_qlen   <= hd2_qlen;
                                    hd_saddr  <= hd2_saddr;
                                    hd_slen   <= hd2_slen;
                                    hd_zaddr  <= hd2_zaddr;
                                    hd_zlen   <= hd2_zlen;
                                    hd_valid  <= hd2_valid;
                                    hd2_valid <= 1'b0;
                                end
                            end
                            4'd9: begin
                                // 2-deep prefetch: while waiting for
                                // gv_done, stock the next gemv job
                                // (level A) and the one after it
                                // (level B). Push states hold until
                                // seg_ready; already-stocked segments
                                // (mask bit set) are skipped so partial
                                // stocks resume without duplicates.
                                if (pf_state != PF_DONE) begin
                                    case (pf_state)
                                        PF_IDLE: begin
                                            if (pf_wantA || pf_wantB) begin
                                                pf_tgt     <= !pf_wantA;
                                                desc_raddr <= pf_wantA
                                                            ? nx_qidx
                                                            : nx2_qidx;
                                                pf_state   <= PF_Q;
                                            end else begin
                                                pf_state <= PF_DONE;
                                            end
                                        end
                                        PF_Q: begin
                                            desc_raddr <= pf_tqidx + 15'd1;
                                            pf_state   <= PF_S;
                                        end
                                        PF_S: begin
                                            pf_qaddr   <= {4'b0, desc_rdata[63:32]};
                                            pf_qlen    <= desc_rdata[95:64];
                                            desc_raddr <= pf_tqidx + 15'd2;
                                            pf_state   <= PF_Z;
                                        end
                                        PF_Z: begin
                                            pf_saddr <= {4'b0, desc_rdata[63:32]};
                                            pf_slen  <= desc_rdata[95:64];
                                            pf_state <= PF_PS;
                                        end
                                        PF_PS: begin
                                            pf_zaddr <= {4'b0, desc_rdata[63:32]};
                                            pf_zlen  <= desc_rdata[95:64];
                                            if (pf_cmask[0] || seg_ready) begin
                                                if (!pf_cmask[0]) begin
                                                    if (pf_tgt) pf_maskB[0] <= 1'b1;
                                                    else        pf_maskA[0] <= 1'b1;
                                                end
                                                pf_state <= PF_PZ;
                                            end
                                        end
                                        PF_PZ: begin
                                            // all three descriptors are
                                            // valid now: hand them over
                                            // so the prefetched job can
                                            // skip its ex=1..4 reads
                                            if (pf_tgt) begin
                                                hd2_qaddr <= pf_qaddr;
                                                hd2_qlen  <= pf_qlen;
                                                hd2_saddr <= pf_saddr;
                                                hd2_slen  <= pf_slen;
                                                hd2_zaddr <= pf_zaddr;
                                                hd2_zlen  <= pf_zlen;
                                                hd2_valid <= 1'b1;
                                            end else begin
                                                hd_qaddr <= pf_qaddr;
                                                hd_qlen  <= pf_qlen;
                                                hd_saddr <= pf_saddr;
                                                hd_slen  <= pf_slen;
                                                hd_zaddr <= pf_zaddr;
                                                hd_zlen  <= pf_zlen;
                                                hd_valid <= 1'b1;
                                            end
                                            if (pf_cmask[1] || seg_ready) begin
                                                if (!pf_cmask[1]) begin
                                                    if (pf_tgt) pf_maskB[1] <= 1'b1;
                                                    else        pf_maskA[1] <= 1'b1;
                                                end
                                                pf_state <= PF_PQ;
                                            end
                                        end
                                        PF_PQ: begin
                                            if (pf_cmask[2] || seg_ready) begin
                                                if (!pf_cmask[2]) begin
                                                    if (pf_tgt) pf_maskB[2] <= 1'b1;
                                                    else        pf_maskA[2] <= 1'b1;
                                                end
                                                if (pf_tgt) haveB <= 1'b1;
                                                else        haveA <= 1'b1;
                                                pf_state <= PF_IDLE;
                                            end
                                        end
                                        default: pf_state <= PF_DONE;
                                    endcase
                                end
                                if (gv_done) begin
                                    bs_owner <= 1'b0;
                                    if (st == ST_HEAD) begin
                                        // running argmax folds the final
                                        // emission beat one cycle after
                                        // y_done_r: wait one cycle (ex=10)
                                        ex <= 4'd10;
                                    end else begin
                                        adv = 1'b1;
                                        ex  <= 4'd0;
                                    end
                                end
                            end
                            4'd10: begin
                                // ST_HEAD only: latch the argmax one cycle
                                // after gv_done, once the final beat has
                                // been folded into the running argmax.
                                amx <= gv_am_idx;
                                adv = 1'b1;
                                ex  <= 4'd0;
                            end
                            default: ex <= 4'd0;
                        endcase
                    end else if (dec_kind == KD_VEC) begin
                        case (ex)
                            4'd1: if (vc_ready) begin
                                ex <= 4'd2;
`ifdef MSH_DEBUG
                                $display("[seq] cyc=%0d VEC code=%0d len=%0d s1=%0d s2=%0d dst=%0d wb=%0d aux=%08x t=%0d li=%0d",
                                         dbg_cyc, dec_code, dec_len, dec_s1, dec_s2,
                                         dec_dst, dec_wb, dec_aux, t, li);
`endif
                            end
                            4'd2: begin
                                if (vc_done) begin
                                    if (dec_code == OP_TOPK) begin
                                        res_cnt <= 4'd0;
                                        ex      <= 4'd3;
                                    end else begin
                                        adv = 1'b1;
                                        ex  <= 4'd0;
                                    end
                                end
                            end
                            4'd3: begin
                                if (vc_res_valid) begin
                                    eid_v[9*(res_cnt[2:0]) +: 9] <= vc_res_data[8:0];
                                    if (res_cnt + 4'd1 == {1'b0, cfg_tk}) begin
                                        adv = 1'b1;
                                        ex  <= 4'd0;
                                    end else
                                        res_cnt <= res_cnt + 4'd1;
                                end
                            end
                            default: ex <= 4'd0;
                        endcase
                    end else begin
                        // KDA / MLA jobs
                        case (ex)
                            4'd1: begin
                                if ((dec_kind == KD_KDA) ? kd_ready
                                                         : ml_ready) begin
                                    ex <= 4'd2;
`ifdef MSH_DEBUG
                                    if (dec_kind == KD_KDA)
                                        $display("[seq] cyc=%0d KDA li=%0d t=%0d", dbg_cyc, kd_layer, t);
                                    else
                                        $display("[seq] cyc=%0d MLA pos=%0d t=%0d", dbg_cyc, ml_pos, t);
`endif
                                end
                            end
                            4'd2: begin
                                if ((dec_kind == KD_KDA) ? kd_done
                                                         : ml_done) begin
                                    adv = 1'b1;
                                    ex  <= 4'd0;
                                end
                            end
                            default: ex <= 4'd0;
                        endcase
                    end

                    // ---- advance the layer program ----
                    if (adv) begin
                        case (st)
                            ST_RATTN: begin
                                if (rs2 == 2'd0) rs2 <= 2'd1;
                                else if (rs2 == 2'd1) begin
                                    if (ci + 4'd1 < rm_ncand) begin
                                        ci  <= ci + 4'd1;
                                        rs2 <= 2'd0;
                                    end else rs2 <= 2'd2;
                                end else begin
                                    rs2 <= 2'd0;
                                    ci  <= 4'd0;
                                    st  <= ST_NORM1;
                                end
                            end
                            ST_RMLP: begin
                                if (rs2 == 2'd0) rs2 <= 2'd1;
                                else if (rs2 == 2'd1) begin
                                    if (ci + 4'd1 < rm_ncand) begin
                                        ci  <= ci + 4'd1;
                                        rs2 <= 2'd0;
                                    end else rs2 <= 2'd2;
                                end else begin
                                    rs2 <= 2'd0;
                                    ci  <= 4'd0;
                                    st  <= ST_NORM2;
                                end
                            end
                            ST_RMOUT: begin
                                if (rs2 == 2'd0) rs2 <= 2'd1;
                                else if (rs2 == 2'd1) begin
                                    if (ci + 4'd1 < rm_ncand) begin
                                        ci  <= ci + 4'd1;
                                        rs2 <= 2'd0;
                                    end else rs2 <= 2'd2;
                                end else begin
                                    rs2 <= 2'd0;
                                    ci  <= 4'd0;
                                    st  <= ST_FNORM;
                                end
                            end
                            ST_NORM1: begin
                                st <= ST_MIX;
                                mx <= 5'd0;
                                hi <= 4'd0;
                            end
                            ST_MIX: begin
                                if (is_F) begin
                                    if (mx == 5'd8) st <= ST_PADD;
                                    else            mx <= mx + 5'd1;
                                end else begin
                                    if (mx == 5'd15 || mx == 5'd16
                                        || mx == 5'd18) begin
                                        if (hi + 4'd1 < cfg_kh)
                                            hi <= hi + 4'd1;
                                        else begin
                                            hi <= 4'd0;
                                            mx <= mx + 5'd1;
                                        end
                                    end else if (mx == 5'd20) st <= ST_PADD;
                                    else                      mx <= mx + 5'd1;
                                end
                            end
                            ST_PADD:  st <= ST_RMLP;
                            ST_NORM2: st <= ST_ROUT;
                            ST_ROUT:  st <= ST_SIGR;
                            ST_SIGR:  st <= ST_TOPK;
                            ST_TOPK:  st <= ST_SHG;
                            ST_SHG:   st <= ST_SHU;
                            ST_SHU:   st <= ST_SILU;
                            ST_SILU:  st <= ST_MULZ;
                            ST_MULZ:  st <= ST_SHD;
                            ST_SHD: begin
                                st   <= ST_EXG;
                                ex_i <= 4'd0;
                            end
                            ST_EXG:   st <= ST_EXU;
                            ST_EXU:   st <= ST_SILUE;
                            ST_SILUE: st <= ST_MULZE;
                            ST_MULZE: st <= ST_EXD;
                            ST_EXD:   st <= ST_MACW;
                            ST_MACW: begin
                                if (ex_i + 4'd1 < cfg_tk) begin
                                    ex_i <= ex_i + 4'd1;
                                    st   <= ST_EXG;
                                end else begin
                                    ex_i <= 4'd0;
                                    st   <= ST_FADD;
                                end
                            end
                            ST_FADD: state <= S_LFIN;
                            ST_FNORM: st <= ST_HEAD;
                            ST_HEAD: begin
                                state   <= S_LGWR;
                                lg_beat <= 16'd0;
                                lw      <= 1'b0;
                            end
                            default: st <= ST_RATTN;
                        endcase
                    end
                end
                S_LFIN: begin
                    li     <= li + 3'd1;
                    if (boundary) blk_idx <= blk_idx + 4'd1;
                    blkcnt <= (blkcnt + 4'd1 == cfg_B) ? 4'd0
                                                       : blkcnt + 4'd1;
                    if (({2'b0, li} + 5'd1) < {1'b0, cfg_L}) begin
                        st    <= ST_RATTN;
                        state <= S_LAY;
                    end else begin
                        st    <= ST_RMOUT;
                        rs2   <= 2'd0;
                        ci    <= 4'd0;
                        state <= S_LAY;
                    end
                end
                // ---------------- write-back ----------------
                S_LGWR: begin
                    if (!lw) begin
                        lw <= 1'b1;        // lg_raddr driven; data next cycle
                    end else if (wr_fire) begin
                        // lw stays set: lg_raddr pre-advances (see above)
                        if (lg_beat + 16'd1 == cfg_V[17:2]) begin
                            lw    <= 1'b0;
                            state <= S_AMWR;
                        end else
                            lg_beat <= lg_beat + 16'd1;
                    end
                end
                S_AMWR: begin
                    if (wr_fire) state <= S_TNEXT;
                end
                S_TNEXT: begin
                    t      <= t + 10'd1;
                    lg_row <= lg_row + {4'b0, cfg_stride};
                    if (t + 10'd1 < cfg_SL) state <= S_TSTART;
                    else                    state <= S_STATUS;
                end
                S_STATUS: begin
                    if (wr_fire) state <= S_DONE;
                end
                S_DONE: begin
                    if (rsp_ready) state <= S_IDLE;
                end
                S_ERR: state <= S_ERR;
                default: state <= S_IDLE;
            endcase
            /* verilator lint_on BLKSEQ */
        end
    end

endmodule

`default_nettype wire
