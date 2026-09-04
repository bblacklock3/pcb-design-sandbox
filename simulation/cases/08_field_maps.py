"""Case 08 -- field maps of the final yaw ring (case 07 configuration).

Pictures, for understanding rather than numbers:
  1. Bz of the transmit coil (with the main-board image) on the target plane, top view
  2. Bz of the sine receive coil on the target plane, top view (the N = 2 pattern)
  3. Eddy-current streamlines on the pocketed face: contours of the solved stream
     function psi are the current paths
  4. Radial cross-sections (r-z plane) through a pocket and through the metal: |B| and
     field lines of transmit plus image plus target currents, with the ring board,
     target and main board drawn in

Run:  python cases/08_field_maps.py
Read: out/08_field_maps/*.png
"""
import importlib.util
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from indsim import biot, geometry as g, plot, sheet  # noqa: E402
from indsim.biot import Segments  # noqa: E402
from indsim.geometry import MM, to_mm  # noqa: E402

spec = importlib.util.spec_from_file_location("c07", HERE / "07_yaw_ring_final.py")
c07 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c07)

OUT = HERE.parent / "out" / "08_field_maps"
DIVERGING = "RdBu_r"      # two hues, neutral midpoint, for signed Bz
SEQUENTIAL = "Blues"      # one hue, light to dark, for |B|
GRID_MM = 0.25            # top-view sample spacing
XSEC_MM = 0.1             # cross-section sample spacing


def coil_outline(ax, coils, colors=("0.25", "#d55e00", "#009e73")):
    for c, col in zip(coils, colors):
        for loop in c.loops:
            p = np.vstack([loop.pts, loop.pts[:1]])
            ax.plot(to_mm(p[:, 0]), to_mm(p[:, 1]), color=col, lw=0.5, alpha=0.8)


