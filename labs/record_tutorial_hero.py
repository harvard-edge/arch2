#!/usr/bin/env python3
"""
Architecture 2.0: Automated Hero Tutorial Video Generator
=========================================================
Records a high-definition, macOS-styled terminal screencast of the Hero
Tutorial demonstration (Micro-Loop B: 500 MHz RTL Timing Closure in SKY130).

Demonstrates the 4-stage narrative arc:
  - Stage 1: The Physical Contract (500 MHz target, 2.000 ns period in SKY130)
  - Stage 2: AI-Assisted Mirage (Open-loop prompt, 32-bit ripple carry, -600 ps WNS failure)
  - Stage 3: AI-Driven Plateau (Gate-sizing asymptote, -72 ps WNS failure)
  - Stage 4: AI-Native Breakthrough (Carry-Save arithmetic, +1.450 ns slack, 1000/1000 formal match)
  - Stage 5: Grand Synthesis Matrix (0/4 vs 0/4 vs 4/4 across all physical loops)

Exports:
  - www/videos/workbench_tutorial_hero.webm
  - www/videos/workbench_tutorial_hero.mp4
"""

import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.columns import Columns

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = ROOT / "www" / "videos"
RAW_DIR = VIDEOS_DIR / "hero_raw"

sys.path.insert(0, str(ROOT / "labs"))
import tutorial


def render_rich_html(render_fn, width=86) -> str:
    """Render a Rich callback to an HTML string with inline styling."""
    c = Console(
        record=True,
        width=width,
        force_terminal=True,
        color_system="truecolor",
    )
    render_fn(c)
    return c.export_html(inline_styles=True, code_format="{code}")


