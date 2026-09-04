"""Case 10 -- the leaf coil with the tungsten leaf behind its flag.

The leaf encoder's 5 x 10 x 0.8 mm aluminium flag rides on the sliding carrier 1.7 mm
above the tungsten leaf (t_leaf = 2 mm, COL-PARAM; spacing from CAD, 2026-09-04). The flag is smaller than the coil's transmit
loop, so the field that leaks round it reaches the leaf, which is a good conductor at
these frequencies (skin depth ~50 um) and moves with the flag. This case adds the leaf
as a second sheet at the flag's far face plus the clearance and asks: how much does it
change the signal, the swept angle, the linearity and the tank, and how sensitive is
the reading to the flag-to-leaf clearance (an assembly tolerance)?

Leaf in-plane size is not in the vault; two sizes bracket it. The plate is modelled by
its near face only (the far face is 2 mm further and the field there is small).

Run:  python cases/10_leaf_with_tungsten.py
Read: out/10_leaf_with_tungsten/REPORT.md
"""
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from indsim import biot, geometry as g, plot, sensor, sheet  # noqa: E402

spec = importlib.util.spec_from_file_location("c01", HERE / "01_leaf_baseline.py")
c01 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c01)
spec4 = importlib.util.spec_from_file_location("c04", HERE / "04_yaw_stack_study.py")
c04 = importlib.util.module_from_spec(spec4)
spec4.loader.exec_module(c04)

OUT = HERE.parent / "out" / "10_leaf_with_tungsten"
FLAG_T = 0.8                 # mm, flag thickness (CAD 2026-09-04: 0.8 mm aluminium)
CLEAR = 1.7                  # mm, flag far face to tungsten near face (CAD 2026-09-04; both on the sliding carrier)
LEAF_Z = c01.GAP + FLAG_T + CLEAR
LEAF_SIZES = {"leaf 12 x 30 mm": (30.0, 12.0), "leaf 20 x 40 mm": (40.0, 20.0)}   # (along travel, across travel)
LEAF_CELL = 0.5
CLEARANCES = (1.2, 1.7, 2.2)
STEP = 0.25
XS = np.arange(-c01.SWEEP_HALF, c01.SWEEP_HALF + STEP / 2, STEP)


def coils():
    rx_sin, rx_cos = g.linear_rx_pair(c01.LAMBDA, c01.LOBE_WIDTH, c01.SIN_LOBES, c01.RX_LAYERS, trace_mm=c01.TRACE)
    tx = g.rect_tx(c01.TX_LEN, c01.TX_WID, c01.TX_TURNS, c01.TX_PITCH, c01.TX_LAYERS, corner_r_mm=c01.TX_CORNER, trace_mm=c01.TRACE)
    return tx, rx_sin, rx_cos


def flag():
    return g.rect_sheet(c01.TARGET_L, c01.TARGET_W, c01.CELL, c01.GAP)


def leaf(size, clearance=CLEAR):
    along, across = size
    return g.rect_sheet(along, across, LEAF_CELL, c01.GAP + FLAG_T + clearance)


def stroke_metrics(res, xs):
    """Case 01's centred-stroke numbers: swept angle, um/count, raw linearity in um."""
    m = (xs >= -c01.STROKE / 2 - 1e-9) & (xs <= c01.STROKE / 2 + 1e-9)
    x, a = xs[m], res["angle"][m]
    lin = sensor.linearity(x, a)
    err_um = lin["residual"] / lin["slope"] * 1e3
    swept = abs(a[-1] - a[0])
    return dict(swept_deg=np.degrees(swept), um_per_count=c01.STROKE * 1e3 / (swept / (2 * np.pi) * 4096),
                raw_um=float(np.abs(err_um).max()), err_um=err_um, x=x, slope=lin["slope"], intercept=lin["intercept"],
                mono=bool(np.all(np.diff(a) > 0) or np.all(np.diff(a) < 0)))


