"""Case 07 -- the yaw ring as proposed, end to end.

Configuration (from cases 04-06): two-layer 1.0 mm ring board, copper band r 17-23 mm
(30 mm beam hole, 50 mm board), N = 2 (180 deg absolute range), transmit 4 turns per
edge at 8 mil trace / 6 mil gap on both layers, receive lobe amplitude 1.28 mm, airgap
1.0 mm, main board 1.0 mm behind the ring board as a uniform pour, target an aluminium
face with two 60 deg pockets overhanging the band by 2 mm (r 15-25).

Outputs, one page for a STUDY record: geometry, tank (free, with plane, with plane and
target; capacitor for 3 MHz), a full mechanical turn (flux, electrical angle, raw error,
harmonics), what a dense firmware LUT leaves when the plane, gap or centring move, the
same with the main board as a finite 70 mm disc with a 30 mm hole instead of an
infinite plane, a mesh check, and the same ring with two 60 deg sectors instead of the
pocketed face, for a frame that is not conductive.

Run:  python cases/07_yaw_ring_final.py [--workers N]
Read: out/07_yaw_ring_final/REPORT.md
"""
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from indsim import biot, geometry as g, plot, sensor, sheet, tables  # noqa: E402
from indsim.parallel import pmap  # noqa: E402

spec = importlib.util.spec_from_file_location("c04", HERE / "04_yaw_stack_study.py")
c04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c04)

OUT = HERE.parent / "out" / "07_yaw_ring_final"
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else None

# ------------------------------------------------------------------ the configuration (mm)
R_IN, R_OUT = 17.0, 23.0
N = 2
LAYERS = (0.0, -1.0)                      # two-layer 1.0 mm board, z = 0 faces the target
BOARD_BACK = -1.0
TX_TURNS, TRACE_TX, GAP_TX = 4, 0.2032, 0.1524   # 8 mil trace, 6 mil gap
TX_PITCH = TRACE_TX + GAP_TX
TRACE_RX = 0.1524
CLEAR = 0.3
RX_AMP = (R_OUT - R_IN - 2 * TX_TURNS * TX_PITCH - 2 * CLEAR) / 2
GAP, STANDOFF = 1.0, 1.0
POCKET_DEG, OVERHANG = 60.0, 2.0
TARGET_R1, TARGET_R2 = R_IN - OVERHANG, R_OUT + OVERHANG
F_TARGET = 3.0e6                          # tank design frequency
CU_T = 35e-6
STEP = 2.5                                # deg, over a full mechanical turn
PLANE_DISC_R, PLANE_HOLE_R, PLANE_CELL = 35.0, 15.0, 1.5   # main board as a finite disc
LEAF_SIGNAL = 14.1                        # nWb/A, the leaf coil of case 01 for scale
PERTURBATIONS = (
    ("plane 0.10 mm closer", dict(plane_dz=+0.10)),
    ("plane 0.25 mm closer", dict(plane_dz=+0.25)),
    ("plane 0.25 mm further", dict(plane_dz=-0.25)),
    ("gap +0.10 mm", dict(gap_dz=+0.10)),
    ("gap +0.25 mm", dict(gap_dz=+0.25)),
    ("gap -0.25 mm", dict(gap_dz=-0.25)),
    ("eccentric 0.10 mm", dict(ecc=0.10)),
    ("eccentric 0.30 mm", dict(ecc=0.30)),
)


def coils():
    tx = g.ring_tx(R_IN, R_OUT, TX_TURNS, TX_PITCH, LAYERS, n_theta=180, trace_mm=TRACE_TX)
    rs, rc = g.ring_rx_pair(R_IN, R_OUT, N, LAYERS, amp_mm=RX_AMP, n_theta=360, trace_mm=TRACE_RX)
    return tx, rs, rc


def pocket_target(gap=GAP, cell=None):
    area = np.pi * (TARGET_R2**2 - TARGET_R1**2) * (1 - 2 * POCKET_DEG / 360.0)
    cell = cell or c04.cell_for_gap(gap, area)
    return g.disc_sheet(TARGET_R2, cell, gap, r_hole_mm=TARGET_R1, n_slots=2, slot_deg=POCKET_DEG)


def sector_target(gap=GAP):
    area = c04.sector_area(POCKET_DEG, 2, TARGET_R1, TARGET_R2)
    return g.sector_sheet(TARGET_R1, TARGET_R2, POCKET_DEG, 2, c04.cell_for_gap(gap, area), gap)


def thetas_full():
    return np.arange(0.0, 360.0 + STEP / 2, STEP)