def get_hero_segments():
    """Pre-render all Rich terminal outputs for the Hero tutorial into styled HTML snippets."""

    # 1. Master Title Banner
    def render_header(c: Console):
        header_text = Text()
        header_text.append(" ARCHITECTURE 2.0 ", style="bold white on blue")
        header_text.append(" • ", style="dim")
        header_text.append("LIVE WORKSHOP TUTORIAL\n", style="bold cyan")
        header_text.append(
            "Micro-Loop B: RTL Generation, Synthesis & Timing Closure\n",
            style="bold white",
        )
        header_text.append(
            "SkyWater SKY130 (130nm) • 500 MHz Target Clock • Bit-Exact Equivalence",
            style="dim white",
        )
        c.print(
            Panel(
                header_text,
                border_style="bright_blue",
                box=box.ROUNDED,
                width=86,
            )
        )

    # 2. Stage 1: The Physical Contract
    def render_stage1(c: Console):
        c.print(
            Panel(
                "[bold cyan]STAGE 1: THE PHYSICAL SILICON CONTRACT[/bold cyan]\n"
                "[bold white]Target Microarchitecture:[/bold white] Systolic Processing Element (PE) Accumulator\n"
                "[bold white]Process Technology:[/bold white] SkyWater SKY130 (130nm Bulk CMOS, 1.8V, TT corner)\n"
                "[bold white]Required Clock Frequency:[/bold white] 500.0 MHz ([bold yellow]Target Clock Period: 2.000 ns[/bold yellow])\n"
                "[bold white]Hard Physical Constraints:[/bold white]\n"
                "  • Setup Slack: Worst Negative Slack (WNS) ≥ 0.000 ns (Zero Violations)\n"
                "  • Sequential Overhead: T_cq (120 ps) + T_setup (80 ps) = 200 ps guardband\n"
                "  • Max Datapath Arrival: T_datapath ≤ 1.800 ns\n"
                "  • Formal Equivalence: 1,000 randomized simulation vectors must match bit-exact",
                title="[bold cyan]1. Physical Design Contract[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
                width=86,
            )
        )
        c.print(
            Panel(
                tutorial.render_horizontal_gauge(
                    "Clock Period", 2.000, 2.000, "ns", is_delay=False
                ),
                title="Physical Clock Period Budget",
                border_style="dim",
                box=box.ROUNDED,
                width=86,
            )
        )

    # 3. Stage 2: AI-Assisted (Open-Loop Mirage)
    def render_stage2(c: Console):
        c.print(
            Panel(
                "[bold red]STAGE 2: AI-ASSISTED (OPEN-LOOP PROMPT GENERATION)[/bold red]\n"
                '[dim]Prompt:[/dim] [italic white]"Write a 32-bit accumulator for a 500 MHz PE in SkyWater 130nm."[/italic white]\n'
                "[bold green]✔ LLM Generation Status:[/bold green] Syntactically Valid Verilog (0 compiler warnings)\n"
                "[bold red]✖ Physical Signoff Gate: REJECTED AT LOGIC SYNTHESIS[/bold red]",
                title="[bold red]2. AI-Assisted Mirage[/bold red]",
                border_style="red",
                box=box.ROUNDED,
                width=86,
            )
        )
        naive_code = (
            "// AI-Assisted Generated Verilog (pe_accumulator_naive.v)\n"
            "always @(posedge clk or posedge rst) begin\n"
            "  if (rst)      acc_out <= 32'b0;\n"
            "  else if (en)  acc_out <= acc_out + data_in; // 32-bit serial carry chain!\n"
            "end"
        )
        c.print(
            Panel(
                Syntax(naive_code, "verilog", theme="monokai", line_numbers=True),
                title="Generated RTL",
                border_style="dim",
                box=box.ROUNDED,
                width=86,
            )
        )
        c.print(
            Panel(
                tutorial.render_horizontal_gauge(
                    "Datapath Delay", 2.600, 2.000, "ns", is_delay=True
                ),
                title="Physical Timing Failure: Setup Slack Violated",
                border_style="red",
                box=box.ROUNDED,
                width=86,
            )
        )
        c.print(
            Panel(
                "[bold red]✖ WORST NEGATIVE SLACK (WNS): -0.600 ns (-600 ps violation)[/bold red]\n"
                "[bold white]Physical Root Cause:[/bold white]\n"
                "• Yosys synthesized 32 full-adder stages in a circular register feedback loop.\n"
                "• Bit 31 cannot compute until carry ripples through bits 0 to 30 (32 × 75 ps = 2.40 ns).\n"
                "• Total datapath arrival: 2.40 ns + 0.20 ns sequential margin = 2.600 ns > 2.000 ns ceiling.",
                title="[bold red]EDA Timing Diagnostic[/bold red]",
                border_style="red",
                box=box.ROUNDED,
                width=86,
            )
        )

    # 4. Stage 3: AI-Driven (Single-Layer Sizing Plateau)
    def render_stage3(c: Console):
        c.print(
            Panel(
                "[bold yellow]STAGE 3: AI-DRIVEN (CLOSED-LOOP TOOL OPTIMIZATION SWEEP)[/bold yellow]\n"
                "[dim]Strategy:[/dim] Iterative gate sizing, buffer tree insertion, and Boolean restructuring.\n"
                "[bold yellow]⚠ Outcome: STALLED AT STRUCTURAL ASYMPTOTE (-72 ps slack deficit)[/bold yellow]",
                title="[bold yellow]3. AI-Driven Plateau[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
                width=86,
            )
        )
        sweep_table = Table(
            box=box.SIMPLE_HEAD,
            header_style="bold yellow",
            border_style="dim",
            width=84,
        )
        sweep_table.add_column("Iteration", justify="center")
        sweep_table.add_column("Sizing & Buffering Action", justify="left")
        sweep_table.add_column("Logic Depth", justify="center")
        sweep_table.add_column("Arrival", justify="right")
        sweep_table.add_column("WNS Slack", justify="right")
        sweep_table.add_column("Status", justify="center")

        sweep_table.add_row(
            "Iter 1",
            "Baseline 1X drive cells",
            "32 stages",
            "2.600 ns",
            "-0.600 ns",
            "[red]FAIL[/red]",
        )
        sweep_table.add_row(
            "Iter 4",
            "Upsize carry gates to 2X",
            "30 stages",
            "2.410 ns",
            "-0.410 ns",
            "[red]FAIL[/red]",
        )
        sweep_table.add_row(
            "Iter 12",
            "Insert high-drive buffers (4X/8X)",
            "28 stages",
            "2.190 ns",
            "-0.190 ns",
            "[red]FAIL[/red]",
        )
        sweep_table.add_row(
            "Iter 25",
            "Carry-skip clustering + maximum drive",
            "26 stages",
            "2.072 ns",
            "-0.072 ns",
            "[bold yellow]PLATEAU[/bold yellow]",
        )
        c.print(sweep_table)

        c.print(
            Panel(
                tutorial.render_horizontal_gauge(
                    "Datapath Delay", 2.072, 2.000, "ns", is_delay=True
                ),
                title="The Sizing Asymptote: Delay Ceases to Decrease",
                border_style="yellow",
                box=box.ROUNDED,
                width=86,
            )
        )
        c.print(
            Panel(
                "[bold yellow]⚠ THE PHYSICAL SIZING ASYMPTOTE EXPLAINED:[/bold yellow]\n"
                "• Sizing up transistors reduces resistance Ron, but increases parasitic gate capacitance Cin.\n"
                "• In a serial ripple-carry chain, stage k drives stage k+1. Sizing stage k+1 loads stage k!\n"
                "• The optimizer hits the Logical Effort intrinsic delay limit: d = g*h + p (p cannot be sized away).\n"
                "• Local parameter sweeps within a fixed abstraction cannot break an O(N) carry recurrence.",
                title="[bold yellow]Physical Limits of Local Search[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
                width=86,
            )
        )

    # 5. Stage 4: AI-Native (Cross-Layer Carry-Save Breakthrough)
    def render_stage4(c: Console):
        c.print(
            Panel(
                "[bold green]STAGE 4: AI-NATIVE (CROSS-LAYER CO-ADAPTATION)[/bold green]\n"
                "[bold white]Physical Rejection Feedback:[/bold white] Ripple carry propagation causes setup timing failure.\n"
                "[bold green]Cross-Domain Action:[/bold green] Refactor mathematical representation to Redundant Carry-Save Arithmetic (CSA).\n"
                "[bold green]✔ Physical Signoff Gate: COMPLETE TIMING CLOSURE & BIT-EXACT VERIFICATION[/bold green]",
                title="[bold green]4. AI-Native Breakthrough[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                width=86,
            )
        )

        left_code = (
            "// AI-Assisted (Two's Complement)\n"
            "always @(posedge clk) begin\n"
            "  if (valid_in)\n"
            "    // 32 FULL ADDERS IN LOOP\n"
            "    acc <= acc + in_val;\n"
            "end"
        )
        right_code = (
            "// AI-Native (Carry-Save CSA)\n"
            "assign s = sum_r ^ carry_r ^ in_val;\n"
            "assign c = (sum_r & carry_r) | ...;\n"
            "always @(posedge clk) begin\n"
            "  // 1 FULL ADDER IN LOOP!\n"
            "  sum_r   <= s;\n"
            "  carry_r <= {c[30:0], 1'b0};\n"
            "end\n"
            "assign acc = sum_r + carry_r;"
        )
        panel_left = Panel(
            Syntax(left_code, "verilog", theme="monokai", line_numbers=False),
            title="Before: Two's Complement",
            border_style="red",
            width=41,
        )
        panel_right = Panel(
            Syntax(right_code, "verilog", theme="monokai", line_numbers=False),
            title="After: Redundant Carry-Save",
            border_style="green",
            width=43,
        )
        c.print(Columns([panel_left, panel_right]))

        c.print(
            Panel(
                tutorial.render_horizontal_gauge(
                    "Datapath Delay", 0.550, 2.000, "ns", is_delay=True
                ),
                title="AI-Native Datapath Delay vs Clock Ceiling",
                border_style="green",
                box=box.ROUNDED,
                width=86,
            )
        )

        comp_table = Table(
            title="Grand Signoff Matrix: PE Accumulator at 500 MHz",
            box=box.ROUNDED,
            header_style="bold green",
            border_style="dim",
            width=86,
        )
        comp_table.add_column("Design Paradigm", justify="left")
        comp_table.add_column("Logic Depth", justify="center")
        comp_table.add_column("Delay (ns)", justify="center")
        comp_table.add_column("WNS Slack", justify="center")
        comp_table.add_column("Signoff Verdict", justify="center")

        comp_table.add_row(
            "AI-Assisted (Open)",
            "32 stages",
            "2.600 ns",
            "-0.600 ns",
            "[red]FAIL (Violated)[/red]",
        )
        comp_table.add_row(
            "AI-Driven (Sizing)",
            "26 stages",
            "2.072 ns",
            "-0.072 ns",
            "[yellow]FAIL (Plateau)[/yellow]",
        )
        comp_table.add_row(
            "AI-Native (Co-Adapt)",
            "1 stage",
            "0.550 ns",
            "+1.450 ns",
            "[bold green]CLOSED (Signoff)[/bold green]",
        )
        c.print(comp_table)

        c.print(
            Panel(
                "[bold green]✔ FORMAL EQUIVALENCE CLOSURE RECEIPT:[/bold green]\n"
                "• Test Engine: Icarus Verilog 12.0 + VVP Simulation Harness\n"
                "• Functional Equivalence: [bold white]1,000 / 1,000 random vectors BIT-EXACT MATCH[/bold white]\n"
                "• Critical Path: Truncated from 32 stages to a single full adder (0.35 ns logic + 0.20 ns margin = 0.55 ns)\n"
                "• Clock Margin: [bold green]+1,450 ps setup slack margin (72.5% headroom for PVT corners)[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                width=86,
            )
        )

    # 6. Stage 5: Grand Synthesis Matrix
    def render_stage5(c: Console):
        c.print(
            Panel(
                "[bold white on blue] ARCHITECTURE 2.0: MASTER SYNTHESIS COMPLETE [/bold white on blue]\n"
                "[bold cyan]Cross-Layer Verification Matrix Across All Four Physical Micro-Loops[/bold cyan]",
                border_style="bright_blue",
                box=box.ROUNDED,
                width=86,
            )
        )
        matrix = Table(
            title="Physical Signoff Matrix: AI-Assisted vs. AI-Driven vs. AI-Native",
            box=box.ROUNDED,
            header_style="bold cyan",
            border_style="dim",
            width=86,
        )
        matrix.add_column("Micro-Loop Domain", justify="left")
        matrix.add_column("AI-Assisted", justify="center")
        matrix.add_column("AI-Driven", justify="center")
        matrix.add_column("AI-Native", justify="center")

        matrix.add_row(
            "Loop A: Microarch\n[dim]Memory Wall[/dim]",
            "FAIL\n[dim]16x64 OS[/dim]",
            "FAIL (Choke)\n[dim]32x32 OS[/dim]",
            "[bold green]PASS (2.73x)[/bold green]\n[dim]8x128 WS[/dim]",
        )
        matrix.add_row(
            "Loop B: RTL Timing\n[dim]500 MHz Closure[/dim]",
            "FAIL (-600 ps)\n[dim]32-bit Ripple[/dim]",
            "FAIL (-72 ps)\n[dim]Sized Ripple[/dim]",
            "[bold green]CLOSED (+1.45 ns)[/bold green]\n[dim]Carry-Save FA[/dim]",
        )
        matrix.add_row(
            "Loop C: Floorplan\n[dim]RUDY & DRC[/dim]",
            "FAIL (18 DRCs)\n[dim]Unplaced[/dim]",
            "FAIL (12 DRCs)\n[dim]HPWL Choke[/dim]",
            "[bold green]SIGNED OFF (0 DRC)[/bold green]\n[dim]Pin/Avenue Co-Adapt[/dim]",
        )
        matrix.add_row(
            "Loop D: HW/SW\n[dim]XR Kernel Profiling[/dim]",
            "FAIL (145k cyc)\n[dim]Scalar custom.dot[/dim]",
            "FAIL (92k cyc)\n[dim]32k Spills[/dim]",
            "[bold green]SIGNED OFF (28.5k)[/bold green]\n[dim]SIMD-4 Post-Inc[/dim]",
        )
        matrix.add_row(
            "[bold white]Overall Signoff[/bold white]",
            "[bold red]0 / 4 PASSED (0%)[/bold red]",
            "[bold yellow]0 / 4 PASSED (0%)[/bold yellow]",
            "[bold green]4 / 4 PASSED (100%)[/bold green]",
        )
        c.print(matrix)

        c.print(
            Panel(
                "[bold white]THE CENTRAL DISCOVERY OF ARCHITECTURE 2.0:[/bold white]\n"
                "1. [bold red]AI-Assisted (Open-Loop):[/bold red] Generates fluent, plausible syntax that universally fails in silicon (0/4 passed).\n"
                "2. [bold yellow]AI-Driven (Tool Sweeps):[/bold yellow] Sweeps local EDA parameters but hits fundamental mathematical and physical plateaus (0/4 passed).\n"
                "3. [bold green]AI-Native (Cross-Layer):[/bold green] Closes the physical feedback loop across abstraction boundaries to achieve complete verified signoff (4/4 passed).",
                border_style="bright_green",
                box=box.ROUNDED,
                width=86,
            )
        )

    return {
        "header": render_rich_html(render_header),
        "stage1": render_rich_html(render_stage1),
        "stage2": render_rich_html(render_stage2),
        "stage3": render_rich_html(render_stage3),
        "stage4": render_rich_html(render_stage4),
        "stage5": render_rich_html(render_stage5),
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body {
    margin: 0;
    padding: 0;
    background: #0f172a;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    overflow: hidden;
  }
  .terminal-window {
    width: 1340px;
    height: 860px;
    background: #181825;
    border-radius: 12px;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.1);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative;
  }
  .window-header {
    height: 42px;
    background: #11111b;
    display: flex;
    align-items: center;
    padding: 0 16px;
    border-bottom: 1px solid #313244;
    user-select: none;
  }
  .window-dots {
    display: flex;
    gap: 8px;
  }
  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }
  .dot-red { background: #f38ba8; }
  .dot-yellow { background: #f9e2af; }
  .dot-green { background: #a6e3a1; }
  .window-title {
    flex: 1;
    text-align: center;
    font-size: 13px;
    color: #a6adc8;
    font-weight: 600;
  }
  .terminal-body {
    flex: 1;
    padding: 20px 24px;
    overflow-y: auto;
    color: #cdd6f4;
    font-size: 12.8px;
    line-height: 1.34;
    white-space: pre;
  }
  .prompt-line {
    display: flex;
    align-items: baseline;
    margin-bottom: 8px;
  }
  .prompt-badge {
    color: #89b4fa;
    font-weight: bold;
    margin-right: 10px;
  }
  .command-text {
    color: #f5e0dc;
    font-weight: 600;
  }
  .cursor {
    display: inline-block;
    width: 8px;
    height: 15px;
    background: #f5e0dc;
    margin-left: 4px;
    animation: blink 1s infinite;
    vertical-align: middle;
  }
  @keyframes blink {
    0%, 49% { opacity: 1; }
    50%, 100% { opacity: 0; }
  }
  /* Callout overlay card */
  .workshop-overlay {
    position: absolute;
    bottom: 24px;
    right: 24px;
    max-width: 440px;
    padding: 16px 20px;
    background: rgba(17, 17, 27, 0.94);
    backdrop-filter: blur(12px);
    color: #ffffff;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.18);
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.5);
    z-index: 9999;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    transform: translateY(0);
    opacity: 1;
  }
  .workshop-overlay.hidden {
    transform: translateY(20px);
    opacity: 0;
    pointer-events: none;
  }
  .workshop-tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 3px 8px;
    border-radius: 4px;
    margin-bottom: 6px;
  }
  .tag-cyan { background: #0891b2; color: #cffafe; }
  .tag-red { background: #b91c1c; color: #fee2e2; }
  .tag-amber { background: #b45309; color: #fef3c7; }
  .tag-green { background: #15803d; color: #dcfce7; }
  .tag-purple { background: #6d28d9; color: #ede9fe; }
  .workshop-title {
    font-size: 15px;
    font-weight: 700;
    margin: 0 0 6px 0;
    color: #f8fafc;
  }
  .workshop-desc {
    font-size: 12.5px;
    color: #cbd5e1;
    line-height: 1.45;
    margin: 0;
    white-space: normal;
  }
</style>
</head>
<body>

<div class="terminal-window">
  <div class="window-header">
    <div class="window-dots">
      <div class="dot dot-red"></div>
      <div class="dot dot-yellow"></div>
      <div class="dot dot-green"></div>
    </div>
    <div class="window-title">vj@arch2-macbook: ~/GitHub/Arch2 (interactive tutorial runner)</div>
  </div>
  <div class="terminal-body" id="term"></div>

  <div id="workshop-callout" class="workshop-overlay hidden">
    <span id="ws-tag" class="workshop-tag tag-cyan">Stage 1</span>
    <h4 id="ws-title" class="workshop-title">Title</h4>
    <p id="ws-desc" class="workshop-desc">Description</p>
  </div>
</div>

<script>
const term = document.getElementById('term');
const callout = document.getElementById('workshop-callout');
const wsTag = document.getElementById('ws-tag');
const wsTitle = document.getElementById('ws-title');
const wsDesc = document.getElementById('ws-desc');

window.typeCommand = function(text, callback) {
  const line = document.createElement('div');
  line.className = 'prompt-line';
  line.innerHTML = '<span class="prompt-badge">vj@arch2:~/Arch2$</span> <span class="command-text"></span><span class="cursor"></span>';
  term.appendChild(line);
  const cmdSpan = line.querySelector('.command-text');
  const cursor = line.querySelector('.cursor');

  let i = 0;
  function typeChar() {
    if (i < text.length) {
      cmdSpan.textContent += text.charAt(i);
      i++;
      setTimeout(typeChar, 28);
    } else {
      setTimeout(() => {
        cursor.remove();
        if (callback) callback();
      }, 350);
    }
  }
  typeChar();
};

window.appendHtml = function(rawHtml) {
  const node = document.createElement('div');
  node.innerHTML = rawHtml;
  term.appendChild(node);
  term.scrollTop = term.scrollHeight;
};

window.clearScreen = function() {
  term.innerHTML = '';
};

window.showCallout = function(tag, tagClass, title, desc) {
  wsTag.textContent = tag;
  wsTag.className = 'workshop-tag ' + tagClass;
  wsTitle.textContent = title;
  wsDesc.textContent = desc;
  callout.classList.remove('hidden');
};

window.hideCallout = function() {
  callout.classList.add('hidden');
};
</script>

</body>
</html>
"""


def record_hero_video():
    """Renders and records the hero tutorial demonstration."""
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Pre-rendering Hero tutorial Rich components to HTML...")
    segments = get_hero_segments()

    html_file = RAW_DIR / "hero_terminal.html"
    html_file.write_text(HTML_TEMPLATE, encoding="utf-8")

    print("Launching Playwright to record Hero tutorial terminal screencast...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 920},
            record_video_dir=str(RAW_DIR),
            record_video_size={"width": 1400, "height": 920},
        )
        page = context.new_page()
        page.goto(html_file.as_uri())
        time.sleep(1.0)

        # Scene 1: Type command and render Title Banner & Stage 1
        page.evaluate("window.typeCommand('./arch2 tutorial --hero')")
        time.sleep(1.8)

        page.evaluate(f"window.appendHtml({json.dumps(segments['header'])})")
        time.sleep(1.2)

        page.evaluate(f"window.appendHtml({json.dumps(segments['stage1'])})")
        page.evaluate(
            """window.showCallout(
                'STAGE 1: THE CONTRACT', 'tag-cyan',
                '500 MHz Target in SkyWater SKY130 (130nm)',
                'Silicon demands setup closure within 2.000 ns. Physics cannot be negotiated with using soft waivers or prompt tricks.'
            )"""
        )
        time.sleep(5.0)

        # Scene 2: Stage 2 - AI-Assisted Mirage (Red Failure)
        page.evaluate("window.clearScreen()")
        page.evaluate(f"window.appendHtml({json.dumps(segments['stage2'])})")
        page.evaluate(
            """window.showCallout(
                'STAGE 2: AI-ASSISTED MIRAGE', 'tag-red',
                'Syntactically Valid RTL Fails in Silicon',
                'The LLM generated clean Verilog in 2 seconds, but placed a circular 32-bit carry recurrence in a single clock cycle (-600 ps WNS).'
            )"""
        )
        time.sleep(5.5)

        # Scene 3: Stage 3 - AI-Driven Plateau (Yellow Asymptote)
        page.evaluate("window.clearScreen()")
        page.evaluate(f"window.appendHtml({json.dumps(segments['stage3'])})")
        page.evaluate(
            """window.showCallout(
                'STAGE 3: THE ASYMPTOTE', 'tag-amber',
                'Tool Sizing Sweeps Hit a Physical Wall',
                'Automated transistor sizing shaves 528 ps but plateaus at -72 ps. Local optimizers cannot change O(N) carry propagation topology.'
            )"""
        )
        time.sleep(5.5)

        # Scene 4: Stage 4 - AI-Native Breakthrough (Green Signoff)
        page.evaluate("window.clearScreen()")
        page.evaluate(f"window.appendHtml({json.dumps(segments['stage4'])})")
        page.evaluate(
            """window.showCallout(
                'STAGE 4: AI-NATIVE BREAKTHROUGH', 'tag-green',
                'Cross-Layer Carry-Save Arithmetic Refactoring',
                'Switching to Carry-Save Arithmetic collapses logic depth from 32 to 1 stage: +1.450 ns slack and 1,000/1,000 formal equivalence.'
            )"""
        )
        time.sleep(6.5)

        # Scene 5: Stage 5 - Grand Synthesis Matrix
        page.evaluate("window.clearScreen()")
        page.evaluate(f"window.appendHtml({json.dumps(segments['stage5'])})")
        page.evaluate(
            """window.showCallout(
                'SYNTHESIS COMPLETE', 'tag-purple',
                '0/4 (Single-Layer) vs. 4/4 (AI-Native)',
                'From systolic memory walls to physical routing DRCs, signoff-grade silicon requires cross-layer co-adaptation.'
            )"""
        )
        time.sleep(5.5)

        page.close()
        context.close()
        browser.close()

    raw_videos = list(RAW_DIR.glob("*.webm"))
    if not raw_videos:
        print("Error: No raw hero video captured.")
        return

    raw_video = raw_videos[0]
    out_webm = VIDEOS_DIR / "workbench_tutorial_hero.webm"
    out_mp4 = VIDEOS_DIR / "workbench_tutorial_hero.mp4"

    shutil.copy2(raw_video, out_webm)
    print(f"Captured Playwright WebM hero video: {out_webm}")

    ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    if os.path.exists(ffmpeg_bin):
        print(f"Converting WebM to high-quality MP4 using {ffmpeg_bin}...")
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(out_webm),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            str(out_mp4),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_mp4.exists():
            print(f"Successfully rendered workshop MP4 hero video: {out_mp4}")
        else:
            print(f"FFmpeg conversion warning: {res.stderr}")

    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)


if __name__ == "__main__":
    record_hero_video()
