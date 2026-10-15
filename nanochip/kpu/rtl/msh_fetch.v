// msh_fetch.v -- DRAM fetch / posted-write engine + byte-stream aligner.
//
// Part of msh_chip_top (see docs/interface.md).
// Single clock, active-low synchronous reset. Verilog-2005 subset accepted
// by both Verilator 5.044 and Yosys 0.62 (read_verilog -sv).
//
// What it does:
//   1. Accepts read segments (true byte address + byte length + tag) into a
//      64-entry FWFT queue. Zero-length segments are skipped silently.
//   2. Issues ceil((addr[3:0]+len)/16) 16B-aligned read requests per segment,
//      <=1 request/cycle, while (in-flight + FIFO occupancy) < FIFO_DEPTH.
//      Responses arrive in order and fill pre-allocated FIFO slots, so a
//      committed response always fits and mem_rsp_ready is tied high.
//   3. Drains the FIFO as a byte stream, one beat per 16B read, never
//      merging beats of different segments.
//   4. Posted writes arbitrate onto the single request port with priority
//      over reads (reads simply wait one cycle); writes never corrupt the
//      read stream.
//
// Byte-stream beat contract (consumer side):
//   bs_data  : raw 16-byte aligned beat starting at floor16(seg_addr)+16*i
//   bs_first : first beat of a segment
//   bs_last  : last beat of a segment
//   bs_tag   : segment tag
//   bs_shift : byte offset of the segment's first byte within the beat
//              (first beat only; 0 on every other beat)
//   bs_count : number of segment bytes carried by this beat (1..16):
//                first & last : seg_len                       (<= 16)
//                last         : (seg_addr[3:0]+seg_len) mod 16, 0 -> 16
//                first        : 16 - seg_addr[3:0]
//                middle       : 16
//
// Storage (macros_only rule): the response FIFO is TWO harness msh_sram
// macros (256 x 256b data + 256 x 32b meta — same total bits as the old
// 256-deep organization, two beats per word). Meta and data are written
// at different times (request issue vs response fill) into the word
// half selected by the pointer's low bit, using disjoint byte strobes.
// The segment queue is packed vectors.
// The macro's synchronous read is hidden behind a 2-word skid queue:
// rd_ptr counts beats and advances by 1 or 2 at load issue, the queue
// feeds the FWFT consumer interface at full rate (back-to-back pops,
// 1 or 2 beats per pop), and loaded words live in registers so no RAM
// slots are reserved (fifo_room = occ < 256).
//
// Reset policy (randreset gate): every control flop is reset. The FIFO
// macro is additionally cleared by a 256-cycle write loop right after
// reset (clr_active), so even raw contents are deterministic; the module
// holds seg_ready/wr_ready low and issues no requests until the clear
// completes.