def sweep(tx, rs, rc, target, plane, ecc=0.0, step=STEP):
    th = np.arange(0.0, 360.0 + step / 2, step)
    tabs = tables.ring_tables(tx, rs, rc, target, N, plane=plane, r_min_mm=TARGET_R1 - 1.5, r_max_mm=TARGET_R2 + 1.5)
    res = sensor.run_sweep(tx, rs, rc, lambda t: target.rotated_deg(t).translated_mm((ecc, 0.0, 0.0)), th, plane=plane, tables=tabs)
    return res, th


def raw_curve(res, th, fit):
    ideal = fit["slope"] * th + fit["intercept"]
    ang = res["angle"] - 2 * np.pi * np.round((res["angle"][0] - ideal[0]) / (2 * np.pi))
    return (ang - ideal) / fit["slope"]


def dense_residual(err_nom, th_nom, err, th):
    d = err - np.interp(th, th_nom, err_nom)
    d -= d.mean()
    return float(np.abs(d).max())


# ------------------------------------------------------------------ workers
def _nominal(kind):
    tx, rs, rc = coils()
    plane = g.ImagePlane(BOARD_BACK - STANDOFF)
    tg = pocket_target() if kind == "pockets" else sector_target()
    res, th = sweep(tx, rs, rc, tg, plane)
    a = c04.analyse(res, th, periods=N)
    hm = sensor.harmonics(res["angle"] - res["angle"][0], a["err_raw"], n_max=8)
    ps = sheet.SheetSolver(tg, plane)
    dL = sheet.rx_flux(tg, ps.respond(tx.segments()), tx.segments(), plane)
    return dict(kind=kind, th=th, phi_sin=res["phi_sin"], phi_cos=res["phi_cos"], angle=res["angle"], err_raw=a["err_raw"],
                err_cal10=a["err_cal"], amp=a["amp"], raw_max=a["raw_max"], cal10_max=a["cal_max"], harmonics=hm,
                direct=(res["direct_sin"], res["direct_cos"]), dL_target=dL, n_cells=tg.n, fit=dict(slope=a["slope"], intercept=a["intercept"]))


def _perturbed(args):
    name, p = args
    tx, rs, rc = coils()
    plane = g.ImagePlane(BOARD_BACK - STANDOFF + p.get("plane_dz", 0.0))
    tg = pocket_target().translated_mm((0, 0, p.get("gap_dz", 0.0)))
    res, th = sweep(tx, rs, rc, tg, plane, ecc=p.get("ecc", 0.0))
    return name, th, res["angle"], float(res["amplitude"].mean())


def _finite_plane():
    """Main board as a 70 mm disc with a 30 mm hole, solved together with the target;
    the coils rotate over the fixed sheets."""
    tx, rs, rc = coils()
    plane_sheet = g.disc_sheet(PLANE_DISC_R, PLANE_CELL, BOARD_BACK - STANDOFF, r_hole_mm=PLANE_HOLE_R)
    tg = pocket_target(cell=0.4)
    both = tg.union(plane_sheet)
    th = np.arange(0.0, 360.0 + 7.5 / 2, 7.5)
    res = sensor.run_sweep(tx, rs, rc, both, th, coil_pose=lambda t, c: c.rotated_deg(-t))
    ps = sheet.SheetSolver(plane_sheet)
    psi = ps.respond(tx.segments())
    dL_plane = sheet.rx_flux(plane_sheet, psi, tx.segments())
    return th, res["angle"], float(res["amplitude"].mean()), dL_plane, plane_sheet.n, tg.n


def _mesh_check(cell):
    tx, rs, rc = coils()
    plane = g.ImagePlane(BOARD_BACK - STANDOFF)
    res, th = sweep(tx, rs, rc, pocket_target(cell=cell), plane, step=5.0)
    a = c04.analyse(res, th, periods=N)
    return cell, pocket_target(cell=cell).n, a["amp"] * 1e9, a["raw_max"]


