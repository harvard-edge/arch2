// msh_gemv.v -- int4 GEMV engine with fused dequant (row mode + head mode).
//
// Part of msh_chip_top. Matches
// rtl/selfmodel/fxmodel.py gemv_acc/gemv BIT-EXACTLY:
//   acc[c] = sum_g s[g,c] * sum_{k in group g} (q[k,c]-z[g,c]) * x[k]
//   y[c]   = sat32((acc[c] + 2^(R-1)) >> R)            (arithmetic shift)
// All arithmetic is exact integer. The per-column zero point is folded via
// the identity sum_k (q-z)*x = (sum_k q*x) - z*(sum_k x), so the MAC array
// only multiplies the raw unsigned nibble by x; z and s are applied once
// per (group, column) at fold time.
//
// Streaming (both modes): the .q region arrives as a byte stream
// (ws_valid/ws_ready, ws_data/ws_shift/ws_count/ws_last — the same
// contract as msh_fetch's byte-stream output). A byte aligner packs the
// stream into row-aligned 16-byte chunks (partial chunk flushed at each
// row end; row = job_N bytes, K/2 rows total). A 4-entry chunk FIFO
// decouples the aligner from the MAC pipeline. Every chunk carries
// (row, col, cnt) with col always a multiple of 16.
//
// MAC pipeline (1-2 chunks/cycle): stage A pops a chunk — or a PAIR of
// adjacent 16B column-group chunks of one row (col1 == col0 + 16) — and
// drives x_addr = row (x_data_e/x_data_o return x[2r]/x[2r+1] one cycle
// later; one read serves both chunks of a pair); stage B adds
// qlo*x[2r] + qhi*x[2r+1] into the per-column int64 group accumulator.
// The accumulator (qacc) is split into TWO msh_sram macros by column-
// word parity (word col[8:4] even/odd), each with its own 2-phase RMW
// channel and 1-entry forwarding register; a pair always hits one word
// of each parity, so the channels never conflict (same total macro
// bits as the old single macro). The first row of a group SETs the
// accumulator (no clearing pass needed); sum_k x is tracked in xsum
// (set/add at each row's first chunk — the even channel's col==0).
// The stream intake can also pop TWO 16B beats per cycle (32B aligner
// path) when the aligner sits at a row boundary and j_n % 16 == 0.
//
// At each group end (last chunk of the group's last row) FOLD computes
//   acc64[c] += s[g,c] * (qacc[c] - z[g,c]*xsum)      (SET when g == 0)
// Row mode: 16 columns/cycle from internal SBUF/ZBUF (128-bit word
// memories loaded from the s and z stream segments, byte-staged word
// writes). Head mode: 16 columns/cycle; the current group's s array is
// prefetched through the hs port during the MAC phase into an internal
// 256b-wide buffer (sbuf_h, one word per 16 columns — the fold needs
// 2 s-words per block, more than the 1-word/cycle hs port sustains;
// prefetch costs N/8 cycles against >= 4N MAC cycles), z comes from the
// hz port (one 16-lane word per block). SBUF2/ZBUF2 live outside this
// module and are preloaded by other means.
// After the last group, WRITE emits y[c] = sat32((acc64[c] + 2^(R-1)) >> R),
// one word/cycle, with a running strictly-greater argmax on am_val/am_idx
// (head mode only).
//
// All storage is harness msh_sram macros (macros_only rule; synchronous
// registered reads, per-byte write enables). Every read-modify-write path
// is retimed around the 1-cycle read latency: the segment loads stage
// bytes into whole words (byte strobes, no RMW), the B2 accumulate issues
// the qacc read one cycle before its write (with a 1-entry forwarding
// register covering back-to-back same-word chunks), the fold is a 4-stage
// F1a/F1b/F2/F3 pipeline, and the write-out emits one cycle after the
// address issue.
//
// Documented assumptions:
//   * row mode N >= 16 (a 16-byte beat then completes at most one row),
//     or the small-N buffered path (S_SLOAD/S_SMAC, K/2*N <= 512 B);
//     head mode N is a multiple of 16 (no partial chunks).
//   * R in [1, 63] (tests use R = 12); K even.
//   * N <= ACC_LANES (512: nano vocab); column word index < ACC_WORDS.
//   * y_addr carries the low 12 bits of the column index (wraps for
//     N > 4096); integration stripes head-mode logits writes by position.
//   * job_q_addr/job_s_addr/job_z_addr/job_xbuf are carried by the fetch
//     engine's segment routing and the XBUF port binding; this module does
//     not use them (y_buf is passed through on the Y port).
//
// Reset policy (randreset gate): every control flop is reset. Data arrays
// are never relied on: qacc/acc64 use set-on-first-write semantics and
// s/z/row bytes are always written before being read, so the outputs are
// identical under random initial state (verified with
// +verilator+rand+reset+2).

