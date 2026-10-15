// Blackbox stub of msh_rom for the synthesis/metrics flows: the macro's
// internals are not mapped to standard cells; instances are priced from their
// DEPTH/WIDTH parameters (see evaluate.py). Read-only (constant LUT) macro,
// two asynchronous read ports -- see msh_rom.v for the full rationale.

(* blackbox *)
module msh_rom #(
    parameter integer DEPTH = 4096,
    parameter integer WIDTH = 24,
    parameter INIT_FILE = "",
    parameter integer ADDRW = $clog2(DEPTH)
) (
    input  wire [ADDRW-1:0] raddr1,
    output wire [WIDTH-1:0] rdata1,
    input  wire [ADDRW-1:0] raddr2,
    output wire [WIDTH-1:0] rdata2
);
endmodule
