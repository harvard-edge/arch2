#include "Vnanochip_teaching_core.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

static std::vector<uint8_t> read_file(const char* path) {
    std::ifstream input(path, std::ios::binary);
    if(!input) throw std::runtime_error(std::string("Cannot read ")+path);
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(input), {});
}
struct Pending { uint64_t due; std::array<uint32_t,4> data; };

int main(int argc,char** argv) {
    Verilated::commandArgs(argc,argv);
    if(argc!=10) { std::cerr<<"program image tables dump max_cycles latency stall_permille reset_seed jitter\n"; return 2; }
    try {
        const uint64_t data_base=uint64_t(1)<<20, table_base=uint64_t(1)<<22;
        auto program=read_file(argv[1]), image=read_file(argv[2]), tables=read_file(argv[3]);
        if(program.size()>data_base || image.size()>table_base-data_base) throw std::runtime_error("Overlapping external regions");
        std::vector<uint8_t> memory(table_base+tables.size()+16,0);
        std::copy(program.begin(),program.end(),memory.begin());
        std::copy(image.begin(),image.end(),memory.begin()+data_base);
        std::copy(tables.begin(),tables.end(),memory.begin()+table_base);
        uint64_t max_cycles=std::stoull(argv[5]), latency=std::stoull(argv[6]);
        uint32_t stall=std::stoul(argv[7]), reset_seed=std::stoul(argv[8]), jitter=std::stoul(argv[9]);
        if(stall>1000 || latency<1) throw std::runtime_error("Invalid memory profile");
        Verilated::randReset(reset_seed?2:0); Verilated::randSeed(reset_seed?reset_seed:1);
        Vnanochip_teaching_core dut;
        std::deque<Pending> pending;
        uint64_t reads=0,writes=0,errors=0,start=0,completed_at=0;
        uint32_t rng=0x5a17d00d;
        auto random=[&]() { rng^=rng<<13; rng^=rng>>17; rng^=rng<<5; return rng; };
        bool started=false,completed=false,fault=false,held=false;
        uint64_t held_addr=0; uint32_t held_write=0,held_mask=0;
        std::array<uint32_t,4> held_data{};
        for(uint64_t cycle=0;cycle<max_cycles+16;cycle++) {
            dut.clk=0; dut.rst_n=cycle>=16; dut.cmd_data=1;
            dut.cmd_valid=cycle>=16 && !started; dut.rsp_ready=1;
            // Reset quiesces this external interface. Preserve the random
            // stream while ignoring uninitialized pre-reset DUT outputs.
            uint32_t ready_sample=random();
            dut.mem_req_ready=dut.rst_n && ready_sample%1000>=stall;
            bool available=!pending.empty() && pending.front().due<=cycle;
            dut.mem_rsp_valid=dut.rst_n && available;
            for(int w=0;w<4;w++) dut.mem_rsp_rdata[w]=available?pending.front().data[w]:0;
            dut.eval();
            if(held && dut.rst_n) {
                if(!dut.mem_req_valid || dut.mem_req_addr!=held_addr || dut.mem_req_write!=held_write || dut.mem_req_wstrb!=held_mask) errors++;
                for(int w=0;w<4;w++) if(dut.mem_req_wdata[w]!=held_data[w]) errors++;
            }
            held=dut.rst_n && dut.mem_req_valid && !dut.mem_req_ready;
            if(held) {
                held_addr=dut.mem_req_addr; held_write=dut.mem_req_write; held_mask=dut.mem_req_wstrb;
                for(int w=0;w<4;w++) held_data[w]=dut.mem_req_wdata[w];
            }
            bool request=dut.rst_n && dut.mem_req_valid && dut.mem_req_ready;
            bool response=dut.rst_n && dut.mem_rsp_valid && dut.mem_rsp_ready;
            bool command=dut.rst_n && dut.cmd_valid && dut.cmd_ready;
            bool done=dut.rst_n && dut.rsp_valid && dut.rsp_ready;
            uint32_t status=dut.rsp_data;
            uint64_t address=dut.mem_req_addr;
            bool write=dut.mem_req_write;
            uint16_t mask=dut.mem_req_wstrb;
            std::array<uint32_t,4> write_data{};
            for(int w=0;w<4;w++) write_data[w]=dut.mem_req_wdata[w];
            dut.clk=1; dut.eval(); dut.clk=0; dut.eval();
            if(command) { started=true; start=cycle; }
            if(response) pending.pop_front();
            if(request) {
                if((address&15) || address+16>memory.size()) { errors++; break; }
                if(write) {
                    writes++;
                    for(int b=0;b<16;b++) if((mask>>b)&1) memory[address+b]=(write_data[b/4]>>(8*(b%4)))&255;
                } else {
                    reads++; Pending reply{};
                    reply.due=cycle+latency+(jitter?random()%(jitter+1):0);
                    if(!pending.empty() && reply.due<pending.back().due) reply.due=pending.back().due;
                    for(int b=0;b<16;b++) reply.data[b/4]|=uint32_t(memory[address+b])<<(8*(b%4));
                    pending.push_back(reply);
                }
            }
            if(done) { completed=status==0x0000d0de; fault=!completed; completed_at=cycle; break; }
            completed_at=cycle;
        }
        std::ofstream output(argv[4],std::ios::binary);
        output.write(reinterpret_cast<const char*>(memory.data()+data_base),image.size());
        if(!output) throw std::runtime_error("Cannot write result image");
        std::string status=completed?(errors?"protocol_error":"completed"):(fault?"fault":"timeout");
        std::cout<<"NANOCHIP_CORE_RESULT {\"status\":\""<<status<<"\",\"cycles\":"<<(started?completed_at-start:0)
            <<",\"read_beats\":"<<reads<<",\"write_beats\":"<<writes<<",\"protocol_errors\":"<<errors
            <<",\"latency\":"<<latency<<",\"stall_permille\":"<<stall<<",\"reset_seed\":"<<reset_seed<<"}\n";
        return completed && !errors?0:1;
    } catch(const std::exception& error) { std::cerr<<error.what()<<"\n"; return 2; }
}
