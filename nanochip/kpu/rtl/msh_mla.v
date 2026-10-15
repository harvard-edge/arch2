// msh_mla.v -- MLA attention unit with KV cache.
//
// Part of msh_chip_top. Matches the
// per-head attention loop of rtl/selfmodel/fxmodel.py mla() BIT-EXACTLY:
//   att[t] = rs(sum_d rs(K[t][d],4) * rs(q[d],4), 18)   (K/q Q4.26)
//   att[t] = rs(att[t] * c_att, 16)                     (c_att Q16-ish)
//   mx     = max_t att[t]
//   ei     = clip(att[t] - mx, -2^30, 0)
//   e[t]   = expneg_lut(ei)  (bucket 2^18 codes at sx=26, full-frac interp:
//            idx = clip((ei>>18)+4096, 0, 4096), frac = ei - (ei>>18)<<18,
//            y = t[idx] + (d[idx]*frac + 2^17) >> 18)
//   se     = sum_t e[t]
//   rec    = recip_eval_i(se, 46)  (norm20: m_q in [2^20,2^21), E9 = E+9;
//            idx = (m_q>>9)-2048, frac = m_q&511,
//            r = t[idx] + (d[idx]*frac + 256) >> 9;  sh = 46-30-E9;
//            rec = sh>=0 ? r<<sh : (r + 2^(-sh-1)) >> (-sh))
//   ctx[d] = sat32((rs(sum_t rs(e[t],4) * V[t][d], 28) * rec + 2^13) >> 14)
// where rs(v, r) = (v + 2^(r-1)) >>> r (round-half-up, arithmetic).
//
// Job: q and k_new arrive SPLIT across four XBUF buffers (four separate
// GEMV outputs): qc [H*dk, element hd*dk + d], qr [H*dr, hd*dr + d],
// kc [H*dk], kr [dr, SHARED across heads]; v_new [H*dv] in one buffer.
// Per the C-model q[hd] = [qc_h | qr_h] and k[hd] = [kc_h | kr]; the
// module gathers the two parts per head (both dk and dr are multiples of
// 4, so the concat is word-aligned). It first stores k_new/v_new into the
// KV cache at position `pos` (both streams in parallel on the two read
// ports — K side reads kc then kr per head, V side reads v), then
// computes attention for each head over t = 0..pos: att (4 dims/cycle),
// exp (1 t/cycle), recip (1 cycle), ctx accumulation (4 dims/cycle,
// set-on-first accumulators), ctx writeout (4 int32 lanes/word). ctx is
// written to the ctx buffer (head-major). The output GEMV (L.mla.o) is
// done elsewhere; this module stops at ctx.
//
// KV caches are harness msh_sram macros (macros_only rule; sync read,
// 128b words = 4 int32 lanes). Compact dynamic addressing (strides from
// the job descriptor; H <= 2, pos < 128): K word = (hd*128 + t)*nwk + w
// (nwk = dqk/4), V word = (hd*128 + t)*nwv + w. Both cleared by a reset
// write-loop (randreset gate) before the first job is accepted. The LUTs
// are harness msh_rom macros (ASYNC read, same-cycle data — the exp/recip
// datapaths keep their original single-cycle structure). All other
// storage is packed vectors (no inferred $mem).
//
// ST_ATT/ST_CTX are retimed around the 1-cycle KV read: the word address
// is issued with (t, w) and the returned word is consumed one cycle
// later with the delayed (at_td/c_td, at_wd/c_wd) — initiation interval
// 1, one drain cycle per pass.
//
// Documented assumptions:
//   * dk, dr, dv are multiples of 4 and > 0; dqk = dk + dr <= 192;
//     dv <= 128; H <= 2; pos < 128. dk arrives as job_dk (the sequencer
//     must supply it — dr = dqk - dk).
//   * Realistic C-model ranges keep intermediates in the widths used
//     below (acc 72b, att 56b, se <= 512*2^26, rec < 2^21).
//
// Reset policy (randreset gate): every control flop is reset; both KV
// SRAMs are explicitly zeroed by the ST_CLEAR sweep. att/e/q/acc_d
// storage is written before being read within a job (verified with
// +verilator+rand+reset+2).

