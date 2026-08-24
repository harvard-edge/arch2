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
    "Arial",
    "Helvetica",
    "sans-serif",
    "Arimo",
    "Liberation Sans",
    "Helvetica Neue",
    "DejaVu Sans",
]


# Canonical Arch2 figure palette (bold two-tier set; see _styles/arch2-html.scss
# for the shared source of truth). Legacy keys (blue/green/orange/purple/red)
# keep their names but now carry the new bold MARK hues so existing plot code
# stays valid while matching the SVG diagrams. Semantic role keys map each hue
# to the design-loop dimension it stands for; *_ink keys are text-safe (>=5:1 on
# white and cream) for labels and thin marks.
COLORS = {
    # MARK tier (bright fills / >=2px strokes)
    "blue": "#1683A6",  # teal  -> workload / objective (brand anchor)
    "green": "#1E9E48",  # green -> evidence / verification
    "orange": "#E68A17",  # amber -> methods / generation
    "amber": "#E68A17",  # amber alias
    "purple": "#6A4FC7",  # violet-> design space / artifact
    "red": "#DE3D3C",  # red   -> constraints / budget
    "magenta": "#D24D96",  # magenta-> decision / deliverable
    "brown": "#8A5310",  # dark amber (neutral warm)
    # Semantic role aliases (MARK)
    "workload": "#1683A6",
    "designspace": "#6A4FC7",
    "constraints": "#DE3D3C",
    "methods": "#E68A17",
    "evidence": "#1E9E48",
    "decision": "#D24D96",
    # INK tier (text-safe: colored text, labels, thin strokes)
    "workload_ink": "#136680",
    "designspace_ink": "#59429E",
    "constraints_ink": "#C62A2A",
    "methods_ink": "#8A5310",
    "evidence_ink": "#157A38",
    "decision_ink": "#A82E70",
    # Neutrals / chrome
    "ink": "#20252B",
    "muted": "#3E474B",
    "grid": "#D5DEE3",
    "row": "#E4E8ED",
    "note_text": "#136680",
    "note_edge": "#136680",
    "note_fill": "#E4F1F6",
    "design_cost_fill": "#E4F1F6",
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
    mpl.rcParams["font.size"] = 6.5
    mpl.rcParams["axes.labelsize"] = 6.5
    mpl.rcParams["axes.titlesize"] = 7.2
    mpl.rcParams["xtick.labelsize"] = 5.8
    mpl.rcParams["ytick.labelsize"] = 5.8
    mpl.rcParams["legend.fontsize"] = 5.8
    # HTML display width = figsize x dpi under Quarto's retina pipeline; 150
    # sizes data figures to roughly the text column. PDF output is vector
    # (sized by out-width), so this affects HTML only.
    mpl.rcParams["figure.dpi"] = 150


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


def clean_spines(ax, keep: tuple[str, ...] = ("bottom", "left")) -> None:
    """Standardize spine styling by hiding unkept spines and coloring kept ones."""
    for spine in ["top", "right", "left", "bottom"]:
        if spine in keep:
            ax.spines[spine].set_visible(True)
            ax.spines[spine].set_color(COLORS["ink"])
            ax.spines[spine].set_linewidth(0.7)
        else:
            ax.spines[spine].set_visible(False)


def inject_svg_font_stack(svg_path: Path | str) -> None:
    """Ensure font stack is explicitly declared in SVG for headless text rendering."""
    path = Path(svg_path)
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if '<style type="text/css">' not in text:
        text = text.replace(
            "<defs>",
            '<defs>\n  <style type="text/css">*{font-family: Arial, Helvetica, sans-serif;}</style>',
            1,
        )
        path.write_text(text, encoding="utf-8")


def save_figure_bundle(
    fig,
    output_base: Path | str,
    formats: tuple[str, ...] = ("svg", "pdf", "png"),
    dpi: int = 300,
    bbox_inches: str = "tight",
) -> dict[str, Path]:
    """Save figure to multiple formats (SVG, PDF, PNG) with consistent font stack and settings."""
    base_path = Path(output_base)
    if base_path.suffix in [".svg", ".pdf", ".png"]:
        stem = base_path.parent / base_path.stem
    else:
        stem = base_path

    saved_paths = {}
    for fmt in formats:
        target = stem.with_suffix(f".{fmt}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "png":
            fig.savefig(target, dpi=dpi, bbox_inches=bbox_inches)
        else:
            fig.savefig(target, bbox_inches=bbox_inches)
        if fmt == "svg":
            inject_svg_font_stack(target)
        saved_paths[fmt] = target

    return saved_paths


def draw_spectrum_bars(
    ax,
    categories: list[str],
    values: list[float],
    labels_fmt: list[str],
    *,
    colors: list[str] | None = None,
    height: float = 0.50,
    left: float | list[float] | None = None,
    xlim: tuple[float, float] | None = None,
    log_scale: bool = True,
    xlabel: str | None = None,
    threshold_inside: float = 1e10,
    bar_edgecolor: str | None = None,
    in_bar_color: str = "#ffffff",
    out_bar_color: str | None = None,
    fontsize: float = 5.8,
) -> None:
    """Draw standardized horizontal spectrum bars with calibrated inside/outside labels."""
    y_pos = list(range(len(categories)))

    if colors is None:
        default_palette = [
            COLORS["ink"],
            COLORS["workload"],
            COLORS["evidence"],
            COLORS["designspace"],
            COLORS["constraints"],
        ]
        colors = [
            default_palette[i % len(default_palette)] for i in range(len(categories))
        ]

    if out_bar_color is None:
        out_bar_color = COLORS["ink"]

    bar_kwargs = {
        "height": height,
        "color": colors,
        "zorder": 3,
    }
    if bar_edgecolor is not None:
        bar_kwargs["edgecolor"] = bar_edgecolor
        bar_kwargs["linewidth"] = 0.6

    if left is not None:
        bars = ax.barh(y_pos[::-1], values, left=left, **bar_kwargs)
    else:
        bars = ax.barh(y_pos[::-1], values, **bar_kwargs)

    if log_scale:
        ax.set_xscale("log")

    if xlim is not None:
        ax.set_xlim(*xlim)

    ax.set_yticks(y_pos[::-1])
    ax.set_yticklabels(categories, fontsize=6.2, fontweight="bold", color=COLORS["ink"])

    if xlabel:
        ax.set_xlabel(xlabel, fontsize=6.5, color=COLORS["ink"])

    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.55, zorder=0)
    clean_spines(ax, keep=("bottom", "left"))

    for bar, val, lbl in zip(bars, values, labels_fmt):
        y_center = bar.get_y() + bar.get_height() / 2
        if val >= threshold_inside:
            ax.text(
                val / 1.45,
                y_center,
                lbl,
                va="center",
                ha="right",
                fontsize=fontsize,
                fontweight="bold",
                color=in_bar_color,
                zorder=4,
            )
        else:
            ax.text(
                val * 1.35,
                y_center,
                lbl,
                va="center",
                ha="left",
                fontsize=fontsize,
                fontweight="bold",
                color=out_bar_color,
                zorder=4,
            )
