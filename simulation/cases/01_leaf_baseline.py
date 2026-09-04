"""Case 01 -- leaf baseline.

Parametric regeneration of the built single-leaf encoder coil (boards/MC3_ENC_V1.0,
Microchip-drawn) and a sweep of the 5 x 10 mm target over the stroke, checked against
the bench numbers in vault record COL-TEST-0005. Parameters at the top; figures and a
CSV land in simulation/out/01_leaf_baseline/. No design rationale here -- the vault
STUDY record that cites this script carries it.

Run:  python cases/01_leaf_baseline.py
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indsim import geometry as g, plot, sensor  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out" / "01_leaf_baseline"

# ------------------------------------------------------------------ parameters (mm)
LAMBDA = 15.0            # electrical period; RX copper spans 15.0 mm along travel on the board
LOBE_WIDTH = 7.6         # peak-to-peak lobe height across travel (2A)
SIN_LOBES = 2            # sine coil: two full lobes; cosine: half / full / half over the same span
TX_LEN, TX_WID = 18.0, 9.6   # outer TX turn, along x across travel (board: 18.0 x ~10.1 centreline)
TX_TURNS, TX_PITCH, TX_CORNER = 4, 0.3048, 1.0   # 4 turns per layer, 6 mil trace + 6 mil gap
TRACE = 0.1524           # 6 mil
# PROVISIONAL layer stack: the imported .kicad_pcb carries no stackup block. JLC-style
# 1.6 mm four-layer with 0.2 mm prepreg either side is assumed. z = 0 is the copper face
# nearest the target (B.Cu), target at +GAP.
Z_BCU, Z_IN2, Z_IN1, Z_FCU = 0.0, -0.2, -1.4, -1.6
RX_LAYERS = (Z_BCU, Z_IN2)   # receive coils on In2.Cu / B.Cu (board: thousands of 6 mil segments)
TX_LAYERS = (Z_IN1, Z_FCU)   # transmit on F.Cu / In1.Cu
TARGET_L, TARGET_W, GAP = 5.0, 10.0, 1.0   # aluminium flag: 5 along travel, 10 across, 1.0 mm airgap
CELL = 0.25              # sheet cell side; keep <= GAP / 3
STROKE = 10.5            # leaf travel (COL-PARAM-0002)
SWEEP_HALF, STEP = 7.5, 0.25   # sweep the flag centre over +/- 7.5 mm, i.e. the whole coil
C_TANK = 600e-12         # 2 x 1200 pF in series on the bench
COUNT_RESERVE = 0.0      # 0.10 for the Microchip library's 409..3685 convention


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rx_sin, rx_cos = g.linear_rx_pair(LAMBDA, LOBE_WIDTH, SIN_LOBES, RX_LAYERS, trace_mm=TRACE)
    tx = g.rect_tx(TX_LEN, TX_WID, TX_TURNS, TX_PITCH, TX_LAYERS, corner_r_mm=TX_CORNER, trace_mm=TRACE)
    target0 = g.rect_sheet(TARGET_L, TARGET_W, CELL, GAP)
    print(f"coils: TX {tx.turns()} turns / {len(tx.segments())} segs, RX {len(rx_sin.segments())} segs; "
          f"target {target0.n} cells of {CELL} mm")

    plot.geometry_plot([tx, rx_sin, rx_cos], [target0], "Leaf Coil And Target, Top View", OUT / "geometry.png")

    xs = np.arange(-SWEEP_HALF, SWEEP_HALF + STEP / 2, STEP)
    res = sensor.run_sweep(tx, rx_sin, rx_cos, lambda x: target0.translated_mm((x, 0.0, 0.0)), xs, log=print)
    ang_deg = np.degrees(res["angle"])
    cts = sensor.counts(res["angle"], COUNT_RESERVE)

    plot.line_plot(xs, {"Sin Coil": res["phi_sin"] * 1e9, "Cos Coil": res["phi_cos"] * 1e9},
                   "Receive Flux Vs Flag Position", "Flag Position (mm)", "Flux Per Ampere Of TX (nWb/A)",
                   OUT / "flux_vs_position.png")
    plot.line_plot(xs, {"Angle": ang_deg}, "Electrical Angle Vs Flag Position", "Flag Position (mm)",
                   "Electrical Angle (deg)", OUT / "angle_vs_position.png")
    plot.line_plot(xs, {"Counts": cts}, "Raw Counts Vs Flag Position", "Flag Position (mm)",
                   "Counts (12 bit per period)", OUT / "counts_vs_position.png")

    # -------- the stroke: centred window, then the best-placed window of the same length
    def window_report(lo):
        m = (xs >= lo - 1e-9) & (xs <= lo + STROKE + 1e-9)
        x, a = xs[m], res["angle"][m]
        lin = sensor.linearity(x, a)
        err_um = lin["residual"] / lin["slope"] * 1e3        # angle residual -> position (um)
        ideal = lin["slope"] * x + lin["intercept"]
        a_cal = sensor.piecewise_correct(a, ideal, n_seg=10)
        err_cal_um = (a_cal - ideal) / lin["slope"] * 1e3
        swept = a[-1] - a[0]
        mono = np.all(np.diff(a) > 0) or np.all(np.diff(a) < 0)
        return {
            "lo": lo, "x": x, "swept_deg": np.degrees(swept), "swept_counts": abs(swept) / (2 * np.pi) * 4096,
            "um_per_count": STROKE * 1e3 / (abs(swept) / (2 * np.pi) * 4096), "monotonic": bool(mono),
            "err_um": err_um, "err_cal_um": err_cal_um, "raw_max_um": np.abs(err_um).max(),
            "cal_max_um": np.abs(err_cal_um).max(), "angle": a, "ideal": ideal,
        }

    centred = window_report(-STROKE / 2)
    candidates = [window_report(lo) for lo in np.arange(-SWEEP_HALF, SWEEP_HALF - STROKE + 1e-9, STEP)]
    best = min(candidates, key=lambda w: w["raw_max_um"])

    for w, tag in ((centred, "centred"), (best, "best")):
        plot.line_plot(w["x"], {"Raw": w["err_um"], "After 10 Segment Correction": w["err_cal_um"]},
                       f"Linearity Error Over The Stroke ({tag.title()} Window)", "Flag Position (mm)",
                       "Position Error (um)", OUT / f"linearity_{tag}.png")
    # harmonic content is only meaningful over a full electrical period; the stroke covers
    # about half of one, so decompose the full +/- 7.5 mm sweep instead when it spans one
    span = res["angle"][-1] - res["angle"][0]
    if abs(span) >= 2 * np.pi:
        lin_full = sensor.linearity(xs, res["angle"])
        h = sensor.harmonics(res["angle"] - res["angle"][0], lin_full["residual"] / lin_full["slope"] * 1e3, n_max=6)
        h_text = f"error harmonics 1..6 over the full sweep (um, vs electrical angle): {np.array2string(h[1:], precision=1)}"
    else:
        h_text = f"error harmonics: not reported, sweep spans {np.degrees(abs(span)):.0f} deg < one period"

    tank = sensor.tank(tx, C_TANK)

    plot.write_csv(OUT / "sweep.csv", {
        "position_mm": xs, "counts": cts, "angle_deg": ang_deg,
        "phi_sin_nWb_per_A": res["phi_sin"] * 1e9, "phi_cos_nWb_per_A": res["phi_cos"] * 1e9,
    })

    lines = [
        "Case 01 leaf baseline -- summary",
        f"  lambda {LAMBDA} mm, lobes {LOBE_WIDTH} mm, TX {TX_TURNS}x{len(TX_LAYERS)} turns {TX_LEN}x{TX_WID} mm, "
        f"target {TARGET_L}x{TARGET_W} mm at {GAP} mm gap, cells {CELL} mm ({target0.n})",
        f"  layer stack PROVISIONAL: RX z = {RX_LAYERS} mm, TX z = {TX_LAYERS} mm",
        f"  direct TX->RX coupling: sin {res['direct_sin']*1e9:.3g} nWb/A, cos {res['direct_cos']*1e9:.3g} nWb/A "
        f"(signal amplitude {res['amplitude'].max()*1e9:.3g} nWb/A peak, {res['amplitude'].min()*1e9:.3g} min)",
        "",
        "Validation against COL-TEST-0005 (centred 10.5 mm window):",
        f"  swept electrical angle  {centred['swept_deg']:.1f} deg = {centred['swept_counts']:.0f} counts   "
        f"(measured ~202 deg / ~2300 counts; band +/-15 % = 172..232 deg)",
        f"  sensitivity             {centred['um_per_count']:.2f} um/count   (measured ~4.6)",
        f"  monotonic, single-valued {centred['monotonic']}",
        f"  linearity raw {centred['raw_max_um']:.0f} um, after 10-segment correction {centred['cal_max_um']:.1f} um",
        f"  {h_text}",
        f"Best-placed window starts at x = {best['lo']:+.2f} mm: swept {best['swept_deg']:.1f} deg, "
        f"raw {best['raw_max_um']:.0f} um, corrected {best['cal_max_um']:.1f} um",
        "",
        f"Transmit tank with C = {C_TANK*1e12:.0f} pF: L = {tank['L']*1e6:.2f} uH, R_ac = {tank['R']:.2f} ohm, "
        f"f0 = {tank['f0']/1e6:.2f} MHz, Q = {tank['Q']:.0f}   (LX34311 window 1-6 MHz, L > 3 uH, Q > 10)",
        f"  {'inside' if 1e6 <= tank['f0'] <= 6e6 else 'OUTSIDE'} the frequency window; "
        f"L {'>=' if tank['L'] >= 3e-6 else '<'} 3 uH",
        f"({time.time()-t0:.1f} s)",
    ]
    text = "\n".join(lines)
    print(text)
    (OUT / "summary.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
