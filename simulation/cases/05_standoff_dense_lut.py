"""Case 05 -- standoff ladder read through a dense firmware LUT.

Case 04 scored accuracy after a 10-segment linearizer, the LX34311's on-chip limit. The
MCU can hold a 100-1000 point table instead, so the static shape of the error curve is
not a cost at all; what the back-plane can still cost is (a) signal, (b) the tank, and
(c) how much the error curve *changes* when the plane, the airgap or the centring move
after calibration. This case measures (c) directly: the difference between the raw
error curve at the perturbed condition and at the nominal one, mean removed.

Grid: gap 1.0 mm; standoff none, 0.5, 1.0, 1.5, 2.0, 3.0 mm; targets: two 60 deg sectors
(case 04 default) and the pocketed aluminium face (two 60 deg pockets) that won case 04's
target section. Perturbations: plane 0.25 mm closer, airgap 0.25 mm larger, target
eccentric by 0.2 mm. All sweep curves are written to CSV.

Run:  python cases/05_standoff_dense_lut.py [--smoke] [--workers N]
Read: out/05_standoff_dense_lut/REPORT.md
"""
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from indsim import geometry as g, plot, sensor  # noqa: E402
from indsim.parallel import pmap  # noqa: E402

spec = importlib.util.spec_from_file_location("c04", HERE / "04_yaw_stack_study.py")
c04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c04)

OUT = HERE.parent / "out" / "05_standoff_dense_lut"
SMOKE = "--smoke" in sys.argv
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else None
GAP = 1.0
STANDOFFS = (None, 0.5, 1.0, 1.5, 2.0, 3.0) if not SMOKE else (None, 1.0)
STEP = 5.0 if not SMOKE else 30.0
DELTA, ECC = 0.25, 0.2
LOG = OUT / "progress.log"


