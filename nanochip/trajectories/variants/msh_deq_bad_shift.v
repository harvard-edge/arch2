// msh_deq_bad_shift.v -- Turn 1 Variant B: Representation drift between RTL and fxmodel.py.
//
// Shifts the dequantized product (q - z) * s by << 13 instead of << 14
// (mis-aligning Q3.12 scale -> Q4.26 activation format by 1 bit) and omits
// signed 32-bit saturation clamping.
// Notice: Because cosine similarity is scale-invariant on a single layer,
// unit-level smoke tests appear plausible, but the bit-exact selfmodel check
// (`rtl/selfmodel/fxmodel.py`) catches the mismatch immediately on row 0!
// Stage 5 (Interpret) routes the return arrow to 3. Implement.

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

    reg [2:0]  state;
    reg [15:0] j_d;
    reg [7:0]  j_gsz;
    reg [3:0]  j_ybuf;

    reg [1023:0] qrow_v;
    reg [31:0]   srow_v;
    reg [15:0]   zrow_v;

    reg [127:0] beat_r;
    reg [4:0]   beat_cnt;
    reg         beat_last;

    reg [15:0] pos;
    reg [15:0] wr_i;
    reg [127:0] pack_v;

    assign job_ready = (state == S_IDLE);
    wire emit_idle   = (beat_cnt == 5'd0);
    assign ws_ready  = ((state == S_S) || (state == S_Z)
                        || (state == S_Q)) && emit_idle;
    wire ws_fire = ws_valid && ws_ready;

    wire [6:0]  w_j   = wr_i[7:1];
    wire [7:0]  w_qb  = qrow_v[8*w_j +: 8];
    wire [3:0]  w_nib = wr_i[0] ? w_qb[7:4] : w_qb[3:0];
    wire        w_g   = (wr_i >= {8'b0, j_gsz});
    wire [7:0]  w_zb  = w_g ? zrow_v[15:8] : zrow_v[7:0];
    wire signed [5:0]  w_qz  = $signed({2'b0, w_nib})
                             - $signed({2'b0, w_zb[3:0]});
    wire signed [15:0] w_s   = w_g ? $signed(srow_v[31:16])
                                   : $signed(srow_v[15:0]);
    wire signed [21:0] w_acc = w_qz * w_s;

    // BUG (Turn 1 representation fault): shifts by << 13 instead of << 14
    // and omits overflow/underflow saturation vs fxmodel.py::emb_row
    wire [31:0] w_y   = {w_acc[18:0], 13'b0};

    assign y_we   = (state == S_WR) && (wr_i[1:0] == 2'd3);
    assign y_addr = {6'b0, wr_i[7:2]};
    assign y_data = {w_y, pack_v[95:0]};
    assign y_buf  = j_ybuf;
    assign done   = (state == S_WR) && (wr_i == j_d - 16'd1);

    wire _unused = &{1'b0, pack_v[127:96], w_zb[7:4], w_acc[21:19]};

    /* verilator lint_off BLKSEQ */
    always @(posedge clk) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            j_d       <= 16'd0;
            j_gsz     <= 8'd0;
            j_ybuf    <= 4'd0;
            pos       <= 16'd0;
            wr_i      <= 16'd0;
            beat_cnt  <= 5'd0;
            beat_last <= 1'b0;
        end else begin
            if (ws_fire) begin
                beat_r    <= ws_data >> {ws_shift, 3'b000};
                beat_cnt  <= ws_count;
                beat_last <= ws_last;
            end
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
