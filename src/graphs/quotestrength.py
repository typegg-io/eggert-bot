from typing import List, Dict

from graphs.core import plt, apply_theme, generate_file_name, GRAPH_PALETTE


def render(users: List[Dict], theme: dict) -> str:
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

    # Crosshair
    axis_color = theme["axis"]
    ax.axhline(0, color=axis_color, linewidth=1, alpha=0.6, zorder=1)
    ax.axvline(0, color=axis_color, linewidth=1, alpha=0.6, zorder=1)

    ax.set_facecolor(theme["background"])
    inner = plt.Rectangle((-1, -1), 2, 2, facecolor=theme["graph_background"], edgecolor=axis_color, linewidth=0.8, alpha=1, zorder=0)
    ax.add_patch(inner)

    # Compass labels
    text_color = theme["text"]
    label_kwargs = dict(ha="center", va="center", color=text_color, fontsize=16, fontweight="bold")
    ax.text(0, 1.15, "Complex", **label_kwargs)
    ax.text(0, -1.15, "Simple", **label_kwargs)
    ax.text(-1.2, 0, "Short", **label_kwargs)
    ax.text(1.2, 0, "Long", **label_kwargs)

    # Slice-based Y adjustment
    num_slices = 20
    y_min, y_max = -1.3, 1.3
    slice_height = (y_max - y_min) / num_slices
    sorted_users = sorted(users, key=lambda u: u["y"], reverse=True)
    used_slices = set()

    for i, user in enumerate(sorted_users):
        x, y = user["x"], user["y"]
        desired_slice = int((y - y_min) / slice_height)
        desired_slice = max(0, min(num_slices - 1, desired_slice))

        # Find nearest available slice <= desired
        for offset in range(num_slices):
            candidate = desired_slice - offset
            if candidate >= 0 and candidate not in used_slices:
                assigned_slice = candidate
                break
        else:  # Fallback: next free slice above
            for candidate in range(desired_slice + 1, num_slices):
                if candidate not in used_slices:
                    assigned_slice = candidate
                    break

        used_slices.add(assigned_slice)
        y_final = y_min + assigned_slice * slice_height + slice_height / 2

        color = GRAPH_PALETTE[users.index(user) % len(GRAPH_PALETTE)]

        ax.scatter(x, y, color=color, s=120, zorder=5, edgecolors="none")
        ax.text(
            x + 0.075,  # Mimic annotation offset
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
    file_name = generate_file_name("quotestrength")
    plt.savefig(file_name)
    plt.close(fig)
    return file_name