def log(msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def targets():
    cell = c04.cell_for_gap(GAP, c04.sector_area(60.0, 2, c04.R_IN - 2, c04.R_OUT + 2))
    yield "2 sectors 60 deg", g.sector_sheet(c04.R_IN - 2, c04.R_OUT + 2, 60.0, 2, cell, GAP)
    cell = c04.cell_for_gap(GAP, np.pi * ((c04.R_OUT + 2) ** 2 - (c04.R_IN - 2) ** 2) * 2 / 3)
    yield "face with 2 pockets 60 deg", g.disc_sheet(c04.R_OUT + 2, cell, GAP, r_hole_mm=c04.R_IN - 2, n_slots=2, slot_deg=60.0)


def raw_error_curve(res, thetas, fit):
    """Raw error (mech deg) of a sweep against the *nominal* best-fit line, unwrap-aligned."""
    ideal = fit["slope"] * thetas + fit["intercept"]
    ang = res["angle"] - 2 * np.pi * np.round((res["angle"][0] - ideal[0]) / (2 * np.pi))
    return (ang - ideal) / fit["slope"]


def dense_delta(err_nom, th_nom, err_pert, th_pert):
    """What a dense LUT calibrated at nominal leaves at the perturbed condition."""
    d = err_pert - np.interp(th_pert, th_nom, err_nom)
    d -= d.mean()  # a pure offset re-zeroes at homing
    return float(np.abs(d).max())


def _condition(args):
    tname, h = args
    tx, rs, rc = c04.build_coils()
    tg = dict(targets())[tname]
    t0 = time.time()
    plane = None if h is None else g.ImagePlane(c04.BOARD_BACK - h)
    res, th = c04.ring_sweep(tx, rs, rc, tg, plane=plane, step=STEP)
    a = c04.analyse(res, th)
    err_nom = a["err_raw"]
    tag = f"{tname} | standoff {h}"
    curves = {f"{tag} | nominal": (th, err_nom)}
    out = {"amp": a["amp"] * 1e9, "raw": a["raw_max"], "cal10": a["cal_max"]}
    perts = {}
    if h is not None:
        r_p, t_p = c04.ring_sweep(tx, rs, rc, tg, plane=g.ImagePlane(c04.BOARD_BACK - h + DELTA), step=STEP)
        perts["plane_closer"] = raw_error_curve(r_p, t_p, a), t_p
    r_g, t_g = c04.ring_sweep(tx, rs, rc, tg.translated_mm((0, 0, DELTA)), plane=plane, step=STEP)
    perts["gap_larger"] = raw_error_curve(r_g, t_g, a), t_g
    r_e, t_e = c04.ring_sweep(tx, rs, rc, tg, plane=plane, step=STEP, ecc=ECC)
    perts["eccentric"] = raw_error_curve(r_e, t_e, a), t_e
    for k, (e, t) in perts.items():
        out[k] = dense_delta(err_nom, th, e, t)
        curves[f"{tag} | {k}"] = (t, e)
    tank = sensor.tank(tx, c04.C_TANK, plane=plane, cu_thickness=c04.CU_T)
    row = (tname, -1 if h is None else h, tank["L"] * 1e6, tank["Q"], out["amp"], out["raw"], out["cal10"],
           out.get("plane_closer", 0.0), out["gap_larger"], out["eccentric"])
    line = (f"{tag}: amp {out['amp']:.1f} nWb/A raw {out['raw']:.3f} cal10 {out['cal10']:.3f} | dense LUT: plane-0.25 "
            f"{out.get('plane_closer', 0):.4f} gap+0.25 {out['gap_larger']:.4f} ecc0.2 {out['eccentric']:.4f} deg ({time.time()-t0:.0f} s)")
    return row, curves, line


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    log(f"start; workers {WORKERS or 'auto'}")
    conditions = [(tname, h) for tname, _ in targets() for h in STANDOFFS]
    results = pmap(_condition, conditions, WORKERS)
    rows, curves = [], {}
    for row, cv, line in results:
        rows.append(row)
        curves.update(cv)
        log(line)
    write_report(rows)
    # curves CSV (long format)
    with open(OUT / "curves.csv", "w") as f:
        f.write("case,theta_deg,raw_error_mech_deg\n")
        for k, (t, e) in curves.items():
            for ti, ei in zip(t, e):
                f.write(f"{k.replace(',', ';')},{ti:.3f},{ei:.6f}\n")
    # figures: dense-LUT residual vs standoff per target
    for name, idx, title in (("plane", 7, "Dense LUT Residual When Plane Comes 0.25 mm Closer"),
                             ("gap", 8, "Dense LUT Residual When Airgap Grows 0.25 mm"),
                             ("ecc", 9, "Dense LUT Residual At 0.2 mm Eccentricity")):
        fig, ax = plot.figure()
        for tname, _ in targets():
            sel = [r for r in rows if r[0] == tname and r[1] >= 0]
            ax.plot([r[1] for r in sel], [r[idx] for r in sel], marker="o", label=tname.title())
        plot.finish(fig, ax, title, "Standoff Behind Board (mm)", "Residual (mech deg)", OUT / f"dense_{name}_vs_standoff.png", legend=True)
    fig, ax = plot.figure()
    for tname, _ in targets():
        sel = [r for r in rows if r[0] == tname and r[1] >= 0]
        ax.plot([r[1] for r in sel], [r[4] for r in sel], marker="o", label=tname.title())
    plot.finish(fig, ax, "Signal Vs Standoff", "Standoff Behind Board (mm)", "Flux Amplitude (nWb/A)", OUT / "amp_vs_standoff.png", legend=True)
    log(f"done in {(time.time()-t_start)/60:.1f} min")


HEADER = ("target", "standoff_mm", "L_uH", "Q", "amp_nWb_per_A", "raw_deg", "cal10seg_deg", "dense_plane_minus025_deg",
          "dense_gap_plus025_deg", "dense_ecc02_deg")


def write_report(rows):
    lines = ["# Case 05 -- standoff ladder through a dense firmware LUT", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')}. Gap {GAP} mm, ring as case 04 (3 turns per edge, 6 mil). "
             "standoff_mm = -1 is no plane.", "",
             "raw_deg and cal10seg_deg are the case 04 metrics (static shape; a dense LUT removes them entirely).",
             "The dense_* columns are what remains after a dense LUT calibrated at nominal when the plane comes 0.25 mm",
             "closer, the airgap grows 0.25 mm, or the target is 0.2 mm eccentric (mean offset removed).", "",
             c04.md_table(HEADER, rows), "",
             "![[dense_plane_vs_standoff.png]] ![[dense_gap_vs_standoff.png]] ![[dense_ecc_vs_standoff.png]] ![[amp_vs_standoff.png]]", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
