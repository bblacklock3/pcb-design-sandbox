"""Interpolation tables for coil fields at a fixed height.

A pose sweep evaluates the transmit and receive fields at every target cell for every
pose. For a ring sensor the coils are fixed and the target moves in the plane z = gap,
so each coil's Bz at that height is a fixed function of (r, theta), periodic in theta:
a ring transmit coil made of n-gons repeats every 360/n degrees, an N-period receive
coil every 360/N degrees apart from its closing vias. Tabulate once on a polar grid, then bilinear-interpolate at
the moving cells. With an image plane the table includes the image, so callers must not
add it again (SheetSolver and rx_flux treat table sources that way).
"""
from __future__ import annotations

import numpy as np

from . import biot
from .biot import Segments
from .geometry import MM, Coil, ImagePlane, Sheet


def _split_vertical(segs: Segments, tol: float = 1e-12):
    """Horizontal filaments (tabulated) and vertical ones (vias, added directly)."""
    dz = np.abs(segs.dl()[:, 2])
    horiz = dz < tol
    h = Segments(segs.p0[horiz], segs.p1[horiz], segs.w[horiz])
    v = Segments(segs.p0[~horiz], segs.p1[~horiz], segs.w[~horiz])
    return h, v


class PolarFieldTable:
    """Bz of a filament set on the plane z, tabulated on a polar grid over one
    `period_deg` of theta and bilinear-interpolated. Only horizontal filaments are
    tabulated: vertical ones (via hops, which break a receive coil's periodicity) are
    few and are evaluated directly at every call."""

    def __init__(self, segs: Segments, z: float, r_min_mm: float, r_max_mm: float, period_deg: float,
                 dr_mm: float = 0.1, dtheta_deg: float = 0.5, plane: ImagePlane | None = None):
        if plane is not None:
            segs = Segments.concat([segs, biot.mirror(segs, plane.z)])
        horiz, self.vertical = _split_vertical(segs)
        self.period = np.deg2rad(period_deg)
        self.r0 = r_min_mm * MM
        self.dr = dr_mm * MM
        nr = int(np.ceil((r_max_mm - r_min_mm) / dr_mm)) + 1
        nth = max(int(np.ceil(period_deg / dtheta_deg)), 1)
        self.dth = self.period / nth
        r = self.r0 + self.dr * np.arange(nr)
        th = self.dth * np.arange(nth + 1)  # closes the period: column nth == column 0
        R, TH = np.meshgrid(r, th, indexing="ij")
        pts = np.column_stack([(R * np.cos(TH)).ravel(), (R * np.sin(TH)).ravel(), np.full(R.size, z)])
        self.table = biot.bz(horiz, pts).reshape(nr, nth + 1)
        self.z = z
        self.nr, self.nth = nr, nth

    def bz(self, pts) -> np.ndarray:
        pts = np.asarray(pts, dtype=float).reshape(-1, 3)
        r = np.hypot(pts[:, 0], pts[:, 1])
        th = np.mod(np.arctan2(pts[:, 1], pts[:, 0]), self.period)
        fr = (r - self.r0) / self.dr
        if np.any(fr < -1e-9) or np.any(fr > self.nr - 1 + 1e-9):
            raise ValueError("point outside the table's radial range")
        fr = np.clip(fr, 0, self.nr - 1 - 1e-12)
        ft = np.clip(th / self.dth, 0, self.nth - 1e-12)
        i, j = fr.astype(int), ft.astype(int)
        u, v = fr - i, ft - j
        T = self.table
        out = ((1 - u) * (1 - v) * T[i, j] + u * (1 - v) * T[i + 1, j]
               + (1 - u) * v * T[i, j + 1] + u * v * T[i + 1, j + 1])
        if len(self.vertical):
            out = out + biot.bz(self.vertical, pts)
        return out


def ring_tables(tx: Coil, rx_sin: Coil, rx_cos: Coil, target: Sheet, n_periods: int, plane: ImagePlane | None = None,
                tx_period_deg: float | None = None, r_min_mm: float | None = None, r_max_mm: float | None = None,
                margin_mm: float = 1.0, dr_mm: float = 0.1, dtheta_deg: float = 0.5):
    """Tables for a ring sensor with a target sweeping in its own plane. The transmit
    period defaults to the polygon's segment pitch (exact for the n-gon circles); the
    receive tables use the electrical period 360/N for the horizontal traces, with the
    via hops (which sit at theta = 0 and at the lobe extrema) evaluated directly. Pass
    r_min/r_max to share one table set across targets of different radial extent."""
    z = target.z
    r = np.hypot(target.centers[:, 0], target.centers[:, 1]) / MM
    # a rigidly rotating or slightly eccentric target stays inside this radial band
    r_min = max(r.min() - margin_mm, 0.0) if r_min_mm is None else r_min_mm
    r_max = r.max() + margin_mm if r_max_mm is None else r_max_mm
    if tx_period_deg is None:
        n_seg = len(tx.loops[0].pts)
        tx_period_deg = 360.0 / n_seg
    rx_period_deg = 360.0 / n_periods
    kw = dict(z=z, r_min_mm=r_min, r_max_mm=r_max, dr_mm=dr_mm, dtheta_deg=dtheta_deg, plane=plane)
    return (PolarFieldTable(tx.segments(), period_deg=tx_period_deg, **kw),
            PolarFieldTable(rx_sin.segments(), period_deg=rx_period_deg, **kw),
            PolarFieldTable(rx_cos.segments(), period_deg=rx_period_deg, **kw))
