import os
import subprocess
import json
import re
import math


def get_workload_shape():
    return {"M": 16, "K": 16, "N": 16}


def synthesize_array(R, C, data_width=16):
    print(f"  Synthesizing {R}x{C} Systolic Array...")

    top_v = f"""
module top(
    input clk,
    input rst,
    input load_weight,
    input [{R*data_width}-1:0] in_a,
    input [{C*data_width}-1:0] in_p,
    output [{R*data_width}-1:0] out_a,
    output [{C*data_width}-1:0] out_p
);
    systolic_array #(
        .ROWS({R}),
        .COLS({C}),
        .DATA_WIDTH({data_width})
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
"""
    with open("top.v", "w") as f:
        f.write(top_v)

    yosys_script = f"""
read_verilog mac.v
read_verilog systolic_array.v
read_verilog top.v
hierarchy -top top
synth -top top -flatten
opt_clean -purge
stat
"""

    with open("synth.ys", "w") as f:
        f.write(yosys_script)

    result = subprocess.run(["yosys", "synth.ys"], capture_output=True, text=True)

    gate_count = 0
    dff_count = 0
    for line in result.stdout.split("\n"):
        if "cells" in line and "Number of cells" not in line:
            # Matches lines like "    13476 cells"
            match = re.search(r"(\d+)\s+cells", line)
            if match:
                gate_count = int(match.group(1))
        elif "$_DFF" in line:
            parts = line.split()
            dff_count += int(parts[-1])

    return {"gate_count": gate_count, "dff_count": dff_count}


def simulate_latency(workload, R, C):
    M, K, N = workload["M"], workload["K"], workload["N"]
    tiles_m = math.ceil(M / R)
    tiles_n = math.ceil(N / C)

    total_cycles = 0
    for tm in range(tiles_m):
        for tn in range(tiles_n):
            load_cycles = R
            compute_cycles = K + R + C - 1
            total_cycles += load_cycles + compute_cycles

    return total_cycles


def main():
    workload = get_workload_shape()
    print(
        f"Workload: {workload['M']}x{workload['K']} * {workload['K']}x{workload['N']} Matrix Multiplication"
    )
    print("-" * 80)
    print(
        f"{'Array':<10} | {'Latency (Cycles)':<18} | {'Gate Count (Yosys)':<20} | {'Score (Lat * Area)':<20}"
    )
    print("-" * 80)

    candidates = [(1, 16), (2, 8), (4, 4), (8, 2), (16, 1)]
    results = []

    for R, C in candidates:
        cycles = simulate_latency(workload, R, C)
        physical_stats = synthesize_array(R, C)
        gates = physical_stats["gate_count"]

        score = cycles * gates
        results.append(
            {"R": R, "C": C, "cycles": cycles, "gates": gates, "score": score}
        )
        print(f"{str(R)+'x'+str(C):<10} | {cycles:<18} | {gates:<20} | {score:<20}")
        print("-" * 80)

    best = min(results, key=lambda x: x["score"])
    print(
        f"\nOptimal Topology (Min Area-Delay Product): {best['R']}x{best['C']} array with score {best['score']}"
    )


if __name__ == "__main__":
    main()
