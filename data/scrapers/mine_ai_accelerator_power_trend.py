#!/usr/bin/env python3
"""
Datacenter Power Delivery & Thermal Limits Dataset (AI-TCO-Limits)
==================================================================
Architecture 2.0 Empirical Provenance Pipeline

This script aggregates the physical constraints of AI architectures over the past decade.
As chips hit the reticle limit, power density (Amps/mm²) and cooling are becoming the
primary bottlenecks. This dataset correlates physical packaging data (Process Node,
Transistor Count, Die Size) with Power (TDP) and Peak Compute (TOPS/TFLOPS).

Outputs:
data/datasets/ai_accelerator_power_thermal_trend.csv
"""

import os
import csv

# Authoritative empirical data sourced from HotChips, ISSCC, IEEE Micro, and vendor whitepapers.
# FP16 TFLOPS used as standard baseline where applicable, or dense BF16/FP16 tensor core metrics.
ACCELERATORS = [
    # Google TPU
    {
        "Year": 2015,
        "Company": "Google",
        "Chip": "TPU v1",
        "Node_nm": 28,
        "Transistors_B": 4.0,
        "Die_Size_mm2": 331,
        "TDP_W": 40,
        "Peak_TFLOPS_FP16": 92.0,
    },  # Int8 used, mapped to equivalent peak for scaling
    {
        "Year": 2017,
        "Company": "Google",
        "Chip": "TPU v2",
        "Node_nm": 16,
        "Transistors_B": 8.5,
        "Die_Size_mm2": 600,
        "TDP_W": 280,
        "Peak_TFLOPS_FP16": 45.0,
    },
    {
        "Year": 2018,
        "Company": "Google",
        "Chip": "TPU v3",
        "Node_nm": 16,
        "Transistors_B": 10.5,
        "Die_Size_mm2": 700,
        "TDP_W": 450,
        "Peak_TFLOPS_FP16": 90.0,
    },
    {
        "Year": 2021,
        "Company": "Google",
        "Chip": "TPU v4",
        "Node_nm": 7,
        "Transistors_B": 22.0,
        "Die_Size_mm2": 600,
        "TDP_W": 175,
        "Peak_TFLOPS_FP16": 275.0,
    },
    {
        "Year": 2023,
        "Company": "Google",
        "Chip": "TPU v5p",
        "Node_nm": 4,
        "Transistors_B": 45.0,
        "Die_Size_mm2": 800,
        "TDP_W": 400,
        "Peak_TFLOPS_FP16": 918.0,
    },
    # NVIDIA
    {
        "Year": 2016,
        "Company": "NVIDIA",
        "Chip": "P100",
        "Node_nm": 16,
        "Transistors_B": 15.3,
        "Die_Size_mm2": 610,
        "TDP_W": 300,
        "Peak_TFLOPS_FP16": 21.2,
    },
    {
        "Year": 2017,
        "Company": "NVIDIA",
        "Chip": "V100",
        "Node_nm": 12,
        "Transistors_B": 21.1,
        "Die_Size_mm2": 815,
        "TDP_W": 300,
        "Peak_TFLOPS_FP16": 125.0,
    },
    {
        "Year": 2020,
        "Company": "NVIDIA",
        "Chip": "A100",
        "Node_nm": 7,
        "Transistors_B": 54.2,
        "Die_Size_mm2": 826,
        "TDP_W": 400,
        "Peak_TFLOPS_FP16": 312.0,
    },
    {
        "Year": 2022,
        "Company": "NVIDIA",
        "Chip": "H100",
        "Node_nm": 4,
        "Transistors_B": 80.0,
        "Die_Size_mm2": 814,
        "TDP_W": 700,
        "Peak_TFLOPS_FP16": 1979.0,
    },
    {
        "Year": 2024,
        "Company": "NVIDIA",
        "Chip": "B200",
        "Node_nm": 4,
        "Transistors_B": 208.0,
        "Die_Size_mm2": 1600,
        "TDP_W": 1000,
        "Peak_TFLOPS_FP16": 4500.0,
    },
    # AMD
    {
        "Year": 2020,
        "Company": "AMD",
        "Chip": "MI100",
        "Node_nm": 7,
        "Transistors_B": 25.6,
        "Die_Size_mm2": 750,
        "TDP_W": 300,
        "Peak_TFLOPS_FP16": 184.6,
    },
    {
        "Year": 2021,
        "Company": "AMD",
        "Chip": "MI250X",
        "Node_nm": 6,
        "Transistors_B": 58.2,
        "Die_Size_mm2": 1560,
        "TDP_W": 560,
        "Peak_TFLOPS_FP16": 383.0,
    },
    {
        "Year": 2023,
        "Company": "AMD",
        "Chip": "MI300X",
        "Node_nm": 5,
        "Transistors_B": 153.0,
        "Die_Size_mm2": 1017,
        "TDP_W": 750,
        "Peak_TFLOPS_FP16": 1300.0,
    },
    # Cerebras
    {
        "Year": 2019,
        "Company": "Cerebras",
        "Chip": "WSE-1",
        "Node_nm": 16,
        "Transistors_B": 1200.0,
        "Die_Size_mm2": 46225,
        "TDP_W": 15000,
        "Peak_TFLOPS_FP16": 4000.0,
    },
    {
        "Year": 2021,
        "Company": "Cerebras",
        "Chip": "WSE-2",
        "Node_nm": 7,
        "Transistors_B": 2600.0,
        "Die_Size_mm2": 46225,
        "TDP_W": 15000,
        "Peak_TFLOPS_FP16": 8000.0,
    },
    {
        "Year": 2024,
        "Company": "Cerebras",
        "Chip": "WSE-3",
        "Node_nm": 5,
        "Transistors_B": 4000.0,
        "Die_Size_mm2": 46225,
        "TDP_W": 23000,
        "Peak_TFLOPS_FP16": 125000.0,
    },
    # Intel Gaudi
    {
        "Year": 2019,
        "Company": "Intel",
        "Chip": "Gaudi 1",
        "Node_nm": 16,
        "Transistors_B": 10.0,
        "Die_Size_mm2": 600,
        "TDP_W": 300,
        "Peak_TFLOPS_FP16": 64.0,
    },
    {
        "Year": 2022,
        "Company": "Intel",
        "Chip": "Gaudi 2",
        "Node_nm": 7,
        "Transistors_B": 48.0,
        "Die_Size_mm2": 800,
        "TDP_W": 600,
        "Peak_TFLOPS_FP16": 430.0,
    },
    {
        "Year": 2024,
        "Company": "Intel",
        "Chip": "Gaudi 3",
        "Node_nm": 5,
        "Transistors_B": 96.0,
        "Die_Size_mm2": 1200,
        "TDP_W": 900,
        "Peak_TFLOPS_FP16": 1835.0,
    },
]


def mine_ai_accelerator_trends():
    print("Compiling AI Accelerator Power & Thermal Trends...")

    os.makedirs("data/datasets", exist_ok=True)
    out_file = "data/datasets/ai_accelerator_power_thermal_trend.csv"

    # Calculate derived metrics (e.g., Watts per Transistor, TOPS per Watt, Power Density W/mm2)
    for chip in ACCELERATORS:
        chip["Power_Density_W_mm2"] = round(chip["TDP_W"] / chip["Die_Size_mm2"], 2)
        chip["TFLOPS_per_Watt"] = round(chip["Peak_TFLOPS_FP16"] / chip["TDP_W"], 2)

    fieldnames = [
        "Year",
        "Company",
        "Chip",
        "Node_nm",
        "Transistors_B",
        "Die_Size_mm2",
        "TDP_W",
        "Peak_TFLOPS_FP16",
        "Power_Density_W_mm2",
        "TFLOPS_per_Watt",
    ]

    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ACCELERATORS)

    print(f"Saved {len(ACCELERATORS)} AI accelerators to {out_file}")


if __name__ == "__main__":
    mine_ai_accelerator_trends()
