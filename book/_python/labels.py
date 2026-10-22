"""Lightweight greedy label placer with leader lines (no adjustText needed)."""


def _overlap(a, b):
    dx = min(a.x1, b.x1) - max(a.x0, b.x0)
    dy = min(a.y1, b.y1) - max(a.y0, b.y0)
    return max(0, dx) * max(0, dy)


def place_labels(
    ax,
    fig,
    items,
    *,
    fontsize=5.0,
    color="#20252B",
    radius=(12, 20),
    leader_color="#8A95A0",
):
    """items: list of (x_data, y_data, text). Greedily choose an offset direction
    for each label that minimizes overlap with already-placed labels and with the
    point cloud, then draw a thin leader line from the point to the label."""
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    ax_bb = ax.get_window_extent(rend)

    def _out_of_bounds(bb):
        # total area of the label bbox that spills outside the axes rectangle
        left = max(0, ax_bb.x0 - bb.x0)
        right = max(0, bb.x1 - ax_bb.x1)
        bottom = max(0, ax_bb.y0 - bb.y0)
        top = max(0, bb.y1 - ax_bb.y1)
        h = bb.y1 - bb.y0
        w = bb.x1 - bb.x0
        return (left + right) * h + (bottom + top) * w

    # obstacle boxes = all plotted point markers (approx as small squares)
    pt_boxes = []
    for coll in ax.collections:
        for px, py in coll.get_offsets():
            dx, dy = ax.transData.transform((px, py))
            pt_boxes.append((dx, dy))

    import math

    dirs = []
    for ang in range(0, 360, 30):
        for r in radius:
            dirs.append(
                (r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang)))
            )

    placed = []
    for xd, yd, txt in items:
        best_t, best_score, best_xy = None, 1e18, None
        for ox, oy in dirs:
            ha = "left" if ox >= 0 else "right"
            va = "bottom" if oy >= 0 else "top"
            t = ax.annotate(
                txt,
                (xd, yd),
                textcoords="offset points",
                xytext=(ox, oy),
                fontsize=fontsize,
                fontweight="bold",
                color=color,
                ha=ha,
                va=va,
                zorder=7,
            )
            bb = t.get_window_extent(rend)
            score = 10.0 * sum(_overlap(bb, pb) for pb in placed)
            score += 500.0 * _out_of_bounds(bb)  # keep labels inside the axes
            # penalize covering many data points
            for dx, dy in pt_boxes:
                if bb.x0 - 2 <= dx <= bb.x1 + 2 and bb.y0 - 2 <= dy <= bb.y1 + 2:
                    score += 60.0
            # prefer shorter leaders
            score += 0.15 * (ox * ox + oy * oy)
            if score < best_score:
                if best_t is not None:
                    best_t.remove()
                best_t, best_score, best_xy = t, score, (ox, oy)
            else:
                t.remove()
        placed.append(best_t.get_window_extent(rend))
        # leader line from point to label anchor
        ox, oy = best_xy
        ax.annotate(
            "",
            xy=(xd, yd),
            textcoords="offset points",
            xytext=(ox * 0.5, oy * 0.5),
            zorder=6,
            arrowprops=dict(
                arrowstyle="-", color=leader_color, lw=0.45, shrinkA=0, shrinkB=1
            ),
        )
