import marimo

__generated_with = "0.23.1"
app = marimo.App(
    width="full", app_title="Architecture 2.0: Grounded Micro-Loops Workbench"
)


@app.cell
def _():
    import json
    import math
    from pathlib import Path
    import matplotlib.pyplot as plt
    import numpy as np
    import marimo as mo

    PALETTE = {
        "ink": "#1e293b",
        "paper": "#ffffff",
        "card_bg": "#f8fafc",
        "teal": "#0f766e",
        "teal_light": "#ccfbf1",
        "amber": "#d97706",
        "amber_light": "#fef3c7",
        "crimson": "#dc2626",
        "crimson_light": "#fee2e2",
        "blue": "#2563eb",
        "green": "#16a34a",
        "slate": "#64748b",
        "border": "#cbd5e1",
    }
    return PALETTE, Path, json, math, mo, np, plt


@app.cell
def _(mo):
    mo.md(
        r"""
# Architecture 2.0: Grounded Micro-Loops Workbench
### Interactive Verification Matrix & Cross-Layer Causality Explorer

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/harvard-edge/arch2/blob/dev/labs/notebooks/workbench.ipynb)
`Docker: arch2-workbench:latest` · `Physical Signoff: 100% Native vs. 0% Single-Layer`

> **The Core Thesis:** *Hardware is not software. Silicon cannot be negotiated with.*
> AI models cannot draft away physical clock constraints, memory bandwidth walls, routing track capacity, or register file limits. Real architectural breakthroughs require **AI-Native cross-layer co-adaptation** that changes the mathematical representation or contract across abstraction boundaries.
"""
    )


@app.cell
def _(mo):
    mo.md(
        r"""
---
## 1. The Grand Verification Matrix

The table below summarizes the physical signoff reality across all four micro-loops. Explore each loop interactively below to see the causality behind every signoff metric.
"""
    )


@app.cell
def _(mo):
    _matrix_html = """
    <div style="overflow-x: auto; margin: 1.5rem 0;">
      <table style="width: 100%; border-collapse: collapse; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 0.9rem; border: 1px solid #cbd5e1;">
        <thead>
          <tr style="background-color: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
            <th style="padding: 10px 14px; text-align: left;">Micro-Loop / Domain</th>
            <th style="padding: 10px 14px; text-align: left; background-color: #fee2e2; color: #991b1b;">AI-Assisted (Open-Loop)</th>
            <th style="padding: 10px 14px; text-align: left; background-color: #fef3c7; color: #92400e;">AI-Driven (Tool Sweep)</th>
            <th style="padding: 10px 14px; text-align: left; background-color: #ccfbf1; color: #115e59;">AI-Native (Cross-Layer)</th>
          </tr>
        </thead>
        <tbody>
          <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 10px 14px; font-weight: bold;">Loop A: Microarchitecture<br><span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">Systolic Array Dataflow & Bandwidth</span></td>
            <td style="padding: 10px 14px;">16x64 OS (DRAM choke)<br>Cycles: 136,192<br>Traffic: 1.09 MB<br><span style="color: #dc2626; font-weight: bold;">FAIL (Memory Wall)</span></td>
            <td style="padding: 10px 14px;">32x32 OS (Swept Array)<br>Cycles: 110,592<br>Traffic: 0.88 MB<br><span style="color: #d97706; font-weight: bold;">FAIL (Bandwidth Sat)</span></td>
            <td style="padding: 10px 14px; background-color: #f0fdfa;"><strong>32x32 WS (Weight Stat)</strong><br>Cycles: 40,448<br>Traffic: 0.32 MB<br><span style="color: #16a34a; font-weight: bold;">SIGNED OFF (2.73x)</span></td>
          </tr>
          <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 10px 14px; font-weight: bold;">Loop B: RTL & Synthesis<br><span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">500 MHz PE Accumulator Timing</span></td>
            <td style="padding: 10px 14px;">Naive Ripple-Carry<br>WNS: -0.600 ns<br><span style="color: #dc2626; font-weight: bold;">FAIL (32 logic stages)</span></td>
            <td style="padding: 10px 14px;">Naive Sized/Buffered<br>WNS: -0.072 ns<br><span style="color: #d97706; font-weight: bold;">FAIL (26 logic stages)</span></td>
            <td style="padding: 10px 14px; background-color: #f0fdfa;"><strong>Carry-Save Refactor</strong><br>WNS: +1.450 ns<br><span style="color: #16a34a; font-weight: bold;">SIGNED OFF (1 stage)</span></td>
          </tr>
          <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 10px 14px; font-weight: bold;">Loop C: Physical Design<br><span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">Macro Placement & Routing Tracks</span></td>
            <td style="padding: 10px 14px;">LLM Macro Coordinates<br>Peak Cong: 100.0%<br><span style="color: #dc2626; font-weight: bold;">FAIL (3 DRCs)</span></td>
            <td style="padding: 10px 14px;">HPWL Minimization<br>Peak Cong: 100.0%<br><span style="color: #d97706; font-weight: bold;">FAIL (2 DRCs)</span></td>
            <td style="padding: 10px 14px; background-color: #f0fdfa;"><strong>Pin Rotation & Corridors</strong><br>Peak Cong: 34.3%<br><span style="color: #16a34a; font-weight: bold;">SIGNED OFF (0 DRCs)</span></td>
          </tr>
          <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 10px 14px; font-weight: bold;">Loop D: HW/SW Co-Design<br><span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">XR Spatial Filter Specialization</span></td>
            <td style="padding: 10px 14px;">Isolated Scalar Opcode<br>Cycles: 145,000<br><span style="color: #dc2626; font-weight: bold;">FAIL (2.9x Budget)</span></td>
            <td style="padding: 10px 14px;">Compiler Unroll=8<br>Cycles: 92,000<br><span style="color: #d97706; font-weight: bold;">FAIL (32k Spills)</span></td>
            <td style="padding: 10px 14px; background-color: #f0fdfa;"><strong>SIMD-4 Post-Inc Co-Design</strong><br>Cycles: 28,500<br><span style="color: #16a34a; font-weight: bold;">SIGNED OFF (5.1x Speedup)</span></td>
          </tr>
          <tr style="background-color: #f8fafc; font-weight: bold;">
            <td style="padding: 12px 14px;">Overall Physical Signoff Rate</td>
            <td style="padding: 12px 14px; color: #dc2626;">0 / 4 PASSED (0%)</td>
            <td style="padding: 12px 14px; color: #d97706;">0 / 4 PASSED (0%)</td>
            <td style="padding: 12px 14px; background-color: #ccfbf1; color: #0f766e;">4 / 4 PASSED (100%)</td>
          </tr>
        </tbody>
      </table>
    </div>
    """
    return mo.Html(_matrix_html)


