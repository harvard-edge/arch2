import re
from pathlib import Path

files_to_process = [
    "chapters/01-moonshot/images/ch1_ai_roles.svg",
    "chapters/01-moonshot/images/ch1_tao_vs_taos.svg",
    "chapters/03-architecture-20-framework/images/ch3_decision_authority.svg",
    "chapters/04-representations/images/ch4_knowledge_fusion.svg",
    "chapters/07-feedback/images/ch7_independent_checks.svg",
    "chapters/08-running-the-loop/images/ch8_design_loop_workflow.svg",
    "chapters/11-ownership/images/ch10_ownership_handoff.svg",
]

canonical_defs = """  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#333333"/>
    </marker>
    <style>
      .font { font-family: Arial, Helvetica, sans-serif; }
      .panel-title { font-size: 13.5px; font-weight: 700; fill: #20252B; }
      .panel-subtitle { font-size: 11.5px; fill: #59636D; }
      .body-bold { font-size: 12.5px; font-weight: 700; fill: #222222; }
      .chip { font-size: 12.5px; font-weight: 700; fill: #222222; }
      .small { font-size: 11.2px; fill: #444444; }
      .panel { fill: #F5F8FA; stroke: #9AA8B5; stroke-width: 1.1; }
      .role-box { fill: #FFFFFF; stroke: #1683A6; stroke-width: 1.45; }
      .line { stroke: #333333; stroke-width: 1.9; fill: none; stroke-linecap: square; stroke-linejoin: miter; }
    </style>
  </defs>"""

base_dir = Path("/Users/VJ/GitHub/Arch2-ch5-rewrite/book")

for rel_path in files_to_process:
    p = base_dir / rel_path
    if not p.exists():
        print(f"Skipping {rel_path}, not found.")
        continue

    content = p.read_text()

    # Replace defs
    content = re.sub(r"<defs>.*?</defs>", canonical_defs, content, flags=re.DOTALL)

    # Replace classes
    content = content.replace('class="title"', 'class="panel-title"')
    content = content.replace('class="text-body"', 'class="small"')
    content = content.replace('class="text-bold"', 'class="body-bold"')
    content = content.replace('class="coord-box"', 'class="panel"')
    content = content.replace('class="edge"', 'class="line"')

    # For rects that don't have classes but have fills
    content = re.sub(r'fill="#d4e6f1"', 'class="role-box"', content)
    content = re.sub(r'fill="#e8f8f5"', 'class="panel"', content)

    # Remove rx and ry
    content = re.sub(r'\s*rx="[0-9.]+"', "", content)
    content = re.sub(r'\s*ry="[0-9.]+"', "", content)

    # Make sure svg has role="img"
    if 'role="img"' not in content:
        content = content.replace("<svg ", '<svg role="img" ')

    p.write_text(content)
    print(f"Processed {rel_path}")
