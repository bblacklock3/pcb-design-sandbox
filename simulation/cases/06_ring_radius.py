"""Case 06 -- how narrow can the yaw ring be?

The inner radius is pinned by the 30 mm beam hole, so board area and mass fall by
pulling the outer radius in. The cost is receive-lobe amplitude A: on a two-layer ring
the transmit turns take about 1 mm of band on each edge, on a four-layer ring the
transmit turns sit under the lobes on their own layers (as on the leaf coil) and the
lobes can use the whole band. Sweep r_out for both layouts at gap 1.0 mm, standoff
1.0 mm, pocketed 60 deg face target, and report signal, tank, raw error and the
dense-LUT sensitivity to gap and plane movement.

Run:  python cases/06_ring_radius.py [--workers N]
Read: out/06_ring_radius/REPORT.md
"""
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from indsim import geometry as g, plot, sensor, sheet, tables  # noqa: E402
from indsim.parallel import pmap  # noqa: E402

spec = importlib.util.spec_from_file_location("c04", HERE / "04_yaw_stack_study.py")
c04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c04)

OUT = HERE.parent / "out" / "06_ring_radius"
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else None

R_IN = 17.0                      # 30 mm hole plus 2 mm of board
R_OUTS = (21.0, 23.0, 25.0, 27.0, 29.0)
N = 2
GAP, STANDOFF = 1.0, 1.0
POCKET_DEG, OVERHANG = 60.0, 2.0
TX_TURNS, TX_PITCH, TRACE = 4, 0.2032 + 0.1524, 0.2032   # 4 turns per edge, 8 mil trace / 6 mil gap
CLEAR = 0.3                      # trace clearance between the lobe extreme and the nearest TX turn
C_TANK = 500e-12
STEP, DELTA = 5.0, 0.25
BOARD_BACK = -1.0

# layouts: (name, RX layers, TX layers, TX turns inside the lobe band?)
LAYOUTS = (
    ("2-layer, TX at band edges", (0.0, -1.0), (0.0, -1.0), False),
    ("4-layer, TX under the lobes", (0.0, -0.2), (-0.8, -1.0), True),
)


def build(r_out, layout):
    name, rx_layers, tx_layers, tx_under = layout
    band = r_out - R_IN
    if tx_under:
        amp = (band - 2 * CLEAR) / 2
        tx = g.ring_tx(R_IN + CLEAR, r_out - CLEAR, TX_TURNS, TX_PITCH, tx_layers, n_theta=180, trace_mm=TRACE)
    else:
        edge = TX_TURNS * TX_PITCH
        amp = (band - 2 * edge - 2 * CLEAR) / 2
        tx = g.ring_tx(R_IN, r_out, TX_TURNS, TX_PITCH, tx_layers, n_theta=180, trace_mm=TRACE)
    if amp < 0.5:
        return None, None, None, amp
    rs, rc = g.ring_rx_pair(R_IN, r_out, N, rx_layers, amp_mm=amp, n_theta=360, trace_mm=0.1524)
    return tx, rs, rc, amp