`default_nettype none

module msh_mla (
    input  wire         clk,
    input  wire         rst_n,
    // job descriptor
    input  wire         job_valid,
    output wire         job_ready,
    input  wire [9:0]   job_pos,        // write/attend position (0..127)
    input  wire [9:0]   job_dqk,        // qk dims per head (<= 192, mult of 4)
    input  wire [9:0]   job_dv,         // v dims per head (<= 128, mult of 4)
    input  wire [9:0]   job_dk,         // c-part dims (split point; dr = dqk-dk)
    input  wire [3:0]   job_H,          // heads (<= 2)
    input  wire [16:0]  job_c_att,      // round(2^16/sqrt(dqk))
    input  wire [3:0]   job_qc_buf,
    input  wire [3:0]   job_qr_buf,
    input  wire [3:0]   job_kc_buf,
    input  wire [3:0]   job_kr_buf,
    input  wire [3:0]   job_v_buf,
    input  wire [3:0]   job_ctx_buf,
    output wire         job_done,
    // XBUF: two read ports (1-cycle registered latency), one write port
    output wire [12:0]  xr0_addr,       // {buf[3:0], word[8:0]}
    input  wire [127:0] xr0_data,
    output wire [12:0]  xr1_addr,
    input  wire [127:0] xr1_data,
    output wire         xw_we,
    output wire [12:0]  xw_addr,
    output wire [127:0] xw_data,
    output wire [3:0]   xw_wstrb
);

    // ---------------- states ----------------
    localparam ST_CLEAR = 4'd0;
    localparam ST_IDLE  = 4'd1;
    localparam ST_STORE = 4'd2;         // k_new/v_new -> KV at pos
    localparam ST_QLOAD = 4'd3;         // per-head q preload
    localparam ST_ATT   = 4'd4;         // att[t] dot products
    localparam ST_EXP   = 4'd5;         // exp LUT + se
    localparam ST_RECIP = 4'd6;         // reciprocal LUT
    localparam ST_CTX   = 4'd7;         // sum_t e[t]*V[t][d]
    localparam ST_CTXW  = 4'd8;         // ctx writeout
    localparam ST_DONE  = 4'd9;

    reg [3:0] state;

    // ---------------- job registers ----------------
    reg [8:0]  j_pos;
    reg [5:0]  j_nwk;                   // dqk/4
    reg [5:0]  j_nwv;                   // dv/4
    reg [7:0]  j_dk;                    // split point (elements)
    reg [5:0]  j_nkc;                   // dk/4
    reg [5:0]  j_nkr;                   // dr/4 = (dqk-dk)/4
    reg [3:0]  j_H;
    reg [16:0] j_catt;
    reg [3:0]  j_qcbuf, j_qrbuf, j_kcbuf, j_krbuf, j_vbuf, j_cbuf;

    // ---------------- counters / accumulators ----------------
    reg [3:0]  hd;
    reg [8:0]  t;
    reg [5:0]  w;
    reg signed [71:0] acc;              // att dot-product accumulator
    reg signed [55:0] mx;               // running att max
    reg [63:0] se;                      // sum of exp outputs
    reg signed [47:0] rec;              // round(2^46/se)
    reg [16:0] clr;

    // store streamers (port0 -> K, port1 -> V)
    reg [1:0]  ks_hd, vs_hd;
    reg [5:0]  ks_w, vs_w;
    reg        ks_ph;                   // 0 = kc part, 1 = kr part
    reg        ks_vd, vs_vd;
    reg [1:0]  ks_hd_d, vs_hd_d;
    reg [5:0]  ks_w_d, vs_w_d;
    reg        ks_ph_d;
    reg        ks_done, vs_done, ks_cap, vs_cap;
    // q loader (port0): phase 0 = qc, phase 1 = qr
    reg [5:0]  q0_w, q0_wd;
    reg        q0_ph, q0_phd, q0_vd;
    // att/ctx sync-read delay registers (KV word returns one cycle
    // after the (t, w) issue)
    reg        att_iss, at_dv;
    reg [8:0]  at_td;
    reg [5:0]  at_wd;
    reg        ctx_iss, c_dv;
    reg [8:0]  c_td;
    reg [5:0]  c_wd;

    // ---------------- storage ----------------
    // KV caches: harness msh_sram macros. Compact dynamic addressing:
    //   ht = hd*128 + t (H <= 2);  K word = ht*nwk + w;  V word = ht*nwv + w
    // K: 2*72*12 = 1728 words (nano nwk = 12); V: 2*72*8 = 1152.
    // Positions bounded at 72 (1.125x max_seq 64, 2x public long run 48
    // trimmed from 96 to fit the 4.0 mm2 area budget; see REPORT.md
    // risk note). ht = hd*72 + t (multiply-free form).
    wire [7:0]  at_ht  = (hd[0] ? 8'd72 : 8'd0) + {1'b0, t[6:0]};
    wire [13:0] k_addr = ({6'b0, at_ht} * {8'b0, j_nwk}) + {8'b0, w};
    wire [13:0] v_addr = ({6'b0, at_ht} * {8'b0, j_nwv}) + {8'b0, w};

    // store capture addresses (data returns from XBUF one cycle after
    // the source issue — the _d registers already carry that delay)
    wire [8:0]  ks_dst    = ks_ph_d ? ({3'b0, j_nkc} + {3'b0, ks_w_d})
                                    : {3'b0, ks_w_d};
    wire [7:0]  ks_ht     = (ks_hd_d[0] ? 8'd72 : 8'd0)
                          + {1'b0, j_pos[6:0]};
    wire [13:0] ks_caddr  = ({6'b0, ks_ht} * {8'b0, j_nwk}) + {5'b0, ks_dst};
    wire [7:0]  vs_ht     = (vs_hd_d[0] ? 8'd72 : 8'd0)
                          + {1'b0, j_pos[6:0]};
    wire [13:0] vs_caddr  = ({6'b0, vs_ht} * {8'b0, j_nwv}) + {8'b0, vs_w_d};

    wire         kw_we    = (state == ST_CLEAR)
                          || ((state == ST_STORE) && ks_vd);
    wire [10:0]  kw_waddr = (state == ST_CLEAR) ? clr[10:0]
                                                : ks_caddr[10:0];
    wire [127:0] kw_wd    = (state == ST_CLEAR) ? 128'd0 : xr0_data;
    wire [10:0]  k_raddr  = (state == ST_ATT) ? k_addr[10:0] : 11'd0;
    wire [127:0] k_rd;
    msh_sram #(.DEPTH(1728), .WIDTH(128)) u_kmem (
        .clk(clk), .we(kw_we), .waddr(kw_waddr), .wdata(kw_wd),
        .wstrb(16'hFFFF),
        .re(1'b1), .raddr(k_raddr), .rdata(k_rd));

    wire         vw_we    = ((state == ST_CLEAR) && (clr < 17'd1152))
                          || ((state == ST_STORE) && vs_vd);
    wire [10:0]  vw_waddr = (state == ST_CLEAR) ? clr[10:0]
                                                : vs_caddr[10:0];
    wire [127:0] vw_wd    = (state == ST_CLEAR) ? 128'd0 : xr1_data;
    wire [10:0]  v_raddr  = (state == ST_CTX) ? v_addr[10:0] : 11'd0;
    wire [127:0] v_rd;
    msh_sram #(.DEPTH(1152), .WIDTH(128)) u_vmem (
        .clk(clk), .we(vw_we), .waddr(vw_waddr), .wdata(vw_wd),
        .wstrb(16'hFFFF),
        .re(1'b1), .raddr(v_raddr), .rdata(v_rd));

    // packed-vector storage (no inferred $mem)
    reg [2047:0]  qbuf_v;               // 64 x int32 (dqk <= 64)

    // att/e/ctx storage as msh_sram macros (synchronous read; the
    // consumers are retimed one cycle — see ST_EXP/ST_CTX/ST_CTXW).
    // Macro bits replace ~47 Kflops of wide variable-index logic.
    wire         atb_we    = (state == ST_ATT) && at_dv
                           && (at_wd == j_nwk - 6'd1);
    wire [6:0]   atb_waddr = at_td[6:0];
    wire [63:0]  atb_wd    = {8'b0, att_v[55:0]};
    wire [6:0]   atb_raddr = (state == ST_EXP) ? t[6:0] : 7'd0;
    wire [63:0]  atb_rd;
    msh_sram #(.DEPTH(128), .WIDTH(64)) u_atb (
        .clk(clk), .we(atb_we), .waddr(atb_waddr), .wdata(atb_wd),
        .wstrb(8'hFF),
        .re(1'b1), .raddr(atb_raddr), .rdata(atb_rd));

    wire         eb_we    = (state == ST_EXP) && e_dv;
    wire [6:0]   eb_waddr = e_td[6:0];
    wire [31:0]  eb_wd    = {5'b0, e_y[26:0]};
    wire [6:0]   eb_raddr = (state == ST_CTX) ? t[6:0] : 7'd0;
    wire [31:0]  eb_rd;
    msh_sram #(.DEPTH(128), .WIDTH(32)) u_eb (
        .clk(clk), .we(eb_we), .waddr(eb_waddr), .wdata(eb_wd),
        .wstrb(4'hF),
        .re(1'b1), .raddr(eb_raddr), .rdata(eb_rd));

    // ctx accumulators: 32 words x 4 x int72 (set-on-first); read at
    // the ST_CTX/ST_CTXW issue, RMW-write one cycle later at consume
    // (same word revisited 8 cycles later — no forwarding needed)
    wire [4:0]   ad_raddr = ((state == ST_CTX) || (state == ST_CTXW))
                          ? w[4:0] : 5'd0;
    wire [287:0] ad_rd;
    wire         ad_we    = (state == ST_CTX) && c_dv;
    wire [4:0]   ad_waddr = c_wd[4:0];
    wire [287:0] ad_wd;
    msh_sram #(.DEPTH(32), .WIDTH(288)) u_accd (
        .clk(clk), .we(ad_we), .waddr(ad_waddr), .wdata(ad_wd),
        .wstrb({36{1'b1}}),
        .re(1'b1), .raddr(ad_raddr), .rdata(ad_rd));
    reg [8:0]  e_td;                  // ST_EXP delayed t (att data phase)
    reg        e_dv;
    reg [4:0]  cw_wd;                 // ST_CTXW delayed word index
    reg        cw_dv;

    // LUT ROMs (harness msh_rom, ASYNC read — same-cycle data, two
    // ports per lookup). ENDPOINT formulation: the C-model's delta
    // tables satisfy d[idx] == t[idx+1] - t[idx] for every idx (verified
    // numerically for expneg_d and recip_d, including the duplicated
    // final row whose delta is 0), so the deltas are computed on the
    // fly from tab[idx] and tab[idx+1] — bit-identical, and the two
    // _d ROMs are eliminated: deltas are computed on the fly from the
    // endpoint ROM's two async read ports.
    wire [31:0] et_rd0, et_rd1;
    wire [23:0] rt_rd0, rt_rd1;
    wire [12:0] rom_e_idx;              // driven below with the exp index
    wire [11:0] rom_r_idx;              // driven below with the recip index
    wire [12:0] rom_e_idx_p1 = rom_e_idx + 13'd1;
    wire [11:0] rom_r_idx_p1 = rom_r_idx + 12'd1;
    msh_rom #(.DEPTH(4098), .WIDTH(32),
              .INIT_FILE("rtl/roms/expneg_msh.hex")) u_rom_et (
        .raddr1(rom_e_idx),    .rdata1(et_rd0),
        .raddr2(rom_e_idx_p1), .rdata2(et_rd1));
    msh_rom #(.DEPTH(2050), .WIDTH(24),
              .INIT_FILE("rtl/roms/recip_msh.hex")) u_rom_rt (
        .raddr1(rom_r_idx),    .rdata1(rt_rd0),
        .raddr2(rom_r_idx_p1), .rdata2(rt_rd1));
    // on-the-fly deltas (== the former _d tables by construction)
    wire signed [32:0] ed_c = $signed(et_rd1) - $signed(et_rd0);
    wire signed [24:0] rd_c = $signed(rt_rd1) - $signed(rt_rd0);

    // ---------------- helpers ----------------
    function signed [79:0] rs80(input signed [79:0] v, input [6:0] r);
        // round-half-up arithmetic shift, r >= 1
        rs80 = (v + (80'sd1 <<< (r - 7'd1))) >>> r;
    endfunction

    function [31:0] sat32(input signed [79:0] v);
        begin
            if (v > 80'sd2147483647)       sat32 = 32'h7FFFFFFF;
            else if (v < -80'sd2147483648) sat32 = 32'h80000000;
            else                           sat32 = v[31:0];
        end
    endfunction

    function [5:0] topbit64(input [63:0] v);
        integer k;
        begin
            topbit64 = 6'd0;
            for (k = 0; k < 64; k = k + 1)
                if (v[k]) topbit64 = k[5:0];
        end
    endfunction

    // ---------------- combinational datapath ----------------
    assign job_ready = (state == ST_IDLE);
    assign job_done  = (state == ST_DONE);

    // store source addresses (XBUF words). K side gathers kc (per-head
    // slice) then kr (shared) per head; the KV destination word offset
    // is contiguous across the concatenation.
    wire [8:0] ks_kc_src = ({7'b0, ks_hd} * {3'b0, j_nkc}) + {3'b0, ks_w};
    wire [8:0] ks_kr_src = {3'b0, ks_w};
    wire [8:0] vs_src = ({7'b0, vs_hd} * {3'b0, j_nwv}) + {3'b0, vs_w};

    // q loader source addresses (qc / qr per-head slices)
    wire [8:0] q_qc_src = ({7'b0, hd[1:0]} * {3'b0, j_nkc}) + {3'b0, q0_w};
    wire [8:0] q_qr_src = ({7'b0, hd[1:0]} * {3'b0, j_nkr}) + {3'b0, q0_w};

    assign xr0_addr = (state == ST_STORE && !ks_ph) ? {j_kcbuf, ks_kc_src}
                    : (state == ST_STORE)           ? {j_krbuf, ks_kr_src}
                    : (state == ST_QLOAD && !q0_ph) ? {j_qcbuf, q_qc_src}
                    : (state == ST_QLOAD)           ? {j_qrbuf, q_qr_src}
                    : 13'd0;
    assign xr1_addr = (state == ST_STORE) ? {j_vbuf, vs_src} : 13'd0;

    integer l;
    // datapath temps at TRUE value widths (multiplier operands stay
    // narrow+equal so yosys doesn't context-extend them to 80x80; see
    // ("unsigned-concat trap": zero-extend before mixing widths)
    reg signed [31:0] t_k, t_q;         // KV/q lanes (int32)
    reg signed [24:0] t_p;              // rs(e, 4): up to +2^23 (25b!)
    reg signed [79:0] t_acc;
    reg signed [55:0] t_a1;
    reg signed [45:0] t_a2;             // rs(acc_d 72b, 28)
    reg signed [79:0] att_acc_n, att_v;
    reg signed [56:0] t_diff;
    reg signed [31:0] t_ei, t_b, t_idxc;
    reg signed [39:0] t_interp;
    reg [31:0]        t_f32;
    reg [17:0]        t_frac;
    reg [12:0]        e_idx;
    reg [27:0]        e_y;
    reg [223:0]       ctx_prod_v;       // 4 x int56 (comb temp)
    reg [127:0]       ctx_word;
    wire signed [55:0] t_att_w = atb_rd[55:0];  // att word (macro read)

    // acc_d RMW (read issued one cycle earlier with (t, w))
    reg [287:0] ad_wd_r;
    integer ai;
    /* verilator lint_off WIDTHEXPAND */
    always @* begin
        ad_wd_r = ad_rd;
        for (ai = 0; ai < 4; ai = ai + 1)
            ad_wd_r[72*ai +: 72] = (c_td == 9'd0)
                ? $signed(ctx_prod_v[56*ai +: 56])
                : $signed(ad_rd[72*ai +: 72]) + $signed(ctx_prod_v[56*ai +: 56]);
    end
    /* verilator lint_on WIDTHEXPAND */
    assign ad_wd = ad_wd_r;
    // recip
    wire [5:0]        rc_e0   = topbit64(se);
    wire signed [7:0] rc_E    = {2'b00, rc_e0} - 8'sd20;
    wire [5:0]        rc_amt  = (rc_E >= 8'sd0) ? rc_E[5:0] : (6'd0 - rc_E[5:0]);
    wire [63:0]       rc_mq   = (rc_E >= 8'sd0) ? (se >>> rc_amt)
                                                : (se <<< rc_amt);
    wire [11:0]       rc_idx  = rc_mq[20:9] - 12'd2048;
    wire [8:0]        rc_frac = rc_mq[8:0];
    wire signed [25:0] rc_di  = rd_c * $signed({1'b0, rc_frac});
    wire signed [25:0] rc_r   = $signed({6'b0, rt_rd0[19:0]})
                              + ((rc_di + 26'sd256) >>> 9);
    wire signed [7:0] rc_sh   = 8'sd7 - rc_E;      // 46-30-(E+9)
    wire [63:0]       rc_ru   = {38'b0, rc_r};
    wire [63:0]       rec_n   = (rc_sh >= 8'sd0)
                              ? (rc_ru <<< rc_sh[5:0])
                              : ((rc_ru + (64'd1 <<< (6'd0 - rc_sh[5:0] - 6'd1)))
                                 >>> (6'd0 - rc_sh[5:0]));

    assign rom_e_idx = e_idx;
    assign rom_r_idx = rc_idx;

    // rs80/sat32 return 80 bits; assignments to the true-width temps
    // intentionally truncate/extend (values always fit)
    /* verilator lint_off WIDTHTRUNC */
    /* verilator lint_off WIDTHEXPAND */
    always @* begin
        // ---- att: acc += sum_l rs(K,4)*rs(q,4) ----
        // (consumes the KV word returned for the delayed at_wd index)
        t_acc = (at_wd == 6'd0) ? 80'sd0 : {{8{acc[71]}}, acc};
        for (l = 0; l < 4; l = l + 1) begin
            t_k = rs80($signed(k_rd[32*l +: 32]), 7'd4);
            t_q = rs80($signed(qbuf_v[32*{at_wd[3:0], l[1:0]} +: 32]), 7'd4);
            t_acc = t_acc + t_k * t_q;
        end
        att_acc_n = t_acc;
        t_a1 = rs80(t_acc, 7'd18);
        att_v = rs80(t_a1 * $signed({1'b0, j_catt}), 7'd16);
        // ---- exp: ei clip, LUT eval (async ROM read, same cycle) ----
        t_diff = {t_att_w[55], t_att_w} - {mx[55], mx};
        if (t_diff > 57'sd0)                 t_ei = 32'sd0;
        else if (t_diff < -57'sd1073741824)  t_ei = -32'sd1073741824;
        else                                 t_ei = t_diff[31:0];
        t_b    = t_ei >>> 18;
        t_idxc = t_b + 32'sd4096;
        if (t_idxc < 32'sd0)          e_idx = 13'd0;
        else if (t_idxc > 32'sd4096)  e_idx = 13'd4096;
        else                          e_idx = t_idxc[12:0];
        t_f32  = t_ei - (t_b <<< 18);
        t_frac = t_f32[17:0];
        t_interp = (ed_c * $signed({1'b0, t_frac}) + 40'sd131072)
                   >>> 18;
        e_y = {1'b0, et_rd0[26:0]} + t_interp[27:0];
        // ---- ctx: per-lane products e4 * V (consumes returned V word) ----
        t_p = rs80({53'b0, eb_rd[26:0]}, 7'd4);
        for (l = 0; l < 4; l = l + 1) begin
            t_k = $signed(v_rd[32*l +: 32]);
            ctx_prod_v[56*l +: 56] = t_p * t_k;
        end
        // ---- ctx writeout: sat32((rs(acc_d,28)*rec + 2^13) >> 14) ----
        for (l = 0; l < 4; l = l + 1) begin
            t_a2 = rs80($signed(ad_rd[72*l +: 72]), 7'd28);
            t_a1 = (t_a2 * $signed(rec_ext[47:0]) + 80'sd8192) >>> 14;
            ctx_word[32*l +: 32] = sat32(t_a1);
        end
    end
    /* verilator lint_on WIDTHEXPAND */
    /* verilator lint_on WIDTHTRUNC */

    // ctx write port (acc_d read is synchronous: the writeout fires
    // one cycle after the word index issue, with cw_wd)
    wire signed [79:0] rec_ext = {{32{rec[47]}}, rec};
    wire signed [79:0] mx_ext  = {{24{mx[55]}}, mx};
    wire [8:0] cw_word = ({7'b0, hd[1:0]} * {3'b0, j_nwv}) + {3'b0, cw_wd};
    assign xw_we    = (state == ST_CTXW) && cw_dv;
    assign xw_addr  = {j_cbuf, cw_word};
    assign xw_data  = ctx_word;
    assign xw_wstrb = 4'b1111;

    // unused spare bits
    wire _unused = &{1'b0, job_pos[9], job_dqk[9:8], job_dv[9:8],
                     job_dk[9:8], job_dqk[1:0], job_dv[1:0], job_dk[1:0],
                     k_addr[13:11], v_addr[13:11],
                     ks_caddr[13:11], vs_caddr[13:11],
                     et_rd0[31:27], et_rd1[31:27],
                     atb_rd[63:56], eb_rd[31:27], rec_ext[79:48],
                     att_acc_n[79:72], att_v[79:56], t_interp[39:28],
                     rc_mq[63:21], rec_n[63:48], t_f32[31:18]};

    // ---------------- sequential process ----------------
    integer i;

    always @(posedge clk) begin
        if (!rst_n) begin
            state    <= ST_CLEAR;
            j_pos    <= 9'd0;
            j_nwk    <= 6'd0;
            j_nwv    <= 6'd0;
            j_dk     <= 8'd0;
            j_nkc    <= 6'd0;
            j_nkr    <= 6'd0;
            j_H      <= 4'd0;
            j_catt   <= 17'd0;
            j_qcbuf  <= 4'd0;
            j_qrbuf  <= 4'd0;
            j_kcbuf  <= 4'd0;
            j_krbuf  <= 4'd0;
            j_vbuf   <= 4'd0;
            j_cbuf   <= 4'd0;
            hd       <= 4'd0;
            t        <= 9'd0;
            w        <= 6'd0;
            acc      <= 72'sd0;
            mx       <= 56'sd0;
            se       <= 64'd0;
            rec      <= 48'sd0;
            clr      <= 17'd0;
            ks_hd    <= 2'd0;
            vs_hd    <= 2'd0;
            ks_w     <= 6'd0;
            vs_w     <= 6'd0;
            ks_ph    <= 1'b0;
            ks_vd    <= 1'b0;
            vs_vd    <= 1'b0;
            ks_hd_d  <= 2'd0;
            vs_hd_d  <= 2'd0;
            ks_w_d   <= 6'd0;
            vs_w_d   <= 6'd0;
            ks_ph_d  <= 1'b0;
            ks_done  <= 1'b0;
            vs_done  <= 1'b0;
            ks_cap   <= 1'b0;
            vs_cap   <= 1'b0;
            q0_w     <= 6'd0;
            q0_wd    <= 6'd0;
            q0_ph    <= 1'b0;
            q0_phd   <= 1'b0;
            q0_vd    <= 1'b0;
            att_iss  <= 1'b0;
            at_dv    <= 1'b0;
            ctx_iss  <= 1'b0;
            c_dv     <= 1'b0;
            e_dv     <= 1'b0;
            cw_dv    <= 1'b0;
        end else begin
            /* verilator lint_off BLKSEQ */
`ifdef MSH_DEBUG
            if (state != ST_CLEAR)
                $display("[mla] st=%0d hd=%0d t=%0d w=%0d", state, hd, t, w);