`default_nettype none

module msh_fetch (
    input  wire         clk,
    input  wire         rst_n,
    // external memory port (128-bit, 16B aligned, in-order read responses)
    output wire         mem_req_valid,
    input  wire         mem_req_ready,
    output wire         mem_req_write,
    output wire [35:0]  mem_req_addr,
    output wire [127:0] mem_req_wdata,
    output wire [15:0]  mem_req_wstrb,
    input  wire         mem_rsp_valid,
    output wire         mem_rsp_ready,
    input  wire [127:0] mem_rsp_rdata,
    // segment queue input (from sequencer)
    input  wire         seg_valid,
    output wire         seg_ready,
    input  wire [35:0]  seg_addr,
    input  wire [31:0]  seg_len,
    input  wire [3:0]   seg_tag,
    // byte-stream output (to consumers)
    output wire         bs_valid,
    input  wire         bs_ready,
    output wire [127:0] bs_data,
    output wire         bs_first,
    output wire         bs_last,
    output wire [3:0]   bs_tag,
    output wire [3:0]   bs_shift,
    output wire [4:0]   bs_count,
    // second beat of the byte stream (the beat AFTER the bs_* one):
    // bs2_valid implies bs_valid; a consumer asserting bs2_ready pops
    // BOTH beats and must not assert bs_ready in the same cycle
    output wire         bs2_valid,
    input  wire         bs2_ready,
    output wire [127:0] bs2_data,
    output wire         bs2_first,
    output wire         bs2_last,
    output wire [3:0]   bs2_tag,
    output wire [3:0]   bs2_shift,
    output wire [4:0]   bs2_count,
    // posted-write channel (from sequencer)
    input  wire         wr_valid,
    output wire         wr_ready,
    input  wire [35:0]  wr_addr,
    input  wire [127:0] wr_data,
    input  wire [15:0]  wr_wstrb,
    // head-q shadow channel (to the gemv head job): the head weight
    // tensor is token-independent, so its segment (TG_HQ) is fetched
    // ONCE per run and stays resident in a 16 KiB shadow buffer;
    // responses for that contiguous request span are diverted out of
    // the FIFO (meta[15] marks those beats as stream-skips). The head
    // job drains the buffer at 2 beats/cycle instead of re-streaming
    // the same 16 KiB from DRAM every token.
    output wire         hq_fill_done,
    output wire         hq_v,           // >=1 beat valid
    output wire         hq_v2,          // >=2 beats valid
    output wire [127:0] hq_d0,
    output wire [127:0] hq_d1,
    output wire         hq_f0,          // beat0 is the segment's first
    output wire         hq_l0,          // beat0 is the segment's last
    output wire         hq_l1,          // beat1 is the segment's last
    output wire [3:0]   hq_sh0,         // beat0 shift (first beat only)
    output wire [4:0]   hq_c0,
    output wire [4:0]   hq_c1,
    input  wire         hq_pop,         // pop 1 beat
    input  wire         hq_pop2,        // pop 2 beats
    // rewind the reader for the next token's head job (the same
    // resident segment is re-read every token)
    input  wire         hq_rewind
);

    localparam [9:0] FIFO_DEPTH = 10'd256;   // response FIFO, in beats
                                             // (trimmed 512->256 for the
                                             // 4.0 mm2 area budget; still
                                             // covers one full q segment
                                             // plus the in-flight window)

    // ----------------------------------------------------------------
    // Storage
    //   FIFO payload:  msh_sram 128 x 256b (two 128b beats per word;
    //     a response fill writes the half selected by fill_ptr[0])
    //   FIFO metadata: msh_sram 128 x 32b (two 15b metas, {1'b0, meta}
    //     per half; written at request issue) — separate macros because
    //     a response fill and a meta write can land on the same cycle
    //     (one write port per macro).
    //   segment queue: packed vectors (async FWFT head read)
    // ----------------------------------------------------------------
    wire [14:0] iss_meta;                   // composed below
    wire         fdata_we    = clr_active || (mem_rsp_valid && !clr_active);
    wire [6:0]   fdata_waddr = clr_active ? clr_cnt[6:0] : fill_ptr[7:1];
    wire [255:0] fdata_wd    = clr_active ? 256'd0 : {2{mem_rsp_rdata}};
    wire [31:0]  fdata_wstrb = clr_active ? 32'hFFFFFFFF
                             : fill_ptr[0] ? 32'hFFFF0000 : 32'h0000FFFF;
    wire [255:0] fdata_rd;
    msh_sram #(.DEPTH(128), .WIDTH(256)) u_fifo_data (
        .clk(clk), .we(fdata_we), .waddr(fdata_waddr), .wdata(fdata_wd),
        .wstrb(fdata_wstrb),
        .re(1'b1), .raddr(rd_ptr[7:1]), .rdata(fdata_rd));

    wire        fmeta_we    = clr_active || (issue_fire && !clr_active);
    wire [6:0]  fmeta_waddr = clr_active ? clr_cnt[6:0] : wr_ptr[7:1];
    // meta[15] of each half: stream-skip flag (TG_HQ shadow beats)
    wire        iss_hq      = (iss_tag == 4'd10);
    wire [31:0] fmeta_wd    = clr_active ? 32'd0 : {2{iss_hq, iss_meta}};
    wire [3:0]  fmeta_wstrb = clr_active ? 4'b1111
                            : wr_ptr[0] ? 4'b1100 : 4'b0011;
    wire [31:0] fmeta_rd;
    msh_sram #(.DEPTH(128), .WIDTH(32)) u_fifo_meta (
        .clk(clk), .we(fmeta_we), .waddr(fmeta_waddr), .wdata(fmeta_wd),
        .wstrb(fmeta_wstrb),
        .re(1'b1), .raddr(rd_ptr[7:1]), .rdata(fmeta_rd));

    reg [2303:0] sq_addr_v;             // 64 x 36b
    reg [2047:0] sq_len_v;              // 64 x 32b
    reg [255:0]  sq_tag_v;              // 64 x 4b

    // ----------------------------------------------------------------
    // head-q shadow buffer (see module header): responses for the HQ
    // segment's responses are written to this 16 KiB shadow by the
    // DRAIN as it passes their skip-flagged FIFO slots (drain order ==
    // request order, so no response-index bookkeeping is needed; the
    // 256-deep FIFO's pointer wraps cannot alias anything).
    // ----------------------------------------------------------------
    reg  [10:0] hq_nbeats;              // HQ span in beats (0 = none)
    reg  [10:0] hq_fill;                // shadow beats written so far
    reg  [4:0]  hq_seg_len;             // segment byte length (<=16 case only)
    reg  [4:0]  hq_lastcnt;             // valid bytes in the last beat
    wire        hq_first_issue = issue_fire && (iss_tag == 4'd10)
                               && iss_first;
    assign      hq_fill_done = (hq_nbeats != 11'd0)
                           && (hq_fill >= hq_nbeats);
    // drain-steered shadow fill: skip-flagged (HQ) halves are paired
    // into full 256b words by a 1-half staging register before writing
    // (drain order == request order; mid-word span boundaries and
    // odd-length tails stay correct with no port conflicts). Only the
    // NEWLY loaded halves count: a stalled drain loads a word as two
    // single-beat straddles, and hq_skips alone would double-count.
    wire [1:0]   hq_skips = {fmeta_rd[31], fmeta_rd[15]};
    wire [1:0]   hq_new   = ld_v & hq_skips;
    reg          hq_stage_v;
    reg  [127:0] hq_stage;
    wire [10:0]  hq_arr   = hq_fill + {10'b0, hq_stage_v};
    wire         hq_flush = hq_stage_v && (hq_arr == hq_nbeats);
    wire         hq_we    = (ld_dv && (hq_fill < hq_nbeats)
                             && (hq_new == 2'b11
                                 || ((hq_new != 2'b00) && hq_stage_v)))
                         || hq_flush;
    wire [8:0]   hq_waddr = hq_fill[9:1];
    wire [255:0] hq_wd   = hq_flush ? {2{hq_stage}}
                         : (hq_new == 2'b11) && !hq_stage_v ? fdata_rd
                         : hq_new[0] ? {fdata_rd[127:0], hq_stage}
                         :               {fdata_rd[255:128], hq_stage};
    wire [31:0]  hq_wstrb = hq_flush
                            ? (hq_fill[0] ? 32'hFFFF0000 : 32'h0000FFFF)
                            : 32'hFFFFFFFF;
    wire [255:0] hq_rd;
    reg  [8:0]  hq_rword;               // skid window: next word to load
    msh_sram #(.DEPTH(512), .WIDTH(256)) u_hqbuf (
        .clk(clk),
        .we(hq_we), .waddr(hq_waddr), .wdata(hq_wd),
        .wstrb(hq_wstrb),
        .re(1'b1), .raddr(hq_rword), .rdata(hq_rd));

    // reader: 2-word skid behind the synchronous macro read (the head
    // job pops 1 or 2 beats/cycle while valid; meta is composed on the
    // fly from the pop counters, no per-beat storage needed)
    reg  [255:0] hq_w0, hq_w1;
    reg  [1:0]   hq_w0_v, hq_w1_v;      // per-half beat-valid masks
    reg          hq_ld_dv;
    reg  [3:0]   hq_shift;              // seg_addr[3:0] at issue
    reg  [10:0]  hq_popb;               // beats popped so far
    wire [10:0]  hq_rem   = hq_nbeats - hq_popb;   // beats left
    wire [9:0]   hq_nwords = hq_nbeats[10:1] + {9'b0, hq_nbeats[0]};
    // presentation (collapses through empty words; beat1 may straddle
    // into the second skid word)
    wire [1:0]   hq_pv_v = (hq_w0_v != 2'b00) ? hq_w0_v : hq_w1_v;
    wire [255:0] hq_pv_d = (hq_w0_v != 2'b00) ? hq_w0 : hq_w1;
    assign      hq_v    = hq_fill_done && (hq_rem != 11'd0)
                        && (hq_pv_v != 2'b00);
    assign      hq_v2   = (hq_pv_v == 2'b11) ? hq_v
                        : hq_v && (hq_w0_v != 2'b00) && (hq_w1_v != 2'b00);
    assign      hq_d0   = hq_pv_v[0] ? hq_pv_d[127:0] : hq_pv_d[255:128];
    assign      hq_d1   = (hq_pv_v == 2'b11) ? hq_pv_d[255:128]
                        : (hq_w1_v[0] ? hq_w1[127:0] : hq_w1[255:128]);
    assign      hq_f0   = (hq_popb == 11'd0);
    assign      hq_l0   = (hq_rem == 11'd1);
    assign      hq_l1   = (hq_rem == 11'd2);
    assign      hq_sh0  = hq_f0 ? hq_shift : 4'd0;
    assign      hq_c0   = hq_f0 ? (hq_l0 ? hq_seg_len[4:0]
                                         : (5'd16 - {1'b0, hq_shift}))
                        : (hq_l0 ? hq_lastcnt : 5'd16);
    assign      hq_c1   = hq_l1 ? hq_lastcnt : 5'd16;
    // skid next-state (mirrors the byte-stream skid incl. straddle)
    reg  [1:0]   hq_nv0_v, hq_nv1_v;
    reg  [255:0] hq_nd0, hq_nd1;
    wire [1:0]   hq_ld_v  = (({1'b0, hq_rword} == hq_nwords - 10'd1)
                             && hq_nbeats[0]) ? 2'b01 : 2'b11;
    wire         hq_ld_fire = hq_fill_done
                            && ({1'b0, hq_rword} < hq_nwords)
                            && ((hq_nv0_v == 2'b00) || (hq_nv1_v == 2'b00));
    always @* begin
        hq_nv0_v = hq_w0_v; hq_nd0 = hq_w0;
        hq_nv1_v = hq_w1_v; hq_nd1 = hq_w1;
        if ((hq_nv0_v == 2'b00) && (hq_nv1_v != 2'b00)) begin
            hq_nv0_v = hq_nv1_v; hq_nd0 = hq_nd1; hq_nv1_v = 2'b00;
        end
        if (hq_pop2) begin
            if (hq_nv0_v == 2'b11) begin
                hq_nv0_v = hq_nv1_v; hq_nd0 = hq_nd1; hq_nv1_v = 2'b00;
            end else if (hq_nv1_v == 2'b11) begin
                hq_nv0_v = 2'b10; hq_nd0 = hq_nd1; hq_nv1_v = 2'b00;
            end else begin
                hq_nv0_v = 2'b00; hq_nv1_v = 2'b00;
            end
        end else if (hq_pop) begin
            if (hq_nv0_v == 2'b11) hq_nv0_v = 2'b10;
            else begin
                hq_nv0_v = hq_nv1_v; hq_nd0 = hq_nd1; hq_nv1_v = 2'b00;
            end
        end
        if (hq_ld_dv) begin
            if (hq_nv0_v == 2'b00) begin
                hq_nv0_v = hq_ld_v; hq_nd0 = hq_rd;
            end else begin
                hq_nv1_v = hq_ld_v; hq_nd1 = hq_rd;
            end
        end
    end

    // ----------------------------------------------------------------
    // Pointers / counters (FIFO pointers have one extra wrap bit)
    // ----------------------------------------------------------------
    reg [9:0] wr_ptr;    // slot allocated at request-accept time
    reg [9:0] fill_ptr;  // slot filled when its response arrives (in order)
    reg [9:0] rd_ptr;    // prefetch pointer (advances into the out register)
    reg [6:0] sq_wr, sq_rd;

    // reserved = in-flight reads + FIFO occupancy; the skid queue holds
    // loaded words in registers, not RAM slots
    wire [9:0] occ       = wr_ptr - rd_ptr;
    wire       fifo_room = (occ < FIFO_DEPTH);

    wire sq_full     = (sq_wr[5:0] == sq_rd[5:0]) && (sq_wr[6] != sq_rd[6]);
    wire sq_nonempty = (sq_wr != sq_rd);

    // ----------------------------------------------------------------
    // Post-reset clear loop (deterministic macro contents for randreset)
    // ----------------------------------------------------------------
    reg [9:0] clr_cnt;
    reg       clr_active;

    // ----------------------------------------------------------------
    // Segment-queue head (FWFT, combinational read of packed vectors)
    // ----------------------------------------------------------------
    wire [35:0] hd_addr = sq_addr_v[36*sq_rd[5:0] +: 36];
    wire [31:0] hd_len  = sq_len_v [32*sq_rd[5:0] +: 32];
    wire [3:0]  hd_tag  = sq_tag_v [4*sq_rd[5:0] +: 4];

    wire [32:0] hd_span    = {1'b0, hd_len} + {29'b0, hd_addr[3:0]};
    wire [28:0] hd_nbeats  = hd_span[32:4] + {28'b0, (|hd_span[3:0])};
    wire [4:0]  hd_lastcnt = (hd_span[3:0] == 4'd0) ? 5'd16
                                                    : {1'b0, hd_span[3:0]};

    // ----------------------------------------------------------------
    // Read-issue engine state (current segment being requested)
    // ----------------------------------------------------------------
    reg        iss_active;
    reg [35:0] iss_addr;     // next aligned address to request
    reg [3:0]  iss_tag;
    reg [3:0]  iss_shift;    // seg_addr[3:0]
    reg        iss_first;    // next beat is the segment's first
    reg [28:0] iss_beats;    // beats remaining
    reg [4:0]  iss_lastcnt;  // valid bytes in the last beat
    reg [4:0]  iss_flen;     // seg_len[4:0] (used when first==last)

    wire        iss_last    = (iss_beats == 29'd1);
    wire [3:0]  iss_shift_o = iss_first ? iss_shift : 4'd0;
    wire [4:0]  iss_count   = (iss_first && iss_last) ? iss_flen
                            : iss_last                ? iss_lastcnt
                            : iss_first               ? (5'd16 - {1'b0, iss_shift})
                            :                           5'd16;
    assign iss_meta = {iss_tag, iss_first, iss_last, iss_shift_o, iss_count};

    // ----------------------------------------------------------------
    // Request-port arbitration: posted writes have priority over reads
    // ----------------------------------------------------------------
    wire rd_pend = iss_active && fifo_room && !clr_active;

    assign mem_req_valid = !clr_active && (wr_valid || rd_pend);
    assign mem_req_write = wr_valid;
    assign mem_req_addr  = wr_valid ? wr_addr : iss_addr;
    assign mem_req_wdata = wr_data;
    assign mem_req_wstrb = wr_wstrb;
    assign wr_ready      = mem_req_ready && !clr_active;

    wire req_fire   = mem_req_valid && mem_req_ready;
    wire issue_fire = req_fire && !wr_valid;   // read request accepted

    // A committed response always has a pre-allocated slot, so the
    // response channel never needs backpressure.
    assign mem_rsp_ready = 1'b1;

    assign seg_ready = !clr_active && !sq_full;

    // ----------------------------------------------------------------
    // Byte-stream output (FWFT via a 2-word skid; the 256b macro read
    // of word rd_ptr[7:1] returns one cycle after the load issue).
    // rd_ptr counts BEATS and advances by 1 or 2 at load issue, so RAM
    // occupancy is wr_ptr - rd_ptr and the skid costs no RAM slots
    // (fifo_room = occ < 256). A load fires as soon as the beat at
    // rd_ptr has arrived — it never waits for its word partner, so
    // single-beat consumers see exactly the old delivery timing; the
    // load carries 2 beats when rd_ptr is even and the whole word is
    // present, else 1. Each slot tracks which halves hold valid beats
    // (mask), so half-filled words (odd segment parities, end of
    // stream) are never stranded. Two slots sustain back-to-back
    // 2-beat pops at full rate: a load is issued only when a slot is
    // guaranteed empty at arrival (nv0/nv1 below). Consumers pop 1
    // (bs_ready) or 2 (bs2_ready, only with bs2_valid; pop2 dominates
    // if both are somehow asserted).
    // ----------------------------------------------------------------
    reg [1:0]   w0_v, w1_v;             // per-half valid masks
    reg [255:0] w0_d, w1_d;
    reg [14:0]  w0_ma, w0_mb, w1_ma, w1_mb;
    reg         ld_dv;
    reg [1:0]   ld_v;                   // halves valid in the in-flight word
`ifdef MSH_DEBUG
    reg [31:0]  dbg2_cyc;
    reg [15:0]  dbg_hq_iss;             // skip-marked beats issued
