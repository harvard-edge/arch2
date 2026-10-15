// Blackbox stub of msh_sram for the synthesis/metrics flows: the macro's
// internals are not mapped to standard cells; instances are priced from
// their DEPTH/WIDTH parameters (see evaluate.py) and cut all combinational
// paths (fully synchronous interface).

(* blackbox *)
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
    output wire [WIDTH-1:0]     rdata
);
endmodule
