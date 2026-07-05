import textwrap

svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 350" style="background-color:#ffffff; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <defs>
    <!-- Arrowhead marker -->
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#4B5563"/>
    </marker>
    <!-- Dashed arrowhead -->
    <marker id="dashedArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#9CA3AF"/>
    </marker>
    
    <!-- Cloud shape for thought bubbles (made slightly wider) -->
    <g id="thought-cloud">
      <path d="M 10 25 C 10 10, 30 5, 45 10 C 60 -5, 95 -5, 110 10 C 125 5, 145 10, 145 25 C 155 30, 160 50, 145 55 C 145 70, 125 75, 110 70 C 95 85, 60 85, 45 70 C 30 75, 10 70, 10 55 C -5 50, 0 30, 10 25 Z" fill="#F3F4F6" stroke="#D1D5DB" stroke-width="1.5"/>
    </g>

    <!-- Person icon -->
    <g id="person">
      <circle cx="20" cy="15" r="10" fill="#4B5563"/>
      <path d="M 5 40 Q 20 20 35 40 Z" fill="#4B5563"/>
    </g>
    
    <g id="agent-icon">
      <rect x="5" y="10" width="30" height="25" rx="4" fill="#3B82F6"/>
      <circle cx="14" cy="20" r="3" fill="white"/>
      <circle cx="26" cy="20" r="3" fill="white"/>
      <path d="M 15 28 L 25 28" stroke="white" stroke-width="2"/>
    </g>
  </defs>

  <!-- Left Section: Undocumented Organization -->
  <rect x="20" y="20" width="290" height="310" rx="8" fill="#F9FAFB" stroke="#E5E7EB" stroke-width="2"/>
  <text x="165" y="45" font-size="14" font-weight="600" fill="#374151" text-anchor="middle">The Undocumented Organization</text>
  <text x="165" y="65" font-size="12" fill="#6B7280" text-anchor="middle">Tacit, unwritten domain expertise</text>
  
  <!-- Expert 1 -->
  <use href="#person" x="40" y="95"/>
  <text x="60" y="145" font-size="11" font-weight="500" fill="#4B5563" text-anchor="middle">Compiler Lead</text>
  <use href="#thought-cloud" x="115" y="60" transform="scale(0.8)"/>
  <text x="175" y="90" font-size="10" fill="#4B5563" text-anchor="middle">"LLVM backend can't</text>
  <text x="175" y="102" font-size="10" fill="#4B5563" text-anchor="middle">lower that matrix layout"</text>
  <path d="M 90 120 C 110 120, 120 110, 130 110" fill="none" stroke="#D1D5DB" stroke-width="1" stroke-dasharray="2,2"/>

  <!-- Expert 2 -->
  <use href="#person" x="40" y="170"/>
  <text x="60" y="220" font-size="11" font-weight="500" fill="#4B5563" text-anchor="middle">Packaging Eng</text>
  <use href="#thought-cloud" x="115" y="140" transform="scale(0.8)"/>
  <text x="175" y="170" font-size="10" fill="#4B5563" text-anchor="middle">"That partition breaks</text>
  <text x="175" y="182" font-size="10" fill="#4B5563" text-anchor="middle">power delivery mesh"</text>
  
  <!-- Expert 3 -->
  <use href="#person" x="40" y="245"/>
  <text x="60" y="295" font-size="11" font-weight="500" fill="#4B5563" text-anchor="middle">Senior Architect</text>
  <use href="#thought-cloud" x="115" y="220" transform="scale(0.8)"/>
  <text x="175" y="250" font-size="10" fill="#4B5563" text-anchor="middle">"Coherency traffic will</text>
  <text x="175" y="262" font-size="10" fill="#4B5563" text-anchor="middle">starve XR display controller"</text>


  <!-- Center Section: The Extraction Bridge -->
  <rect x="340" y="20" width="220" height="310" rx="8" fill="#EEF2FF" stroke="#C7D2FE" stroke-width="2"/>
  <text x="450" y="45" font-size="14" font-weight="600" fill="#3730A3" text-anchor="middle">The Extraction Bridge</text>
  
  <use href="#person" x="430" y="150" transform="scale(1.5)"/>
  <text x="450" y="225" font-size="14" font-weight="600" fill="#4338CA" text-anchor="middle">Human Architect</text>
  <text x="450" y="245" font-size="12" fill="#4F46E5" text-anchor="middle">Hunts down context &amp;</text>
  <text x="450" y="260" font-size="12" fill="#4F46E5" text-anchor="middle">formalizes constraints</text>

  <!-- Arrows flowing from Experts to Architect -->
  <path d="M 300 120 L 340 160" fill="none" stroke="#9CA3AF" stroke-width="2" marker-end="url(#arrow)" stroke-dasharray="4,2"/>
  <path d="M 300 185 L 340 185" fill="none" stroke="#9CA3AF" stroke-width="2" marker-end="url(#arrow)" stroke-dasharray="4,2"/>
  <path d="M 300 250 L 340 210" fill="none" stroke="#9CA3AF" stroke-width="2" marker-end="url(#arrow)" stroke-dasharray="4,2"/>
  
  <text x="325" y="145" font-size="11" fill="#6B7280" font-style="italic" transform="rotate(38 325 145)">Extract</text>


  <!-- Right Section: Explicit Loop State -->
  <rect x="600" y="20" width="280" height="310" rx="8" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="2"/>
  <text x="740" y="45" font-size="14" font-weight="600" fill="#0F172A" text-anchor="middle">Explicit Loop State</text>
  <text x="740" y="65" font-size="12" fill="#64748B" text-anchor="middle">Machine-readable constraints</text>
  
  <!-- Boxes -->
  <rect x="620" y="90" width="160" height="40" rx="4" fill="#FFFFFF" stroke="#94A3B8" stroke-width="1.5"/>
  <text x="700" y="115" font-size="12" font-weight="500" fill="#334155" text-anchor="middle">Environment Contracts</text>

  <rect x="620" y="165" width="160" height="40" rx="4" fill="#FFFFFF" stroke="#94A3B8" stroke-width="1.5"/>
  <text x="700" y="190" font-size="12" font-weight="500" fill="#334155" text-anchor="middle">Rejection Gates</text>

  <rect x="620" y="240" width="160" height="40" rx="4" fill="#FFFFFF" stroke="#94A3B8" stroke-width="1.5"/>
  <text x="700" y="265" font-size="12" font-weight="500" fill="#334155" text-anchor="middle">Evidence Ledgers</text>

  <!-- Flow from Architect to Loop State -->
  <path d="M 560 185 L 610 185" fill="none" stroke="#4338CA" stroke-width="2.5" marker-end="url(#arrow)"/>
  <text x="585" y="175" font-size="11" font-weight="500" fill="#4338CA" text-anchor="middle">Codify</text>

  <!-- The AI Agent -->
  <use href="#agent-icon" x="820" y="160" transform="scale(1.2)"/>
  <text x="845" y="210" font-size="12" font-weight="600" fill="#1D4ED8" text-anchor="middle">AI Agent</text>
  <text x="845" y="225" font-size="11" fill="#3B82F6" text-anchor="middle">Acts on rules</text>

  <!-- Flow between Agent and State -->
  <path d="M 820 185 L 790 185" fill="none" stroke="#3B82F6" stroke-width="2" marker-end="url(#arrow)"/>
  <path d="M 790 195 L 820 195" fill="none" stroke="#3B82F6" stroke-width="2" marker-end="url(#arrow)" stroke-dasharray="3,3"/>
  
  <text x="805" y="165" font-size="10" fill="#64748B" text-anchor="middle">Queries</text>
  <text x="805" y="210" font-size="10" fill="#64748B" text-anchor="middle">Proposes</text>

  <!-- Warning text about direct access -->
  <path d="M 830 140 L 830 60 L 300 60 L 300 90" fill="none" stroke="#EF4444" stroke-width="1.5" stroke-dasharray="6,4" marker-end="url(#arrow)"/>
  <text x="565" y="55" font-size="11" font-weight="600" fill="#EF4444" text-anchor="middle">× Cannot directly query undocumented human wisdom</text>
</svg>
"""

with open('synthesis/book/chapters/10-what-architect-owns/images/F10-tacit-extraction-bridge.svg', 'w') as f:
    f.write(svg_content)

print("Updated SVG generated successfully.")
