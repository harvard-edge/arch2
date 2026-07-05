import os
import re

epigraphs = {
    "05-architecture-environments-tool-interfaces": """::: {.epigraph}
> *"We shape our tools and thereafter our tools shape us."*
>
> — John Culkin
:::

""",
    "06-methods-generation-prediction-optimization": """::: {.epigraph}
> *"The best way to predict the future is to invent it."*
>
> — Alan Kay
:::

""",
    "07-feedback-verification-trust": """::: {.epigraph}
> *"Program testing can be used to show the presence of bugs, but never to show their absence!"*
>
> — Edsger W. Dijkstra
:::

""",
    "08-running-the-loop": """::: {.epigraph}
> *"In theory, there is no difference between theory and practice. But, in practice, there is."*
>
> — Jan L. A. van de Snepscheut
:::

""",
    "09-loop-patterns-across-stack": """::: {.epigraph}
> *"There is no single development, in either technology or management technique, which by itself promises even one order of magnitude improvement in productivity, in reliability, in simplicity."*
>
> — Fred Brooks
:::

""",
    "10-what-architect-owns": """::: {.epigraph}
> *"The architect's two most important tools are the eraser at the drafting board and the wrecking bar at the site."*
>
> — Frank Lloyd Wright
:::

"""
}

for ch_name, epigraph in epigraphs.items():
    filepath = f"synthesis/book/chapters/{ch_name}/index.qmd"
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r") as f:
        content = f.read()
    
    # insert after the # Heading
    match = re.search(r'^(# [^\n]+)\n', content)
    if match:
        heading = match.group(1)
        new_content = content.replace(f"{heading}\n", f"{heading}\n\n{epigraph}")
        if new_content != content:
            with open(filepath, "w") as f:
                f.write(new_content)
            print(f"Added epigraph to {ch_name}")

