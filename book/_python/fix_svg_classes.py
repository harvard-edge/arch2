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

canonical_classes = {
    "panel-title",
    "panel-subtitle",
    "body-bold",
    "chip",
    "small",
    "panel",
    "role-box",
    "line",
}

base_dir = Path("/Users/VJ/GitHub/Arch2-ch5-rewrite/book")


def replacer(match):
    cls = match.group(1)
    if cls in canonical_classes:
        return match.group(0)
    # If it's an unknown class, default to role-box
    return 'class="role-box"'


for rel_path in files_to_process:
    p = base_dir / rel_path
    if not p.exists():
        continue

    content = p.read_text()

    # Also fix paths that don't have a class and might be filled black
    # But wait, SVG arrows are paths without class inside <marker>
    # We only care about rect, polygon, circle with weird classes.

    content = re.sub(r'class="([^"]+)"', replacer, content)

    p.write_text(content)
    print(f"Fixed {rel_path}")
