from typing import List, Dict, Optional, Tuple

import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from graphs.core import plt, apply_theme, generate_file_name, GRAPH_PALETTE


def render(users: List[Dict], theme: dict, heatmap_points: Optional[List[Tuple[float, float]]] = None) -> str:
    fig, ax = plt.subplots(figsize=(6, 6), constrained_layout=True)

    apply_theme(ax, theme=theme, legend_loc=None, force_legend=False)

    # Compass-style plot
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_aspect("equal", adjustable="box")

    ax.set_facecolor(theme["background"])
    inner = plt.Rectangle(
        (-1, -1), 2, 2,
        facecolor=theme["graph_background"], edgecolor=theme["axis"],
        linewidth=0.8, alpha=1, zorder=0
    )
    ax.add_patch(inner)

    # Heatmap
    if heatmap_points and len(heatmap_points) >= 2:
        xs = np.array([p[0] for p in heatmap_points])
        ys = np.array([p[1] for p in heatmap_points])

        res = 300
        xi = np.linspace(-1, 1, res)
        yi = np.linspace(-1, 1, res)
        Xi, Yi = np.meshgrid(xi, yi)

        hx = 0.5 * np.std(xs)
        hy = 0.5 * np.std(ys)
        Zi = np.zeros((res, res))
        for xi_pt, yi_pt in zip(xs, ys):
            Zi += np.exp(-((Xi - xi_pt) ** 2 / (2 * hx ** 2) + (Yi - yi_pt) ** 2 / (2 * hy ** 2)))
        Zi /= Zi.max()
        Zi = Zi ** 1.5

        cmap = LinearSegmentedColormap.from_list("qs_heat", [
            (0.00, (0.15, 0.85, 0.10, 0.00)),
            (0.15, (0.15, 0.85, 0.10, 0.85)),
            (0.50, (1.00, 1.00, 0.00, 0.90)),
            (1.00, (0.90, 0.10, 0.10, 1.00)),
        ])

        ax.imshow(
            Zi, extent=[-1, 1, -1, 1], origin="lower", cmap=cmap,
            aspect="auto", zorder=2, interpolation="bilinear"
        )

    # Crosshair (above heatmap)
    axis_color = theme["axis"]
    ax.axhline(0, color=axis_color, linewidth=1, alpha=0.6, zorder=3)
    ax.axvline(0, color=axis_color, linewidth=1, alpha=0.6, zorder=3)

    # Compass labels
    text_color = theme["text"]
    label_kwargs = dict(ha="center", va="center", color=text_color, fontsize=16, fontweight="bold")
    ax.text(0, 1.15, "Complex", **label_kwargs)
    ax.text(0, -1.15, "Simple", **label_kwargs)
    ax.text(-1.2, 0, "Short", **label_kwargs)
    ax.text(1.2, 0, "Long", **label_kwargs)

    # Slice-based Y adjustment for multi-user label placement
    num_slices = 20
    y_min, y_max = -1.3, 1.3
    slice_height = (y_max - y_min) / num_slices
    sorted_users = sorted(users, key=lambda u: u["y"], reverse=True)
    used_slices = set()

    for i, user in enumerate(sorted_users):
        x, y = user["x"], user["y"]
        color = GRAPH_PALETTE[users.index(user) % len(GRAPH_PALETTE)]
        ax.scatter(x, y, color=color, s=120, zorder=5, edgecolors="none")

        if len(users) > 1:
            desired_slice = int((y - y_min) / slice_height)
            desired_slice = max(0, min(num_slices - 1, desired_slice))

            for offset in range(num_slices):
                candidate = desired_slice - offset
                if candidate >= 0 and candidate not in used_slices:
                    assigned_slice = candidate
                    break
            else:
                for candidate in range(desired_slice + 1, num_slices):
                    if candidate not in used_slices:
                        assigned_slice = candidate
                        break

            used_slices.add(assigned_slice)
            y_final = y_min + assigned_slice * slice_height + slice_height / 2

            ax.text(
                x + 0.075,
                y_final,
                user["username"],
                ha="left",
                va="center",
                fontsize=16,
                fontweight="bold",
                color=color,
                zorder=6,
            )

    ax.set_title("Quote Strength", y=1.1, fontsize=22)
    if len(users) == 1:
        ax.text(
            0, 1.255, users[0]["username"],
            ha="center", va="center", color=text_color,
            fontsize=16, fontweight="bold", clip_on=False,
        )
    file_name = generate_file_name("quotestrength")
    plt.savefig(file_name)
    plt.close(fig)
    return file_name
