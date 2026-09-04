"""Figure helpers that follow the Design Wiki plot rules (vault CLAUDE.md, Plot styling):
ASCII-only text, Title Case labels with units in parentheses, one plot per figure,
grid at alpha 0.3, tight_layout before saving. Scripts save to files, so the Agg
backend is set here (never in the vault's inline sandbox).
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIGSIZE = (6.4, 4.0)
DPI = 150


def check_ascii(*texts: str) -> None:
    for t in texts:
        if t is None:
            continue
        bad = [c for c in t if ord(c) > 126]
        if bad:
            raise ValueError(f"non-ASCII in plot text {t!r}: {bad}")


def figure(figsize=FIGSIZE):
    return plt.subplots(figsize=figsize)


def finish(fig, ax, title: str, xlabel: str, ylabel: str, path: str | Path | None = None, legend: bool = False):
    """Label, grid, tighten, save (PNG) and close. Returns the path written."""
    check_ascii(title, xlabel, ylabel)
    if legend:
        for t in ax.get_legend_handles_labels()[1]:
            check_ascii(t)
        ax.legend(fontsize=8)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def line_plot(x, ys: dict, title: str, xlabel: str, ylabel: str, path=None, **kw):
    """One figure, one or more series (dict label -> y)."""
    fig, ax = figure()
    for label, y in ys.items():
        ax.plot(x, y, label=label, **kw)
    return finish(fig, ax, title, xlabel, ylabel, path, legend=len(ys) > 1)


def geometry_plot(coils, sheets=(), title="Coil Geometry", path=None, cells=False):
    """Top view of coils and sheets in mm."""
    fig, ax = figure(figsize=(6.4, 6.4))
    for c in coils:
        c.plot(ax, label=c.name)
    for s in sheets:
        s.plot(ax, cells=cells, label="Target")
    return finish(fig, ax, title, "X (mm)", "Y (mm)", path, legend=True)


def write_csv(path: str | Path, columns: dict) -> Path:
    """Columns: dict header -> 1-D array. Header text must be ASCII."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    check_ascii(*columns.keys())
    n = len(next(iter(columns.values())))
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(columns.keys())
        for i in range(n):
            w.writerow([f"{col[i]:.9g}" for col in columns.values()])
    return path