`default_nettype none

module msh_gemv #(
    parameter ACC_LANES = 512,                    // per-column accumulator depth
    parameter ACC_WORDS = ACC_LANES / 16,         // 16 lanes per 1024-bit word
    parameter ACC_AW    = 5                       // clog2(ACC_WORDS) for nano
) (
    input  wire         clk,
    input  wire         rst_n,
    // job descriptor
    input  wire         job_valid,
    output wire         job_ready,
    input  wire         job_mode,       // 0 = row mode, 1 = head mode
    input  wire [35:0]  job_q_addr,
    input  wire [15:0]  job_K,          // fan-in rows (even)
    input  wire [17:0]  job_N,          // fan-out columns
    input  wire [2:0]   job_ng,         // number of groups (<= 4)
    input  wire [7:0]   job_gsz,        // group size in fan-in rows
    input  wire [35:0]  job_s_addr,
    input  wire [35:0]  job_z_addr,
    input  wire [7:0]   job_R,          // output shift (tests: 12)
    input  wire [3:0]   job_xbuf,
    input  wire [3:0]   job_ybuf,
    // X-vector read port (even/odd banks, 1-cycle registered latency)
    output wire [11:0]  x_addr,         // packed row index r -> x[2r], x[2r+1]
    input  wire [31:0]  x_data_e,
    input  wire [31:0]  x_data_o,
    // weight byte stream (from msh_fetch)
    input  wire         ws_valid,
    output wire         ws_ready,
    input  wire [127:0] ws_data,
    input  wire [4:0]   ws_count,       // valid bytes 1..16
    input  wire [3:0]   ws_shift,       // offset of first valid byte
    input  wire         ws_last,        // last beat of current segment
    // second stream beat (2-beat pops, S_RUN only): ws2_valid implies
    // ws_valid; when the gemv asserts ws2_ready it does NOT assert
    // ws_ready — the fetch pops BOTH beats in that cycle
    input  wire         ws2_valid,
    output wire         ws2_ready,
    input  wire [127:0] ws2_data,
    input  wire [4:0]   ws2_count,
    // head-q shadow buffer residency: when the fetch holds the whole
    // head weight segment, the head job's intake comes from the shadow
    // channel (muxed at chip_top) instead of the DRAM byte stream, and
    // the stream pops nothing (gv_hq_use gates the bs pop enables)
    input  wire         hq_fill_done,
    output wire         gv_hq_use,
    // head-mode resident s/z read ports (SBUF2/ZBUF2 in msh_mem.v).
    // READ TIMING: synchronous (1-cycle registered, matches msh_hsz);
    // the fold issues addresses one cycle before consuming the data.
    // Word-organized, flat (group, column) layout:
    //   s: 8 int16 lanes per 128b word (lane j at bits [16j+15:16j], LE);
    //      word address = g*(N/8) + c/8. Read ONLY during the MAC phase
    //      (one word/cycle prefetch into the internal sbuf_h — the fold
    //      needs 2 s-words per 16-column block, more than the port can
    //      sustain; the prefetch takes N/8 cycles vs >= 4N MAC cycles).
    //   z: 16 uint8 lanes per 128b word (lane j at bits [8j+7:8j]);
    //      word address = g*(N/16) + c/16. Read during FOLD only (one word
    //      per 16-column block). All addresses are word-aligned.
    output wire [17:0]  hs_addr,
    input  wire [127:0] hs_data,
    output wire [17:0]  hz_addr,
    input  wire [127:0] hz_data,
    // Y write port: 4 int32 lanes per beat (lane i at bits [32i+:32]);
    // y_addr = column index of lane 0 (a multiple of 4); y_wstrb =
    // per-lane write strobes (row-mode tail beats may be partial)
    output wire         y_we,
    output wire [11:0]  y_addr,
    output wire [127:0] y_data,
    output wire [3:0]   y_wstrb,
    output wire [3:0]   y_buf,
    // running argmax (head mode, valid during write-out)
    output wire [31:0]  am_val,
    output wire [17:0]  am_idx,
    output wire         am_valid,
    // job completion pulse (with the last y word)
    output wire         done
);

    // ---------------- states ----------------
    localparam S_IDLE   = 3'd0;
    localparam S_LOAD_S = 3'd1;
    localparam S_LOAD_Z = 3'd2;
    localparam S_RUN    = 3'd3;
    localparam S_FOLD   = 3'd4;
    localparam S_WRITE  = 3'd5;
    localparam S_SLOAD  = 3'd6;          // small-N (j_n < 16): buffer .q
    localparam S_SMAC   = 3'd7;          // small-N: inject chunks from qram

    reg [2:0] state;

    // ---------------- job registers ----------------
    reg        j_mode;
    reg        hq_use_r;                // latched at accept: shadow-q job
    reg [15:0] j_k2;                    // K/2 packed rows
    reg [17:0] j_n;
    reg [2:0]  j_ng;
    reg [7:0]  j_gsz2;                  // gsz/2 packed rows per group
    reg [7:0]  j_r;
    reg [3:0]  j_ybuf;

    // ---------------- group tracking ----------------
    reg [2:0]  g_cnt;
    reg [15:0] g_start;                 // first packed row of current group
    reg [20:0] s_base;                  // sbuf byte offset = g*N*2
    reg [20:0] z_base;                  // zbuf byte offset / head word = g*N

    wire [16:0] g_end_full = {1'b0, g_start} + {9'b0, j_gsz2};
    wire [15:0] ge_row = (g_end_full > {1'b0, j_k2})
                       ? (j_k2 - 16'd1) : (g_end_full[15:0] - 16'd1);

    // ---------------- storage (harness msh_sram macros) ----------------
    // All synchronous read (1-cycle); the datapath pipelines accordingly.
    // Row-mode s/z: two write-synced copies each for the unaligned fold
    // barrel (words k and k+1 in the same cycle).
    wire [127:0] sw_lo, sw_hi, zw_lo, zw_hi;
    wire [11:0]  sw_addr;
    wire [10:0]  zw_addr;
    wire         sw_we, zw_we;
    wire [7:0]   sw_waddr;
    wire [6:0]   zw_waddr;
    wire [127:0] sw_wdata, zw_wdata;
    wire [15:0]  sw_wstrb, zw_wstrb;

    msh_sram #(.DEPTH(256), .WIDTH(128)) u_sbuf_lo (
        .clk(clk), .we(sw_we), .waddr(sw_waddr),
        .wdata(sw_wdata), .wstrb(sw_wstrb),
        .re(1'b1), .raddr(sw_addr[11:4]), .rdata(sw_lo));
    msh_sram #(.DEPTH(256), .WIDTH(128)) u_sbuf_hi (
        .clk(clk), .we(sw_we), .waddr(sw_waddr),
        .wdata(sw_wdata), .wstrb(sw_wstrb),
        .re(1'b1), .raddr(sw_addr[11:4] + 8'd1), .rdata(sw_hi));
    msh_sram #(.DEPTH(128), .WIDTH(128)) u_zbuf_lo (
        .clk(clk), .we(zw_we), .waddr(zw_waddr),
        .wdata(zw_wdata), .wstrb(zw_wstrb),
        .re(1'b1), .raddr(zw_addr[10:4]), .rdata(zw_lo));
    msh_sram #(.DEPTH(128), .WIDTH(128)) u_zbuf_hi (
        .clk(clk), .we(zw_we), .waddr(zw_waddr),
        .wdata(zw_wdata), .wstrb(zw_wstrb),
        .re(1'b1), .raddr(zw_addr[10:4] + 7'd1), .rdata(zw_hi));

    // small-N .q buffer: 32 x 128b words, two copies for the unaligned
    // 16-byte chunk barrel
    wire [127:0] qr_lo, qr_hi;
    wire [8:0]   qr_addr;
    wire         qr_we;
    wire [4:0]   qr_waddr;
    wire [127:0] qr_wdata;
    wire [15:0]  qr_wstrb;
    msh_sram #(.DEPTH(32), .WIDTH(128)) u_qram_lo (
        .clk(clk), .we(qr_we), .waddr(qr_waddr),
        .wdata(qr_wdata), .wstrb(qr_wstrb),
        .re(1'b1), .raddr(qr_addr[8:4]), .rdata(qr_lo));
    msh_sram #(.DEPTH(32), .WIDTH(128)) u_qram_hi (
        .clk(clk), .we(qr_we), .waddr(qr_waddr),
        .wdata(qr_wdata), .wstrb(qr_wstrb),
        .re(1'b1), .raddr(qr_addr[8:4] + 5'd1), .rdata(qr_hi));

    // accumulators + head-s prefetch buffer (one read port each).
    // qacc is split into two macros by column-word parity (word index
    // col[8:4]: even -> A, odd -> B; ACC_WORDS/2 words each, same total
    // bits) so the two B2 channels each own one macro's ports.
    wire [1023:0] qwA_rd, qwB_rd, aw_rd;
    wire [255:0]  sh_rd;
    wire [3:0]    qwA_raddr, qwB_raddr;
    wire [4:0]    aw_raddr, sh_raddr;
    wire          qwA_we, qwB_we, aw_we, sh_we;
    wire [3:0]    qwA_waddr, qwB_waddr;
    wire [4:0]    aw_waddr, sh_waddr;
    wire [1023:0] qwA_wd, qwB_wd, aw_wd;
    wire [255:0]  sh_wd;
    wire [31:0]   sh_wstrb;
    msh_sram #(.DEPTH(ACC_WORDS/2), .WIDTH(1024)) u_qacc_a (
        .clk(clk), .we(qwA_we), .waddr(qwA_waddr), .wdata(qwA_wd),
        .wstrb({128{1'b1}}),
        .re(1'b1), .raddr(qwA_raddr), .rdata(qwA_rd));
    msh_sram #(.DEPTH(ACC_WORDS/2), .WIDTH(1024)) u_qacc_b (
        .clk(clk), .we(qwB_we), .waddr(qwB_waddr), .wdata(qwB_wd),
        .wstrb({128{1'b1}}),
        .re(1'b1), .raddr(qwB_raddr), .rdata(qwB_rd));
    // fold-side qacc read: both macros read the row fold_c[8:5]; the
    // block's word is selected by its parity (valid in F1b)
    wire [1023:0] qw_rd = f1a_col[4] ? qwB_rd : qwA_rd;
    msh_sram #(.DEPTH(ACC_WORDS), .WIDTH(1024)) u_acc (
        .clk(clk), .we(aw_we), .waddr(aw_waddr), .wdata(aw_wd),
        .wstrb({128{1'b1}}),
        .re(1'b1), .raddr(aw_raddr), .rdata(aw_rd));
    msh_sram #(.DEPTH(ACC_WORDS), .WIDTH(256)) u_sbufh (
        .clk(clk), .we(sh_we), .waddr(sh_waddr), .wdata(sh_wd),
        .wstrb(sh_wstrb),
        .re(1'b1), .raddr(sh_raddr), .rdata(sh_rd));

    // ---------------- stream aligner ----------------
    reg [4:0]  fill;                    // staged bytes (0..15 between beats)
    reg [247:0] stage_v;                // 31 x 8b (packed vector: no $mem)
    reg [15:0] q_row;                   // current .q packed row
    reg [17:0] row_bcnt;                // bytes seen in current row

    // ---------------- chunk FIFO (depth 8, packed vectors: no $mem) ----
    reg [127:0]  cf_row_v;              // 8 x 16b
    reg [143:0]  cf_col_v;              // 8 x 18b
    reg [39:0]   cf_cnt_v;              // 8 x 5b
    reg [1023:0] cf_dat_v;              // 8 x 128b
    reg [2:0] cf_rd, cf_wr;
    reg [3:0] cf_occ;
    wire [15:0]  cfr_row = cf_row_v[16*cf_rd +: 16];
    wire [17:0]  cfr_col = cf_col_v[18*cf_rd +: 18];
    wire [4:0]   cfr_cnt = cf_cnt_v[5*cf_rd +: 5];
    wire [127:0] cfr_dat = cf_dat_v[128*cf_rd +: 128];
    reg [2:0]   cf_wr2;             // second push slot (blocking temp;
                                    // assigned at the push site — a wire
                                    // here would read the pre-block e1_v
                                    // because Verilator evaluates the
                                    // continuous assign after the clocked
                                    // block, so e2 overwrote e1's slot)

`ifdef MSH_DEBUG
    reg [31:0] dbg_cyc;
    reg [2:0]   dbg_state_d;
    reg [11:0] dbg_stall;
    always @(posedge clk) begin
        if (!rst_n) begin
            dbg_cyc   <= 32'd0;
            dbg_state_d <= 3'd0;
            dbg_stall <= 12'd0;
        end else begin
            dbg_cyc <= dbg_cyc + 32'd1;
            if (ws_fire)
                $display("[gemv] cyc=%0d ws fire st=%0d cnt=%0d sh=%0d last=%0d fill=%0d occ=%0d stalls=%0d",
                         dbg_cyc, state, ws_count, ws_shift, ws_last,
                         fill, cf_occ, dbg_stall);
        end
    end
