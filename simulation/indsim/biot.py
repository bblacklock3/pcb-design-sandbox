"""Quasi-static magnetics on straight filaments.

Everything here is in SI (metres, amperes, tesla, henry). All fields are for the
current given by each segment's weight `w` (turns x sense x amperes); the callers
in this package use unit current so results are per-ampere quantities.

Segments are a flat structure-of-arrays so the field of thousands of filaments at
thousands of points vectorises cleanly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

MU0 = 4e-7 * np.pi
RHO_CU = 1.68e-8  # ohm m, annealed copper at 20 C


@dataclass(frozen=True)
class Segments:
    """Straight filaments p0 -> p1 carrying current `w` (signed, includes turns)."""

    p0: np.ndarray  # (N, 3)
    p1: np.ndarray  # (N, 3)
    w: np.ndarray  # (N,)

    def __post_init__(self):
        p0 = np.asarray(self.p0, dtype=float).reshape(-1, 3)
        p1 = np.asarray(self.p1, dtype=float).reshape(-1, 3)
        w = np.broadcast_to(np.asarray(self.w, dtype=float), (p0.shape[0],)).copy()
        object.__setattr__(self, "p0", p0)
        object.__setattr__(self, "p1", p1)
        object.__setattr__(self, "w", w)

    @classmethod
    def from_polyline(cls, pts, weight=1.0, closed=True) -> "Segments":
        pts = np.asarray(pts, dtype=float).reshape(-1, 3)
        if closed and not np.allclose(pts[0], pts[-1]):
            pts = np.vstack([pts, pts[:1]])
        return cls(pts[:-1], pts[1:], np.full(len(pts) - 1, float(weight)))

    @classmethod
    def concat(cls, parts: Iterable["Segments"]) -> "Segments":
        parts = list(parts)
        if not parts:
            return cls(np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0))
        return cls(
            np.vstack([s.p0 for s in parts]),
            np.vstack([s.p1 for s in parts]),
            np.concatenate([s.w for s in parts]),
        )

    def __len__(self):
        return self.p0.shape[0]

    def dl(self) -> np.ndarray:
        return self.p1 - self.p0

    def mid(self) -> np.ndarray:
        return 0.5 * (self.p0 + self.p1)

    def length(self) -> float:
        """Total geometric filament length (m). Turns are separate loops, not weights."""
        return float(np.sum(np.linalg.norm(self.dl(), axis=1)))

    def translated(self, d) -> "Segments":
        d = np.asarray(d, dtype=float).reshape(1, 3)
        return Segments(self.p0 + d, self.p1 + d, self.w)

    def scaled(self, k: float) -> "Segments":
        return Segments(self.p0, self.p1, self.w * k)


def bfield(segs: Segments, pts, chunk: int = 2048) -> np.ndarray:
    """Magnetic flux density (T) at `pts` (M, 3) from all segments. Returns (M, 3).

    Analytic finite-segment Biot-Savart:
        B = mu0/(4 pi) * w * (L x r1) / |L x r1|^2 * (L.r1/|r1| - L.r2/|r2|)
    with L = p1 - p0, r1 = P - p0, r2 = P - p1. Points on a filament's line get zero
    from that filament (the field there is undefined; this keeps sweeps finite).
    """
    pts = np.asarray(pts, dtype=float).reshape(-1, 3)
    out = np.zeros_like(pts)
    if len(segs) == 0 or pts.shape[0] == 0:
        return out
    L = segs.dl()  # (N, 3)
    w = segs.w
    for s in range(0, pts.shape[0], chunk):
        P = pts[s : s + chunk]  # (m, 3)
        r1 = P[None, :, :] - segs.p0[:, None, :]  # (N, m, 3)
        r2 = P[None, :, :] - segs.p1[:, None, :]
        cross = np.cross(L[:, None, :], r1)  # (N, m, 3)
        denom = np.einsum("ijk,ijk->ij", cross, cross)  # |L x r1|^2
        n1 = np.linalg.norm(r1, axis=2)
        n2 = np.linalg.norm(r2, axis=2)
        Ldotr1 = np.einsum("ik,ijk->ij", L, r1)
        Ldotr2 = np.einsum("ik,ijk->ij", L, r2)
        with np.errstate(divide="ignore", invalid="ignore"):
            term = Ldotr1 / n1 - Ldotr2 / n2
            coef = np.where(denom > 1e-300, term / denom, 0.0)
            coef = np.nan_to_num(coef, nan=0.0, posinf=0.0, neginf=0.0)
        out[s : s + chunk] = (MU0 / (4 * np.pi)) * np.einsum("i,ij,ijk->jk", w, coef, cross)
    return out


def bz(segs: Segments, pts, chunk: int = 2048) -> np.ndarray:
    """Normal (z) component of `bfield`, shape (M,)."""
    return bfield(segs, pts, chunk=chunk)[:, 2]


def _neumann(a: Segments, b: Segments, reg2: float, chunk: int = 1024) -> float:
    """mu0/(4 pi) * sum_ij w_i w_j (dl_i . dl_j) / sqrt(|m_i - m_j|^2 + reg2)."""
    dla, dlb = a.dl(), b.dl()
    ma, mb = a.mid(), b.mid()
    total = 0.0
    for s in range(0, len(a), chunk):
        d = ma[s : s + chunk, None, :] - mb[None, :, :]
        r = np.sqrt(np.einsum("ijk,ijk->ij", d, d) + reg2)
        dot = dla[s : s + chunk] @ dlb.T
        total += float(np.einsum("i,ij,j->", a.w[s : s + chunk], dot / r, b.w))
    return MU0 / (4 * np.pi) * total


def mutual_inductance(a: Segments, b: Segments) -> float:
    """Neumann double integral with midpoint quadrature (H, per unit current in each).

    Accurate when segment lengths are small compared with the separation of the two
    filament sets; fine for coils on different layers (>= 0.2 mm apart) at ~0.1 mm
    segmentation. Do not call with a == b: use `self_inductance`.
    """
    return _neumann(a, b, 0.0)


def self_inductance(segs: Segments, wire_radius: float) -> float:
    """Self-inductance of a filament set with the Neumann kernel regularised as
    1/sqrt(r^2 + a^2), `a` = effective wire radius (half the trace width per the spec).

    Reproduces mu0*R*(ln(8R/a) - 2) for a thin circular loop to better than 0.1 %.
    """
    a = float(wire_radius)
    # Checked in tests/test_biot.py against the circular-loop formula; see README for
    # the measured deviation.
    return _neumann(segs, segs, a * a)


def mirror(segs: Segments, plane_z: float) -> Segments:
    """Image of `segs` in a perfectly conducting plane at z = plane_z.

    Horizontal currents mirror with reversed sense so the normal field vanishes on
    the plane. (Vertical current elements would keep their sense; this package has
    no vertical filaments -- vias are ignored.)
    """
    p0 = segs.p0.copy()
    p1 = segs.p1.copy()
    p0[:, 2] = 2 * plane_z - p0[:, 2]
    p1[:, 2] = 2 * plane_z - p1[:, 2]
    return Segments(p0, p1, -segs.w)


def skin_depth(freq: float, rho: float = RHO_CU) -> float:
    return float(np.sqrt(rho / (np.pi * freq * MU0)))


def trace_resistance(length: float, width: float, thickness: float, freq: float, rho: float = RHO_CU) -> float:
    """AC resistance (ohm) of a rectangular trace, current on both faces.

    Effective thickness 2*delta*(1 - exp(-t/(2*delta))): tends to t when thin, 2*delta
    when thick. Edge crowding is ignored.
    """
    delta = skin_depth(freq, rho)
    t_eff = 2 * delta * (1 - np.exp(-thickness / (2 * delta)))
    return float(rho * length / (width * t_eff))
