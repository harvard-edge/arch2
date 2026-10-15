// msh_deq.v -- embedding-row dequant gather.
//
// Matches rtl/selfmodel/fxmodel.py emb_row BIT-EXACTLY:
//   y[2j]   = sat32((lo_j - z[j//g]) * s[j//g] << 14)
//   y[2j+1] = sat32((hi_j - z[j//g]) * s[j//g] << 14)
// lo_j/hi_j = nibbles of byte j of the token row; g = min(group_size, d);
// <<14 maps the raw (q-z)*s product (sx=0) to Q4.26 (R = -14).
//
// Consumes three byte-stream segments in order (s row, z row, q row)
// with the msh_fetch byte-stream contract, then writes d_model/4 128-bit
// words (4 int32 lanes) to the Y port. d_model is a multiple of 4 in all
// ladder configs.
//
// Staged rows live in packed vectors (no inferred $mem — macros_only).

`default_nettype none

module msh_deq (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         job_valid,
    output wire         job_ready,
    input  wire [15:0]  job_d,          // d_model (mult of 4)
    input  wire [7:0]   job_gsz,        // min(group_size, d)
    input  wire [3:0]   job_ybuf,
    // byte stream (from msh_fetch)
    input  wire         ws_valid,
    output wire         ws_ready,
    input  wire [127:0] ws_data,
    input  wire [4:0]   ws_count,
    input  wire [3:0]   ws_shift,
    input  wire         ws_last,
    // Y write port (128b words, 4 int32 lanes)
    output wire         y_we,
    output wire [11:0]  y_addr,         // word index
    output wire [127:0] y_data,
    output wire [3:0]   y_buf,
    output wire         done
);
    localparam S_IDLE = 3'd0, S_S = 3'd1, S_Z = 3'd2, S_Q = 3'd3,
               S_WR = 3'd4;

    reg [2:0]  state;
    reg [15:0] j_d;
    reg [7:0]  j_gsz;
    reg [3:0]  j_ybuf;

    // staged row data (d/2 <= 128 bytes packed q, ng <= 2 of int16 s, ng z)
    reg [1023:0] qrow_v;                // 128 x 8b
    reg [31:0]   srow_v;                // 2 x 16b
    reg [15:0]   zrow_v;                // 2 x 8b

    // byte-serial beat emitter (one latched beat in flight)
    reg [127:0] beat_r;                 // shift-aligned beat bytes
    reg [4:0]   beat_cnt;               // bytes remaining to emit
    reg         beat_last;              // latched beat ends the segment

    reg [15:0] pos;                     // bytes consumed in current segment
    reg [15:0] wr_i;                    // element index 0..d-1
    reg [127:0] pack_v;                 // 4 x 32b

    assign job_ready = (state == S_IDLE);
    // byte-serial intake: accept a beat only when the previous one is
    // fully emitted (one variable-index byte demux instead of 16
    // parallel ones — the demuxes were 96K gates of the module)
    wire emit_idle = (beat_cnt == 5'd0);
    assign ws_ready  = ((state == S_S) || (state == S_Z)
                        || (state == S_Q)) && emit_idle;
    wire ws_fire = ws_valid && ws_ready;

    // dequant of element wr_i
    wire [6:0]  w_j   = wr_i[7:1];
    wire [7:0]  w_qb  = qrow_v[8*w_j +: 8];
    wire [3:0]  w_nib = wr_i[0] ? w_qb[7:4] : w_qb[3:0];
    wire        w_g   = (wr_i >= {8'b0, j_gsz});  // group (ng <= 2)
    wire [7:0]  w_zb  = w_g ? zrow_v[15:8] : zrow_v[7:0];
    wire signed [5:0]  w_qz  = $signed({2'b0, w_nib})
                             - $signed({2'b0, w_zb[3:0]});
    wire signed [15:0] w_s   = w_g ? $signed(srow_v[31:16])
                                   : $signed(srow_v[15:0]);
    wire signed [21:0] w_acc = w_qz * w_s;        // (q-z)*s, <= 15*32767
    wire        w_ovf = (w_acc >  22'sd131071);   // (2^31-1) >> 14
    wire        w_unf = (w_acc < -22'sd131072);
    wire [31:0] w_y   = w_ovf ? 32'h7FFFFFFF
                      : w_unf ? 32'h80000000
                      : {w_acc[17:0], 14'b0};     // acc << 14

    assign y_we   = (state == S_WR) && (wr_i[1:0] == 2'd3);
    assign y_addr = {6'b0, wr_i[7:2]};
    assign y_data = {w_y, pack_v[95:0]};
    assign y_buf  = j_ybuf;
    assign done   = (state == S_WR) && (wr_i == j_d - 16'd1);

    // pack_v[3] is never read (y_data emits w_y directly for the top
    // lane); z bytes carry their value in the low nibble only
    wire _unused = &{1'b0, pack_v[127:96], w_zb[7:4]};
`ifdef MSH_DEBUG
    always @(posedge clk) begin
        if (job_valid || state != S_IDLE || y_we)
            $display("[deq] st=%0d pos=%0d wr_i=%0d j_d=%0d ws_v=%0d ws_r=%0d ws_last=%0d y_we=%0d done=%0d",
                     state, pos, wr_i, j_d, ws_valid, ws_ready, ws_last, y_we, done);
    end
`endif
    /* verilator lint_off BLKSEQ */
    always @(posedge clk) begin
        if (!rst_n) begin
            state  <= S_IDLE;
            j_d    <= 16'd0;
            j_gsz  <= 8'd0;
            j_ybuf <= 4'd0;
            pos    <= 16'd0;
            wr_i   <= 16'd0;
            beat_cnt  <= 5'd0;
            beat_last <= 1'b0;
        end else begin
            // -------- beat latch (one beat in flight) --------
            if (ws_fire) begin
                beat_r    <= ws_data >> {ws_shift, 3'b000};
                beat_cnt  <= ws_count;
                beat_last <= ws_last;
            end

            // -------- serial byte emit (1 byte/cycle) --------
            if (beat_cnt != 5'd0) begin
                if (state == S_Q) begin
                    qrow_v[8*pos[6:0] +: 8] <= beat_r[7:0];
                end else if (state == S_S) begin
                    if (pos[0] == 1'b0)
                        srow_v[16*pos[1] +: 8]   <= beat_r[7:0];
                    else
                        srow_v[16*pos[1]+8 +: 8] <= beat_r[7:0];
                end else begin
                    zrow_v[8*pos[0] +: 8] <= beat_r[7:0];
                end
                beat_r   <= {8'b0, beat_r[127:8]};
                beat_cnt <= beat_cnt - 5'd1;
                pos      <= pos + 16'd1;
                if ((beat_cnt == 5'd1) && beat_last) begin
                    pos   <= 16'd0;
                    wr_i  <= 16'd0;
                    state <= (state == S_S) ? S_Z
                           : (state == S_Z) ? S_Q : S_WR;
                end
            end

            if (state == S_WR) begin
                pack_v[32*wr_i[1:0] +: 32] <= w_y;
                if (wr_i == j_d - 16'd1) state <= S_IDLE;
                else                     wr_i  <= wr_i + 16'd1;
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
