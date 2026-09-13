#!/usr/bin/env python3
"""
Generate fig-scissors-gap: Unchecked candidate generation outpaces evaluation capacity.
--------------------------------------------------------------------------------------
A precision technical scissors plot illustrating the "Scissors Gap" in AI-native architecture.
As candidate generation velocity accelerates, physical evaluation and reviewer throughput scale
sub-linearly, creating a widening wedge of unverified, unsettled candidates.

Outputs:
  - fig-scissors-gap.pdf
  - fig-scissors-gap.svg
  - fig-scissors-gap.png
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy.interpolate import splprep, splev
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book._python.plots import COLORS, apply_style

apply_style()


def cubic_bezier(p0, p1, p2, p3, n=100):
    t = np.linspace(0, 1, n)[:, None]
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t**2 * p2
        + t**3 * p3
    )


def generate_scissors_figure(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    out_pdf = output_dir / "fig-scissors-gap.pdf"
    out_svg = output_dir / "fig-scissors-gap.svg"
    out_png = output_dir / "fig-scissors-gap.png"

    fig, ax = plt.subplots(figsize=(7.6, 3.65), dpi=240)
    fig.subplots_adjust(left=0.07, right=0.96, top=0.91, bottom=0.13)

    ax.set_xlim(0, 10.8)
    ax.set_ylim(0, 9.4)
    xc, yc = 3.30, 3.20

    # -------------------------------------------------------------------------
    # 0. Background House Grid
    # -------------------------------------------------------------------------
    for gx in np.arange(2.0, 9.5, 1.0):
        ax.axvline(
            gx,
            color=COLORS["grid"],
            linewidth=0.55,
            linestyle="--",
            alpha=0.55,
            zorder=0,
        )
    for gy in np.arange(1.5, 8.5, 1.0):
        ax.axhline(
            gy,
            color=COLORS["grid"],
            linewidth=0.55,
            linestyle="--",
            alpha=0.55,
            zorder=0,
        )

    # -------------------------------------------------------------------------
    # 1. Precision Shears Handles (Bows & Shanks)
    # -------------------------------------------------------------------------
    theta = np.linspace(0, 2 * np.pi, 150)

    # --- BLUE UPPER HANDLE (Thumb Bow) ---
    c_ux, c_uy = 1.35, 4.60
    ang_u = np.radians(20)
    rx_in_u, ry_in_u = 0.40, 0.58

    inner_thumb_x = (
        c_ux
        + rx_in_u * np.cos(theta) * np.cos(ang_u)
        - ry_in_u * np.sin(theta) * np.sin(ang_u)
    )
    inner_thumb_y = (
        c_uy
        + rx_in_u * np.cos(theta) * np.sin(ang_u)
        + ry_in_u * np.sin(theta) * np.cos(ang_u)
    )

    blue_pts = np.array(
        [
            [xc - 0.12, yc + 0.38],  # shank top at pivot boss
            [2.52, 4.18],  # upper shank neck
            [1.96, 4.88],  # outer bow top-right
            [1.42, 5.34],  # bow crown
            [0.78, 4.96],  # bow outer top-left
            [0.64, 4.36],  # bow outer left
            [0.86, 3.78],  # bow outer bottom-left
            [1.44, 3.70],  # bow outer bottom
            [2.15, 3.76],  # lower shank neck
            [xc - 0.12, yc + 0.08],  # shank bottom at pivot boss (strictly above yc)
        ]
    )
    tck_b, _ = splprep([blue_pts[:, 0], blue_pts[:, 1]], s=0, per=True)
    u_fine = np.linspace(0, 1, 300)
    xb_fine, yb_fine = splev(u_fine, tck_b)

    # --- RED LOWER HANDLE (Drop-Forged Ergonomic Finger Bow) ---
    c_lx, c_ly = 1.48, 1.82
    ang_l = np.radians(-18)
    rx_in_l, ry_in_l = 0.46, 0.72

    inner_finger_x = (
        c_lx
        + rx_in_l * np.cos(theta) * np.cos(ang_l)
        - ry_in_l * np.sin(theta) * np.sin(ang_l)
    )
    inner_finger_y = (
        c_ly
        + rx_in_l * np.cos(theta) * np.sin(ang_l)
        + ry_in_l * np.sin(theta) * np.cos(ang_l)
    )

    red_pts = np.array(
        [
            [xc - 0.12, yc - 0.08],  # shank top at pivot boss (strictly below yc)
            [2.55, 2.70],  # upper shank neck
            [1.95, 2.75],  # bow top-right
            [1.48, 2.78],  # bow top crown
            [0.82, 2.58],  # bow upper-left
            [0.46, 1.95],  # bow mid-left (strictly convex curvature)
            [0.38, 1.35],  # bow lower-left heel
            [0.46, 0.88],  # bow bottom-left transition
            [1.15, 0.78],  # bow bottom crown
            [1.85, 1.02],  # bow bottom-right transition
            [2.45, 1.85],  # lower shank neck
            [xc - 0.12, yc - 0.38],  # shank bottom at pivot boss
        ]
    )
    tck_r, _ = splprep([red_pts[:, 0], red_pts[:, 1]], s=0, per=True)
    xr_fine, yr_fine = splev(u_fine, tck_r)

    # Render handle bodies
    ax.fill(
        xb_fine,
        yb_fine,
        facecolor="#EBF5F8",
        edgecolor=COLORS["blue"],
        linewidth=2.2,
        zorder=3,
    )
    ax.fill(
        inner_thumb_x,
        inner_thumb_y,
        facecolor="white",
        edgecolor=COLORS["blue"],
        linewidth=1.6,
        zorder=4,
    )

    ax.fill(
        xr_fine,
        yr_fine,
        facecolor="#FDF2F2",
        edgecolor=COLORS["red"],
        linewidth=2.2,
        zorder=3,
    )
    ax.fill(
        inner_finger_x,
        inner_finger_y,
        facecolor="white",
        edgecolor=COLORS["red"],
        linewidth=1.6,
        zorder=4,
    )

    # -------------------------------------------------------------------------
    # 2. Precision Sculpted Blades
    # -------------------------------------------------------------------------
    tip_u = np.array([8.95, 7.85])
    tip_l = np.array([8.95, 3.55])

    # Upper Blade (Red: Demand / Work awaiting review)
    u_cut = cubic_bezier(
        np.array([xc, yc]), np.array([5.1, 4.60]), np.array([7.1, 6.20]), tip_u, 100
    )
    u_spine = cubic_bezier(
        np.array([xc, yc + 0.44]),
        np.array([4.85, 5.35]),
        np.array([6.85, 7.12]),
        tip_u,
        100,
    )
    u_bevel = cubic_bezier(
        np.array([xc + 0.38, yc + 0.26]),
        np.array([4.95, 4.95]),
        np.array([6.95, 6.65]),
        tip_u,
        100,
    )

    u_facet_upper = np.vstack([u_spine, u_bevel[::-1]])
    ax.add_patch(
        patches.Polygon(u_facet_upper, facecolor="#FEE2E2", alpha=0.95, zorder=3)
    )
    u_facet_lower = np.vstack([u_bevel, u_cut[::-1]])
    ax.add_patch(
        patches.Polygon(u_facet_lower, facecolor="#FFFFFF", alpha=0.85, zorder=3)
    )

    ax.plot(
        u_spine[:, 0],
        u_spine[:, 1],
        color=COLORS["red"],
        linewidth=1.5,
        alpha=0.85,
        zorder=4,
    )
    ax.plot(
        u_bevel[:, 0],
        u_bevel[:, 1],
        color=COLORS["red"],
        linewidth=0.8,
        linestyle="--",
        alpha=0.55,
        zorder=4,
    )
    ax.plot(
        u_cut[:, 0],
        u_cut[:, 1],
        color=COLORS["red"],
        linewidth=3.4,
        solid_capstyle="round",
        zorder=5,
    )

    # Lower Blade (Blue: Capacity / Review & verification throughput)
    l_cut = cubic_bezier(
        np.array([xc, yc]), np.array([5.1, 3.28]), np.array([7.1, 3.42]), tip_l, 100
    )
    l_spine = cubic_bezier(
        np.array([xc, yc - 0.44]),
        np.array([4.9, 2.65]),
        np.array([7.0, 3.02]),
        tip_l,
        100,
    )
    l_bevel = cubic_bezier(
        np.array([xc + 0.38, yc - 0.22]),
        np.array([4.98, 2.96]),
        np.array([7.02, 3.22]),
        tip_l,
        100,
    )

    l_facet_lower = np.vstack([l_spine, l_bevel[::-1]])
    ax.add_patch(
        patches.Polygon(l_facet_lower, facecolor="#D9EDF7", alpha=0.98, zorder=3)
    )
    l_facet_upper = np.vstack([l_bevel, l_cut[::-1]])
    ax.add_patch(
        patches.Polygon(l_facet_upper, facecolor="#F0F9FF", alpha=0.95, zorder=3)
    )

    ax.plot(
        l_spine[:, 0],
        l_spine[:, 1],
        color=COLORS["blue"],
        linewidth=1.5,
        alpha=0.85,
        zorder=4,
    )
    ax.plot(
        l_bevel[:, 0],
        l_bevel[:, 1],
        color=COLORS["blue"],
        linewidth=0.8,
        linestyle="--",
        alpha=0.55,
        zorder=4,
    )
    ax.plot(
        l_cut[:, 0],
        l_cut[:, 1],
        color=COLORS["blue"],
        linewidth=3.4,
        solid_capstyle="round",
        zorder=5,
    )

    # -------------------------------------------------------------------------
    # 3. The Scissors Gap (Filled Area)
    # -------------------------------------------------------------------------
    gap_poly = np.vstack([u_cut, l_cut[::-1]])
    ax.add_patch(patches.Polygon(gap_poly, facecolor="#E4F1F6", alpha=0.88, zorder=1))

    for frac in [0.25, 0.45, 0.65, 0.85]:
        gx = xc + frac * (8.95 - xc)
        idx = int(frac * 99)
        ax.plot(
            [gx, gx],
            [l_cut[idx, 1], u_cut[idx, 1]],
            color="#BEDAE5",
            linewidth=0.7,
            linestyle=":",
            alpha=0.75,
            zorder=2,
        )

    # -------------------------------------------------------------------------
    # 4. Precision Mechanical Pivot Assembly
    # -------------------------------------------------------------------------
    pivot_boss = patches.Circle(
        (xc, yc),
        0.46,
        facecolor="#F1F5F9",
        edgecolor=COLORS["ink"],
        linewidth=1.0,
        zorder=6,
    )
    pivot_outer = patches.Circle(
        (xc, yc),
        0.34,
        facecolor="#E2E8F0",
        edgecolor=COLORS["ink"],
        linewidth=1.6,
        zorder=7,
    )
    pivot_mid = patches.Circle(
        (xc, yc),
        0.24,
        facecolor="#CBD5E1",
        edgecolor=COLORS["ink"],
        linewidth=1.1,
        zorder=8,
    )
    pivot_inner = patches.Circle(
        (xc, yc),
        0.16,
        facecolor="#F8FAFC",
        edgecolor=COLORS["ink"],
        linewidth=0.8,
        zorder=9,
    )
    ax.add_patch(pivot_boss)
    ax.add_patch(pivot_outer)
    ax.add_patch(pivot_mid)
    ax.add_patch(pivot_inner)

    slot_angle = np.radians(38)
    r_slot = 0.13
    dx = r_slot * np.cos(slot_angle)
    dy = r_slot * np.sin(slot_angle)
    ax.plot(
        [xc - dx, xc + dx],
        [yc - dy, yc + dy],
        color=COLORS["ink"],
        linewidth=1.8,
        solid_capstyle="round",
        zorder=10,
    )

    # -------------------------------------------------------------------------
    # 5. Editorial Typography & Balanced Badges
    # -------------------------------------------------------------------------
    # Upper Curve Label
    ax.text(
        6.1,
        7.55,
        "work awaiting evaluation and review",
        fontsize=8.0,
        fontweight="bold",
        color=COLORS["red"],
        ha="center",
        va="bottom",
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor=COLORS["red"],
            lw=0.6,
            alpha=0.96,
        ),
        zorder=11,
    )

    # Lower Curve Label
    ax.text(
        6.1,
        2.05,
        "tool and reviewer capacity",
        fontsize=8.0,
        fontweight="bold",
        color=COLORS["blue"],
        ha="center",
        va="top",
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor=COLORS["blue"],
            lw=0.6,
            alpha=0.96,
        ),
        zorder=11,
    )

    # Pivot Callout
    ax.annotate(
        "Crossover / Fulcrum\n(generation matches capacity)",
        xy=(xc, yc - 0.46),
        xytext=(xc, 0.95),
        textcoords="data",
        fontsize=6.2,
        fontweight="bold",
        color=COLORS["ink"],
        ha="center",
        va="top",
        bbox=dict(
            boxstyle="round,pad=0.28",
            facecolor="white",
            edgecolor=COLORS["grid"],
            lw=0.7,
            alpha=0.96,
        ),
        arrowprops=dict(arrowstyle="->", color=COLORS["ink"], lw=0.9, shrinkB=4),
        zorder=12,
    )

    # Gap Label
    ax.text(
        6.5,
        5.0,
        "THE SCISSORS GAP",
        fontsize=8.8,
        fontweight="bold",
        color=COLORS["workload_ink"],
        ha="center",
        va="center",
        zorder=6,
    )
    ax.text(
        6.5,
        4.45,
        "Widening backlog of unverified candidates",
        fontsize=6.2,
        fontstyle="italic",
        color=COLORS["workload_ink"],
        ha="center",
        va="center",
        zorder=6,
    )

    # Right side curly bracket
    bx = 9.15
    y_top = tip_u[1]
    y_bot = tip_l[1]
    y_mid = (y_top + y_bot) / 2.0

    ax.plot(
        [bx, bx + 0.18], [y_top, y_top], color=COLORS["blue"], linewidth=1.8, zorder=6
    )
    ax.plot(
        [bx, bx + 0.18], [y_bot, y_bot], color=COLORS["blue"], linewidth=1.8, zorder=6
    )
    ax.plot(
        [bx + 0.18, bx + 0.18],
        [y_bot, y_top],
        color=COLORS["blue"],
        linewidth=1.8,
        zorder=6,
    )
    ax.plot(
        [bx + 0.18, bx + 0.28],
        [y_mid, y_mid],
        color=COLORS["blue"],
        linewidth=1.8,
        zorder=6,
    )

    ax.text(
        bx + 0.38,
        y_mid + 0.25,
        "unsettled work",
        fontsize=8.6,
        fontweight="bold",
        color=COLORS["blue"],
        va="center",
        zorder=6,
    )
    ax.text(
        bx + 0.38,
        y_mid - 0.25,
        "not yet evaluated\nor reviewed",
        fontsize=6.4,
        color=COLORS["ink"],
        va="top",
        zorder=6,
    )

    # Headroom annotations
    ax.text(
        1.35,
        5.95,
        "Verification headroom\n(capacity exceeds generation)",
        fontsize=5.8,
        fontweight="bold",
        color=COLORS["workload_ink"],
        ha="center",
        va="bottom",
        zorder=6,
    )
    ax.text(
        1.48,
        0.45,
        "Tractable initial volume",
        fontsize=5.8,
        fontweight="bold",
        color=COLORS["constraints_ink"],
        ha="center",
        va="top",
        zorder=6,
    )

    # -------------------------------------------------------------------------
    # 6. Axes Styling
    # -------------------------------------------------------------------------
    ax.set_xlabel(
        "increasing design scope and result volume",
        fontsize=7.4,
        color=COLORS["ink"],
        labelpad=8,
    )
    ax.set_ylabel(
        "relative work and capacity", fontsize=7.4, color=COLORS["ink"], labelpad=8
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)

    ax.set_xticks([])
    ax.set_yticks([])

    fig.savefig(out_png, dpi=240, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated:\n  {out_pdf}\n  {out_svg}\n  {out_png}")


if __name__ == "__main__":
    target_dir = (
        REPO_ROOT / "book" / "contents" / "chapters" / "02-pressures" / "images"
    )
    generate_scissors_figure(target_dir)
