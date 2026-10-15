// Testbench driver for the msh_chip_top evaluation (Verilator 5).
//
// Provides:
//  * command/response streams (issues one RUN command, waits for DONE)
//  * an external-memory model: 128-bit data, byte-address, 16-byte aligned,
//    at most one request accepted per cycle, reads answered IN ORDER after
//    a per-request latency of AT LEAST --lat-base cycles (default
//    MEM_LATENCY_MIN; the elasticity sweep raises it — designs must not
//    bake the base latency into their control), plus a deterministic
//    pseudo-random jitter of up to --lat-jitter cycles; writes are posted
//  * pseudo-random back-pressure: mem_req_ready deasserts with probability
//    --stall-permille/1000 on any cycle (0 = always ready). The jitter and
//    stall streams are seeded by --timing-seed, so runs are reproducible.
//    Latency jitter does NOT reduce sustained bandwidth (delivery stays
//    monotonic at up to one beat per cycle); ready stalls do, and are only
//    used on correctness (short) runs — see harness/evaluate.py.
//  * cycle counting and beat statistics
//
// This file is part of the frozen harness. Do not modify.

#include <verilated.h>
#include "Vmsh_chip_top.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <deque>
#include <fstream>
#include <string>
#include <vector>

static const uint32_t CMD_RUN = 0x00000001u;
static const uint32_t RSP_DONE = 0x0000D0DEu;
static const uint64_t MEM_LATENCY_MIN = 24;

struct Rsp {
    uint64_t ready_cycle;
    uint8_t data[16];
};

// deterministic PRNG (xorshift64*) for timing jitter / back-pressure
struct TRng {
    uint64_t s;
    explicit TRng(uint64_t seed) : s(seed ? seed : 0x9E3779B97F4A7C15ull) {}
    uint64_t next() {
        s ^= s >> 12;
        s ^= s << 25;
        s ^= s >> 27;
        return s * 0x2545F4914F6CDD1Dull;
    }
};

static std::string arg_str(int argc, char** argv, const char* key, const char* dflt) {
    size_t klen = strlen(key);
    for (int i = 1; i < argc; i++)
        if (!strncmp(argv[i], key, klen) && argv[i][klen] == '=')
            return std::string(argv[i] + klen + 1);
    return std::string(dflt);
}

