// msh_mem.v -- shared on-chip memories for msh_chip_top (nano task).
//
// All storage goes through the harness msh_sram macro (macros_only rule;
// inferred $mem fails the audit). Dual-read-port modules (XBUF/WBUF) use
// two write-synchronized macro copies. HSZ element writes map onto the
// macro's per-byte write strobes directly (no read-modify-write needed).
// Reads are synchronous (1-cycle registered), matching the original
// modules' behavior.
//
// Depths are sized for the nano config with margin for stretched
// sequence lengths and group_size 64 (both announced in the image
// header; the design self-configures, RAM depths are static). Address
// layout per consumer: {buf[3:0], word[8:0]} 13-bit external address,
// word index into the macro = {addr[12:9], addr[4:0]} (16 bufs x
// 32 words; max vector staged per buffer = mla_dc = 128 int32 lanes
// = 32 words; max buffer index B_B0 = 14).
//   XBUF  16 bufs x 32 words x 128b (2 copies)   WBUF  2048 x 16b (2)
//   DESC  512 x 128b (nano NT = 246)             TOK   512 x 32b
//   HS    128 words (2 groups x 512 vocab / 8)   HZ    64 words

`default_nettype none
/* verilator lint_off DECLFILENAME */

module msh_xbuf (
    input  wire         clk,
    // port A (read)
    input  wire [13:0]  a_addr,      // {buf[4:0], word[8:0]}
    output wire [127:0] a_rdata,
    // port B (read)
    input  wire [13:0]  b_addr,
    output wire [127:0] b_rdata,
    // port W (write)
    input  wire         w_we,
    input  wire [13:0]  w_addr,
    input  wire [127:0] w_wdata,
    input  wire [3:0]   w_wmask
);
    // 4 int32 lanes per word: 4-bit lane strobe -> per-byte strobes
    wire [15:0] w_wstrb = {{4{w_wmask[3]}}, {4{w_wmask[2]}},
                           {4{w_wmask[1]}}, {4{w_wmask[0]}}};

    msh_sram #(.DEPTH(512), .WIDTH(128)) u_a (
        .clk(clk),
        .we(w_we), .waddr({w_addr[12:9], w_addr[4:0]}),
        .wdata(w_wdata), .wstrb(w_wstrb),
        .re(1'b1), .raddr({a_addr[12:9], a_addr[4:0]}), .rdata(a_rdata)
    );
    msh_sram #(.DEPTH(512), .WIDTH(128)) u_b (
        .clk(clk),
        .we(w_we), .waddr({w_addr[12:9], w_addr[4:0]}),
        .wdata(w_wdata), .wstrb(w_wstrb),
        .re(1'b1), .raddr({b_addr[12:9], b_addr[4:0]}), .rdata(b_rdata)
    );

    wire _unused = &{1'b0, a_addr[13], b_addr[13], w_addr[13],
                     a_addr[8:5], b_addr[8:5], w_addr[8:5]};
endmodule


// WBUF: 2048 x 16b int16 params (norm offsets, proj, conv, A, dtb, bias;
// nano uses 1970).
module msh_wbuf (
    input  wire         clk,
    input  wire [14:0]  a_addr,
    output wire [15:0]  a_rdata,
    input  wire [14:0]  b_addr,
    output wire [15:0]  b_rdata,
    input  wire         w_we,
    input  wire [14:0]  w_addr,
    input  wire [15:0]  w_wdata
);
    msh_sram #(.DEPTH(2048), .WIDTH(16)) u_a (
        .clk(clk),
        .we(w_we), .waddr(w_addr[10:0]), .wdata(w_wdata), .wstrb(2'b11),
        .re(1'b1), .raddr(a_addr[10:0]), .rdata(a_rdata)
    );
    msh_sram #(.DEPTH(2048), .WIDTH(16)) u_b (
        .clk(clk),
        .we(w_we), .waddr(w_addr[10:0]), .wdata(w_wdata), .wstrb(2'b11),
        .re(1'b1), .raddr(b_addr[10:0]), .rdata(b_rdata)
    );

    wire _unused = &{1'b0, a_addr[14:11], b_addr[14:11], w_addr[14:11]};
endmodule


// DESC: descriptor table copy, 512 x 128b (nano NT = 246).
module msh_desc (
    input  wire         clk,
    input  wire [14:0]  a_addr,
    output wire [127:0] a_rdata,
    input  wire         w_we,
    input  wire [14:0]  w_addr,
    input  wire [127:0] w_wdata
);
    msh_sram #(.DEPTH(512), .WIDTH(128)) u_mem (
        .clk(clk),
        .we(w_we), .waddr(w_addr[8:0]), .wdata(w_wdata), .wstrb(16'hFFFF),
        .re(1'b1), .raddr(a_addr[8:0]), .rdata(a_rdata)
    );

    wire _unused = &{1'b0, a_addr[14:9], w_addr[14:9]};
endmodule


// HS/HZ: resident LM-head scales/zeros, 128b-word organization for the
// msh_gemv head-fold (s: 8 x int16 lanes/word, z: 16 x uint8 lanes/word).
// Element writes use the macro's per-byte strobes directly (s = 2-byte
// lane, z = 1-byte lane), so no read-modify-write is needed. Reads are
// synchronous (1-cycle) — the gemv fold issues addresses one cycle early.
module msh_hsz (
    input  wire         clk,
    input  wire [17:0]  s_addr,      // WORD address (gemv fold)
    output wire [127:0] s_rdata,
    input  wire [17:0]  z_addr,
    output wire [127:0] z_rdata,
    input  wire         s_we,        // element write (seq startup)
    input  wire [18:0]  s_waddr,     // element index
    input  wire [15:0]  s_wdata,
    input  wire         z_we,
    input  wire [18:0]  z_waddr,
    input  wire [7:0]   z_wdata
);
    // s: int16 element at word s_waddr[18:3], lane s_waddr[2:0]
    wire [15:0] s_wstrb = 16'h0003 << {s_waddr[2:0], 1'b0};
    wire [127:0] s_wpat = {8{s_wdata}};
    msh_sram #(.DEPTH(128), .WIDTH(128)) u_s (
        .clk(clk),
        .we(s_we), .waddr(s_waddr[9:3]), .wdata(s_wpat), .wstrb(s_wstrb),
        .re(1'b1), .raddr(s_addr[6:0]), .rdata(s_rdata)
    );
    // z: uint8 element at word z_waddr[18:4], lane z_waddr[3:0]
    wire [15:0] z_wstrb = 16'h0001 << z_waddr[3:0];
    wire [127:0] z_wpat = {16{z_wdata}};
    msh_sram #(.DEPTH(64), .WIDTH(128)) u_z (
        .clk(clk),
        .we(z_we), .waddr(z_waddr[9:4]), .wdata(z_wpat), .wstrb(z_wstrb),
        .re(1'b1), .raddr(z_addr[5:0]), .rdata(z_rdata)
    );

    wire _unused = &{1'b0, s_addr[17:7], z_addr[17:6],
                     s_waddr[18:10], z_waddr[18:10],
                     s_wpat, z_wpat};
endmodule


// TOK: token ids, 512 x 32b.
module msh_tok (
    input  wire         clk,
    input  wire [8:0]   a_addr,
    output wire [31:0]  a_rdata,
    input  wire         w_we,
    input  wire [8:0]   w_addr,
    input  wire [31:0]  w_wdata
);
    msh_sram #(.DEPTH(512), .WIDTH(32)) u_mem (
        .clk(clk),
        .we(w_we), .waddr(w_addr), .wdata(w_wdata), .wstrb(4'hF),
        .re(1'b1), .raddr(a_addr), .rdata(a_rdata)
    );
endmodule
