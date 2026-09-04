"""Case 04 -- yaw ring stack-height and target study.

Question: how thin can the yaw sensor stack be? Two levers: bring the target closer to
the coils (smaller airgap) and bring the main board closer behind the ring board
(smaller standoff). And is the two-sector target the best target for those conditions?

Sections (each writes its own CSV and figures as soon as it finishes, and the report is
regenerated after every section, so a partial run is still readable):

  0. mesh convergence  -- how far the cell size can be trusted at small gaps
  1. tank options      -- L, Q vs plane height for TX turn count and trace width
  2. gap x standoff    -- signal, raw/calibrated error, and robustness to 0.25 mm of
                          plane height and airgap, for every (gap, standoff) pair
  3. target shapes     -- sector angle (fine), one vs two sectors, radial overhang,
                          inverse target (metal face with pockets), slotted disc
  4. misalignment      -- once-per-turn error vs eccentricity for one vs two sectors and
                          for radial overhang

Pass criteria used for the verdict columns (PROVISIONAL, stated so they can be argued
with in the vault): L >= 3 uH and Q >= 10 (LX34311), calibrated error <= 0.25 mech deg,
signal >= 50 % of the free-space amplitude, and <= 0.10 mech deg of extra error when the
plane comes 0.25 mm closer or the airgap grows 0.25 mm after calibration.

Speed: K matrices are built by Toeplitz lookup, coil fields at the target come from
polar interpolation tables cached per (gap, plane), and independent conditions run in a
process pool (`--workers N`, default half the CPUs).

Run:   python cases/04_yaw_stack_study.py [--workers N]
       python cases/04_yaw_stack_study.py --smoke    (coarse grids, to check the plumbing)
Watch: out/04_yaw_stack_study/progress.log ; read out/04_yaw_stack_study/REPORT.md
"""
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indsim import geometry as g, plot, sensor, sheet, tables  # noqa: E402
from indsim.parallel import pmap  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out" / "04_yaw_stack_study"
SMOKE = "--smoke" in sys.argv
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else None

# ------------------------------------------------------------------ fixed ring (mm)
R_IN, R_OUT = 17.0, 29.0
N = 2                                  # electrical periods: 180 deg absolute range
TX_TURNS, TX_PITCH = 3, 0.3048
RX_AMP = 4.8
TRACE = 0.1524
TX_NTHETA, RX_NTHETA = 180, 360
LAYERS = (0.0, -1.0)                   # two-layer 1.0 mm ring board, z = 0 faces the target
BOARD_BACK = -1.0
C_TANK = 600e-12
CU_T = 35e-6
TABLE_R = (R_IN - 5.0, R_OUT + 5.0)    # radial range shared by every table (overhang 3 + ecc + margin)

# ------------------------------------------------------------------ study grids (mm, deg)
GAPS = (0.75, 1.0, 1.5, 2.0) if not SMOKE else (1.0,)
STANDOFFS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0) if not SMOKE else (1.0, 3.0)
STEP = 5.0 if not SMOKE else 30.0      # target angle step over one electrical period
ROB_STEP = 5.0 if not SMOKE else 30.0  # step for the robustness re-sweeps
MAX_CELLS = 9000                       # Toeplitz build is cheap; LU of 9000^2 is ~5 s
SECTOR_DEG_DEFAULT, K_DEFAULT = 60.0, 2
OVERHANG_DEFAULT = 2.0                 # target radial overhang beyond the coil band, each side
DELTA = 0.25                           # move used for the robustness columns
SECTOR_FINE = tuple(np.arange(30.0, 91.0, 5.0)) if not SMOKE else (60.0,)
OVERHANGS = (0.0, 1.0, 2.0, 3.0) if not SMOKE else (0.0, 2.0)
ECCS = (0.0, 0.1, 0.2, 0.3) if not SMOKE else (0.0, 0.3)
CONVERGENCE_CELLS = (0.6, 0.45, 0.35, 0.30, 0.25) if not SMOKE else (0.6, 0.45)
CRIT = {"L": 3e-6, "Q": 10.0, "cal_deg": 0.25, "amp_frac": 0.5, "robust_deg": 0.10}

LOG = OUT / "progress.log"
_TABLES = {}


