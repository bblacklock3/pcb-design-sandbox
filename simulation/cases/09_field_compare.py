"""Case 09 -- leaf coil and yaw ring field maps side by side, same spatial scale.

Left: the built leaf coil (case 01 configuration: lambda 15 mm, 7.6 mm lobes, TX 4 turns on
each of two layers, 5 x 10 mm flag at 1 mm, no board behind). Right: the proposed yaw ring
(case 07: r 17-23, pocketed face at 1 mm, main board pour 1 mm behind). Every pair shares
axis limits (so 1 mm is the same length in both panels) and one colour scale.

  1. transmit Bz on the target plane
  2. sine receive coil Bz on the target plane
  3. eddy-current streamlines on the target (stream function contours)
  4. cross-section perpendicular to the sensing direction, through the target metal
  5. the same cut where there is no target metal

Run:  python cases/09_field_compare.py
Read: out/09_field_compare/*.png
"""
import importlib.util
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.tri as mtri  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from indsim import biot, geometry as g, plot, sheet  # noqa: E402
from indsim.biot import Segments  # noqa: E402
from indsim.geometry import MM, to_mm  # noqa: E402

spec = importlib.util.spec_from_file_location("c07", HERE / "07_yaw_ring_final.py")
c07 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c07)

OUT = HERE.parent / "out" / "09_field_compare"
DIVERGING, SEQUENTIAL = "RdBu_r", "Blues"
EXT = 27.0                 # mm, half-width of every top view (the ring sets it)
GRID = 0.25
XSEC = 0.1
Z_RANGE = (-3.0, 4.0)
XSEC_HALF = 11.0           # mm, half-span of the cross-section cuts (22 mm, matching r 9-31 for the ring)

# ---------------- leaf (case 01)
LEAF = dict(lam=15.0, lobe=7.6, n_lobes=2, rx_z=(0.0, -0.2), tx_z=(-1.4, -1.6), tx_len=18.0, tx_wid=9.6,
            tx_turns=4, tx_pitch=0.3048, corner=1.0, target=(5.0, 10.0), gap=1.0, cell=0.25)


def leaf_setup():
    rs, rc = g.linear_rx_pair(LEAF["lam"], LEAF["lobe"], LEAF["n_lobes"], LEAF["rx_z"])
    tx = g.rect_tx(LEAF["tx_len"], LEAF["tx_wid"], LEAF["tx_turns"], LEAF["tx_pitch"], LEAF["tx_z"], corner_r_mm=LEAF["corner"])
    tg = g.rect_sheet(LEAF["target"][0], LEAF["target"][1], LEAF["cell"], LEAF["gap"])
    return tx, rs, rc, tg, None


def ring_setup():
    tx, rs, rc = c07.coils()
    plane = g.ImagePlane(c07.BOARD_BACK - c07.STANDOFF)
    return tx, rs, rc, c07.pocket_target(cell=0.4), plane


def with_image(segs, plane):
    return segs if plane is None else Segments.concat([segs, biot.mirror(segs, plane.z)])


def outline(ax, coils, target, colors=("0.25", "#d55e00", "#009e73")):
    for c, col in zip(coils, colors):
        for loop in c.loops:
            p = np.vstack([loop.pts, loop.pts[:1]])
            ax.plot(to_mm(p[:, 0]), to_mm(p[:, 1]), color=col, lw=0.5, alpha=0.8)
    target.plot(ax, color="0.1")


