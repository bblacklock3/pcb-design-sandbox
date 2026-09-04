"""Case 03 -- conducting back-plane behind the yaw ring.

The ring sensor of case 02 with (A) a uniform infinite conducting plane behind the
coil board at heights 1-12 mm (image method) and (B) a finite plane with a 30 mm
hole (cell solver, solved together with the target) at the same heights. Outputs: TX
inductance and Q vs height, receive offset (direct TX->RX coupling through the plane)
vs height, raw and calibrated linearity vs height.

Run:  python cases/03_backplane.py [--fast]
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indsim import biot, geometry as g, plot, sensor, sheet  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out" / "03_backplane"
FAST = "--fast" in sys.argv

# ------------------------------------------------------------------ parameters (mm)
R_IN, R_OUT = 17.0, 29.0
N_PERIODS = 2
TX_TURNS, TX_PITCH = 3, 0.3048
RX_AMP = 4.8
TRACE = 0.1524
TX_NTHETA, RX_NTHETA = 180, 360   # curve sampling; 720/360 changes flux by 0.2 %, costs 2.5x
LAYERS = (0.0, -1.0)         # two-layer 1.0 mm ring board; back face at z = -1.0
BOARD_BACK = -1.0
SECTOR_DEG, N_SECTORS = 60.0, 2
TARGET_R1, TARGET_R2 = 15.0, 31.0
GAP = 2.0
CELL = 0.6
C_TANK = 600e-12
HEIGHTS = (1.0, 2.0, 3.0, 5.0, 8.0, 12.0)          # plane below the board back face
PLANE_R_OUT, PLANE_HOLE, PLANE_CELL = 35.0, 15.0, 1.2   # finite plane: 70 mm disc, 30 mm hole
STEP = 15.0 if FAST else 7.5                       # angle step for linearity sweeps
FINITE_HEIGHTS = (1.0, 2.0, 3.0, 5.0, 8.0) if not FAST else (2.0, 5.0)


def build():
    rx_sin, rx_cos = g.ring_rx_pair(R_IN, R_OUT, N_PERIODS, LAYERS, amp_mm=RX_AMP, n_theta=RX_NTHETA, trace_mm=TRACE)
    tx = g.ring_tx(R_IN, R_OUT, TX_TURNS, TX_PITCH, LAYERS, n_theta=TX_NTHETA, trace_mm=TRACE)
    target = g.sector_sheet(TARGET_R1, TARGET_R2, SECTOR_DEG, N_SECTORS, CELL, GAP)
    return tx, rx_sin, rx_cos, target


def linearity_of(res, thetas):
    lin = sensor.linearity(thetas, res["angle"])
    ideal = lin["slope"] * thetas + lin["intercept"]
    err_raw = lin["residual"] / lin["slope"]
    cal = sensor.piecewise_correct(res["angle"], ideal, n_seg=10)
    err_cal = (cal - ideal) / lin["slope"]
    return float(np.abs(err_raw).max()), float(np.abs(err_cal).max())


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    tx, rx_sin, rx_cos, target = build()
    period = 360.0 / N_PERIODS
    thetas = np.arange(0.0, period + STEP / 2, STEP)
    tx_s = tx.segments()
    rx_s = {"sin": rx_sin.segments(), "cos": rx_cos.segments()}

    # -------- reference: no plane
    free = sensor.tank(tx, C_TANK)
    ref = sensor.run_sweep(tx, rx_sin, rx_cos, lambda th: target.rotated_deg(th), thetas)
    ref_raw, ref_cal = linearity_of(ref, thetas)
    print(f"no plane: L {free['L']*1e6:.2f} uH, Q {free['Q']:.0f}, amplitude {ref['amplitude'].mean()*1e9:.3g} nWb/A, "
          f"raw {ref_raw:.3f} deg, cal {ref_cal:.4f} deg")

    # -------- A. infinite plane, image method
    print("A. infinite plane")
    A = {k: [] for k in ("L", "Q", "f0", "offset", "amp", "raw", "cal")}
    for hgt in HEIGHTS:
        plane = g.ImagePlane(BOARD_BACK - hgt)
        tk = sensor.tank(tx, C_TANK, plane=plane)
        res = sensor.run_sweep(tx, rx_sin, rx_cos, lambda th: target.rotated_deg(th), thetas, plane=plane)
        raw, cal = linearity_of(res, thetas)
        offset = np.hypot(res["direct_sin"], res["direct_cos"])
        for k, v in zip(("L", "Q", "f0", "offset", "amp", "raw", "cal"),
                        (tk["L"], tk["Q"], tk["f0"], offset, res["amplitude"].mean(), raw, cal)):
            A[k].append(v)
        print(f"  h {hgt:4.1f} mm: L {tk['L']*1e6:.2f} uH  Q {tk['Q']:.0f}  f0 {tk['f0']/1e6:.2f} MHz  "
              f"offset {offset*1e9:.3g} nWb/A  amp {res['amplitude'].mean()*1e9:.3g}  raw {raw:.3f}  cal {cal:.4f} deg")

    # -------- B. finite plane with hole, cell solver, target and plane solved together
    print("B. finite plane with 30 mm hole")
    B = {k: [] for k in ("L", "Q", "f0", "offset", "amp", "raw", "cal")}
    for hgt in FINITE_HEIGHTS:
        plane_sheet = g.disc_sheet(PLANE_R_OUT, PLANE_CELL, BOARD_BACK - hgt, r_hole_mm=PLANE_HOLE)
        # tank and offset: plane alone, excited by the TX
        ps = sheet.SheetSolver(plane_sheet)
        psi = ps.respond(tx_s)
        dL = sheet.rx_flux(plane_sheet, psi, tx_s)
        L = free["L"] + dL
        f0 = 1 / (2 * np.pi * np.sqrt(L * C_TANK))
        R = biot.trace_resistance(tx.length(), tx.trace_width, 35e-6, f0)
        Q = 2 * np.pi * f0 * L / R
        off = np.hypot(*(biot.mutual_inductance(tx_s, rx_s[k]) + sheet.rx_flux(plane_sheet, psi, rx_s[k]) for k in ("sin", "cos")))
        # linearity: target + plane in one solve, coils rotate
        both = target.union(plane_sheet)
        res = sensor.run_sweep(tx, rx_sin, rx_cos, both, thetas, coil_pose=lambda th, c: c.rotated_deg(-th), log=print)
        raw, cal = linearity_of(res, thetas)
        for k, v in zip(("L", "Q", "f0", "offset", "amp", "raw", "cal"), (L, Q, f0, off, res["amplitude"].mean(), raw, cal)):
            B[k].append(v)
        print(f"  h {hgt:4.1f} mm ({plane_sheet.n} plane cells): L {L*1e6:.2f} uH  Q {Q:.0f}  f0 {f0/1e6:.2f} MHz  "
              f"offset {off*1e9:.3g} nWb/A  amp {res['amplitude'].mean()*1e9:.3g}  raw {raw:.3f}  cal {cal:.4f} deg")

    H, HF = np.array(HEIGHTS), np.array(FINITE_HEIGHTS)

    def plot_pair(key, title, ylabel, fname, scale=1.0, ref_val=None):
        fig, ax = plot.figure()
        ax.plot(H, np.array(A[key]) * scale, marker="o", label="Infinite Plane")
        ax.plot(HF, np.array(B[key]) * scale, marker="s", label="70 mm Disc With 30 mm Hole")
        if ref_val is not None:
            ax.axhline(ref_val * scale, color="0.5", ls="--", label="No Plane")
        plot.finish(fig, ax, title, "Plane Height Behind Board (mm)", ylabel, OUT / fname, legend=True)

    plot_pair("L", "Transmit Inductance Vs Plane Height", "Inductance (uH)", "L_vs_height.png", 1e6, free["L"])
    plot_pair("Q", "Transmit Q Vs Plane Height", "Q", "Q_vs_height.png", 1.0, free["Q"])
    plot_pair("f0", "Tank Frequency Vs Plane Height", "Frequency (MHz)", "f0_vs_height.png", 1e-6, free["f0"])
    plot_pair("offset", "Receive Offset Vs Plane Height", "Direct Coupling (nWb/A)", "offset_vs_height.png", 1e9,
              np.hypot(ref["direct_sin"], ref["direct_cos"]))
    plot_pair("amp", "Signal Amplitude Vs Plane Height", "Flux Amplitude (nWb/A)", "amplitude_vs_height.png", 1e9,
              ref["amplitude"].mean())
    plot_pair("raw", "Raw Angle Error Vs Plane Height", "Peak Angle Error (mech deg)", "raw_error_vs_height.png", 1.0, ref_raw)
    plot_pair("cal", "Calibrated Angle Error Vs Plane Height", "Peak Angle Error (mech deg)", "cal_error_vs_height.png", 1.0, ref_cal)

    plot.write_csv(OUT / "infinite_plane.csv", {"height_mm": H, "L_uH": np.array(A["L"]) * 1e6, "Q": A["Q"],
                   "f0_MHz": np.array(A["f0"]) * 1e-6, "offset_nWb_per_A": np.array(A["offset"]) * 1e9,
                   "amplitude_nWb_per_A": np.array(A["amp"]) * 1e9, "raw_err_deg": A["raw"], "cal_err_deg": A["cal"]})
    plot.write_csv(OUT / "finite_plane.csv", {"height_mm": HF, "L_uH": np.array(B["L"]) * 1e6, "Q": B["Q"],
                   "f0_MHz": np.array(B["f0"]) * 1e-6, "offset_nWb_per_A": np.array(B["offset"]) * 1e9,
                   "amplitude_nWb_per_A": np.array(B["amp"]) * 1e9, "raw_err_deg": B["raw"], "cal_err_deg": B["cal"]})

    lines = [
        "Case 03 back-plane -- summary",
        f"  ring as case 02; plane heights {HEIGHTS} mm behind the board back face (z = {BOARD_BACK} mm)",
        f"  no plane: L {free['L']*1e6:.2f} uH, Q {free['Q']:.0f}, f0 {free['f0']/1e6:.2f} MHz, cal error {ref_cal:.4f} deg",
        f"  Microchip rule of thumb: ground plane >= 3 x airgap = {3*GAP:.0f} mm from the sense coils "
        f"(coil design course); compare the offset/amp and error columns either side of {3*GAP:.0f} mm",
        "  infinite plane (image method):",
    ] + [f"    h {h:4.1f} mm: L {l*1e6:.2f} uH  Q {q:.0f}  f0 {f/1e6:.2f} MHz  offset/amp {o/a:.3f}  raw {r:.3f}  cal {c:.4f} deg"
         for h, l, q, f, o, a, r, c in zip(H, A["L"], A["Q"], A["f0"], A["offset"], A["amp"], A["raw"], A["cal"])] + [
        f"  finite plane, {PLANE_R_OUT*2:.0f} mm disc with {PLANE_HOLE*2:.0f} mm hole, cells {PLANE_CELL} mm (under-resolved below ~{3*PLANE_CELL:.0f} mm):",
    ] + [f"    h {h:4.1f} mm: L {l*1e6:.2f} uH  Q {q:.0f}  f0 {f/1e6:.2f} MHz  offset/amp {o/a:.3f}  raw {r:.3f}  cal {c:.4f} deg"
         for h, l, q, f, o, a, r, c in zip(HF, B["L"], B["Q"], B["f0"], B["offset"], B["amp"], B["raw"], B["cal"])] + [
        f"({time.time()-t0:.0f} s{', FAST' if FAST else ''})",
    ]
    text = "\n".join(lines)
    print(text)
    (OUT / "summary.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