def log(msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def cell_for_gap(gap_mm, area_mm2=None):
    """Cell side: a third of the airgap, floored at 0.25 mm, coarsened if the target area
    would need more than MAX_CELLS cells."""
    c = max(gap_mm / 3, 0.25)
    if area_mm2 is not None:
        c = max(c, float(np.sqrt(area_mm2 / MAX_CELLS)))
    return float(c)


def sector_area(sector_deg, k, r1, r2):
    return k * sector_deg / 360.0 * np.pi * (r2**2 - r1**2)


def build_coils(tx_turns=TX_TURNS, trace=TRACE):
    rx_sin, rx_cos = g.ring_rx_pair(R_IN, R_OUT, N, LAYERS, amp_mm=RX_AMP, n_theta=RX_NTHETA, trace_mm=trace)
    tx = g.ring_tx(R_IN, R_OUT, tx_turns, TX_PITCH, LAYERS, n_theta=TX_NTHETA, trace_mm=trace)
    return tx, rx_sin, rx_cos


def sector_target(gap, sector_deg=SECTOR_DEG_DEFAULT, k=K_DEFAULT, overhang=OVERHANG_DEFAULT, cell=None):
    r1, r2 = R_IN - overhang, R_OUT + overhang
    cell = cell or cell_for_gap(gap, sector_area(sector_deg, k, r1, r2))
    return g.sector_sheet(r1, r2, sector_deg, k, cell, gap)


def get_tables(tx, rx_sin, rx_cos, target, plane):
    """Field tables per (gap, plane height, coil set), cached in this process."""
    key = (round(target.z, 9), None if plane is None else round(plane.z, 9), id(tx))
    if key not in _TABLES:
        _TABLES[key] = tables.ring_tables(tx, rx_sin, rx_cos, target, N, plane=plane, r_min_mm=TABLE_R[0], r_max_mm=TABLE_R[1])
    return _TABLES[key]


def analyse(res, thetas, periods=1):
    """Mechanical-degree linearity: raw, after the per-period 10-segment linearizer, and
    the linearizer map itself so it can be re-applied to a perturbed sweep."""
    lin = sensor.linearity(thetas, res["angle"])
    ideal = lin["slope"] * thetas + lin["intercept"]
    err_raw = lin["residual"] / lin["slope"]
    knots_meas = np.linspace(res["angle"].min(), res["angle"].max(), 10 * periods + 1)
    basis = np.column_stack([np.interp(res["angle"], knots_meas, np.eye(len(knots_meas))[i]) for i in range(len(knots_meas))])
    coef, *_ = np.linalg.lstsq(basis, ideal, rcond=None)
    cal = basis @ coef
    err_cal = (cal - ideal) / lin["slope"]
    return {
        "slope": lin["slope"], "intercept": lin["intercept"], "err_raw": err_raw, "err_cal": err_cal,
        "raw_max": float(np.abs(err_raw).max()), "cal_max": float(np.abs(err_cal).max()),
        "knots": knots_meas, "coef": coef, "amp": float(res["amplitude"].mean()),
    }


def apply_calibration(cal_map, res, thetas):
    """Error (mech deg) of a perturbed sweep read through a 10-segment linearizer fitted
    at nominal (the on-chip view)."""
    ideal = cal_map["slope"] * thetas + cal_map["intercept"]
    ang = res["angle"] - 2 * np.pi * np.round((res["angle"][0] - ideal[0]) / (2 * np.pi))
    corrected = np.interp(ang, cal_map["knots"], cal_map["coef"])
    err = (corrected - ideal) / cal_map["slope"]
    err -= err.mean()
    return float(np.abs(err).max())


def dense_delta(cal_map, res, thetas, err_nom, th_nom):
    """What a dense firmware LUT calibrated at nominal leaves at a perturbed condition:
    the change of the raw error curve, mean removed (the firmware view)."""
    ideal = cal_map["slope"] * thetas + cal_map["intercept"]
    ang = res["angle"] - 2 * np.pi * np.round((res["angle"][0] - ideal[0]) / (2 * np.pi))
    err = (ang - ideal) / cal_map["slope"]
    d = err - np.interp(thetas, th_nom, err_nom)
    d -= d.mean()
    return float(np.abs(d).max())


def ring_sweep(tx, rx_sin, rx_cos, target, plane=None, step=STEP, periods=1, ecc=0.0, use_tables=True):
    thetas = np.arange(0.0, periods * 360.0 / N + step / 2, step)
    place = lambda th: target.rotated_deg(th).translated_mm((ecc, 0.0, 0.0))  # noqa: E731
    tabs = get_tables(tx, rx_sin, rx_cos, target, plane) if use_tables else None
    res = sensor.run_sweep(tx, rx_sin, rx_cos, place, thetas, plane=plane, tables=tabs)
    return res, thetas


def tank_with_plane(tx, plane):
    return sensor.tank(tx, C_TANK, plane=plane, cu_thickness=CU_T)


def write_rows(path, header, rows):
    plot.write_csv(path, {h: np.array([r[i] for r in rows], dtype=float) for i, h in enumerate(header)})


def write_rows_text(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(f"{v:.6g}" if isinstance(v, (int, float, np.floating)) else str(v).replace(",", ";") for v in r) + "\n")


# ============================================================ section 0
def _s0_point(args):
    gap, cell = args
    tx, rs, rc = build_coils()
    tg = sector_target(gap, cell=cell)
    t0 = time.time()
    res, th = ring_sweep(tx, rs, rc, tg, step=15.0 if not SMOKE else 30.0)
    a = analyse(res, th)
    return (gap, cell, tg.n, a["amp"] * 1e9, a["raw_max"], a["cal_max"], time.time() - t0)


def section_convergence(report):
    log("0. mesh convergence")
    grid = [(gap, cell) for gap in ((1.0, 0.75) if not SMOKE else (1.0,)) for cell in CONVERGENCE_CELLS]
    out = pmap(_s0_point, grid, WORKERS)
    rows = []
    ref = {}
    for gap, cell, n, amp, raw, cal, secs in out:
        ref.setdefault(gap, amp)
        rows.append((gap, cell, n, amp, amp / ref[gap], raw, cal, secs))
        log(f"   gap {gap} cell {cell}: {n} cells, amp {amp:.2f} nWb/A ({amp/ref[gap]:.4f} of coarsest), raw {raw:.3f} cal {cal:.4f} deg, {secs:.0f} s")
    header = ("gap_mm", "cell_mm", "n_cells", "amp_nWb_per_A", "amp_rel", "raw_deg", "cal_deg", "seconds")
    write_rows(OUT / "s0_convergence.csv", header, rows)
    report["s0"] = (header, rows)


# ============================================================ section 1
def _s1_coil(args):
    turns, trace = args
    tx, _, _ = build_coils(turns, trace)
    rows = []
    free = sensor.tank(tx, C_TANK, cu_thickness=CU_T)
    for h in (None,) + STANDOFFS:
        t = free if h is None else tank_with_plane(tx, g.ImagePlane(BOARD_BACK - h))
        c_for_3mhz = 1 / ((2 * np.pi * 3e6) ** 2 * t["L"])
        rows.append((turns, trace / 0.0254, -1 if h is None else h, t["L"] * 1e6, t["Q"], t["f0"] / 1e6, t["R"], c_for_3mhz * 1e12,
                     int(t["L"] >= CRIT["L"] and t["Q"] >= CRIT["Q"])))
    return rows


def section_tank(report):
    log("1. tank options vs plane height")
    combos = [(t, w) for t in ((3, 4, 5) if not SMOKE else (3,)) for w in ((0.1524, 0.2032, 0.254) if not SMOKE else (0.1524,))]
    rows = [r for block in pmap(_s1_coil, combos, WORKERS) for r in block]
    for turns, trace in combos:
        sel = [r for r in rows if r[0] == turns and abs(r[1] - trace / 0.0254) < 0.5]
        log(f"   {turns} turns/edge, {trace/0.0254:.0f} mil: free L {sel[0][3]:.2f} uH Q {sel[0][4]:.0f}, at {STANDOFFS[0]} mm standoff L {sel[1][3]:.2f} uH Q {sel[1][4]:.0f}")
    header = ("tx_turns_per_edge", "trace_mil", "standoff_mm", "L_uH", "Q", "f0_MHz_at_600pF", "R_ohm", "C_pF_for_3MHz", "passes_L_Q")
    write_rows(OUT / "s1_tank.csv", header, rows)
    report["s1"] = (header, rows)
    fig, ax = plot.figure()
    for turns in (3, 4, 5):
        sel = [r for r in rows if r[0] == turns and abs(r[1] - 6) < 0.5 and r[2] >= 0]
        if sel:
            ax.plot([r[2] for r in sel], [r[3] for r in sel], marker="o", label=f"{turns} Turns Per Edge")
    ax.axhline(3.0, color="0.5", ls="--", label="LX34311 Minimum")
    plot.finish(fig, ax, "Transmit Inductance Vs Standoff, 6 mil Trace", "Standoff Behind Board (mm)", "Inductance (uH)",
                OUT / "s1_L_vs_standoff.png", legend=True)
    fig, ax = plot.figure()
    for trace in (0.1524, 0.2032, 0.254):
        sel = [r for r in rows if r[0] == 3 and abs(r[1] - trace / 0.0254) < 0.5 and r[2] >= 0]
        if sel:
            ax.plot([r[2] for r in sel], [r[4] for r in sel], marker="o", label=f"{trace/0.0254:.0f} mil Trace")
    ax.axhline(10.0, color="0.5", ls="--", label="LX34311 Minimum")
    plot.finish(fig, ax, "Transmit Q Vs Standoff, 3 Turns Per Edge", "Standoff Behind Board (mm)", "Q",
                OUT / "s1_Q_vs_standoff.png", legend=True)


# ============================================================ section 2
S2_HEADER = ("gap_mm", "standoff_mm", "L_uH", "Q", "f0_MHz", "amp_nWb_per_A", "amp_rel_free", "raw_deg", "cal_deg",
             "plane_minus025_deg", "gap_plus025_deg", "dense_plane_minus025_deg", "dense_gap_plus025_deg", "passes")


def _s2_cell(args):
    gap, h = args
    tx, rs, rc = build_coils()
    tg = sector_target(gap)
    t0 = time.time()
    plane = None if h is None else g.ImagePlane(BOARD_BACK - h)
    res, th = ring_sweep(tx, rs, rc, tg, plane=plane)
    a = analyse(res, th)
    tk = {"L": 0.0, "Q": 0.0, "f0": 0.0} if plane is None else tank_with_plane(tx, plane)
    # adverse directions: plane DELTA closer, target DELTA further
    rob_plane = dense_plane = 0.0
    if plane is not None:
        r_p, t_p = ring_sweep(tx, rs, rc, tg, plane=g.ImagePlane(BOARD_BACK - h + DELTA), step=ROB_STEP)
        rob_plane = apply_calibration(a, r_p, t_p)
        dense_plane = dense_delta(a, r_p, t_p, a["err_raw"], th)
    r_g, t_g = ring_sweep(tx, rs, rc, tg.translated_mm((0, 0, DELTA)), plane=plane, step=ROB_STEP)
    rob_gap = apply_calibration(a, r_g, t_g)
    dense_gap = dense_delta(a, r_g, t_g, a["err_raw"], th)
    return (gap, -1 if h is None else h, tk["L"] * 1e6, tk["Q"], tk["f0"] / 1e6, a["amp"] * 1e9, a["raw_max"], a["cal_max"],
            rob_plane, rob_gap, dense_plane, dense_gap, tg.n, time.time() - t0)


def section_gap_standoff(report):
    log("2. gap x standoff grid")
    grid = [(gap, h) for gap in GAPS for h in (None,) + STANDOFFS]
    out = pmap(_s2_cell, grid, WORKERS)
    free_amp = {r[0]: r[5] for r in out if r[1] == -1}
    rows = []
    for gap, h, L, Q, f0, amp, raw, cal, rob_plane, rob_gap, dense_plane, dense_gap, n, secs in out:
        rel = amp / free_amp[gap]
        if h == -1:
            passes = -1
        else:
            passes = int(L >= CRIT["L"] * 1e6 and Q >= CRIT["Q"] and cal <= CRIT["cal_deg"] and rel >= CRIT["amp_frac"]
                         and max(rob_plane, rob_gap) <= CRIT["robust_deg"])
        rows.append((gap, h, L, Q, f0, amp, rel, raw, cal, rob_plane, rob_gap, dense_plane, dense_gap, passes))
        log(f"   gap {gap} standoff {h}: L {L:.2f} Q {Q:.0f} amp {rel:.2f}x raw {raw:.3f} cal {cal:.4f} | 10-seg: plane {rob_plane:.4f} gap {rob_gap:.4f} "
            f"| dense: plane {dense_plane:.4f} gap {dense_gap:.4f} deg {'PASS' if passes == 1 else ''} ({n} cells, {secs:.0f} s)")
    report["s2"] = (S2_HEADER, rows)
    write_rows(OUT / "s2_gap_standoff.csv", S2_HEADER, rows)
    for key, idx, title, ylabel, fname in (
        ("amp", 6, "Signal Vs Standoff, Relative To No Plane", "Amplitude Ratio", "s2_amp_vs_standoff.png"),
        ("cal", 8, "Calibrated Error Vs Standoff, 10 Segments", "Peak Error After Linearizer (mech deg)", "s2_cal_vs_standoff.png"),
        ("rob", 9, "Extra Error When The Plane Comes 0.25 mm Closer, 10 Segments", "Peak Error (mech deg)", "s2_plane_robustness.png"),
        ("robg", 10, "Extra Error When The Airgap Grows 0.25 mm, 10 Segments", "Peak Error (mech deg)", "s2_gap_robustness.png"),
        ("dp", 11, "Dense LUT Residual When The Plane Comes 0.25 mm Closer", "Residual (mech deg)", "s2_dense_plane.png"),
        ("dg", 12, "Dense LUT Residual When The Airgap Grows 0.25 mm", "Residual (mech deg)", "s2_dense_gap.png"),
        ("L", 2, "Transmit Inductance Vs Standoff", "Inductance (uH)", "s2_L_vs_standoff.png"),
    ):
        fig, ax = plot.figure()
        for gap in GAPS:
            sel = [r for r in rows if r[0] == gap and r[1] >= 0]
            ax.plot([r[1] for r in sel], [r[idx] for r in sel], marker="o", label=f"Gap {gap} mm")
        if key == "L":
            ax.axhline(3.0, color="0.5", ls="--", label="LX34311 Minimum")
        if key in ("rob", "robg"):
            ax.axhline(CRIT["robust_deg"], color="0.5", ls="--", label="Criterion")
        if key == "cal":
            ax.axhline(CRIT["cal_deg"], color="0.5", ls="--", label="Criterion")
        plot.finish(fig, ax, title, "Standoff Behind Board (mm)", ylabel, OUT / fname, legend=True)


# ============================================================ section 3
S3_HEADER = ("target", "n_cells", "amp_nWb_per_A", "raw_deg", "cal_deg", "gap_plus025_deg", "dense_gap_plus025_deg",
             "h1_deg", "h2_deg", "h3_deg", "h4_deg", "dL_target_uH", "note")
S3_GAP, S3_H = 1.0, 2.0


def _s3_make(spec):
    kind, p = spec["kind"], spec["params"]
    gap = S3_GAP
    if kind == "sector":
        return sector_target(gap, p["deg"], p["k"], p["overhang"])
    if kind == "inset":
        return g.sector_sheet(R_IN + 2, R_OUT - 2, 60.0, 2, cell_for_gap(gap), gap)
    cell = cell_for_gap(gap, np.pi * ((R_OUT + 2.0) ** 2 - (R_IN - 2.0) ** 2))
    if kind == "pockets":
        return g.disc_sheet(R_OUT + 2.0, cell, gap, r_hole_mm=R_IN - 2.0, n_slots=2, slot_deg=p["deg"])
    if kind == "slots":
        return g.disc_sheet(R_OUT + 2.0, cell, gap, r_hole_mm=R_IN - 2.0, n_slots=4, slot_deg=45.0)
    raise ValueError(kind)


def _s3_target(spec):
    tx, rs, rc = build_coils()
    plane = g.ImagePlane(BOARD_BACK - S3_H)
    tg = _s3_make(spec)
    t0 = time.time()
    res, th = ring_sweep(tx, rs, rc, tg, plane=plane)
    a = analyse(res, th)
    hm = sensor.harmonics(res["angle"] - res["angle"][0], a["err_raw"], n_max=6)
    r_g, t_g = ring_sweep(tx, rs, rc, tg.translated_mm((0, 0, DELTA)), plane=plane, step=ROB_STEP)
    rob = apply_calibration(a, r_g, t_g)
    dense = dense_delta(a, r_g, t_g, a["err_raw"], th)
    ps = sheet.SheetSolver(tg, plane)
    dL = sheet.rx_flux(tg, ps.respond(tx.segments()), tx.segments(), plane)
    return (spec["name"], tg.n, a["amp"] * 1e9, a["raw_max"], a["cal_max"], rob, dense, hm[1], hm[2], hm[3], hm[4], dL * 1e6, spec["note"], time.time() - t0)


def section_targets(report):
    log("3. target shapes")
    specs = [dict(name=f"2 sectors {sd:.0f} deg, overhang 2", kind="sector", params=dict(deg=sd, k=2, overhang=2.0), note="sector angle sweep") for sd in SECTOR_FINE]
    specs += [dict(name=f"1 sector {sd:.0f} deg, overhang 2", kind="sector", params=dict(deg=sd, k=1, overhang=2.0), note="single sector") for sd in ((45.0, 60.0, 90.0) if not SMOKE else (60.0,))]
    specs += [dict(name=f"2 sectors 60 deg, overhang {ov:.0f}", kind="sector", params=dict(deg=60.0, k=2, overhang=ov), note="radial overhang") for ov in OVERHANGS]
    specs += [dict(name=f"inverse: annulus with 2 pockets {pk:.0f} deg", kind="pockets", params=dict(deg=pk), note="metal face with pockets") for pk in ((30.0, 45.0, 60.0, 75.0, 90.0) if not SMOKE else (60.0,))]
    specs += [dict(name="annulus with 4 slots 45 deg", kind="slots", params={}, note="N=2 sees slots 180 deg apart in phase: no signal, expected"),
              dict(name="2 sectors 60 deg, r 19-27 (inset 2)", kind="inset", params={}, note="inset")]
    out = pmap(_s3_target, specs, WORKERS)
    rows = [r[:-1] for r in out]
    for r in out:
        log(f"   {r[0]}: amp {r[2]:.2f} raw {r[3]:.3f} cal {r[4]:.4f} gap+ {r[5]:.4f} dense {r[6]:.4f} deg, h1..4 {r[7]:.3f} {r[8]:.3f} {r[9]:.3f} {r[10]:.3f}, dL {r[11]:.3f} uH ({r[13]:.0f} s)")
    report["s3"] = (S3_HEADER, rows)
    write_rows_text(OUT / "s3_targets.csv", S3_HEADER, rows)
    sel = [r for r in rows if r[12] == "sector angle sweep"]
    angs = [float(r[0].split()[2]) for r in sel]
    plot.line_plot(angs, {"Amplitude": [r[2] for r in sel]}, "Signal Vs Sector Angle, Two Sectors", "Sector Angle (deg)",
                   "Flux Amplitude (nWb/A)", OUT / "s3_amp_vs_sector.png", marker="o")
    plot.line_plot(angs, {"Raw": [r[3] for r in sel], "After 10 Segments": [r[4] for r in sel], "Dense LUT, Gap +0.25 mm": [r[6] for r in sel]},
                   "Angle Error Vs Sector Angle, Two Sectors", "Sector Angle (deg)", "Peak Error (mech deg)",
                   OUT / "s3_error_vs_sector.png", marker="o")
    plot.line_plot(angs, {"1st": [r[7] for r in sel], "2nd": [r[8] for r in sel], "3rd": [r[9] for r in sel], "4th": [r[10] for r in sel]},
                   "Raw Error Harmonics Vs Sector Angle", "Sector Angle (deg)", "Harmonic Amplitude (mech deg)",
                   OUT / "s3_harmonics_vs_sector.png", marker="o")
    pk = [r for r in rows if r[12] == "metal face with pockets"]
    if len(pk) > 1:
        pangs = [float(r[0].split()[-2]) for r in pk]
        plot.line_plot(pangs, {"Amplitude": [r[2] for r in pk]}, "Signal Vs Pocket Angle, Metal Face", "Pocket Angle (deg)",
                       "Flux Amplitude (nWb/A)", OUT / "s3_amp_vs_pocket.png", marker="o")
        plot.line_plot(pangs, {"Raw": [r[3] for r in pk], "After 10 Segments": [r[4] for r in pk], "Dense LUT, Gap +0.25 mm": [r[6] for r in pk]},
                       "Angle Error Vs Pocket Angle, Metal Face", "Pocket Angle (deg)", "Peak Error (mech deg)",
                       OUT / "s3_error_vs_pocket.png", marker="o")


# ============================================================ section 4
S4_HEADER = ("sectors", "overhang_mm", "ecc_mm", "amp_nWb_per_A", "raw_deg", "cal_deg", "once_per_turn_deg", "twice_per_turn_deg", "dense_vs_centred_deg")


def _s4_variant(args):
    k, ov = args
    tx, rs, rc = build_coils()
    gap, h = 1.0, 2.0
    plane = g.ImagePlane(BOARD_BACK - h)
    tg = sector_target(gap, 60.0, k, ov)
    rows = []
    nominal = None
    for e in ECCS:
        res, th = ring_sweep(tx, rs, rc, tg, plane=plane, periods=N, ecc=e)
        a = analyse(res, th, periods=N)
        hm = sensor.harmonics(np.radians(th), a["err_raw"], n_max=4)
        if nominal is None:
            nominal = (a, th)
            dense = 0.0
        else:
            dense = dense_delta(nominal[0], res, th, nominal[0]["err_raw"], nominal[1])
        rows.append((k, ov, e, a["amp"] * 1e9, a["raw_max"], a["cal_max"], hm[1], hm[2], dense))
    return rows


def section_misalignment(report):
    log("4. misalignment: eccentricity vs sectors and overhang")
    variants = [(2, ov) for ov in OVERHANGS] + [(1, 2.0)]
    rows = [r for block in pmap(_s4_variant, variants, WORKERS) for r in block]
    for r in rows:
        log(f"   {r[0]} sector(s), overhang {r[1]}, ecc {r[2]}: once-per-turn {r[6]:.4f} twice {r[7]:.4f} raw {r[4]:.3f} cal {r[5]:.4f} dense-vs-centred {r[8]:.4f} deg")
    report["s4"] = (S4_HEADER, rows)
    write_rows(OUT / "s4_misalignment.csv", S4_HEADER, rows)
    fig, ax = plot.figure()
    for k, ov in variants:
        sel = [r for r in rows if r[0] == k and r[1] == ov]
        ax.plot([r[2] for r in sel], [r[6] for r in sel], marker="o", label=f"{k} Sector{'s' if k > 1 else ''}, Overhang {ov:.0f} mm")
    plot.finish(fig, ax, "Once Per Turn Error Vs Eccentricity", "Eccentricity (mm)", "Error Amplitude (mech deg)",
                OUT / "s4_once_per_turn.png", legend=True)


# ============================================================ report
def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        cells = []
        for v in r:
            if isinstance(v, str):
                cells.append(v)
            elif isinstance(v, (int, np.integer)) or (float(v).is_integer() and abs(v) < 1e6):
                cells.append(f"{int(v)}")
            else:
                cells.append(f"{v:.4g}")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def write_report(report):
    lines = [
        "# Case 04 -- yaw ring stack-height and target study",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `simulation/cases/04_yaw_stack_study.py`"
        f"{' (SMOKE run: coarse grids)' if SMOKE else ''}. Ring r {R_IN}-{R_OUT} mm, N = {N}, TX {TX_TURNS} turns per edge "
        f"per layer, RX amplitude {RX_AMP} mm, two-layer {abs(LAYERS[1]):.1f} mm board, C = {C_TANK*1e12:.0f} pF.",
        "",
        "Two views of accuracy: `cal_deg` and the `plane_/gap_` columns use the LX34311's 10-segment linearizer",
        "(the on-chip view). The `dense_*` columns are what a dense firmware LUT calibrated at nominal leaves when the",
        "condition changes (the change of the raw error curve, mean removed) -- with a dense LUT the static shape",
        "calibrates out entirely and only these remain.",
        "",
        "Pass criteria (PROVISIONAL): L >= 3 uH, Q >= 10, calibrated error <= 0.25 mech deg, signal >= 50 % of the",
        "no-plane amplitude, and <= 0.10 mech deg extra error when, after 10-segment calibration, the plane comes 0.25 mm",
        "closer or the airgap grows 0.25 mm (the adverse directions).",
        "Standoff is measured from the back face of the 1.0 mm ring board to the conducting plane; the distance from the",
        "receive copper is standoff + 1.0 mm. Microchip's rule asks for 3 x airgap from the receive copper.",
        "",
        "Model limits: perfect conductors, no AGC, collocation cells of about gap/3 (floored at 0.25 mm -- see section 0),",
        "the main board approximated as an infinite plane.",
        "",
    ]
    if "s0" in report:
        lines += ["## 0. Mesh convergence", "", md_table(*report["s0"]), ""]
    if "s1" in report:
        lines += ["## 1. Tank options: L and Q vs standoff", "",
                  "standoff_mm = -1 is free space. C_pF_for_3MHz is the tank capacitance that would put the oscillator at 3 MHz.", "",
                  md_table(*report["s1"]), "", "![[s1_L_vs_standoff.png]] ![[s1_Q_vs_standoff.png]]", ""]
    if "s2" in report:
        header, rows = report["s2"]
        passing = [r for r in rows if r[-1] == 1]
        lines += ["## 2. Gap x standoff grid", "",
                  "standoff_mm = -1 rows are the no-plane reference for each gap (their gap columns are airgap robustness with no plane).", ""]
        if passing:
            best = min(passing, key=lambda r: r[0] + r[1])
            lines += [f"**Thinnest combination passing the 10-segment criteria on this grid: gap {best[0]} mm, standoff {best[1]} mm** "
                      f"(coil face to plane {best[0] + 1.0 + best[1]:.2f} mm).", ""]
        lines += [md_table(header, rows), "",
                  "![[s2_amp_vs_standoff.png]] ![[s2_cal_vs_standoff.png]] ![[s2_plane_robustness.png]] ![[s2_gap_robustness.png]] "
                  "![[s2_dense_plane.png]] ![[s2_dense_gap.png]] ![[s2_L_vs_standoff.png]]", ""]
    if "s3" in report:
        lines += [f"## 3. Target shapes at gap {S3_GAP} mm, standoff {S3_H} mm", "",
                  "h1..h4 are the raw-error harmonics against electrical angle. dL_target is the transmit inductance change",
                  "caused by the target itself.", "",
                  md_table(*report["s3"]), "",
                  "![[s3_amp_vs_sector.png]] ![[s3_error_vs_sector.png]] ![[s3_harmonics_vs_sector.png]] ![[s3_amp_vs_pocket.png]] ![[s3_error_vs_pocket.png]]", ""]
    if "s4" in report:
        lines += ["## 4. Misalignment: once-per-turn error vs eccentricity", "",
                  "dense_vs_centred is what a dense LUT calibrated on the centred target leaves at that eccentricity.", "",
                  md_table(*report["s4"]), "", "![[s4_once_per_turn.png]]", ""]
    if report.get("errors"):
        lines += ["## Errors", ""] + [f"- {e}" for e in report["errors"]] + [""]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    log(f"start{' (SMOKE)' if SMOKE else ''}; gaps {GAPS}, standoffs {STANDOFFS}, step {STEP} deg, workers {WORKERS or 'auto'}")
    report = {"errors": []}
    for fn in (section_convergence, section_tank, section_gap_standoff, section_targets, section_misalignment):
        t0 = time.time()
        try:
            fn(report)
        except Exception as ex:  # keep going: a partial report beats none
            msg = f"{fn.__name__} failed after {time.time()-t0:.0f} s: {ex!r}"
            log(msg)
            log(traceback.format_exc())
            report["errors"].append(msg)
        write_report(report)
        log(f"   {fn.__name__} done in {(time.time()-t0)/60:.1f} min")
    log(f"all done in {(time.time()-t_start)/60:.1f} min -> {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