`endif

    // ---------------- MAC stage B (B1 multiply, B2 accumulate) ----------------
    reg         b_valid;
    reg         b_pair;                 // two chunks popped (b_* + b_*_o)
    reg [15:0]  b_row;
    reg [17:0]  b_col;
    reg [4:0]   b_cnt;
    reg [127:0] b_data;
    reg         b_set;                  // row is first row of its group
    reg         b_gend;                 // chunk ends the group's last row
    reg [17:0]  b_col_o;                // odd chunk of the pair (col+16)
    reg [4:0]   b_cnt_o;
    reg [127:0] b_data_o;
    reg         b_set_o;
    reg         b_gend_o;

    reg         b1_valid;
    reg         b1_pair;
    reg [17:0]  b1_col;
    reg [4:0]   b1_cnt;
    reg         b1_set;
    reg         b1_gend;
    reg [639:0] b1_prod;                // 16 x int40 (qlo*xe + qhi*xo)
    reg [33:0]  b1_xs;                  // xe + xo for xsum
    reg [17:0]  b1_col_o;
    reg [4:0]   b1_cnt_o;
    reg         b1_set_o;
    reg         b1_gend_o;
    reg [639:0] b1_prod_o;              // odd chunk's 16 products

    // B2 writeback stage, one channel per qacc macro (the channel's
    // qacc read was issued one cycle earlier, at b1)
    reg         b1dA_valid, b1dB_valid;
    reg [17:0]  b1dA_col,  b1dB_col;
    reg [4:0]   b1dA_cnt,  b1dB_cnt;
    reg         b1dA_set,  b1dB_set;
    reg         b1dA_gend, b1dB_gend;
    reg [639:0] b1dA_prod, b1dB_prod;
    reg [33:0]  b1dA_xs,   b1dB_xs;
    // per-macro 1-entry forwarding: the macro returns OLD data on a
    // same-cycle read+write to one address (back-to-back same-word
    // chunks of consecutive rows)
    reg           qwA_fwd_v, qwB_fwd_v;
    reg [3:0]     qwA_fwd_addr, qwB_fwd_addr;
    reg [1023:0]  qwA_fwd_wd, qwB_fwd_wd;

    reg signed [63:0] xsum;             // sum of x over the current group

    // ---------------- fold pipeline (F1a/F1b/F2/F3) ----------------
    reg [17:0] fold_c;
    reg        f1a_v, f1a_g0, f1a_last; // F1a: issued block metadata
    reg [17:0] f1a_col;
    reg [3:0]  f1a_zsh, f1a_ssh;        // barrel shifts (byte offset*8)
    reg        f1_v, f1_g0, f1_last;    // F1b outputs
    reg [17:0] f1_col;
    reg [1023:0] f1_qw, f1_aw;          // qacc/acc words for the block
    reg [255:0]  f1_s;                  // 16 x int16 scales
    reg [383:0]  f1_sz;                 // 16 x int24 s*z products
    // fold phase: F1a issues on even phases; the 16 lanes are
    // time-multiplexed as two 8-lane sub-beats (F2a/F2b) sharing 16
    // multipliers (halves the fold multiplier count)
    reg        f2a_v, f2a_last;
    reg [17:0] f2a_col;
    reg [1023:0] f2a_base;
    reg [511:0]  f2a_t1, f2a_t2;
    reg [511:0]  f2b_t1, f2b_t2;
    reg [17:0] wr_c;
    reg [31:0] am_val_r;
    reg [17:0] am_idx_r;
    reg [11:0] x_addr_r;
    reg [12:0] seg_pos;             // .q/s/z segment byte position (max 4096)
    // segment-load staging (one word in flight)
    reg [127:0] ld_stage;
    reg         ld_flush;           // deferred tail write (ws_last crossing)
    reg [127:0] ld_ftail;
    reg [15:0]  ld_fmask;
    reg [8:0]   ld_fwidx;
    // head-mode s prefetch (synchronous hs read: write lands 1 cycle late)
    reg [17:0]  pf_cnt;                 // 128b s-words prefetched this group
    reg [17:0]  pf_gbase;               // s-word base of current group
    reg         hf_wait;                // group-end done, prefetch pending
    reg         pf_run_d;
    reg [17:0]  pf_cnt_d;
    // small-N inject (synchronous qram read: push lands 1 cycle late)
    reg [15:0]  smac_r;                 // small-N: next row to inject
    reg         smac_dv;
    reg [15:0]  smac_base_d, smac_r_d;

    // ---------------- combinational interface ----------------
    assign job_ready = (state == S_IDLE);
    // head job uses the resident shadow buffer once the fetch holds the
    // whole head weight segment (see msh_fetch TG_HQ). Latched at job
    // accept: fill_done can rise mid-first-job (the shadow fill runs
    // concurrent with the streamed q), and flipping the ws mux then
    // would restart the beat stream mid-segment. Qualified by busy: a
    // stale hq_use_r while S_IDLE would gate the byte stream for other
    // engines (the deq job between head and next token never touches
    // the gemv, so the latch would stick).
    assign gv_hq_use  = hq_use_r && (state != S_IDLE);

    // second cf entry (pair candidate); reads garbage when cf_occ < 2,
    // which a_pair masks
    wire [2:0]   cf_rd1   = cf_rd + 3'd1;
    wire [15:0]  cfr1_row = cf_row_v[16*cf_rd1 +: 16];
    wire [17:0]  cfr1_col = cf_col_v[18*cf_rd1 +: 18];
    wire [4:0]   cfr1_cnt = cf_cnt_v[5*cf_rd1 +: 5];
    wire [127:0] cfr1_dat = cf_dat_v[128*cf_rd1 +: 128];
    // pair condition: cfr0 and cfr1 are the same row and cfr1_col ==
    // cfr0_col + 16 (adjacent column groups). Because the aligner emits
    // in strict byte order this is exactly "cfr0_col is an even group
    // index within the row".
    wire a_pair   = (cf_occ >= 4'd2) && (cfr1_row == cfr_row)
                  && (cfr1_col == (cfr_col + 18'd16));
    wire gend_ret = (b1dA_valid && b1dA_gend) || (b1dB_valid && b1dB_gend);
    wire a_load = ((state == S_RUN) || (state == S_SMAC))
                && (cf_occ != 4'd0)
                && !(b_valid  && (b_gend  || (b_pair  && b_gend_o)))
                && !(b1_valid && (b1_gend || (b1_pair && b1_gend_o)))
                && !gend_ret;
    wire [2:0] a_pop = a_load ? (a_pair ? 3'd2 : 3'd1) : 3'd0;
    assign x_addr = a_load ? cfr_row[11:0] : x_addr_r;

    // 2-beat intake (S_RUN only): pop two full 16B beats per cycle when
    // all hold — the aligner sits at a row boundary (fill == 0), the
    // row length is chunk-aligned (j_n % 16 == 0, all real configs),
    // beat0 is a full unshifted beat (ws_count == 16 excludes a shifted
    // first beat, whose bytes would not land at stage offset 0) and is
    // not the segment's last (so beat1 is a same-segment full beat:
    // the q length is a multiple of 16 when j_n is). Jobs that fail
    // any term use the bit-identical 16B path for the whole segment.
    wire run2_ok = (state == S_RUN) && (q_row < j_k2) && (cf_occ <= 4'd5)
                 && (fill == 5'd0) && !ws_last && (j_n[3:0] == 4'd0)
                 && (ws_count == 5'd16) && (ws2_count == 5'd16);
    assign ws2_ready = run2_ok;
    assign ws_ready = ((((state == S_LOAD_S) || (state == S_LOAD_Z)
                         || (state == S_SLOAD)) && !ld_flush)
                       || ((state == S_RUN) && (cf_occ <= 4'd6)
                           && (q_row < j_k2)))
                      && !run2_ok;
    // NOTE: the q_row < j_k2 term stops intake the cycle after the
    // last row-pair completes. Without it the engine keeps accepting
    // beats for 2-3 cycles while the B pipeline retires the final
    // chunks — invisible with just-in-time segments (empty stream),
    // fatal with a prefetched stream: it would eat the next job's
    // weight bytes. The same care applies to beat1 (hence !ws_last).
    wire ws_fire  = ws_valid && ws_ready;
    // 2-beat pop as the fetch sees it (ws2_valid implies ws_valid)
    wire ws_fire2 = ws_valid && ws2_valid && run2_ok;

    // small-N inject: issue the qram read this cycle, push the chunk
    // from the returned data next cycle (initiation interval 1)
    wire smac_issue = (state == S_SMAC) && (smac_r < j_k2)
                    && (cf_occ <= 4'd6);
    wire [15:0] smac_base = smac_r * j_n[15:0];
    wire _unused_smac = &{1'b0, smac_base[15:9], smac_base[3:0]};

    // head-mode z read address (fold stage F1a; data returns in F1b);
    // s is prefetched into sbuf_h during the MAC phase (hs port)
    wire        hz_issue = (state == S_FOLD) && j_mode && (fold_c < j_n);
    wire [20:0] hz_col   = z_base + {3'b0, fold_c};   // g*N + c0, 16-aligned
    assign hz_addr = hz_issue ? {1'b0, hz_col[20:4]} : 18'd0;

    wire [17:0] pf_total = {3'b0, j_n[17:3]};         // 128b s-words/group
    wire        pf_run   = (state == S_RUN) && j_mode && (pf_cnt < pf_total);
    wire        pf_done  = (pf_cnt == pf_total);
    assign hs_addr = pf_run ? (pf_gbase + pf_cnt) : 18'd0;

    // ---------------- segment-load staging merge ----------------
    // Incoming bytes are staged into ld_stage; a macro word write fires
    // when the word completes (<= 1 word per beat) or as a partial flush
    // at ws_last. A ws_last beat that completes a word AND leaves a tail
    // defers the tail one cycle via ld_flush (stream stalled by ws_ready).
    wire [127:0] beat_sh  = ws_data >> {ws_shift, 3'b000};
    wire [4:0]   ld_off   = {1'b0, seg_pos[3:0]};
    wire [5:0]   ld_end   = {1'b0, ld_off} + {1'b0, ws_count};
    wire         ld_cross = ld_end > 6'd16;
    wire         ld_in    = ws_fire && ((state == S_LOAD_S)
                             || (state == S_LOAD_Z) || (state == S_SLOAD));
    wire         ld_wfull = ld_in && (ld_end >= 6'd16);
    wire         ld_wpart = ld_in && ws_last && !ld_cross
                          && (ld_end[3:0] != 4'd0);
    reg [255:0] ld_merged;
    integer mi;
    always @* begin
        ld_merged = {128'd0, ld_stage};
        for (mi = 0; mi < 16; mi = mi + 1)
            if ({1'b0, mi[3:0]} < ws_count)
                ld_merged[{ld_off + mi[4:0], 3'b000} +: 8] =
                    beat_sh[{mi[3:0], 3'b000} +: 8];
    end
    wire [127:0] ld_wd    = ld_flush ? ld_ftail : ld_merged[127:0];
    wire [15:0]  ld_wstrb = ld_flush ? ld_fmask
                          : (ld_end >= 6'd16) ? 16'hFFFF
                          : ((16'h0001 << ld_end[3:0]) - 16'h0001);
    wire [8:0]   ld_widx  = ld_flush ? ld_fwidx : seg_pos[12:4];
    wire         ld_anyw  = ld_wfull || ld_wpart || ld_flush;

    assign sw_we    = ld_anyw && (state == S_LOAD_S);
    assign sw_waddr = ld_widx[7:0];
    assign sw_wdata = ld_wd;
    assign sw_wstrb = ld_wstrb;
    assign zw_we    = ld_anyw && (state == S_LOAD_Z);
    assign zw_waddr = ld_widx[6:0];
    assign zw_wdata = ld_wd;
    assign zw_wstrb = ld_wstrb;
    assign qr_we    = ld_anyw && (state == S_SLOAD);
    assign qr_waddr = ld_widx[4:0];
    assign qr_wdata = ld_wd;
    assign qr_wstrb = ld_wstrb;

    // ---------------- read address muxes ----------------
    // F1a issues all fold reads one cycle before F1b consumes them.
    wire [20:0] idx_az = z_base + {3'b0, fold_c};      // z byte index
    wire [20:0] idx_as = s_base + {2'b0, fold_c, 1'b0};// s byte index
    assign zw_addr  = idx_az[10:0];
    assign sw_addr  = idx_as[11:0];
    assign qr_addr  = smac_base[8:0];
    // B2 channel routing: a chunk targets qacc macro A (B) when its
    // column word col[8:4] is even (odd); a pair (c, c+16) always hits
    // one word of each parity, so the channels never share a macro
    wire        b1_ch0A  = (b1_col[4] == 1'b0);
    wire        b1A_v    = b1_valid && (b1_pair || b1_ch0A);
    wire        b1B_v    = b1_valid && (b1_pair || !b1_ch0A);
    wire [17:0] b1_colA  = b1_ch0A ? b1_col    : b1_col_o;
    wire [4:0]  b1_cntA  = b1_ch0A ? b1_cnt    : b1_cnt_o;
    wire        b1_setA  = b1_ch0A ? b1_set    : b1_set_o;
    wire        b1_gendA = b1_ch0A ? b1_gend   : b1_gend_o;
    wire [639:0] b1_prodA = b1_ch0A ? b1_prod  : b1_prod_o;
    wire [17:0] b1_colB  = b1_ch0A ? b1_col_o  : b1_col;
    wire [4:0]  b1_cntB  = b1_ch0A ? b1_cnt_o  : b1_cnt;
    wire        b1_setB  = b1_ch0A ? b1_set_o  : b1_set;
    wire        b1_gendB = b1_ch0A ? b1_gend_o : b1_gend;
    wire [639:0] b1_prodB = b1_ch0A ? b1_prod_o : b1_prod;
    assign qwA_raddr = (state == S_FOLD) ? fold_c[8:5] : b1_colA[8:5];
    assign qwB_raddr = (state == S_FOLD) ? fold_c[8:5] : b1_colB[8:5];
    // S_WRITE reads one 16-lane acc word per 16-column group: word 0 at
    // entry (wr_ph == 0), then a prefetch of the next group issued in
    // sub-beat 2 (data returns in sub-beat 3 and is held in wr_word)
    assign aw_raddr = (state == S_FOLD) ? fold_c[8:4]
                    : ((state == S_WRITE) && (wr_ph == 2'd2)
                       && (wr_sub == 2'd2) && wr_more2)
                        ? wr_c[8:4] + 5'd1 : wr_c[8:4];
    assign sh_raddr = fold_c[8:4];

    // ---------------- B2 accumulate writeback (qacc RMW, per macro) ----
    wire [1023:0] qwA_cur = (qwA_fwd_v && (qwA_fwd_addr == b1dA_col[8:5]))
                          ? qwA_fwd_wd : qwA_rd;
    wire [1023:0] qwB_cur = (qwB_fwd_v && (qwB_fwd_addr == b1dB_col[8:5]))
                          ? qwB_fwd_wd : qwB_rd;
    reg [1023:0] qwA_wd_r, qwB_wd_r;
    integer bi;
    always @* begin
        qwA_wd_r = qwA_cur;
        qwB_wd_r = qwB_cur;
        for (bi = 0; bi < 16; bi = bi + 1) begin
            if ({1'b0, bi[3:0]} < b1dA_cnt)
                qwA_wd_r[64*bi +: 64] =
                    (b1dA_set ? 64'sd0 : $signed(qwA_cur[64*bi +: 64]))
                    + {{24{b1dA_prod[40*bi+39]}}, b1dA_prod[40*bi +: 40]};
            if ({1'b0, bi[3:0]} < b1dB_cnt)
                qwB_wd_r[64*bi +: 64] =
                    (b1dB_set ? 64'sd0 : $signed(qwB_cur[64*bi +: 64]))
                    + {{24{b1dB_prod[40*bi+39]}}, b1dB_prod[40*bi +: 40]};
        end
    end
    assign qwA_we    = b1dA_valid;
    assign qwA_waddr = b1dA_col[8:5];           // col < 512 => word < 16
    assign qwA_wd    = qwA_wd_r;
    assign qwB_we    = b1dB_valid;
    assign qwB_waddr = b1dB_col[8:5];
    assign qwB_wd    = qwB_wd_r;

    // ---------------- shared 16-lane fold multiplies ----------------
    // F2 computes all 16 lanes in one cycle (unrolled from the old
    // 8-lane two-phase time-mux: F1b and F3 were already full-width,
    // so the fold initiation interval drops from 2 to 1 block/cycle)
    reg [1023:0] f2m_t1, f2m_t2;
    integer fm;
    always @* begin
        f2m_t1 = 1024'd0;
        f2m_t2 = 1024'd0;
        for (fm = 0; fm < 16; fm = fm + 1) begin
            f2m_t1[64*fm +: 64] =
                $signed(f1_s[16*fm +: 16])
                * $signed(f1_qw[64*fm +: 64]);
            f2m_t2[64*fm +: 64] =
                $signed(f1_sz[24*fm +: 24])
                * xsum;
        end
    end

    // ---------------- F3 combine + acc writeback ----------------
    reg [1023:0] aw_wd_r;
    integer fi;
    always @* begin
        for (fi = 0; fi < 8; fi = fi + 1) begin
            if ((f2a_col + {14'b0, fi[3:0]}) < j_n)
                aw_wd_r[64*fi +: 64] =
                    $signed(f2a_base[64*fi +: 64])
                    + $signed(f2a_t1[64*fi +: 64])
                    - $signed(f2a_t2[64*fi +: 64]);
            else
                aw_wd_r[64*fi +: 64] = 64'sd0;
            if ((f2a_col + 18'd8 + {14'b0, fi[3:0]}) < j_n)
                aw_wd_r[64*(fi + 8) +: 64] =
                    $signed(f2a_base[64*(fi + 8) +: 64])
                    + $signed(f2b_t1[64*fi +: 64])
                    - $signed(f2b_t2[64*fi +: 64]);
            else
                aw_wd_r[64*(fi + 8) +: 64] = 64'sd0;
        end
    end
    assign aw_we    = f2a_v;
    assign aw_waddr = f2a_col[8:4];
    assign aw_wd    = aw_wd_r;

    // head-mode s prefetch writeback (hs read issued one cycle earlier)
    assign sh_we    = pf_run_d;
    assign sh_waddr = pf_cnt_d[ACC_AW:1];       // two 128b words per 256b
    assign sh_wd    = {2{hs_data}};
    assign sh_wstrb = pf_cnt_d[0] ? 32'hFFFF0000 : 32'h0000FFFF;

    // write-out datapath (4 columns/cycle): one 16-lane acc word is held
    // in wr_word and emitted as four 4-lane sub-beats; the next group's
    // word is prefetched during sub-beat 2 and loaded at sub-beat 3, so
    // the pipeline sustains 4 columns/cycle after a 2-cycle startup
    // (issue word 0, load word 0). The rounding constant is job-static:
    // registered at job accept.
    reg [1023:0] wr_word;
    reg [1:0]    wr_ph;              // 0: issue word0, 1: load word0, 2: emit
    reg [1:0]    wr_sub;             // sub-beat within the 16-column group
    reg [17:0]   wr_am_base;         // base column of the registered beat
    wire [5:0]   wr_lane0 = {2'b0, wr_sub, 2'b00};
    wire [5:0]   r_sh    = j_r[5:0];
    reg signed [63:0] j_round;
    wire         wr_more2 = (wr_c + 18'd8)  < j_n;  // prefetch exists (sub 2)
    wire         wr_more3 = (wr_c + 18'd4)  < j_n;  // load prefetch (sub 3)
    wire         wr_last  = (wr_c + 18'd4) >= j_n;  // final emission beat
    wire [18:0]  wr_rem   = {1'b0, j_n} - {1'b0, wr_c};
    wire [2:0]   wr_vcnt  = (wr_rem >= 19'd4) ? 3'd4 : wr_rem[2:0];
    wire [4:0]   wr_strb5 = (5'b00001 << wr_vcnt) - 5'b00001;
    wire [3:0]   wr_strb  = wr_strb5[3:0];

    // 4 parallel saturates of the current sub-beat's lanes
    reg [127:0] y_dat_c;
    integer yi;
    reg signed [63:0] y_full;
    always @* begin
        for (yi = 0; yi < 4; yi = yi + 1) begin
            y_full = ($signed(wr_word[64*(wr_lane0 + {4'b0, yi[1:0]}) +: 64])
                      + j_round) >>> r_sh;
            y_dat_c[32*yi +: 32] =
                (y_full > 64'sd2147483647)  ? 32'h7FFFFFFF
              : (y_full < -64'sd2147483648) ? 32'h80000000
              :                               y_full[31:0];
        end
    end

    // combinational argmax scan of the registered emission beat (used by
    // the S_WRITE block one cycle after y_data_r is registered)
    wire [18:0]  am_rem = {1'b0, j_n} - {1'b0, wr_am_base};
    reg [31:0]  am_bv;
    reg [17:0]  am_bi;
    always @* begin
        am_bv = am_val_r;
        am_bi = am_idx_r;
        if ((am_rem > 19'd0)
            && ((wr_am_base == 18'd0)
                || ($signed(y_data_r[31:0]) > $signed(am_bv)))) begin
            am_bv = y_data_r[31:0];
            am_bi = wr_am_base;
        end
        if ((am_rem > 19'd1)
            && ($signed(y_data_r[63:32]) > $signed(am_bv))) begin
            am_bv = y_data_r[63:32];
            am_bi = wr_am_base + 18'd1;
        end
        if ((am_rem > 19'd2)
            && ($signed(y_data_r[95:64]) > $signed(am_bv))) begin
            am_bv = y_data_r[95:64];
            am_bi = wr_am_base + 18'd2;
        end
        if ((am_rem > 19'd3)
            && ($signed(y_data_r[127:96]) > $signed(am_bv))) begin
            am_bv = y_data_r[127:96];
            am_bi = wr_am_base + 18'd3;
        end
    end

    reg        y_we_r, y_done_r, am_valid_r;
    reg [11:0] y_addr_r;
    reg [127:0] y_data_r;
    reg [3:0]  y_wstrb_r;

    assign y_we     = y_we_r;
    assign y_addr   = y_addr_r;
    assign y_data   = y_data_r;
    assign y_wstrb  = y_wstrb_r;
    assign y_buf    = j_ybuf;
    assign done     = y_done_r;
    assign am_valid = am_valid_r;
    assign am_val   = am_val_r;
    assign am_idx   = am_idx_r;

    // unused job fields (routing lives in the fetch engine / port binding)
    // and unused bits of wider-than-needed signals
    wire _unused = &{1'b0, job_q_addr, job_s_addr, job_z_addr, job_xbuf,
                     job_K[0], job_gsz[0], j_r[7:6], b_row,
                     hz_col[20:18], hz_col[3:0],
                     idx_az[20:11], idx_as[20:12],
                     smac_base_d[15:4], pf_cnt_d[17:6],
                     sw_addr[3:0], zw_addr[3:0], qr_addr[3:0],
                     ld_widx[8], wr_strb5[4],
                     a_kfull[17:5], f_sz64[63:24]};

    // ---------------- sequential process ----------------
    integer i, jj;
    // aligner temps (blocking, single-cycle lifetime, parallel structure)
    reg [4:0]   a_sum;                  // fill + ws_count (0..31)
    reg [17:0]  a_kfull;                // j_n - row_bcnt
    reg         a_rowend;               // a row ends within this beat
    reg         a_full;                 // full-chunk crossing in this beat
    reg [4:0]   a_end_fill;             // staged bytes at row end
    reg         a_part;                 // partial-chunk emit in this beat
    reg [4:0]   a_shift;                // consumed slots (down-shift)
    reg [5:0]   a_jd;                   // per-slot beat index
    reg [255:0] a_vec;                  // appended stage (32 slots)
    reg [255:0] a_shifted;              // next stage after down-shift
    reg         e1_v, e2_v;
    reg         a_re1, a_re2;           // 32B path: row ends at byte 16/32
    reg [15:0]  e1_row, e2_row;
    reg [17:0]  e1_col, e2_col;
    reg [4:0]   e1_cnt, e2_cnt;
    reg [127:0] e1_dat, e2_dat;
    reg [2:0]   n_push;
    // arithmetic temps
    reg signed [5:0]  mac_qlo, mac_qhi; // nibble 0..15 (signed for the mul)
    reg signed [32:0] mac_xe33, mac_xo33;   // int32 exact
    reg signed [33:0] mac_xs;               // xe + xo
    reg signed [39:0] mac_prod;
    reg signed [63:0] f_z, f_s, f_sz64;
    // barrel temps
    reg [255:0]  s_flat, z_flat;
    reg [255:0]  q16;                   // small-N qram read barrel

    always @(posedge clk) begin
        if (!rst_n) begin
            state    <= S_IDLE;
            j_mode   <= 1'b0;
            hq_use_r <= 1'b0;
            j_k2     <= 16'd0;
            j_n      <= 18'd0;
            j_ng     <= 3'd0;
            j_gsz2   <= 8'd0;
            j_r      <= 8'd0;
            j_round  <= 64'd0;
            j_ybuf   <= 4'd0;
            g_cnt    <= 3'd0;
            g_start  <= 16'd0;
            s_base   <= 21'd0;
            z_base   <= 21'd0;
            fill     <= 5'd0;
            q_row    <= 16'd0;
            row_bcnt <= 18'd0;
            cf_rd    <= 3'd0;
            cf_wr    <= 3'd0;
            cf_occ   <= 4'd0;
            b_valid  <= 1'b0;
            b1_valid <= 1'b0;
            b1dA_valid<= 1'b0;
            b1dB_valid<= 1'b0;
            b_pair   <= 1'b0;
            b_row    <= 16'd0;
            b_col    <= 18'd0;
            b_cnt    <= 5'd0;
            b_data   <= 128'd0;
            b_set    <= 1'b0;
            b_gend   <= 1'b0;
            b_col_o  <= 18'd0;
            b_cnt_o  <= 5'd0;
            b_data_o <= 128'd0;
            b_set_o  <= 1'b0;
            b_gend_o <= 1'b0;
            b1_pair  <= 1'b0;
            b1_col_o <= 18'd0;
            b1_cnt_o <= 5'd0;
            b1_set_o <= 1'b0;
            b1_gend_o<= 1'b0;
            b1_prod_o<= 640'd0;
            b1dA_col <= 18'd0;
            b1dA_cnt <= 5'd0;
            b1dA_set <= 1'b0;
            b1dA_gend<= 1'b0;
            b1dA_prod<= 640'd0;
            b1dA_xs  <= 34'd0;
            b1dB_col <= 18'd0;
            b1dB_cnt <= 5'd0;
            b1dB_set <= 1'b0;
            b1dB_gend<= 1'b0;
            b1dB_prod<= 640'd0;
            b1dB_xs  <= 34'd0;
            qwA_fwd_v <= 1'b0;
            qwB_fwd_v <= 1'b0;
            qwA_fwd_addr <= 4'd0;
            qwB_fwd_addr <= 4'd0;
            qwA_fwd_wd <= 1024'd0;
            qwB_fwd_wd <= 1024'd0;
            xsum     <= 64'sd0;
            fold_c   <= 18'd0;
            f1a_v    <= 1'b0;
            f1_v     <= 1'b0;
            f2a_v    <= 1'b0;
            wr_c     <= 18'd0;
            wr_ph    <= 2'd0;
            wr_sub   <= 2'd0;
            wr_am_base <= 18'd0;
            am_val_r <= 32'h80000000;
            am_idx_r <= 18'd0;
            x_addr_r <= 12'd0;
            seg_pos  <= 13'd0;
            ld_stage <= 128'd0;
            ld_flush <= 1'b0;
            pf_cnt   <= 18'd0;
            pf_gbase <= 18'd0;
            pf_run_d <= 1'b0;
            hf_wait  <= 1'b0;
            smac_dv  <= 1'b0;
            y_we_r     <= 1'b0;
            y_done_r   <= 1'b0;
            am_valid_r <= 1'b0;
            y_addr_r   <= 12'd0;
            y_data_r   <= 128'd0;
            y_wstrb_r  <= 4'd0;
        end else begin
`ifdef MSH_DEBUG
            if ((state == S_RUN) && !ws_ready)
                dbg_stall <= dbg_stall + 12'd1;