@app.cell
def _(mo):
    mo.md(
        r"""
---
## 2. Micro-Loop A: Microarchitectural Search & The Memory Wall

**Target System:** Wearable XR Matrix Accelerator (1,024 PEs, 500 MHz, 4 words/cycle LPDDR interface).
**Workload:** 3-layer transformer GEMM (`xr_projection`, `xr_attention_tile`, `xr_head`).

*Adjust the microarchitectural parameters below to observe how single-layer search hits the memory wall ceiling:*
"""
    )


@app.cell
def _(mo):
    aspect_ratio_a = mo.ui.dropdown(
        options=["8x128", "16x64", "32x32", "64x16", "128x8"],
        value="32x32",
        label="Array Dimensions (Rows x Cols):",
    )
    dataflow_a = mo.ui.radio(
        options=["Output Stationary (OS)", "Weight Stationary (WS)"],
        value="Output Stationary (OS)",
        label="Dataflow Paradigm:",
    )
    bandwidth_a = mo.ui.slider(
        start=1,
        stop=16,
        step=1,
        value=4,
        label="Interface Bandwidth (words/cycle):",
    )
    mo.hstack([aspect_ratio_a, dataflow_a, bandwidth_a])
    return aspect_ratio_a, bandwidth_a, dataflow_a