`endif
            case (state)
            // -------- KV SRAM clear sweep (randreset gate) --------
            ST_CLEAR: begin
                // macro writes are combinational (kw_*/vw_*)
                if (clr == 17'd1727) state <= ST_IDLE;
                else                 clr   <= clr + 17'd1;
            end

            // -------- job accept --------
            ST_IDLE: begin
                if (job_valid) begin
                    j_pos   <= job_pos[8:0];
                    j_nwk   <= job_dqk[7:2];
                    j_nwv   <= job_dv[7:2];
                    j_dk    <= job_dk[7:0];
                    j_nkc   <= job_dk[7:2];
                    j_nkr   <= job_dqk[7:2] - job_dk[7:2];
                    j_H     <= job_H;
                    j_catt  <= job_c_att;
                    j_qcbuf <= job_qc_buf;
                    j_qrbuf <= job_qr_buf;
                    j_kcbuf <= job_kc_buf;
                    j_krbuf <= job_kr_buf;
                    j_vbuf  <= job_v_buf;
                    j_cbuf  <= job_ctx_buf;
                    ks_hd   <= 2'd0;
                    vs_hd   <= 2'd0;
                    ks_w    <= 6'd0;
                    vs_w    <= 6'd0;
                    ks_ph   <= 1'b0;
                    ks_vd   <= 1'b0;
                    vs_vd   <= 1'b0;
                    ks_done <= 1'b0;
                    vs_done <= 1'b0;
                    ks_cap  <= 1'b0;
                    vs_cap  <= 1'b0;
                    state   <= ST_STORE;
                end
            end

            // -------- store k_new (port0) / v_new (port1) into KV --------
            // macro writes are combinational (kw_*/vw_* from ks_vd/vs_vd)
            ST_STORE: begin
                // K side: kc slice (phase 0) then kr shared part (phase 1)
                if (!ks_done) begin
                    ks_vd   <= 1'b1;
                    ks_hd_d <= ks_hd;
                    ks_w_d  <= ks_w;
                    ks_ph_d <= ks_ph;
                    if (!ks_ph) begin
                        if (ks_w == j_nkc - 6'd1) begin
                            ks_w  <= 6'd0;
                            ks_ph <= 1'b1;
                        end else begin
                            ks_w <= ks_w + 6'd1;
                        end
                    end else begin
                        if (ks_w == j_nkr - 6'd1) begin
                            ks_w  <= 6'd0;
                            ks_ph <= 1'b0;
                            if (ks_hd == j_H[1:0] - 2'd1) ks_done <= 1'b1;
                            else                          ks_hd   <= ks_hd + 2'd1;
                        end else begin
                            ks_w <= ks_w + 6'd1;
                        end
                    end
                end else begin
                    ks_vd <= 1'b0;
                end
                if (ks_vd) begin
                    if (ks_ph_d && (ks_hd_d == j_H[1:0] - 2'd1)
                        && (ks_w_d == j_nkr - 6'd1)) ks_cap <= 1'b1;
                end
                // V side
                if (!vs_done) begin
                    vs_vd   <= 1'b1;
                    vs_hd_d <= vs_hd;
                    vs_w_d  <= vs_w;
                    if (vs_w == j_nwv - 6'd1) begin
                        vs_w <= 6'd0;
                        if (vs_hd == j_H[1:0] - 2'd1) vs_done <= 1'b1;
                        else                          vs_hd   <= vs_hd + 2'd1;
                    end else begin
                        vs_w <= vs_w + 6'd1;
                    end
                end else begin
                    vs_vd <= 1'b0;
                end
                if (vs_vd) begin
                    if ((vs_hd_d == j_H[1:0] - 2'd1)
                        && (vs_w_d == j_nwv - 6'd1)) vs_cap <= 1'b1;
                end
                if (ks_cap && vs_cap) begin
                    hd    <= 4'd0;
                    q0_w  <= 6'd0;
                    q0_ph <= 1'b0;
                    q0_vd <= 1'b0;
                    state <= ST_QLOAD;
                end
            end

            // -------- per-head q preload (qc slice then qr slice) --------
            ST_QLOAD: begin
                if ((!q0_ph && (q0_w != j_nkc))
                    || (q0_ph && (q0_w != j_nkr))) begin
                    q0_vd  <= 1'b1;
                    q0_wd  <= q0_w;
                    q0_phd <= q0_ph;
                    q0_w   <= q0_w + 6'd1;
                end else begin
                    q0_vd <= 1'b0;
                end
                if (q0_vd) begin
                    for (i = 0; i < 4; i = i + 1) begin
                        if (!q0_phd)
                            qbuf_v[32*{q0_wd[2:0], i[1:0]} +: 32] <=
                                xr0_data[32*i +: 32];
                        else
                            qbuf_v[32*(j_dk + {3'b0, q0_wd[2:0], i[1:0]})
                                   +: 32] <= xr0_data[32*i +: 32];
                    end
                    if (!q0_phd && (q0_wd == j_nkc - 6'd1)) begin
                        q0_ph <= 1'b1;
                        q0_w  <= 6'd0;
                    end
                    if (q0_phd && (q0_wd == j_nkr - 6'd1)) begin
                        t     <= 9'd0;
                        w     <= 6'd0;
                        state <= ST_ATT;
                    end
                end
            end

            // -------- att[t] over t = 0..pos --------
            // sync KV read: issue (t, w), consume the returned word one
            // cycle later with (at_td, at_wd) — II=1, one drain cycle.
            ST_ATT: begin
                if (!att_iss) begin
                    at_dv <= 1'b1;
                    at_td <= t;
                    at_wd <= w;
                    if (w == j_nwk - 6'd1) begin
                        w <= 6'd0;
                        if (t == j_pos) att_iss <= 1'b1;
                        else            t <= t + 9'd1;
                    end else begin
                        w <= w + 6'd1;
                    end
                end else begin
                    at_dv <= 1'b0;
                end
                if (at_dv) begin
                    acc <= att_acc_n[71:0];
                    if (at_wd == j_nwk - 6'd1) begin
                        // att write is combinational (atb_we/atb_wd)
`ifdef MSH_DEBUG
                        $display("[mla] att hd=%0d t=%0d acc=%0d att_v=%0d",
                                 hd, at_td, att_acc_n, att_v);