`endif
            /* verilator lint_off BLKSEQ */
            // temp defaults (single-cycle lifetime, avoid latches)
            a_sum = 5'd0; a_kfull = 18'd0;
            a_rowend = 1'b0; a_full = 1'b0; a_end_fill = 5'd0;
            a_part = 1'b0; a_shift = 5'd0; a_jd = 6'd0;
            a_vec = 256'd0; a_shifted = 256'd0;
            e1_v = 1'b0; e1_row = 16'd0; e1_col = 18'd0;
            e1_cnt = 5'd0; e1_dat = 128'd0;
            e2_v = 1'b0; e2_row = 16'd0; e2_col = 18'd0;
            e2_cnt = 5'd0; e2_dat = 128'd0;
            a_re1 = 1'b0; a_re2 = 1'b0;
            n_push  = 3'd0;
            cf_wr2  = 3'd0;
            mac_xe33  = {x_data_e[31], x_data_e};
            mac_xo33  = {x_data_o[31], x_data_o};
            mac_xs    = $signed({mac_xe33[32], mac_xe33})
                      + $signed({mac_xo33[32], mac_xo33});
            mac_qlo = 6'sd0;
            mac_qhi = 6'sd0;
            mac_prod = 40'sd0;
            f_z    = 64'sd0;
            f_s    = 64'sd0;
            f_sz64 = 64'sd0;
            s_flat = 256'd0; z_flat = 256'd0;
            q16    = 256'd0;

            // -------- head-mode s prefetch (during MAC phase) --------
            // synchronous hs read: hs_addr is issued this cycle, the
            // sbuf_h write lands on the next edge (pf_*_d delays).
            pf_run_d <= pf_run;
            pf_cnt_d <= pf_cnt;
            if (pf_run)
                pf_cnt <= pf_cnt + 18'd1;

            // -------- deferred group-end (head prefetch not done) --------
            if (hf_wait && pf_done) begin
                state   <= S_FOLD;
                fold_c  <= 18'd0;
                hf_wait <= 1'b0;
            end

            // -------- stream intake: segment loads / .q aligner --------
            // Loads stage bytes into ld_stage; the macro word write is
            // combinational (sw/zw/qr_*, <= 1 word per beat). A ws_last
            // beat that completes a word AND leaves a tail defers the
            // tail write one cycle via ld_flush.
            if (ld_flush) begin
                // deferred tail write fires combinationally this cycle
                ld_flush <= 1'b0;
                ld_stage <= 128'd0;
                seg_pos  <= 13'd0;
                if (state == S_LOAD_S) begin
                    state <= S_LOAD_Z;
                end else if (state == S_LOAD_Z) begin
                    state <= (j_n < 18'd16) ? S_SLOAD : S_RUN;
                end else begin
                    smac_r <= 16'd0;
                    state  <= S_SMAC;
                end
            end else if (ld_in) begin
                if (ld_end >= 6'd16)
                    ld_stage <= ld_merged[255:128];
                else
                    ld_stage <= ld_merged[127:0];
                if (ws_last) begin
                    if (ld_cross) begin
                        // completed word writes now; tail deferred
                        ld_flush <= 1'b1;
                        ld_ftail <= ld_merged[255:128];
                        ld_fmask <= (16'h0001 << (ld_end - 6'd16))
                                    - 16'h0001;
                        ld_fwidx <= seg_pos[12:4] + 9'd1;
                    end else begin
                        ld_stage <= 128'd0;
                        seg_pos  <= 13'd0;
                        if (state == S_LOAD_S) begin
                            state <= S_LOAD_Z;
                        end else if (state == S_LOAD_Z) begin
                            state <= (j_n < 18'd16) ? S_SLOAD : S_RUN;
                        end else begin
                            smac_r <= 16'd0;
                            state  <= S_SMAC;
                        end
                    end
                end else begin
                    seg_pos <= seg_pos + {8'b0, ws_count};
                end
            end else if (ws_fire2) begin
                // S_RUN 32B intake (2-beat pop, fill == 0, j_n%16 == 0):
                // the events per cycle are limited to <= 2 chunk emits
                // and <= 2 row ends — 32 bytes are exactly 2 full
                // chunks and row boundaries fall only on 16-byte
                // multiples, so a row can end after byte 16 (a_re1)
                // and/or after byte 32 (a_re2) of the pair, never
                // inside a chunk. e1 is the chunk at row bytes
                // [row_bcnt, +16), e2 the next 16 bytes of the same row
                // or the first chunk of the next row (which itself
                // completes when j_n == 16).
                a_re1    = (row_bcnt + 18'd16 == j_n);
                a_re2    = (a_re1 && (j_n == 18'd16))
                         || (!a_re1 && (row_bcnt + 18'd32 == j_n));
                e1_v     = 1'b1;
                e1_row   = q_row;
                e1_col   = row_bcnt;
                e1_cnt   = 5'd16;
                e1_dat   = beat_sh;
                e2_v     = 1'b1;
                e2_row   = a_re1 ? (q_row + 16'd1) : q_row;
                e2_col   = a_re1 ? 18'd0 : (row_bcnt + 18'd16);
                e2_cnt   = 5'd16;
                e2_dat   = ws2_data;
                q_row    <= q_row + {15'b0, a_re1} + {15'b0, a_re2};
                row_bcnt <= a_re2 ? 18'd0
                          : a_re1 ? 18'd16 : (row_bcnt + 18'd32);
                n_push   = 3'd2;
                // fill stays 0 and no stage bytes are kept, so the next
                // beat (either path) starts from a clean row boundary
            end else if (ws_fire) begin
                // S_RUN: PARALLEL byte aligner -> row-aligned chunks.
                // All per-byte state is computed from registers only
                // (no accumulation across loop iterations):
                //   1. beat bytes barrel-shifted once by ws_shift
                //   2. 32 appended slots computed in parallel
                //      (slot j = stage[j] if j < fill else beat[j-fill])
                //   3. events from single comparisons: row end at
                //      byte k = j_n - row_bcnt (>= 1 event per beat
                //      impossible for j_n >= 16), full-chunk crossing
                //      at fill == 16; both ordered by k vs 16 - fill
                //   4. next stage = one barrel down-shift of the
                //      appended vector past the consumed bytes
                a_sum    = fill + ws_count;
                a_kfull  = j_n - row_bcnt;
                a_rowend = (row_bcnt < j_n)
                         && (j_n <= row_bcnt + {13'b0, ws_count});
                a_full   = (a_sum >= 5'd16)
                         && (!a_rowend
                             || ({1'b0, 5'd16 - fill}
                                 <= {1'b0, a_kfull[4:0]}));
                a_end_fill = fill + a_kfull[4:0]
                           - (a_full ? 5'd16 : 5'd0);
                a_part   = a_rowend && (a_end_fill != 5'd0);
                a_shift  = a_rowend ? (fill + a_kfull[4:0])
                         : a_full   ? 5'd16 : 5'd0;
                // appended stage vector (parallel per-slot muxes)
                for (jj = 0; jj <= 31; jj = jj + 1) begin
                    a_jd = {1'b0, jj[4:0]} - {1'b0, fill};
                    // fill <= 15 always (a full chunk emits at 16), so
                    // this branch only fires for jj <= 14 — the 4-bit
                    // index slice keeps the part-select statically in
                    // bounds (stage_v is 31 bytes) without changing
                    // behavior
                    if ({1'b0, jj[4:0]} < {1'b0, fill})
                        a_vec[8*jj +: 8] = stage_v[8*jj[3:0] +: 8];
                    else if (a_jd < {1'b0, ws_count})
                        a_vec[8*jj +: 8] =
                            beat_sh[{a_jd[3:0], 3'b000} +: 8];
                    else
                        a_vec[8*jj +: 8] = 8'd0;
                end
                // chunk emits (combinational from the parallel state)
                if (a_full) begin
                    e1_v   = 1'b1;
                    e1_row = q_row;
                    e1_col = row_bcnt - {13'b0, fill};
                    e1_cnt = 5'd16;
                    e1_dat = a_vec[127:0];
                end
                if (a_part) begin
                    e2_v   = 1'b1;
                    e2_row = q_row;
                    e2_col = j_n - {13'b0, a_end_fill};
                    e2_cnt = a_end_fill;
                    for (jj = 0; jj < 16; jj = jj + 1)
                        e2_dat[8*jj +: 8] =
                            ({1'b0, jj[3:0]} < a_end_fill)
                            ? (a_full ? a_vec[8*(jj + 16) +: 8]
                                      : a_vec[8*jj +: 8])
                            : 8'd0;
                end
                // next aligner state (one barrel shift + counters)
                a_shifted = a_vec >> {a_shift, 3'b000};
                for (jj = 0; jj <= 30; jj = jj + 1)
                    stage_v[8*jj +: 8] <= a_shifted[8*jj +: 8];
                fill <= a_rowend ? (ws_count - a_kfull[4:0])
                      : a_full   ? (a_sum - 5'd16) : a_sum;
                row_bcnt <= a_rowend
                          ? {13'b0, ws_count - a_kfull[4:0]}
                          : (row_bcnt + {13'b0, ws_count});
                q_row  <= q_row + {15'b0, a_rowend};
                n_push = {2'b0, e1_v} + {2'b0, e2_v};
            end

            // -------- chunk FIFO push / pop --------
            if (smac_dv) begin
                // small-N inject: row data returned from qram (issued
                // one cycle earlier by smac_issue)
                cf_row_v[16*cf_wr +: 16] <= smac_r_d;
                cf_col_v[18*cf_wr +: 18] <= 18'd0;
                cf_cnt_v[5*cf_wr +: 5]   <= {1'b0, j_n[3:0]};
                q16 = {qr_hi, qr_lo} >> {smac_base_d[3:0], 3'b000};
                for (i = 0; i < 16; i = i + 1)
                    cf_dat_v[128*cf_wr + 8*i +: 8] <=
                        ({14'b0, i[3:0]} < j_n)
                        ? q16[8*i +: 8] : 8'd0;
                cf_wr  <= cf_wr + 3'd1;
                cf_occ <= cf_occ + 4'd1 - {1'b0, a_pop};
                if (a_load) cf_rd <= cf_rd + a_pop;
            end else begin
                if (e1_v) begin
                    cf_row_v[16*cf_wr +: 16] <= e1_row;
                    cf_col_v[18*cf_wr +: 18] <= e1_col;
                    cf_cnt_v[5*cf_wr +: 5]   <= e1_cnt;
                    cf_dat_v[128*cf_wr +: 128] <= e1_dat;
                end
                cf_wr2 = cf_wr + {2'b0, e1_v};
                if (e2_v) begin
                    cf_row_v[16*cf_wr2 +: 16] <= e2_row;
                    cf_col_v[18*cf_wr2 +: 18] <= e2_col;
                    cf_cnt_v[5*cf_wr2 +: 5]   <= e2_cnt;
                    cf_dat_v[128*cf_wr2 +: 128] <= e2_dat;
                end
`ifdef MSH_DEBUG
                if ((e1_v || e2_v) && (state == S_RUN))
                    $display("[gemv] cfpush cyc=%0d e1v=%0d e2v=%0d wr2=%0d e1(r=%0d c=%0d n=%0d d0=%08x) e2(r=%0d c=%0d n=%0d d0=%08x) wr=%0d occ=%0d",
                             dbg_cyc, e1_v, e2_v, cf_wr2, e1_row, e1_col, e1_cnt, e1_dat[31:0],
                             e2_row, e2_col, e2_cnt, e2_dat[31:0], cf_wr, cf_occ);
