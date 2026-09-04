"""Case 04 -- yaw ring stack-height and target study (long running, overnight).

Question: how thin can the yaw sensor stack be? Two levers: bring the target closer to
the coils (smaller airgap) and bring the main board closer behind the ring board
(smaller standoff). And is the two-sector target the best target for those conditions?

Sections (each writes its own CSV and figures as soon as it finishes, and the report is
regenerated after every section, so a partial run is still readable):

  0. mesh convergence  -- how far the cell size can be trusted at small gaps
  1. tank options      -- L, Q vs plane height for TX turn count and trace width (fast)
  2. gap x standoff    -- signal, raw/calibrated error, and robustness to +/-0.25 mm of
                          plane height and airgap, for every (gap, standoff) pair
  3. target shapes     -- sector angle (fine), one vs two sectors, radial overhang,
                          inverse target (metal disc with pockets), slotted disc
  4. misalignment      -- once-per-turn error vs eccentricity for one vs two sectors and
                          for radial overhang

Pass criteria used for the verdict columns (PROVISIONAL, stated so they can be argued
with in the vault): L >= 3 uH and Q >= 10 (LX34311), calibrated error <= 0.25 mech deg,
signal >= 50 % of the free-space amplitude, and <= 0.10 mech deg of extra error when the
plane comes 0.25 mm closer or the airgap grows 0.25 mm after calibration.

Run:   python cases/04_yaw_stack_study.py            (several hours)
       python cases/04_yaw_stack_study.py --smoke    (minutes, coarse, to check the plumbing)
Watch: out/04_yaw_stack_study/progress.log ; read out/04_yaw_stack_study/REPORT.md
"""
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indsim import biot, geometry as g, plot, sensor, sheet  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out" / "04_yaw_stack_study"
SMOKE = "--smoke" in sys.argv

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

# ------------------------------------------------------------------ study grids (mm, deg)
GAPS = (0.75, 1.0, 1.5) if not SMOKE else (1.0,)   # 2.0 mm: cases 02/03
STANDOFFS = (0.5, 1.0, 1.5, 2.0, 3.0) if not SMOKE else (1.0, 3.0)   # 5 mm and beyond: case 03
STEP = 5.0 if not SMOKE else 30.0      # target angle step over one electrical period
ROB_STEP = 10.0 if not SMOKE else 30.0  # coarser step for the 0.25 mm robustness re-sweeps
MAX_CELLS = 5000                       # K build time goes as n^2; convergence section prices this
SECTOR_DEG_DEFAULT, K_DEFAULT = 60.0, 2
OVERHANG_DEFAULT = 2.0                 # target radial overhang beyond the coil band, each side
DELTA = 0.25                           # +/- move used for the robustness columns
SECTOR_FINE = (30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0) if not SMOKE else (60.0,)
OVERHANGS = (0.0, 1.0, 2.0, 3.0) if not SMOKE else (0.0, 2.0)
ECCS = (0.0, 0.1, 0.2, 0.3) if not SMOKE else (0.0, 0.3)
CONVERGENCE_CELLS = (0.6, 0.45, 0.35, 0.30) if not SMOKE else (0.6, 0.45)   # 0.30 -> 8570 cells, the one slow point
CRIT = {"L": 3e-6, "Q": 10.0, "cal_deg": 0.25, "amp_frac": 0.5, "robust_deg": 0.10}

LOG = None