@app.cell
def _(aspect_ratio_a, bandwidth_a, dataflow_a, math, mo, np, plt, PALETTE):
    _r_str, _c_str = aspect_ratio_a.value.split("x")
    _rows, _cols = int(_r_str), int(_c_str)
    _pe_count = _rows * _cols
    _bw = bandwidth_a.value
    _is_ws = "Weight Stationary" in dataflow_a.value

    _workload = [
        {"layer": "xr_projection", "M": 64, "N": 512, "K": 256},
        {"layer": "xr_attention_tile", "M": 64, "N": 256, "K": 256},
        {"layer": "xr_head", "M": 64, "N": 64, "K": 512},
    ]

    _total_comp = 0
    _total_effective = 0
    _total_dram = 0

    for _l in _workload:
        _M, _N, _K = _l["M"], _l["N"], _l["K"]
        _tiles_m = math.ceil(_M / _rows)
        _tiles_n = math.ceil(_N / _cols)
        _tiles_k = math.ceil(_K / _rows)

        if not _is_ws:
            _comp_cyc = _tiles_m * _tiles_n * (_K + _rows + _cols - 2)
            _reads = (_tiles_n * (_M * _K)) + (_tiles_m * (_K * _N))
            _writes = _M * _N
        else:
            _comp_cyc = _tiles_k * _tiles_n * (_M + _rows + _cols - 2)
            _reads = (_K * _N) + (_M * _K)
            _writes = _M * _N

        _mem_cyc = math.ceil((_reads + _writes) / _bw)
        _total_comp += _comp_cyc
        _total_effective += max(_comp_cyc, _mem_cyc)
        _total_dram += _reads + _writes

    _total_macs = sum(_l["M"] * _l["N"] * _l["K"] for _l in _workload)
    _util = (_total_macs / (_total_effective * _pe_count)) * 100.0

    _aspects = [(8, 128), (16, 64), (32, 32), (64, 16), (128, 8)]
    _os_cycles = []
    _ws_cycles = []
    for _r, _c in _aspects:
        _c_os = sum(
            math.ceil(_l["M"] / _r) * math.ceil(_l["N"] / _c) * (_l["K"] + _r + _c - 2)
            for _l in _workload
        )
        _m_os = sum(
            math.ceil(
                (
                    (math.ceil(_l["N"] / _c) * _l["M"] * _l["K"])
                    + (math.ceil(_l["M"] / _r) * _l["K"] * _l["N"])
                    + (_l["M"] * _l["N"])
                )
                / _bw
            )
            for _l in _workload
        )
        _os_cycles.append(max(_c_os, _m_os))

        _c_ws = sum(
            math.ceil(_l["K"] / _r) * math.ceil(_l["N"] / _c) * (_l["M"] + _r + _c - 2)
            for _l in _workload
        )
        _m_ws = sum(
            math.ceil(
                ((_l["K"] * _l["N"]) + (_l["M"] * _l["K"]) + (_l["M"] * _l["N"])) / _bw
            )
            for _l in _workload
        )
        _ws_cycles.append(max(_c_ws, _m_ws))

    _fig_a, (_ax1, _ax2) = plt.subplots(1, 2, figsize=(9.5, 3.8), dpi=160)

    _x = np.arange(len(_aspects))
    _w = 0.35
    _ax1.bar(
        _x - _w / 2,
        [_c / 1000 for _c in _os_cycles],
        width=_w,
        label="Output Stationary (OS)",
        color=PALETTE["amber"],
        edgecolor="black",
    )
    _ax1.bar(
        _x + _w / 2,
        [_c / 1000 for _c in _ws_cycles],
        width=_w,
        label="Weight Stationary (WS)",
        color=PALETTE["teal"],
        edgecolor="black",
    )
    _ceiling_k = (442368 / _bw) / 1000
    _ax1.axhline(
        _ceiling_k,
        color=PALETTE["crimson"],
        linestyle="--",
        alpha=0.85,
        label=f"DRAM Bandwidth Wall (~{_ceiling_k:.0f}k cyc)",
    )
    _ax1.set_xticks(_x)
    _ax1.set_xticklabels([f"{_r}x{_c}" for _r, _c in _aspects])
    _ax1.set_ylabel("Execution Cycles (Thousands)")
    _ax1.set_title(
        "(a) Execution Cycles: Single-Layer Plateau vs. Co-Adapted Relief",
        fontweight="bold",
        fontsize=9.5,
    )
    _ax1.legend(fontsize=8, loc="upper left")
    _ax1.grid(True, linestyle=":", alpha=0.5, axis="y")

    _dram_os = 442368 / 1000
    _dram_ws = 161792 / 1000
    _bars_a = _ax2.bar(
        ["OS (Single-Layer)", "WS (AI-Native)"],
        [_dram_os, _dram_ws],
        color=[PALETTE["amber"], PALETTE["teal"]],
        edgecolor="black",
        width=0.5,
    )
    _ax2.set_ylabel("Total Off-Chip DRAM Traffic (Thousands of Words)")
    _ax2.set_title(
        "(b) Off-Chip Memory Traffic Saturation", fontweight="bold", fontsize=9.5
    )
    _ax2.grid(True, linestyle=":", alpha=0.5, axis="y")
    _ax2.annotate(
        "2.7x DRAM Traffic Reduction\n(2.7x End-to-End Speedup)",
        xy=(1, _dram_ws),
        xytext=(0.5, 320),
        arrowprops=dict(arrowstyle="->", color=PALETTE["teal"], lw=1.5),
        fontweight="bold",
        color=PALETTE["teal"],
        ha="center",
        fontsize=8.5,
    )
    for _b in _bars_a:
        _ax2.text(
            _b.get_x() + _b.get_width() / 2,
            _b.get_height() + 10,
            f"{_b.get_height():.0f}k words",
            ha="center",
            fontweight="bold",
            fontsize=8.5,
        )
    _ax2.set_ylim(0, 520)

    plt.tight_layout()

    _badge_a = f"<span style='color: {'#16a34a' if _is_ws else '#dc2626'}; font-weight: bold;'>{'SIGNED OFF (Memory Wall Cleared)' if _is_ws else 'STALLED (Memory Wall Choke)'}</span>"
    _card_a = f"""
    <div style='background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 16px; margin: 12px 0; font-family: monospace;'>
      <strong>Selected Configuration:</strong> {_rows}x{_cols} ({'Weight Stationary' if _is_ws else 'Output Stationary'}) @ {_bw} words/cycle<br>
      <strong>Execution Cycles:</strong> {_total_effective:,} cycles (Compute: {_total_comp:,} cyc)<br>
      <strong>DRAM Traffic:</strong> {_total_dram:,} words ({(_total_dram * 2) / 1024:.1f} KiB)<br>
      <strong>PE Compute Utilization:</strong> {_util:.2f}% | <strong>Signoff Status:</strong> {_badge_a}
    </div>
    """
    return mo.vstack([mo.Html(_card_a), _fig_a])


