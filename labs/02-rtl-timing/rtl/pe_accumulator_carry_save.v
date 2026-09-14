// Redundant Carry-Save PE Accumulator
// Keeps sum and carry vectors separated; eliminates carry-propagation chain from the feedback loop.
module pe_accumulator_carry_save (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] data_in,
    output wire [31:0] acc_out
);

    reg [31:0] sum_reg;
    reg [31:0] carry_reg;

    wire [31:0] s;
    wire [31:0] c;

    // Bitwise Full Adder across (sum_reg, carry_reg, data_in)
    assign s = sum_reg ^ carry_reg ^ data_in;
    assign c = (sum_reg & carry_reg) | (carry_reg & data_in) | (sum_reg & data_in);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sum_reg   <= 32'd0;
            carry_reg <= 32'd0;
        end else if (valid_in) begin
            sum_reg   <= s;
            carry_reg <= {c[30:0], 1'b0}; // Shift carry left by 1 for next accumulation
        end
    end

    // Final resolution adder (evaluated on readout)
    assign acc_out = sum_reg + carry_reg;

endmodule
