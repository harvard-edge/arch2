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

    fig, ax = plt.subplots(figsize=(7.6, 3.6), dpi=240)
    fig.subplots_adjust(left=0.07, right=0.96, top=0.91, bottom=0.13)

    ax.set_xlim(0, 10.8)
    ax.set_ylim(0, 9.4)
    xc, yc = 3.3, 3.2

    # -------------------------------------------------------------------------
    # 1. Background Grid & Framing
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
    # 2. Handles (Left of Pivot)
    # -------------------------------------------------------------------------
    t = np.linspace(0, 1, 60)

    # Upper Handle: Blue (Capacity exceeds demand before crossover)
    # Loop center: (1.45, 4.65)
    p0_bs = np.array([1.88, 4.15])
    p1_bs = np.array([2.55, 3.65])
    p2_bs = np.array([xc, yc])
    s_b = (
        (1 - t)[:, None] ** 2 * p0_bs
        + 2 * (1 - t)[:, None] * t[:, None] * p1_bs
        + t[:, None] ** 2 * p2_bs
    )

    ax.plot(
        s_b[:, 0],
        s_b[:, 1],
        color=COLORS["blue"],
        linewidth=6.0,
        solid_capstyle="round",
        zorder=3,
    )
    ax.plot(
        s_b[:, 0],
        s_b[:, 1],
        color="#EBF5F8",
        linewidth=2.8,
        solid_capstyle="round",
        zorder=4,
    )

    # Thumb loop (elliptical bow)
    thumb_outer = patches.Ellipse(
        (1.45, 4.65),
        1.25,
        1.6,
        angle=25,
        facecolor="#EBF5F8",
        edgecolor=COLORS["blue"],
        linewidth=2.8,
        zorder=5,
    )
    thumb_inner = patches.Ellipse(
        (1.45, 4.65),
        0.65,
        0.95,
        angle=25,
        facecolor="white",
        edgecolor=COLORS["blue"],
        linewidth=1.8,
        zorder=6,
    )
    ax.add_patch(thumb_outer)
    ax.add_patch(thumb_inner)

    # Lower Handle: Red (Work / Demand)
    # Loop center: (1.45, 1.75)
    p0_rs = np.array([1.88, 2.25])
    p1_rs = np.array([2.55, 2.75])
    p2_rs = np.array([xc, yc])
    s_r = (
        (1 - t)[:, None] ** 2 * p0_rs
        + 2 * (1 - t)[:, None] * t[:, None] * p1_rs
        + t[:, None] ** 2 * p2_rs
    )

    ax.plot(
        s_r[:, 0],
        s_r[:, 1],
        color=COLORS["red"],
        linewidth=6.0,
        solid_capstyle="round",
        zorder=3,
    )
    ax.plot(
        s_r[:, 0],
        s_r[:, 1],
        color="#FDF2F2",
        linewidth=2.8,
        solid_capstyle="round",
        zorder=4,
    )

    # Finger loop (elongated bow)
    finger_outer = patches.Ellipse(
        (1.45, 1.75),
        1.5,
        1.9,
        angle=-20,
        facecolor="#FDF2F2",
        edgecolor=COLORS["red"],
        linewidth=2.8,
        zorder=5,
    )
    finger_inner = patches.Ellipse(
        (1.45, 1.75),
        0.8,
        1.15,
        angle=-20,
        facecolor="white",
        edgecolor=COLORS["red"],
        linewidth=1.8,
        zorder=6,
    )
    ax.add_patch(finger_outer)
    ax.add_patch(finger_inner)

    # -------------------------------------------------------------------------
    # 3. Precision Blades & The Scissors Gap (Right of Pivot)
    # -------------------------------------------------------------------------
    tip_u = np.array([8.9, 7.8])
    tip_l = np.array([8.9, 3.5])

    # Upper Blade (Red: Demand / Work awaiting review)
    u_cut = cubic_bezier(
        np.array([xc, yc]), np.array([5.0, 4.5]), np.array([7.0, 6.1]), tip_u, 100
    )
    u_spine = cubic_bezier(
        np.array([xc, yc + 0.38]),
        np.array([4.8, 5.2]),
        np.array([6.8, 7.0]),
        tip_u,
        100,
    )
    u_bevel = cubic_bezier(
        np.array([xc + 0.3, yc + 0.22]),
        np.array([4.9, 4.85]),
        np.array([6.9, 6.55]),
        tip_u,
        100,
    )

    # Shading facets
    u_facet_upper = np.vstack([u_spine, u_bevel[::-1]])
    ax.add_patch(
        patches.Polygon(u_facet_upper, facecolor="#FEE2E2", alpha=0.95, zorder=3)
    )
    u_facet_lower = np.vstack([u_bevel, u_cut[::-1]])
    ax.add_patch(
        patches.Polygon(u_facet_lower, facecolor="#FFFFFF", alpha=0.75, zorder=3)
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
        alpha=0.5,
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
        np.array([xc, yc]), np.array([5.0, 3.25]), np.array([7.0, 3.38]), tip_l, 100
    )
    l_spine = cubic_bezier(
        np.array([xc, yc - 0.38]),
        np.array([4.8, 2.8]),
        np.array([6.8, 3.1]),
        tip_l,
        100,
    )
    l_bevel = cubic_bezier(
        np.array([xc + 0.3, yc - 0.20]),
        np.array([4.9, 3.02]),
        np.array([6.9, 3.32]),
        tip_l,
        100,
    )

    l_facet_lower = np.vstack([l_spine, l_bevel[::-1]])
    ax.add_patch(
        patches.Polygon(l_facet_lower, facecolor="#E0F2FE", alpha=0.95, zorder=3)
    )
    l_facet_upper = np.vstack([l_bevel, l_cut[::-1]])
    ax.add_patch(
        patches.Polygon(l_facet_upper, facecolor="#FFFFFF", alpha=0.75, zorder=3)
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
        alpha=0.5,
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
    # 4. The Scissors Gap (Unsettled Work Area)
    # -------------------------------------------------------------------------
    gap_poly = np.vstack([u_cut, l_cut[::-1]])
    ax.add_patch(patches.Polygon(gap_poly, facecolor="#E4F1F6", alpha=0.88, zorder=1))

    for frac in [0.25, 0.45, 0.65, 0.85]:
        gx = xc + frac * (8.9 - xc)
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
    # 5. Mechanical Fulcrum / Pivot Screw Assembly
    # -------------------------------------------------------------------------
    pivot_outer = patches.Circle(
        (xc, yc),
        0.32,
        facecolor="#E2E8F0",
        edgecolor=COLORS["ink"],
        linewidth=1.6,
        zorder=7,
    )
    pivot_mid = patches.Circle(
        (xc, yc),
        0.23,
        facecolor="#CBD5E1",
        edgecolor=COLORS["ink"],
        linewidth=1.1,
        zorder=8,
    )
    pivot_inner = patches.Circle(
        (xc, yc),
        0.15,
        facecolor="#F8FAFC",
        edgecolor=COLORS["ink"],
        linewidth=0.8,
        zorder=9,
    )
    ax.add_patch(pivot_outer)
    ax.add_patch(pivot_mid)
    ax.add_patch(pivot_inner)

    slot_angle = np.radians(38)
    r_slot = 0.12
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
    # 6. Typography & Labels
    # -------------------------------------------------------------------------
    # Upper Curve Label
    ax.text(
        6.1,
        8.1,
        "work awaiting evaluation and review",
        fontsize=8.2,
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
        2.25,
        "tool and reviewer capacity",
        fontsize=8.2,
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
        xy=(xc, yc - 0.35),
        xytext=(xc, 1.0),
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

    # Dimension Bracket on the far right
    bx = 9.15
    y_top = tip_u[1]
    y_bot = tip_l[1]
    y_mid = 0.5 * (y_top + y_bot)

    ax.plot(
        [bx, bx + 0.18, bx + 0.18, bx],
        [y_top, y_top, y_bot, y_bot],
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
        bx + 0.42,
        y_mid + 0.22,
        "unsettled work",
        fontsize=7.8,
        fontweight="bold",
        color=COLORS["workload_ink"],
        ha="left",
        va="bottom",
        zorder=6,
    )
    ax.text(
        bx + 0.42,
        y_mid - 0.22,
        "not yet evaluated\nor reviewed",
        fontsize=6.2,
        color=COLORS["muted"],
        ha="left",
        va="top",
        zorder=6,
    )

    # Headroom annotation
    ax.text(
        1.45,
        5.85,
        "Verification headroom\n(capacity exceeds generation)",
        fontsize=5.8,
        fontweight="bold",
        color=COLORS["workload_ink"],
        ha="center",
        va="bottom",
        zorder=6,
    )

    # -------------------------------------------------------------------------
    # 7. Axes Styling
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
