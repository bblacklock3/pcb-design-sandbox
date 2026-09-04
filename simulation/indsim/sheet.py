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


def build_k_direct(sh: Sheet, plane: ImagePlane | None = None) -> np.ndarray:
    """Collocation matrix K[i, j] (T per ampere of cell current) by evaluating every
    cell loop at every cell centre, including the image of every loop when an infinite
    perfectly conducting plane is present. O(n^2) field evaluations; the reference path."""
    loops = sh.cell_loops()
    K = _loop_bz_matrix(loops, sh.centers)
    if plane is not None:
        K += _loop_bz_matrix(biot.mirror(loops, plane.z), sh.centers)
    return K


def _unit_square_segments(a: float, z: float = 0.0, sense: float = 1.0) -> Segments:
    h = a / 2
    pts = np.array([[-h, -h, z], [h, -h, z], [h, h, z], [-h, h, z]])
    return Segments.from_polyline(pts, weight=sense)


def _toeplitz_block(sh: Sheet, idx: np.ndarray, plane: ImagePlane | None, chunk: int = 1024) -> np.ndarray:
    """K restricted to the cells `idx` of one uniform lattice. The field at cell p from
    the unit loop round cell q depends only on the index difference, so a table over
    all differences is evaluated once (in the lattice's own frame; Bz is rotation
    invariant) and the block is filled by lookup."""
    a = float(sh.side[idx[0]])
    lat = sh.lattice[idx]
    di_max = int(lat[:, 0].max() - lat[:, 0].min())
    dj_max = int(lat[:, 1].max() - lat[:, 1].min())
    di = np.arange(-di_max, di_max + 1)
    dj = np.arange(-dj_max, dj_max + 1)
    DI, DJ = np.meshgrid(di, dj, indexing="ij")
    pts = np.column_stack([DI.ravel() * a, DJ.ravel() * a, np.zeros(DI.size)])
    table = biot.bz(_unit_square_segments(a), pts)
    if plane is not None:
        # image loop: reversed sense, 2*(z - z_plane) below the sheet's own plane
        img = _unit_square_segments(a, z=2 * (plane.z - sh.centers[idx[0], 2]), sense=-1.0)
        table = table + biot.bz(img, pts)
    table = table.reshape(DI.shape)
    ii = lat[:, 0] - lat[:, 0].min()
    jj = lat[:, 1] - lat[:, 1].min()
    n = len(idx)
    K = np.empty((n, n))
    for s0 in range(0, n, chunk):
        sl = slice(s0, s0 + chunk)
        K[sl] = table[(ii[sl, None] - ii[None, :]) + di_max, (jj[sl, None] - jj[None, :]) + dj_max]
    return K


def build_k(sh: Sheet, plane: ImagePlane | None = None) -> np.ndarray:
    """Collocation matrix K. Uniform lattices (every sheet from `mesh_sheet`, and each
    member of a union) use the Toeplitz lookup; couplings between different lattices in
    a union are evaluated directly. Falls back to `build_k_direct` without lattice data."""
    if sh.lattice is None:
        return build_k_direct(sh, plane)
    n = sh.n
    K = np.empty((n, n))
    blocks = np.unique(sh.block)
    loops = sh.cell_loops() if len(blocks) > 1 else None
    for b in blocks:
        idx = np.flatnonzero(sh.block == b)
        K[np.ix_(idx, idx)] = _toeplitz_block(sh, idx, plane)
        for b2 in blocks:
            if b2 == b:
                continue
            idx2 = np.flatnonzero(sh.block == b2)
            seg_sl = (4 * idx2[:, None] + np.arange(4)[None, :]).ravel()
            src = Segments(loops.p0[seg_sl], loops.p1[seg_sl], loops.w[seg_sl])
            cross = _loop_bz_matrix(src, sh.centers[idx])
            if plane is not None:
                cross = cross + _loop_bz_matrix(biot.mirror(src, plane.z), sh.centers[idx])
            K[np.ix_(idx, idx2)] = cross
    return K


class SheetSolver:
    """Holds a sheet and the LU factors of its K matrix. `moved` re-targets the same
    factors to a rigidly translated/rotated copy of the sheet (same z when a plane is
    present). K itself is dropped after factorisation unless `keep_k` is set: the factors
    are all a solve needs, and keeping both doubles the memory per worker."""

    def __init__(self, sheet: Sheet, plane: ImagePlane | None = None, K=None, lu=None, keep_k: bool = False):
        self.sheet = sheet
        self.plane = plane
        if lu is None:
            K = build_k(sheet, plane) if K is None else K
            lu = lu_factor(K, overwrite_a=not keep_k)
        self.K = K if keep_k else None
        self.lu = lu

    def solve(self, bz_source: np.ndarray) -> np.ndarray:
        """psi such that K @ psi = -bz_source (amperes of circulating cell current)."""
        return lu_solve(self.lu, -np.asarray(bz_source, dtype=float))

    def source_bz(self, source) -> np.ndarray:
        """Normal field at the cells from `source`: a Segments set (plus its image when a
        plane is present) or any object with a `bz(points)` method that already includes
        the image (a field table)."""
        if not isinstance(source, Segments):
            return source.bz(self.sheet.centers)
        bz = biot.bz(source, self.sheet.centers)
        if self.plane is not None:
            bz = bz + biot.bz(biot.mirror(source, self.plane.z), self.sheet.centers)
        return bz

    def respond(self, source) -> np.ndarray:
        """Cell currents psi induced by unit current in `source` (plus its image)."""
        return self.solve(self.source_bz(source))

    def moved(self, new_sheet: Sheet) -> "SheetSolver":
        if new_sheet.n != self.sheet.n or not np.allclose(new_sheet.side, self.sheet.side):
            raise ValueError("moved() needs the same mesh; rebuild the solver instead")
        if self.plane is not None and not np.isclose(new_sheet.z, self.sheet.z):
            raise ValueError("with an image plane the sheet height is baked into K; rebuild")
        return SheetSolver(new_sheet, self.plane, self.K, self.lu, keep_k=self.K is not None)


def rx_flux(sh: Sheet, psi: np.ndarray, rx, plane: ImagePlane | None = None) -> float:
    """Flux (Wb per ampere of source) linking `rx` from the sheet currents, by
    reciprocity: sum_j psi_j * Bz_rx(centre_j) * a^2. With a plane, Bz_rx includes
    the image of `rx`. `rx` may be a Segments set or a field table with `bz(points)`."""
    if not isinstance(rx, Segments):
        bz = rx.bz(sh.centers)
    else:
        bz = biot.bz(rx, sh.centers)
        if plane is not None:
            bz = bz + biot.bz(biot.mirror(rx, plane.z), sh.centers)
    return float(np.sum(psi * bz * sh.cell_area()))
