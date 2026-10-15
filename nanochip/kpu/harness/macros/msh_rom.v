// msh_rom -- harness-provided READ-ONLY memory macro for constant lookup
// tables (sigmoid/gate/exp activations). Companion to msh_sram: msh_sram is
// for WRITABLE storage; msh_rom is for CONSTANT tables that cannot be a
// writable SRAM. Instantiated by the design; injected by the harness (do NOT
// redefine or list this file in rtl/filelist.f).
//
// Why this exists: the macros_only rule bans inferred $mem, and a constant
// LUT is not a writable SRAM, so without a ROM macro the only option was to
// expand the table into combinational mux logic -- which bloats the design
// (~50k lines / hundreds of thousands of gates) and gives the table index a
// fanout of thousands (a timing disaster). msh_rom keeps the table as ONE
// compact macro: the index drives a single block (fanout ~1), like the
// original $readmemh-loaded `reg [W-1:0] tab [0:D-1]` array it replaces.
//
// Interface: TWO asynchronous read ports (rdata = mem[raddr] combinationally)
// so one lookup can fetch tab[idx] and tab[idx+1] for linear interpolation in
// the same cycle -- matching how the LUT is read (one element per cycle).
// Contents are loaded at time 0 with $readmemh from a file under rtl/roms/
// (the only place the audit allows $readmem). WIDTH must be a multiple of 8.
//
// Priced like msh_sram: DEPTH*WIDTH bits count toward the SRAM-capacity and
// area budgets at ~1 Mbit/mm^2.

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

    // The macro's internal storage IS an inferred memory, but -- exactly like
    // msh_sram -- it lives inside a harness-injected macro, so the macros_only
    // gate does not count it as design $mem_v2.
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    initial begin
        if (INIT_FILE != "")
            $readmemh(INIT_FILE, mem);
    end

    assign rdata1 = mem[raddr1];
    assign rdata2 = mem[raddr2];

endmodule
