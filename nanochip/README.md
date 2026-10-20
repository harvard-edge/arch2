# Nanochip: an AI-native architecture laboratory

Nanochip turns the Kimi nano-KPU example into a complete laboratory for
learning AI-native architecture, from workload through checked GDSII. Students
build one experimental system that prepares data, trains a small design model,
proposes hardware changes, executes them through engineering tools, and learns
from the returned measurements. The chip gives these components a concrete
destination.

The current complete-workload path trains and adapts real model parameters,
executes the selected RTL, and compares frozen learned and conventional methods
on held-out cases. It has passed functional validation in the prepared offline
container. Complete-core physical acceptance and the final cumulative capstone
remain under validation; a successful functional run does not establish them.

With PyTorch, NumPy, Verilator, Make, and a C++ compiler already installed, run
the functional comparison from the repository root:

```bash
python3 -m nanochip.laboratory doctor
python3 -m nanochip.laboratory system --functional-only \
  --output output/nanochip/system-001
```

Each run needs a new output directory. Its `report.md` and `report.json` connect
the data, checkpoints, candidate sources, tool results, and measured costs.
The first complete functional comparison reached the same best design with
adapted inference, unchanged inference, enumeration, and a constant policy.
It demonstrates the working learning loop without establishing a design
advantage from adaptation.

The [system guide](docs/SYSTEM_GUIDE.md) explains the information flow and its
two feedback paths. The [full runtime guide](containers/FULL_RUNTIME.md)
records the prepared container, exact commands, and validation boundary.
Packages and images remain local; no registry publication or package-name
ownership is claimed.

## Components and teaching plan

The [cumulative student guide](laboratory/course/README.md) defines nine labs.
Students construct data handling, numerical representations, a harness, model
training, inference and retrieval, prediction and search, an RTL transformation,
physical interpretation, and the final comparison. Editable modules and retained
artifacts connect the labs. Instructor recovery is explicit, and an upstream
change invalidates dependent completion records.

To install the local Python entrypoint with existing build tools, then create a
student workspace:

```bash
python3 -m pip install --no-index --no-deps --no-build-isolation -e ./nanochip
nanochip course init my-nanochip --mode student
nanochip course status --workspace my-nanochip
```

The Python package supplies the interfaces and exercises; the prepared container
supplies learning dependencies and the EDA toolchain. The small model students
train proposes design actions. The chip executes a separate reduced Kimi-derived
mathematical workload, using generated test weights and independent numerical
references. The [modular laboratory guide](laboratory/README.md) describes these
components and their boundaries. The earlier
[demo walkthrough](docs/DEMO_WALKTHROUGH.md) and
[first exercise](laboratory/exercises/FIRST_SYSTEM.md) remain useful development
records. Their results do not establish complete-core acceptance.

## Historical workbench

The [historical workbench](docs/HISTORICAL_WORKBENCH.md) preserves the earlier
six-stage forensic walkthrough, lab mapping, and upstream nano-KPU study.
Its numeric claims and pre-layout physical scope remain historical records;
they do not establish acceptance of the current complete-core course.
