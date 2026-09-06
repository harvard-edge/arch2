"""Generate fig-architecture-20-loop SVG, PDF, and PNG conforming to book styling."""

from pathlib import Path
import subprocess

SCRIPT_DIR = Path(__file__).resolve().parent

SVG_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 425" role="img" aria-labelledby="loop-title loop-desc">
  <title id="loop-title">The Architecture 2.0 execution loop and system boundaries</title>
  <desc id="loop-desc">An input boundary carries system intent, physical bounds, and objective criteria from the architect into an autonomous multi-tool execution loop. Inside the loop, AI agents across architecture, RTL, software, verification, and optimization produce candidate designs evaluated by tools and measured across performance, energy, area, thermal, and carbon. Measurements feed back into candidate search and exit to the output boundary, where commitment authority audits evidence and decides on physical fabrication.</desc>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#333333"/>
    </marker>
    <marker id="arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#1E9E48"/>
    </marker>
    <style>
      .font { font-family: Arial, Helvetica, sans-serif; fill: #20252B; }
      .mono { font-family: "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace; }
      .group { font-size: 11px; font-weight: 700; fill: #59636D; letter-spacing: 0.55px; }
      .label { font-size: 13.5px; font-weight: 700; fill: #20252B; }
      .sub { font-size: 11.2px; fill: #444444; }
      .bullet { font-size: 11px; fill: #333333; }
      .tree-text { font-size: 11px; font-family: "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace; fill: #20252B; }
      .loop-text { font-size: 10.8px; font-weight: 700; fill: #1E9E48; }

      .panel { fill: #F8FAFC; stroke: #9AA8B5; stroke-width: 1.2; }
      .input { fill: #E4F1F6; stroke: #1683A6; stroke-width: 1.5; }
      .agents { fill: #F0ECFA; stroke: #6A4FC7; stroke-width: 1.5; }
      .design { fill: #FBF0DE; stroke: #E68A17; stroke-width: 1.5; }
      .tools { fill: #F5F8FA; stroke: #9AA8B5; stroke-width: 1.5; }
      .measure { fill: #E7F5EC; stroke: #1E9E48; stroke-width: 1.5; }
      .decision { fill: #FBEDF4; stroke: #D24D96; stroke-width: 1.5; }

      .edge { fill: none; stroke: #333333; stroke-width: 1.8; stroke-linecap: square; stroke-linejoin: miter; marker-end: url(#arrow); }
      .loop { fill: none; stroke: #1E9E48; stroke-width: 1.8; stroke-dasharray: 6 4; stroke-linecap: square; stroke-linejoin: miter; marker-end: url(#arrow-green); }
      .tree-line { stroke: #59636D; stroke-width: 1.2; fill: none; stroke-linecap: square; stroke-linejoin: miter; }
      .divider-blue { stroke: #1683A6; stroke-width: 0.8; }
      .divider-pink { stroke: #D24D96; stroke-width: 0.8; }
    </style>
  </defs>

  <rect width="960" height="425" fill="#FFFFFF"/>

  <g class="font">
    <!-- =================================================================== -->
    <!-- Group Labels                                                        -->
    <!-- =================================================================== -->
    <text class="group" x="115" y="32" text-anchor="middle">INPUT BOUNDARY</text>
    <text class="group" x="495" y="32" text-anchor="middle">AUTONOMOUS MULTI-TOOL EXECUTION LOOP</text>
    <text class="group" x="865" y="32" text-anchor="middle">OUTPUT BOUNDARY</text>

    <!-- =================================================================== -->
    <!-- INPUT BOUNDARY: goal                                                -->
    <!-- =================================================================== -->
    <rect class="input" x="25" y="44" width="180" height="258"/>
    <text class="label mono" x="115" y="70" text-anchor="middle">goal</text>
    <text class="sub" x="115" y="88" text-anchor="middle" font-weight="700">Problem formulation</text>
    <line class="divider-blue" x1="37" y1="98" x2="193" y2="98"/>

    <text class="bullet" x="37" y="120">&#x2022; system intent + workload</text>
    <text class="bullet" x="37" y="140">&#x2022; physical limits (power, area)</text>
    <text class="bullet" x="37" y="160">&#x2022; thermal dissipation budget</text>
    <text class="bullet" x="37" y="180">&#x2022; objective / loss criteria</text>
    <text class="bullet" x="37" y="200">&#x2022; anti-gaming constraints</text>

    <line class="divider-blue" x1="37" y1="240" x2="193" y2="240"/>
    <text class="sub" x="115" y="260" text-anchor="middle" font-weight="700">Human architect</text>
    <text class="sub" x="115" y="278" text-anchor="middle">frames question + bounds</text>

    <!-- Edge: goal -> AI agents -->
    <path class="edge" d="M 205 119 H 245"/>

    <!-- =================================================================== -->
    <!-- AUTONOMOUS EXECUTION LOOP PANEL                                     -->
    <!-- =================================================================== -->
    <rect class="panel" x="225" y="44" width="540" height="258"/>

    <!-- Return feedback loop line across top -->
    <path class="loop" d="M 687 100 V 62 H 305 V 98"/>
    <text class="loop-text" x="496" y="56" text-anchor="middle">feedback: measurements steer candidate refinement</text>

    <!-- Node 1: AI agents -->
    <rect class="agents" x="245" y="100" width="120" height="38"/>
    <text class="label mono" x="305" y="124" text-anchor="middle">AI agents</text>

    <!-- Tree under AI agents -->
    <line class="tree-line" x1="262" y1="138" x2="262" y2="246"/>
    <path class="tree-line" d="M 262 158 H 276"/>
    <text class="tree-text" x="282" y="162">architecture</text>
    <path class="tree-line" d="M 262 180 H 276"/>
    <text class="tree-text" x="282" y="184">RTL</text>
    <path class="tree-line" d="M 262 202 H 276"/>
    <text class="tree-text" x="282" y="206">software</text>
    <path class="tree-line" d="M 262 224 H 276"/>
    <text class="tree-text" x="282" y="228">verification</text>
    <path class="tree-line" d="M 262 246 H 276"/>
    <text class="tree-text" x="282" y="250">optimization</text>

    <!-- Edge: AI agents -> design -->
    <path class="edge" d="M 365 119 H 395"/>

    <!-- Node 2: design -->
    <rect class="design" x="395" y="100" width="85" height="38"/>
    <text class="label mono" x="437.5" y="124" text-anchor="middle">design</text>
    <text class="sub" x="437.5" y="156" text-anchor="middle">IRs, netlists,</text>
    <text class="sub" x="437.5" y="172" text-anchor="middle">parameters</text>

    <!-- Edge: design -> tools -->
    <path class="edge" d="M 480 119 H 510"/>

    <!-- Node 3: tools -->
    <rect class="tools" x="510" y="100" width="85" height="38"/>
    <text class="label mono" x="552.5" y="124" text-anchor="middle">tools</text>
    <text class="sub" x="552.5" y="156" text-anchor="middle">simulators, EDA,</text>
    <text class="sub" x="552.5" y="172" text-anchor="middle">signoff checks</text>

    <!-- Edge: tools -> measurements -->
    <path class="edge" d="M 595 119 H 625"/>

    <!-- Node 4: measurements -->
    <rect class="measure" x="625" y="100" width="125" height="38"/>
    <text class="label mono" x="687.5" y="124" text-anchor="middle">measurements</text>

    <!-- Tree under measurements -->
    <line class="tree-line" x1="642" y1="138" x2="642" y2="246"/>
    <path class="tree-line" d="M 642 158 H 656"/>
    <text class="tree-text" x="662" y="162">performance</text>
    <path class="tree-line" d="M 642 180 H 656"/>
    <text class="tree-text" x="662" y="184">energy</text>
    <path class="tree-line" d="M 642 202 H 656"/>
    <text class="tree-text" x="662" y="206">area</text>
    <path class="tree-line" d="M 642 224 H 656"/>
    <text class="tree-text" x="662" y="228">thermal</text>
    <path class="tree-line" d="M 642 246 H 656"/>
    <text class="tree-text" x="662" y="250">carbon</text>

    <!-- Edge: measurements -> commitment -->
    <path class="edge" d="M 750 119 H 785"/>

    <!-- =================================================================== -->
    <!-- OUTPUT BOUNDARY: commitment                                         -->
    <!-- =================================================================== -->
    <rect class="decision" x="785" y="44" width="160" height="258"/>
    <text class="label mono" x="865" y="70" text-anchor="middle">commitment</text>
    <text class="sub" x="865" y="88" text-anchor="middle" font-weight="700">Commitment authority</text>
    <line class="divider-pink" x1="797" y1="98" x2="933" y2="98"/>

    <text class="bullet" x="797" y="120">&#x2022; cross-tool evidence audit</text>
    <text class="bullet" x="797" y="140">&#x2022; artifact vs reality check</text>
    <text class="bullet" x="797" y="160">&#x2022; residual risk evaluation</text>
    <text class="bullet" x="797" y="180">&#x2022; corner margin signoff</text>
    <text class="bullet" x="797" y="200">&#x2022; mask capital allocation</text>

    <line class="divider-pink" x1="797" y1="240" x2="933" y2="240"/>
    <text class="sub" x="865" y="260" text-anchor="middle" font-weight="700">Named authority</text>
    <text class="sub" x="865" y="278" text-anchor="middle">retires decisions in-order</text>

    <!-- =================================================================== -->
    <!-- BOTTOM COMPARISON PANEL                                             -->
    <!-- =================================================================== -->
    <rect class="panel" x="25" y="320" width="920" height="85"/>
    <text class="group" x="40" y="340">HUMAN ROLE ACROSS DESIGN EPOCHS</text>

    <!-- Arch 1.0 -->
    <rect class="tools" x="40" y="348" width="420" height="46"/>
    <text class="label" x="52" y="367" font-size="12px">Architecture 1.0 (Manual execution):</text>
    <text class="sub" x="52" y="383">Engineer operates inside the loop drafting RTL, writing scripts, and tuning parameters.</text>

    <!-- Arch 2.0 -->
    <rect class="input" x="480" y="348" width="450" height="46"/>
    <text class="label" x="492" y="367" font-size="12px">Architecture 2.0 (Closed-loop system):</text>
    <text class="sub" x="492" y="383">Execution loop is automated; architect operates at the input and output boundaries.</text>
  </g>
</svg>
"""


def main() -> None:
    svg_path = SCRIPT_DIR / "fig-architecture-20-loop.svg"
    pdf_path = SCRIPT_DIR / "fig-architecture-20-loop.pdf"
    png_path = SCRIPT_DIR / "fig-architecture-20-loop.png"

    print(f"Writing SVG to {svg_path}...")
    svg_path.write_text(SVG_CONTENT.strip() + "\n", encoding="utf-8")

    print(f"Converting SVG to PDF via rsvg-convert -> {pdf_path}...")
    subprocess.run(
        ["rsvg-convert", "-f", "pdf", str(svg_path), "-o", str(pdf_path)],
        check=True,
    )

    print(f"Converting SVG to PNG (2160px width) via rsvg-convert -> {png_path}...")
    subprocess.run(
        ["rsvg-convert", "-w", "2160", str(svg_path), "-o", str(png_path)],
        check=True,
    )
    print("Done! All three format twins created successfully.")


if __name__ == "__main__":
    main()
