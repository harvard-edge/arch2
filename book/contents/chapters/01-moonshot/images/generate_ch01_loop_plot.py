"""Generate fig-architecture-20-loop SVG, PDF, and PNG with pristine layout."""

from pathlib import Path
import subprocess

SCRIPT_DIR = Path(__file__).resolve().parent

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 620" width="100%" height="100%" role="img">
  <title>The Architecture 2.0 Execution Loop and Human Bookends</title>
  <desc>Diagram showing the Architecture 2.0 execution loop with AI agents across architecture, RTL, software, verification, and optimization feeding design and tools to produce measurements across performance, energy, area, thermal, and carbon, highlighting how human architects migrate to the two bookends of intent formulation and commitment authority.</desc>
  <defs>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 1 L 9 5 L 0 9 Z" fill="#0284C7"/>
    </marker>
    <marker id="arrow-dark" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 1 L 9 5 L 0 9 Z" fill="#475569"/>
    </marker>
    <marker id="arrow-loop" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 1 L 9 5 L 0 9 Z" fill="#0D5C75"/>
    </marker>
    <marker id="arrow-commit" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 1 L 9 5 L 0 9 Z" fill="#D97706"/>
    </marker>
    <style>
      .font-sans { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
      .font-mono { font-family: "JetBrains Mono", "SF Mono", Menlo, Monaco, Consolas, monospace; }

      .main-title { font-size: 17px; font-weight: 700; fill: #0F172A; }
      .main-subtitle { font-size: 12px; font-weight: 400; fill: #475569; }

      .badge-text { font-size: 9.5px; font-weight: 700; fill: #FFFFFF; letter-spacing: 0.6px; text-transform: uppercase; }
      .card-title { font-size: 13px; font-weight: 700; fill: #0F172A; }
      .card-sub { font-size: 10.5px; font-weight: 400; fill: #475569; }

      .mono-title { font-size: 13.5px; font-weight: 700; fill: #0F172A; }
      .tree-text { font-size: 11.5px; font-weight: 500; fill: #334155; }

      .contrast-hdr { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; fill: #475569; }
      .contrast-body { font-size: 10.5px; font-weight: 400; fill: #334155; }

      .loop-label { font-size: 9.5px; font-weight: 700; fill: #FFFFFF; letter-spacing: 0.4px; text-transform: uppercase; }
    </style>
  </defs>

  <!-- Background -->
  <rect width="1080" height="620" fill="#FFFFFF"/>

  <!-- Main Title & Subtitle -->
  <text class="font-sans main-title" x="40" y="34">The Architecture 2.0 Loop and the Migration of Human Judgment</text>
  <text class="font-sans main-subtitle" x="40" y="52">Automating the inner multi-tool execution cycle relocates human engineering judgment to the input and output bookends</text>

  <!-- ===================================================================== -->
  <!-- BOOKEND 1 (INPUT): Human Architect - Goal Formulation                 -->
  <!-- ===================================================================== -->
  <g transform="translate(40, 75)">
    <!-- Container -->
    <rect width="200" height="395" rx="6" fill="#F0F9FF" stroke="#0284C7" stroke-width="1.6"/>
    <!-- Header -->
    <path d="M 0 6 Q 0 0 6 0 L 194 0 Q 200 0 200 6 L 200 32 L 0 32 Z" fill="#BAE6FD"/>
    <line x1="0" y1="32" x2="200" y2="32" stroke="#0284C7" stroke-width="1.2"/>

    <!-- Badge -->
    <rect x="12" y="6" width="94" height="19" rx="3" fill="#0284C7"/>
    <text class="font-sans badge-text" x="59" y="19.5" text-anchor="middle">INPUT BOOKEND</text>

    <text class="font-sans card-title" x="14" y="52">Problem Formulation</text>
    <text class="font-sans card-sub" x="14" y="68">Owned by the Human Architect</text>

    <line x1="14" y1="78" x2="186" y2="78" stroke="#CBD5E1" stroke-width="1"/>

    <!-- Core node 'goal' aligned horizontally with execution chain -->
    <rect x="14" y="92" width="172" height="42" rx="4" fill="#FFFFFF" stroke="#0284C7" stroke-width="1.6"/>
    <text class="font-mono mono-title" x="100" y="118" text-anchor="middle" fill="#0369A1">goal</text>

    <!-- Bullet points -->
    <g transform="translate(14, 154)">
      <circle cx="5" cy="6" r="2.5" fill="#0284C7"/>
      <text class="font-sans card-sub" x="15" y="10" font-weight="600" fill="#0F172A">System intent &amp; workload</text>
      <text class="font-sans card-sub" x="15" y="24">Target algorithms &amp; use cases</text>

      <circle cx="5" cy="46" r="2.5" fill="#0284C7"/>
      <text class="font-sans card-sub" x="15" y="50" font-weight="600" fill="#0F172A">Physical boundaries</text>
      <text class="font-sans card-sub" x="15" y="64">Thermal, power &amp; area envelopes</text>

      <circle cx="5" cy="86" r="2.5" fill="#0284C7"/>
      <text class="font-sans card-sub" x="15" y="90" font-weight="600" fill="#0F172A">Loss &amp; reward definition</text>
      <text class="font-sans card-sub" x="15" y="104">Multi-objective Pareto criteria</text>

      <circle cx="5" cy="126" r="2.5" fill="#0284C7"/>
      <text class="font-sans card-sub" x="15" y="130" font-weight="600" fill="#0F172A">Anti-gaming constraints</text>
      <text class="font-sans card-sub" x="15" y="144">Preventing proxy exploitation</text>
    </g>

    <rect x="14" y="325" width="172" height="54" rx="4" fill="#E0F2FE"/>
    <text class="font-sans card-sub" x="22" y="342" font-weight="600" fill="#0369A1">Role of the Architect:</text>
    <text class="font-sans card-sub" x="22" y="357" fill="#0369A1">Framing what problem to solve</text>
    <text class="font-sans card-sub" x="22" y="370" fill="#0369A1">and setting hard invariants.</text>
  </g>

  <!-- Straight Horizontal Pipeline Arrow: goal -> AI agents (y = 75 + 113 = 188) -->
  <path d="M 240 188 L 278 188" stroke="#0284C7" stroke-width="2.4" stroke-linecap="round" marker-end="url(#arrow-blue)"/>

  <!-- ===================================================================== -->
  <!-- CENTER: Autonomous Multi-Tool Execution Loop                          -->
  <!-- ===================================================================== -->
  <g transform="translate(280, 75)">
    <!-- Container -->
    <rect width="520" height="395" rx="6" fill="#F8FAFC" stroke="#0D5C75" stroke-width="1.6"/>
    <!-- Header -->
    <path d="M 0 6 Q 0 0 6 0 L 514 0 Q 520 0 520 6 L 520 32 L 0 32 Z" fill="#E2E8F0"/>
    <line x1="0" y1="32" x2="520" y2="32" stroke="#0D5C75" stroke-width="1.2"/>

    <!-- Badge -->
    <rect x="14" y="6" width="195" height="19" rx="3" fill="#0D5C75"/>
    <text class="font-sans badge-text" x="111.5" y="19.5" text-anchor="middle">AUTONOMOUS EXECUTION LOOP</text>
    <text class="font-sans card-sub" x="220" y="20" font-weight="600" fill="#334155">Iterative Search &amp; Verification (No Human in the Inner Loop)</text>

    <!-- Return feedback loop arrow over top -->
    <!-- Starts from top of measurements (x=432), goes up to y=46, curves left to x=72, curves down into AI agents (x=72, y=90) -->
    <path d="M 432 92 L 432 50 Q 432 40 422 40 L 82 40 Q 72 40 72 50 L 72 88" fill="none" stroke="#0D5C75" stroke-width="2" stroke-linecap="round" marker-end="url(#arrow-loop)"/>

    <!-- Loop pill badge cleanly centered over horizontal return path -->
    <rect x="155" y="29" width="194" height="22" rx="11" fill="#0D5C75"/>
    <text class="font-sans loop-label" x="252" y="44" text-anchor="middle">Feedback &amp; Candidate Mutation</text>

    <!-- Main execution sequence nodes (y=92 to match goal) -->
    <!-- 1. AI agents -->
    <g transform="translate(18, 92)">
      <rect width="110" height="42" rx="4" fill="#E4F1F6" stroke="#1683A6" stroke-width="1.5"/>
      <text class="font-mono mono-title" x="55" y="26" text-anchor="middle" fill="#0F172A">AI agents</text>

      <!-- Tree under AI agents -->
      <g transform="translate(20, 50)">
        <!-- Vertical stem -->
        <line x1="0" y1="0" x2="0" y2="128" stroke="#475569" stroke-width="1.4"/>

        <!-- Branch 1: architecture -->
        <path d="M 0 16 L 16 16" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="20">architecture</text>

        <!-- Branch 2: RTL -->
        <path d="M 0 44 L 16 44" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="48">RTL</text>

        <!-- Branch 3: software -->
        <path d="M 0 72 L 16 72" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="76">software</text>

        <!-- Branch 4: verification -->
        <path d="M 0 100 L 16 100" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="104">verification</text>

        <!-- Branch 5: optimization -->
        <path d="M 0 128 L 16 128" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="132">optimization</text>
      </g>
    </g>

    <!-- Arrow 1: agents -> design -->
    <path d="M 130 113 L 152 113" stroke="#475569" stroke-width="2" stroke-linecap="round" marker-end="url(#arrow-dark)"/>

    <!-- 2. design -->
    <g transform="translate(155, 92)">
      <rect width="84" height="42" rx="4" fill="#FFFFFF" stroke="#64748B" stroke-width="1.4"/>
      <text class="font-mono mono-title" x="42" y="26" text-anchor="middle" fill="#0F172A">design</text>
      <text class="font-sans card-sub" x="42" y="55" text-anchor="middle" font-size="9px">IRs &amp; netlists</text>
    </g>

    <!-- Arrow 2: design -> tools -->
    <path d="M 241 113 L 263 113" stroke="#475569" stroke-width="2" stroke-linecap="round" marker-end="url(#arrow-dark)"/>

    <!-- 3. tools -->
    <g transform="translate(266, 92)">
      <rect width="80" height="42" rx="4" fill="#FFFFFF" stroke="#64748B" stroke-width="1.4"/>
      <text class="font-mono mono-title" x="40" y="26" text-anchor="middle" fill="#0F172A">tools</text>
      <text class="font-sans card-sub" x="40" y="55" text-anchor="middle" font-size="9px">Sim &amp; EDA</text>
    </g>

    <!-- Arrow 3: tools -> measurements -->
    <path d="M 348 113 L 370 113" stroke="#475569" stroke-width="2" stroke-linecap="round" marker-end="url(#arrow-dark)"/>

    <!-- 4. measurements -->
    <g transform="translate(373, 92)">
      <rect width="130" height="42" rx="4" fill="#FEF3C7" stroke="#D97706" stroke-width="1.5"/>
      <text class="font-mono mono-title" x="65" y="26" text-anchor="middle" fill="#92400E">measurements</text>

      <!-- Tree under measurements -->
      <g transform="translate(20, 50)">
        <!-- Vertical stem -->
        <line x1="0" y1="0" x2="0" y2="128" stroke="#475569" stroke-width="1.4"/>

        <!-- Branch 1: performance -->
        <path d="M 0 16 L 16 16" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="20">performance</text>

        <!-- Branch 2: energy -->
        <path d="M 0 44 L 16 44" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="48">energy</text>

        <!-- Branch 3: area -->
        <path d="M 0 72 L 16 72" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="76">area</text>

        <!-- Branch 4: thermal -->
        <path d="M 0 100 L 16 100" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="104">thermal</text>

        <!-- Branch 5: carbon -->
        <path d="M 0 128 L 16 128" stroke="#475569" stroke-width="1.4"/>
        <text class="font-mono tree-text" x="22" y="132">carbon</text>
      </g>
    </g>

    <!-- Explanatory note in center bottom -->
    <rect x="18" y="325" width="484" height="54" rx="4" fill="#F1F5F9" stroke="#CBD5E1" stroke-width="1"/>
    <text class="font-sans card-sub" x="30" y="342" font-weight="600" fill="#1E293B">The Autonomous Cycle:</text>
    <text class="font-sans card-sub" x="30" y="357" fill="#475569">Generators synthesize candidates across five stack layers; authoritative tools</text>
    <text class="font-sans card-sub" x="30" y="370" fill="#475569">measure multidimensional physical costs and steer continuous refinement.</text>
  </g>

  <!-- Straight Horizontal Pipeline Arrow: measurements -> commitment (y = 75 + 113 = 188) -->
  <path d="M 800 188 L 838 188" stroke="#D97706" stroke-width="2.4" stroke-linecap="round" marker-end="url(#arrow-commit)"/>

  <!-- ===================================================================== -->
  <!-- BOOKEND 2 (OUTPUT): Commitment Authority                              -->
  <!-- ===================================================================== -->
  <g transform="translate(840, 75)">
    <!-- Container -->
    <rect width="200" height="395" rx="6" fill="#FFFBEB" stroke="#D97706" stroke-width="1.6"/>
    <!-- Header -->
    <path d="M 0 6 Q 0 0 6 0 L 194 0 Q 200 0 200 6 L 200 32 L 0 32 Z" fill="#FDE68A"/>
    <line x1="0" y1="32" x2="200" y2="32" stroke="#D97706" stroke-width="1.2"/>

    <!-- Badge -->
    <rect x="12" y="6" width="102" height="19" rx="3" fill="#D97706"/>
    <text class="font-sans badge-text" x="63" y="19.5" text-anchor="middle">OUTPUT BOOKEND</text>

    <text class="font-sans card-title" x="14" y="52">Commitment Authority</text>
    <text class="font-sans card-sub" x="14" y="68">Owned by Accountable Leadership</text>

    <line x1="14" y1="78" x2="186" y2="78" stroke="#CBD5E1" stroke-width="1"/>

    <!-- Core node 'commitment' aligned horizontally with execution chain -->
    <rect x="14" y="92" width="172" height="42" rx="4" fill="#FFFFFF" stroke="#D97706" stroke-width="1.6"/>
    <text class="font-mono mono-title" x="100" y="118" text-anchor="middle" fill="#B45309">commitment</text>

    <!-- Bullet points -->
    <g transform="translate(14, 154)">
      <circle cx="5" cy="6" r="2.5" fill="#D97706"/>
      <text class="font-sans card-sub" x="15" y="10" font-weight="600" fill="#0F172A">Evidence qualification</text>
      <text class="font-sans card-sub" x="15" y="24">Auditing multi-tool signoff logs</text>

      <circle cx="5" cy="46" r="2.5" fill="#D97706"/>
      <text class="font-sans card-sub" x="15" y="50" font-weight="600" fill="#0F172A">Cross-layer diagnosis</text>
      <text class="font-sans card-sub" x="15" y="64">Detecting simulator artifacts</text>

      <circle cx="5" cy="86" r="2.5" fill="#D97706"/>
      <text class="font-sans card-sub" x="15" y="90" font-weight="600" fill="#0F172A">Residual risk assessment</text>
      <text class="font-sans card-sub" x="15" y="104">Evaluating yield &amp; corner margins</text>

      <circle cx="5" cy="126" r="2.5" fill="#D97706"/>
      <text class="font-sans card-sub" x="15" y="130" font-weight="600" fill="#0F172A">Mask capital signoff</text>
      <text class="font-sans card-sub" x="15" y="144">Staking $10M–$100M+ NRE budget</text>
    </g>

    <rect x="14" y="325" width="172" height="54" rx="4" fill="#FEF3C7"/>
    <text class="font-sans card-sub" x="22" y="342" font-weight="600" fill="#92400E">Role of Authority:</text>
    <text class="font-sans card-sub" x="22" y="357" fill="#92400E">In-order retirement of architectural</text>
    <text class="font-sans card-sub" x="22" y="370" fill="#92400E">decisions into physical silicon.</text>
  </g>

  <!-- ===================================================================== -->
  <!-- BOTTOM CONTRAST BAR: Architecture 1.0 vs Architecture 2.0             -->
  <!-- ===================================================================== -->
  <g transform="translate(40, 485)">
    <rect width="1000" height="115" rx="6" fill="#F8FAFC" stroke="#94A3B8" stroke-width="1.2"/>

    <!-- Title -->
    <text class="font-sans contrast-hdr" x="20" y="24">The Structural Inversion of Engineering Labor Across Epochs</text>

    <!-- Arch 1.0 box -->
    <g transform="translate(20, 35)">
      <rect width="470" height="68" rx="4" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
      <rect x="10" y="8" width="112" height="18" rx="3" fill="#64748B"/>
      <text class="font-sans badge-text" x="66" y="20.5" text-anchor="middle">ARCHITECTURE 1.0</text>
      <text class="font-sans contrast-body" x="132" y="21" font-weight="700" fill="#0F172A">Human operates INSIDE the execution loop</text>
      <text class="font-sans contrast-body" x="12" y="42" fill="#475569">Architects manually draft RTL, write simulation scripts, parse timing logs,</text>
      <text class="font-sans contrast-body" x="12" y="58" fill="#475569">and tune microarchitectural knobs by hand. Cognitive effort is trapped in execution mechanics.</text>
    </g>

    <!-- Arch 2.0 box -->
    <g transform="translate(510, 35)">
      <rect width="470" height="68" rx="4" fill="#FFFFFF" stroke="#0284C7" stroke-width="1.2"/>
      <rect x="10" y="8" width="112" height="18" rx="3" fill="#0284C7"/>
      <text class="font-sans badge-text" x="66" y="20.5" text-anchor="middle">ARCHITECTURE 2.0</text>
      <text class="font-sans contrast-body" x="132" y="21" font-weight="700" fill="#0369A1">Human governs the TWO LOAD-BEARING BOOKENDS</text>
      <text class="font-sans contrast-body" x="12" y="42" fill="#334155">Execution loop is automated across multi-tool chains. Human judgment is elevated to</text>
      <text class="font-sans contrast-body" x="12" y="58" fill="#334155"><tspan font-weight="700">intent formulation</tspan> at the input and <tspan font-weight="700">commitment authority</tspan> at the signoff boundary.</text>
    </g>
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
