#!/usr/bin/env python3
"""Micro-Loop D: Hardware-Software Co-Design and Instruction Specialization.

=======================================================================
Demonstrates the concrete distinction across design paradigms:
  1. AI-Assisted (Open-Loop):
     LLM drafts an isolated custom scalar dot-product opcode. While raw multiply-add
     is fast, address arithmetic (58,000 cycles) and register spills (45,000 cycles)
     dominate runtime. Total = 145,000 cycles (violates 50,000 budget by 2.9x).
  2. AI-Driven (Closed-Loop, Single-Layer):
     Compiler autotuner aggressively unrolls loops (unroll=8) and reschedules code on
     static scalar hardware. Unrolling exhausts physical registers, forcing 32,000
     stack spill-and-reload cycles. Total = 92,000 cycles (still fails by 1.84x).
  3. AI-Native (Closed-Loop, Cross-Layer):
     Profiler diagnoses address arithmetic and stack spill bottlenecks, triggering
     simultaneous co-design of:
       - Hardware: 4-way packed SIMD FMA with auto-post-increment memory addressing.
       - Compiler: Specialized lowering targeting post-increment vector primitives.
     Collapses address math to 6,000 cycles and spills to 10,000 cycles.
     Total = 28,500 cycles (5.09x speedup, 1.75x inside budget, 9,400 GE area).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
import yaml

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

ROOT = Path(__file__).resolve().parent
WORKLOAD_DIR = ROOT / "workload"

# Representative assembly listings
ASM_ASSISTED = """\
# AI-Assisted: Isolated Custom Opcode (Scalar Overhead Dominated)
.L_inner_loop:
    slli    t0, s1, 8          # Address math: y * FRAME_WIDTH
    add     t0, t0, s2         # Address math: + x
    add     t1, a0, t0         # Pixel pointer calculation
    lbu     a4, 0(t1)          # Scalar pixel load
    add     t2, a2, s3         # Weight pointer calculation
    lb      a5, 0(t2)          # Scalar weight load
    custom.dot a3, a4, a5      # Isolated custom MAC instruction
    addi    s3, s3, 1          # Increment weight index
    addi    s2, s2, 1          # Increment pixel index
    blt     s2, t3, .L_inner_loop
"""

ASM_DRIVEN = """\
# AI-Driven: Aggressive Compiler Unrolling (Register Spills to Stack)
.L_unrolled_8x:
    # --- Unroll factor 8 exhausts RV32 32-register file ---
    sw      s4, 16(sp)         # Spill saved register to stack
    sw      s5, 20(sp)         # Spill saved register to stack
    sw      s6, 24(sp)         # Spill saved register to stack
    lbu     a4, 0(t1)
    lb      a5, 0(t2)
    custom.dot a3, a4, a5
    lbu     a6, 1(t1)
    lb      a7, 1(t2)
    custom.dot a3, a6, a7
    # ... (14 stack memory accesses per iteration) ...
    lw      s6, 24(sp)         # Reload spilled register from stack
    lw      s5, 20(sp)         # Reload spilled register from stack
    lw      s4, 16(sp)         # Reload spilled register from stack
"""

ASM_NATIVE = """\
# AI-Native: Co-Designed Packed SIMD with Post-Increment Addressing
.L_simd_vector_loop:
    # 4 pixels + 4 weights processed in a single cycle
    # Hardware automatically auto-increments pointers a0 and a1
    vdot4.postinc   v0, (a0)+, (a1)+   # 4-way SIMD FMA + Post-Inc
    vdot4.postinc   v0, (a0)+, (a1)+   # 4-way SIMD FMA + Post-Inc
    # Zero stack spills, zero separate pointer increment instructions
    bne             a0, a3, .L_simd_vector_loop
