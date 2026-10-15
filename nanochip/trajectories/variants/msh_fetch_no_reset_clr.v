// msh_fetch_no_reset_clr.v -- Turn 2 Variant B: Naive fetch FIFO without
// credit-tracked deep window (`FIFO_DEPTH = 4` serialized stalls) and missing
// reset clear / unreset pointer state (`randreset` + `2x latency` failure).
//
// Demonstrates why Turn 2 fails both:
//   1. `do_randreset` (`+verilator+rand+reset+2`): uninitialized `hq_nbeats`,
//      `hq_fill`, `w0_v`, `w1_v` and skipped `clr_active` cause X/random state
//      corruption under non-zero initial flop/SRAM state.
//   2. `do_latency_sweep` (`lat_base = 24 -> 48`): shallow in-flight window
//      serializes DRAM reads across the 48-cycle round-trip latency, degrading
//      latency elasticity from 1.0091 toward ~1.68x.
// Stage 5 (Interpret) routes the return arrow to 2. Explore.

`default_nettype none

module msh_fetch_naive_stall (
    input  wire         clk,
    input  wire         rst_n,
    output wire         mem_req_valid,
    input  wire         mem_req_ready,
    output wire         mem_req_write,
    output wire [35:0]  mem_req_addr,
    output wire [127:0] mem_req_wdata,
    output wire [15:0]  mem_req_wstrb,
    input  wire         mem_rsp_valid,
    output wire         mem_rsp_ready,
    input  wire [127:0] mem_rsp_rdata,
    input  wire         seg_valid,
    output wire         seg_ready,
    input  wire [35:0]  seg_addr,
    input  wire [31:0]  seg_len,
    input  wire [3:0]   seg_tag,
    output wire         bs_valid,
    input  wire         bs_ready,
    output wire [127:0] bs_data,
    output wire         bs_first,
    output wire         bs_last,
    output wire [3:0]   bs_tag,
    output wire [3:0]   bs_shift,
    output wire [4:0]   bs_count
);
    // Shallow 2-beat window: allows at most 2 requests in flight across a
    // 24..48 cycle DRAM pipe, starving msh_gemv and failing latency elasticity.
    localparam [3:0] SHALLOW_DEPTH = 4'd2;

    // BUG 1: Missing reset initialization on control pointers & valid masks
    // (passes zero-initialized simulator defaults, fails +verilator+rand+reset+2)
    reg [3:0]   wr_ptr;
    reg [3:0]   rd_ptr;
    reg         iss_active;
    reg [35:0]  iss_addr;
    reg [28:0]  iss_beats;
    reg [3:0]   iss_tag;
    reg [3:0]   iss_shift;
    reg         iss_first;
    reg [4:0]   iss_lastcnt;
    reg [127:0] beat_buf;
    reg         beat_valid;

    wire [3:0] occ       = wr_ptr - rd_ptr;
    wire       fifo_room = (occ < SHALLOW_DEPTH) && !beat_valid;

    assign seg_ready     = !iss_active;
    assign mem_req_valid = iss_active && fifo_room;
    assign mem_req_write = 1'b0;
    assign mem_req_addr  = iss_addr;
    assign mem_req_wdata = 128'd0;
    assign mem_req_wstrb = 16'd0;
    assign mem_rsp_ready = !beat_valid || bs_ready;

    assign bs_valid = beat_valid;
    assign bs_data  = beat_buf;
    assign bs_first = iss_first;
    assign bs_last  = (iss_beats == 29'd0);
    assign bs_tag   = iss_tag;
    assign bs_shift = iss_first ? iss_shift : 4'd0;
    assign bs_count = (iss_beats == 29'd0) ? iss_lastcnt : 5'd16;

    always @(posedge clk) begin
        if (!rst_n) begin
            iss_active <= 1'b0;
            // NOTE: wr_ptr, rd_ptr, beat_valid intentionally left unreset here
            // to reproduce the Turn 2 randreset divergence failure!
        end else begin
            if (!iss_active && seg_valid) begin
                iss_active  <= (seg_len != 32'd0);
                iss_addr    <= {seg_addr[35:4], 4'b0000};
                iss_tag     <= seg_tag;
                iss_shift   <= seg_addr[3:0];
                iss_first   <= 1'b1;
                iss_beats   <= ((seg_len + {28'b0, seg_addr[3:0]} + 32'd15) >> 4);
                iss_lastcnt <= 5'd16;
            end else if (mem_req_valid && mem_req_ready) begin
                wr_ptr    <= wr_ptr + 4'd1;
                iss_addr  <= iss_addr + 36'd16;
                iss_beats <= iss_beats - 29'd1;
                if (iss_beats == 29'd1) iss_active <= 1'b0;
            end

            if (mem_rsp_valid && mem_rsp_ready) begin
                beat_buf   <= mem_rsp_rdata;
                beat_valid <= 1'b1;
            end else if (bs_valid && bs_ready) begin
                beat_valid <= 1'b0;
                iss_first  <= 1'b0;
                rd_ptr     <= rd_ptr + 4'd1;
            end
        end
    end
endmodule

`default_nettype wire
