// 2-Stage Pipelined PE Accumulator
// Breaks 32-bit addition into two 16-bit cycles.
module pe_accumulator_retimed (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] data_in,
    output wire [31:0] acc_out
);

    reg [15:0] low_acc;
    reg [15:0] high_acc;
    reg        carry_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            low_acc   <= 16'd0;
            high_acc  <= 16'd0;
            carry_reg <= 1'b0;
        end else if (valid_in) begin
            {carry_reg, low_acc} <= low_acc + data_in[15:0];
            high_acc             <= high_acc + data_in[31:16] + carry_reg;
        end
    end

    assign acc_out = {high_acc, low_acc};

endmodule
