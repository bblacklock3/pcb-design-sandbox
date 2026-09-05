"""Case 12 -- what sets the leaf coil's airgap sensitivity, and what reduces it.

After the direct coupling is removed, the reading still changes with airgap because the
coil's spatial harmonics decay with distance at different rates: a component of spatial
wavelength lambda/n falls as exp(-2 pi n z / lambda), so the error curve's shape (which is
made of those higher components) changes as the fundamental does not. Predictions:
the residual per mm of gap change should fall exponentially with nominal gap, scale with
the coil's raw harmonic error, and fall with a longer electrical period.

This case measures, with the flag and tungsten leaf as a rigid pair:
  - residual after a dense LUT for +0.10 and +0.25 mm of gap, at nominal gaps 0.75-2.0 mm
  - the signal amplitude at each gap (the AGC's view of the gap, usable for a 2-D LUT)
for the as-built coil with its offsets trimmed, the end-compensated 6-turn coil, and a
lambda = 18 mm / 6 mm flag variant (CALC-0012 config A) with the same compensation.

Run:  python cases/12_leaf_gap_sensitivity.py
Read: out/12_leaf_gap_sensitivity/REPORT.md
"""
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from indsim import biot, geometry as g, plot, sensor  # noqa: E402
from indsim.parallel import pmap  # noqa: E402

spec = importlib.util.spec_from_file_location("c01", HERE / "01_leaf_baseline.py")
c01 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c01)
spec4 = importlib.util.spec_from_file_location("c04", HERE / "04_yaw_stack_study.py")
c04 = importlib.util.module_from_spec(spec4)
spec4.loader.exec_module(c04)
spec10 = importlib.util.spec_from_file_location("c10", HERE / "10_leaf_with_tungsten.py")
c10 = importlib.util.module_from_spec(spec10)
spec10.loader.exec_module(c10)

OUT = HERE.parent / "out" / "12_leaf_gap_sensitivity"
GAPS = (0.75, 1.0, 1.5, 2.0)
DELTAS = (0.10, 0.25)
LEAF_SIZE = c10.LEAF_SIZES["leaf 12 x 30 mm"]
STEP = 0.25

COILS = {
    "as built, offsets trimmed": dict(lam=15.0, flag_len=5.0, tx_turns=4, comp=False, trim=True),
    "6 turns, cos ends compensated": dict(lam=15.0, flag_len=5.0, tx_turns=6, comp=True, trim=False),
    "lambda 18, 6 mm flag, 6 turns, compensated": dict(lam=18.0, flag_len=6.0, tx_turns=6, comp=True, trim=False),
}


def null_scale(tx, lam):
    """End half-lobe scale that nulls the cosine coil's direct coupling (linear in scale)."""
    m = []
    for k in (0.85, 0.90):
        _, rc = g.linear_rx_pair(lam, c01.LOBE_WIDTH, c01.SIN_LOBES, c01.RX_LAYERS, cos_end_scale=k)
        m.append(biot.mutual_inductance(tx.segments(), rc.segments()))
    return 0.85 - m[0] * (0.90 - 0.85) / (m[1] - m[0])


def build(v):
    tx_len = max(c01.TX_LEN, v["lam"] + 3.0) if v["lam"] > 15.0 else c01.TX_LEN
    tx = g.rect_tx(tx_len, c01.TX_WID, v["tx_turns"], c01.TX_PITCH, c01.TX_LAYERS, corner_r_mm=c01.TX_CORNER)
    k = null_scale(tx, v["lam"]) if v["comp"] else 1.0
    rs, rc = g.linear_rx_pair(v["lam"], c01.LOBE_WIDTH, c01.SIN_LOBES, c01.RX_LAYERS, cos_end_scale=k)
    return tx, rs, rc, k


def xs_for(lam):
    half = lam / 2
    return np.arange(-half, half + STEP / 2, STEP)


