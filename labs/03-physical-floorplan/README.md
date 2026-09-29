# Loop C: Macro Placement and Routing Congestion

A teaching lab, not a measurement. See [../README.md](../README.md#2-what-is-computed-and-what-is-authored) for what the labs compute and what is authored.

## 1. The Question

A placement with the shortest wirelength can still leave too few routing tracks where the macro pins escape. What does a wirelength-only objective miss?

## 2. Design and Model

* **Tile:** $1000 \times 1000\ \mu\text{m}$, one compute core and four SRAM macros.
* **Congestion model:** a simplified RUDY-style estimate on a $25 \times 25$ grid. Each bin has a nominal track capacity; macros block 80 percent of it and the core 20 percent. Each macro adds a bus of wires spread over its bounding box to the core plus a pin-escape load at its pin location.

This model is a teaching simplification. It is not a global router, and it is not calibrated against one.

## 3. What the Script Does

| Mode | Layout | Where its numbers come from |
| :--- | :--- | :--- |
| `assisted` | Macros placed asymmetrically | Layout and HPWL authored; congestion computed from the model. |
| `driven` | Macros packed around the core with inward-facing pins | Layout and HPWL authored; congestion computed from the model. |
| `native` | Pins turned outward with wide channels between macros and core | Layout and HPWL authored; congestion computed from the model. |

The pin-escape load is also authored, and it differs by mode, so part of each mode's outcome is set directly in the script. The `drc_violations` field counts grid bins above 85 percent of nominal capacity. It is not a design-rule check, and `signoff_passed` means only that the count is zero and peak congestion is at most 85 percent under this model.

## 4. Things to Try

* Set the three modes to the same pin-escape load and see how much of the difference remains.
* Compute HPWL from the macro and pin coordinates instead of using the authored values.
* Run one of the layouts through OpenROAD global routing and compare its congestion report with this model.

## 5. Running

```bash
./arch2 docker lab 03
python3 labs/03-physical-floorplan/run.py
```

Outputs: `results.json` (layouts, authored HPWL, modeled congestion) and `results.png` (congestion maps).
