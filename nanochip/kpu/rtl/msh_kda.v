// msh_kda.v -- KDA delta-rule state unit.
//
// Part of msh_chip_top. Matches the
// per-head state-update loop of rtl/selfmodel/fxmodel.py kda() BIT-EXACTLY:
//   Sd  = rs(S[i][j] * alpha[i], 26)           (S Q4.27, alpha Q0.26)
//   Sd4 = rs(Sd, 4)
//   kS  = sum_i kh[i] * Sd4                    (kh Q2.26)
//   u   = (v[j] << 1) - rs(kS, 22)             (v Q4.26 -> u Q4.27)
//   bk  = rs(beta * kh[i], 24)                 (beta Q0.26 -> bk Q2.28)
//   upd = rs(bk * u, 28)
//   S_new = sat32(Sd + upd)                    (written back to the S SRAM)
//   o[j]  = sat32(rs(rs(sum_i qh[i]*rs(S_new,4), 23) * c_dh, 16))   (Q2.26)
// where rs(v, r) = (v + 2^(r-1)) >>> r (round-half-up, arithmetic).
//
// Job: q/k (already l2-normed, Q2.26), v (Q4.26), beta (Q0.26), alpha
// (Q0.26) sit in XBUF buffers, head slices contiguous (head hd starts at
// element hd*dh; beta is H int32 lanes in word 0). All of dh, H*dh are
// multiples of 4 (32..128, H <= 4 per configs). The module processes one
// head at a time: preload q/k/v/alpha + beta from XBUF (2 read ports,
// 128b words, 1-cycle latency), bk once per head, then per column j a
// pass1 (accumulate kS, stash Sd) / pass2 (rank-1 update + writeback,
// accumulate o) over the S column 8 rows/word, FOUR rows per cycle
// (two sub-beats per 256b word — halves the datapath area vs the
// 8-lane version at ~2x the pass cycles; the word's two halves are
// consumed on consecutive cycles). The per-column pass1/pass2 run as a
// software pipeline (ST_PRIME/ST_PIPE/ST_DRAIN): pass1 for column j+1
// (S read port) overlaps pass2 for column j (S write port) — the two
// never address the same column; Sd/u are ping-ponged by column parity
// (sdbuf_v/u_r even, sdbuf_o_v/u_o_r odd). o[j] is written to the O
// buffer one int32 lane at a time (xw_wstrb). The onorm + z-gate +
// core concat are vec ops done elsewhere; this module stops at o.
//
// S state lives in a harness msh_sram macro (macros_only rule; sync read,
// 256b words = 8 rows/word). Compact dynamic addressing: word index =
// hd*(dh*dh/8) + col*(dh/8) + wb/2 (strides from the job descriptor; the
// nano config — 1 KDA layer, 2 heads, dh 32 — uses 256 of the 256 words).
// pass2 writes each word in two half-word strobed beats (sb selects the
// 128b half). Cleared by a reset write-loop (randreset gate). A
// 2-cycle-latency debug read port (s_dbg_*) exposes the state to the unit
// TB; it is only sampled while idle. All per-head buffers are packed
// vectors (no $mem). pass1 is retimed around the 1-cycle macro read: the
// word address is issued every cycle and the returned word is consumed
// one cycle later with the delayed sub-beat index p1_rw (initiation
// interval 1; the odd sub-beat re-reads the same word).
//
// Documented assumptions:
//   * dh is a multiple of 4, 32 <= dh <= 128; H <= 4; one KDA layer.
//   * Realistic value ranges from the C-model (|kh|,|qh| <= ~2^26 unit
//     norm, |S| < 2^31, |u| < 2^37, beta/alpha < 2^26) keep every
//     intermediate in the widths used below.
//
// Reset policy (randreset gate): every control flop is reset; the S SRAM
// is explicitly zeroed by the ST_CLEAR sweep before the first job is
// accepted. All other storage is written before being read within a job
// (verified with +verilator+rand+reset+2).