def top_view(field, extent_mm, title, fname, coils, target=None, cmap=DIVERGING, label="Bz Per Ampere Of TX (uT/A)", symmetric=True):
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    vmax = np.nanmax(np.abs(field))
    kw = dict(vmin=-vmax, vmax=vmax) if symmetric else dict(vmin=0, vmax=vmax)
    im = ax.imshow(field.T, origin="lower", extent=[-extent_mm, extent_mm, -extent_mm, extent_mm], cmap=cmap, **kw)
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    cb.set_label(label)
    coil_outline(ax, coils)
    if target is not None:
        target.plot(ax, color="0.1")
    ax.set_aspect("equal")
    plot.finish(fig, ax, title, "X (mm)", "Y (mm)", OUT / fname)


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    tx, rs, rc = c07.coils()
    plane = g.ImagePlane(c07.BOARD_BACK - c07.STANDOFF)
    tg = c07.pocket_target(cell=0.4)
    tx_s = tx.segments()
    tx_eff = Segments.concat([tx_s, biot.mirror(tx_s, plane.z)])
    rs_s = rs.segments()

    # ---------------- top views on the target plane
    ext = c07.TARGET_R2 + 2.0
    xs = np.arange(-ext, ext + GRID_MM / 2, GRID_MM)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    pts = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, c07.GAP)]) * MM
    bz_tx = biot.bz(tx_eff, pts).reshape(X.shape) * 1e6
    top_view(bz_tx, ext, "Transmit Field On The Target Plane, Main Board 1 mm Behind", "01_tx_bz_top.png", (tx, rs, rc), tg)
    bz_rx = biot.bz(rs_s, pts).reshape(X.shape) * 1e6
    top_view(bz_rx, ext, "Sine Receive Coil Field On The Target Plane", "02_rx_sin_bz_top.png", (tx, rs, rc), tg,
             label="Bz Per Ampere Of RX (uT/A)")
    print(f"top views {time.time()-t0:.0f} s")

    # ---------------- eddy currents on the target: stream function contours
    solver = sheet.SheetSolver(tg, plane)
    psi = solver.respond(tx_s)
    cx, cy = to_mm(tg.centers[:, 0]), to_mm(tg.centers[:, 1])
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    import matplotlib.tri as mtri
    tri = mtri.Triangulation(cx, cy)
    # drop triangles that bridge the pockets or the hole (long edges)
    xy = np.column_stack([cx, cy])
    tp = tri.triangles
    edge = np.max([np.linalg.norm(xy[tp[:, i]] - xy[tp[:, (i + 1) % 3]], axis=1) for i in range(3)], axis=0)
    tri.set_mask(edge > 1.5 * tg.a / MM)
    vmax = np.abs(psi).max() * 1e3
    cf = ax.tricontourf(tri, psi * 1e3, levels=np.linspace(-vmax, vmax, 41), cmap=DIVERGING)
    ax.tricontour(tri, psi * 1e3, levels=16, colors="0.15", linewidths=0.4)
    cb = fig.colorbar(cf, ax=ax, shrink=0.85)
    cb.set_label("Stream Function Per Ampere Of TX (mA/A)")
    coil_outline(ax, (tx, rs, rc))
    tg.plot(ax, color="0.1")
    ax.set_aspect("equal")
    plot.finish(fig, ax, "Eddy Current Streamlines On The Pocketed Face", "X (mm)", "Y (mm)", OUT / "03_target_eddy_streamlines.png")
    print(f"eddy currents {time.time()-t0:.0f} s")

    # ---------------- cross-sections: r-z plane at two azimuths
    cells = tg.cell_loops()
    cell_src = Segments(cells.p0, cells.p1, np.repeat(psi, 4))
    all_src = Segments.concat([tx_eff, cell_src, biot.mirror(cell_src, plane.z)])
    r = np.arange(9.0, 31.0 + XSEC_MM / 2, XSEC_MM)
    z = np.arange(-3.0, 4.0 + XSEC_MM / 2, XSEC_MM)
    R, Z = np.meshgrid(r, z, indexing="ij")
    for th_deg, tag, fname in ((90.0, "Through The Metal", "04_xsec_metal.png"), (0.0, "Through A Pocket", "05_xsec_pocket.png")):
        th = np.deg2rad(th_deg)
        pts = np.column_stack([R.ravel() * np.cos(th), R.ravel() * np.sin(th), Z.ravel()]) * MM
        B = biot.bfield(all_src, pts)
        Br = (B[:, 0] * np.cos(th) + B[:, 1] * np.sin(th)).reshape(R.shape)
        Bz = B[:, 2].reshape(R.shape)
        mag = np.hypot(Br, Bz) * 1e6
        fig, ax = plt.subplots(figsize=(7.2, 3.6))
        # colour range from the bulk of the field, not the points that land on a filament
        lo, hi = np.percentile(np.log10(mag), [3, 99])
        im = ax.pcolormesh(R, Z, np.clip(np.log10(mag), lo, hi), cmap=SEQUENTIAL, shading="auto", vmin=lo, vmax=hi)
        cb = fig.colorbar(im, ax=ax, shrink=0.9)
        cb.set_label("log10 |B| Per Ampere Of TX (uT/A)")
        ax.streamplot(r, z, Br.T, Bz.T, color="0.2", linewidth=0.6, density=1.4, arrowsize=0.7)
        # hardware: ring board, target sheet, main board pour, TX/RX copper radii
        ax.fill_between([c07.R_IN - 2, c07.R_OUT + 2], c07.BOARD_BACK, 0.0, color="#7f7f7f", alpha=0.35, lw=0)
        # below the main-board pour is the image construction, not a physical region
        ax.fill_between([r.min(), r.max()], z.min(), plane.z / MM, color="#c8c8c8", alpha=0.85, lw=0, zorder=3)
        ax.axhline(plane.z / MM, color="#d55e00", lw=2, zorder=4)
        in_metal = th_deg == 90.0
        ax.plot([c07.TARGET_R1, c07.TARGET_R2], [c07.GAP, c07.GAP], color="0.05", lw=2.5 if in_metal else 0.0)
        if not in_metal:
            ax.plot([c07.TARGET_R1, c07.TARGET_R2], [c07.GAP, c07.GAP], color="0.05", lw=1.0, ls=":")
        for loop in tx.loops:
            rr = np.hypot(loop.pts[0, 0], loop.pts[0, 1]) / MM
            ax.plot(rr, loop.pts[0, 2] / MM, "s", color="#1f77b4", ms=3)
        ax.set_xlim(r.min(), r.max())
        ax.set_ylim(z.min(), z.max())
        ax.set_aspect("equal")
        plot.finish(fig, ax, f"Field Cross Section {tag} (theta {th_deg:.0f} deg)", "Radius (mm)", "Z (mm)", OUT / fname)
        print(f"cross section {tag} {time.time()-t0:.0f} s")
    print(f"done in {time.time()-t0:.0f} s -> {OUT}")


if __name__ == "__main__":
    main()