`endif

    // presentation collapses through empty (fully-skipped) words, so
    // TG_HQ shadow beats never stall the stream or leak into it
    wire [1:0]   pv_v  = (w0_v != 2'b00) ? w0_v : w1_v;
    wire [255:0] pv_d  = (w0_v != 2'b00) ? w0_d : w1_d;
    wire [14:0]  pv_ma = (w0_v != 2'b00) ? w0_ma : w1_ma;
    wire [14:0]  pv_mb = (w0_v != 2'b00) ? w0_mb : w1_mb;
    assign bs_valid = (pv_v != 2'b00);
    assign bs_data  = pv_v[0] ? pv_d[127:0] : pv_d[255:128];
    assign {bs_tag, bs_first, bs_last, bs_shift, bs_count} =
        pv_v[0] ? pv_ma : pv_mb;
    assign bs2_valid = (pv_v == 2'b11) ? 1'b1
                     : (w0_v != 2'b00) && (w1_v != 2'b00);
    assign bs2_data  = (pv_v == 2'b11) ? pv_d[255:128]
                     : w1_v[0] ? w1_d[127:0] : w1_d[255:128];
    assign {bs2_tag, bs2_first, bs2_last, bs2_shift, bs2_count} =
        (pv_v == 2'b11) ? pv_mb
                     : (w1_v[0] ? w1_ma : w1_mb);

    wire bs_pop  = bs_valid && bs_ready;
    wire bs_pop2 = bs2_valid && bs2_ready;
    wire pop1    = bs_pop && !bs_pop2;
    wire pop2    = bs_pop2;

    // next skid state after this cycle's pops and the in-flight arrival
    reg [1:0]   nv0, nv1;
    reg [255:0] nd0, nd1;
    reg [14:0]  nm0a, nm0b, nm1a, nm1b;
    always @* begin
        nv0 = w0_v; nd0 = w0_d; nm0a = w0_ma; nm0b = w0_mb;
        nv1 = w1_v; nd1 = w1_d; nm1a = w1_ma; nm1b = w1_mb;
        // collapse an empty w0 (empty words are fully-skipped shadow
        // beats or pre-arrival gaps)
        if ((nv0 == 2'b00) && (nv1 != 2'b00)) begin
            nv0 = nv1; nd0 = nd1; nm0a = nm1a; nm0b = nm1b;
            nv1 = 2'b00;
        end
        if (pop2) begin
            if (nv0 == 2'b11) begin
                // both halves of the presented word consumed
                nv0 = nv1; nd0 = nd1; nm0a = nm1a; nm0b = nm1b;
                nv1 = 2'b00;
            end else if (nv1 == 2'b11) begin
                // w0's beat + w1's low consumed; w1's high shifts
                nv0 = 2'b10; nd0 = nd1; nm0a = nm1a; nm0b = nm1b;
                nv1 = 2'b00;
            end else begin
                // two single-beat slots consumed
                nv0 = 2'b00;
                nv1 = 2'b00;
            end
        end else if (pop1) begin
            if (nv0 == 2'b11) begin
                nv0 = 2'b10;          // low consumed, high remains
            end else begin
                nv0 = nv1; nd0 = nd1; nm0a = nm1a; nm0b = nm1b;
                nv1 = 2'b00;
            end
        end
        // arrival lands in the first empty slot (guaranteed by ld_fire);
        // shadow beats (meta[15]) arrive with their valid bits cleared
        if (ld_dv) begin
            if (nv0 == 2'b00) begin
                nv0  = ld_v & ~{fmeta_rd[31], fmeta_rd[15]};
                nd0  = fdata_rd;
                nm0a = fmeta_rd[14:0];
                nm0b = fmeta_rd[30:16];
            end else begin
                nv1  = ld_v & ~{fmeta_rd[31], fmeta_rd[15]};
                nd1  = fdata_rd;
                nm1a = fmeta_rd[14:0];
                nm1b = fmeta_rd[30:16];
            end
        end
    end

    // fill distance (beats arrived but not yet loaded); exact because
    // the in-order fill keeps fill_ptr - rd_ptr inside [0, 256]
    wire [9:0] fill_d  = fill_ptr - rd_ptr;
    wire       ld2     = (rd_ptr[0] == 1'b0) && (fill_d >= 10'd2);
    // a load is issued only when a word slot is guaranteed free at
    // arrival (this cycle's pops and the in-flight arrival are already
    // accounted in nv0/nv1)
    wire       ld_fire = (fill_d != 10'd0)
                       && ((nv0 == 2'b00) || (nv1 == 2'b00));

    // ----------------------------------------------------------------
    // Sequential logic
    // ----------------------------------------------------------------
    always @(posedge clk) begin
        if (!rst_n) begin
            wr_ptr      <= 10'd0;
            fill_ptr    <= 10'd0;
            rd_ptr      <= 10'd0;
            sq_wr       <= 7'd0;
            sq_rd       <= 7'd0;
            iss_active  <= 1'b0;
            iss_addr    <= 36'd0;
            iss_tag     <= 4'd0;
            iss_shift   <= 4'd0;
            iss_first   <= 1'b0;
            iss_beats   <= 29'd0;
            iss_lastcnt <= 5'd0;
            iss_flen    <= 5'd0;
            clr_cnt     <= 10'd0;
            clr_active  <= 1'b1;
            w0_v        <= 2'b00;
            w1_v        <= 2'b00;
            w0_d        <= 256'd0;
            w1_d        <= 256'd0;
            w0_ma       <= 15'd0;
            w0_mb       <= 15'd0;
            w1_ma       <= 15'd0;
            w1_mb       <= 15'd0;
            ld_dv       <= 1'b0;
            ld_v        <= 2'b00;
`ifdef MSH_DEBUG
            dbg2_cyc    <= 32'd0;
            dbg_hq_iss  <= 16'd0;
