import os

OUT_DIR = "/Users/VJ/GitHub/arch2/synthesis/assets/figures/src"
STYLE = """
    <style>
      .font { font-family: Arial, Helvetica, sans-serif; }
      .title { font-size: 16px; font-weight: 700; fill: #202020; }
      .label { font-size: 14.4px; font-weight: 700; fill: #202020; }
      .label-white { font-size: 14.4px; font-weight: 700; fill: #ffffff; }
      .small { font-size: 9.2px; fill: #303030; }
      .center { font-size: 12.0px; font-weight: 700; fill: #202020; }
      .note { font-size: 10.4px; font-weight: 700; fill: #285F7A; }
      .muted { font-size: 8.8px; fill: #555555; }
      .line { stroke: #444444; stroke-width: 1.15; fill: none; }
      .line-dashed { stroke: #444444; stroke-width: 1.15; fill: none; stroke-dasharray: 4,4; }
      .thin { stroke: #6F7E86; stroke-width: 1.05; fill: none; }
      .arrow-end { marker-end: url(#arrow); }
    </style>
"""

DEFS = """
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#444444"/>
    </marker>
""" + STYLE + """  </defs>"""

# F2 Waterbed Effect
f2_waterbed = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="50 0 650 350" role="img">
  <title>F2 Waterbed Effect</title>
  {DEFS}
  <rect x="50" y="0" width="650" height="350" fill="#ffffff"/>
  
  <g class="font">
    <text class="title" x="350" y="40" text-anchor="middle">The Waterbed Effect in System Energy</text>
    <text class="small" x="350" y="58" text-anchor="middle">Naive optimization shrinks compute but balloons data movement</text>
  </g>

  <!-- Baseline Bar -->
  <g class="font">
    <text class="center" x="200" y="100" text-anchor="middle">Baseline Design</text>
    <rect x="150" y="120" width="100" height="40" fill="#9ECBE1" stroke="#356C8C"/>
    <text class="small" x="200" y="144" text-anchor="middle">Compute</text>
    
    <rect x="150" y="160" width="100" height="60" fill="#F0C27B" stroke="#B07021"/>
    <text class="small" x="200" y="194" text-anchor="middle">Memory</text>
    
    <rect x="150" y="220" width="100" height="30" fill="#B8D7A8" stroke="#5F8F4E"/>
    <text class="small" x="200" y="239" text-anchor="middle">Interconnect</text>
    
    <rect x="150" y="250" width="100" height="20" fill="#E8D1D1" stroke="#A35656"/>
    <text class="small" x="200" y="264" text-anchor="middle">Control/Leakage</text>
  </g>

  <!-- Arrow -->
  <path class="line arrow-end" d="M 280 185 L 360 185"/>
  <text class="font muted" x="320" y="175" text-anchor="middle">AI Optimizer</text>
  <text class="font muted" x="320" y="200" text-anchor="middle">(ignores memory cost)</text>

  <!-- Optimized Bar -->
  <g class="font">
    <text class="center" x="480" y="100" text-anchor="middle">"Optimized" Design</text>
    <rect x="430" y="120" width="100" height="15" fill="#9ECBE1" stroke="#356C8C"/>
    <text class="small" x="480" y="132" text-anchor="middle">Compute</text>
    
    <rect x="430" y="135" width="100" height="100" fill="#F0C27B" stroke="#B07021"/>
    <text class="small" x="480" y="190" text-anchor="middle">Memory (Ballooned!)</text>
    
    <rect x="430" y="235" width="100" height="60" fill="#B8D7A8" stroke="#5F8F4E"/>
    <text class="small" x="480" y="269" text-anchor="middle">Interconnect</text>
    
    <rect x="430" y="295" width="100" height="25" fill="#E8D1D1" stroke="#A35656"/>
    <text class="small" x="480" y="312" text-anchor="middle">Control/Leakage</text>
  </g>
</svg>
"""

with open(os.path.join(OUT_DIR, "F2-waterbed-effect.svg"), "w") as f:
    f.write(f2_waterbed)

# F3 Architecture Tuple
f3_tuple = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="50 0 700 250" role="img">
  <title>F3 Architecture Tuple Mapping</title>
  {DEFS}
  <rect x="50" y="0" width="700" height="250" fill="#ffffff"/>

  <g class="font">
    <!-- State -->
    <rect x="80" y="80" width="90" height="60" rx="5" fill="#9ECBE1" stroke="#356C8C"/>
    <text class="label" x="125" y="105" text-anchor="middle">S</text>
    <text class="small" x="125" y="125" text-anchor="middle">State</text>

    <!-- Action -->
    <rect x="230" y="80" width="90" height="60" rx="5" fill="#B8D7A8" stroke="#5F8F4E"/>
    <text class="label" x="275" y="105" text-anchor="middle">A</text>
    <text class="small" x="275" y="125" text-anchor="middle">Action</text>

    <!-- Transition -->
    <rect x="380" y="80" width="90" height="60" rx="5" fill="#F0C27B" stroke="#B07021"/>
    <text class="label" x="425" y="105" text-anchor="middle">T</text>
    <text class="small" x="425" y="125" text-anchor="middle">Transition</text>

    <!-- Observation -->
    <rect x="530" y="30" width="90" height="60" rx="5" fill="#E8D1D1" stroke="#A35656"/>
    <text class="label" x="575" y="55" text-anchor="middle">O</text>
    <text class="small" x="575" y="75" text-anchor="middle">Observation</text>

    <!-- Reward -->
    <rect x="530" y="130" width="90" height="60" rx="5" fill="#EAD9FA" stroke="#8A66C2"/>
    <text class="label" x="575" y="155" text-anchor="middle">R</text>
    <text class="small" x="575" y="175" text-anchor="middle">Reward/Cost</text>

    <!-- Arrows -->
    <path class="line arrow-end" d="M 170 110 L 230 110"/>
    <path class="line arrow-end" d="M 320 110 L 380 110"/>
    <path class="line arrow-end" d="M 470 95 L 530 75"/>
    <path class="line arrow-end" d="M 470 125 L 530 145"/>

    <!-- Loop back -->
    <path class="line-dashed arrow-end" d="M 575 190 Q 575 220 325 220 Q 125 220 125 140"/>
    <text class="small" x="325" y="215" text-anchor="middle">Loop Iteration</text>
  </g>
</svg>
"""

