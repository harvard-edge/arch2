import os

svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 480" role="img">
  <title>The Rejection Bottleneck</title>
  <desc>A funnel diagram showing 1M AI-generated candidates funneling down to a single human architect.</desc>
  <defs>
    <style>
      .font { font-family: Arial, Helvetica, sans-serif; }
      .box { fill: #F4F1FA; stroke: #7E6AA8; stroke-width: 2; }
      .funnel { fill: #E8F4F8; stroke: #1F5F7A; stroke-width: 3; }
      .label-large { font-size: 24px; font-weight: 700; fill: #222222; text-anchor: middle; }
      .label-medium { font-size: 20px; font-weight: 700; fill: #1F5F7A; text-anchor: middle; }
      .label-small { font-size: 16px; fill: #555555; text-anchor: middle; }
      .alert-red { font-size: 22px; font-weight: 700; fill: #9E2F36; text-anchor: middle; }
      .line { stroke: #333333; stroke-width: 2; fill: none; stroke-dasharray: 6,4; }
    </style>
  </defs>

  <!-- Funnel Shape -->
  <path d="M 200,80 L 760,80 L 600,280 L 600,400 L 360,400 L 360,280 Z" class="funnel" />

  <!-- Layer 1: Generation -->
  <line x1="200" y1="140" x2="760" y2="140" class="line" />
  <text x="480" y="115" class="font label-large">1,000,000+ Candidates</text>
  <text x="480" y="135" class="font label-small">AI Generative Models / Optimizers</text>

  <!-- Layer 2: Fast Proxies -->
  <line x1="260" y1="210" x2="700" y2="210" class="line" />
  <text x="480" y="180" class="font label-medium">10,000 Candidates</text>
  <text x="480" y="200" class="font label-small">Cheap Surrogate Models &amp; ML Predictors</text>

  <!-- Layer 3: Physical Simulation -->
  <line x1="320" y1="280" x2="640" y2="280" class="line" />
  <text x="480" y="250" class="font label-medium">50 Candidates</text>
  <text x="480" y="270" class="font label-small">Cycle-Accurate Simulation &amp; EDA Scripts</text>

  <!-- Layer 4: The Bottleneck -->
  <text x="480" y="330" class="font alert-red">THE REJECTION BOUND</text>
  <text x="480" y="360" class="font label-large">5 Candidates / Day</text>
  <text x="480" y="385" class="font label-small">Manual Human Review &amp; Commitment</text>
  
  <!-- Human Owner Icon/Box at the bottom -->
  <rect x="380" y="410" width="200" height="50" rx="8" class="box" />
  <text x="480" y="442" class="font label-medium" fill="#59467F">The Accountable Architect</text>
</svg>
"""

with open("synthesis/book/chapters/02-design-loop-no-longer-scales/images/F2-rejection-bottleneck.svg", "w") as f:
    f.write(svg_content)
