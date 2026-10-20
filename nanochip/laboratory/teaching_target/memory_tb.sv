// Bounded interface exercise. Uses the frozen wrapper and injected SRAM model.
// This is behavioral simulation, not SRAM physical realization or equivalence.
module memory_tb;
    reg clk = 0;
    reg x_we;
    reg [13:0] x_wa, x_a, x_b;
    reg [127:0] x_wd;
    reg [3:0] x_mask;
    wire [127:0] x_ad, x_bd;
    msh_xbuf xbuf(.clk(clk), .a_addr(x_a), .a_rdata(x_ad),
        .b_addr(x_b), .b_rdata(x_bd), .w_we(x_we), .w_addr(x_wa),
        .w_wdata(x_wd), .w_wmask(x_mask));

    reg we = 0, re = 0;
    reg [1:0] wa = 0, ra = 0;
    reg [31:0] wd = 0;
    reg [3:0] strb = 0;
    wire [31:0] rd;
    // Constructed small fixture for the same generic SRAM contract.
    msh_sram #(.DEPTH(4), .WIDTH(32)) fixture(
        .clk(clk), .we(we), .waddr(wa), .wdata(wd), .wstrb(strb),
        .re(re), .raddr(ra), .rdata(rd));

    task tick;
        #1; clk = 1; #1; clk = 0; #1;
    endtask

    task expect_word(input [31:0] expected);
        if (rd !== expected) $fatal(1, "SRAM contract mismatch: actual=%h expected=%h", rd, expected);
    endtask

    integer fd, fields, compare_enable, cycles = 0, comparisons = 0;
    reg [127:0] expected_a, expected_b;
    initial begin
        // Avoid relying on simulation initialization of unwritten storage.
        x_we=0; x_wa=0; x_wd=0; x_mask=0; x_a=0; x_b=0;
        we=1; wa=0; wd=32'h11223344; strb=4'hf; re=0; tick();
        // Collision must return the old value, then expose the new value.
        re=1; ra=0; wd=32'haabbccdd; tick(); expect_word(32'h11223344);
        we=0; tick(); expect_word(32'haabbccdd);
        // Enable only the least-significant byte, while reading the old word.
        we=1; strb=4'h1; wd=32'h55667788; tick(); expect_word(32'haabbccdd);
        we=0; tick(); expect_word(32'haabbcc88);
        // Disabled read holds its output even when the stored word changes.
        re=0; we=1; strb=4'hf; wd=32'hdeadbeef; tick(); expect_word(32'haabbcc88);
        we=0; re=1; tick(); expect_word(32'hdeadbeef);
        // A zero mask changes no bytes.
        we=1; strb=0; wd=0; tick(); expect_word(32'hdeadbeef);
        we=0; tick(); expect_word(32'hdeadbeef);

        fd=$fopen("xbuf_vectors.hex", "r");
        if (fd == 0) $fatal(1, "Missing XBUF vectors");
        while (!$feof(fd)) begin
            fields=$fscanf(fd, "%h %h %h %h %h %h %h %h %h\n",
                x_we, x_wa, x_wd, x_mask, x_a, x_b,
                compare_enable, expected_a, expected_b);
            if (fields != 9) $fatal(1, "Malformed XBUF vector");
            tick(); cycles=cycles+1;
            if (compare_enable != 0) begin
                comparisons=comparisons+1;
                if (x_ad !== expected_a || x_bd !== expected_b)
                    $fatal(1, "XBUF mismatch at vector %0d: actual=%h/%h expected=%h/%h",
                        cycles, x_ad, x_bd, expected_a, expected_b);
            end
        end
        $fclose(fd);
        if (comparisons == 0) $fatal(1, "No checked XBUF vectors");
        $display("NANOCHIP_MEMORY_PASS cycles=%0d comparisons=%0d", cycles, comparisons);
        $finish;
    end
endmodule
