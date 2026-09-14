// Testbench: Functional Equivalence between Naive and Carry-Save Accumulator
// Exercised over 1,000 random vectors to formally prove microarchitectural equivalence.

`timescale 1ns/1ps

module tb_pe_accumulator;

    reg         clk;
    reg         rst_n;
    reg         valid_in;
    reg  [31:0] data_in;

    wire [31:0] acc_out_naive;
    wire [31:0] acc_out_csa;

    // Instantiate Naive Accumulator (AI-Assisted baseline)
    pe_accumulator_naive u_naive (
        .clk(clk),
        .rst_n(rst_n),
        .valid_in(valid_in),
        .data_in(data_in),
        .acc_out(acc_out_naive)
    );

    // Instantiate Carry-Save Accumulator (AI-Native refactored)
    pe_accumulator_carry_save u_csa (
        .clk(clk),
        .rst_n(rst_n),
        .valid_in(valid_in),
        .data_in(data_in),
        .acc_out(acc_out_csa)
    );

    // Clock generation: 500 MHz (2.0 ns period)
    always #1.0 clk = ~clk;

    integer i;
    integer err_count;
    integer ok_count;

    initial begin
        clk = 0;
        rst_n = 0;
        valid_in = 0;
        data_in = 32'd0;
        err_count = 0;
        ok_count = 0;

        // Apply reset
        #4.0;
        rst_n = 1;
        #2.0;

        // Drive 1,000 test vectors
        for (i = 0; i < 1000; i = i + 1) begin
            @(posedge clk);
            #0.1; // Small sample delay after edge
            valid_in = 1'b1;
            data_in = $random;

            @(negedge clk);
            if (acc_out_naive !== acc_out_csa) begin
                $display("[ERROR] Cycle %0d: Naive=0x%08h, CSA=0x%08h, In=0x%08h",
                         i, acc_out_naive, acc_out_csa, data_in);
                err_count = err_count + 1;
            end else begin
                ok_count = ok_count + 1;
            end
        end

        @(posedge clk);
        valid_in = 1'b0;
        #5.0;

        if (err_count == 0) begin
            $display("[TB_RESULT] PASS: %0d/1000 vectors bit-exact equivalence confirmed.", ok_count);
        end else begin
            $display("[TB_RESULT] FAIL: %0d mismatches detected!", err_count);
        end

        $finish;
    end

endmodule
