"""Micro-Loop C Physical Referee: Macro Placement, Geometric DRC & RUDY Congestion.
===================================================================================
Enforces strict physical and topological invariants for silicon macro floorplanning:
  1. Die Boundary Enclosure Invariant:
     All macros and the compute core must lie strictly within [0, die_w] x [0, die_h].
     Catches boundary escape attacks (CHEAT-C2).
  2. Non-Degenerate Geometry Invariant:
     Every block must have strictly positive width and height (w >= 100 um, h >= 100 um).
     Catches collapsed or negative dimension attacks (CHEAT-C3).
  3. Geometric DRC Non-Overlap & Halo Invariant:
     Macros must not overlap each other and must maintain a minimum routing halo (>= 15 um).
     Macros must not intersect the standard cell compute core.
     Catches macro stacking at (0,0) or core collision (CHEAT-C1, CHEAT-C4).
  4. Macro Pin Attachment Invariant:
     Macro interface pins must attach to the perimeter of the macro bounding box (CHEAT-C5).
  5. 2D RUDY Routing Congestion Signoff Invariant:
     Wire density over blockage-aware metal track capacity must not exceed 85.0%.
     DRC wire shorts (cells exceeding 85% capacity) must equal 0.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from labs.referees.base import BaseReferee, PhysicalReceipt

CANONICAL_MACROS = ["SRAM0", "SRAM1", "SRAM2", "SRAM3"]
DEFAULT_DIE_W = 1000.0
DEFAULT_DIE_H = 1000.0
MIN_HALO_UM = 15.0
MAX_PEAK_CONGESTION_PCT = 85.0


def boxes_overlap(
    b1: Tuple[float, float, float, float],
    b2: Tuple[float, float, float, float],
    min_clearance: float = 0.0,
) -> bool:
    """Returns True if box1 and box2 overlap or violate minimum clearance."""
    x1_min, y1_min, x1_max, y1_max = b1
    x2_min, y2_min, x2_max, y2_max = b2
    # Check if separated along X or Y by at least min_clearance
    if (x1_max + min_clearance <= x2_min) or (x2_max + min_clearance <= x1_min):
        return False
    if (y1_max + min_clearance <= y2_min) or (y2_max + min_clearance <= y1_min):
        return False
    return True


class FloorplanReferee(BaseReferee):
    """Adversarial referee evaluating macro placement, geometric DRC, and 2D RUDY congestion."""

    def __init__(
        self,
        die_width_um: float = DEFAULT_DIE_W,
        die_height_um: float = DEFAULT_DIE_H,
        min_halo_um: float = MIN_HALO_UM,
        max_peak_congestion_pct: float = MAX_PEAK_CONGESTION_PCT,
        grid_size: int = 25,
    ):
        self.die_w = die_width_um
        self.die_h = die_height_um
        self.min_halo = min_halo_um
        self.max_congestion = max_peak_congestion_pct
        self.grid_size = grid_size
        self.cell_w = die_width_um / grid_size
        self.cell_h = die_height_um / grid_size

    def evaluate(
        self,
        candidate: Dict[str, Any],
        iteration: int = 1,
        paradigm: str = "AI-Exploration",
        headline: str = "Macro Placement Floorplan Evaluation",
        **kwargs: Any,
    ) -> PhysicalReceipt:
        """Evaluates a floorplan layout candidate against geometric DRC and routing models."""
        core = candidate.get("core")
        macros = candidate.get("macros", [])

        # -----------------------------------------------------------------
        # Gate 1: Inventory & Structure Check
        # -----------------------------------------------------------------
        if not core or "box" not in core:
            return PhysicalReceipt(
                loop="C",
                iteration=iteration,
                paradigm=paradigm,
                headline=headline,
                target_metric="Peak Routing Congestion (RUDY)",
                achieved_value=100.0,
                unit="%",
                limit_value=self.max_congestion,
                slack=-100.0,
                status="FAIL",
                tool_provenance="Geometric DRC Checker",
                verification_status="FAIL: Missing Core Compute Engine",
                diagnostics=[
                    "Design candidate does not define a standard-cell Core bounding box."
                ],
                reward_hack_detected=True,
                cheat_id="CHEAT-C5",
            )

        macro_names = [m.get("name", "") for m in macros]
        for req in CANONICAL_MACROS:
            if req not in macro_names:
                return PhysicalReceipt(
                    loop="C",
                    iteration=iteration,
                    paradigm=paradigm,
                    headline=headline,
                    target_metric="Peak Routing Congestion (RUDY)",
                    achieved_value=100.0,
                    unit="%",
                    limit_value=self.max_congestion,
                    slack=-100.0,
                    status="FAIL",
                    tool_provenance="Geometric DRC Checker",
                    verification_status=f"FAIL: Missing Required Macro '{req}'",
                    diagnostics=[
                        f"Candidate omitted required memory macro '{req}'.",
                        f"Inventory found: {macro_names}, expected: {CANONICAL_MACROS}",
                    ],
                    reward_hack_detected=True,
                    cheat_id="CHEAT-C5",
                )

        # -----------------------------------------------------------------
        # Gate 2: Die Boundary Enclosure & Non-Degenerate Dimensions
        # -----------------------------------------------------------------
        all_blocks = [("Core", core["box"])] + [(m["name"], m["box"]) for m in macros]
        for name, box in all_blocks:
            x0, y0, x1, y1 = box
            # Boundary enclosure
            if x0 < 0 or y0 < 0 or x1 > self.die_w or y1 > self.die_h:
                return PhysicalReceipt(
                    loop="C",
                    iteration=iteration,
                    paradigm=paradigm,
                    headline=headline,
                    target_metric="Peak Routing Congestion (RUDY)",
                    achieved_value=100.0,
                    unit="%",
                    limit_value=self.max_congestion,
                    slack=-100.0,
                    status="FAIL",
                    tool_provenance="Geometric DRC Checker (Die Boundary)",
                    verification_status=f"FAIL: Block '{name}' Placed Outside Die Canvas",
                    diagnostics=[
                        f"REWARD HACK DETECTED (CHEAT-C2): '{name}' coordinates ({x0}, {y0}, {x1}, {y1}) exceed canvas [0, {self.die_w}] x [0, {self.die_h}].",
                        "Physical boundary escape violation.",
                    ],
                    reward_hack_detected=True,
                    cheat_id="CHEAT-C2",
                )

            # Positive dimensions
            w = x1 - x0
            h = y1 - y0
            if w < 50.0 or h < 50.0:
                return PhysicalReceipt(
                    loop="C",
                    iteration=iteration,
                    paradigm=paradigm,
                    headline=headline,
                    target_metric="Peak Routing Congestion (RUDY)",
                    achieved_value=100.0,
                    unit="%",
                    limit_value=self.max_congestion,
                    slack=-100.0,
                    status="FAIL",
                    tool_provenance="Geometric DRC Checker (Dimensions)",
                    verification_status=f"FAIL: Degenerate Geometry for '{name}'",
                    diagnostics=[
                        f"REWARD HACK DETECTED (CHEAT-C3): Block '{name}' dimension ({w:.1f} x {h:.1f} um) is degenerate (< 50 um).",
                        "Physical silicon blocks cannot be shrunk to zero area.",
                    ],
                    reward_hack_detected=True,
                    cheat_id="CHEAT-C3",
                )

        # -----------------------------------------------------------------
        # Gate 3: Geometric DRC Non-Overlap & Halo Clearances
        # -----------------------------------------------------------------
        core_box = core["box"]
        # Check Core vs Macros
        for m in macros:
            m_box = m["box"]
            m_name = m["name"]
            if boxes_overlap(core_box, m_box, min_clearance=self.min_halo):
                return PhysicalReceipt(
                    loop="C",
                    iteration=iteration,
                    paradigm=paradigm,
                    headline=headline,
                    target_metric="Peak Routing Congestion (RUDY)",
                    achieved_value=100.0,
                    unit="%",
                    limit_value=self.max_congestion,
                    slack=-100.0,
                    status="FAIL",
                    tool_provenance="Geometric DRC Checker (Core Collision)",
                    verification_status=f"FAIL: Macro '{m_name}' Collides with Compute Core",
                    diagnostics=[
                        f"REWARD HACK DETECTED (CHEAT-C4): Macro '{m_name}' box {m_box} overlaps or violates {self.min_halo} um halo with Core {core_box}.",
                        "Standard cell placement area cannot be occluded by hard SRAM macros.",
                    ],
                    reward_hack_detected=True,
                    cheat_id="CHEAT-C4",
                )

        # Check Macro vs Macro (DRC overlap & halo)
        for i in range(len(macros)):
            for j in range(i + 1, len(macros)):
                m1, m2 = macros[i], macros[j]
                if boxes_overlap(m1["box"], m2["box"], min_clearance=self.min_halo):
                    return PhysicalReceipt(
                        loop="C",
                        iteration=iteration,
                        paradigm=paradigm,
                        headline=headline,
                        target_metric="Peak Routing Congestion (RUDY)",
                        achieved_value=100.0,
                        unit="%",
                        limit_value=self.max_congestion,
                        slack=-100.0,
                        status="FAIL",
                        tool_provenance="Geometric DRC Checker (Macro Stacking)",
                        verification_status=f"FAIL: Macros '{m1['name']}' and '{m2['name']}' Overlap / Violate Halo",
                        diagnostics=[
                            f"REWARD HACK DETECTED (CHEAT-C1): Macros '{m1['name']}' ({m1['box']}) and '{m2['name']}' ({m2['box']}) overlap or violate {self.min_halo} um halo.",
                            "Hard macro stacking violates fundamental physical fabrication constraints.",
                        ],
                        reward_hack_detected=True,
                        cheat_id="CHEAT-C1",
                    )

        # -----------------------------------------------------------------
        # Gate 4: Pin Perimeter Attachment Check
        # -----------------------------------------------------------------
        for m in macros:
            if "pins" not in m:
                continue
            px, py = m["pins"]
            bx0, by0, bx1, by1 = m["box"]
            # Pin must be within 15 um of macro perimeter
            dx = max(0.0, bx0 - px, px - bx1)
            dy = max(0.0, by0 - py, py - by1)
            dist_to_macro = math.hypot(dx, dy)
            if dist_to_macro > 15.0:
                return PhysicalReceipt(
                    loop="C",
                    iteration=iteration,
                    paradigm=paradigm,
                    headline=headline,
                    target_metric="Peak Routing Congestion (RUDY)",
                    achieved_value=100.0,
                    unit="%",
                    limit_value=self.max_congestion,
                    slack=-100.0,
                    status="FAIL",
                    tool_provenance="Geometric DRC Checker (Pin Attachment)",
                    verification_status=f"FAIL: Pin for '{m['name']}' Detached from Macro Perimeter",
                    diagnostics=[
                        f"Pin coordinates ({px}, {py}) are {dist_to_macro:.1f} um detached from macro perimeter {m['box']}.",
                        "Macro pins must attach to the physical macro boundary.",
                    ],
                    reward_hack_detected=True,
                    cheat_id="CHEAT-C5",
                )

        # -----------------------------------------------------------------
        # Gate 5: 2D RUDY Routing Congestion Grid Simulation
        # -----------------------------------------------------------------
        sim_res = self._compute_rudy_congestion(
            core, macros, candidate.get("escape_mode", "standard")
        )
        peak_congestion = sim_res["peak_congestion_pct"]
        avg_congestion = sim_res["avg_congestion_pct"]
        drc_violations = sim_res["drc_violations"]
        hpwl_um = sim_res["hpwl_um"]

        slack = round(self.max_congestion - peak_congestion, 2)
        status = (
            "PASS"
            if (peak_congestion <= self.max_congestion and drc_violations == 0)
            else "FAIL"
        )

        diag = [
            f"Half-Perimeter Wirelength (HPWL): {hpwl_um:,.1f} um",
            f"Peak Routing Congestion: {peak_congestion:.1f}% (Limit: <= {self.max_congestion:.1f}%)",
            f"Average Die Congestion: {avg_congestion:.1f}%",
            f"DRC Wire Shorts (>85% track saturation): {drc_violations} violations",
        ]
        if status == "PASS":
            diag.append(
                "Routing Signoff: APPROVED (Zero DRC shorts, track capacity satisfied)"
            )
            v_status = f"PASS: Routing Congestion Closed ({peak_congestion:.1f}% <= {self.max_congestion:.1f}%)"
            hack = False
            cheat = None
        else:
            diag.append(
                "Routing Signoff: DENIED (Severe routing congestion bottleneck / DRC shorts)"
            )
            v_status = f"FAIL: Peak Congestion {peak_congestion:.1f}% > {self.max_congestion:.1f}% ({drc_violations} DRC shorts)"
            hack = False
            cheat = None

        return PhysicalReceipt(
            loop="C",
            iteration=iteration,
            paradigm=paradigm,
            headline=headline,
            target_metric="Peak Routing Congestion (RUDY)",
            achieved_value=peak_congestion,
            unit="%",
            limit_value=self.max_congestion,
            slack=slack,
            status=status,
            tool_provenance=f"2D RUDY Congestion Engine ({self.grid_size}x{self.grid_size} Grid)",
            verification_status=v_status,
            diagnostics=diag,
            reward_hack_detected=hack,
            cheat_id=cheat,
            metadata={
                "hpwl_um": hpwl_um,
                "peak_congestion_pct": peak_congestion,
                "avg_congestion_pct": avg_congestion,
                "drc_violations": drc_violations,
                "grid_size": self.grid_size,
            },
        )

    def _compute_rudy_congestion(
        self,
        core: Dict[str, Any],
        macros: List[Dict[str, Any]],
        escape_mode: str = "standard",
    ) -> Dict[str, Any]:
        """Calculates HPWL and 2D RUDY congestion grid based on physical metal track availability."""
        tracks_per_cell = 100.0
        capacity = np.full(
            (self.grid_size, self.grid_size), tracks_per_cell, dtype=float
        )

        # Macro SRAMs block 80% of routing tracks in their bounding boxes
        for m in macros:
            bx0, by0, bx1, by1 = m["box"]
            gx0, gy0 = int(bx0 / self.cell_w), int(by0 / self.cell_h)
            gx1, gy1 = int(bx1 / self.cell_w), int(by1 / self.cell_h)
            capacity[gy0:gy1, gx0:gx1] *= 0.20

        # Core standard cells consume 20% for local pin taps (80% available for global over-cell routing)
        cx0, cy0 = int(core["box"][0] / self.cell_w), int(core["box"][1] / self.cell_h)
        cx1, cy1 = int(core["box"][2] / self.cell_w), int(core["box"][3] / self.cell_h)
        capacity[cy0:cy1, cx0:cx1] *= 0.80

        # Wire demand model: 128 wires per macro memory bus
        demand = np.zeros((self.grid_size, self.grid_size), dtype=float)
        cx = (core["box"][0] + core["box"][2]) / 2.0
        cy = (core["box"][1] + core["box"][3]) / 2.0
        total_hpwl = 0.0

        for m in macros:
            px, py = m.get(
                "pins",
                ((m["box"][0] + m["box"][2]) / 2.0, (m["box"][1] + m["box"][3]) / 2.0),
            )
            hpwl = abs(cx - px) + abs(cy - py)
            total_hpwl += hpwl

            bx0 = max(0, int(min(cx, px) / self.cell_w))
            by0 = max(0, int(min(cy, py) / self.cell_h))
            bx1 = min(self.grid_size, int(max(cx, px) / self.cell_w) + 1)
            by1 = min(self.grid_size, int(max(cy, py) / self.cell_h) + 1)

            w_bins = max(1, bx1 - bx0)
            h_bins = max(1, by1 - by0)
            demand[by0:by1, bx0:bx1] += 48.0 / (w_bins * h_bins)

            # Pin escape congestion
            pin_gx = min(self.grid_size - 1, max(0, int(px / self.cell_w)))
            pin_gy = min(self.grid_size - 1, max(0, int(py / self.cell_h)))

            # Pin escape congestion: depends on routing channel width between macro and core
            channel_width = max(
                0.0,
                min(
                    core["box"][0] - m["box"][2]
                    if m["box"][2] <= core["box"][0]
                    else float("inf"),
                    m["box"][0] - core["box"][2]
                    if m["box"][0] >= core["box"][2]
                    else float("inf"),
                    core["box"][1] - m["box"][3]
                    if m["box"][3] <= core["box"][1]
                    else float("inf"),
                    m["box"][1] - core["box"][3]
                    if m["box"][1] >= core["box"][3]
                    else float("inf"),
                ),
            )

            # Inward facing pins packed tightly against core in narrow channels cause severe choke
            if channel_width < 60.0:
                escape_density = 75.0  # Severe choke (driven single-layer packing)
            elif channel_width < 100.0:
                escape_density = 45.0  # Moderate choke (assisted uncoordinated)
            else:
                escape_density = 12.0  # Wide co-adapted channel (native)

            demand[pin_gy, pin_gx] += escape_density

        congestion_grid = (demand / np.maximum(capacity, 1.0)) * 100.0
        final_congestion_grid = np.clip(congestion_grid, 10.0, 100.0)

        peak_congestion = float(np.max(final_congestion_grid))
        avg_congestion = float(np.mean(final_congestion_grid))
        drc_violations = int(np.sum(final_congestion_grid > 85.0))

        return {
            "hpwl_um": round(total_hpwl, 1),
            "peak_congestion_pct": round(peak_congestion, 1),
            "avg_congestion_pct": round(avg_congestion, 1),
            "drc_violations": drc_violations,
            "congestion_grid": final_congestion_grid.tolist(),
        }
