"""Coils, sheets and planes, plus the parametric generators.

API boundary is millimetres (every argument ending in `_mm`); everything stored on
the objects is metres so `biot` and `sheet` never see a unit.

Coordinate convention: the coil board is the plane z = 0 face nearest the target
(receive layers at z <= 0, transmit layers further negative), the target sheet sits
at positive z (the airgap), and a back-plane behind the board sits at negative z.
Linear coils run along x; ring coils are centred on the origin.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

from .biot import Segments

MM = 1e-3


def mm(x):
    """Millimetres -> metres."""
    return np.asarray(x, dtype=float) * MM if np.ndim(x) else float(x) * MM


def to_mm(x):
    """Metres -> millimetres."""
    return np.asarray(x, dtype=float) / MM if np.ndim(x) else float(x) / MM


# --------------------------------------------------------------------------- coils


def _rot_z(angle: float) -> np.ndarray:
    c, s_ = np.cos(angle), np.sin(angle)
    return np.array([[c, -s_, 0.0], [s_, c, 0.0], [0.0, 0.0, 1.0]])


@dataclass(frozen=True)
class Loop:
    """A closed filament polyline (metres). `sense` +1/-1 is the current direction
    relative to the vertex order; `turns` multiplies the current."""

    pts: np.ndarray  # (n, 3), first vertex not repeated
    sense: int = 1
    turns: int = 1

    def __post_init__(self):
        pts = np.asarray(self.pts, dtype=float).reshape(-1, 3)
        if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
            pts = pts[:-1]
        object.__setattr__(self, "pts", pts)

    def segments(self) -> Segments:
        return Segments.from_polyline(self.pts, weight=self.sense * self.turns, closed=True)

    def signed_area(self) -> float:
        """Shoelace area of the xy projection, times sense and turns (m^2)."""
        x, y = self.pts[:, 0], self.pts[:, 1]
        return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) * self.sense * self.turns

    def translated(self, d) -> "Loop":
        return Loop(self.pts + np.asarray(d, dtype=float).reshape(1, 3), self.sense, self.turns)

    def mirrored(self, plane_z: float) -> "Loop":
        p = self.pts.copy()
        p[:, 2] = 2 * plane_z - p[:, 2]
        return Loop(p, -self.sense, self.turns)

    def rotated(self, angle: float) -> "Loop":
        return Loop(self.pts @ _rot_z(angle).T, self.sense, self.turns)


@dataclass(frozen=True)
class Coil:
    name: str
    loops: tuple
    trace_width: float = 0.1524e-3  # m, 6 mil default

    def __post_init__(self):
        object.__setattr__(self, "loops", tuple(self.loops))

    def segments(self) -> Segments:
        return Segments.concat(l.segments() for l in self.loops)

    def net_signed_area(self) -> float:
        return float(sum(l.signed_area() for l in self.loops))

    def turns(self) -> int:
        return int(sum(abs(l.turns) for l in self.loops))

    def length(self) -> float:
        """Copper length (m): every turn is its own loop, so this is the trace length."""
        return float(sum(l.segments().length() * abs(l.turns) for l in self.loops))

    def translated(self, d) -> "Coil":
        return Coil(self.name, tuple(l.translated(d) for l in self.loops), self.trace_width)

    def translated_mm(self, d_mm) -> "Coil":
        return self.translated(mm(np.asarray(d_mm, dtype=float)))

    def mirrored(self, plane_z: float) -> "Coil":
        return Coil(self.name + "_image", tuple(l.mirrored(plane_z) for l in self.loops), self.trace_width)

    def rotated(self, angle: float) -> "Coil":
        """Rotate about the z axis through the origin by `angle` (rad)."""
        return Coil(self.name, tuple(l.rotated(angle) for l in self.loops), self.trace_width)

    def rotated_deg(self, angle_deg: float) -> "Coil":
        return self.rotated(np.deg2rad(angle_deg))

    def z_levels(self) -> np.ndarray:
        return np.unique(np.round(np.concatenate([l.pts[:, 2] for l in self.loops]), 9))

    def plot(self, ax, color=None, lw=0.8, label=None):
        """Top view (mm). One colour per coil; z shown only through the label."""
        first = True
        for l in self.loops:
            p = np.vstack([l.pts, l.pts[:1]])
            line, = ax.plot(to_mm(p[:, 0]), to_mm(p[:, 1]), color=color, lw=lw, label=(label or self.name) if first else None)
            color = line.get_color()  # keep every loop of this coil the same colour
            first = False
        ax.set_aspect("equal")
        return ax


def _swap_layers(xy: np.ndarray, seg: np.ndarray, z_a: float, z_b: float) -> np.ndarray:
    """Points (n, 2) -> (m, 3): z alternates between z_a and z_b with the parity of `seg`,
    and the vertex at every change is duplicated on both layers (the via)."""
    z = np.where(seg % 2 == 0, z_a, z_b)
    pts = np.column_stack([xy, z])
    change = np.flatnonzero(z[1:] != z[:-1]) + 1
    if change.size:
        extra = pts[change].copy()
        extra[:, 2] = z[change - 1]
        pts = np.insert(pts, change, extra, axis=0)
    return pts


def _peak_segments(u: np.ndarray, first_peak: float, half_period: float, layer_swap: bool) -> np.ndarray:
    """Index of the interval between successive extrema of f(u); 0 before the first peak."""
    if not layer_swap:
        return np.zeros(u.shape, dtype=int)
    seg = np.maximum(np.floor((u - first_peak + 1e-9 * half_period) / half_period).astype(int) + 1, 0)
    seg[-1] = seg[-2]  # an extremum on the last sample needs no via: the trace hops there anyway
    return seg


def _linear_rx(lam, amp, n_lobes, z1, z2, func, pts_per_lobe, layer_swap, end_scale=1.0) -> Loop:
    length = n_lobes * lam / 2
    n = n_lobes * pts_per_lobe
    xp = np.linspace(0.0, length, n + 1)  # 0 .. L, sampled so lam/4 multiples land on samples
    y = amp * func(2 * np.pi * xp / lam)
    if end_scale != 1.0:
        # end compensation: the outermost quarter-period at each end (a half lobe on the
        # cosine coil) gets a different amplitude; it still joins at a zero crossing
        ends = (xp < lam / 4 - 1e-12) | (xp > length - lam / 4 + 1e-12)
        y = np.where(ends, y * end_scale, y)
    y = np.where(np.abs(y) < 1e-15 * amp, 0.0, y)
    x = xp - length / 2
    # layers swap at the lobe extrema (Microchip: lambda/4 and 3 lambda/4 on the sine coil,
    # lambda/2 on the cosine coil); the two traces cross at the zeros on opposite layers
    seg = _peak_segments(xp, lam / 4 if func is np.sin else 0.0, lam / 2, layer_swap)
    fwd = _swap_layers(np.column_stack([x, y]), seg, z1, z2)
    back = _swap_layers(np.column_stack([x, -y]), seg, z2, z1)[::-1]
    return Loop(np.vstack([fwd, back]), sense=1)


def linear_rx_pair(
    lam_mm: float,
    lobe_width_mm: float,
    n_lobes: int,
    layers_z_mm: Sequence[float],
    pts_per_lobe: int = 60,
    trace_mm: float = 0.1524,
    layer_swap: bool = True,
    cos_end_scale: float = 1.0,
) -> tuple[Coil, Coil]:
    """Sine and cosine receive coils for a linear track along x, centred on the origin.
    `cos_end_scale` scales the cosine coil's end half-lobes (end compensation, to null
    its direct coupling to a transmit loop whose field is strongest near the ends).

    Each coil is one figure-8 loop: forward along +A*f(2*pi*x/lambda), back along -A*f.
    With `layer_swap` (the default, and how Microchip routes them) both traces change
    layer at every lobe extremum, so each layer carries half of every lobe and the two
    traces cross at the zeros on opposite layers. `layer_swap=False` keeps the forward
    trace on the first layer and the return on the second. `lobe_width_mm` is the
    peak-to-peak lobe height (2A). The sine coil has `n_lobes` full lobes (use an even
    count for zero net area); the cosine coil is the same span shifted a quarter period,
    so it ends in half lobes.
    """
    if len(layers_z_mm) != 2:
        raise ValueError("receive coils need exactly two layer z values")
    lam, amp = mm(lam_mm), mm(lobe_width_mm) / 2
    z1, z2 = mm(layers_z_mm[0]), mm(layers_z_mm[1])
    if pts_per_lobe % 2:
        pts_per_lobe += 1
    sin_loop = _linear_rx(lam, amp, n_lobes, z1, z2, np.sin, pts_per_lobe, layer_swap)
    cos_loop = _linear_rx(lam, amp, n_lobes, z1, z2, np.cos, pts_per_lobe, layer_swap, cos_end_scale)
    tw = mm(trace_mm)
    return Coil("RX_sin", (sin_loop,), tw), Coil("RX_cos", (cos_loop,), tw)


def _rounded_rect(half_len, half_wid, r, z, pts_per_corner=8) -> np.ndarray:
    """CCW rounded rectangle centred on the origin, length along x."""
    r = min(r, half_len, half_wid)
    if r <= 0:
        return np.array(
            [[half_len, -half_wid, z], [half_len, half_wid, z], [-half_len, half_wid, z], [-half_len, -half_wid, z]]
        )
    cx, cy = half_len - r, half_wid - r
    pts = []
    for (sx, sy, a0) in ((1, -1, -np.pi / 2), (1, 1, 0.0), (-1, 1, np.pi / 2), (-1, -1, np.pi)):
        th = a0 + np.linspace(0, np.pi / 2, pts_per_corner + 1)
        pts.append(np.column_stack([sx * cx + r * np.cos(th), sy * cy + r * np.sin(th), np.full_like(th, z)]))
    return np.vstack(pts)


def rect_tx(
    len_mm: float,
    wid_mm: float,
    n_turns: int,
    pitch_mm: float,
    layers_z_mm: Sequence[float],
    corner_r_mm: float | None = None,
    sense: int = 1,
    trace_mm: float = 0.1524,
) -> Coil:
    """Transmit loop: `n_turns` concentric rounded rectangles per layer, stepping
    inward by `pitch_mm` from the outer centreline size len x wid (along x, across y)."""
    loops = []
    r0 = mm(corner_r_mm) if corner_r_mm else 0.0
    for z_mm in layers_z_mm:
        for k in range(n_turns):
            hl = mm(len_mm) / 2 - k * mm(pitch_mm)
            hw = mm(wid_mm) / 2 - k * mm(pitch_mm)
            loops.append(Loop(_rounded_rect(hl, hw, max(r0 - k * mm(pitch_mm), 0.0), mm(z_mm)), sense=sense))
    return Coil("TX", tuple(loops), mm(trace_mm))


def _ring_rx(r_m, amp, n_periods, z1, z2, func, n_theta, layer_swap) -> Loop:
    th = np.linspace(0.0, 2 * np.pi, n_theta + 1)  # closed curve: last angle == first
    r1 = r_m + amp * func(n_periods * th)
    r2 = r_m - amp * func(n_periods * th)
    seg = _peak_segments(n_periods * th, np.pi / 2 if func is np.sin else 0.0, np.pi, layer_swap)
    fwd = _swap_layers(np.column_stack([r1 * np.cos(th), r1 * np.sin(th)]), seg, z1, z2)
    back = _swap_layers(np.column_stack([r2 * np.cos(th), r2 * np.sin(th)]), seg, z2, z1)[::-1]
    # forward round the ring, via down, back round the other trace, via up (closes)
    return Loop(np.vstack([fwd, back]), sense=1)


def ring_rx_pair(
    r_in_mm: float,
    r_out_mm: float,
    n_periods: int,
    layers_z_mm: Sequence[float],
    amp_mm: float | None = None,
    n_theta: int = 720,
    trace_mm: float = 0.1524,
    layer_swap: bool = True,
) -> tuple[Coil, Coil]:
    """Sine and cosine ring receive coils: r = r_m +/- A f(N theta). Electrical period
    is 360/N degrees; the cosine coil is the sine pattern advanced by a quarter period.
    `layer_swap` (default) changes layer at every lobe extremum as on the linear coil."""
    if len(layers_z_mm) != 2:
        raise ValueError("receive coils need exactly two layer z values")
    r_in, r_out = mm(r_in_mm), mm(r_out_mm)
    r_m = 0.5 * (r_in + r_out)
    amp = mm(amp_mm) if amp_mm is not None else 0.5 * (r_out - r_in)
    z1, z2 = mm(layers_z_mm[0]), mm(layers_z_mm[1])
    tw = mm(trace_mm)
    return (
        Coil("RX_sin", (_ring_rx(r_m, amp, n_periods, z1, z2, np.sin, n_theta, layer_swap),), tw),
        Coil("RX_cos", (_ring_rx(r_m, amp, n_periods, z1, z2, np.cos, n_theta, layer_swap),), tw),
    )


def _circle(r, z, n=360) -> np.ndarray:
    th = np.linspace(0.0, 2 * np.pi, n + 1)[:-1]
    return np.column_stack([r * np.cos(th), r * np.sin(th), np.full_like(th, z)])


def ring_tx(
    r_in_mm: float,
    r_out_mm: float,
    n_turns: int,
    pitch_mm: float,
    layers_z_mm: Sequence[float],
    n_theta: int = 360,
    trace_mm: float = 0.1524,
) -> Coil:
    """Annular transmit loop: `n_turns` circles stepping inward from r_out (sense +1)
    and `n_turns` stepping outward from r_in (sense -1) on each layer."""
    loops = []
    for z_mm in layers_z_mm:
        for k in range(n_turns):
            loops.append(Loop(_circle(mm(r_out_mm) - k * mm(pitch_mm), mm(z_mm), n_theta), sense=1))
            loops.append(Loop(_circle(mm(r_in_mm) + k * mm(pitch_mm), mm(z_mm), n_theta), sense=-1))
    return Coil("TX", tuple(loops), mm(trace_mm))


# --------------------------------------------------------------------------- sheets


@dataclass(frozen=True)
class Sheet:
    """A thin perfectly conducting sheet meshed into square cells.

    `side` is the cell side per cell (m) and `corners` the four CCW vertex offsets of
    every cell from its centre, shape (n, 4, 3). Cells rotate rigidly with the sheet,
    so the cell-to-cell geometry (hence the K matrix) is invariant under `translated`
    and `rotated`. Sheets with different cell sizes can be joined with `union` for a
    single solve (a target over a finite back-plane, say).
    """

    centers: np.ndarray  # (n, 3)
    side: np.ndarray  # (n,) or scalar
    corners: np.ndarray = field(default=None)  # (n, 4, 3)
    outline: tuple = ()  # tuple of (k, 2) polygons in metres, for plotting
    lattice: np.ndarray = field(default=None)  # (n, 2) integer grid indices, for the Toeplitz K build
    block: np.ndarray = field(default=None)  # (n,) which uniform mesh a cell belongs to (unions)

    def __post_init__(self):
        c = np.asarray(self.centers, dtype=float).reshape(-1, 3)
        object.__setattr__(self, "centers", c)
        side = np.broadcast_to(np.asarray(self.side, dtype=float), (c.shape[0],)).copy()
        object.__setattr__(self, "side", side)
        if self.corners is None:
            h = side[:, None] / 2
            unit = np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]], dtype=float)
            object.__setattr__(self, "corners", unit[None, :, :] * h[:, :, None])
        else:
            object.__setattr__(self, "corners", np.asarray(self.corners, dtype=float).reshape(-1, 4, 3))
        object.__setattr__(self, "outline", tuple(np.asarray(o, dtype=float) for o in self.outline))
        if self.lattice is not None:
            object.__setattr__(self, "lattice", np.asarray(self.lattice, dtype=np.int64).reshape(-1, 2))
        block = np.zeros(c.shape[0], dtype=np.int64) if self.block is None else np.asarray(self.block, dtype=np.int64)
        object.__setattr__(self, "block", block)

    @property
    def n(self) -> int:
        return self.centers.shape[0]

    @property
    def a(self) -> float:
        """Cell side (m) when uniform; raises for a union of different meshes."""
        if self.n and not np.allclose(self.side, self.side[0]):
            raise ValueError("non-uniform cell size; use cell_area()")
        return float(self.side[0]) if self.n else float("nan")

    @property
    def z(self) -> float:
        return float(self.centers[0, 2]) if self.n else float("nan")

    def cell_area(self) -> np.ndarray:
        return self.side**2

    def area(self) -> float:
        return float(np.sum(self.cell_area()))

    def cell_loops(self) -> Segments:
        """All cell boundaries as unit-current CCW loops, cell-major (4 segments each)."""
        v = self.centers[:, None, :] + self.corners  # (n, 4, 3)
        p0 = v.reshape(-1, 3)
        p1 = np.roll(v, -1, axis=1).reshape(-1, 3)
        return Segments(p0, p1, np.ones(p0.shape[0]))

    def translated(self, d) -> "Sheet":
        d = np.asarray(d, dtype=float).reshape(3)
        return Sheet(self.centers + d, self.side, self.corners, tuple(o + d[:2] for o in self.outline), self.lattice, self.block)

    def translated_mm(self, d_mm) -> "Sheet":
        return self.translated(mm(np.asarray(d_mm, dtype=float)))

    def rotated(self, angle: float, about=(0.0, 0.0)) -> "Sheet":
        """Rotate about the z axis through `about` (m) by `angle` (rad)."""
        R = _rot_z(angle)
        ab = np.array([about[0], about[1], 0.0])
        centers = (self.centers - ab) @ R.T + ab
        corners = self.corners @ R.T
        outline = tuple((o - ab[:2]) @ R[:2, :2].T + ab[:2] for o in self.outline)
        return Sheet(centers, self.side, corners, outline, self.lattice, self.block)

    def rotated_deg(self, angle_deg: float, about_mm=(0.0, 0.0)) -> "Sheet":
        return self.rotated(np.deg2rad(angle_deg), about=(mm(about_mm[0]), mm(about_mm[1])))

    def union(self, other: "Sheet") -> "Sheet":
        """Join two sheets into one solve domain (cells keep their own size)."""
        lattice = None
        if self.lattice is not None and other.lattice is not None:
            lattice = np.vstack([self.lattice, other.lattice])
        return Sheet(
            np.vstack([self.centers, other.centers]),
            np.concatenate([self.side, other.side]),
            np.vstack([self.corners, other.corners]),
            self.outline + other.outline,
            lattice,
            np.concatenate([self.block, other.block + self.block.max() + 1]),
        )

    def plot(self, ax, color="0.3", cells=False, label=None):
        first = True
        for o in self.outline:
            p = np.vstack([o, o[:1]])
            ax.plot(to_mm(p[:, 0]), to_mm(p[:, 1]), color=color, lw=1.0, label=label if first else None)
            first = False
        if cells:
            ax.scatter(to_mm(self.centers[:, 0]), to_mm(self.centers[:, 1]), s=2, color=color, alpha=0.4)
        ax.set_aspect("equal")
        return ax


def union(sheets: Sequence[Sheet]) -> Sheet:
    out = sheets[0]
    for s in sheets[1:]:
        out = out.union(s)
    return out


def mesh_sheet(inside: Callable[[np.ndarray, np.ndarray], np.ndarray], bbox_mm, a_mm: float, z_mm: float, outline_mm=()) -> Sheet:
    """Square-cell mesh of the region where `inside(x_mm, y_mm)` is true, within
    bbox_mm = (xmin, xmax, ymin, ymax). Cells are kept on their centre."""
    xmin, xmax, ymin, ymax = bbox_mm
    nx = max(int(np.ceil((xmax - xmin) / a_mm - 1e-9)), 1)
    ny = max(int(np.ceil((ymax - ymin) / a_mm - 1e-9)), 1)
    # centre the grid on the bbox so symmetric shapes mesh symmetrically
    x0 = 0.5 * (xmin + xmax) - 0.5 * (nx - 1) * a_mm
    y0 = 0.5 * (ymin + ymax) - 0.5 * (ny - 1) * a_mm
    xs = x0 + a_mm * np.arange(nx)
    ys = y0 + a_mm * np.arange(ny)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    keep = inside(X.ravel(), Y.ravel())
    centers = np.column_stack([X.ravel()[keep], Y.ravel()[keep], np.full(int(keep.sum()), z_mm)])
    I, J = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
    lattice = np.column_stack([I.ravel()[keep], J.ravel()[keep]])
    return Sheet(mm(centers), mm(a_mm), None, tuple(mm(np.asarray(o, dtype=float)) for o in outline_mm), lattice)


def rect_sheet(lx_mm: float, ly_mm: float, a_mm: float, z_mm: float, hole_r_mm: float = 0.0) -> Sheet:
    """Rectangle lx (x) by ly (y) centred on the origin, optional central round hole."""

    def inside(x, y):
        ok = (np.abs(x) <= lx_mm / 2 + 1e-9) & (np.abs(y) <= ly_mm / 2 + 1e-9)
        if hole_r_mm > 0:
            ok &= np.hypot(x, y) > hole_r_mm
        return ok

    outline = [np.array([[-lx_mm / 2, -ly_mm / 2], [lx_mm / 2, -ly_mm / 2], [lx_mm / 2, ly_mm / 2], [-lx_mm / 2, ly_mm / 2]])]
    if hole_r_mm > 0:
        outline.append(_circle(hole_r_mm, 0.0, 180)[:, :2])
    return mesh_sheet(inside, (-lx_mm / 2, lx_mm / 2, -ly_mm / 2, ly_mm / 2), a_mm, z_mm, outline)


def _ang_dist_deg(x, y, centres_deg):
    ang = np.degrees(np.arctan2(y, x))
    d = np.full_like(ang, 360.0)
    for c in np.atleast_1d(centres_deg):
        dd = np.abs(((ang - c) + 180.0) % 360.0 - 180.0)
        d = np.minimum(d, dd)
    return d


def _sector_outline(r1, r2, c_deg, half_deg, n=40):
    th = np.deg2rad(np.linspace(c_deg - half_deg, c_deg + half_deg, n))
    outer = np.column_stack([r2 * np.cos(th), r2 * np.sin(th)])
    inner = np.column_stack([r1 * np.cos(th[::-1]), r1 * np.sin(th[::-1])])
    return np.vstack([outer, inner])


def sector_sheet(r1_mm: float, r2_mm: float, angle_deg: float, k: int, a_mm: float, z_mm: float, phase_deg: float = 0.0) -> Sheet:
    """`k` identical annular sectors of `angle_deg` between radii r1 and r2, spaced
    360/k apart, the first centred on `phase_deg`."""
    centres = phase_deg + 360.0 * np.arange(k) / k

    def inside(x, y):
        r = np.hypot(x, y)
        return (r >= r1_mm) & (r <= r2_mm) & (_ang_dist_deg(x, y, centres) <= angle_deg / 2)

    outline = [_sector_outline(r1_mm, r2_mm, c, angle_deg / 2) for c in centres]
    return mesh_sheet(inside, (-r2_mm, r2_mm, -r2_mm, r2_mm), a_mm, z_mm, outline)


def disc_sheet(
    r_out_mm: float,
    a_mm: float,
    z_mm: float,
    r_hole_mm: float = 0.0,
    n_slots: int = 0,
    slot_deg: float = 0.0,
    slot_r_mm: tuple[float, float] | None = None,
    phase_deg: float = 0.0,
) -> Sheet:
    """Disc with an optional central hole and optional radial slots (metal removed),
    `n_slots` of `slot_deg` on an even pitch between slot_r_mm = (r1, r2)."""
    sr1, sr2 = slot_r_mm if slot_r_mm else (r_hole_mm, r_out_mm)

    def inside(x, y):
        r = np.hypot(x, y)
        ok = (r <= r_out_mm) & (r >= r_hole_mm)
        if n_slots > 0 and slot_deg > 0:
            centres = phase_deg + 360.0 * np.arange(n_slots) / n_slots
            in_slot = (_ang_dist_deg(x, y, centres) < slot_deg / 2) & (r >= sr1) & (r <= sr2)
            ok &= ~in_slot
        return ok

    outline = [_circle(r_out_mm, 0.0, 180)[:, :2]]
    if r_hole_mm > 0:
        outline.append(_circle(r_hole_mm, 0.0, 180)[:, :2])
    if n_slots > 0 and slot_deg > 0:
        for c in phase_deg + 360.0 * np.arange(n_slots) / n_slots:
            outline.append(_sector_outline(sr1, sr2, c, slot_deg / 2, n=6))
    return mesh_sheet(inside, (-r_out_mm, r_out_mm, -r_out_mm, r_out_mm), a_mm, z_mm, outline)


class ImagePlane:
    """An infinite perfectly conducting plane at height z (image method)."""

    def __init__(self, z_mm: float):
        self.z = mm(z_mm)

    def __repr__(self):
        return f"ImagePlane(z_mm={to_mm(self.z):.3f})"
