// msh_lg.v -- logits staging RAM (harness msh_sram macro): 128 x 128b
// holds one position's vocab row of int32 logits (nano vocab 512 / 4
// lanes = 128 words; the head-mode y stream stripes by position and the
// top-level column counter resets per head job). One read port
// (sequencer readback), one lane-masked write port (gemv head-mode y).

`default_nettype none

module msh_lg (
    input  wire         clk,
    input  wire [15:0]  a_addr,
    output wire [127:0] a_rdata,
    input  wire         w_we,
    input  wire [15:0]  w_addr,
    input  wire [127:0] w_wdata,
    input  wire [3:0]   w_wmask
);
    // 4 int32 lanes per word: 4-bit lane strobe -> per-byte strobes
    wire [15:0] w_wstrb = {{4{w_wmask[3]}}, {4{w_wmask[2]}},
                           {4{w_wmask[1]}}, {4{w_wmask[0]}}};

    msh_sram #(.DEPTH(128), .WIDTH(128)) u_mem (
        .clk(clk),
        .we(w_we), .waddr(w_addr[6:0]), .wdata(w_wdata), .wstrb(w_wstrb),
        .re(1'b1), .raddr(a_addr[6:0]), .rdata(a_rdata));

    wire _unused = &{1'b0, a_addr[15:7], w_addr[15:7]};
endmodule

`default_nettype wire