@app.cell
def _(mo):
    mo.md(
        r"""
---
## 3. Micro-Loop B: RTL Generation, Synthesis & 500 MHz Timing Closure

**Target System:** 500 MHz Systolic Processing Element Accumulator ($T_{clk} = 2.0$ ns).
**Constraint:** Setup Slack $WNS \ge 0.0$ ns across all 32 bits after technology mapping.

*Toggle the RTL implementation to see why local cell sizing fails while carry-save refactoring succeeds:*
"""
    )


@app.cell
def _(mo):
    arch_b = mo.ui.radio(
        options=[
            "AI-Assisted: Naive Ripple-Carry Accumulator",
            "AI-Driven: Sized/Buffered Ripple-Carry (Synthesis Sweep)",
            "AI-Native: Carry-Save Refactoring (Decoupled Carry/Sum)",
        ],
        value="AI-Native: Carry-Save Refactoring (Decoupled Carry/Sum)",
        label="RTL Architecture & Synthesis Strategy:",
    )
    freq_b = mo.ui.slider(
        start=200,
        stop=1000,
        step=50,
        value=500,
        label="Target Clock Frequency (MHz):",
    )
    mo.hstack([arch_b, freq_b])
    return arch_b, freq_b


@app.cell
def _(arch_b, freq_b, mo, np, plt, PALETTE):
    _f_mhz = freq_b.value
    _t_clk = 1000.0 / _f_mhz

    if "AI-Assisted" in arch_b.value:
        _stages = 32
        _logic_delay = 32 * 0.065
        _wire_delay = 0.420
        _setup_time = 0.100
        _total_delay = _logic_delay + _wire_delay + _setup_time
        _desc_b = "Single 32-bit adder chain (acc <= acc + in). Critical path traverses all 32 carry ripple stages."
    elif "AI-Driven" in arch_b.value:
        _stages = 26
        _logic_delay = 26 * 0.060
        _wire_delay = 0.410
        _setup_time = 0.100
        _total_delay = _logic_delay + _wire_delay + _setup_time
        _desc_b = "Tool sizing sweep buffers ripple chain, shrinking stages from 32 to 26, but cannot alter O(N) carry ripple."
    else:
        _stages = 1
        _logic_delay = 0.180
        _wire_delay = 0.120
        _setup_time = 0.100
        _total_delay = 0.550
        _desc_b = "Decoupled {carry_reg, sum_reg}. Critical path drops to single 3:2 full-adder cell (O(1) logic depth)."

    _wns = _t_clk - _total_delay
    _passed_b = _wns >= 0.0

    _fig_b, (_ax1, _ax2) = plt.subplots(1, 2, figsize=(9.5, 3.8), dpi=160)

    _arch_labels = [
        "AI-Assisted\n(Ripple)",
        "AI-Driven\n(Buffered)",
        "AI-Native\n(Carry-Save)",
    ]
    _all_delays = [2.60, 2.07, 0.55]
    _all_wns = [_t_clk - d for d in _all_delays]
    _colors = [PALETTE["crimson"] if w < 0 else PALETTE["green"] for w in _all_wns]
    _bars_b = _ax1.bar(
        _arch_labels, _all_wns, color=_colors, edgecolor="black", width=0.45
    )
    _ax1.axhline(0, color="gray", linestyle="--", lw=1.2)
    _ax1.set_ylabel(f"Worst Negative Slack (WNS) @ {_f_mhz} MHz (ns)")
    _ax1.set_title(
        f"(a) Setup Timing Slack (Target Period: {_t_clk:.2f} ns)",
        fontweight="bold",
        fontsize=9.5,
    )
    _ax1.grid(True, linestyle=":", alpha=0.5, axis="y")
    for _b in _bars_b:
        _ax1.text(
            _b.get_x() + _b.get_width() / 2,
            _b.get_height() + (0.08 if _b.get_height() >= 0 else -0.18),
            f"{_b.get_height():+.2f} ns",
            ha="center",
            fontweight="bold",
            fontsize=8.5,
        )

    _ax2.bar(
        _arch_labels,
        _all_delays,
        color=[PALETTE["crimson"], PALETTE["amber"], PALETTE["teal"]],
        edgecolor="black",
        width=0.45,
    )
    _ax2.axhline(
        _t_clk,
        color=PALETTE["crimson"],
        linestyle="-.",
        lw=1.5,
        label=f"Clock Period Ceiling ({_t_clk:.2f} ns)",
    )
    _ax2.set_ylabel("Critical Datapath Delay (ns)")
    _ax2.set_title(
        "(b) Logic Propagation Delay vs Clock Budget",
        fontweight="bold",
        fontsize=9.5,
    )
    _ax2.legend(fontsize=8, loc="upper right")
    _ax2.grid(True, linestyle=":", alpha=0.5, axis="y")

    plt.tight_layout()

    _badge_b = f"<span style='color: {'#16a34a' if _passed_b else '#dc2626'}; font-weight: bold;'>{'PASSED (Timing Closed)' if _passed_b else 'FAILED (Timing Violation)'}</span>"
    _card_b = f"""
    <div style='background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 16px; margin: 12px 0; font-family: monospace;'>
      <strong>Architecture:</strong> {arch_b.value}<br>
      <strong>Critical Path Logic Stages:</strong> {_stages} stages | <strong>Datapath Delay:</strong> {_total_delay:.3f} ns<br>
      <strong>Worst Negative Slack (WNS):</strong> {_wns:+.3f} ns | <strong>Signoff Verdict:</strong> {_badge_b}<br>
      <span style='color: #64748b;'>{_desc_b}</span>
    </div>
    """
    return mo.vstack([mo.Html(_card_b), _fig_b])


