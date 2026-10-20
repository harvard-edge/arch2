// Constructed block-level stimulus. No workload or physical implementation claim.
#include "Vmsh_deq.h"
#include "verilated.h"
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

struct Row {
    unsigned d, group, buffer, schedule;
    std::vector<int> scales;
    std::vector<unsigned> zeros, q;
    std::vector<uint32_t> expected;
};

class Probe {
    Vmsh_deq dut;
    const Row* row = nullptr;
    unsigned words = 0, row_done = 0;
public:
    uint64_t cycles = 0, stalled = 0, bubbles = 0, lanes = 0, mismatches = 0;
    unsigned completed = 0;

    Probe() {
        dut.clk = 0; dut.rst_n = 0; dut.job_valid = 0; dut.ws_valid = 0;
        dut.ws_count = 0; dut.ws_shift = 0; dut.ws_last = 0;
        for (int i = 0; i < 4; ++i) tick();
        dut.rst_n = 1;
        tick();
    }

    void tick() {
        dut.clk = 0;
        dut.eval();
        if (row) {
            if (dut.ws_valid && !dut.ws_ready) ++stalled;
            if (dut.y_we) {
                if (words >= row->d / 4 || dut.y_addr != words || dut.y_buf != row->buffer)
                    throw std::runtime_error("unexpected write count, address, or buffer");
                for (unsigned lane = 0; lane < 4; ++lane) {
                    uint32_t observed = dut.y_data[lane];
                    uint32_t expected = row->expected[4 * words + lane];
                    ++lanes;
                    if (observed != expected) {
                        if (mismatches < 12)
                            std::cout << "mismatch row=" << completed << " lane="
                                      << 4 * words + lane << " expected=" << expected
                                      << " observed=" << observed << '\n';
                        ++mismatches;
                    }
                }
                ++words;
            }
            if (dut.done) {
                if (!dut.y_we || words != row->d / 4 || row_done)
                    throw std::runtime_error("done without exactly the final write");
                ++row_done;
            }
        }
        dut.clk = 1; dut.eval();
        dut.clk = 0; dut.eval();
        ++cycles;
    }

    void segment(const std::vector<unsigned>& bytes, unsigned schedule) {
        size_t pos = 0;
        unsigned beat = 0;
        while (pos < bytes.size()) {
            // Pause the producer only before presenting a new beat; hold every
            // presented beat unchanged until valid && ready is sampled.
            dut.ws_valid = 0;
            if (schedule) {
                unsigned gap = (beat + schedule) % 3;
                for (unsigned i = 0; i < gap; ++i) { ++bubbles; tick(); }
            }
            static const unsigned shifts[] = {0, 3, 15, 1};
            static const unsigned sizes[] = {16, 7, 1, 3};
            unsigned shift = schedule ? shifts[(beat + schedule) % 4] : 0;
            unsigned count = std::min<unsigned>(bytes.size() - pos,
                std::min(16 - shift, schedule ? sizes[beat % 4] : 16));
            for (unsigned i = 0; i < 4; ++i) dut.ws_data[i] = 0xa5a5a5a5;
            for (unsigned i = 0; i < count; ++i) {
                unsigned offset = shift + i, word = offset / 4, bits = 8 * (offset % 4);
                dut.ws_data[word] = (dut.ws_data[word] & ~(0xffu << bits))
                                   | ((bytes[pos + i] & 0xffu) << bits);
            }
            dut.ws_count = count; dut.ws_shift = shift;
            dut.ws_last = pos + count == bytes.size(); dut.ws_valid = 1;
            unsigned waited = 0;
            while (true) {
                dut.eval();
                bool accepted = dut.ws_ready;
                tick();
                if (accepted) break;
                if (++waited > 4096) throw std::runtime_error("stream handshake timeout");
            }
            dut.ws_valid = 0;
            pos += count; ++beat;
        }
    }

    void run(const Row& r) {
        dut.eval();
        if (!dut.job_ready) throw std::runtime_error("job not ready between rows");
        row = &r; words = 0; row_done = 0;
        dut.job_d = r.d; dut.job_gsz = r.group; dut.job_ybuf = r.buffer;
        dut.job_valid = 1; tick(); dut.job_valid = 0;
        std::vector<unsigned> scales, packed;
        for (int s : r.scales) {
            uint16_t bits = static_cast<uint16_t>(s);
            scales.push_back(bits & 0xffu); scales.push_back(bits >> 8);
        }
        for (unsigned i = 0; i < r.d; i += 2)
            packed.push_back(r.q[i] | (r.q[i + 1] << 4));
        segment(scales, r.schedule);
        segment(r.zeros, r.schedule);
        segment(packed, r.schedule);
        for (unsigned i = 0; !row_done; ++i) {
            if (i > 4096) throw std::runtime_error("output completion timeout");
            tick();
        }
        // Observe idle cycles too, to catch extra writes or repeated done.
        tick(); tick();
        if (!dut.job_ready) throw std::runtime_error("not idle after completion");
        row = nullptr; ++completed;
    }
};

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Probe p;
    std::string error;
    unsigned count = 0;
    try {
        if (argc != 2) throw std::runtime_error("expected vectors file");
        std::ifstream in(argv[1]);
        if (!(in >> count) || !count || count > 1000) throw std::runtime_error("bad vector header");
        for (unsigned i = 0; i < count; ++i) {
            Row r;
            if (!(in >> r.d >> r.group >> r.buffer >> r.schedule) || !r.d || r.d > 256
                || r.d % 4 || !r.group || r.group > 128 || r.d % r.group
                || r.d / r.group > 2 || r.buffer > 15)
                throw std::runtime_error("bad row header");
            unsigned ng = r.d / r.group;
            r.scales.resize(ng); r.zeros.resize(ng); r.q.resize(r.d); r.expected.resize(r.d);
            for (auto& v : r.scales) in >> v;
            for (auto& v : r.zeros) in >> v;
            for (auto& v : r.q) in >> v;
            for (auto& v : r.expected) in >> v;
            if (!in) throw std::runtime_error("truncated vectors");
            p.run(r);
        }
    } catch (const std::exception& e) { error = e.what(); }
    bool ok = error.empty() && p.completed == count && p.mismatches == 0;
    std::cout << "PROBE_JSON {\"ok\":" << (ok ? "true" : "false")
              << ",\"rows_completed\":" << p.completed << ",\"lanes_checked\":" << p.lanes
              << ",\"mismatches\":" << p.mismatches << ",\"cycles\":" << p.cycles
              << ",\"stream_stall_cycles\":" << p.stalled
              << ",\"producer_bubble_cycles\":" << p.bubbles
              << ",\"protocol_error\":\"" << error << "\"}\n";
    return ok ? 0 : 1;
}