def condition(args):
    r_out, layout = args
    tx, rs, rc, amp = build(r_out, layout)
    if tx is None:
        return (layout[0], r_out, amp, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    t0 = time.time()
    plane = g.ImagePlane(BOARD_BACK - STANDOFF)
    area = np.pi * ((r_out + OVERHANG) ** 2 - (R_IN - OVERHANG) ** 2) * 2 / 3
    cell = c04.cell_for_gap(GAP, area)
    tg = g.disc_sheet(r_out + OVERHANG, cell, GAP, r_hole_mm=R_IN - OVERHANG, n_slots=2, slot_deg=POCKET_DEG)
    thetas = np.arange(0.0, 360.0 / N + STEP / 2, STEP)
    tabs = {}

    def sweep(target, pl, key):
        if key not in tabs:
            tabs[key] = tables.ring_tables(tx, rs, rc, target, N, plane=pl, r_min_mm=R_IN - OVERHANG - 1.5, r_max_mm=r_out + OVERHANG + 1.5)
        return sensor.run_sweep(tx, rs, rc, lambda th: target.rotated_deg(th), thetas, plane=pl, tables=tabs[key])

    res = sweep(tg, plane, "nom")
    a = c04.analyse(res, thetas)
    r_g = sweep(tg.translated_mm((0, 0, DELTA)), plane, "gap")
    r_p = sweep(tg, g.ImagePlane(BOARD_BACK - STANDOFF + DELTA), "plane")
    dense_gap = c04.dense_delta(a, r_g, thetas, a["err_raw"], thetas)
    dense_plane = c04.dense_delta(a, r_p, thetas, a["err_raw"], thetas)
    tank = sensor.tank(tx, C_TANK, plane=plane)
    ps = sheet.SheetSolver(tg, plane)
    dL = sheet.rx_flux(tg, ps.respond(tx.segments()), tx.segments(), plane)
    L_loaded = tank["L"] + dL
    mass_rel = ((r_out + 2) ** 2 - (R_IN - 2) ** 2) / ((29.0 + 2) ** 2 - (R_IN - 2) ** 2)  # board area vs the 29 mm ring
    return (layout[0], r_out, amp, a["amp"] * 1e9, a["raw_max"], dense_plane, dense_gap, tank["L"] * 1e6, L_loaded * 1e6,
            tank["Q"], mass_rel, time.time() - t0)


HEADER = ("layout", "r_out_mm", "lobe_amp_mm", "signal_nWb_per_A", "raw_deg", "dense_plane_minus025_deg", "dense_gap_plus025_deg",
          "L_uH", "L_with_target_uH", "Q", "board_area_rel", "seconds")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    conds = [(r, lay) for lay in LAYOUTS for r in R_OUTS]
    rows = pmap(condition, conds, WORKERS)
    for r in rows:
        print(f"{r[0]} r_out {r[1]}: A {r[2]:.2f} mm, signal {r[3]:.1f}, raw {r[4]:.3f}, dense plane {r[5]:.4f} gap {r[6]:.4f}, "
              f"L {r[7]:.2f} -> {r[8]:.2f} uH, Q {r[9]:.0f}, area {r[10]:.2f} ({r[11]:.0f} s)")
    c04.write_rows_text(OUT / "radius.csv", HEADER, rows)
    lines = ["# Case 06 -- ring outer radius", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')}. r_in {R_IN} mm (30 mm hole), gap {GAP} mm, standoff {STANDOFF} mm, "
             f"pocketed face with two {POCKET_DEG:.0f} deg pockets and {OVERHANG} mm overhang, TX {TX_TURNS} turns per edge at "
             f"{TRACE/0.0254:.0f} mil, C = {C_TANK*1e12:.0f} pF. board_area_rel is the ring board area against the r 29 mm ring "
             "(both with a 2 mm rim).", "",
             "Two-layer: transmit turns occupy the band edges and the lobes get what is left. Four-layer: transmit turns sit under",
             "the lobes on layers 3-4 (as on the leaf coil) so the lobes use the whole band. lobe_amp 0 means the band is too",
             "narrow for that layout.", "",
             c04.md_table(HEADER, rows), "", "![[signal_vs_rout.png]] ![[dense_vs_rout.png]] ![[L_vs_rout.png]]", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))
    for idx, title, ylabel, fname in ((3, "Signal Vs Outer Radius", "Flux Amplitude (nWb/A)", "signal_vs_rout.png"),
                                      (6, "Dense LUT Residual, Gap +0.25 mm, Vs Outer Radius", "Residual (mech deg)", "dense_vs_rout.png"),
                                      (8, "Transmit Inductance With Target Vs Outer Radius", "Inductance (uH)", "L_vs_rout.png")):
        fig, ax = plot.figure()
        for lay in LAYOUTS:
            sel = [r for r in rows if r[0] == lay[0] and r[2] > 0]
            ax.plot([r[1] for r in sel], [r[idx] for r in sel], marker="o", label=lay[0].title())
        if idx == 8:
            ax.axhline(3.0, color="0.5", ls="--", label="LX34311 Minimum")
        plot.finish(fig, ax, title, "Outer Radius (mm)", ylabel, OUT / fname, legend=True)
    print(f"done in {(time.time()-t0)/60:.1f} min -> {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