static uint64_t arg_u64(int argc, char** argv, const char* key, uint64_t dflt) {
    std::string s = arg_str(argc, argv, key, "");
    return s.empty() ? dflt : strtoull(s.c_str(), nullptr, 0);
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    std::string image_path = arg_str(argc, argv, "--image", "");
    std::string result_path = arg_str(argc, argv, "--result", "");
    uint64_t out_base = arg_u64(argc, argv, "--out-base", 0);
    uint64_t out_len = arg_u64(argc, argv, "--out-len", 0);
    uint64_t timeout = arg_u64(argc, argv, "--timeout", 100000000ull);
    uint64_t progress = arg_u64(argc, argv, "--progress", 0);
    uint64_t lat_jitter = arg_u64(argc, argv, "--lat-jitter", 0);
    uint64_t lat_base = arg_u64(argc, argv, "--lat-base", MEM_LATENCY_MIN);
    uint64_t stall_pm = arg_u64(argc, argv, "--stall-permille", 0);
    uint64_t tseed = arg_u64(argc, argv, "--timing-seed", 1);

    std::vector<uint8_t> mem;
    {
        std::ifstream f(image_path, std::ios::binary);
        if (!f) { fprintf(stderr, "cannot open image %s\n", image_path.c_str()); return 2; }
        f.seekg(0, std::ios::end);
        size_t n = (size_t)f.tellg();
        f.seekg(0);
        mem.resize((n + 15) & ~size_t(15));
        f.read((char*)mem.data(), n);
    }

    auto* top = new Vmsh_chip_top;
    TRng rng(tseed);

    uint64_t cyc = 0, cyc_start = 0, cyc_end = 0;
    uint64_t read_beats = 0, write_beats = 0, addr_errors = 0;
    uint64_t stall_cycles = 0, last_rdy_cycle = 0;
    bool cmd_sent = false, done = false, timed_out = false;
    uint32_t last_rsp = 0;
    std::deque<Rsp> rq;

    // reset
    top->clk = 0; top->rst_n = 0;
    top->cmd_valid = 0; top->cmd_data = 0; top->rsp_ready = 0;
    top->mem_req_ready = 0; top->mem_rsp_valid = 0;
    for (int i = 0; i < 16; i++) { top->clk = 1; top->eval(); top->clk = 0; top->eval(); }
    top->rst_n = 1;

    while (!done && cyc < timeout) {
        // ---- drive inputs for this cycle ----
        top->cmd_valid = !cmd_sent;
        top->cmd_data = CMD_RUN;
        top->rsp_ready = 1;
        bool rdy = true;
        if (stall_pm) {
            rdy = (rng.next() % 1000) >= stall_pm;
            if (!rdy) stall_cycles++;
        }
        top->mem_req_ready = rdy;
        bool rsp_avail = !rq.empty() && rq.front().ready_cycle <= cyc;
        top->mem_rsp_valid = rsp_avail;
        if (rsp_avail)
            memcpy(&top->mem_rsp_rdata, rq.front().data, 16);
        else
            memset(&top->mem_rsp_rdata, 0, 16);

        // ---- settle combinational logic, sample pre-edge handshakes ----
        top->clk = 0;
        top->eval();
        bool h_cmd = top->cmd_valid && top->cmd_ready;
        bool h_rsp = top->rsp_valid && top->rsp_ready;
        uint32_t rsp_word = top->rsp_data;
        bool h_req = top->mem_req_valid && top->mem_req_ready;
        bool req_write = top->mem_req_write;
        uint64_t req_addr = (uint64_t)top->mem_req_addr;
        uint16_t req_strb = top->mem_req_wstrb;
        uint8_t req_data[16];
        memcpy(req_data, &top->mem_req_wdata, 16);
        bool h_mrsp = rsp_avail && top->mem_rsp_ready;

        // ---- clock edge ----
        top->clk = 1;
        top->eval();

        // ---- update models from sampled handshakes ----
        if (h_cmd) { cmd_sent = true; cyc_start = cyc; }
        if (h_rsp) {
            last_rsp = rsp_word;
            if (rsp_word == RSP_DONE) { done = true; cyc_end = cyc; }
        }
        if (h_mrsp) rq.pop_front();
        if (h_req) {
            uint64_t lat = lat_base
                + (lat_jitter ? (rng.next() % (lat_jitter + 1)) : 0);
            uint64_t rc = cyc + lat;
            if (rc <= last_rdy_cycle) rc = last_rdy_cycle + 1;  // in order
            if ((req_addr & 15) != 0 || req_addr + 16 > mem.size()) {
                addr_errors++;
                if (!req_write) {
                    Rsp r{}; r.ready_cycle = rc;
                    memset(r.data, 0, 16);
                    rq.push_back(r);
                    last_rdy_cycle = rc;
                    read_beats++;
                } else write_beats++;
            } else if (req_write) {
                for (int b = 0; b < 16; b++)
                    if (req_strb & (1u << b)) mem[req_addr + b] = req_data[b];
                write_beats++;
            } else {
                Rsp r{}; r.ready_cycle = rc;
                memcpy(r.data, &mem[req_addr], 16);
                rq.push_back(r);
                last_rdy_cycle = rc;
                read_beats++;
            }
        }
        cyc++;
        if (progress && cyc % progress == 0)
            fprintf(stderr, "[tb] cycle %llu reads=%llu writes=%llu\n",
                    (unsigned long long)cyc, (unsigned long long)read_beats,
                    (unsigned long long)write_beats);
    }
    if (!done) { timed_out = true; cyc_end = cyc; }

    if (!result_path.empty() && out_len > 0 && out_base + out_len <= mem.size()) {
        std::ofstream f(result_path, std::ios::binary);
        f.write((const char*)&mem[out_base], out_len);
    }

    printf("RESULT {\"cycles\": %llu, \"cyc_start\": %llu, \"read_beats\": %llu, "
           "\"write_beats\": %llu, \"timeout\": %s, \"addr_errors\": %llu, "
           "\"last_rsp\": %u, \"stall_cycles\": %llu, \"lat_base\": %llu, "
           "\"lat_jitter\": %llu, "
           "\"stall_permille\": %llu, \"timing_seed\": %llu}\n",
           (unsigned long long)(cyc_end - cyc_start),
           (unsigned long long)cyc_start,
           (unsigned long long)read_beats, (unsigned long long)write_beats,
           timed_out ? "true" : "false",
           (unsigned long long)addr_errors, last_rsp,
           (unsigned long long)stall_cycles, (unsigned long long)lat_base,
           (unsigned long long)lat_jitter,
           (unsigned long long)stall_pm, (unsigned long long)tseed);

    top->final();
    delete top;
    return timed_out ? 3 : 0;
}
