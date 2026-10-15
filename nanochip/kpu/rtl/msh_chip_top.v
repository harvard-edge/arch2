// msh_chip_top -- Moonshot hybrid inference chip, top level.
//
// Wires the engines (fetch/gemv/deq/vec/kda/mla/seq) to the shared
// memories (XBUF/WBUF/DESC/TOK/HS/HZ/LG). The sequencer drives everything;
// v1 serializes engine jobs so the shared-port muxes are one-hot by
// construction. Port list is fixed by the harness (docs/interface.md).

`default_nettype none

module msh_chip_top (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [31:0]  cmd_data,
    input  wire         cmd_valid,
    output wire         cmd_ready,
    output wire [31:0]  rsp_data,
    output wire         rsp_valid,
    input  wire         rsp_ready,
    output wire         mem_req_valid,
    input  wire         mem_req_ready,
    output wire         mem_req_write,
    output wire [35:0]  mem_req_addr,
    output wire [127:0] mem_req_wdata,
    output wire [15:0]  mem_req_wstrb,
    input  wire         mem_rsp_valid,
    output wire         mem_rsp_ready,
    input  wire [127:0] mem_rsp_rdata
);

    // ================= fetch =================
    wire        seg_valid, seg_ready, bs_valid, bs_ready;
    wire        bs2_valid, bs2_ready, bs2_first, bs2_last;
    wire [35:0] seg_addr;
    wire [31:0] seg_len;
    wire [3:0]  seg_tag, bs_tag, bs_shift, bs2_tag, bs2_shift;
    wire [127:0] bs_data, bs2_data;
    wire        bs_first, bs_last;
    wire [4:0]  bs_count, bs2_count;
    wire        wr_valid, wr_ready;
    wire [35:0] wr_addr;
    wire [127:0] wr_data;
    wire [15:0] wr_wstrb;

    msh_fetch u_fetch (
        .clk(clk), .rst_n(rst_n),
        .mem_req_valid(mem_req_valid), .mem_req_ready(mem_req_ready),
        .mem_req_write(mem_req_write), .mem_req_addr(mem_req_addr),
        .mem_req_wdata(mem_req_wdata), .mem_req_wstrb(mem_req_wstrb),
        .mem_rsp_valid(mem_rsp_valid), .mem_rsp_ready(mem_rsp_ready),
        .mem_rsp_rdata(mem_rsp_rdata),
        .seg_valid(seg_valid), .seg_ready(seg_ready),
        .seg_addr(seg_addr), .seg_len(seg_len), .seg_tag(seg_tag),
        .bs_valid(bs_valid), .bs_ready(bs_ready), .bs_data(bs_data),
        .bs_first(bs_first), .bs_last(bs_last), .bs_tag(bs_tag),
        .bs_shift(bs_shift), .bs_count(bs_count),
        .bs2_valid(bs2_valid), .bs2_ready(bs2_ready), .bs2_data(bs2_data),
        .bs2_first(bs2_first), .bs2_last(bs2_last), .bs2_tag(bs2_tag),
        .bs2_shift(bs2_shift), .bs2_count(bs2_count),
        .wr_valid(wr_valid), .wr_ready(wr_ready),
        .wr_addr(wr_addr), .wr_data(wr_data), .wr_wstrb(wr_wstrb),
        .hq_fill_done(hq_fill_done),
        .hq_v(hq_v), .hq_v2(hq_v2), .hq_d0(hq_d0), .hq_d1(hq_d1),
        .hq_f0(hq_f0), .hq_l0(hq_l0), .hq_l1(hq_l1), .hq_sh0(hq_sh0),
        .hq_c0(hq_c0), .hq_c1(hq_c1), .hq_pop(hq_pop), .hq_pop2(hq_pop2),
        .hq_rewind(hq_rewind)
    );
    wire        hq_fill_done, hq_v, hq_v2, hq_pop, hq_pop2, hq_rewind;
    wire [127:0] hq_d0, hq_d1;
    wire        hq_f0, hq_l0, hq_l1;
    wire [3:0]  hq_sh0;
    wire [4:0]  hq_c0, hq_c1;

    // 2-beat pops are driven by the gemv's 32B intake (milestone 2)
    // and never while the deq owns the stream

    // ================= byte-stream mux (bs_owner: 0 seq, 1 gemv/deq) =====
    wire        bs_owner;
    wire        seq_bs_ready, gv_bs_ready, gv_bs2_ready;
    assign bs_ready  = bs_owner ? gv_bs_ready : seq_bs_ready;
    // 2-beat pops: only the gemv (never the seq, never while deq owns)
    assign bs2_ready = bs_owner ? gv_bs2_ready : 1'b0;

    // ================= XBUF =================
    wire [13:0]  xa_addr, xb_addr, xw_addr;
    wire [127:0] xa_data, xb_data, xw_data;
    wire         xw_we;
    wire [3:0]   xw_mask;

    msh_xbuf u_xbuf (
        .clk(clk),
        .a_addr(xa_addr), .a_rdata(xa_data),
        .b_addr(xb_addr), .b_rdata(xb_data),
        .w_we(xw_we), .w_addr(xw_addr), .w_wdata(xw_data),
        .w_wmask(xw_mask)
    );

    // ================= engine job buses (from seq) =================
    // gemv/deq
    wire        gv_valid, gv_ready, gv_done;
    wire [1:0]  gv_mode;
    wire [35:0] gv_q_addr, gv_s_addr, gv_z_addr;
    wire [15:0] gv_K, gv_gsz;
    wire [17:0] gv_N;
    wire [3:0]  gv_ng;
    wire [7:0]  gv_R;
    wire [4:0]  gv_xbuf, gv_ybuf;
    wire [31:0] gv_am_val;
    wire [17:0] gv_am_idx;
    wire        gv_deq = (gv_mode == 2'd2);
    wire        gv_am_valid, deq_done;
    reg  [1:0]  gv_mode_done_r;
    // done source follows the accepted job's mode (gemv vs deq)
    wire        gv_done_any = (gv_mode_done_r == 2'd2) ? deq_done
                            :                              gv_done;

    wire        gemv_job_v = gv_valid && !gv_deq;
    wire        deq_job_v  = gv_valid && gv_deq;
    wire        gemv_ready, deq_ready;
    assign gv_ready = gv_deq ? deq_ready : gemv_ready;

    // vec
    wire        vc_valid, vc_ready, vc_done;
    wire [4:0]  vc_code;
    wire [11:0] vc_len;
    wire [4:0]  vc_src1, vc_src2, vc_dst;
    wire [14:0] vc_wbase;
    wire [31:0] vc_aux;
    wire        vc_res_valid;
    wire [31:0] vc_res_data;

    // kda
    wire        kd_valid, kd_ready, kd_done;
    wire [2:0]  kd_layer;
    wire [9:0]  kd_dh;
    wire [3:0]  kd_H;
    wire [16:0] kd_cdh;
    wire [4:0]  kd_q, kd_k, kd_v, kd_beta, kd_alpha, kd_o;

    // mla
    wire        ml_valid, ml_ready, ml_done;
    wire [9:0]  ml_pos, ml_dqk, ml_dv, ml_dk;
    wire [3:0]  ml_H;
    wire [16:0] ml_catt;
    wire [4:0]  ml_qc, ml_qr, ml_kc, ml_kr, ml_v, ml_ctx;

    // ================= XBUF read-port muxes =================
    // vec ports
    wire [13:0]  vc_xa_addr, vc_xb_addr, vc_xw_addr;
    wire [127:0] vc_xw_data;
    wire         vc_xw_we;
    wire [3:0]   vc_xw_mask;
    // kda ports
    wire [12:0]  kd_xr0_addr, kd_xr1_addr, kd_xw_addr;
    wire [127:0] kd_xw_data;
    wire         kd_xw_we;
    wire [3:0]   kd_xw_mask;
    // mla ports
    wire [12:0]  ml_xr0_addr, ml_xr1_addr, ml_xw_addr;
    wire [127:0] ml_xw_data;
    wire         ml_xw_we;
    wire [3:0]   ml_xw_mask;
    // gemv x port (word + demux)
    wire [11:0]  gv_x_addr;
    wire [31:0]  gv_x_e, gv_x_o;

    // current gemv job's xbuf (registered at accept)
    reg [3:0] gv_xbuf_r;
    always @(posedge clk) begin
        if (!rst_n) gv_xbuf_r <= 4'd0;
        else if (gemv_job_v && gemv_ready) gv_xbuf_r <= gv_xbuf[3:0];
    end

    // busy flags (one-hot by serialization; deq shares gemv's slots)
    wire gemv_busy, deq_busy, vc_busy, kd_busy, ml_busy;

    // read-port ownership tracks the currently accepted job (busy-based
    // ownership is wrong while engines sit in their reset clear sweeps:
    // they held the ports with addr 0 during the first GEMVs).
    // 0 = gemv-x (default), 1 = vec, 2 = kda, 3 = mla
    reg [1:0] rd_owner;
    always @(posedge clk) begin
        if (!rst_n) rd_owner <= 2'd0;
        else if (vc_valid && vc_ready) rd_owner <= 2'd1;
        else if (kd_valid && kd_ready) rd_owner <= 2'd2;
        else if (ml_valid && ml_ready) rd_owner <= 2'd3;
        else if (gv_valid && gv_ready)  rd_owner <= 2'd0;
        else if (vc_done || kd_done || ml_done || gv_done_any)
            rd_owner <= 2'd0;
    end
    wire [12:0] gx_word_addr = {gv_xbuf_r, 2'b00, gv_x_addr[7:1]};
    assign xa_addr = (rd_owner == 2'd1) ? vc_xa_addr
                   : (rd_owner == 2'd2) ? {1'b0, kd_xr0_addr}
                   : (rd_owner == 2'd3) ? {1'b0, ml_xr0_addr}
                   :                      {1'b0, gx_word_addr};
    assign xb_addr = (rd_owner == 2'd1) ? vc_xb_addr
                   : (rd_owner == 2'd2) ? {1'b0, kd_xr1_addr}
                   : (rd_owner == 2'd3) ? {1'b0, ml_xr1_addr}
                   :                      14'd0;

    // gemv x demux: the RAM data is one cycle stale relative to x_addr,
    // so the lane parity must be registered with the read (else the lanes
    // swap at every row-boundary chunk).
    reg gx_par;
    always @(posedge clk) begin
        if (!rst_n) gx_par <= 1'b0;
        else        gx_par <= gv_x_addr[0];
    end
    assign gv_x_e = gx_par ? xa_data[95:64]  : xa_data[31:0];
    assign gv_x_o = gx_par ? xa_data[127:96] : xa_data[63:32];

    // write mux: vec > kda > mla > gemv-y > deq-y
    wire        gv_y_we;
    wire [11:0] gv_y_addr;
    wire [127:0] gv_y_data;
    wire [3:0]  gv_y_wstrb;
    wire [3:0]  gv_y_buf;
    wire        deq_y_we;
    wire [11:0] deq_y_addr;
    wire [127:0] deq_y_data;
    wire [3:0]  deq_y_buf;

    // head-mode y goes to LG instead of XBUF; the column index is counted
    // at the top (gemv y_addr wraps at 4096; the y stream is strictly
    // in-order from column 0 of each head job)
    reg [1:0]  gv_mode_r;
    reg [17:0] gv_y_col;
    always @(posedge clk) begin
        if (!rst_n) begin
            gv_mode_r      <= 2'd0;
            gv_mode_done_r <= 2'd0;
            gv_y_col       <= 18'd0;
        end else if (gv_valid && gv_ready) begin
            gv_mode_r      <= gv_mode;
            gv_mode_done_r <= gv_mode;
            gv_y_col       <= 18'd0;
        end else if (gv_y_we && gv_y_to_lg) begin
            // 4 columns per y beat (head-mode N is a multiple of 16, so
            // every head-mode beat carries 4 valid lanes)
            gv_y_col       <= gv_y_col + 18'd4;
        end
    end
    wire gv_y_to_lg = (gv_mode_r == 2'd1);

    // request-based write arbitration (busy-based ownership drops writes
    // while another engine sits in its reset clear with xw_we == 0).
    wire wr_req_vec = vc_xw_we;
    wire wr_req_kda = kd_xw_we;
    wire wr_req_mla = ml_xw_we;
    wire wr_req_deq = deq_y_we;
    wire wr_req_gv  = gv_y_we && !gv_y_to_lg;
    assign xw_we   = wr_req_vec | wr_req_kda | wr_req_mla | wr_req_deq
                   | wr_req_gv;
    assign xw_addr = wr_req_vec ? vc_xw_addr
                   : wr_req_kda ? {1'b0, kd_xw_addr}
                   : wr_req_mla ? {1'b0, ml_xw_addr}
                   : wr_req_deq ? {1'b0, deq_y_buf[3:0], deq_y_addr[8:0]}
                   :              {1'b0, gv_y_buf[3:0], gv_y_addr[10:2]};
    assign xw_data = wr_req_vec ? vc_xw_data
                   : wr_req_kda ? kd_xw_data
                   : wr_req_mla ? ml_xw_data
                   : wr_req_deq ? deq_y_data
                   :              gv_y_data;
    assign xw_mask = wr_req_vec ? vc_xw_mask
                   : wr_req_kda ? kd_xw_mask
                   : wr_req_mla ? ml_xw_mask
                   : wr_req_deq ? 4'hF
                   :              gv_y_wstrb;

    // ================= LG RAM (head-mode logits staging) =================
    wire [15:0] lg_raddr;
    wire [127:0] lg_rdata;
    wire        lg_we    = gv_y_we && gv_y_to_lg;
    // full 18-bit column -> 16-bit word address (vocab up to 262144;
    // the earlier [15:2] slice wrapped at 65536 lanes = full-config
    // logits for indices >= 65536 lost/overwritten)
    wire [15:0] lg_waddr = gv_y_col[17:2];
    wire [127:0] lg_wdata = gv_y_data;
    wire [3:0]  lg_wmask = gv_y_wstrb;

    msh_lg u_lg (
        .clk(clk),
        .a_addr(lg_raddr), .a_rdata(lg_rdata),
        .w_we(lg_we), .w_addr(lg_waddr), .w_wdata(lg_wdata),
        .w_wmask(lg_wmask)
    );

    // ================= WBUF / DESC / TOK / HS-HZ =================
    wire [14:0] vc_w_addr14;
    wire [15:0] vc_w_data, vc_w2_data;
    wire [14:0] vc_w2_addr14;
    wire        wb_we;
    wire [14:0] wb_waddr;
    wire [15:0] wb_wdata;

    msh_wbuf u_wbuf (
        .clk(clk),
        .a_addr(vc_w_addr14), .a_rdata(vc_w_data),
        .b_addr(vc_w2_addr14), .b_rdata(vc_w2_data),
        .w_we(wb_we), .w_addr(wb_waddr), .w_wdata(wb_wdata)
    );

    wire [14:0]  desc_raddr, desc_waddr;
    wire [127:0] desc_rdata, desc_wdata;
    wire         desc_we;
    msh_desc u_desc (
        .clk(clk),
        .a_addr(desc_raddr), .a_rdata(desc_rdata),
        .w_we(desc_we), .w_addr(desc_waddr), .w_wdata(desc_wdata)
    );

    wire [8:0]  tok_raddr, tok_waddr;
    wire [31:0] tok_rdata, tok_wdata;
    wire        tok_we;
    msh_tok u_tok (
        .clk(clk),
        .a_addr(tok_raddr), .a_rdata(tok_rdata),
        .w_we(tok_we), .w_addr(tok_waddr), .w_wdata(tok_wdata)
    );

    // HS/HZ: 128b-word resident head s/z (gemv word read), element-write
    // RMW from seq's startup stream (handled inside msh_hsz).
    wire [17:0]  hs_addr, hz_addr;
    wire [127:0] hs_rdata, hz_rdata;
    wire         hs_we, hz_we;
    wire [18:0]  hs_waddr, hz_waddr;
    wire [15:0]  hs_wdata;
    wire [7:0]   hz_wdata;

    msh_hsz u_hsz (
        .clk(clk),
        .s_addr(hs_addr), .s_rdata(hs_rdata),
        .z_addr(hz_addr), .z_rdata(hz_rdata),
        .s_we(hs_we), .s_waddr(hs_waddr), .s_wdata(hs_wdata),
        .z_we(hz_we), .z_waddr(hz_waddr), .z_wdata(hz_wdata)
    );

    // ================= engines =================
    wire [17:0]  gemv_hs_addr, gemv_hz_addr;
    wire [127:0] gemv_hs_data, gemv_hz_data;
    wire         gemv_ws_ready, gemv_ws2_ready;
    wire         gv_hq_use;
    // when the head job drains the shadow buffer, the byte stream is
    // not consumed (and must not be popped)
    assign gv_bs_ready  = gv_hq_use ? 1'b0
                        : (deq_busy ? deq_ws_ready : gemv_ws_ready);
    assign gv_bs2_ready = gv_hq_use ? 1'b0 : (!deq_busy && gemv_ws2_ready);
    // pops must mirror the gemv intake fires exactly (valid-gated): an
    // ungated pop would drain the shadow reader while the gemv sees no
    // valid beat, scrambling the pop-counter-derived beat meta
    assign hq_pop       = gv_hq_use && hq_v  && gemv_ws_ready;
    assign hq_pop2      = gv_hq_use && hq_v2 && gemv_ws2_ready;

    // gemv stream intake: shadow channel for the head job when resident
    wire         gemv_ws_valid  = gv_hq_use ? hq_v : (bs_valid && bs_owner);
    wire [127:0] gemv_ws_data   = gv_hq_use ? hq_d0 : bs_data;
    wire [4:0]   gemv_ws_count  = gv_hq_use ? hq_c0 : bs_count;
    wire [3:0]   gemv_ws_shift  = gv_hq_use ? hq_sh0 : bs_shift;
    wire         gemv_ws_last   = gv_hq_use ? hq_l0 : bs_last;
    wire         gemv_ws2_valid = gv_hq_use ? hq_v2 : (bs2_valid && bs_owner);
    wire [127:0] gemv_ws2_data  = gv_hq_use ? hq_d1 : bs2_data;
    wire [4:0]   gemv_ws2_count = gv_hq_use ? hq_c1 : bs2_count;

    msh_gemv u_gemv (
        .clk(clk), .rst_n(rst_n),
        .job_valid(gemv_job_v), .job_ready(gemv_ready),
        .job_mode(gv_mode[0]),
        .job_q_addr(gv_q_addr), .job_K(gv_K), .job_N(gv_N),
        .job_ng(gv_ng[2:0]), .job_gsz(gv_gsz[7:0]),
        .job_s_addr(gv_s_addr), .job_z_addr(gv_z_addr),
        .job_R(gv_R), .job_xbuf(gv_xbuf[3:0]), .job_ybuf(gv_ybuf[3:0]),
        .x_addr(gv_x_addr), .x_data_e(gv_x_e), .x_data_o(gv_x_o),
        .ws_valid(gemv_ws_valid), .ws_ready(gemv_ws_ready),
        .ws_data(gemv_ws_data), .ws_count(gemv_ws_count),
        .ws_shift(gemv_ws_shift), .ws_last(gemv_ws_last),
        .ws2_valid(gemv_ws2_valid), .ws2_ready(gemv_ws2_ready),
        .ws2_data(gemv_ws2_data), .ws2_count(gemv_ws2_count),
        .hq_fill_done(hq_fill_done), .gv_hq_use(gv_hq_use),
        .hs_addr(gemv_hs_addr), .hs_data(gemv_hs_data),
        .hz_addr(gemv_hz_addr), .hz_data(gemv_hz_data),
        .y_we(gv_y_we), .y_addr(gv_y_addr), .y_data(gv_y_data),
        .y_wstrb(gv_y_wstrb),
        .y_buf(gv_y_buf),
        .am_val(gv_am_val), .am_idx(gv_am_idx), .am_valid(gv_am_valid),
        .done(gv_done)
    );
    assign gemv_busy = !gemv_ready;
    assign hs_addr = gemv_hs_addr;
    assign hz_addr = gemv_hz_addr;
    assign gemv_hs_data = hs_rdata;
    assign gemv_hz_data = hz_rdata;

    wire deq_ws_ready;
    msh_deq u_deq (
        .clk(clk), .rst_n(rst_n),
        .job_valid(deq_job_v), .job_ready(deq_ready),
        .job_d(gv_N[15:0]), .job_gsz(gv_gsz[7:0]), .job_ybuf(gv_ybuf[3:0]),
        .ws_valid(bs_valid && bs_owner), .ws_ready(deq_ws_ready),
        .ws_data(bs_data), .ws_count(bs_count), .ws_shift(bs_shift),
        .ws_last(bs_last),
        .y_we(deq_y_we), .y_addr(deq_y_addr), .y_data(deq_y_data),
        .y_buf(deq_y_buf),
        .done(deq_done)
    );
    assign deq_busy = !deq_ready;

    msh_vec u_vec (
        .clk(clk), .rst_n(rst_n),
        .op_valid(vc_valid), .op_ready(vc_ready),
        .op_code(vc_code), .op_len(vc_len),
        .op_src1({1'b0, vc_src1[3:0]}), .op_src2({1'b0, vc_src2[3:0]}),
        .op_dst({1'b0, vc_dst[3:0]}), .op_wbase(vc_wbase), .op_aux(vc_aux),
        .op_done(vc_done),
        .xa_addr(vc_xa_addr), .xa_data(xa_data),
        .xb_addr(vc_xb_addr), .xb_data(xb_data),
        .xw_we(vc_xw_we), .xw_addr(vc_xw_addr), .xw_data(vc_xw_data),
        .xw_mask(vc_xw_mask),
        .w_addr(vc_w_addr14), .w_data(vc_w_data),
        .w2_addr(vc_w2_addr14), .w2_data(vc_w2_data),
        .dot_val({vc_res_data_hi, vc_res_data}), .dot_valid(vc_res_valid)
    );
    wire [31:0] vc_res_data_hi;
    assign vc_busy = !vc_ready;

    msh_kda u_kda (
        .clk(clk), .rst_n(rst_n),
        .job_valid(kd_valid), .job_ready(kd_ready),
        .job_layer(kd_layer[1:0]), .job_dh(kd_dh[8:0]), .job_H(kd_H),
        .job_c_dh(kd_cdh),
        .job_q_buf(kd_q[3:0]), .job_k_buf(kd_k[3:0]),
        .job_v_buf(kd_v[3:0]), .job_beta_buf(kd_beta[3:0]),
        .job_alpha_buf(kd_alpha[3:0]), .job_z_buf(4'd0),
        .job_o_buf(kd_o[3:0]),
        .job_done(kd_done),
        .xr0_addr(kd_xr0_addr), .xr0_data(xa_data),
        .xr1_addr(kd_xr1_addr), .xr1_data(xb_data),
        .xw_we(kd_xw_we), .xw_addr(kd_xw_addr), .xw_data(kd_xw_data),
        .xw_wstrb(kd_xw_mask),
        .s_dbg_addr(18'd0), .s_dbg_data(kda_dbg_unused)
    );
    wire [31:0] kda_dbg_unused;
    assign kd_busy = !kd_ready;

    msh_mla u_mla (
        .clk(clk), .rst_n(rst_n),
        .job_valid(ml_valid), .job_ready(ml_ready),
        .job_pos(ml_pos), .job_dqk(ml_dqk), .job_dv(ml_dv),
        .job_dk(ml_dk), .job_H(ml_H), .job_c_att(ml_catt),
        .job_qc_buf(ml_qc[3:0]), .job_qr_buf(ml_qr[3:0]),
        .job_kc_buf(ml_kc[3:0]), .job_kr_buf(ml_kr[3:0]),
        .job_v_buf(ml_v[3:0]), .job_ctx_buf(ml_ctx[3:0]),
        .job_done(ml_done),
        .xr0_addr(ml_xr0_addr), .xr0_data(xa_data),
        .xr1_addr(ml_xr1_addr), .xr1_data(xb_data),
        .xw_we(ml_xw_we), .xw_addr(ml_xw_addr), .xw_data(ml_xw_data),
        .xw_wstrb(ml_xw_mask)
    );
    assign ml_busy = !ml_ready;

    // ================= sequencer =================
    wire        seq_cmd_ready, seq_rsp_valid;
    wire [31:0] seq_rsp_data;
    assign cmd_ready = seq_cmd_ready;
    assign rsp_valid = seq_rsp_valid;
    assign rsp_data  = seq_rsp_data;

    msh_seq u_seq (
        .clk(clk), .rst_n(rst_n),
        .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cmd_ready(seq_cmd_ready),
        .rsp_data(seq_rsp_data), .rsp_valid(seq_rsp_valid),
        .rsp_ready(rsp_ready),
        .seg_valid(seg_valid), .seg_ready(seg_ready),
        .seg_addr(seg_addr), .seg_len(seg_len), .seg_tag(seg_tag),
        .bs_valid(bs_valid && !bs_owner), .bs_ready(seq_bs_ready),
        .bs_data(bs_data), .bs_first(bs_first), .bs_last(bs_last),
        .bs_tag(bs_tag), .bs_shift(bs_shift), .bs_count(bs_count),
        .bs_owner(bs_owner), .hq_fill_done(hq_fill_done),
        .hq_rewind(hq_rewind),
        .wr_valid(wr_valid), .wr_ready(wr_ready),
        .wr_addr(wr_addr), .wr_data(wr_data), .wr_wstrb(wr_wstrb),
        .gv_valid(gv_valid), .gv_ready(gv_ready),
        .gv_mode(gv_mode), .gv_q_addr(gv_q_addr), .gv_K(gv_K),
        .gv_N(gv_N), .gv_ng(gv_ng), .gv_gsz(gv_gsz),
        .gv_s_addr(gv_s_addr), .gv_z_addr(gv_z_addr), .gv_R(gv_R),
        .gv_xbuf(gv_xbuf), .gv_ybuf(gv_ybuf),
        .gv_done(gv_done_any), .gv_am_val(gv_am_val), .gv_am_idx(gv_am_idx),
        .gv_gready(gemv_ready), .gv_dready(deq_ready),
        .vc_valid(vc_valid), .vc_ready(vc_ready),
        .vc_code(vc_code), .vc_len(vc_len),
        .vc_src1(vc_src1), .vc_src2(vc_src2), .vc_dst(vc_dst),
        .vc_wbase(vc_wbase), .vc_aux(vc_aux),
        .vc_done(vc_done),
        .vc_res_valid(vc_res_valid), .vc_res_data(vc_res_data),
        .kd_valid(kd_valid), .kd_ready(kd_ready),
        .kd_layer(kd_layer), .kd_dh(kd_dh), .kd_H(kd_H), .kd_cdh(kd_cdh),
        .kd_q(kd_q), .kd_k(kd_k), .kd_v(kd_v),
        .kd_beta(kd_beta), .kd_alpha(kd_alpha), .kd_o(kd_o),
        .kd_done(kd_done),
        .ml_valid(ml_valid), .ml_ready(ml_ready),
        .ml_pos(ml_pos), .ml_dqk(ml_dqk), .ml_dv(ml_dv),
        .ml_dk(ml_dk), .ml_H(ml_H), .ml_catt(ml_catt),
        .ml_qc(ml_qc), .ml_qr(ml_qr), .ml_kc(ml_kc), .ml_kr(ml_kr),
        .ml_v(ml_v), .ml_ctx(ml_ctx),
        .ml_done(ml_done),
        .desc_raddr(desc_raddr), .desc_rdata(desc_rdata),
        .desc_we(desc_we), .desc_waddr(desc_waddr), .desc_wdata(desc_wdata),
        .tok_raddr(tok_raddr), .tok_rdata(tok_rdata),
        .tok_we(tok_we), .tok_waddr(tok_waddr), .tok_wdata(tok_wdata),
        .wb_we(wb_we), .wb_waddr(wb_waddr), .wb_wdata(wb_wdata),
        .hs_we(hs_we), .hs_waddr(hs_waddr), .hs_wdata(hs_wdata),
        .hz_we(hz_we), .hz_waddr(hz_waddr), .hz_wdata(hz_wdata),
        .lg_raddr(lg_raddr), .lg_rdata(lg_rdata)
    );

`ifdef MSH_DEBUG
    always @(posedge clk) begin
        if (gv_valid && gv_ready)
            $display("[gv] JOB mode=%0d K=%0d N=%0d gsz=%0d R=%0d ybuf=%0d",
                     gv_mode, gv_K, gv_N, gv_gsz, gv_R, gv_ybuf);
        if (gv_done_any)
            $display("[gv] DONE mode_r=%0d", gv_mode_done_r);
        if (deq_y_we)
            $display("[top] deq_y_we=1 deq_busy=%0d vc_busy=%0d xw_we=%0d xw_addr=%0d",
                     deq_busy, vc_busy, xw_we, xw_addr);
        if (gemv_busy && (gv_x_addr != 12'd0))
            $display("[top] gx r=%0d xa_addr=%0d xa_data=%032x xbuf_r=%0d b%b%b%b%b",
                     gv_x_addr, xa_addr, xa_data, gv_xbuf_r,
                     vc_busy, kd_busy, ml_busy, deq_busy);
        if (xw_we)
            $display("[xw] addr=%0d data=%032x mask=%b req=%b%b%b%b%b",
                     xw_addr, xw_data, xw_mask,
                     wr_req_vec, wr_req_kda, wr_req_mla, wr_req_deq,
                     wr_req_gv);
        if (lg_we)
            $display("[lg] addr=%0d data=%08x mask=%b",
                     lg_waddr, gv_y_data, lg_wmask);
    end
`endif
    wire _unused = &{1'b0, bs_first, bs_tag, gv_am_valid, hq_f0, hq_l1,
                     bs2_first, bs2_last, bs2_tag, bs2_shift,
                     kda_dbg_unused, gemv_busy, vc_busy, kd_busy, ml_busy,
                     gv_x_addr[11:8], deq_y_addr[11:9],
                     gv_y_addr[11], gv_y_addr[1:0],
                     vc_res_data_hi, kd_dh[9], ml_dk[9],
                     gv_gsz[15:8], gv_ng[3], gv_xbuf[4], gv_ybuf[4],
                     vc_src1[4], vc_src2[4], vc_dst[4],
                     kd_layer[2], kd_q[4], kd_k[4], kd_v[4], kd_beta[4],
                     kd_alpha[4], kd_o[4],
                     ml_qc[4], ml_qr[4], ml_kc[4], ml_kr[4], ml_v[4],
                     ml_ctx[4],
                     gv_K[15:12], gv_N[17:16]};
endmodule

`default_nettype wire