`endif
                cf_wr  <= cf_wr + n_push;
                cf_occ <= cf_occ + {1'b0, n_push} - {1'b0, a_pop};
                if (a_load) cf_rd <= cf_rd + a_pop;
            end

            // -------- small-N inject issue (address + delay regs) --------
            if (smac_issue) begin
                smac_dv     <= 1'b1;
                smac_base_d <= smac_base;
                smac_r_d    <= smac_r;
                smac_r      <= smac_r + 16'd1;
            end else begin
                smac_dv     <= 1'b0;
            end

            // -------- stage A: pop 1-2 chunks, issue ONE x read ------
            // a pair shares its row's x read: xe/xo serve both chunks
            if (a_load) begin
                b_valid  <= 1'b1;
                b_pair   <= a_pair;
                b_row    <= cfr_row;
                b_col    <= cfr_col;
                b_cnt    <= cfr_cnt;
                b_data   <= cfr_dat;
                b_set    <= (cfr_row == g_start);
                b_gend   <= (cfr_row == ge_row)
                         && ((cfr_col + {13'b0, cfr_cnt}) == j_n);
                b_col_o  <= cfr1_col;
                b_cnt_o  <= cfr1_cnt;
                b_data_o <= cfr1_dat;
                b_set_o  <= (cfr1_row == g_start);
                b_gend_o <= (cfr1_row == ge_row)
                         && ((cfr1_col + {13'b0, cfr1_cnt}) == j_n);
                x_addr_r <= cfr_row[11:0];
`ifdef MSH_DEBUG
                if (state == S_RUN) begin
                    $display("[gemv] cfpop cyc=%0d pair=%0d c0(r=%0d c=%0d n=%0d d0=%08x) c1(r=%0d c=%0d n=%0d d0=%08x) rd=%0d occ=%0d",
                             dbg_cyc, a_pair, cfr_row, cfr_col, cfr_cnt, cfr_dat[31:0],
                             cfr1_row, cfr1_col, cfr1_cnt, cfr1_dat[31:0], cf_rd, cf_occ);
                    $display("[gemv] cfdump wr=%0d s0(c=%0d,n=%0d) s1(c=%0d,n=%0d) s2(c=%0d,n=%0d) s3(c=%0d,n=%0d) s4(c=%0d,n=%0d) s5(c=%0d,n=%0d) s6(c=%0d,n=%0d) s7(c=%0d,n=%0d)",
                             cf_wr,
                             cf_col_v[17:0], cf_cnt_v[4:0],
                             cf_col_v[35:18], cf_cnt_v[9:5],
                             cf_col_v[53:36], cf_cnt_v[14:10],
                             cf_col_v[71:54], cf_cnt_v[19:15],
                             cf_col_v[89:72], cf_cnt_v[24:20],
                             cf_col_v[107:90], cf_cnt_v[29:25],
                             cf_col_v[125:108], cf_cnt_v[34:30],
                             cf_col_v[143:126], cf_cnt_v[39:35]);
                end