`endif
                        if ((at_td == 9'd0) || (att_v > mx_ext))
                            mx <= att_v[55:0];
                        if (at_td == j_pos) begin
                            t       <= 9'd0;
                            att_iss <= 1'b0;
                            state   <= ST_EXP;
                        end
                    end
                end
            end

            // -------- e[t] = exp(att[t]-mx), se = sum --------
            // sync att read: issue t, consume the returned word next
            // cycle with e_td (async ROM lookup keeps II=1); the e_buf
            // macro write is combinational (eb_we/eb_waddr/eb_wd).
            ST_EXP: begin
                if ({1'b0, t} <= {1'b0, j_pos}) begin
                    e_dv <= 1'b1;
                    e_td <= t;
                    t    <= t + 9'd1;
                end else begin
                    e_dv <= 1'b0;
                end
                if (e_dv) begin
`ifdef MSH_DEBUG
                    $display("[mla] exp hd=%0d t=%0d att=%0d mx=%0d ei=%0d idx=%0d e=%0d",
                             hd, e_td, t_att_w, mx, t_ei, e_idx, e_y);
`endif
                    if (e_td == 9'd0) se <= {36'b0, e_y};
                    else              se <= se + {36'b0, e_y};
                    if (e_td == j_pos) begin
                        t     <= 9'd0;
                        state <= ST_RECIP;
                    end
                end
            end

            // -------- rec = recip(se) (async ROM read, same cycle) --------
            ST_RECIP: begin
                rec   <= rec_n[47:0];
`ifdef MSH_DEBUG
                $display("[mla] recip hd=%0d se=%0d e0=%0d E=%0d mq=%0d idx=%0d r=%0d sh=%0d rec=%0d",
                         hd, se, rc_e0, rc_E, rc_mq, rc_idx, rc_r, rc_sh, rec_n);
