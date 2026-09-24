module systolic_array #(
    parameter ROWS = 4,
    parameter COLS = 4,
    parameter DATA_WIDTH = 16
)(
    input clk,
    input rst,
    input load_weight,

    // Inputs at the West edge (Activations)
    input [ROWS*DATA_WIDTH-1:0] in_a,

    // Inputs at the North edge (Partial Sums)
    input [COLS*DATA_WIDTH-1:0] in_p,

    // Outputs at the East edge (Activations passing through - mostly for debug)
    output [ROWS*DATA_WIDTH-1:0] out_a,

    // Outputs at the South edge (Final accumulated results)
    output [COLS*DATA_WIDTH-1:0] out_p
);

    // Internal wires connecting the MACs
    wire [DATA_WIDTH-1:0] w_a [0:ROWS-1][0:COLS]; // Activations (West to East)
    wire [DATA_WIDTH-1:0] w_p [0:ROWS][0:COLS-1]; // Partial sums (North to South)

    // Map top-level inputs to the edges of the internal wire mesh
    genvar r, c;
    generate
        // Connect West edge
        for (r = 0; r < ROWS; r = r + 1) begin : west_edge
            assign w_a[r][0] = in_a[(r*DATA_WIDTH) +: DATA_WIDTH];
            assign out_a[(r*DATA_WIDTH) +: DATA_WIDTH] = w_a[r][COLS];
        end

        // Connect North edge
        for (c = 0; c < COLS; c = c + 1) begin : north_edge
            assign w_p[0][c] = in_p[(c*DATA_WIDTH) +: DATA_WIDTH];
            assign out_p[(c*DATA_WIDTH) +: DATA_WIDTH] = w_p[ROWS][c];
        end

        // Instantiate the grid of MAC units
        for (r = 0; r < ROWS; r = r + 1) begin : row
            for (c = 0; c < COLS; c = c + 1) begin : col
                mac #(
                    .DATA_WIDTH(DATA_WIDTH)
                ) pe (
                    .clk(clk),
                    .rst(rst),
                    .load_weight(load_weight),
                    .in_a(w_a[r][c]),     // Activation from West
                    .in_p(w_p[r][c]),     // Partial sum from North
                    .out_a(w_a[r][c+1]),  // Activation to East
                    .out_p(w_p[r+1][c])   // Partial sum to South
                );
            end
        end
    endgenerate

endmodule