def pair_figure(title, label, panels, fname, cmap, symmetric=True):
    """Two top-view panels with identical limits and one colour scale.
    panels: list of (subtitle, field (n, n) on the shared grid, coils, target)."""
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.8))
    vmax = max(np.nanmax(np.abs(f)) for _, f, _, _ in panels)
    kw = dict(vmin=-vmax, vmax=vmax) if symmetric else dict(vmin=0, vmax=vmax)
    for ax, (sub, field, coils, target) in zip(axes, panels):
        im = ax.imshow(field.T, origin="lower", extent=[-EXT, EXT, -EXT, EXT], cmap=cmap, **kw)
        outline(ax, coils, target)
        ax.set_aspect("equal")
        ax.set_xlim(-EXT, EXT)
        ax.set_ylim(-EXT, EXT)
        ax.set_title(sub)
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.grid(alpha=0.3)
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
    cb.set_label(label)
    plot.check_ascii(title, label, *[p[0] for p in panels])
    fig.suptitle(title)
    fig.savefig(OUT / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    setups = {"leaf": leaf_setup(), "ring": ring_setup()}
    xs = np.arange(-EXT, EXT + GRID / 2, GRID)
    X, Y = np.meshgrid(xs, xs, indexing="ij")

    # ---------------- 1, 2: top views on each target plane
    tx_panels, rx_panels = [], []
    psi = {}
    for name, sub in (("leaf", "Leaf Coil, Flag At 1 mm, No Board Behind"), ("ring", "Yaw Ring r 17-23, Face At 1 mm, Main Board 1 mm Behind")):
        tx, rs, rc, tg, plane = setups[name]
        pts = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, tg.z / MM)]) * MM
        tx_panels.append((sub, biot.bz(with_image(tx.segments(), plane), pts).reshape(X.shape) * 1e6, (tx, rs, rc), tg))
        rx_panels.append((sub, biot.bz(rs.segments(), pts).reshape(X.shape) * 1e6, (tx, rs, rc), tg))
        psi[name] = sheet.SheetSolver(tg, plane).respond(tx.segments())
    pair_figure("Transmit Field On The Target Plane", "Bz Per Ampere Of TX (uT/A)", tx_panels, "01_tx_bz_top.png", DIVERGING)
    pair_figure("Sine Receive Coil Field On The Target Plane", "Bz Per Ampere Of RX (uT/A)", rx_panels, "02_rx_sin_bz_top.png", DIVERGING)
    print(f"top views {time.time()-t0:.0f} s")

    # ---------------- 3: eddy currents
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.8))
    vmax = max(np.abs(psi[n]).max() for n in psi) * 1e3
    for ax, name, sub in zip(axes, ("leaf", "ring"), ("Leaf Flag 5 x 10 mm", "Pocketed Face, Two 60 deg Pockets")):
        tx, rs, rc, tg, plane = setups[name]
        cx, cy = to_mm(tg.centers[:, 0]), to_mm(tg.centers[:, 1])
        tri = mtri.Triangulation(cx, cy)
        xy = np.column_stack([cx, cy])
        tp = tri.triangles
        edge = np.max([np.linalg.norm(xy[tp[:, i]] - xy[tp[:, (i + 1) % 3]], axis=1) for i in range(3)], axis=0)
        tri.set_mask(edge > 1.5 * tg.a / MM)
        cf = ax.tricontourf(tri, psi[name] * 1e3, levels=np.linspace(-vmax, vmax, 41), cmap=DIVERGING)
        ax.tricontour(tri, psi[name] * 1e3, levels=16, colors="0.15", linewidths=0.4)
        outline(ax, (tx, rs, rc), tg)
        ax.set_aspect("equal")
        ax.set_xlim(-EXT, EXT)
        ax.set_ylim(-EXT, EXT)
        ax.set_title(sub)
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.grid(alpha=0.3)
    cb = fig.colorbar(cf, ax=axes, shrink=0.85, pad=0.02)
    cb.set_label("Stream Function Per Ampere Of TX (mA/A)")
    fig.suptitle("Eddy Current Streamlines On The Target")
    fig.savefig(OUT / "03_target_eddy_streamlines.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"eddy currents {time.time()-t0:.0f} s")

    # ---------------- 4, 5: cross-sections perpendicular to the sensing direction
    u = np.arange(-XSEC_HALF, XSEC_HALF + XSEC / 2, XSEC)
    z = np.arange(Z_RANGE[0], Z_RANGE[1] + XSEC / 2, XSEC)
    U, Z = np.meshgrid(u, z, indexing="ij")
    cuts = {
        "metal": ("Cut Through The Target Metal", {"leaf": ("x = 0, across travel", 0.0), "ring": ("theta = 90 deg", 90.0)}, "04_xsec_metal.png"),
        "open": ("Cut Where There Is No Target Metal", {"leaf": ("x = 7 mm, beyond the flag", 7.0), "ring": ("theta = 0, through a pocket", 0.0)}, "05_xsec_open.png"),
    }
    fields = {}
    for key, (title, where, fname) in cuts.items():
        for name in ("leaf", "ring"):
            tx, rs, rc, tg, plane = setups[name]
            cells = tg.cell_loops()
            cell_src = Segments(cells.p0, cells.p1, np.repeat(psi[name], 4))
            src = Segments.concat([with_image(tx.segments(), plane), with_image(cell_src, plane)])
            if name == "leaf":
                x0 = where[name][1]
                pts = np.column_stack([np.full(U.size, x0), U.ravel(), Z.ravel()]) * MM
                B = biot.bfield(src, pts)
                Bu, Bz = B[:, 1].reshape(U.shape), B[:, 2].reshape(U.shape)
            else:
                th = np.deg2rad(where[name][1])
                rr = U.ravel() + 20.0  # centre the 22 mm window on the band centre r = 20
                pts = np.column_stack([rr * np.cos(th), rr * np.sin(th), Z.ravel()]) * MM
                B = biot.bfield(src, pts)
                Bu = (B[:, 0] * np.cos(th) + B[:, 1] * np.sin(th)).reshape(U.shape)
                Bz = B[:, 2].reshape(U.shape)
            fields[(key, name)] = (Bu, Bz)
        # shared colour range from both panels
        mags = [np.hypot(*fields[(key, n)]) * 1e6 for n in ("leaf", "ring")]
        lo, hi = np.percentile(np.log10(np.concatenate([m.ravel() for m in mags])), [3, 99])
        fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.2))
        for ax, name, mag in zip(axes, ("leaf", "ring"), mags):
            tx, rs, rc, tg, plane = setups[name]
            Bu, Bz = fields[(key, name)]
            im = ax.pcolormesh(U, Z, np.clip(np.log10(mag), lo, hi), cmap=SEQUENTIAL, shading="auto", vmin=lo, vmax=hi)
            ax.streamplot(u, z, Bu.T, Bz.T, color="0.2", linewidth=0.6, density=1.3, arrowsize=0.7)
            if name == "leaf":
                ax.fill_between([-LEAF["tx_wid"] / 2 - 0.5, LEAF["tx_wid"] / 2 + 0.5], -1.6, 0.0, color="#7f7f7f", alpha=0.35, lw=0)
                if key == "metal":
                    ax.plot([-LEAF["target"][1] / 2, LEAF["target"][1] / 2], [LEAF["gap"]] * 2, color="0.05", lw=2.5)
                else:
                    ax.plot([-LEAF["target"][1] / 2, LEAF["target"][1] / 2], [LEAF["gap"]] * 2, color="0.05", lw=1.0, ls=":")
                for loop in tx.loops:
                    yy = loop.pts[:, 1] / MM
                    for sgn in (-1, 1):
                        ax.plot(sgn * np.abs(yy).max(), loop.pts[0, 2] / MM, "s", color="#1f77b4", ms=3)
                ax.set_xlabel("Y Across Travel (mm)")
            else:
                ax.fill_between([c07.R_IN - 2 - 20, c07.R_OUT + 2 - 20], c07.BOARD_BACK, 0.0, color="#7f7f7f", alpha=0.35, lw=0)
                ax.fill_between([u.min(), u.max()], z.min(), plane.z / MM, color="#c8c8c8", alpha=0.85, lw=0, zorder=3)
                ax.axhline(plane.z / MM, color="#d55e00", lw=2, zorder=4)
                tr = [c07.TARGET_R1 - 20, c07.TARGET_R2 - 20]
                ax.plot(tr, [c07.GAP] * 2, color="0.05", lw=2.5 if key == "metal" else 1.0, ls="-" if key == "metal" else ":")
                for loop in tx.loops:
                    ax.plot(np.hypot(loop.pts[0, 0], loop.pts[0, 1]) / MM - 20, loop.pts[0, 2] / MM, "s", color="#1f77b4", ms=3)
                ax.set_xlabel("Radius Minus 20 mm (mm)")
            ax.set_xlim(u.min(), u.max())
            ax.set_ylim(*Z_RANGE)
            ax.set_aspect("equal")
            ax.set_ylabel("Z (mm)")
            ax.set_title(("Leaf Coil, " if name == "leaf" else "Yaw Ring, ") + where[name][0])
            ax.grid(alpha=0.3)
        cb = fig.colorbar(im, ax=axes, shrink=0.9, pad=0.02)
        cb.set_label("log10 |B| Per Ampere Of TX (uT/A)")
        fig.suptitle(title)
        fig.savefig(OUT / fname, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"cross section {key} {time.time()-t0:.0f} s")
    print(f"done in {time.time()-t0:.0f} s -> {OUT}")


if __name__ == "__main__":
    main()