`endif
            hq_nbeats   <= 11'd0;
            hq_fill     <= 11'd0;
            hq_stage_v  <= 1'b0;
            hq_stage    <= 128'd0;
            hq_seg_len  <= 5'd0;
            hq_lastcnt  <= 5'd0;
            hq_shift    <= 4'd0;
            hq_rword    <= 9'd0;
            hq_popb     <= 11'd0;
            hq_w0_v     <= 2'b00;
            hq_w1_v     <= 2'b00;
            hq_ld_dv    <= 1'b0;
        end else if (clr_active) begin
            // macro clear write is combinational (fifo_*)
            if (clr_cnt == 10'd0) begin
                sq_addr_v <= 2304'd0;
                sq_len_v  <= 2048'd0;
                sq_tag_v  <= 256'd0;
            end
            if (clr_cnt == 10'd127) clr_active <= 1'b0;
            else                    clr_cnt    <= clr_cnt + 10'd1;
        end else begin
            // segment queue push
            if (seg_valid && seg_ready) begin
                sq_addr_v[36*sq_wr[5:0] +: 36] <= seg_addr;
                sq_len_v [32*sq_wr[5:0] +: 32] <= seg_len;
                sq_tag_v [4*sq_wr[5:0] +: 4]   <= seg_tag;
                sq_wr <= sq_wr + 7'd1;
            end
            // in-order response fill (slot was allocated at request time;
            // the macro write is combinational)
            if (mem_rsp_valid) begin
                fill_ptr <= fill_ptr + 10'd1;
            end
            // drain-steered shadow fill: 1-half staging pairs HQ beats
            // into full words; a trailing odd half flushes at span end
            if (hq_flush) begin
                hq_stage_v <= 1'b0;
                hq_fill    <= hq_fill + 11'd1;
            end else if (ld_dv && (hq_new != 2'b00)
                         && (hq_fill < hq_nbeats)) begin
                if (hq_new == 2'b11) begin
                    if (hq_stage_v) begin
                        hq_stage   <= fdata_rd[255:128];
                        hq_fill    <= hq_fill + 11'd2;
                    end else begin
                        hq_fill    <= hq_fill + 11'd2;
                    end
                end else if (hq_stage_v) begin
                    hq_stage_v <= 1'b0;
                    hq_fill    <= hq_fill + 11'd2;
                end else begin
                    hq_stage_v <= 1'b1;
                    hq_stage   <= hq_new[0] ? fdata_rd[127:0]
                                            : fdata_rd[255:128];
                end
            end
            // skid word load/drain (1-cycle macro read, 2-word buffer)
            ld_dv <= ld_fire;
            if (ld_fire) begin
                ld_v   <= ld2 ? 2'b11 : (rd_ptr[0] ? 2'b10 : 2'b01);
                rd_ptr <= rd_ptr + (ld2 ? 10'd2 : 10'd1);
            end
            w0_v  <= nv0;  w0_d  <= nd0;
            w0_ma <= nm0a; w0_mb <= nm0b;
            w1_v  <= nv1;  w1_d  <= nd1;
            w1_ma <= nm1a; w1_mb <= nm1b;
`ifdef MSH_DEBUG
            if (bs_pop || bs_pop2)
                $display("[fetch] pop tag=%0d first=%0d last=%0d cnt=%0d rd=%0d w0v=%0d w1v=%0d",
                         bs_tag, bs_first, bs_last, bs_count, rd_ptr,
                         w0_v, w1_v);
            if ((dbg2_cyc > 32'd5400) && ((w0_v != nv0) || (w1_v != nv1)))
                $display("[fetch] w0v %0d->%0d w1v %0d->%0d rd=%0d fill_d=%0d bs_v=%0d rdy=%0d",
                         w0_v, nv0, w1_v, nv1, rd_ptr, fill_d, bs_valid,
                         bs_ready);
            dbg2_cyc <= dbg2_cyc + 32'd1;
`endif
            // head-q reader skid + pop counter (rewound per head job)
`ifdef MSH_DEBUG
            if (hq_pop || hq_pop2)
                $display("[fetch] hqpop pb=%0d rem=%0d v=%0d v2=%0d fd=%0d nb=%0d fill=%0d",
                         hq_popb, hq_rem, hq_v, hq_v2, hq_fill_done,
                         hq_nbeats, hq_fill);
            if (hq_first_issue || ((hq_fill != hq_fill) === 1'bx))
                $display("[fetch] hqarm nb=%0d", hq_nbeats);
            if ((hq_nbeats != 11'd0) && (hq_fill < hq_nbeats) && hq_we)
                if (hq_fill[3:0] == 4'd0)
                    $display("[fetch] hqfill fill=%0d nb=%0d stg=%0d sk=%0d",
                             hq_fill, hq_nbeats, hq_stage_v, hq_skips);
`endif
            if (hq_rewind) begin
                hq_popb  <= 11'd0;
                hq_rword <= 9'd0;
                hq_w0_v  <= 2'b00;
                hq_w1_v  <= 2'b00;
                hq_ld_dv <= 1'b0;
            end else begin
                hq_ld_dv <= hq_ld_fire;
                if (hq_ld_fire) hq_rword <= hq_rword + 9'd1;
                if (hq_pop2)      hq_popb <= hq_popb + 11'd2;
                else if (hq_pop)  hq_popb <= hq_popb + 11'd1;
                hq_w0_v <= hq_nv0_v; hq_w0 <= hq_nd0;
                hq_w1_v <= hq_nv1_v; hq_w1 <= hq_nd1;
            end
            // segment load / skip, then per-beat request issue
            if (!iss_active) begin
                if (sq_nonempty) begin
                    if (hd_len == 32'd0) begin
                        sq_rd <= sq_rd + 7'd1;   // zero-length: skip
                    end else begin
                        iss_active  <= 1'b1;
                        iss_addr    <= {hd_addr[35:4], 4'b0000};
                        iss_tag     <= hd_tag;
                        iss_shift   <= hd_addr[3:0];
                        iss_first   <= 1'b1;
                        iss_beats   <= hd_nbeats;
                        iss_lastcnt <= hd_lastcnt;
                        iss_flen    <= hd_len[4:0];
                        if (hd_tag == 4'd10) begin
                            // HQ shadow segment: reader meta only; the
                            // divert span arms at the first HQ request
                            hq_seg_len <= hd_len[4:0];
                            hq_lastcnt <= hd_lastcnt;
                            hq_shift   <= hd_addr[3:0];
                        end
                        sq_rd       <= sq_rd + 7'd1;
                    end
                end
            end else if (issue_fire) begin
                // meta write is combinational (fifo_*)
                wr_ptr    <= wr_ptr + 10'd1;
                iss_addr  <= iss_addr + 36'd16;
                iss_first <= 1'b0;
                iss_beats <= iss_beats - 29'd1;
                if (iss_last) iss_active <= 1'b0;
                if (hq_first_issue) begin
                    hq_nbeats <= iss_beats[10:0];
                end
`ifdef MSH_DEBUG
                if (iss_hq) dbg_hq_iss <= dbg_hq_iss + 16'd1;
                $display("[fetch] rd req addr=%h tag=%0d first=%0d last=%0d",
                         iss_addr, iss_tag, iss_first, iss_last);
`endif
            end
        end
    end

    // fmeta_rd[31] and fmeta_rd[15] are padding
    wire _unused = &{1'b0, fmeta_rd[31], fmeta_rd[15]};

endmodule

`default_nettype wire