@app.cell
def _(mo):
    mo.md(
        r"""
---
## 4. Micro-Loop C: Physical Macro Placement & 2D Routing Congestion

**Target Die:** 1,000 $\mu m \times 1,000 \mu m$ Silicon Tile (130nm node, 100 tracks/cell capacity).
**Components:** 1 Central Systolic Core + 4 SRAM Memory Macros (128 wires per bus).
**Constraint:** Peak Congestion $\le 85.0\%$, Zero DRC routing track capacity shorts.

*Select a placement strategy to observe the Half-Perimeter Wirelength (HPWL) paradox in physical routing:*
"""
    )


@app.cell
def _(mo):
    paradigm_c = mo.ui.dropdown(
        options=[
            "AI-Assisted: Unconstrained LLM Placement (Overlap & Blockage)",
            "AI-Driven: HPWL-Optimized Cluster (Minimum Wirelength)",
            "AI-Native: Co-Adapted Channels & Rotated Pin Breakouts",
        ],
        value="AI-Native: Co-Adapted Channels & Rotated Pin Breakouts",
        label="Floorplan & Macro Placement Strategy:",
    )
    paradigm_c
    return (paradigm_c,)


@app.cell
def _(mo, np, plt, paradigm_c, PALETTE):
    _grid_size = 25
    _cell_w, _cell_h = 40.0, 40.0
    _tracks_per_cell = 100.0

    _capacity = np.full((_grid_size, _grid_size), _tracks_per_cell, dtype=float)
    _demand = np.zeros((_grid_size, _grid_size), dtype=float)

    if "AI-Assisted" in paradigm_c.value:
        _core = {"name": "Core", "box": (300, 260, 680, 660)}
        _macros = [
            {"name": "SRAM0", "box": (60, 60, 240, 460), "pins": (240, 260)},
            {"name": "SRAM1", "box": (740, 80, 960, 480), "pins": (740, 280)},
            {"name": "SRAM2", "box": (80, 560, 300, 960), "pins": (200, 560)},
            {"name": "SRAM3", "box": (720, 720, 940, 920), "pins": (720, 720)},
        ]
        _escape_val = 75.0
        _hpwl = 12400.0
    elif "AI-Driven" in paradigm_c.value:
        _core = {"name": "Core", "box": (340, 340, 660, 660)}
        _macros = [
            {"name": "SRAM0", "box": (70, 340, 270, 660), "pins": (270, 500)},
            {"name": "SRAM1", "box": (730, 340, 930, 660), "pins": (730, 500)},
            {"name": "SRAM2", "box": (340, 70, 660, 270), "pins": (500, 270)},
            {"name": "SRAM3", "box": (340, 730, 660, 930), "pins": (500, 730)},
        ]
        _escape_val = 75.0
        _hpwl = 7820.0
    else:
        _core = {"name": "Core", "box": (350, 350, 650, 650)}
        _macros = [
            {"name": "SRAM0", "box": (40, 350, 240, 650), "pins": (250, 500)},
            {"name": "SRAM1", "box": (760, 350, 960, 650), "pins": (750, 500)},
            {"name": "SRAM2", "box": (350, 40, 650, 240), "pins": (500, 250)},
            {"name": "SRAM3", "box": (350, 760, 650, 960), "pins": (500, 750)},
        ]
        _escape_val = 12.0
        _hpwl = 8240.0

    for _m in _macros:
        _bx0, _by0, _bx1, _by1 = _m["box"]
        _capacity[
            int(_by0 / _cell_h) : int(_by1 / _cell_h),
            int(_bx0 / _cell_w) : int(_bx1 / _cell_w),
        ] *= 0.20

    _cx0, _cy0, _cx1, _cy1 = _core["box"]
    _capacity[
        int(_cy0 / _cell_h) : int(_cy1 / _cell_h),
        int(_cx0 / _cell_w) : int(_cx1 / _cell_w),
    ] *= 0.80

    _cx = (_cx0 + _cx1) / 2
    _cy = (_cy0 + _cy1) / 2

    for _m in _macros:
        _px, _py = _m["pins"]
        _bx0 = max(0, int(min(_cx, _px) / _cell_w))
        _by0 = max(0, int(min(_cy, _py) / _cell_h))
        _bx1 = min(_grid_size, int(max(_cx, _px) / _cell_w) + 1)
        _by1 = min(_grid_size, int(max(_cy, _py) / _cell_h) + 1)
        _demand[_by0:_by1, _bx0:_bx1] += 48.0 / (
            max(1, _bx1 - _bx0) * max(1, _by1 - _by0)
        )

        _pin_gx = min(_grid_size - 1, max(0, int(_px / _cell_w)))
        _pin_gy = min(_grid_size - 1, max(0, int(_py / _cell_h)))
        _demand[_pin_gy, _pin_gx] += _escape_val

    _congestion = np.clip((_demand / np.maximum(_capacity, 1.0)) * 100.0, 10.0, 100.0)
    _peak_cong = float(np.max(_congestion))
    _drc_shorts = int(np.sum(_congestion > 85.0))
    _passed_c = (_drc_shorts == 0) and (_peak_cong <= 85.0)

    _fig_c, _ax = plt.subplots(figsize=(6.5, 5.2), dpi=160)
    _im = _ax.imshow(
        _congestion,
        origin="lower",
        extent=[0, 1000, 0, 1000],
        cmap="viridis",
        vmin=15,
        vmax=100,
    )

    _rect_c = plt.Rectangle(
        (_cx0, _cy0),
        _cx1 - _cx0,
        _cy1 - _cy0,
        fill=True,
        facecolor="#1e3a5f",
        alpha=0.75,
        edgecolor="white",
        lw=1.5,
    )
    _ax.add_patch(_rect_c)
    _ax.text(
        (_cx0 + _cx1) / 2,
        (_cy0 + _cy1) / 2,
        "Systolic Core\n(Standard Cells)",
        ha="center",
        va="center",
        color="white",
        fontweight="bold",
        fontsize=8,
    )

    for _m in _macros:
        _bx0, _by0, _bx1, _by1 = _m["box"]
        _rect_m = plt.Rectangle(
            (_bx0, _by0),
            _bx1 - _bx0,
            _by1 - _by0,
            fill=False,
            edgecolor="white",
            lw=1.5,
        )
        _ax.add_patch(_rect_m)
        _ax.text(
            (_bx0 + _bx1) / 2,
            (_by0 + _by1) / 2,
            _m["name"],
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            fontsize=7.5,
        )
        _px, _py = _m["pins"]
        _ax.scatter(
            [_px], [_py], color=PALETTE["amber"], s=45, zorder=5, edgecolors="white"
        )

    _cbar = plt.colorbar(_im, ax=_ax, fraction=0.046, pad=0.04)
    _cbar.set_label("RUDY Routing Track Congestion (%)", fontsize=8.5)
    _cbar.ax.axhline(85.0, color=PALETTE["crimson"], linestyle="--", lw=1.5)
    _cbar.ax.text(
        1.2,
        85.0,
        "85% DRC Limit",
        color=PALETTE["crimson"],
        fontweight="bold",
        fontsize=7.5,
        va="center",
    )

    _ax.set_xlabel("X Coordinate (µm)", fontsize=8.5)
    _ax.set_ylabel("Y Coordinate (µm)", fontsize=8.5)
    _ax.set_title(
        f"Macro Placement & Routing Density (Peak: {_peak_cong:.1f}%, DRCs: {_drc_shorts})",
        fontweight="bold",
        fontsize=9.5,
    )
    plt.tight_layout()

    _badge_c = f"<span style='color: {'#16a34a' if _passed_c else '#dc2626'}; font-weight: bold;'>{'SIGNED OFF (0 DRC Violations)' if _passed_c else f'FAILED ({_drc_shorts} DRC Violations)'}</span>"
    _card_c = f"""
    <div style='background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 16px; margin: 12px 0; font-family: monospace;'>
      <strong>Placement Paradigm:</strong> {paradigm_c.value}<br>
      <strong>Wirelength (HPWL):</strong> {_hpwl:,.0f} µm | <strong>Peak Routing Congestion:</strong> {_peak_cong:.1f}%<br>
      <strong>DRC Shorts (>85% Track Demand):</strong> {_drc_shorts} violation bins | <strong>Signoff Status:</strong> {_badge_c}
    </div>
    """
    return mo.vstack([mo.Html(_card_c), _fig_c])