`endif
            end else begin
                b_valid <= 1'b0;
            end

            // -------- stage B1: 32-lane multiply (registered) --------
            // exact-width multipliers: nibble (6b signed, 0..15) x x (33b
            // signed = int32 exact) -> 40b product. The accumulate lives
            // in B2 so the multiply owns the whole cycle (timing). The
            // pair's odd chunk gets its own 16 lanes sharing xe/xo.
            if (b_valid) begin
                for (i = 0; i < 16; i = i + 1) begin
                    mac_qlo  = {2'b0, b_data[8*i+3 -: 4]};
                    mac_qhi  = {2'b0, b_data[8*i+7 -: 4]};
                    // 6b x 33b multiplies (operands at true widths; the
                    // 40b sign-extension context would build 40x40s)
                    mac_prod = mac_qlo * mac_xe33 + mac_qhi * mac_xo33;
                    b1_prod[40*i +: 40] <= mac_prod;
                    mac_qlo  = {2'b0, b_data_o[8*i+3 -: 4]};
                    mac_qhi  = {2'b0, b_data_o[8*i+7 -: 4]};
                    mac_prod = mac_qlo * mac_xe33 + mac_qhi * mac_xo33;
                    b1_prod_o[40*i +: 40] <= mac_prod;
                end
                b1_xs    <= mac_xs;
                b1_col   <= b_col;
                b1_cnt   <= b_cnt;
                b1_set   <= b_set;
                b1_gend  <= b_gend;
                b1_pair  <= b_pair;
                b1_col_o <= b_col_o;
                b1_cnt_o <= b_cnt_o;
                b1_set_o <= b_set_o;
                b1_gend_o <= b_gend_o;
                b1_valid <= 1'b1;
            end else begin
                b1_valid <= 1'b0;
            end

            // -------- stage B2: qacc accumulate (2-phase RMW per macro)
            // Each channel registers the chunk routed to its macro at b1
            // (its qacc read was issued combinationally that cycle) and
            // merges+writes the returned word one cycle later. A pair
            // always engages BOTH macros (one even + one odd word), so
            // there is no port conflict; a single chunk uses whichever
            // macro its column parity selects.
            if (b1A_v) begin
                b1dA_col   <= b1_colA;
                b1dA_cnt   <= b1_cntA;
                b1dA_set   <= b1_setA;
                b1dA_gend  <= b1_gendA;
                b1dA_prod  <= b1_prodA;
                b1dA_xs    <= b1_xs;
                b1dA_valid <= 1'b1;
            end else begin
                b1dA_valid <= 1'b0;
            end
            if (b1B_v) begin
                b1dB_col   <= b1_colB;
                b1dB_cnt   <= b1_cntB;
                b1dB_set   <= b1_setB;
                b1dB_gend  <= b1_gendB;
                b1dB_prod  <= b1_prodB;
                b1dB_xs    <= b1_xs;
                b1dB_valid <= 1'b1;
            end else begin
                b1dB_valid <= 1'b0;
            end
            qwA_fwd_v <= qwA_we;
            if (qwA_we) begin
                qwA_fwd_addr <= qwA_waddr;
                qwA_fwd_wd   <= qwA_wd_r;
            end
            qwB_fwd_v <= qwB_we;
            if (qwB_we) begin
                qwB_fwd_addr <= qwB_waddr;
                qwB_fwd_wd   <= qwB_wd_r;
            end
            // xsum: one xe+xo per row, taken from the col==0 chunk (a
            // pair's col==0 chunk is always on the even macro; the odd
            // channel never carries col==0 — j_n == 16 single-group
            // rows cannot form a pair, so the single path handles them)
            if (b1dA_valid && (b1dA_col == 18'd0)) begin
                if (b1dA_set) xsum <= {{30{b1dA_xs[33]}}, b1dA_xs};
                else          xsum <= xsum + {{30{b1dA_xs[33]}}, b1dA_xs};
            end
            if (b1dB_valid && (b1dB_col == 18'd0)) begin
                if (b1dB_set) xsum <= {{30{b1dB_xs[33]}}, b1dB_xs};
                else          xsum <= xsum + {{30{b1dB_xs[33]}}, b1dB_xs};
            end
            // group end: the gend chunk is the last of the row pass; a
            // pair retires both channels in the same cycle, so waiting
            // for the gend channel's writeback retires both
            if (gend_ret) begin
                if (!j_mode || pf_done) begin
                    state   <= S_FOLD;
                    fold_c  <= 18'd0;
                end else begin
                    hf_wait <= 1'b1;
                end
            end
`ifdef MSH_DEBUG
            if (b1dA_valid)
                $display("[gemv] macA c=%0d cnt=%0d set=%0d gend=%0d prod0=%0d",
                         b1dA_col, b1dA_cnt, b1dA_set, b1dA_gend,
                         $signed(b1dA_prod[39:0]));
            if (b1dB_valid)
                $display("[gemv] macB c=%0d cnt=%0d set=%0d gend=%0d prod0=%0d",
                         b1dB_col, b1dB_cnt, b1dB_set, b1dB_gend,
                         $signed(b1dB_prod[39:0]));
