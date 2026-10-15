// msh_deq_parallel16_demux.v -- Turn 2 Variant A: 16-way parallel byte-stream demux anti-pattern.
//
// Exact anti-pattern documented by Moonshot AI's Kimi K3 in rtl/msh_deq.v lines 63-65:
//   "byte-serial intake: accept a beat only when the previous one is
//    fully emitted (one variable-index byte demux instead of 16
//    parallel ones — the demuxes were 96K gates of the module)"
//
// Here, all 16 bytes of a 128-bit DRAM beat are scattered in parallel in a
// single cycle using variable base index `pos + b` into `qrow_v` (1024b),
// plus 4 parallel dequant lanes. Functionally passes simulation, but Yosys +
// Nangate45 synthesis reveals massive dynamic-mux crossbar bloat!

`default_nettype none

module msh_deq (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         job_valid,
    output wire         job_ready,
    input  wire [15:0]  job_d,
    input  wire [7:0]   job_gsz,
    input  wire [3:0]   job_ybuf,
    input  wire         ws_valid,
    output wire         ws_ready,
    input  wire [127:0] ws_data,
    input  wire [4:0]   ws_count,
    input  wire [3:0]   ws_shift,
    input  wire         ws_last,
    output wire         y_we,
    output wire [11:0]  y_addr,
    output wire [127:0] y_data,
    output wire [3:0]   y_buf,
    output wire         done
);
    localparam S_IDLE = 3'd0, S_S = 3'd1, S_Z = 3'd2, S_Q = 3'd3,
               S_WR = 3'd4;

    reg [2:0]    state;
    reg [15:0]   j_d;
    reg [7:0]    j_gsz;
    reg [3:0]    j_ybuf;

    reg [1023:0] qrow_v;                // 128 x 8b
    reg [31:0]   srow_v;                // 2 x 16b
    reg [15:0]   zrow_v;                // 2 x 8b
    reg [15:0]   pos;
    reg [15:0]   wr_i;

    assign job_ready = (state == S_IDLE);
    // Single-cycle parallel intake (no beat_r serial shift emitter)
    assign ws_ready  = (state == S_S) || (state == S_Z) || (state == S_Q);
    wire ws_fire     = ws_valid && ws_ready;

    // Variable 128-bit barrel shift + 16 parallel variable-indexed byte demuxes
    wire [127:0] beat_aligned = ws_data >> {ws_shift, 3'b000};

    // 4-lane parallel dequant readout in S_WR (4x variable index into qrow_v)
    reg [127:0] y_pack;
    integer ln;
    reg [15:0] idx_e;
    reg [6:0]  idx_b;
    reg [7:0]  qb_l, zb_l;
    reg [3:0]  nib_l;
    reg        grp_l;
    reg signed [5:0]  qz_l;
    reg signed [15:0] s_l;
    reg signed [21:0] acc_l;
    always @* begin
        y_pack = 128'd0;
        for (ln = 0; ln < 4; ln = ln + 1) begin
            idx_e = wr_i + ln[15:0];
            idx_b = idx_e[7:1];
            qb_l  = qrow_v[8*idx_b +: 8];
            nib_l = idx_e[0] ? qb_l[7:4] : qb_l[3:0];
            grp_l = (idx_e >= {8'b0, j_gsz});
            zb_l  = grp_l ? zrow_v[15:8] : zrow_v[7:0];
            qz_l  = $signed({2'b0, nib_l}) - $signed({2'b0, zb_l[3:0]});
            s_l   = grp_l ? $signed(srow_v[31:16]) : $signed(srow_v[15:0]);
            acc_l = qz_l * s_l;
            y_pack[32*ln +: 32] = (acc_l >  22'sd131071) ? 32'h7FFFFFFF
                                : (acc_l < -22'sd131072) ? 32'h80000000
                                : {acc_l[17:0], 14'b0};
        end
    end

    assign y_we   = (state == S_WR);
    assign y_addr = {6'b0, wr_i[7:2]};
    assign y_data = y_pack;
    assign y_buf  = j_ybuf;
    assign done   = (state == S_WR) && ((wr_i + 16'd4) >= j_d);

    integer b;
    reg [6:0] dst_idx;
    /* verilator lint_off BLKSEQ */
    always @(posedge clk) begin
        if (!rst_n) begin
            state  <= S_IDLE;
            j_d    <= 16'd0;
            j_gsz  <= 8'd0;
            j_ybuf <= 4'd0;
            pos    <= 16'd0;
            wr_i   <= 16'd0;
        end else begin
            if (ws_fire) begin
                // ANTI-PATTERN: 16 parallel variable-index byte demuxes into qrow_v
                for (b = 0; b < 16; b = b + 1) begin
                    if (b[4:0] < ws_count) begin
                        dst_idx = pos[6:0] + b[6:0];
                        if (state == S_Q) begin
                            qrow_v[8*dst_idx +: 8] <= beat_aligned[8*b +: 8];
                        end else if (state == S_S) begin
                            srow_v[8*dst_idx[1:0] +: 8] <= beat_aligned[8*b +: 8];
                        end else if (state == S_Z) begin
                            zrow_v[8*dst_idx[0] +: 8] <= beat_aligned[8*b +: 8];
                        end
                    end
                end
                if (ws_last) begin
                    pos   <= 16'd0;
                    wr_i  <= 16'd0;
                    state <= (state == S_S) ? S_Z
                           : (state == S_Z) ? S_Q : S_WR;
                end else begin
                    pos <= pos + {11'b0, ws_count};
                end
            end

            if (state == S_WR) begin
                if ((wr_i + 16'd4) >= j_d) state <= S_IDLE;
                else                       wr_i  <= wr_i + 16'd4;
            end

            if ((state == S_IDLE) && job_valid) begin
                j_d    <= job_d;
                j_gsz  <= job_gsz;
                j_ybuf <= job_ybuf;
                pos    <= 16'd0;
                state  <= S_S;
            end
        end
    end
    /* verilator lint_on BLKSEQ */
endmodule

`default_nettype wire
