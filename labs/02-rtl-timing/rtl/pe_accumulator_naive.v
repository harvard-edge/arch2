// Naive 32-bit PE Accumulator
// Single-cycle unpipelined addition in the register feedback loop.
module pe_accumulator_naive (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] data_in,
    output reg  [31:0] acc_out
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc_out <= 32'd0;
        end else if (valid_in) begin
            // 32-bit ripple carry chain in feedback loop
            acc_out <= acc_out + data_in;
        end
    end

endmodule
