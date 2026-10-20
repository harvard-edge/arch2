# Nanochip guides and figures

Start with the [system guide](SYSTEM_GUIDE.md) for the current implementation,
commands, measurements, and remaining limits. The [cumulative student guide](../laboratory/course/README.md)
describes the nine components students build.

The `system` command trains and adapts a small design helper and evaluates its
proposals on the complete reduced workload. The earlier `demo` command uses a
dequantizer block; its [walkthrough](DEMO_WALKTHROUGH.md) retains that narrower
scope. Current physical status belongs to the system guide, so an earlier
block result cannot be mistaken for complete-core GDS evidence.

The [historical workbench](HISTORICAL_WORKBENCH.md) retains the earlier six-stage
forensic walkthrough and upstream nano-KPU study. Its claims keep their original
pre-layout scope, separate from the current cumulative construction course.

## Planning figures

`nanochip-sandbox-proposal.svg` adds a student entry point, explicit retrieval
and method choices, and independent evaluation to the full system view. Its
[diagram](nanochip-sandbox-proposal.svg) and PNG/PDF twins are proposed
architecture for discussion, not implementation status. The original figure
below remains unchanged.

`nanochip-system-plan.svg` is the editable source for the proposed cumulative
laboratory architecture. It describes intended components and dependencies,
not measured results or implemented capabilities. The PNG and PDF are rendered
copies.

Render from this directory with librsvg:

```sh
rsvg-convert --width 4000 --dpi-x 300 --dpi-y 300 nanochip-system-plan.svg --output nanochip-system-plan.png
rsvg-convert --format pdf nanochip-system-plan.svg --output nanochip-system-plan.pdf
```

Inspect the rendered PNG after changing the source. Check text fit, arrow
connections, clipping, and legibility before reusing the figure.