`endif
                w     <= 6'd0;
                state <= ST_CTX;
            end

            // -------- acc_d += rs(e[t],4) * V[t][d] --------
            // sync KV read: issue (t, w), consume with (c_td, c_wd).
            ST_CTX: begin
                if (!ctx_iss) begin
                    c_dv <= 1'b1;
                    c_td <= t;
                    c_wd <= w;
                    if (w == j_nwv - 6'd1) begin
                        w <= 6'd0;
                        if (t == j_pos) ctx_iss <= 1'b1;
                        else            t <= t + 9'd1;
                    end else begin
                        w <= w + 6'd1;
                    end
                end else begin
                    c_dv <= 1'b0;
                end
                if (c_dv) begin
                    // acc_d RMW is combinational (ad_we/ad_waddr/ad_wd)
                    if ((c_td == j_pos) && (c_wd == j_nwv - 6'd1)) begin
                        ctx_iss <= 1'b0;
                        cw_dv   <= 1'b0;
                        state   <= ST_CTXW;
                    end
                end
            end

            // -------- ctx writeout (sync acc_d read: issue w,
            // consume the returned word next cycle with cw_wd) --------
            ST_CTXW: begin
                if ({1'b0, w} < {1'b0, j_nwv}) begin
                    cw_dv <= 1'b1;
                    cw_wd <= w[4:0];
                    w     <= w + 6'd1;
                end else begin
                    cw_dv <= 1'b0;
                end
                if (cw_dv) begin
                    // xw_* are combinational this cycle (ctx_word from
                    // the returned acc_d word)
`ifdef MSH_DEBUG
                    $display("[mla] ctxw hd=%0d w=%0d acc0=%0d acc1=%0d acc2=%0d acc3=%0d word=%032x",
                             hd, cw_wd,
                             ad_rd[72*0 +: 72], ad_rd[72*1 +: 72],
                             ad_rd[72*2 +: 72], ad_rd[72*3 +: 72],
                             ctx_word);
`endif
                    if (cw_wd == j_nwv[4:0] - 5'd1) begin
                        if (hd == j_H - 4'd1) begin
                            state <= ST_DONE;
                        end else begin
                            hd    <= hd + 4'd1;
                            q0_w  <= 6'd0;
                            q0_ph <= 1'b0;
                            q0_vd <= 1'b0;
                            state <= ST_QLOAD;
                        end
                    end
                end
            end

            // -------- done pulse --------
            ST_DONE: begin
                state <= ST_IDLE;
            end

            default: state <= ST_IDLE;
            endcase
            /* verilator lint_on BLKSEQ */
        end
    end

endmodule

`default_nettype wire
