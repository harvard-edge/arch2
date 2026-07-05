"""Shared plotting style for executable Quarto figures."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
from textwrap import wrap

STYLE_PATH = Path(__file__).resolve().parents[1] / "_styles" / "arch2.mplstyle"
FONT_DIR = Path(__file__).resolve().parents[1] / "_fonts"

# Preferred sans-serif stack for every figure, matching the SVG diagrams
# ("Arial, Helvetica, sans-serif"). Arimo and Liberation Sans are open,
# metric-compatible substitutes for machines without Arial (e.g. CI/Linux).
BRAND_SANS = [
    "Arimo",
    "Arial",
    "Liberation Sans",
    "Helvetica Neue",
    "Helvetica",
    "DejaVu Sans",
]


COLORS = {
    "blue": "#4C78A8",
    "green": "#54A24B",
    "orange": "#D88A30",
    "purple": "#7E6AA8",
    "red": "#E15759",
    "brown": "#8C6D31",
    "ink": "#222222",
    "muted": "#444444",
    "grid": "#D7DEE5",
    "row": "#E4E8ED",
    "note_text": "#356C8C",
    "note_edge": "#356C8C",
    "note_fill": "#F5FAFD",
    "design_cost_fill": "#E9F1FA",
}


def _register_brand_fonts() -> None:
    """Make Arial-family fonts resolvable by name in this interpreter.

    matplotlib does not always index system Arial/Helvetica by name, so the
    style's font stack can silently fall back to DejaVu Sans. Register any
    vendored fonts plus matching system fonts so figures embed the same
    sans-serif family as the SVG diagrams.
    """

    candidates: list[str] = []
    if FONT_DIR.is_dir():
        candidates += [str(p) for p in sorted(FONT_DIR.glob("*.tt[fc]"))]
    wanted = ("arimo", "arial", "liberationsans", "helvetica")
    try:
        for path in fm.findSystemFonts():
            name = Path(path).name.lower().replace(" ", "")
            if any(token in name for token in wanted):
                candidates.append(path)
    except Exception:
        pass
    for path in candidates:
        try:
            fm.fontManager.addfont(path)
        except Exception:
            pass


def apply_style() -> None:
    """Apply the house style for Architecture 2.0 matplotlib figures."""

    _register_brand_fonts()
    plt.style.use(STYLE_PATH)
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = BRAND_SANS


def top_log_axis(
    ax,
    *,
    xlim: tuple[float, float],
    xticks: list[float],
    xticklabels: list[str],
    xlabel: str,
    tick_fontsize: float = 6.2,
    label_fontsize: float = 7,
) -> None:
    """Use a top-oriented log axis for compact scale-comparison plots."""

    ax.set_xscale("log")
    ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel, fontsize=label_fontsize, labelpad=6)
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels, fontsize=tick_fontsize)
    ax.tick_params(axis="x", length=2.5, width=0.6, pad=2)
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.55)

    for spine in ["left", "right", "bottom"]:
        ax.spines[spine].set_visible(False)
    ax.spines["top"].set_color(COLORS["ink"])
    ax.spines["top"].set_linewidth(0.7)


def row_axis(ax, row_count: int) -> None:
    """Set the shared y-axis treatment for labeled horizontal row plots."""

    ax.set_ylim(-0.65, row_count - 0.35)
    ax.invert_yaxis()
    ax.set_yticks([])


def draw_range_rows(
    ax,
    rows: list[dict],
    *,
    low_key: str,
    high_key: str,
    label_x: float,
    right_x: float,
    label_fontsize: float = 6.4,
    note_fontsize: float = 5.3,
    right_fontsize: float = 5.9,
    y_positions: list[float] | None = None,
    show_notes: bool = True,
    label_dy: float = -0.12,
    note_dy: float = 0.18,
) -> None:
    """Draw labeled horizontal ranges with square endpoints.

    ``label_dy`` and ``note_dy`` set the vertical offset (in row units) of the
    bold label and its sub-note from the row baseline. Increase the gap between
    them on dense plots so the two text lines do not collide.
    """

    positions = y_positions if y_positions is not None else list(range(len(rows)))
    for y, row in zip(positions, rows):
        low = row[low_key]
        high = row[high_key]
        color = row["color"]
        ax.axhline(y, color=COLORS["row"], linewidth=0.65, zorder=0)
        ax.hlines(y, low, high, color=color, linewidth=2.2, zorder=2)
        ax.scatter(
            [low, high],
            [y, y],
            marker="s",
            s=17,
            facecolor=COLORS["note_fill"],
            edgecolor=color,
            linewidth=0.9,
            zorder=3,
        )
        ax.text(
            label_x,
            y + label_dy if show_notes else y,
            row["display_label"],
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=label_fontsize,
            fontweight="bold",
            color=COLORS["ink"],
            clip_on=False,
        )
        if show_notes:
            ax.text(
                label_x,
                y + note_dy,
                row["display_note"],
                transform=ax.get_yaxis_transform(),
                ha="left",
                va="center",
                fontsize=note_fontsize,
                color=COLORS["muted"],
                clip_on=False,
            )
        ax.text(
            right_x,
            y,
            row["right_label"],
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=right_fontsize,
            fontweight="bold",
            color=color,
            clip_on=False,
        )


def add_note_box(
    fig,
    text: str,
    *,
    xywh: tuple[float, float, float, float],
    fontsize: float = 5.8,
) -> None:
    """Add the shared boxed note used under compact quantitative plots."""

    box_width_in = xywh[2] * fig.get_figwidth()
    avg_char_width_in = (fontsize / 72.0) * 0.48
    wrap_width = max(34, int((box_width_in / avg_char_width_in) * 0.78))
    wrapped_lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(
            wrap(
                line,
                width=wrap_width,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    wrapped_text = "\n".join(wrapped_lines)

    line_count = max(1, len(wrapped_lines))
    line_height_in = (fontsize / 72.0) * 1.32
    min_height = ((line_count * line_height_in) + 0.045) / fig.get_figheight()
    width, height = xywh[2], max(xywh[3], min_height)
    center_y = xywh[1] + xywh[3] / 2
    y = max(0.018, center_y - height / 2)

    note_box = Rectangle(
        (xywh[0], y),
        width,
        height,
        transform=fig.transFigure,
        facecolor=COLORS["note_fill"],
        edgecolor=COLORS["note_edge"],
        linewidth=0.6,
        clip_on=False,
        zorder=-1,
    )
    fig.add_artist(note_box)
    fig.text(
        xywh[0] + width / 2,
        y + height / 2,
        wrapped_text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        color=COLORS["note_text"],
        linespacing=1.15,
    )
