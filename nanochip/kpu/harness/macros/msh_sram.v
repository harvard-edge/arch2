// msh_sram -- harness-provided on-chip SRAM macro: 1 write port + 1 read
// port, synchronous (registered) read, per-byte write enables.
// Same-cycle read+write to the same address returns the OLD data.
// Instantiated by the design; injected by the harness (do NOT redefine or
// list this file in rtl/filelist.f). WIDTH must be a multiple of 8.

module msh_sram #(
    parameter integer DEPTH = 1024,
    parameter integer WIDTH = 128,
    parameter integer ADDRW = $clog2(DEPTH)
) (
    input  wire                 clk,
    input  wire                 we,
    input  wire [ADDRW-1:0]     waddr,
    input  wire [WIDTH-1:0]     wdata,
    input  wire [WIDTH/8-1:0]   wstrb,
    input  wire                 re,
    input  wire [ADDRW-1:0]     raddr,
    output reg  [WIDTH-1:0]     rdata
);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    genvar b;
    generate
        for (b = 0; b < WIDTH/8; b = b + 1) begin : g_wbyte
            always @(posedge clk)
                if (we && wstrb[b])
                    mem[waddr][8*b +: 8] <= wdata[8*b +: 8];
        end
    endgenerate

    always @(posedge clk)
        if (re)
            rdata <= mem[raddr];

endmodule
