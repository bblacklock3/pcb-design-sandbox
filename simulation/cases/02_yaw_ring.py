"""Case 02 -- yaw ring.

Parametric N-period ring coil for the yaw axis (vault design Yaw-Absolute-Inductive)
with a two-sector target, swept over angle, sector angle, airgap and eccentricity.
Parameters at the top; figures and CSVs land in simulation/out/02_yaw_ring/. Design
rationale stays in the vault.

Run:  python cases/02_yaw_ring.py            (full sweeps, several minutes)
      python cases/02_yaw_ring.py --fast     (coarser steps for a smoke run)
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indsim import geometry as g, plot, sensor  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out" / "02_yaw_ring"
FAST = "--fast" in sys.argv

# ------------------------------------------------------------------ parameters (mm)
R_IN, R_OUT = 17.0, 29.0     # coil band: 30 mm beam hole board, 60 mm outer
N_PERIODS = 2                # 2 -> 180 deg absolute range; 3 and 4 also run
TX_TURNS, TX_PITCH = 3, 0.3048   # per edge per layer: 3 at r_out stepping in, 3 at r_in stepping out
RX_AMP = 4.8                 # receive lobe amplitude A; band r_m +/- A inside the TX turns
TRACE = 0.1524
TX_NTHETA, RX_NTHETA = 180, 360   # curve sampling; 720/360 changes flux by 0.2 %, costs 2.5x
# two-layer 1.0 mm ring board; z = 0 is the copper face nearest the target
LAYERS = (0.0, -1.0)
SECTOR_DEG, N_SECTORS = 60.0, 2
TARGET_R1, TARGET_R2 = 15.0, 31.0   # radial overhang 2 mm each side of the coil band
GAP = 2.0
CELL = 0.6                   # <= GAP / 3
C_TANK = 600e-12

ANGLE_STEP = 5.0 if FAST else 2.0          # main sweep over one electrical period
SUB_STEP = 10.0 if FAST else 5.0           # secondary sweeps
SECTOR_SWEEP = (30.0, 45.0, 60.0, 75.0, 90.0)
GAP_SWEEP = (1.0, 2.0, 3.0)
ECC_SWEEP = (0.0, 0.1, 0.2, 0.3)


def build_coils(n_periods=N_PERIODS):
    rx_sin, rx_cos = g.ring_rx_pair(R_IN, R_OUT, n_periods, LAYERS, amp_mm=RX_AMP, n_theta=RX_NTHETA, trace_mm=TRACE)
    tx = g.ring_tx(R_IN, R_OUT, TX_TURNS, TX_PITCH, LAYERS, n_theta=TX_NTHETA, trace_mm=TRACE)
    return tx, rx_sin, rx_cos


def sweep(tx, rx_sin, rx_cos, target, step, n_periods=N_PERIODS, ecc_mm=0.0, periods=1, log=None):
    """Rotate the target through `periods` electrical periods. Returns the run_sweep dict
    plus mechanical-degree linearity, raw and after 10-segment correction."""
    period = 360.0 / n_periods
    thetas = np.arange(0.0, periods * period + step / 2, step)

    def place(th):
        return target.rotated_deg(th).translated_mm((ecc_mm, 0.0, 0.0))

    res = sensor.run_sweep(tx, rx_sin, rx_cos, place, thetas, log=log)
    lin = sensor.linearity(thetas, res["angle"])
    ideal = lin["slope"] * thetas + lin["intercept"]
    err_raw = lin["residual"] / lin["slope"]  # electrical residual -> mechanical degrees
    cal = sensor.piecewise_correct(res["angle"], ideal, n_seg=10)
    err_cal = (cal - ideal) / lin["slope"]
    res.update(theta=thetas, err_raw_deg=err_raw, err_cal_deg=err_cal, slope=lin["slope"], ideal=ideal,
               raw_max=float(np.abs(err_raw).max()), cal_max=float(np.abs(err_cal).max()))
    return res


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    tx, rx_sin, rx_cos = build_coils()
    target = g.sector_sheet(TARGET_R1, TARGET_R2, SECTOR_DEG, N_SECTORS, CELL, GAP)
    print(f"ring N={N_PERIODS}: TX {tx.turns()} turns, RX {len(rx_sin.segments())} segs; target {target.n} cells")
    plot.geometry_plot([tx, rx_sin, rx_cos], [target], f"Ring Coil N = {N_PERIODS} And Two Sector Target", OUT / "geometry.png")

    # -------- A. main angle sweep
    print("A. angle sweep")
    main_res = sweep(tx, rx_sin, rx_cos, target, ANGLE_STEP, log=print)
    th = main_res["theta"]
    plot.line_plot(th, {"Sin Coil": main_res["phi_sin"] * 1e9, "Cos Coil": main_res["phi_cos"] * 1e9},
                   "Receive Flux Vs Target Angle", "Target Angle (deg)", "Flux Per Ampere Of TX (nWb/A)",
                   OUT / "flux_vs_angle.png")
    plot.line_plot(th, {"Electrical Angle": np.degrees(main_res["angle"])}, "Electrical Angle Vs Target Angle",
                   "Target Angle (deg)", "Electrical Angle (deg)", OUT / "angle_vs_angle.png")
    plot.line_plot(th, {"Raw": main_res["err_raw_deg"], "After 10 Segment Correction": main_res["err_cal_deg"]},
                   "Angle Error Over One Period", "Target Angle (deg)", "Angle Error (mech deg)",
                   OUT / "linearity.png")
    h = sensor.harmonics(main_res["ideal"] - main_res["ideal"][0], main_res["err_raw_deg"], n_max=6)
    plot.write_csv(OUT / "angle_sweep.csv", {
        "target_angle_deg": th, "electrical_angle_deg": np.degrees(main_res["angle"]), "counts": main_res["counts"],
        "phi_sin_nWb_per_A": main_res["phi_sin"] * 1e9, "phi_cos_nWb_per_A": main_res["phi_cos"] * 1e9,
        "err_raw_mech_deg": main_res["err_raw_deg"], "err_cal_mech_deg": main_res["err_cal_deg"],
    })

    # -------- B. sector angle
    print("B. sector angle sweep")
    amp_s, raw_s, cal_s = [], [], []
    for sd in SECTOR_SWEEP:
        tg = g.sector_sheet(TARGET_R1, TARGET_R2, sd, N_SECTORS, CELL, GAP)
        r = sweep(tx, rx_sin, rx_cos, tg, SUB_STEP)
        amp_s.append(r["amplitude"].mean() * 1e9); raw_s.append(r["raw_max"]); cal_s.append(r["cal_max"])
        print(f"  sector {sd:.0f} deg: amplitude {amp_s[-1]:.3g} nWb/A, raw {raw_s[-1]:.3f} deg, cal {cal_s[-1]:.4f} deg")
    plot.line_plot(SECTOR_SWEEP, {"Amplitude": amp_s}, "Signal Amplitude Vs Sector Angle", "Sector Angle (deg)",
                   "Flux Amplitude (nWb/A)", OUT / "amplitude_vs_sector.png", marker="o")
    plot.line_plot(SECTOR_SWEEP, {"Raw": raw_s, "After 10 Segment Correction": cal_s}, "Angle Error Vs Sector Angle",
                   "Sector Angle (deg)", "Peak Angle Error (mech deg)", OUT / "linearity_vs_sector.png", marker="o")

    # -------- C. airgap
    print("C. gap sweep")
    amp_g, raw_g, cal_g = [], [], []
    for gp in GAP_SWEEP:
        tg = g.sector_sheet(TARGET_R1, TARGET_R2, SECTOR_DEG, N_SECTORS, min(CELL, gp / 3), gp)
        r = sweep(tx, rx_sin, rx_cos, tg, SUB_STEP)
        amp_g.append(r["amplitude"].mean() * 1e9); raw_g.append(r["raw_max"]); cal_g.append(r["cal_max"])
        print(f"  gap {gp:.1f} mm: amplitude {amp_g[-1]:.3g} nWb/A, raw {raw_g[-1]:.3f} deg, cal {cal_g[-1]:.4f} deg")
    plot.line_plot(GAP_SWEEP, {"Amplitude": amp_g}, "Signal Amplitude Vs Airgap", "Airgap (mm)",
                   "Flux Amplitude (nWb/A)", OUT / "amplitude_vs_gap.png", marker="o")
    plot.line_plot(GAP_SWEEP, {"Raw": raw_g, "After 10 Segment Correction": cal_g}, "Angle Error Vs Airgap",
                   "Airgap (mm)", "Peak Angle Error (mech deg)", OUT / "linearity_vs_gap.png", marker="o")

    # -------- D. eccentricity: a once-per-turn term needs a full mechanical turn, so
    # sweep all N electrical periods and decompose the error against mechanical angle
    print("D. eccentricity sweep")
    h1, raw_e, cal_e = [], [], []
    for e in ECC_SWEEP:
        r = sweep(tx, rx_sin, rx_cos, target, SUB_STEP, ecc_mm=e, periods=N_PERIODS)
        hh = sensor.harmonics(np.radians(r["theta"]), r["err_raw_deg"], n_max=4)  # vs mechanical angle
        h1.append(hh[1]); raw_e.append(r["raw_max"]); cal_e.append(r["cal_max"])
        print(f"  ecc {e:.2f} mm: once-per-turn error {h1[-1]:.4f} deg, raw {raw_e[-1]:.3f} deg, cal {cal_e[-1]:.4f} deg")
    plot.line_plot(ECC_SWEEP, {"First Harmonic": h1}, "Once Per Turn Error Vs Eccentricity", "Eccentricity (mm)",
                   "Error Amplitude (mech deg)", OUT / "first_harmonic_vs_eccentricity.png", marker="o")
    plot.line_plot(ECC_SWEEP, {"Raw": raw_e, "After 10 Segment Correction": cal_e}, "Angle Error Vs Eccentricity",
                   "Eccentricity (mm)", "Peak Angle Error (mech deg)", OUT / "linearity_vs_eccentricity.png", marker="o")

    tank = sensor.tank(tx, C_TANK)
    lines = [
        "Case 02 yaw ring -- summary",
        f"  r {R_IN}-{R_OUT} mm, N = {N_PERIODS}, TX {TX_TURNS} turns per edge per layer ({tx.turns()} loops), "
        f"RX amplitude {RX_AMP} mm, layers z = {LAYERS} mm",
        f"  target {N_SECTORS} x {SECTOR_DEG:.0f} deg sectors r {TARGET_R1}-{TARGET_R2} mm at {GAP} mm gap, "
        f"cells {CELL} mm ({target.n})",
        f"  direct TX->RX: sin {main_res['direct_sin']*1e9:.3g} nWb/A, cos {main_res['direct_cos']*1e9:.3g} nWb/A; "
        f"signal amplitude {main_res['amplitude'].mean()*1e9:.3g} nWb/A",
        f"  electrical span per period {np.degrees(main_res['angle'][-1]-main_res['angle'][0]):.1f} deg "
        f"(ideal 360), monotonic {bool(np.all(np.diff(main_res['angle']) > 0))}",
        f"  angle error raw {main_res['raw_max']:.3f} mech deg, after 10-segment correction {main_res['cal_max']:.4f} mech deg",
        f"  raw error harmonics 1..6 of electrical angle (mech deg): {np.array2string(h[1:], precision=4)}",
        f"  sector sweep {SECTOR_SWEEP}: amplitude {np.array2string(np.array(amp_s), precision=3)} nWb/A, "
        f"cal error {np.array2string(np.array(cal_s), precision=4)} deg",
        f"  gap sweep {GAP_SWEEP}: amplitude {np.array2string(np.array(amp_g), precision=3)} nWb/A, "
        f"cal error {np.array2string(np.array(cal_g), precision=4)} deg",
        f"  eccentricity {ECC_SWEEP}: once-per-turn error {np.array2string(np.array(h1), precision=4)} deg",
        f"Transmit tank with C = {C_TANK*1e12:.0f} pF: L = {tank['L']*1e6:.2f} uH, R_ac = {tank['R']:.2f} ohm, "
        f"f0 = {tank['f0']/1e6:.2f} MHz, Q = {tank['Q']:.0f}   (LX34311 window 1-6 MHz, L > 3 uH, Q > 10)",
        f"({time.time()-t0:.0f} s{', FAST' if FAST else ''})",
    ]
    text = "\n".join(lines)
    print(text)
    (OUT / "summary.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