`default_nettype none

module msh_kda (
    input  wire         clk,
    input  wire         rst_n,
    // job descriptor
    input  wire         job_valid,
    output wire         job_ready,
    input  wire [1:0]   job_layer,
    input  wire [8:0]   job_dh,         // rows/cols per head (32..128, mult of 4)
    input  wire [3:0]   job_H,          // heads (<= 4)
    input  wire [16:0]  job_c_dh,       // round(2^16/sqrt(dh))
    input  wire [3:0]   job_q_buf,
    input  wire [3:0]   job_k_buf,
    input  wire [3:0]   job_v_buf,
    input  wire [3:0]   job_beta_buf,
    input  wire [3:0]   job_alpha_buf,
    input  wire [3:0]   job_z_buf,      // unused (z-gate is a vec op)
    input  wire [3:0]   job_o_buf,
    output wire         job_done,
    // XBUF: two read ports (1-cycle registered latency), one write port
    output wire [12:0]  xr0_addr,       // {buf[3:0], word[8:0]}
    input  wire [127:0] xr0_data,
    output wire [12:0]  xr1_addr,
    input  wire [127:0] xr1_data,
    output wire         xw_we,
    output wire [12:0]  xw_addr,
    output wire [127:0] xw_data,
    output wire [3:0]   xw_wstrb,       // per-int32-lane write enables
    // S SRAM debug read port (test visibility, 2-cycle latency)
    input  wire [17:0]  s_dbg_addr,     // 32b-word address
    output wire [31:0]  s_dbg_data
);

    // ---------------- states ----------------
    localparam ST_CLEAR = 4'd0;
    localparam ST_IDLE  = 4'd1;
    localparam ST_BETA  = 4'd2;         // issue beta word read
    localparam ST_LOAD  = 4'd3;         // stream q/v (port0), k/alpha (port1)
    localparam ST_BK    = 4'd4;         // bk[i] = rs(beta*kh[i], 24)
    localparam ST_PRIME = 4'd5;         // pass1 for column 0 (pipeline fill)
    localparam ST_PIPE  = 4'd6;         // steady: pass1(col+1) || pass2(col)
    localparam ST_DRAIN = 4'd7;         // pass2 for the last column
    localparam ST_DONE  = 4'd8;

    reg [3:0] state;

    // ---------------- job registers ----------------
    reg [1:0]  j_layer;
    reg [8:0]  j_dh;
    reg [5:0]  j_nw;                    // dh/4 XBUF words per slice
    reg [5:0]  j_sw;                    // dh/8 S-words per column pass
    reg [3:0]  j_H;
    reg [16:0] j_cdh;
    reg [3:0]  j_qbuf, j_kbuf, j_vbuf, j_bbuf, j_abuf, j_obuf;

    // ---------------- counters / accumulators ----------------
    reg [3:0]  hd;                      // current head (0..3)
    reg [8:0]  col;                     // pass2 column j
    reg [8:0]  col_p1;                  // pass1 column (runs one ahead)
    reg [5:0]  wb;                      // pass2 sub-beat within column
    reg [5:0]  p1_wb;                   // pass1 issue counter
    reg [5:0]  p1_rw;                   // pass1: sub-beat of returned data
    reg        p1_dv;                   // pass1: returned-data valid
    reg signed [31:0] beta_r;
    reg signed [55:0] u_r;              // u of even columns
    reg signed [55:0] u_o_r;            // u of odd columns
    reg signed [71:0] acc_kS;
    reg signed [71:0] acc_o;
    reg [14:0] clr;                     // clear sweep counter

    // ---------------- XBUF stream loaders ----------------
    reg       p0_ph, p1_ph;             // 0 = first tensor, 1 = second
    reg [5:0] p0_cnt, p1_cnt;           // issue counter
    reg       p0_vd, p1_vd;             // returning-data valid (1-cycle delay)
    reg [5:0] p0_wd, p1_wd;             // returning-data word index
    reg       p0_phd, p1_phd;           // returning-data phase
    reg       p0_done, p1_done;         // issue complete
    reg       p0_cap, p1_cap;           // capture complete
    reg       beta_pend;

    // ---------------- storage ----------------
    // S state: harness msh_sram macro (256 x 256b words = 8 rows/word).
    // Compact dynamic addressing (strides from the job descriptor):
    //   word = hd*(dh*dh/8) + col*(dh/8) + wb/2
    // pass1 (read port) and pass2 (write port) address DIFFERENT columns
    // in ST_PIPE, so the single-read/single-write macro overlaps them.
    wire [12:0] s_hdspan = {5'b0, j_dh[7:0]} * {1'b0, j_sw[4:0]};
    wire [12:0] s_ridx   = ({11'b0, hd[1:0]} * s_hdspan)
                         + ({6'b0, col_p1[6:0]} * {1'b0, j_sw[4:0]})
                         + {11'b0, p1_wb[2:1]};
    wire [12:0] s_widx   = ({11'b0, hd[1:0]} * s_hdspan)
                         + ({6'b0, col[6:0]} * {1'b0, j_sw[4:0]})
                         + {11'b0, wb[2:1]};
    wire [6:0]   s_nsb   = ({1'b0, j_sw} << 1);     // sub-beats per pass
    // pass2 sub-beat fires this cycle: in ST_PIPE it is staggered one
    // cycle behind pass1's issue (p1_wb != 0), so both passes finish
    // the window on the same cycle
    wire         p2_fire = (state == ST_DRAIN)
                        || ((state == ST_PIPE) && (p1_wb != 6'd0));
    wire         s_we    = (state == ST_CLEAR) || p2_fire;
    wire [7:0]   s_waddr = (state == ST_CLEAR) ? clr[7:0] : s_widx[7:0];
    wire [255:0] s_wd    = (state == ST_CLEAR) ? 256'd0 : {2{p2_word}};
    wire [31:0]  s_wstrb = (state == ST_CLEAR) ? {32{1'b1}}
                         : wb[0] ? 32'hFFFF0000 : 32'h0000FFFF;
    wire [7:0]   s_raddr = ((state == ST_PRIME) || (state == ST_PIPE))
                         ? s_ridx[7:0] : s_dbg_addr_r[10:3];
    wire [255:0] s_rd;
    msh_sram #(.DEPTH(256), .WIDTH(256)) u_smem (
        .clk(clk), .we(s_we), .waddr(s_waddr), .wdata(s_wd),
        .wstrb(s_wstrb),
        .re(1'b1), .raddr(s_raddr), .rdata(s_rd));

    // per-head buffers (packed vectors: no inferred $mem; nano dh 32
    // -> 32 entries each)
    reg [1023:0] qbuf_v;                // 32 x int32
    reg [1023:0] kbuf_v;
    reg [1023:0] vbuf_v;
    reg [1023:0] abuf_v;
    reg [1407:0] bbuf_v;                // 32 x int44 (bk, Q2.28 signed)
    reg [1087:0] sdbuf_v;               // 32 x int34 (Sd of even column)
    reg [1087:0] sdbuf_o_v;             // 32 x int34 (Sd of odd column)

    reg [17:0] s_dbg_addr_r;

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

    // ---------------- combinational datapath ----------------
    assign job_ready = (state == ST_IDLE);
    assign job_done  = (state == ST_DONE);

    wire [8:0]  ld_base = ({7'b0, hd[1:0]} * {3'b0, j_nw});      // hd*nw
    wire [8:0]  ld_p0   = ld_base + {3'b0, p0_cnt};
    wire [8:0]  ld_p1   = ld_base + {3'b0, p1_cnt};

    assign xr0_addr = (state == ST_BETA)        ? {j_bbuf, 9'd0}
                    : (state == ST_LOAD && !p0_ph) ? {j_qbuf, ld_p0}
                    : (state == ST_LOAD)           ? {j_vbuf, ld_p0}
                    : 13'd0;
    assign xr1_addr = (state == ST_LOAD && !p1_ph) ? {j_kbuf, ld_p1}
                    : (state == ST_LOAD)           ? {j_abuf, ld_p1}
                    : 13'd0;

    // per-sub-beat pass1 / pass2 arithmetic (4 rows per cycle; row index
    // within the column = wb*4 + l, half-word of the S word by wb[0]).
    // ST_PIPE evaluates BOTH passes every cycle -> separate temps.
    // Datapath temps at TRUE value widths (documented ranges in the
    // header): multiplier operands stay narrow+equal so yosys doesn't
    // context-extend them to 80x80.
    integer l;
    reg signed [31:0] t_s, t_a;         // RAM lanes (int32)
    reg signed [33:0] t_sd;             // rs(alpha*S, 26)
    reg signed [29:0] t_sd4;            // rs(t_sd, 4)
    reg signed [65:0] t_prod;
    reg signed [79:0] t_acc;
    reg signed [43:0] t_bk;             // rs(beta*k, 24)
    // pass2 temps
    reg signed [31:0] t2_pn4;           // rs(S_new, 4)
    reg signed [43:0] t2_bk;
    reg signed [71:0] t2_upd;
    reg signed [72:0] t2_new;
    reg signed [65:0] t2_prod;
    reg signed [79:0] t2_acc;
    reg signed [33:0] t2_sd;
    reg signed [56:0] t_o1;
    reg signed [58:0] t_o2;
    reg [31:0]        t_sat;
    reg signed [79:0] p1_acc_n, p1_u_n, p2_acc_n;
    reg [135:0]       p1_sd_v;          // 4 x int34 (comb temp)
    reg [175:0]       bk_lane_v;        // 4 x int44 (comb temp)
    reg [127:0]       p2_word;          // 4 x int32 (sub-beat result)
    reg signed [31:0] p2_o;

    // rs80/sat32 return 80 bits; assignments to the true-width temps
    // intentionally truncate/extend (values always fit)
    /* verilator lint_off WIDTHTRUNC */
    /* verilator lint_off WIDTHEXPAND */
    always @* begin
        // ---- bk lanes (ST_BK), 4 rows this sub-beat ----
        for (l = 0; l < 4; l = l + 1) begin
            t_a = kbuf_v[32*{wb[2:0], l[1:0]} +: 32];
            t_bk = rs80(beta_r * t_a, 7'd24);
            bk_lane_v[44*l +: 44] = t_bk[43:0];
        end
        // ---- pass1: Sd, Sd4, kS (consumes returned macro data) ----
        t_acc = (p1_rw == 6'd0) ? 80'sd0 : {{8{acc_kS[71]}}, acc_kS};
        for (l = 0; l < 4; l = l + 1) begin
            t_s   = p1_rw[0] ? s_rd[128+32*l +: 32] : s_rd[32*l +: 32];
            t_a   = abuf_v[32*{p1_rw[2:0], l[1:0]} +: 32];
            t_sd  = rs80(t_a * t_s, 7'd26);
            p1_sd_v[34*l +: 34] = t_sd[33:0];
            t_sd4 = rs80(t_sd, 7'd4);
            t_prod = $signed(kbuf_v[32*{p1_rw[2:0], l[1:0]} +: 32])
                     * $signed({{4{t_sd4[29]}}, t_sd4});
            t_acc = t_acc + {{14{t_prod[65]}}, t_prod};
        end
        p1_acc_n = t_acc;
        p1_u_n = ({{48{vbuf_v[32*col_p1[6:0]+31]}}, vbuf_v[32*col_p1[6:0] +: 32]}
                  <<< 1) - rs80(t_acc, 7'd22);
        // ---- pass2: rank-1 update, o accumulation ----
        t2_acc = (wb == 6'd0) ? 80'sd0 : {{8{acc_o[71]}}, acc_o};
        for (l = 0; l < 4; l = l + 1) begin
            t2_bk  = bbuf_v[44*{wb[2:0], l[1:0]} +: 44];
            // u fits 37 bits (|u| <= 2^36 + 2^31: v<<1 vs rs(kS,22))
            t2_upd = rs80(t2_bk * $signed(t2_u[36:0]), 7'd28);
            t2_sd  = col[0] ? sdbuf_o_v[34*{wb[2:0], l[1:0]} +: 34]
                            : sdbuf_v  [34*{wb[2:0], l[1:0]} +: 34];
            // $signed on the concat: bare concatenations are unsigned and
            // would force the add unsigned, zero-extending t2_upd (narrower
            // than the 73-bit context) instead of sign-extending it
            t2_new = $signed({{39{t2_sd[33]}}, t2_sd}) + t2_upd;
            t_sat = sat32(t2_new);
            t2_pn4 = rs80({{48{t_sat[31]}}, t_sat}, 7'd4);
            p2_word[32*l +: 32] = t_sat;
            t2_prod = $signed(qbuf_v[32*{wb[2:0], l[1:0]} +: 32]) * t2_pn4;
            t2_acc = t2_acc + {{14{t2_prod[65]}}, t2_prod};
        end
        p2_acc_n = t2_acc;
        t_o1 = rs80(t2_acc, 7'd23);
        t_o2 = rs80(t_o1 * $signed({1'b0, j_cdh}), 7'd16);
        p2_o = sat32({{21{t_o2[58]}}, t_o2});
    end
    /* verilator lint_on WIDTHEXPAND */
    /* verilator lint_on WIDTHTRUNC */

    // pass2's u for the current column (odd/even ping-pong with pass1)
    wire signed [55:0] t2_u = col[0] ? u_o_r : u_r;

    // o write port (single lane, last sub-beat of the column)
    wire [8:0] o_word = ld_base + {4'b0, col[6:2]};
    assign xw_we    = p2_fire && ({1'b0, wb} == s_nsb - 7'd1);
    assign xw_addr  = {j_obuf, o_word};
    assign xw_data  = {p2_o, p2_o, p2_o, p2_o};
    assign xw_wstrb = 4'b0001 << col[1:0];

    // debug read port (registered address; macro data one cycle later)
    assign s_dbg_data = s_rd[32*s_dbg_addr_r[2:0] +: 32];

    // unused job field (z-gate handled by the vec unit) and spare bits
    wire _unused = &{1'b0, job_z_buf, job_layer, j_layer, job_dh[8],
                     s_widx[12:8], s_ridx[12:8], s_dbg_addr_r[17:11],
                     u_r[55:37], u_o_r[55:37], t2_u[55:37],
                     p1_acc_n[79:72], p1_u_n[79:56], p2_acc_n[79:72],
                     s_nsb[6:5]};

    // ---------------- sequential process ----------------
    integer i;

    always @(posedge clk) begin
        if (!rst_n) begin
            state     <= ST_CLEAR;
            j_layer   <= 2'd0;
            j_dh      <= 9'd0;
            j_nw      <= 6'd0;
            j_sw      <= 6'd0;
            j_H       <= 4'd0;
            j_cdh     <= 17'd0;
            j_qbuf    <= 4'd0;
            j_kbuf    <= 4'd0;
            j_vbuf    <= 4'd0;
            j_bbuf    <= 4'd0;
            j_abuf    <= 4'd0;
            j_obuf    <= 4'd0;
            hd        <= 4'd0;
            col       <= 9'd0;
            col_p1    <= 9'd0;
            wb        <= 6'd0;
            p1_wb     <= 6'd0;
            p1_rw     <= 6'd0;
            p1_dv     <= 1'b0;
            beta_r    <= 32'sd0;
            u_r       <= 56'sd0;
            u_o_r     <= 56'sd0;
            acc_kS    <= 72'sd0;
            acc_o     <= 72'sd0;
            clr       <= 15'd0;
            p0_ph     <= 1'b0;
            p1_ph     <= 1'b0;
            p0_cnt    <= 6'd0;
            p1_cnt    <= 6'd0;
            p0_vd     <= 1'b0;
            p1_vd     <= 1'b0;
            p0_wd     <= 6'd0;
            p1_wd     <= 6'd0;
            p0_phd    <= 1'b0;
            p1_phd    <= 1'b0;
            p0_done   <= 1'b0;
            p1_done   <= 1'b0;
            p0_cap    <= 1'b0;
            p1_cap    <= 1'b0;
            beta_pend <= 1'b0;
            s_dbg_addr_r <= 18'd0;
        end else begin
            /* verilator lint_off BLKSEQ */
            s_dbg_addr_r <= s_dbg_addr;

`ifdef MSH_DEBUG
            if (state != ST_CLEAR)
                $display("[kda] st=%0d hd=%0d col=%0d wb=%0d", state, hd, col, wb);