def log(msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    if LOG is not None:
        with open(LOG, "a") as f:
            f.write(line + "\n")


def cell_for_gap(gap_mm, area_mm2=None):
    """Cell side: a third of the airgap, floored at 0.30 mm, and coarsened if the target
    area would need more than MAX_CELLS cells (keeps K under ~600 MB)."""
    c = max(gap_mm / 3, 0.30)
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
    """Error (mech deg) of a perturbed sweep read through a linearizer fitted elsewhere."""
    ideal = cal_map["slope"] * thetas + cal_map["intercept"]
    # unwrap may start a turn away from the calibration sweep: bring it back
    ang = res["angle"] - 2 * np.pi * np.round((res["angle"][0] - ideal[0]) / (2 * np.pi))
    corrected = np.interp(ang, cal_map["knots"], cal_map["coef"])
    err = (corrected - ideal) / cal_map["slope"]
    err -= err.mean()  # a constant offset re-zeroes at the next homing; keep the shape
    return float(np.abs(err).max())


def ring_sweep(tx, rx_sin, rx_cos, target, plane=None, step=STEP, periods=1, ecc=0.0):
    thetas = np.arange(0.0, periods * 360.0 / N + step / 2, step)
    place = lambda th: target.rotated_deg(th).translated_mm((ecc, 0.0, 0.0))  # noqa: E731
    res = sensor.run_sweep(tx, rx_sin, rx_cos, place, thetas, plane=plane)
    return res, thetas


def tank_with_plane(tx, plane):
    return sensor.tank(tx, C_TANK, plane=plane, cu_thickness=CU_T)


def write_rows(path, header, rows):
    plot.write_csv(path, {h: np.array([r[i] for r in rows], dtype=float) for i, h in enumerate(header)})


# ============================================================ sections
def section_convergence(report):
    log("0. mesh convergence")
    tx, rs, rc = build_coils()
    rows = []
    for gap in (1.0, 0.75) if not SMOKE else (1.0,):
        ref = None
        for cell in CONVERGENCE_CELLS:
            tg = sector_target(gap, cell=cell)
            t0 = time.time()
            res, th = ring_sweep(tx, rs, rc, tg, step=15.0 if not SMOKE else 30.0)
            a = analyse(res, th)
            ref = ref or a["amp"]
            rows.append((gap, cell, tg.n, a["amp"] * 1e9, a["amp"] / ref, a["raw_max"], a["cal_max"], time.time() - t0))
            log(f"   gap {gap} cell {cell}: {tg.n} cells, amp {a['amp']*1e9:.2f} nWb/A ({a['amp']/ref:.4f} of coarsest), "
                f"raw {a['raw_max']:.3f} cal {a['cal_max']:.4f} deg, {time.time()-t0:.0f} s")
    header = ("gap_mm", "cell_mm", "n_cells", "amp_nWb_per_A", "amp_rel", "raw_deg", "cal_deg", "seconds")
    write_rows(OUT / "s0_convergence.csv", header, rows)
    report["s0"] = (header, rows)


def section_tank(report):
    log("1. tank options vs plane height")
    rows = []
    for turns in (3, 4, 5) if not SMOKE else (3,):
        for trace in (0.1524, 0.2032, 0.254) if not SMOKE else (0.1524,):
            tx, _, _ = build_coils(turns, trace)
            free = sensor.tank(tx, C_TANK, cu_thickness=CU_T)
            for h in (None,) + STANDOFFS:
                t = free if h is None else tank_with_plane(tx, g.ImagePlane(BOARD_BACK - h))
                c_for_3mhz = 1 / ((2 * np.pi * 3e6) ** 2 * t["L"])
                rows.append((turns, trace / 0.0254, -1 if h is None else h, t["L"] * 1e6, t["Q"], t["f0"] / 1e6, t["R"], c_for_3mhz * 1e12,
                             int(t["L"] >= CRIT["L"] and t["Q"] >= CRIT["Q"])))
            log(f"   {turns} turns/edge, {trace/0.0254:.0f} mil: free L {free['L']*1e6:.2f} uH Q {free['Q']:.0f}, "
                f"at {STANDOFFS[0]} mm standoff L {rows[-len(STANDOFFS)][3]:.2f} uH Q {rows[-len(STANDOFFS)][4]:.0f}")
    header = ("tx_turns_per_edge", "trace_mil", "standoff_mm", "L_uH", "Q", "f0_MHz_at_600pF", "R_ohm", "C_pF_for_3MHz", "passes_L_Q")
    write_rows(OUT / "s1_tank.csv", header, rows)
    report["s1"] = (header, rows)
    # figure: L vs standoff for each turn count at 6 mil
    fig, ax = plot.figure()
    for turns in (3, 4, 5):
        sel = [r for r in rows if r[0] == turns and abs(r[1] - 6) < 0.5 and r[2] >= 0]
        ax.plot([r[2] for r in sel], [r[3] for r in sel], marker="o", label=f"{turns} Turns Per Edge")
    ax.axhline(3.0, color="0.5", ls="--", label="LX34311 Minimum")
    plot.finish(fig, ax, "Transmit Inductance Vs Standoff, 6 mil Trace", "Standoff Behind Board (mm)", "Inductance (uH)",
                OUT / "s1_L_vs_standoff.png", legend=True)
    fig, ax = plot.figure()
    for trace in (0.1524, 0.2032, 0.254):
        sel = [r for r in rows if r[0] == 3 and abs(r[1] - trace / 0.0254) < 0.5 and r[2] >= 0]
        ax.plot([r[2] for r in sel], [r[4] for r in sel], marker="o", label=f"{trace/0.0254:.0f} mil Trace")
    ax.axhline(10.0, color="0.5", ls="--", label="LX34311 Minimum")
    plot.finish(fig, ax, "Transmit Q Vs Standoff, 3 Turns Per Edge", "Standoff Behind Board (mm)", "Q",
                OUT / "s1_Q_vs_standoff.png", legend=True)


def section_gap_standoff(report):
    log("2. gap x standoff grid")
    tx, rs, rc = build_coils()
    rows = []
    free_amp = {}
    for gap in GAPS:
        tg = sector_target(gap)
        res, th = ring_sweep(tx, rs, rc, tg)
        a0 = analyse(res, th)
        free_amp[gap] = a0["amp"]
        # airgap robustness with no plane: calibrate at gap, read at gap +/- DELTA
        rob_gap = apply_calibration(a0, *ring_sweep(tx, rs, rc, tg.translated_mm((0, 0, DELTA)), step=ROB_STEP))
        rows.append((gap, -1, 0, 0, 0, a0["amp"] * 1e9, 1.0, a0["raw_max"], a0["cal_max"], 0.0, rob_gap, -1))
        log(f"   gap {gap}: free amp {a0['amp']*1e9:.2f} nWb/A raw {a0['raw_max']:.3f} cal {a0['cal_max']:.4f} deg, "
            f"+/-{DELTA} mm gap after cal {rob_gap:.4f} deg ({tg.n} cells)")
        for h in STANDOFFS:
            t0 = time.time()
            plane = g.ImagePlane(BOARD_BACK - h)
            tk = tank_with_plane(tx, plane)
            res, th = ring_sweep(tx, rs, rc, tg, plane=plane)
            a = analyse(res, th)
            # plane moves +/- DELTA after calibration (board flex, standoff tolerance)
            # one-sided, adverse directions: plane DELTA closer, target DELTA further
            rob_plane = apply_calibration(a, *ring_sweep(tx, rs, rc, tg, plane=g.ImagePlane(BOARD_BACK - h + DELTA), step=ROB_STEP))
            rob_gap = apply_calibration(a, *ring_sweep(tx, rs, rc, tg.translated_mm((0, 0, DELTA)), plane=plane, step=ROB_STEP))
            passes = int(tk["L"] >= CRIT["L"] and tk["Q"] >= CRIT["Q"] and a["cal_max"] <= CRIT["cal_deg"]
                         and a["amp"] / free_amp[gap] >= CRIT["amp_frac"] and max(rob_plane, rob_gap) <= CRIT["robust_deg"])
            rows.append((gap, h, tk["L"] * 1e6, tk["Q"], tk["f0"] / 1e6, a["amp"] * 1e9, a["amp"] / free_amp[gap], a["raw_max"], a["cal_max"], rob_plane, rob_gap, passes))
            log(f"   gap {gap} standoff {h}: L {tk['L']*1e6:.2f} Q {tk['Q']:.0f} amp {a['amp']/free_amp[gap]:.2f}x "
                f"raw {a['raw_max']:.3f} cal {a['cal_max']:.4f} plane+/- {rob_plane:.4f} gap+/- {rob_gap:.4f} deg "
                f"{'PASS' if passes else 'fail'} ({time.time()-t0:.0f} s)")
        report["s2"] = (S2_HEADER, rows)
        write_rows(OUT / "s2_gap_standoff.csv", S2_HEADER, rows)
        write_report(report)
    # figures
    for key, idx, title, ylabel, fname in (
        ("amp", 6, "Signal Vs Standoff, Relative To No Plane", "Amplitude Ratio", "s2_amp_vs_standoff.png"),
        ("cal", 8, "Calibrated Error Vs Standoff", "Peak Error After Linearizer (mech deg)", "s2_cal_vs_standoff.png"),
        ("rob", 9, "Extra Error When The Plane Comes 0.25 mm Closer", "Peak Error (mech deg)", "s2_plane_robustness.png"),
        ("robg", 10, "Extra Error When The Airgap Grows 0.25 mm", "Peak Error (mech deg)", "s2_gap_robustness.png"),
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


S2_HEADER = ("gap_mm", "standoff_mm", "L_uH", "Q", "f0_MHz", "amp_nWb_per_A", "amp_rel_free", "raw_deg", "cal_deg",
             "plane_minus025_deg", "gap_plus025_deg", "passes")


def section_targets(report):
    log("3. target shapes")
    tx, rs, rc = build_coils()
    gap = 1.0
    h = 2.0
    plane = g.ImagePlane(BOARD_BACK - h)
    rows = []

    def run(name, tg, note=""):
        t0 = time.time()
        res, th = ring_sweep(tx, rs, rc, tg, plane=plane)
        a = analyse(res, th)
        hm = sensor.harmonics(res["angle"] - res["angle"][0], a["err_raw"], n_max=6)
        rob = apply_calibration(a, *ring_sweep(tx, rs, rc, tg.translated_mm((0, 0, DELTA)), plane=plane, step=ROB_STEP))
        # target loads the tank too: inductance drop from the target sheet alone
        ps = sheet.SheetSolver(tg, plane)
        dL = sheet.rx_flux(tg, ps.respond(tx.segments()), tx.segments(), plane)
        rows.append((name, tg.n, a["amp"] * 1e9, a["raw_max"], a["cal_max"], rob, hm[1], hm[2], hm[3], hm[4], dL * 1e6, note))
        log(f"   {name}: amp {a['amp']*1e9:.2f} raw {a['raw_max']:.3f} cal {a['cal_max']:.4f} gap+/- {rob:.4f} deg, "
            f"h1..4 {hm[1]:.3f} {hm[2]:.3f} {hm[3]:.3f} {hm[4]:.3f}, dL {dL*1e6:.3f} uH ({time.time()-t0:.0f} s)")
        report["s3"] = (S3_HEADER, rows)
        write_report(report)

    for sd in SECTOR_FINE:
        run(f"2 sectors {sd:.0f} deg, overhang 2", sector_target(gap, sd, 2, 2.0), "sector angle sweep")
    for sd in (45.0, 60.0, 90.0) if not SMOKE else (60.0,):
        run(f"1 sector {sd:.0f} deg, overhang 2", sector_target(gap, sd, 1, 2.0), "single sector")
    for ov in OVERHANGS:
        run(f"2 sectors 60 deg, overhang {ov:.0f}", sector_target(gap, 60.0, 2, ov), "radial overhang")
    # inverse target: a full metal face with two 60 deg pockets (an aluminium frame face)
    cell = cell_for_gap(gap, np.pi * ((R_OUT + 2.0) ** 2 - (R_IN - 2.0) ** 2))
    for pocket in (60.0, 90.0) if not SMOKE else (60.0,):
        inv = g.disc_sheet(R_OUT + 2.0, cell, gap, r_hole_mm=R_IN - 2.0, n_slots=2, slot_deg=pocket)
        run(f"inverse: annulus with 2 pockets {pocket:.0f} deg", inv, "metal face with pockets")
    # slotted disc (library-style periodic target): 4 slots on the 2-period ring is the same
    # electrical phase in every slot, so it reads like 2 sectors x 2; included for the record
    slotted = g.disc_sheet(R_OUT + 2.0, cell, gap, r_hole_mm=R_IN - 2.0, n_slots=4, slot_deg=45.0)
    run("annulus with 4 slots 45 deg", slotted, "N=2 sees slots 180 deg apart in phase")
    # sector with reduced radial extent (no overhang, inside the band) for the record
    run("2 sectors 60 deg, r 19-27 (inset 2)", g.sector_sheet(R_IN + 2, R_OUT - 2, 60.0, 2, cell_for_gap(gap), gap), "inset")
    write_rows_text(OUT / "s3_targets.csv", S3_HEADER, rows)
    # figure: sector angle sweep
    sel = [r for r in rows if r[11] == "sector angle sweep"]
    angs = [float(r[0].split()[2]) for r in sel]
    plot.line_plot(angs, {"Amplitude": [r[2] for r in sel]}, "Signal Vs Sector Angle, Two Sectors", "Sector Angle (deg)",
                   "Flux Amplitude (nWb/A)", OUT / "s3_amp_vs_sector.png", marker="o")
    plot.line_plot(angs, {"Raw": [r[3] for r in sel], "After Linearizer": [r[4] for r in sel], "Gap +0.25 mm After Cal": [r[5] for r in sel]},
                   "Angle Error Vs Sector Angle, Two Sectors", "Sector Angle (deg)", "Peak Error (mech deg)",
                   OUT / "s3_error_vs_sector.png", marker="o")
    plot.line_plot(angs, {"1st": [r[6] for r in sel], "2nd": [r[7] for r in sel], "3rd": [r[8] for r in sel], "4th": [r[9] for r in sel]},
                   "Raw Error Harmonics Vs Sector Angle", "Sector Angle (deg)", "Harmonic Amplitude (mech deg)",
                   OUT / "s3_harmonics_vs_sector.png", marker="o")


S3_HEADER = ("target", "n_cells", "amp_nWb_per_A", "raw_deg", "cal_deg", "gap_plus025_deg", "h1_deg", "h2_deg", "h3_deg", "h4_deg", "dL_target_uH", "note")


def write_rows_text(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(f"{v:.6g}" if isinstance(v, (int, float, np.floating)) else str(v).replace(",", ";") for v in r) + "\n")


def section_misalignment(report):
    log("4. misalignment: eccentricity vs sectors and overhang")
    tx, rs, rc = build_coils()
    gap, h = 1.0, 2.0
    plane = g.ImagePlane(BOARD_BACK - h)
    rows = []
    variants = [(2, ov) for ov in OVERHANGS] + [(1, 2.0)]
    for k, ov in variants:
        tg = sector_target(gap, 60.0, k, ov)
        for e in ECCS:
            t0 = time.time()
            res, th = ring_sweep(tx, rs, rc, tg, plane=plane, periods=N, ecc=e)
            a = analyse(res, th, periods=N)
            hm = sensor.harmonics(np.radians(th), a["err_raw"], n_max=4)   # against mechanical angle
            rows.append((k, ov, e, a["amp"] * 1e9, a["raw_max"], a["cal_max"], hm[1], hm[2]))
            log(f"   {k} sector(s), overhang {ov}, ecc {e}: once-per-turn {hm[1]:.4f} twice {hm[2]:.4f} raw {a['raw_max']:.3f} "
                f"cal {a['cal_max']:.4f} deg ({time.time()-t0:.0f} s)")
        report["s4"] = (S4_HEADER, rows)
        write_report(report)
    write_rows(OUT / "s4_misalignment.csv", S4_HEADER, rows)
    fig, ax = plot.figure()
    for k, ov in variants:
        sel = [r for r in rows if r[0] == k and r[1] == ov]
        ax.plot([r[2] for r in sel], [r[6] for r in sel], marker="o", label=f"{k} Sector{'s' if k > 1 else ''}, Overhang {ov:.0f} mm")
    plot.finish(fig, ax, "Once Per Turn Error Vs Eccentricity", "Eccentricity (mm)", "Error Amplitude (mech deg)",
                OUT / "s4_once_per_turn.png", legend=True)


S4_HEADER = ("sectors", "overhang_mm", "ecc_mm", "amp_nWb_per_A", "raw_deg", "cal_deg", "once_per_turn_deg", "twice_per_turn_deg")


# ============================================================ report
def md_table(header, rows, fmt=None):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        cells = []
        for v in r:
            if isinstance(v, str):
                cells.append(v)
            elif isinstance(v, (int, np.integer)) or float(v).is_integer() and abs(v) < 1e6:
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
        "Pass criteria (PROVISIONAL): L >= 3 uH, Q >= 10, calibrated error <= 0.25 mech deg, signal >= 50 % of the",
        "no-plane amplitude, and <= 0.10 mech deg extra error when, after calibration, the plane comes 0.25 mm closer",
        "or the airgap grows 0.25 mm (the adverse directions; one-sided to halve the run time).",
        "Standoff is measured from the back face of the 1.0 mm ring board to the conducting plane; the distance from the",
        "receive copper is standoff + 1.0 mm. Microchip's rule asks for 3 x airgap from the receive copper.",
        "",
        "Model limits: perfect conductors, no AGC, collocation cells of about gap/3 (floored at 0.30 mm -- see section 0",
        "for how much the 0.75 mm gap can be trusted), the main board approximated as an infinite plane.",
        "",
    ]
    if "s0" in report:
        lines += ["## 0. Mesh convergence", "", md_table(*report["s0"]), ""]
    if "s1" in report:
        header, rows = report["s1"]
        lines += ["## 1. Tank options: L and Q vs standoff", "",
                  "standoff_mm = -1 is free space. C_pF_for_3MHz is the tank capacitance that would put the oscillator at 3 MHz.", "",
                  md_table(header, rows), "", "![[s1_L_vs_standoff.png]] ![[s1_Q_vs_standoff.png]]", ""]
    if "s2" in report:
        header, rows = report["s2"]
        passing = [r for r in rows if r[-1] == 1]
        lines += ["## 2. Gap x standoff grid", "",
                  "standoff_mm = -1 rows are the no-plane reference for each gap (their gap_plus025 column is airgap robustness with no plane).", ""]
        if passing:
            best = min(passing, key=lambda r: r[0] + r[1])
            lines += [f"**Thinnest passing combination on this grid: gap {best[0]} mm, standoff {best[1]} mm** "
                      f"(stack from coil face to target {best[0]} mm plus board 1.0 mm plus standoff {best[1]} mm = {best[0] + 1.0 + best[1]:.2f} mm).", ""]
        lines += [md_table(header, rows), "",
                  "![[s2_amp_vs_standoff.png]] ![[s2_cal_vs_standoff.png]] ![[s2_plane_robustness.png]] ![[s2_gap_robustness.png]] ![[s2_L_vs_standoff.png]]", ""]
    if "s3" in report:
        header, rows = report["s3"]
        lines += ["## 3. Target shapes at gap 1.0 mm, standoff 2.0 mm", "",
                  "h1..h4 are the raw-error harmonics against electrical angle (the linearizer removes low orders best).",
                  "dL_target is the transmit inductance change caused by the target itself.", "",
                  md_table(header, rows), "", "![[s3_amp_vs_sector.png]] ![[s3_error_vs_sector.png]] ![[s3_harmonics_vs_sector.png]]", ""]
    if "s4" in report:
        header, rows = report["s4"]
        lines += ["## 4. Misalignment: once-per-turn error vs eccentricity", "", md_table(header, rows), "", "![[s4_once_per_turn.png]]", ""]
    if "errors" in report and report["errors"]:
        lines += ["## Errors", ""] + [f"- {e}" for e in report["errors"]] + [""]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n")


def main():
    global LOG
    OUT.mkdir(parents=True, exist_ok=True)
    LOG = OUT / "progress.log"
    t_start = time.time()
    log(f"start{' (SMOKE)' if SMOKE else ''}; gaps {GAPS}, standoffs {STANDOFFS}, step {STEP} deg")
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
