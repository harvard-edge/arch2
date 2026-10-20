// Complete teaching-core execution engine. Program/weights/tables are external;
// every arithmetic operation and data-dependent decision executes on this RTL.
// The compiler supplies shape-derived instructions, never activation answers.
module nanochip_teaching_core #(
    parameter integer MUL_BITS = 1,
    parameter integer SCRATCH_WORDS = 1024
) (
    input wire clk, input wire rst_n,
    input wire [31:0] cmd_data, input wire cmd_valid, output wire cmd_ready,
    output wire [31:0] rsp_data, output wire rsp_valid, input wire rsp_ready,
    output reg mem_req_valid, input wire mem_req_ready, output reg mem_req_write,
    output reg [35:0] mem_req_addr, output reg [127:0] mem_req_wdata,
    output reg [15:0] mem_req_wstrb,
    input wire mem_rsp_valid, output wire mem_rsp_ready, input wire [127:0] mem_rsp_rdata
);
    localparam IDLE=0, FETCH_REQ=1, FETCH_WAIT=2, EXEC=3,
        LOAD_REQ=4, LOAD_WAIT=5, STORE_REQ=6, MULTIPLY=7,
        SCRATCH_READ=8, SCRATCH_WAIT=9, DONE=10, ERROR=11;
    localparam SAW=$clog2(SCRATCH_WORDS);
    localparam signed [127:0] SCRATCH_LIMIT=SCRATCH_WORDS;
    localparam [7:0] MUL_STEP=MUL_BITS;
    reg [3:0] state;
    reg signed [127:0] registers [0:15];
    reg [31:0] pc;
    reg [127:0] instruction;
    wire [7:0] opcode=instruction[7:0];
    wire [3:0] rd=instruction[11:8], ra=instruction[15:12], rb=instruction[19:16];
    wire [3:0] flags=instruction[23:20];
    wire signed [127:0] immediate={{64{instruction[95]}},instruction[95:32]};
    wire signed [127:0] lhs=registers[ra], rhs=registers[rb];
    wire signed [127:0] effective=lhs+immediate;
    reg [35:0] data_address;
    reg [31:0] store_value;
    reg [3:0] destination, load_flags;
    wire [127:0] shifted_data=mem_rsp_rdata >> {data_address[3:0],3'b0};
    reg [127:0] mul_x,mul_y,mul_acc;
    reg [7:0] mul_remaining;
    wire [127:0] mul_add0=mul_y[0] ? mul_x : 128'd0;
    wire [127:0] mul_add1=(MUL_BITS==2 && mul_y[1]) ? (mul_x << 1) : 128'd0;
    wire [127:0] mul_sum=mul_acc+mul_add0+mul_add1;
    reg [SAW-1:0] scratch_address;
    wire [31:0] scratch_read_data;
    wire scratch_valid=effective>=0 && effective<SCRATCH_LIMIT;
    wire scratch_we=state==EXEC && opcode==15 && scratch_valid;

    nanochip_teaching_scratch #(.DEPTH(SCRATCH_WORDS)) scratch(
        .clk(clk), .we(scratch_we), .waddr(effective[SAW-1:0]),
        .wdata(rhs[31:0]), .re(state==SCRATCH_READ),
        .raddr(scratch_address), .rdata(scratch_read_data));

    assign cmd_ready=state==IDLE;
    assign rsp_valid=state==DONE || state==ERROR;
    assign rsp_data=state==DONE ? 32'h0000d0de : 32'hdead0001;
    assign mem_rsp_ready=state==FETCH_WAIT || state==LOAD_WAIT;

    always @* begin
        mem_req_valid=0; mem_req_write=0; mem_req_addr=0;
        mem_req_wdata=0; mem_req_wstrb=0;
        case(state)
            FETCH_REQ: begin
                mem_req_valid=1; mem_req_addr={pc,4'b0};
            end
            LOAD_REQ: begin
                mem_req_valid=1; mem_req_addr={data_address[35:4],4'b0};
            end
            STORE_REQ: begin
                mem_req_valid=1; mem_req_write=1;
                mem_req_addr={data_address[35:4],4'b0};
                mem_req_wdata={96'd0,store_value} << {data_address[3:0],3'b0};
                mem_req_wstrb=16'h000f << data_address[3:0];
            end
            default: begin end
        endcase
    end

    integer i;
    always @(posedge clk) begin
        if(!rst_n) begin
            state<=IDLE; pc<=0; instruction<=0; data_address<=0;
            store_value<=0; destination<=0; load_flags<=0;
            mul_x<=0; mul_y<=0; mul_acc<=0; mul_remaining<=0;
            scratch_address<=0;
            for(i=0;i<16;i=i+1) registers[i]<=0;
        end else begin
            case(state)
                IDLE: if(cmd_valid) begin
                    if(cmd_data==32'd1) begin pc<=0; state<=FETCH_REQ; end
                    else state<=ERROR;
                end
                FETCH_REQ: if(mem_req_ready) state<=FETCH_WAIT;
                FETCH_WAIT: if(mem_rsp_valid) begin instruction<=mem_rsp_rdata; state<=EXEC; end
                EXEC: begin
                    pc<=pc+1; state<=FETCH_REQ;
                    if(instruction[127:96]!=0 || instruction[31:24]!=0) state<=ERROR;
                    else case(opcode)
                        0: state<=DONE;
                        1: registers[rd]<=immediate;
                        2: registers[rd]<=lhs+rhs;
                        3: registers[rd]<=lhs-rhs;
                        4: begin
                            mul_x<=lhs; mul_y<=rhs; mul_acc<=0;
                            mul_remaining<=128; destination<=rd; state<=MULTIPLY;
                        end
                        5: registers[rd]<=lhs >>> rhs[6:0];
                        6: registers[rd]<=lhs << rhs[6:0];
                        7: registers[rd]<=lhs & rhs;
                        8: registers[rd]<=lhs | rhs;
                        9: registers[rd]<=lhs ^ rhs;
                        10: registers[rd]<={127'd0,lhs<rhs};
                        11: registers[rd]<={127'd0,lhs==rhs};
                        12: if(lhs==0) begin
                            if(immediate<0 || immediate>128'hffffffff) state<=ERROR;
                            else pc<=immediate[31:0];
                        end
                        13: begin
                            if(immediate<0 || immediate>128'hffffffff) state<=ERROR;
                            else pc<=immediate[31:0];
                        end
                        14: begin
                            if(!scratch_valid) state<=ERROR;
                            else begin
                                scratch_address<=effective[SAW-1:0]; destination<=rd;
                                state<=SCRATCH_READ;
                            end
                        end
                        15: if(!scratch_valid) state<=ERROR;
                        16: begin
                            if(effective<0 || effective>=128'h1000000000 ||
                               ({1'b0,effective[3:0]}+(5'd1 << flags[1:0]))>16) state<=ERROR;
                            else begin
                                data_address<=effective[35:0]; destination<=rd;
                                load_flags<=flags; state<=LOAD_REQ;
                            end
                        end
                        17: begin
                            if(effective<0 || effective>=128'h1000000000 || effective[1:0]!=0) state<=ERROR;
                            else begin data_address<=effective[35:0]; store_value<=rhs[31:0]; state<=STORE_REQ; end
                        end
                        18: begin
                            if(lhs>128'sd2147483647) registers[rd]<=128'sd2147483647;
                            else if(lhs< -128'sd2147483648) registers[rd]<= -128'sd2147483648;
                            else registers[rd]<=lhs;
                        end
                        default: state<=ERROR;
                    endcase
                end
                LOAD_REQ: if(mem_req_ready) state<=LOAD_WAIT;
                LOAD_WAIT: if(mem_rsp_valid) begin
                    case(load_flags[1:0])
                        0: registers[destination]<=load_flags[2] ? {{120{shifted_data[7]}},shifted_data[7:0]} : {120'd0,shifted_data[7:0]};
                        1: registers[destination]<=load_flags[2] ? {{112{shifted_data[15]}},shifted_data[15:0]} : {112'd0,shifted_data[15:0]};
                        2: registers[destination]<=load_flags[2] ? {{96{shifted_data[31]}},shifted_data[31:0]} : {96'd0,shifted_data[31:0]};
                        3: registers[destination]<=load_flags[2] ? {{64{shifted_data[63]}},shifted_data[63:0]} : {64'd0,shifted_data[63:0]};
                    endcase
                    state<=FETCH_REQ;
                end
                STORE_REQ: if(mem_req_ready) state<=FETCH_REQ;
                MULTIPLY: begin
                    mul_acc<=mul_sum; mul_x<=mul_x << MUL_BITS; mul_y<=mul_y >> MUL_BITS;
                    mul_remaining<=mul_remaining-MUL_STEP;
                    if(mul_remaining<=MUL_STEP) begin registers[destination]<=mul_sum; state<=FETCH_REQ; end
                end
                SCRATCH_READ: state<=SCRATCH_WAIT;
                SCRATCH_WAIT: begin registers[destination]<={{96{scratch_read_data[31]}},scratch_read_data}; state<=FETCH_REQ; end
                DONE: if(rsp_ready) state<=IDLE;
                ERROR: if(rsp_ready) state<=IDLE;
                default: state<=ERROR;
            endcase
        end
    end
endmodule

// This initial implementation maps into real standard cells. A characterized
// macro wrapper may replace it while preserving this synchronous interface.
module nanochip_teaching_scratch #(
    parameter integer DEPTH=1024, parameter integer AW=$clog2(DEPTH)
) (
    input wire clk, input wire we, input wire [AW-1:0] waddr,
    input wire [31:0] wdata, input wire re, input wire [AW-1:0] raddr,
    output reg [31:0] rdata
);
    reg [31:0] words [0:DEPTH-1];
    always @(posedge clk) begin
        if(we) words[waddr]<=wdata;
        if(re) rdata<=words[raddr];
    end
endmodule
