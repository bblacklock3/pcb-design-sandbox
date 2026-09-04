"""Perfectly conducting thin sheets as a dipole layer of square cells.

Each cell j carries a stream-function value psi_j. A piecewise-constant stream
function is exactly a set of square boundary loops, so the sheet's field is
sum_j psi_j * B(unit loop j). The perfect-conductor condition (no normal flux through
the sheet) collocated at cell centres is

    K @ psi + bz_source = 0,    K[i, j] = Bz at centre i from unit current round cell j.

K depends only on the cell layout, so it is built and LU-factorised once per sheet
(and per back-plane height, when an image plane is present) and reused for every
pose in a sweep. Receive flux uses reciprocity: the flux a coil sees from cell j is
psi_j * Bz_coil(centre_j) * a_j^2.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import lu_factor, lu_solve

from . import biot
from .biot import MU0, Segments
from .geometry import ImagePlane, Sheet


def _bz_cols(segs: Segments, pts: np.ndarray) -> np.ndarray:
    """Per-segment Bz contributions, shape (M_pts, N_seg). Same kernel as biot.bfield."""
    L = segs.dl()
    r1 = pts[None, :, :] - segs.p0[:, None, :]  # (N, M, 3)
    r2 = pts[None, :, :] - segs.p1[:, None, :]
    cross_z = L[:, None, 0] * r1[:, :, 1] - L[:, None, 1] * r1[:, :, 0]
    cross_x = L[:, None, 1] * r1[:, :, 2] - L[:, None, 2] * r1[:, :, 1]
    cross_y = L[:, None, 2] * r1[:, :, 0] - L[:, None, 0] * r1[:, :, 2]
    denom = cross_x**2 + cross_y**2 + cross_z**2
    n1 = np.linalg.norm(r1, axis=2)
    n2 = np.linalg.norm(r2, axis=2)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.einsum("ik,ijk->ij", L, r1) / n1 - np.einsum("ik,ijk->ij", L, r2) / n2
        coef = np.where(denom > 1e-300, term / denom, 0.0)
        coef = np.nan_to_num(coef, nan=0.0, posinf=0.0, neginf=0.0)
    return (MU0 / (4 * np.pi)) * (segs.w[:, None] * coef * cross_z).T


def _loop_bz_matrix(loops: Segments, pts: np.ndarray, group: int = 4, chunk_loops: int = 128) -> np.ndarray:
    """Bz at `pts` from each closed loop of `group` consecutive segments: (M_pts, n_loops)."""
    n_loops = len(loops) // group
    out = np.empty((pts.shape[0], n_loops))
    for j0 in range(0, n_loops, chunk_loops):
        j1 = min(j0 + chunk_loops, n_loops)
        sl = slice(group * j0, group * j1)
        cols = _bz_cols(Segments(loops.p0[sl], loops.p1[sl], loops.w[sl]), pts)  # (M, group*m)
        out[:, j0:j1] = cols.reshape(pts.shape[0], j1 - j0, group).sum(axis=2)
    return out


def build_k(sh: Sheet, plane: ImagePlane | None = None) -> np.ndarray:
    """Collocation matrix K[i, j] (T per ampere of cell current), including the image
    of every cell loop when an infinite perfectly conducting plane is present."""
    loops = sh.cell_loops()
    K = _loop_bz_matrix(loops, sh.centers)
    if plane is not None:
        K += _loop_bz_matrix(biot.mirror(loops, plane.z), sh.centers)
    return K


class SheetSolver:
    """Holds a sheet, its K matrix and LU factors. `moved` re-targets the same factors
    to a rigidly translated/rotated copy of the sheet (same z when a plane is present)."""

    def __init__(self, sheet: Sheet, plane: ImagePlane | None = None, K=None, lu=None):
        self.sheet = sheet
        self.plane = plane
        self.K = K if K is not None else build_k(sheet, plane)
        self.lu = lu if lu is not None else lu_factor(self.K)

    def solve(self, bz_source: np.ndarray) -> np.ndarray:
        """psi such that K @ psi = -bz_source (amperes of circulating cell current)."""
        return lu_solve(self.lu, -np.asarray(bz_source, dtype=float))

    def source_bz(self, source: Segments) -> np.ndarray:
        bz = biot.bz(source, self.sheet.centers)
        if self.plane is not None:
            bz = bz + biot.bz(biot.mirror(source, self.plane.z), self.sheet.centers)
        return bz

    def respond(self, source: Segments) -> np.ndarray:
        """Cell currents psi induced by unit current in `source` (plus its image)."""
        return self.solve(self.source_bz(source))

    def moved(self, new_sheet: Sheet) -> "SheetSolver":
        if new_sheet.n != self.sheet.n or not np.allclose(new_sheet.side, self.sheet.side):
            raise ValueError("moved() needs the same mesh; rebuild the solver instead")
        if self.plane is not None and not np.isclose(new_sheet.z, self.sheet.z):
            raise ValueError("with an image plane the sheet height is baked into K; rebuild")
        return SheetSolver(new_sheet, self.plane, self.K, self.lu)


def rx_flux(sh: Sheet, psi: np.ndarray, rx: Segments, plane: ImagePlane | None = None) -> float:
    """Flux (Wb per ampere of source) linking `rx` from the sheet currents, by
    reciprocity: sum_j psi_j * Bz_rx(centre_j) * a^2. With a plane, Bz_rx includes
    the image of `rx`."""
    bz = biot.bz(rx, sh.centers)
    if plane is not None:
        bz = bz + biot.bz(biot.mirror(rx, plane.z), sh.centers)
    return float(np.sum(psi * bz * sh.cell_area()))