`endif

            // -------- FOLD (4-stage pipeline, initiation interval 1) ----
            // acc64[c] += s*(qacc - z*xsum) computed as the EXACT integer
            // identity s*qacc - (s*z)*xsum so the two 64-bit multiplies
            // are parallel instead of cascaded. All operand reads are
            // synchronous macro reads:
            //   F1a: issue addresses (row: s/z barrel words; head: sbuf_h
            //        + hz; qacc/acc words), register block metadata
            //   F1b: barrel the returned words, sz = s*z per lane
            //   F2:  t1 = s*qacc, t2 = sz*xsum  (independent multipliers)
            //   F3:  acc64 = base + t1 - t2     (base = 0 for group 0,
            //        combinational aw_we/aw_wd writeback)
            // Consecutive blocks touch disjoint acc words; the next
            // group's F1a reads acc words written by the previous group's
            // F3 many cycles earlier (the MAC phase separates them), so
            // there is no RMW hazard.
            if (state == S_FOLD) begin
                // ---- F1a: issue all reads (one block per cycle) ----
                if (fold_c < j_n) begin
                    f1a_col  <= fold_c;
                    f1a_g0   <= (g_cnt == 3'd0);
                    f1a_last <= (fold_c + 18'd16 >= j_n);
                    f1a_zsh  <= idx_az[3:0];
                    f1a_ssh  <= idx_as[3:0];
                    f1a_v    <= 1'b1;
                    fold_c   <= fold_c + 18'd16;
                end else begin
                    f1a_v    <= 1'b0;
                end
                // ---- F1b: barrel + s*z ----
                if (f1a_v) begin
                    if (!j_mode) begin
                        z_flat = ({zw_hi, zw_lo} >> {f1a_zsh, 3'b000});
                        s_flat = ({sw_hi, sw_lo} >> {f1a_ssh, 3'b000});
                    end else begin
                        z_flat = {128'd0, hz_data};
                        s_flat = sh_rd;
`ifdef MSH_DEBUG
                        if (f1a_col >= 18'd98288 && f1a_col <= 18'd98352) begin
                            $display("[gemv] F1 gc=%0d c=%0d s0=%04x s1=%04x z0=%02x z1=%02x qw0=%016x xsum=%016x",
                                     g_cnt, f1a_col,
                                     s_flat[15:0], s_flat[31:16],
                                     z_flat[7:0], z_flat[15:8],
                                     qw_rd[63:0], xsum);
                        end