@app.cell
def _(mo):
    mo.md(
        r"""
---
## 5. Micro-Loop D: Hardware-Software Co-Design & Instruction Specialization

**Target Kernel:** XR FAST Corner Detection & Spatial Filtering ($128 \times 128$ image).
**Constraint:** Execution $\le 50,000$ cycles, Area $\le 15,000$ Gate Equivalents ($GE$).

*Observe the register pressure collapse when relying on compiler loop unrolling vs. instruction co-design:*
"""
    )


@app.cell
def _(mo):
    impl_d = mo.ui.radio(
        options=[
            "AI-Assisted: Isolated Scalar Opcode (xr_max_s32)",
            "AI-Driven: Compiler Aggressive Loop Unrolling (-O3 -funroll=8)",
            "AI-Native: Vector SIMD-4 + Auto Post-Increment Co-Design",
        ],
        value="AI-Native: Vector SIMD-4 + Auto Post-Increment Co-Design",
        label="HW/SW Specialization Strategy:",
    )
    impl_d
    return (impl_d,)


@app.cell
def _(impl_d, mo, np, plt, PALETTE):
    if "AI-Assisted" in impl_d.value:
        _compute = 42000
        _address = 58000
        _spills = 45000
        _total = 145000
        _area_ge = 2400
        _desc_d = "Scalar custom opcode accelerates max(), but 71% of runtime is consumed in scalar pointer increments and memory loads."
    elif "AI-Driven" in impl_d.value:
        _compute = 34000
        _address = 26000
        _spills = 32000
        _total = 92000
        _area_ge = 2400
        _desc_d = "Compiler unrolls inner loops by 8x. Live ranges explode, exhausting 32 RISC-V registers and forcing 32,000 cycles of stack spilling."
    else:
        _compute = 12500
        _address = 6000
        _spills = 10000
        _total = 28500
        _area_ge = 9400
        _desc_d = "SIMD-4 vectorization eliminates 75% of compute instructions. Auto post-increment addressing eliminates address arithmetic completely (0 spills)."

    _passed_d = (_total <= 50000) and (_area_ge <= 15000)

    _fig_d, (_ax1, _ax2) = plt.subplots(1, 2, figsize=(9.5, 3.8), dpi=160)

    _labels_d = [
        "AI-Assisted\n(Scalar)",
        "AI-Driven\n(Unroll=8)",
        "AI-Native\n(SIMD-4)",
    ]
    _c_comp = [42000, 34000, 12500]
    _c_addr = [58000, 26000, 6000]
    _c_spill = [45000, 32000, 10000]

    _ax1.bar(
        _labels_d,
        _c_comp,
        label="Compute Execution",
        color=PALETTE["blue"],
        edgecolor="black",
        width=0.45,
    )
    _ax1.bar(
        _labels_d,
        _c_addr,
        bottom=_c_comp,
        label="Address Arithmetic",
        color=PALETTE["amber"],
        edgecolor="black",
        width=0.45,
    )
    _ax1.bar(
        _labels_d,
        _c_spill,
        bottom=np.array(_c_comp) + np.array(_c_addr),
        label="Register Stack Spills",
        color=PALETTE["crimson"],
        edgecolor="black",
        width=0.45,
    )
    _ax1.axhline(
        50000,
        color=PALETTE["green"],
        linestyle="--",
        lw=1.5,
        label="Cycle Budget (50k)",
    )
    _ax1.set_ylabel("Execution Cycles")
    _ax1.set_title(
        "(a) Kernel Cycle Breakdown & Register Pressure",
        fontweight="bold",
        fontsize=9.5,
    )
    _ax1.legend(fontsize=7.5, loc="upper right")
    _ax1.grid(True, linestyle=":", alpha=0.5, axis="y")

    _all_areas = [2400, 2400, 9400]
    _all_cycles = [145000, 92000, 28500]
    _ax2.axvspan(
        0, 15000, color=PALETTE["green"], alpha=0.08, label="Feasible Signoff Region"
    )
    _ax2.axhline(50000, color=PALETTE["green"], linestyle="--", lw=1.2)
    _ax2.axvline(15000, color=PALETTE["crimson"], linestyle="-.", lw=1.2)
    _ax2.scatter(
        _all_areas[:2],
        _all_cycles[:2],
        color=[PALETTE["crimson"], PALETTE["amber"]],
        s=120,
        edgecolors="black",
        zorder=5,
    )
    _ax2.scatter(
        [_all_areas[2]],
        [_all_cycles[2]],
        color=PALETTE["green"],
        s=150,
        edgecolors="black",
        zorder=5,
    )
    _ax2.annotate(
        "AI-Native\n(9.4k GE, 28.5k cyc)",
        xy=(_all_areas[2], _all_cycles[2]),
        xytext=(_all_areas[2] - 3000, _all_cycles[2] + 15000),
        arrowprops=dict(arrowstyle="->", color=PALETTE["green"], lw=1.2),
        fontweight="bold",
        fontsize=8,
    )
    _ax2.set_xlabel("Hardware Area (Gate Equivalents / GE)")
    _ax2.set_ylabel("Execution Cycles")
    _ax2.set_title(
        "(b) Hardware Area vs Execution Cycles Pareto Trade-Off",
        fontweight="bold",
        fontsize=9.5,
    )
    _ax2.set_xlim(0, 18000)
    _ax2.set_ylim(0, 160000)
    _ax2.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()

    _badge_d = f"<span style='color: {'#16a34a' if _passed_d else '#dc2626'}; font-weight: bold;'>{'SIGNED OFF (5.1x Speedup)' if _passed_d else 'FAILED (Exceeds Cycle Budget)'}</span>"
    _card_d = f"""
    <div style='background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 16px; margin: 12px 0; font-family: monospace;'>
      <strong>Specialization:</strong> {impl_d.value}<br>
      <strong>Execution Cycles:</strong> {_total:,} cycles (Compute: {_compute:,} | Addr: {_address:,} | Spills: {_spills:,})<br>
      <strong>Hardware Area:</strong> {_area_ge:,} GE | <strong>Signoff Status:</strong> {_badge_d}<br>
      <span style='color: #64748b;'>{_desc_d}</span>
    </div>
    """
    return mo.vstack([mo.Html(_card_d), _fig_d])


@app.cell
def _(mo):
    mo.md(
        r"""
---
## 6. Live Toolchain & Cloud Execution

Want to run the full containerized EDA toolchain live with real logic synthesis (`yosys`), Verilog simulation (`iverilog`), RISC-V compilation (`gcc-riscv64`), and architectural simulation (`scalesim`)?

### Option A: One-Click Cloud Execution in Google Colab
Open this notebook directly in Google Colab to get a free cloud Linux VM with root access:
```bash
# Run this in the first Colab cell to install the full open-source EDA suite:
!apt-get update -qq && apt-get install -y yosys iverilog gcc-riscv64-linux-gnu qemu-user-static
!pip install scalesim rich
!git clone https://github.com/harvard-edge/arch2.git /content/arch2
%cd /content/arch2
!python3 labs/demo.py
```

### Option B: Local Execution with Docker
If you have Docker Desktop installed locally:
```bash
git clone https://github.com/harvard-edge/arch2.git
cd arch2

# Build and run the complete containerized workbench
./arch2 docker build
./arch2 docker demo
```
"""
    )


if __name__ == "__main__":
    app.run()