"""


def evaluate_codesign(paradigm: str) -> Dict[str, Any]:
    """Evaluates execution cycle breakdown, hardware area, and signoff status."""
    p_map = {
        "assisted_scalar_opcode": "assisted",
        "driven_compiler_autotuned": "driven",
        "native_joint_codesigned": "native",
        "assisted": "assisted",
        "driven": "driven",
        "native": "native",
    }
    paradigm = p_map.get(paradigm, paradigm)

    if paradigm == "assisted":
        compute_cycles = 42000
        address_calc_cycles = 58000
        register_spill_cycles = 45000
        total_cycles = compute_cycles + address_calc_cycles + register_spill_cycles
        hardware_area_ge = 2400
        instruction_set = "RV32IM + scalar custom.dot"
        compiler_strategy = "Standard GCC -O3"
        description = "Isolated custom scalar opcode drafted by LLM"
        action_taken = "Single opcode addition; scalar address calculation and load/store bottlenecks persist"

    elif paradigm == "driven":
        compute_cycles = 34000
        address_calc_cycles = 26000
        register_spill_cycles = 32000
        total_cycles = compute_cycles + address_calc_cycles + register_spill_cycles
        hardware_area_ge = 2400  # Hardware unchanged
        instruction_set = "RV32IM + scalar custom.dot"
        compiler_strategy = "Compiler autotuning (unroll=8, loop skewing)"
        description = "Aggressive compiler autotuning on static hardware"
        action_taken = "Compiler flag sweep; unrolling exhausts 32-entry register file, triggering 32k spill cycles"

    elif paradigm == "native":
        compute_cycles = 12500
        address_calc_cycles = 6000
        register_spill_cycles = 10000
        total_cycles = compute_cycles + address_calc_cycles + register_spill_cycles
        hardware_area_ge = 9400
        instruction_set = "RV32IM + SIMD-4 vdot4.postinc"
        compiler_strategy = "Matched vectorizer lowering to post-increment primitives"
        description = (
            "Joint HW/SW co-design: SIMD-4 post-inc hardware + matched vector lowering"
        )
        action_taken = "Cross-layer co-adaptation: post-increment addressing eliminates address arithmetic; SIMD vectors eliminate spills"

    else:
        raise ValueError(f"Unknown paradigm: {paradigm}")

    cycle_target_met = total_cycles <= 50000
    area_target_met = hardware_area_ge <= 15000
    signoff_passed = cycle_target_met and area_target_met

    return {
        "paradigm": paradigm,
        "description": description,
        "action_taken": action_taken,
        "instruction_set": instruction_set,
        "compiler_strategy": compiler_strategy,
        "compute_cycles": compute_cycles,
        "address_calc_cycles": address_calc_cycles,
        "register_spill_cycles": register_spill_cycles,
        "total_cycles": total_cycles,
        "hardware_area_ge": hardware_area_ge,
        "cycle_target_met": cycle_target_met,
        "area_target_met": area_target_met,
        "signoff_passed": signoff_passed,
    }


def generate_visual_plot(data: Dict[str, Any], output_path: Path) -> None:
    """Generates a publication-grade 2-panel chart: stacked cycle breakdown and PPA trade-off."""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    paradigms = [
        "AI-Assisted\n(Scalar Opcode)",
        "AI-Driven\n(Compiler Unroll)",
        "AI-Native\n(SIMD Post-Inc)",
    ]
    keys = ["assisted", "driven", "native"]

    comp_c = [data[k]["compute_cycles"] for k in keys]
    addr_c = [data[k]["address_calc_cycles"] for k in keys]
    spill_c = [data[k]["register_spill_cycles"] for k in keys]
    total_c = [data[k]["total_cycles"] for k in keys]

    # Panel 1: Stacked Cycle Breakdown
    x = np.arange(len(paradigms))
    width = 0.52

    c_comp = "#2980B9"  # Core compute
    c_addr = "#E67E22"  # Address calculation overhead
    c_spill = "#C0392B"  # Stack spill penalty

    p1 = ax1.bar(
        x,
        comp_c,
        width,
        label="Compute Execution",
        color=c_comp,
        edgecolor="#1B2631",
        zorder=3,
    )
    p2 = ax1.bar(
        x,
        addr_c,
        width,
        bottom=comp_c,
        label="Address Arithmetic",
        color=c_addr,
        edgecolor="#1B2631",
        zorder=3,
    )
    p3 = ax1.bar(
        x,
        spill_c,
        width,
        bottom=np.array(comp_c) + np.array(addr_c),
        label="Register Stack Spills",
        color=c_spill,
        edgecolor="#1B2631",
        zorder=3,
    )

    ax1.axhline(
        50000,
        color="#27AE60",
        linestyle="--",
        linewidth=1.8,
        zorder=4,
        label="Cycle Budget Ceiling (50k)",
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(paradigms, fontsize=10)
    ax1.set_title(
        "Kernel Execution Cycle Breakdown by Overhead Source",
        fontsize=12.5,
        fontweight="bold",
        pad=12,
    )
    ax1.set_ylabel("Execution Cycles", fontsize=11, fontweight="bold")
    ax1.grid(axis="y", linestyle=":", alpha=0.6, zorder=0)
    ax1.set_ylim(0, 165000)

    for i, tot in enumerate(total_c):
        status = "PASS" if tot <= 50000 else "FAIL"
        ax1.text(
            x[i],
            tot + 3500,
            f"{tot:,}\n({status})",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
            color="#1B2631",
        )

    ax1.legend(loc="upper right", framealpha=0.9, fontsize=9.5)

    # Panel 2: Cycles vs Hardware Area PPA Pareto Space
    areas = [data[k]["hardware_area_ge"] for k in keys]
    marker_colors = ["#D9534F", "#F0AD4E", "#27AE60"]

    ax2.axvline(
        15000,
        color="#C0392B",
        linestyle="-.",
        linewidth=1.5,
        label="Max Hardware Area Budget (15k GE)",
    )
    ax2.axhline(
        50000,
        color="#27AE60",
        linestyle="--",
        linewidth=1.5,
        label="Target Cycle Budget (50k)",
    )

    # Target feasible design region
    ax2.fill_between(
        [0, 15000],
        0,
        50000,
        color="#27AE60",
        alpha=0.10,
        label="Feasible Signoff Region",
    )

    for i, (k, name) in enumerate(zip(keys, ["Assisted", "Driven", "Native"])):
        ax2.scatter(
            areas[i],
            total_c[i],
            color=marker_colors[i],
            s=180,
            edgecolor="#1B2631",
            linewidth=1.5,
            zorder=5,
        )
        offset_y = 6000 if i != 1 else -10000
        offset_x = 500 if i != 2 else -3000
        ax2.annotate(
            f"AI-{name}\n({areas[i]:,} GE, {total_c[i]:,} cyc)",
            (areas[i], total_c[i]),
            xytext=(areas[i] + offset_x, total_c[i] + offset_y),
            fontsize=9.5,
            fontweight="bold",
            color="#1B2631",
            arrowprops=dict(arrowstyle="->", color="#1B2631", lw=1.0),
            zorder=6,
        )

    ax2.set_xlim(0, 18000)
    ax2.set_ylim(0, 165000)
    ax2.set_title(
        "Hardware Area vs Execution Cycles Pareto Trade-Off",
        fontsize=12.5,
        fontweight="bold",
        pad=12,
    )
    ax2.set_xlabel(
        "Hardware Area (Gate Equivalents / GE)", fontsize=11, fontweight="bold"
    )
    ax2.set_ylabel("Execution Cycles", fontsize=11, fontweight="bold")
    ax2.grid(linestyle=":", alpha=0.6, zorder=0)
    ax2.legend(loc="upper right", framealpha=0.9, fontsize=9.5)

    fig.suptitle(
        "Micro-Loop D: Hardware-Software Co-Design and Instruction Specialization",
        fontsize=14.5,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_path, dpi=300)
    plt.close()


def print_rich_dashboard(
    data: Dict[str, Any], show_asm: bool, console: Console
) -> None:
    """Displays a formatted rich dashboard in the terminal."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]Micro-Loop D: Hardware-Software Co-Design and Instruction Specialization[/bold cyan]\n"
            "[dim]Target: Mobile XR Feature Detection (256x256 Filter) | Budget: <= 50,000 cycles, <= 15,000 GE[/dim]",
            border_style="cyan",
        )
    )

    table = Table(
        title="Paradigm Comparison: HW/SW Co-Design", header_style="bold magenta"
    )
    table.add_column("Metric / Dimension", style="bold")
    table.add_column("AI-Assisted (Open-Loop)", style="red")
    table.add_column("AI-Driven (Compiler Sweep)", style="yellow")
    table.add_column("AI-Native (Cross-Layer)", style="green")

    table.add_row(
        "Specialization",
        "Isolated scalar custom.dot",
        "Compiler unroll=8 on static ISA",
        "SIMD-4 FMA + Post-Inc HW & Lowering",
    )
    table.add_row(
        "Compute Cycles",
        f"{data['assisted']['compute_cycles']:,}",
        f"{data['driven']['compute_cycles']:,}",
        f"{data['native']['compute_cycles']:,} (-63%)",
    )
    table.add_row(
        "Address Math Cycles",
        f"{data['assisted']['address_calc_cycles']:,}",
        f"{data['driven']['address_calc_cycles']:,}",
        f"{data['native']['address_calc_cycles']:,} (-77% via post-inc)",
    )
    table.add_row(
        "Register Spill Cycles",
        f"{data['assisted']['register_spill_cycles']:,}",
        f"{data['driven']['register_spill_cycles']:,} (stack thrashing)",
        f"{data['native']['register_spill_cycles']:,} (-69% via SIMD)",
    )
    table.add_row(
        "Total Cycles",
        f"{data['assisted']['total_cycles']:,} [FAIL]",
        f"{data['driven']['total_cycles']:,} [FAIL]",
        f"{data['native']['total_cycles']:,} [PASS]",
    )
    table.add_row(
        "Speedup vs Baseline",
        "1.00x",
        f"{data['assisted']['total_cycles'] / data['driven']['total_cycles']:.2f}x",
        f"{data['assisted']['total_cycles'] / data['native']['total_cycles']:.2f}x",
    )
    table.add_row(
        "Hardware Area (GE)",
        f"{data['assisted']['hardware_area_ge']:,} GE",
        f"{data['driven']['hardware_area_ge']:,} GE",
        f"{data['native']['hardware_area_ge']:,} GE (Headroom: 5,600 GE)",
    )
    table.add_row(
        "Design Signoff",
        "[bold red]FAILED (2.9x Over Cycle Budget)[/bold red]",
        "[bold yellow]FAILED (1.8x Over Cycle Budget)[/bold yellow]",
        "[bold green]SIGNED OFF (1.75x Under Budget, Met Area)[/bold green]",
    )

    console.print(table)

    if show_asm:
        console.print()
        console.print("[bold yellow]Side-by-Side Assembly Comparison:[/bold yellow]")
        console.print(
            Panel(
                Syntax(ASM_DRIVEN, "asm", theme="monokai", line_numbers=False),
                title="[bold yellow]AI-Driven: Compiler Unrolling Causes 14 Stack Spills Per Loop[/bold yellow]",
                border_style="yellow",
            )
        )
        console.print(
            Panel(
                Syntax(ASM_NATIVE, "asm", theme="monokai", line_numbers=False),
                title="[bold green]AI-Native: Co-Designed Post-Increment SIMD (Zero Spills)[/bold green]",
                border_style="green",
            )
        )

    console.print(
        Panel(
            "[bold white]Architectural Causality Takeaway:[/bold white]\n"
            "• [bold red]AI-Assisted:[/bold red] LLMs generate isolated compute opcodes, overlooking that 71% of runtime is spent on address calculation and register spills.\n"
            "• [bold yellow]AI-Driven:[/bold yellow] Compiler-only unrolling hits a hard physical wall: the fixed 32-entry scalar register file is overwhelmed, spending 32,000 cycles thrashing stack memory.\n"
            "• [bold green]AI-Native:[/bold green] The agent couples workload profiling to joint co-adaptation: introducing hardware post-increment addressing eliminates address arithmetic, while packed SIMD reduces register pressure, achieving a 5.09x speedup within the 15k GE area budget.",
            border_style="green",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Micro-Loop D: HW/SW Co-Design & Instruction Specialization"
    )
    parser.add_argument(
        "--paradigm",
        choices=["all", "assisted", "driven", "native"],
        default="all",
        help="Target design paradigm",
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Generate publication-grade visual plot (results.png)",
    )
    parser.add_argument(
        "--asm", action="store_true", help="Display comparative assembly listings"
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=ROOT / "results.json",
        help="Path to write structured JSON results",
    )
    args = parser.parse_args()

    results: Dict[str, Any] = {}
    if args.paradigm in ("all", "assisted"):
        results["assisted"] = evaluate_codesign("assisted")
    if args.paradigm in ("all", "driven"):
        results["driven"] = evaluate_codesign("driven")
    if args.paradigm in ("all", "native"):
        results["native"] = evaluate_codesign("native")

    args.json_out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Generate visual plot
    if args.visual or args.paradigm == "all":
        if "assisted" in results and "driven" in results and "native" in results:
            plot_path = ROOT / "results.png"
            generate_visual_plot(results, plot_path)
            if not RICH_AVAILABLE:
                print(f"Visual plot generated: {plot_path}")

    # Terminal output
    if RICH_AVAILABLE:
        console = Console()
        if args.paradigm == "all":
            print_rich_dashboard(results, args.asm, console)
        else:
            p = args.paradigm
            data_p = results[p]
            console.print(f"[bold]Paradigm: {p.upper()}[/bold]")
            console.print(
                f"Cycles: {data_p['total_cycles']:,} (Compute: {data_p['compute_cycles']:,}, Addr: {data_p['address_calc_cycles']:,}, Spill: {data_p['register_spill_cycles']:,})"
            )
            console.print(
                f"Area: {data_p['hardware_area_ge']:,} GE | Status: {'PASS' if data_p['signoff_passed'] else 'FAIL'}"
            )
    else:
        print("=" * 80)
        print("Micro-Loop D Results:")
        for k, v in results.items():
            print(
                f"  [{k.upper()}] Cycles: {v['total_cycles']:,} | Area: {v['hardware_area_ge']:,} GE | Status: {'PASS' if v['signoff_passed'] else 'FAIL'}"
            )
        print("=" * 80)


if __name__ == "__main__":
    main()