`endif
                    end
                    for (i = 0; i < 16; i = i + 1) begin
                        f_z = {56'b0, z_flat[8*i +: 8]};
                        f_s = {{48{s_flat[16*i+15]}},
                               s_flat[16*i +: 16]};
                        f_sz64 = f_s * f_z;
                        f1_s[16*i +: 16]  <= f_s[15:0];
                        f1_sz[24*i +: 24] <= f_sz64[23:0];
                    end
                    f1_qw   <= qw_rd;
                    f1_aw   <= aw_rd;
                    f1_col  <= f1a_col;
                    f1_g0   <= f1a_g0;
                    f1_last <= f1a_last;
                    f1_v    <= 1'b1;
                end else begin
                    f1_v    <= 1'b0;
                end
                // ---- F2: 16-lane multiplies, one block/cycle --------
                if (f1_v) begin
                    f2a_t1   <= f2m_t1[511:0];
                    f2a_t2   <= f2m_t2[511:0];
                    f2a_base <= f1_g0 ? 1024'd0 : f1_aw;
                    f2a_col  <= f1_col;
                    f2a_last <= f1_last;
                    f2b_t1   <= f2m_t1[1023:512];
                    f2b_t2   <= f2m_t2[1023:512];
                    f2a_v    <= 1'b1;
                end else begin
                    f2a_v    <= 1'b0;
                end
                // ---- F3: combine + writeback (aw_we/aw_wd comb) ----
                if (f2a_v) begin
                    if (f2a_last) begin
                        if (g_cnt == j_ng - 3'd1) begin
                            state <= S_WRITE;
                            wr_c  <= 18'd0;
                            wr_ph <= 2'd0;
                            wr_sub <= 2'd0;
                        end else begin
                            g_cnt    <= g_cnt + 3'd1;
                            g_start  <= g_start + {8'b0, j_gsz2};
                            s_base   <= s_base + {2'b0, j_n, 1'b0};
                            z_base   <= z_base + {3'b0, j_n};
                            pf_cnt   <= 18'd0;
                            pf_gbase <= pf_gbase + {3'b0, j_n[17:3]};
                            fold_c   <= 18'd0;
                                            // small-N jobs (N<16) inject from qram in
                            // S_SMAC; S_RUN would wait for a weight
                            // stream that S_SLOAD already consumed
                            state    <= (j_n < 18'd16) ? S_SMAC : S_RUN;
                        end
                    end
                end
            end

`ifdef MSH_DEBUG
            if ((state == S_FOLD) && f1a_v && (f1a_col == 18'd0)
                && (g_cnt == 3'd0))
                $display("[gemv] fold qacc0=%016x xsum=%016x z0=%02x s0=%04x",
                         qw_rd[63:0], xsum, zw_lo[7:0], sw_lo[15:0]);
`endif
            // -------- WRITE: y = sat32((acc + 2^(R-1)) >> R), 4/cycle --------
            // pulse defaults (single-cycle outputs)
            y_we_r     <= 1'b0;
            y_done_r   <= 1'b0;
            am_valid_r <= 1'b0;
            if (state == S_WRITE) begin
                if (wr_ph == 2'd0) begin
                    // issue the read of acc word 0 (aw_raddr comb = 0)
                    wr_ph <= 2'd1;
                end else if (wr_ph == 2'd1) begin
                    // word 0 returned; hold it for the 4 sub-beats
                    wr_word <= aw_rd;
                    wr_ph   <= 2'd2;
                end else begin
                    // emission beat: 4 lanes of wr_word
                    y_we_r     <= 1'b1;
                    y_addr_r   <= wr_c[11:0];
                    y_data_r   <= y_dat_c;
                    y_wstrb_r  <= wr_strb;
                    y_done_r   <= wr_last;
                    am_valid_r <= j_mode;
                    wr_am_base <= wr_c;
                    wr_c       <= wr_c + 18'd4;
                    wr_sub     <= wr_sub + 2'd1;
                    // load the prefetched next-group word (issued at
                    // sub-beat 2 when more groups remain)
                    if ((wr_sub == 2'd3) && wr_more3)
                        wr_word <= aw_rd;
                    if (wr_last)
                        state <= S_IDLE;
                end
            end
            // running argmax over the registered emission beat (one cycle
            // after y_data_r, same lag as before widening; strictly-
            // greater => lowest-index tie; lane 0 of the first beat seeds
            // unconditionally since a logit can be INT32_MIN)
            if (y_we_r && j_mode) begin
                am_val_r <= am_bv;
                am_idx_r <= am_bi;
            end

`ifdef MSH_DEBUG
            if (j_mode && (state == S_RUN) && (dbg_cyc[6:0] == 7'd0))
                $display("[gemv] hqst rbc=%0d qr=%0d jn=%0d jk2=%0d fill=%0d occ=%0d",
                         row_bcnt, q_row, j_n, j_k2, fill, cf_occ);
            if (state != dbg_state_d)
                $display("[gemv] cyc=%0d STATE %0d -> %0d", dbg_cyc,
                         dbg_state_d, state);
            dbg_state_d <= state;
`endif
            // -------- job accept --------
            if ((state == S_IDLE) && job_valid) begin
                j_mode   <= job_mode;
                hq_use_r <= job_mode && hq_fill_done;
                j_k2     <= {1'b0, job_K[15:1]};
                j_n      <= job_N;
                j_ng     <= job_ng;
                j_r      <= job_R;
                j_round  <= 64'sd1 <<< (job_R[5:0] - 6'd1);
                j_gsz2   <= {1'b0, job_gsz[7:1]};
                j_ybuf   <= job_ybuf;
                g_cnt    <= 3'd0;
                g_start  <= 16'd0;
                s_base   <= 21'd0;
                z_base   <= 21'd0;
                fill     <= 5'd0;
                q_row    <= 16'd0;
                row_bcnt <= 18'd0;
                cf_rd    <= 3'd0;
                cf_wr    <= 3'd0;
                cf_occ   <= 4'd0;
                b_valid  <= 1'b0;
                b1_valid <= 1'b0;
                b1dA_valid<= 1'b0;
                b1dB_valid<= 1'b0;
                b_pair   <= 1'b0;
                b1_pair  <= 1'b0;
                qwA_fwd_v <= 1'b0;
                qwB_fwd_v <= 1'b0;
                xsum     <= 64'sd0;
                fold_c   <= 18'd0;
                f1a_v    <= 1'b0;
                f1_v     <= 1'b0;
                f2a_v    <= 1'b0;
                    wr_c     <= 18'd0;
                wr_ph    <= 2'd0;
                wr_sub   <= 2'd0;
                wr_am_base <= 18'd0;
                am_val_r <= 32'h80000000;
                am_idx_r <= 18'd0;
                seg_pos  <= 13'd0;
                ld_stage <= 128'd0;
                ld_flush <= 1'b0;
                pf_run_d <= 1'b0;
                smac_dv  <= 1'b0;
                state    <= job_mode ? S_RUN : S_LOAD_S;
                smac_r   <= 16'd0;
                pf_cnt   <= 18'd0;
                pf_gbase <= 18'd0;
                hf_wait  <= 1'b0;
            end
            /* verilator lint_on BLKSEQ */
        end
    end

endmodule

`default_nettype wire