`endif
            case (state)
            // -------- S SRAM clear sweep (randreset gate) --------
            ST_CLEAR: begin
                // macro write is combinational (s_we/s_waddr/s_wd)
                if (clr == 15'd255) state <= ST_IDLE;
                else                clr   <= clr + 15'd1;
            end

            // -------- job accept --------
            ST_IDLE: begin
                if (job_valid) begin
                    j_layer <= job_layer;
                    j_dh    <= job_dh;
                    j_nw    <= job_dh[7:2];
                    j_sw    <= job_dh[8:3];
                    j_H     <= job_H;
                    j_cdh   <= job_c_dh;
                    j_qbuf  <= job_q_buf;
                    j_kbuf  <= job_k_buf;
                    j_vbuf  <= job_v_buf;
                    j_bbuf  <= job_beta_buf;
                    j_abuf  <= job_alpha_buf;
                    j_obuf  <= job_o_buf;
                    hd      <= 4'd0;
                    state   <= ST_BETA;
                end
            end

            // -------- issue beta read, (re)start head loaders --------
            ST_BETA: begin
                beta_pend <= 1'b1;
                p0_ph     <= 1'b0;
                p0_cnt    <= 6'd0;
                p0_vd     <= 1'b0;
                p0_done   <= 1'b0;
                p0_cap    <= 1'b0;
                p1_ph     <= 1'b0;
                p1_cnt    <= 6'd0;
                p1_vd     <= 1'b0;
                p1_done   <= 1'b0;
                p1_cap    <= 1'b0;
                state     <= ST_LOAD;
            end

            // -------- stream q/v (port0) and k/alpha (port1) --------
            ST_LOAD: begin
                if (beta_pend) begin
                    beta_r <= xr0_data[32*hd[1:0] +: 32];
                    beta_pend <= 1'b0;
                end
                // port0 issue: q then v
                if (!p0_done) begin
                    p0_vd  <= 1'b1;
                    p0_wd  <= p0_cnt;
                    p0_phd <= p0_ph;
                    if (p0_cnt == j_nw - 6'd1) begin
                        p0_cnt <= 6'd0;
                        if (p0_ph) p0_done <= 1'b1;
                        else       p0_ph   <= 1'b1;
                    end else begin
                        p0_cnt <= p0_cnt + 6'd1;
                    end
                end else begin
                    p0_vd <= 1'b0;
                end
                // port1 issue: k then alpha
                if (!p1_done) begin
                    p1_vd  <= 1'b1;
                    p1_wd  <= p1_cnt;
                    p1_phd <= p1_ph;
                    if (p1_cnt == j_nw - 6'd1) begin
                        p1_cnt <= 6'd0;
                        if (p1_ph) p1_done <= 1'b1;
                        else       p1_ph   <= 1'b1;
                    end else begin
                        p1_cnt <= p1_cnt + 6'd1;
                    end
                end else begin
                    p1_vd <= 1'b0;
                end
                // captures (1-cycle read latency)
                if (p0_vd) begin
                    for (i = 0; i < 4; i = i + 1) begin
                        if (!p0_phd)
                            qbuf_v[32*{p0_wd[2:0], i[1:0]} +: 32] <=
                                xr0_data[32*i +: 32];
                        else
                            vbuf_v[32*{p0_wd[2:0], i[1:0]} +: 32] <=
                                xr0_data[32*i +: 32];
                    end
                    if (p0_phd && (p0_wd == j_nw - 6'd1)) p0_cap <= 1'b1;
                end
                if (p1_vd) begin
                    for (i = 0; i < 4; i = i + 1) begin
                        if (!p1_phd)
                            kbuf_v[32*{p1_wd[2:0], i[1:0]} +: 32] <=
                                xr1_data[32*i +: 32];
                        else
                            abuf_v[32*{p1_wd[2:0], i[1:0]} +: 32] <=
                                xr1_data[32*i +: 32];
                    end
                    if (p1_phd && (p1_wd == j_nw - 6'd1)) p1_cap <= 1'b1;
                end
                if (p0_cap && p1_cap) begin
                    wb    <= 6'd0;
                    state <= ST_BK;
                end
            end

            // -------- bk[i] = rs(beta * kh[i], 24), 4 rows/sub-beat ----
            ST_BK: begin
                for (i = 0; i < 4; i = i + 1)
                    bbuf_v[44*{wb[2:0], i[1:0]} +: 44] <=
                        bk_lane_v[44*i +: 44];
                if ({1'b0, wb} == s_nsb - 7'd1) begin
                    wb     <= 6'd0;
                    col    <= 9'd0;
                    col_p1 <= 9'd0;
                    p1_wb  <= 6'd0;
                    p1_dv  <= 1'b0;
                    state  <= ST_PRIME;
                end else begin
                    wb <= wb + 6'd1;
                end
            end

            // -------- pipeline fill: pass1 for column 0 --------
            // (same retimed macro-read pattern as ST_PIPE below)
            ST_PRIME: begin
                if ({2'b0, p1_wb} < {1'b0, s_nsb}) begin
                    p1_dv <= 1'b1;
                    p1_rw <= p1_wb;
                    p1_wb <= p1_wb + 6'd1;
                end else begin
                    p1_dv <= 1'b0;
                end
                if (p1_dv) begin
                    acc_kS <= p1_acc_n[71:0];
                    for (i = 0; i < 4; i = i + 1)
                        sdbuf_v[34*{p1_rw[2:0], i[1:0]} +: 34] <=
                            p1_sd_v[34*i +: 34];
                    if ({1'b0, p1_rw} == s_nsb - 7'd1) begin
                        u_r    <= p1_u_n[55:0];
                        wb     <= 6'd0;
                        p1_wb  <= 6'd0;
                        col_p1 <= 9'd1;
                        state  <= ST_PIPE;
                    end
                end
            end

            // -------- steady window: pass1(col_p1) || pass2(col) --------
            // pass1 fills the column-parity sdbuf/u that pass2 consumes
            // NEXT window; pass2 reads the one filled LAST window. The S
            // macro's read and write ports never address the same column.
            ST_PIPE: begin
                if ({2'b0, p1_wb} < {1'b0, s_nsb}) begin
                    p1_dv <= 1'b1;
                    p1_rw <= p1_wb;
                    p1_wb <= p1_wb + 6'd1;
                end else begin
                    p1_dv <= 1'b0;
                end
                if (p1_dv) begin
                    acc_kS <= p1_acc_n[71:0];
                    for (i = 0; i < 4; i = i + 1)
                        if (col_p1[0])
                            sdbuf_o_v[34*{p1_rw[2:0], i[1:0]} +: 34] <=
                                p1_sd_v[34*i +: 34];
                        else
                            sdbuf_v[34*{p1_rw[2:0], i[1:0]} +: 34] <=
                                p1_sd_v[34*i +: 34];
                    if ({1'b0, p1_rw} == s_nsb - 7'd1) begin
                        if (col_p1[0]) u_o_r <= p1_u_n[55:0];
                        else           u_r   <= p1_u_n[55:0];
                    end
                end
                // pass2 accumulate (combinational p2_fire gates the S
                // write and xw_o ports; wb is pass2's sub-beat)
                if (p1_wb != 6'd0)
                    acc_o <= p2_acc_n[71:0];
                // window end: pass1's last consume coincides with
                // pass2's last sub-beat by construction
                if (p1_dv && ({1'b0, p1_rw} == s_nsb - 7'd1)) begin
                    wb    <= 6'd0;
                    p1_wb <= 6'd0;
                    if (col == j_dh - 9'd2) begin
                        col   <= col + 9'd1;
                        state <= ST_DRAIN;
                    end else begin
                        col    <= col + 9'd1;
                        col_p1 <= col_p1 + 9'd1;
                    end
                end else if (p1_wb != 6'd0) begin
                    wb <= wb + 6'd1;
                end
            end

            // -------- pipeline drain: pass2 for the last column --------
            ST_DRAIN: begin
                acc_o <= p2_acc_n[71:0];
                // macro write is combinational (s_we/s_waddr/s_wd/s_wstrb)
                if ({1'b0, wb} == s_nsb - 7'd1) begin
                    // xw_* write of o[col] is combinational this cycle
                    wb <= 6'd0;
                    if (hd == j_H - 4'd1) begin
                        state <= ST_DONE;
                    end else begin
                        hd    <= hd + 4'd1;
                        state <= ST_BETA;
                    end
                end else begin
                    wb <= wb + 6'd1;
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
