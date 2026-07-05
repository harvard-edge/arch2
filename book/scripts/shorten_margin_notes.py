import re
import glob

replacements = {
    "synthesis/book/chapters/02-design-loop-no-longer-scales/index.qmd": (
        r':::\s*\{\.column-margin\}\n\*\*Rejected too late: FDIV\*\*.*?\n:::',
        """::: {.column-margin}
**Author's Note: The FDIV Bug**
*The 1994 Pentium FDIV bug cost Intel $475M because just five table entries were wrong. No cheap check caught it before silicon. This classic failure perfectly illustrates why AI loops must have explicit, automated rejection authority—the missing rejection, not the missing entries, sets the price.*
:::"""
    ),
    "synthesis/book/chapters/04-data-representations-world-models/index.qmd": (
        r':::\s*\{\.column-margin\}\n\*\*The un-rerunnable result\*\*.*?\n:::',
        """::: {.column-margin}
**Author's Note: The Un-rerunnable Result**
*We've all seen a team report a strong result, only to fail reproducing it six months later because a simulator default shifted or a script was lost on an old laptop. The fix isn't human heroics—it's enforcing strict tool and environment provenance as the run happens.*
:::"""
    ),
    "synthesis/book/chapters/03-architecture-20-framework/index.qmd": (
        r':::\s*\{\.column-margin\}\n\*\*Author\'s Reflection: Ontology vs\. Taxonomy\*\*.*?\n:::',
        """::: {.column-margin}
**Author's Note: Ontology vs. Taxonomy**
*An ontology defines fundamental entities (What is State? What is Action?). A taxonomy categorizes specific instances (Is this a Surrogate Predictor?). You cannot meaningfully classify the structural shapes of these design loops—the taxonomy—until you establish their core building blocks—the ontology.*
:::"""
    ),
    "synthesis/book/chapters/09-loop-patterns-across-stack/index.qmd": (
        r':::\s*\{\.column-margin\}\n\*\*Author\'s Reflection: Ontology vs\. Taxonomy\*\*.*?\n:::',
        """::: {.column-margin}
**Author's Note: Structural Lenses**
*If you apply a Joel Emer-style taxonomy, you realize we aren’t categorizing tools—we're categorizing feedback loops. When reading a new ISCA paper, don't just ask "what layer of the stack is this?" Ask "which branch of the loop taxonomy is this?" It gives you a structural lens to spot failure modes.*
:::"""
    )
}

for filepath, (pattern, replacement) in replacements.items():
    with open(filepath, "r") as f:
        content = f.read()
        
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Updated {filepath}")
    else:
        print(f"Failed to match pattern in {filepath}")