# ------------------------------------------------------------------ main
def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    tx, rs, rc = coils()
    tg = pocket_target()
    plane = g.ImagePlane(BOARD_BACK - STANDOFF)
    print(f"ring r {R_IN}-{R_OUT}: TX {tx.turns()} loops, RX amplitude {RX_AMP:.2f} mm; target {tg.n} cells")
    plot.geometry_plot([tx, rs, rc], [tg], "Yaw Ring r 17-23 With Pocketed Face Target", OUT / "geometry.png")

    # tank
    free = sensor.tank(tx, 1e-9, cu_thickness=CU_T)
    with_plane = sensor.tank(tx, 1e-9, plane=plane, cu_thickness=CU_T)
    ps = sheet.SheetSolver(tg, plane)
    dL_target = sheet.rx_flux(tg, ps.respond(tx.segments()), tx.segments(), plane)
    L_op = with_plane["L"] + dL_target
    C = 1 / ((2 * np.pi * F_TARGET) ** 2 * L_op)
    R = biot.trace_resistance(tx.length(), tx.trace_width, CU_T, F_TARGET)
    Q_op = 2 * np.pi * F_TARGET * L_op / R
    f_free = 1 / (2 * np.pi * np.sqrt(free["L"] * C))
    tank_rows = [("free space", free["L"] * 1e6, free["Q"]),
                 (f"main board pour {STANDOFF} mm behind", with_plane["L"] * 1e6, with_plane["Q"]),
                 ("pour and target (operating point)", L_op * 1e6, Q_op)]

    # parallel: nominal (pockets, sectors), perturbations, finite plane, mesh check
    jobs = [("nom", "pockets"), ("nom", "sectors")] + [("pert", p) for p in PERTURBATIONS] + [("finite", None), ("mesh", 0.5), ("mesh", 0.3)]
    results = pmap(_job, jobs, WORKERS)
    out = dict(zip([j if j[0] != "pert" else ("pert", j[1][0]) for j in jobs], results))
    nom = out[("nom", "pockets")]
    sec = out[("nom", "sectors")]

    # dense-LUT residuals of the perturbations against the nominal pocket curve
    pert_rows = []
    for name, _ in PERTURBATIONS:
        pname, th_p, ang_p, amp_p = out[("pert", name)]
        err_p = raw_curve({"angle": ang_p}, th_p, nom["fit"])
        pert_rows.append((name, dense_residual(nom["err_raw"], nom["th"], err_p, th_p), amp_p / nom["amp"]))
    th_f, ang_f, amp_f, dL_plane_f, n_plane, n_tg = out[("finite", None)]
    err_f = raw_curve({"angle": ang_f}, th_f, nom["fit"])
    finite_vs_infinite = dense_residual(nom["err_raw"], nom["th"], err_f, th_f)
    mesh_rows = [out[("mesh", c)] for c in (0.5, 0.3)]

    # figures
    th = nom["th"]
    plot.line_plot(th, {"Sin Coil": nom["phi_sin"] * 1e9, "Cos Coil": nom["phi_cos"] * 1e9}, "Receive Flux Over One Turn",
                   "Target Angle (deg)", "Flux Per Ampere Of TX (nWb/A)", OUT / "flux.png")
    plot.line_plot(th, {"Electrical Angle": np.degrees(nom["angle"])}, "Electrical Angle Over One Turn", "Target Angle (deg)",
                   "Electrical Angle (deg)", OUT / "angle.png")
    plot.line_plot(th, {"Pocketed Face": nom["err_raw"], "Two Sectors": sec["err_raw"]}, "Raw Angle Error Over One Turn",
                   "Target Angle (deg)", "Error (mech deg)", OUT / "raw_error.png")
    plot.line_plot(th, {"After 10 Segments Per Period": nom["err_cal10"]}, "Error After The On-Chip Linearizer",
                   "Target Angle (deg)", "Error (mech deg)", OUT / "cal10_error.png")
    fig, ax = plot.figure()
    ax.bar(np.arange(1, 9) - 0.2, nom["harmonics"][1:9], width=0.4, label="Pocketed Face")
    ax.bar(np.arange(1, 9) + 0.2, sec["harmonics"][1:9], width=0.4, label="Two Sectors")
    plot.finish(fig, ax, "Raw Error Harmonics Of Electrical Angle", "Harmonic", "Amplitude (mech deg)", OUT / "harmonics.png", legend=True)
    fig, ax = plot.figure()
    ax.barh([r[0] for r in pert_rows], [r[1] for r in pert_rows])
    plot.finish(fig, ax, "Dense LUT Residual After A Change", "Residual (mech deg)", "", OUT / "perturbations.png")
    for name, (t, e) in (("finite", (th_f, err_f)),):
        plot.line_plot(t, {"70 mm Disc With 30 mm Hole": e, "Infinite Plane": np.interp(t, th, nom["err_raw"])},
                       "Raw Error: Finite Main Board Vs Infinite Plane", "Target Angle (deg)", "Error (mech deg)", OUT / "finite_plane.png")

    plot.write_csv(OUT / "turn.csv", {"target_angle_deg": th, "electrical_angle_deg": np.degrees(nom["angle"]), "counts_per_period": sensor.counts(nom["angle"]),
                                      "phi_sin_nWb_per_A": nom["phi_sin"] * 1e9, "phi_cos_nWb_per_A": nom["phi_cos"] * 1e9,
                                      "raw_error_mech_deg": nom["err_raw"], "cal10_error_mech_deg": nom["err_cal10"]})

    # report
    mono = bool(np.all(np.diff(nom["angle"]) > 0))
    lines = [
        "# Case 07 -- yaw ring r 17-23, end to end", "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `simulation/cases/07_yaw_ring_final.py` in {(time.time()-t0)/60:.1f} min.", "",
        "## Configuration", "",
        f"- Ring board: two-layer, {abs(LAYERS[1]):.1f} mm, copper band r {R_IN}-{R_OUT} mm, 30 mm beam hole, about 50 mm outside diameter",
        f"- Transmit: {TX_TURNS} turns per edge per layer ({tx.turns()} loops), {TRACE_TX/0.0254:.0f} mil trace, {GAP_TX/0.0254:.0f} mil gap, outer turns clockwise, inner turns counter-clockwise",
        f"- Receive: N = {N} (180 deg absolute), lobe amplitude {RX_AMP:.2f} mm, {TRACE_RX/0.0254:.0f} mil, layer swaps at the lobe extrema",
        f"- Target: aluminium face with two {POCKET_DEG:.0f} deg pockets, r {TARGET_R1}-{TARGET_R2} mm, airgap {GAP} mm",
        f"- Main board: uniform pour {STANDOFF} mm behind the ring board's back face ({STANDOFF + abs(LAYERS[1]):.1f} mm from the receive copper)",
        f"- Stack from coil face to main-board copper: {GAP + abs(LAYERS[1]) + STANDOFF:.1f} mm", "",
        "## Tank", "",
        c04.md_table(("condition", "L_uH", "Q"), tank_rows), "",
        f"Tank capacitance for {F_TARGET/1e6:.0f} MHz at the operating point: {C*1e12:.0f} pF effective, i.e. **2 x {2*C*1e12:.0f} pF** C0G 50 V "
        f"(free-space frequency then {f_free/1e6:.2f} MHz). LX34311 window: L > 3 uH, Q > 10, 1-6 MHz.", "",
        "## One mechanical turn", "",
        f"- Signal {nom['amp']*1e9:.1f} nWb/A ({nom['amp']*1e9/LEAF_SIGNAL:.1f} x the leaf coil on the bench); direct TX->RX coupling "
        f"{abs(nom['direct'][0])*1e9:.3g} / {abs(nom['direct'][1])*1e9:.3g} nWb/A",
        f"- Electrical angle monotonic over the turn: {mono}; two electrical periods per turn",
        f"- Raw error {nom['raw_max']:.3f} mech deg peak; after the on-chip 10-segment linearizer {nom['cal10_max']:.3f} deg; a dense firmware LUT removes the static shape",
        f"- Raw error harmonics 1..8 of electrical angle (mech deg): {np.array2string(nom['harmonics'][1:9], precision=4)}",
        f"- The same ring with two {POCKET_DEG:.0f} deg sectors instead of the pocketed face: signal {sec['amp']*1e9:.1f} nWb/A, raw error {sec['raw_max']:.3f} deg", "",
        "![[geometry.png]] ![[flux.png]] ![[angle.png]] ![[raw_error.png]] ![[cal10_error.png]] ![[harmonics.png]]", "",
        "## What a dense LUT leaves when something moves", "",
        "Calibrated at nominal, then the condition changes. Residual is the change of the error curve, mean removed.", "",
        c04.md_table(("change", "residual_mech_deg", "signal_rel"), pert_rows), "",
        "![[perturbations.png]]", "",
        "## Main board as a finite disc", "",
        f"70 mm disc with a 30 mm hole ({n_plane} cells at {PLANE_CELL} mm) solved together with the target ({n_tg} cells), coils rotating: "
        f"signal {amp_f*1e9:.1f} nWb/A against {nom['amp']*1e9:.1f} with the infinite plane; error curve differs by {finite_vs_infinite:.4f} mech deg "
        f"(dense-LUT sense); transmit inductance change from the disc {dL_plane_f*1e6:.2f} uH against {(with_plane['L']-free['L'])*1e6:.2f} uH from the infinite plane.", "",
        "![[finite_plane.png]]", "",
        "## Mesh check", "",
        c04.md_table(("cell_mm", "n_cells", "signal_nWb_per_A", "raw_deg"), mesh_rows), "",
        "## Limits", "",
        "Perfect conductors (no eddy loss, so Q here counts copper loss only), no AGC, the main board as a uniform pour, no target",
        "tilt, no temperature. Layer stack 1.0 mm two-layer; via hops modelled as short vertical filaments.", "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines))
    print("\n".join(lines[:40]))
    print(f"done in {(time.time()-t0)/60:.1f} min -> {OUT / 'REPORT.md'}")


def _job(job):
    kind, arg = job
    if kind == "nom":
        return _nominal(arg)
    if kind == "pert":
        return _perturbed(arg)
    if kind == "finite":
        return _finite_plane()
    if kind == "mesh":
        return _mesh_check(arg)
    raise ValueError(kind)


if __name__ == "__main__":
    main()
