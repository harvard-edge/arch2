
module top(
    input clk,
    input rst,
    input load_weight,
    input [256-1:0] in_a,
    input [16-1:0] in_p,
    output [256-1:0] out_a,
    output [16-1:0] out_p
);
    systolic_array #(
        .ROWS(16),
        .COLS(1),
        .DATA_WIDTH(16)
    ) dut (
        .clk(clk),
        .rst(rst),
        .load_weight(load_weight),
        .in_a(in_a),
        .in_p(in_p),
        .out_a(out_a),
        .out_p(out_p)
    );
endmodule
