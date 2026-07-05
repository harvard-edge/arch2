import os
import re

epigraphs = {
    "01-moonshot": """::: {.epigraph}
> *"The purpose of computing is insight, not numbers."*
>
> — Richard Hamming
:::

""",
    "02-design-loop-no-longer-scales": """::: {.epigraph}
> *"A complex system that works is invariably found to have evolved from a simple system that worked."*
>
> — John Gall
:::

""",
    "03-architecture-20-framework": """::: {.epigraph}
> *"All models are wrong, but some are useful."*
>
> — George E. P. Box
:::

""",
    "04-data-representations-world-models": """::: {.epigraph}
> *"The limits of my language mean the limits of my world."*
>
> — Ludwig Wittgenstein
:::

"""
}

for ch_name, epigraph in epigraphs.items():
    filepath = f"synthesis/book/chapters/{ch_name}/index.qmd"
    with open(filepath, "r") as f:
        content = f.read()
    
    # insert after the # Heading
    # The heading looks like: # Title {#sec-...}
    match = re.search(r'^(# [^\n]+)\n', content)
    if match:
        heading = match.group(1)
        # replace heading with heading + \n + epigraph
        new_content = content.replace(f"{heading}\n", f"{heading}\n\n{epigraph}")
        if new_content != content:
            with open(filepath, "w") as f:
                f.write(new_content)
            print(f"Added epigraph to {ch_name}")

