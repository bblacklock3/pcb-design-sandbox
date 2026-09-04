"""Case 06 -- where should the ring's copper band sit?

Two ways to make the ring board smaller: keep the inner radius on the 30 mm beam hole
and pull the outer radius in, or keep the outer radius at the envelope and push the
inner radius out (a thin ring far from the axis, with a larger hole). Same band widths
either way, so the comparison is placement at small versus large radius: lobe arc
length, signal, tank, raw error, dense-LUT sensitivity to gap and plane movement, and
board area and polar moment. Two-layer ring with the transmit turns at the band edges
(the first run of this case showed a four-layer ring with transmit under the lobes buys
signal but not accuracy), gap 1.0 mm, standoff 1.0 mm, pocketed 60 deg face target.

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

R_IN_MIN, R_OUT_MAX = 17.0, 29.0  # 30 mm hole plus 2 mm of board; 62 mm board envelope
# two families of the same band widths: anchored on the hole (r_in fixed, r_out pulled in)
# and anchored on the envelope (r_out fixed, r_in pushed out)
BANDS = ((17.0, 23.0), (17.0, 25.0), (17.0, 27.0), (17.0, 29.0), (19.0, 29.0), (21.0, 29.0), (23.0, 29.0))
RIM = 2.0                        # board rim beyond the copper band, each side
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
)


def build(r_in, r_out, layout):
    name, rx_layers, tx_layers, tx_under = layout
    band = r_out - r_in
    if tx_under:
        amp = (band - 2 * CLEAR) / 2
        tx = g.ring_tx(r_in + CLEAR, r_out - CLEAR, TX_TURNS, TX_PITCH, tx_layers, n_theta=180, trace_mm=TRACE)
    else:
        edge = TX_TURNS * TX_PITCH
        amp = (band - 2 * edge - 2 * CLEAR) / 2
        tx = g.ring_tx(r_in, r_out, TX_TURNS, TX_PITCH, tx_layers, n_theta=180, trace_mm=TRACE)
    if amp < 0.5:
        return None, None, None, amp
    rs, rc = g.ring_rx_pair(r_in, r_out, N, rx_layers, amp_mm=amp, n_theta=360, trace_mm=0.1524)
    return tx, rs, rc, amp


def board_metrics(r_in, r_out):
    """Ring board area and polar moment (uniform sheet) against the r 17-29 ring, rims included."""
    a, b = r_in - RIM, r_out + RIM
    a0, b0 = R_IN_MIN - RIM, R_OUT_MAX + RIM
    area = (b**2 - a**2) / (b0**2 - a0**2)
    inertia = (b**4 - a**4) / (b0**4 - a0**4)
    return area, inertia


def condition(args):
    r_in, r_out, layout = args
    tx, rs, rc, amp = build(r_in, r_out, layout)
    area_rel, inertia_rel = board_metrics(r_in, r_out)
    if tx is None:
        return (layout[0], r_in, r_out, r_out - r_in, amp, 0, 0, 0, 0, 0, 0, 0, area_rel, inertia_rel, 0)
    t0 = time.time()
    plane = g.ImagePlane(BOARD_BACK - STANDOFF)
    area = np.pi * ((r_out + OVERHANG) ** 2 - (r_in - OVERHANG) ** 2) * 2 / 3
    cell = c04.cell_for_gap(GAP, area)
    tg = g.disc_sheet(r_out + OVERHANG, cell, GAP, r_hole_mm=r_in - OVERHANG, n_slots=2, slot_deg=POCKET_DEG)
    thetas = np.arange(0.0, 360.0 / N + STEP / 2, STEP)
    tabs = {}

    def sweep(target, pl, key):
        if key not in tabs:
            tabs[key] = tables.ring_tables(tx, rs, rc, target, N, plane=pl, r_min_mm=r_in - OVERHANG - 1.5, r_max_mm=r_out + OVERHANG + 1.5)
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
    return (layout[0], r_in, r_out, r_out - r_in, amp, a["amp"] * 1e9, a["raw_max"], dense_plane, dense_gap, tank["L"] * 1e6,
            L_loaded * 1e6, tank["Q"], area_rel, inertia_rel, time.time() - t0)


HEADER = ("layout", "r_in_mm", "r_out_mm", "band_mm", "lobe_amp_mm", "signal_nWb_per_A", "raw_deg", "dense_plane_minus025_deg",
          "dense_gap_plus025_deg", "L_uH", "L_with_target_uH", "Q", "board_area_rel", "board_inertia_rel", "seconds")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    conds = [(ri, ro, lay) for lay in LAYOUTS for ri, ro in BANDS]
    rows = pmap(condition, conds, WORKERS)
    for r in rows:
        print(f"{r[0]} r {r[1]:.0f}-{r[2]:.0f} (band {r[3]:.0f}): A {r[4]:.2f} mm, signal {r[5]:.1f}, raw {r[6]:.3f}, dense plane {r[7]:.4f} "
              f"gap {r[8]:.4f}, L {r[9]:.2f} -> {r[10]:.2f} uH, Q {r[11]:.0f}, area {r[12]:.2f} inertia {r[13]:.2f} ({r[14]:.0f} s)")
    c04.write_rows_text(OUT / "radius.csv", HEADER, rows)
    lines = ["# Case 06 -- ring radial placement", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')}. Gap {GAP} mm, standoff {STANDOFF} mm, pocketed face with two "
             f"{POCKET_DEG:.0f} deg pockets and {OVERHANG} mm overhang, TX {TX_TURNS} turns per edge at {TRACE/0.0254:.0f} mil, "
             f"C = {C_TANK*1e12:.0f} pF. Two-layer ring, transmit turns at the band edges.", "",
             f"Bands anchored on the {2*(R_IN_MIN-RIM):.0f} mm hole (r_in {R_IN_MIN}) shrink the board; bands anchored on the "
             f"{2*(R_OUT_MAX+RIM):.0f} mm envelope (r_out {R_OUT_MAX}) push the hole outward. board_area_rel and board_inertia_rel",
             "are for a uniform annulus with 2 mm rims against the r 17-29 ring. Compare rows of equal band_mm.", "",
             c04.md_table(HEADER, rows), "", "![[signal_vs_band.png]] ![[dense_vs_band.png]] ![[L_vs_band.png]]", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))
    for idx, title, ylabel, fname in ((5, "Signal Vs Band Width", "Flux Amplitude (nWb/A)", "signal_vs_band.png"),
                                      (8, "Dense LUT Residual, Gap +0.25 mm, Vs Band Width", "Residual (mech deg)", "dense_vs_band.png"),
                                      (10, "Transmit Inductance With Target Vs Band Width", "Inductance (uH)", "L_vs_band.png")):
        fig, ax = plot.figure()
        for anchor, label in (("in", f"Anchored On The Hole, r_in {R_IN_MIN:.0f}"), ("out", f"Anchored On The Envelope, r_out {R_OUT_MAX:.0f}")):
            sel = [r for r in rows if r[4] > 0 and ((r[1] == R_IN_MIN) if anchor == "in" else (r[2] == R_OUT_MAX))]
            sel.sort(key=lambda r: r[3])
            ax.plot([r[3] for r in sel], [r[idx] for r in sel], marker="o", label=label)
        if idx == 10:
            ax.axhline(3.0, color="0.5", ls="--", label="LX34311 Minimum")
        plot.finish(fig, ax, title, "Band Width (mm)", ylabel, OUT / fname, legend=True)
    print(f"done in {(time.time()-t0)/60:.1f} min -> {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