with open(os.path.join(OUT_DIR, "F3-architecture-tuple.svg"), "w") as f:
    f.write(f3_tuple)

# F10 Commitment Ladder
f10_ladder = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="50 0 650 350" role="img">
  <title>F10 Commitment Ladder</title>
  {DEFS}
  <rect x="50" y="0" width="650" height="350" fill="#ffffff"/>
  
  <g class="font">
    <text class="title" x="350" y="40" text-anchor="middle">The Commitment Staircase</text>
    
    <!-- Steps -->
    <path class="line" d="M 100 280 L 180 280 L 180 230 L 280 230 L 280 180 L 380 180 L 380 130 L 480 130 L 480 80 L 580 80" stroke-width="2"/>
    
    <rect x="110" y="285" width="70" height="25" fill="#E8D1D1" stroke="#A35656"/>
    <text class="small" x="145" y="302" text-anchor="middle">Analytical</text>
    
    <rect x="190" y="235" width="80" height="25" fill="#F0C27B" stroke="#B07021"/>
    <text class="small" x="230" y="252" text-anchor="middle">Trace / Proxy</text>

    <rect x="290" y="185" width="80" height="25" fill="#B8D7A8" stroke="#5F8F4E"/>
    <text class="small" x="330" y="202" text-anchor="middle">Cycle-Accurate</text>

    <rect x="390" y="135" width="80" height="25" fill="#9ECBE1" stroke="#356C8C"/>
    <text class="small" x="430" y="152" text-anchor="middle">RTL Synthesis</text>

    <rect x="490" y="85" width="80" height="25" fill="#EAD9FA" stroke="#8A66C2"/>
    <text class="small" x="530" y="102" text-anchor="middle">Silicon/FPGA</text>
    
    <!-- Axes Labels -->
    <text class="center" x="350" y="330" text-anchor="middle">Fidelity &amp; Engineering Cost</text>
    <text class="center" x="80" y="180" transform="rotate(-90 80 180)" text-anchor="middle">Human Commitment &amp; Risk</text>
  </g>
</svg>
"""

with open(os.path.join(OUT_DIR, "F10-commitment-ladder.svg"), "w") as f:
    f.write(f10_ladder)

# F8 Loop Beat Sequence Diagram
f8_beat = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="50 0 650 350" role="img">
  <title>F8 Loop Beat</title>
  {DEFS}
  <rect x="50" y="0" width="650" height="350" fill="#ffffff"/>
  
  <g class="font">
    <text class="title" x="350" y="30" text-anchor="middle">The Beat of the Loop</text>
    
    <!-- Entities -->
    <rect x="150" y="50" width="80" height="30" fill="#9ECBE1" stroke="#356C8C"/>
    <text class="center" x="190" y="70" text-anchor="middle">AI Agent</text>
    
    <rect x="300" y="50" width="80" height="30" fill="#B8D7A8" stroke="#5F8F4E"/>
    <text class="center" x="340" y="70" text-anchor="middle">Environment</text>
    
    <rect x="450" y="50" width="80" height="30" fill="#F0C27B" stroke="#B07021"/>
    <text class="center" x="490" y="70" text-anchor="middle">Architect</text>
    
    <!-- Lifelines -->
    <path class="line-dashed" d="M 190 80 L 190 320"/>
    <path class="line-dashed" d="M 340 80 L 340 320"/>
    <path class="line-dashed" d="M 490 80 L 490 320"/>
    
    <!-- Messages -->
    <path class="line arrow-end" d="M 490 100 L 190 100"/>
    <text class="small" x="340" y="95" text-anchor="middle">High-Level Prompt / Boundaries</text>
    
    <path class="line arrow-end" d="M 190 140 L 340 140"/>
    <text class="small" x="265" y="135" text-anchor="middle">Propose Action/Code</text>
    
    <path class="line arrow-end" d="M 340 180 L 190 180"/>
    <text class="small" x="265" y="175" text-anchor="middle">Feedback / Metrics / Error</text>
    
    <path class="line arrow-end" d="M 190 220 L 340 220"/>
    <text class="small" x="265" y="215" text-anchor="middle">Revise Action</text>

    <path class="line arrow-end" d="M 340 260 L 490 260"/>
    <text class="small" x="415" y="255" text-anchor="middle">Escalate to Review</text>

    <path class="line arrow-end" d="M 490 300 L 190 300"/>
    <text class="small" x="340" y="295" text-anchor="middle">Reject or Approve</text>
  </g>
</svg>
"""

with open(os.path.join(OUT_DIR, "F8-loop-beat.svg"), "w") as f:
    f.write(f8_beat)

print("SVGs generated successfully.")