def read(res, trim):
    if not trim:
        return res
    ang = np.unwrap(np.arctan2(res["phi_sin"] - res["direct_sin"], res["phi_cos"] - res["direct_cos"]))
    return dict(res, angle=ang)


def condition(args):
    name, v, gap = args
    t0 = time.time()
    tx, rs, rc, k = build(v)
    xs = xs_for(v["lam"])

    def target(dz=0.0):
        flag = g.rect_sheet(v["flag_len"], c01.TARGET_W, c01.CELL, gap + dz)
        leaf = g.rect_sheet(LEAF_SIZE[0], LEAF_SIZE[1], c10.LEAF_CELL, gap + c10.FLAG_T + c10.CLEAR + dz)
        return flag.union(leaf)

    def sweep(tg):
        return read(sensor.run_sweep(tx, rs, rc, lambda x: tg.translated_mm((x, 0, 0)), xs), v["trim"])

    nom = sweep(target())
    m = c10.stroke_metrics(nom, xs)
    out = [name, gap, k, nom["amplitude"].mean() * 1e9, m["swept_deg"], m["raw_um"]]
    for d in DELTAS:
        out.append(c10.dense_um(m, sweep(target(d)), xs))
    # harmonic content of the raw error against electrical angle over the stroke (for the mechanism)
    hm = sensor.harmonics(nom["angle"] - nom["angle"][0], (nom["angle"] - np.polyval(np.polyfit(xs, nom["angle"], 1), xs)) / m["slope"] * 1e3, n_max=4)
    out += [hm[2], hm[3], time.time() - t0]
    return tuple(out)


HEADER = ("coil", "gap_mm", "cos_end_scale", "signal_nWb_per_A", "swept_deg", "raw_um", "dense_gap+0.10_um", "dense_gap+0.25_um", "h2_um", "h3_um", "seconds")


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    conds = [(n, v, gp) for n, v in COILS.items() for gp in GAPS]
    rows = pmap(condition, conds)
    for r in rows:
        print(f"{r[0]:44s} gap {r[1]:.2f}: k {r[2]:.3f} signal {r[3]:.1f} swept {r[4]:.0f} raw {r[5]:.0f} | +0.10 mm {r[6]:.0f} um, +0.25 mm {r[7]:.0f} um | h2 {r[8]:.0f} h3 {r[9]:.0f} ({r[10]:.0f} s)")
    c04.write_rows_text(OUT / "gap_sensitivity.csv", HEADER, rows)
    fig, ax = plot.figure()
    for n in COILS:
        sel = [r for r in rows if r[0] == n]
        ax.plot([r[1] for r in sel], [r[6] for r in sel], marker="o", label=n.title())
    plot.finish(fig, ax, "Dense LUT Residual For 0.10 mm Of Gap Change Vs Nominal Gap", "Nominal Airgap (mm)", "Residual (um)",
                OUT / "residual_vs_gap.png", legend=True)
    fig, ax = plot.figure()
    for n in COILS:
        sel = [r for r in rows if r[0] == n]
        ax.plot([r[1] for r in sel], [r[3] for r in sel], marker="o", label=n.title())
    plot.finish(fig, ax, "Signal Vs Nominal Gap", "Nominal Airgap (mm)", "Flux Amplitude (nWb/A)", OUT / "signal_vs_gap.png", legend=True)
    lines = ["# Case 12 -- leaf coil airgap sensitivity", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')}. Flag {c01.TARGET_W} mm wide x {c10.FLAG_T} mm, tungsten leaf {LEAF_SIZE[1]} x {LEAF_SIZE[0]} mm "
             f"{c10.CLEAR} mm behind it, moving as a rigid pair. Residuals are what a dense LUT calibrated at the nominal gap leaves when the gap grows by the stated amount.", "",
             c04.md_table(HEADER, rows), "", "![[residual_vs_gap.png]] ![[signal_vs_gap.png]]", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))
    print(f"done in {(time.time()-t0)/60:.1f} min -> {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