def dense_um(ref, res, xs):
    """Change of the position-error curve over the stroke, mean removed (dense LUT view), um."""
    m = (xs >= -c01.STROKE / 2 - 1e-9) & (xs <= c01.STROKE / 2 + 1e-9)
    a = res["angle"][m]
    ideal = ref["slope"] * ref["x"] + ref["intercept"]
    a = a - 2 * np.pi * np.round((a[0] - ideal[0]) / (2 * np.pi))
    err = (a - ideal) / ref["slope"] * 1e3
    d = err - ref["err_um"]
    d -= d.mean()
    return float(np.abs(d).max())


def run(tx, rs, rc, target):
    res = sensor.run_sweep(tx, rs, rc, lambda x: target.translated_mm((x, 0.0, 0.0)), XS)
    return res


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    tx, rs, rc = coils()
    cases = {"flag only (case 01)": flag()}
    for name, size in LEAF_SIZES.items():
        cases[f"flag + {name}"] = flag().union(leaf(size))
    cases["leaf 12 x 30 mm alone, no flag"] = leaf(LEAF_SIZES["leaf 12 x 30 mm"])
    results, rows = {}, []
    for name, tg in cases.items():
        t1 = time.time()
        res = run(tx, rs, rc, tg)
        met = stroke_metrics(res, XS)
        ps = sheet.SheetSolver(tg)
        dL = sheet.rx_flux(tg, ps.respond(tx.segments()), tx.segments())
        results[name] = (res, met)
        rows.append((name, tg.n, res["amplitude"].max() * 1e9, res["amplitude"].min() * 1e9, met["swept_deg"], met["um_per_count"],
                     met["raw_um"], int(met["mono"]), dL * 1e6))
        print(f"{name}: {tg.n} cells, amp {res['amplitude'].max()*1e9:.1f}/{res['amplitude'].min()*1e9:.1f} nWb/A, swept {met['swept_deg']:.1f} deg, "
              f"{met['um_per_count']:.2f} um/count, raw {met['raw_um']:.0f} um, mono {met['mono']}, dL {dL*1e6:.3f} uH ({time.time()-t1:.0f} s)")

    # clearance sensitivity: calibrate with the leaf at 1.0 mm, read with it at 0.5 and 1.5 mm
    ref_name = "flag + leaf 12 x 30 mm"  # calibrated at the nominal clearance
    ref = results[ref_name][1]
    clear_rows = []
    for cl in CLEARANCES:
        tg = flag().union(leaf(LEAF_SIZES["leaf 12 x 30 mm"], cl))
        res = run(tx, rs, rc, tg)
        met = stroke_metrics(res, XS)
        clear_rows.append((cl, res["amplitude"].max() * 1e9, met["swept_deg"], met["raw_um"], dense_um(ref, res, XS)))
        print(f"clearance {cl} mm: swept {met['swept_deg']:.1f} deg, raw {met['raw_um']:.0f} um, dense-LUT change vs {CLEAR} mm {clear_rows[-1][4]:.1f} um")

    # what the chip's SSIN/SCOS offset registers could take back: trim the leaf's mean channel offsets
    r_flag, r_both, r_leaf = results["flag only (case 01)"][0], results[ref_name][0], results["leaf 12 x 30 mm alone, no flag"][0]
    off_c = float(np.mean(r_leaf["phi_cos"] - r_flag["direct_cos"]))
    off_s = float(np.mean(r_leaf["phi_sin"]))
    trimmed = dict(r_both, angle=np.unwrap(np.arctan2(r_both["phi_sin"] - off_s, r_both["phi_cos"] - off_c)))
    met_tr = stroke_metrics(trimmed, XS)
    offset_lines = [f"The leaf's own contribution is a near-constant cosine offset of {off_c*1e9:+.2f} nWb/A (spread {np.ptp(r_leaf['phi_cos'])*1e9:.2f}) "
                    f"and a position-dependent sine term of {np.ptp(r_leaf['phi_sin'])*1e9:.2f} nWb/A spread, against flag swings of {np.ptp(r_flag['phi_cos'])*1e9:.1f} / {np.ptp(r_flag['phi_sin'])*1e9:.1f} nWb/A.",
                    f"Trimming the constant offsets (LX34311 SSIN/SCOS registers) restores the swept angle to {met_tr['swept_deg']:.1f} deg, {met_tr['um_per_count']:.2f} um/count; the rest is the position-dependent part and stays for the linearizer."]
    print("\n".join(offset_lines))

    # tank
    free = sensor.tank(tx, c01.C_TANK)
    tank_rows = [("coil alone", free["L"] * 1e6, free["f0"] / 1e6)]
    for name in ("flag only (case 01)", "flag + leaf 12 x 30 mm", "flag + leaf 20 x 40 mm"):
        L = free["L"] + rows[[r[0] for r in rows].index(name)][8] * 1e-6
        tank_rows.append((name, L * 1e6, 1 / (2 * np.pi * np.sqrt(L * c01.C_TANK)) / 1e6))

    # figures
    plot.line_plot(XS, {n: results[n][0]["phi_sin"] * 1e9 for n in list(cases)[:3]}, "Sine Coil Flux Vs Position",
                   "Flag Position (mm)", "Flux Per Ampere Of TX (nWb/A)", OUT / "flux_sin.png")
    plot.line_plot(XS, {n: results[n][0]["phi_cos"] * 1e9 for n in list(cases)[:3]}, "Cosine Coil Flux Vs Position",
                   "Flag Position (mm)", "Flux Per Ampere Of TX (nWb/A)", OUT / "flux_cos.png")
    plot.line_plot(ref["x"], {n: results[n][1]["err_um"] for n in list(cases)[:3]}, "Raw Position Error Over The Stroke",
                   "Flag Position (mm)", "Position Error (um)", OUT / "linearity.png")
    plot.line_plot(XS, {n: np.degrees(results[n][0]["angle"]) for n in list(cases)[:3]}, "Electrical Angle Vs Position",
                   "Flag Position (mm)", "Electrical Angle (deg)", OUT / "angle.png")

    header = ("case", "n_cells", "amp_max_nWb_per_A", "amp_min_nWb_per_A", "swept_deg_over_stroke", "um_per_count", "raw_linearity_um", "monotonic", "dL_uH")
    lines = ["# Case 10 -- leaf coil with the tungsten leaf behind the flag", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')}. Leaf coil as case 01; flag {c01.TARGET_L} x {c01.TARGET_W} x {FLAG_T} mm at {c01.GAP} mm; "
             f"tungsten leaf near face {CLEAR} mm behind the flag ({LEAF_Z} mm from the coil face), moving with the flag. "
             "Bench reference (COL-TEST-0005): ~202 deg swept, ~4.6 um/count.", "",
             c04.md_table(header, rows), "",
             "## Flag-to-leaf clearance (assembly tolerance)", "",
             f"Calibrated with the leaf {CLEAR} mm behind the flag; the last column is what a dense LUT leaves if the clearance is actually the value in the first column.", "",
             c04.md_table(("clearance_mm", "amp_max_nWb_per_A", "swept_deg", "raw_um", "dense_LUT_change_um"), clear_rows), "",
             "## Tank at 2 x 1200 pF", "",
             c04.md_table(("condition", "L_uH", "f0_MHz"), tank_rows), "",
             "## Offset decomposition", "", *offset_lines, "",
             "![[flux_sin.png]] ![[flux_cos.png]] ![[angle.png]] ![[linearity.png]]", "",
             "Limits: perfect conductors; the leaf is its near face only; leaf in-plane size assumed (two sizes bracket it); no board behind the coil.", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))
    print(f"done in {time.time()-t0:.0f} s -> {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
