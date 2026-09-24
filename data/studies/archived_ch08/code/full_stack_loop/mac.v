module mac #(
    parameter DATA_WIDTH = 16
)(
    input clk,
    input rst,
    input load_weight,

    input signed [DATA_WIDTH-1:0] in_a, // Activation from West
    input signed [DATA_WIDTH-1:0] in_p, // Partial sum from North

    output reg signed [DATA_WIDTH-1:0] out_a, // Activation to East
    output reg signed [DATA_WIDTH-1:0] out_p  // Partial sum to South
);

    reg signed [DATA_WIDTH-1:0] weight;

    always @(posedge clk) begin
        if (rst) begin
            weight <= 0;
            out_a <= 0;
            out_p <= 0;
        end else if (load_weight) begin
            // When loading weight, we can pass weights in through in_a or in_p
            // For simplicity, let's load weight from in_p during a special setup phase
            weight <= in_p;
            out_a <= 0;
            out_p <= 0;
        end else begin
            // Normal execution
            out_a <= in_a;
            out_p <= in_p + (in_a * weight);
        end
    end

endmodule
