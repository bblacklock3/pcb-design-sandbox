"""Sensor-level maths: pose sweeps, electrical angle, counts, linearity,
piecewise-linear correction, harmonic content, and the transmit tank estimate.

Amplitudes are ratiometric (no AGC model); absolute fluxes are still returned so
signal strength can be compared between geometries.
"""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np

from . import biot
from .geometry import Coil, ImagePlane, Sheet
from .sheet import SheetSolver, rx_flux

COUNTS_PER_PERIOD = 4096


def electrical_angle(phi_sin, phi_cos, unwrap: bool = True) -> np.ndarray:
    ang = np.arctan2(np.asarray(phi_sin, dtype=float), np.asarray(phi_cos, dtype=float))
    return np.unwrap(ang) if unwrap else ang


def counts(angle_rad, reserve: float = 0.0) -> np.ndarray:
    """12-bit counts over one electrical period. `reserve` = 0.1 reproduces the
    Microchip library convention of keeping 10 % clear at each end (409.6 .. 3686.4)."""
    frac = np.asarray(angle_rad, dtype=float) / (2 * np.pi)
    return COUNTS_PER_PERIOD * (reserve + (1 - 2 * reserve) * frac)


def fit_line(x, y) -> tuple[float, float]:
    slope, intercept = np.polyfit(np.asarray(x, dtype=float), np.asarray(y, dtype=float), 1)
    return float(slope), float(intercept)


def linearity(x, y) -> dict:
    """Residual of y against its best-fit line over x. Units of y."""
    slope, intercept = fit_line(x, y)
    residual = np.asarray(y, dtype=float) - (slope * np.asarray(x, dtype=float) + intercept)
    return {"slope": slope, "intercept": intercept, "residual": residual, "max_abs": float(np.abs(residual).max())}


def piecewise_correct(y_meas, y_ref, n_seg: int = 10) -> np.ndarray:
    """Continuous piecewise-linear map y_meas -> y_ref with `n_seg` segments on
    knots spread uniformly over the measured range (least squares on a hat basis).
    Mimics the LX34311's segment linearizer applied to the measured angle."""
    y_meas = np.asarray(y_meas, dtype=float)
    y_ref = np.asarray(y_ref, dtype=float)
    knots = np.linspace(y_meas.min(), y_meas.max(), n_seg + 1)
    # hat basis: B_k(y) = interp with unit at knot k
    basis = np.column_stack([np.interp(y_meas, knots, np.eye(n_seg + 1)[k]) for k in range(n_seg + 1)])
    coef, *_ = np.linalg.lstsq(basis, y_ref, rcond=None)
    return basis @ coef


def harmonics(theta, err, n_max: int = 6) -> np.ndarray:
    """Amplitude of harmonics 0..n_max of `err` as a function of `theta` (rad), by
    least squares. Index k is the k-th harmonic; index 0 is the mean."""
    theta = np.asarray(theta, dtype=float)
    cols = [np.ones_like(theta)]
    for k in range(1, n_max + 1):
        cols += [np.cos(k * theta), np.sin(k * theta)]
    coef, *_ = np.linalg.lstsq(np.column_stack(cols), np.asarray(err, dtype=float), rcond=None)
    amp = np.empty(n_max + 1)
    amp[0] = abs(coef[0])
    for k in range(1, n_max + 1):
        amp[k] = np.hypot(coef[2 * k - 1], coef[2 * k])
    return amp


def run_sweep(
    tx: Coil,
    rx_sin: Coil,
    rx_cos: Coil,
    place: Callable[[float], Sheet] | Sheet,
    poses: Sequence[float],
    plane: ImagePlane | None = None,
    coil_pose: Callable[[float, Coil], Coil] | None = None,
    solver: SheetSolver | None = None,
    log: Callable[[str], None] | None = None,
) -> dict:
    """Sweep the sensor through `poses`.

    Two ways to move: either `place(pose)` returns the target Sheet as a rigid motion of
    `place(poses[0])` (same mesh, same z) and the coils stay put, or `place` is a fixed
    Sheet and `coil_pose(pose, coil)` returns each coil moved (rotated/translated) for
    that pose. The second form is what a fixed target over a fixed finite back-plane
    needs, since then K is factorised once for the union of both sheets. In both forms
    the direct TX->RX coupling is a rigid-motion invariant and is computed once.

    Returns fluxes per ampere of TX current, the direct coupling, the unwrapped
    electrical angle and raw counts."""
    poses = np.asarray(poses, dtype=float)
    fixed_sheet = isinstance(place, Sheet)
    if fixed_sheet and coil_pose is None:
        raise ValueError("a fixed sheet needs coil_pose to move the coils")
    if solver is None:
        solver = SheetSolver(place if fixed_sheet else place(poses[0]), plane)
    tx_s, sin_s, cos_s = tx.segments(), rx_sin.segments(), rx_cos.segments()
    tx_eff = tx_s if plane is None else biot.Segments.concat([tx_s, biot.mirror(tx_s, plane.z)])
    direct_sin = biot.mutual_inductance(tx_eff, sin_s)
    direct_cos = biot.mutual_inductance(tx_eff, cos_s)
    phi_sin = np.empty_like(poses)
    phi_cos = np.empty_like(poses)
    for i, p in enumerate(poses):
        if fixed_sheet:
            sh, sv = place, solver
            t_s, s_s, c_s = (coil_pose(p, c).segments() for c in (tx, rx_sin, rx_cos))
        else:
            sh = place(p)
            sv = solver.moved(sh)
            t_s, s_s, c_s = tx_s, sin_s, cos_s
        psi = sv.respond(t_s)
        phi_sin[i] = direct_sin + rx_flux(sh, psi, s_s, plane)
        phi_cos[i] = direct_cos + rx_flux(sh, psi, c_s, plane)
        if log and (i % max(len(poses) // 10, 1) == 0):
            log(f"  pose {i + 1}/{len(poses)}")
    ang = electrical_angle(phi_sin, phi_cos)
    return {
        "pose": poses,
        "phi_sin": phi_sin,
        "phi_cos": phi_cos,
        "direct_sin": direct_sin,
        "direct_cos": direct_cos,
        "amplitude": np.hypot(phi_sin, phi_cos),
        "angle": ang,
        "counts": counts(ang),
        "solver": solver,
    }


def tank(tx: Coil, c_tank: float, plane: ImagePlane | None = None, cu_thickness: float = 35e-6) -> dict:
    """Transmit tank estimate: L (with the image-plane correction when present), AC
    resistance at the resonant frequency, f0 and Q. Perfect-conductor plane and
    target, so only copper loss is counted; the LX34311 wants 1-6 MHz, L > 3 uH, Q > 10."""
    segs = tx.segments()
    L = biot.self_inductance(segs, tx.trace_width / 2)
    if plane is not None:
        L += biot.mutual_inductance(segs, biot.mirror(segs, plane.z))
    f0 = 1 / (2 * np.pi * np.sqrt(L * c_tank))
    R = biot.trace_resistance(tx.length(), tx.trace_width, cu_thickness, f0)
    Q = 2 * np.pi * f0 * L / R
    return {"L": float(L), "R": float(R), "f0": float(f0), "Q": float(Q), "C": float(c_tank)}
