"""Case 11 -- leaf coil variants against the tungsten leaf behind the flag.

Case 10 showed the tungsten leaf 3.5 mm behind the coil face compresses the swept angle
and makes the reading sensitive to the flag-to-leaf clearance. Two mechanisms: the
cosine coil's direct coupling to the transmit loop displaces the signal vector, so any
small extra offset costs a lot of angle; and the transmit field that leaks past the
5 mm flag's ends couples into the leaf. This case scores coil-side changes a board
re-order could carry, each against the same three perturbations read through a dense
LUT calibrated at nominal:

  - clearance: flag-to-leaf spacing 0.5 mm off nominal (a build tolerance)
  - rigid gap: flag and leaf together 0.25 mm further from the coil (assembly drift)
  - plain gap, no leaf, for reference

Variants: as built; TX with two counter-wound guard turns outside it; TX at the 19 mm
envelope; a 14 mm wide flag; 6 TX turns per layer (the inductance fix); and an
end-compensated cosine coil whose end half-lobes are sized to null its direct coupling
to the transmit loop, alone and with the 6-turn transmit coil.

Run:  python cases/11_leaf_coil_variants.py
Read: out/11_leaf_coil_variants/REPORT.md
"""
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from indsim import geometry as g, plot, sensor, sheet  # noqa: E402
from indsim.geometry import Coil, Loop  # noqa: E402
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

OUT = HERE.parent / "out" / "11_leaf_coil_variants"
LEAF_SIZE = c10.LEAF_SIZES["leaf 12 x 30 mm"]
DELTA_CLEAR, DELTA_GAP = 0.5, 0.25
STEP = 0.25
XS = np.arange(-c01.SWEEP_HALF, c01.SWEEP_HALF + STEP / 2, STEP)

VARIANTS = {
    "as built": dict(),
    "TX + 2 counter-wound guard turns": dict(guard=2),
    "TX 19 mm long (envelope max)": dict(tx_len=19.0),
    "flag 5 x 14 mm": dict(flag_w=14.0),
    "TX 6 turns per layer": dict(tx_turns=6),
    "cos ends x0.853 (null, 4 turns)": dict(cos_end=0.853),
    "6 turns + cos ends x0.872 (null)": dict(tx_turns=6, cos_end=0.872),
}


def build(v):
    tx_len = v.get("tx_len", c01.TX_LEN)
    tx_turns = v.get("tx_turns", c01.TX_TURNS)
    rs, rc = g.linear_rx_pair(c01.LAMBDA, c01.LOBE_WIDTH, c01.SIN_LOBES, c01.RX_LAYERS, trace_mm=c01.TRACE, cos_end_scale=v.get("cos_end", 1.0))
    tx = g.rect_tx(tx_len, c01.TX_WID, tx_turns, c01.TX_PITCH, c01.TX_LAYERS, corner_r_mm=c01.TX_CORNER, trace_mm=c01.TRACE)
    if v.get("guard"):
        # counter-wound turns just outside the transmit loop, on the same layers: the pair
        # looks like a closed magnetic circuit from a distance and leaks less to the leaf
        guard = g.rect_tx(tx_len + 2 * 0.6 + 2 * (v["guard"] - 1) * c01.TX_PITCH, c01.TX_WID + 2 * 0.6 + 2 * (v["guard"] - 1) * c01.TX_PITCH,
                          v["guard"], c01.TX_PITCH, c01.TX_LAYERS, corner_r_mm=c01.TX_CORNER + 0.6, sense=-1, trace_mm=c01.TRACE)
        tx = Coil("TX", tx.loops + guard.loops, tx.trace_width)
    flag = g.rect_sheet(c01.TARGET_L, v.get("flag_w", c01.TARGET_W), c01.CELL, c01.GAP)
    return tx, rs, rc, flag


def leaf(clear=c10.CLEAR, dz=0.0):
    return g.rect_sheet(LEAF_SIZE[0], LEAF_SIZE[1], c10.LEAF_CELL, c01.GAP + c10.FLAG_T + clear + dz)


def sweep(tx, rs, rc, target):
    return sensor.run_sweep(tx, rs, rc, lambda x: target.translated_mm((x, 0.0, 0.0)), XS)


def trimmed(res):
    """The same sweep read after the chip's SSIN/SCOS offset trims remove the coil's own
    direct TX->RX coupling (a constant, independent of gap)."""
    ang = np.unwrap(np.arctan2(res["phi_sin"] - res["direct_sin"], res["phi_cos"] - res["direct_cos"]))
    return dict(res, angle=ang)


def variant(item):
    name, v = item
    t0 = time.time()
    tx, rs, rc, flag = build(v)
    r_flag = sweep(tx, rs, rc, flag)
    m_flag = c10.stroke_metrics(r_flag, XS)
    r_nom = sweep(tx, rs, rc, flag.union(leaf()))
    m_nom = c10.stroke_metrics(r_nom, XS)
    # perturbations read through a dense LUT calibrated on the nominal (with leaf)
    d_clear = max(c10.dense_um(m_nom, sweep(tx, rs, rc, flag.union(leaf(c10.CLEAR + s * DELTA_CLEAR))), XS) for s in (-1, 1))
    d_gap = c10.dense_um(m_nom, sweep(tx, rs, rc, flag.union(leaf()).translated_mm((0, 0, DELTA_GAP))), XS)
    d_gap_noleaf = c10.dense_um(m_flag, sweep(tx, rs, rc, flag.translated_mm((0, 0, DELTA_GAP))), XS)
    # the same three perturbations with the direct coupling trimmed out (SSIN/SCOS registers)
    mt_flag = c10.stroke_metrics(trimmed(r_flag), XS)
    mt_nom = c10.stroke_metrics(trimmed(r_nom), XS)
    t_clear = max(c10.dense_um(mt_nom, trimmed(sweep(tx, rs, rc, flag.union(leaf(c10.CLEAR + s_ * DELTA_CLEAR)))), XS) for s_ in (-1, 1))
    t_gap = c10.dense_um(mt_nom, trimmed(sweep(tx, rs, rc, flag.union(leaf()).translated_mm((0, 0, DELTA_GAP)))), XS)
    t_gap_noleaf = c10.dense_um(mt_flag, trimmed(sweep(tx, rs, rc, flag.translated_mm((0, 0, DELTA_GAP)))), XS)
    tank = sensor.tank(tx, c01.C_TANK)
    return (name, tank["L"] * 1e6, tank["Q"], r_flag["direct_cos"] * 1e9, r_flag["amplitude"].max() * 1e9,
            m_flag["swept_deg"], m_nom["swept_deg"], m_nom["raw_um"], d_gap_noleaf, d_gap, d_clear,
            mt_flag["swept_deg"], mt_nom["swept_deg"], t_gap_noleaf, t_gap, t_clear, time.time() - t0)


HEADER = ("variant", "L_uH", "Q", "direct_cos_nWb_per_A", "signal_nWb_per_A", "swept_no_leaf_deg", "swept_with_leaf_deg",
          "raw_with_leaf_um", "gap+0.25_no_leaf_um", "gap+0.25_rigid_pair_um", "clearance+-0.5_um",
          "trim_swept_no_leaf_deg", "trim_swept_with_leaf_deg", "trim_gap+0.25_no_leaf_um", "trim_gap+0.25_rigid_um", "trim_clearance+-0.5_um", "seconds")


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = pmap(variant, list(VARIANTS.items()))
    for r in rows:
        print(f"{r[0]:34s} L {r[1]:.2f} Q {r[2]:.0f} | direct cos {r[3]:+.2f} sig {r[4]:.1f} | swept {r[5]:.0f}->{r[6]:.0f} raw {r[7]:.0f} | "
              f"dense: gap {r[8]:.0f} rigid {r[9]:.0f} clear {r[10]:.0f} | TRIMMED swept {r[11]:.0f}->{r[12]:.0f}, gap {r[13]:.0f} rigid {r[14]:.0f} clear {r[15]:.0f} um ({r[16]:.0f} s)")
    c04.write_rows_text(OUT / "variants.csv", HEADER, rows)
    lines = ["# Case 11 -- leaf coil variants against the tungsten leaf", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')}. Leaf coil as case 01 unless varied; flag {c01.TARGET_L} x W x {c10.FLAG_T} mm at {c01.GAP} mm; "
             f"tungsten leaf {LEAF_SIZE[1]} x {LEAF_SIZE[0]} mm, near face {c10.CLEAR} mm behind the flag. Tank at 2 x 1200 pF.", "",
             "The last three columns are what a dense LUT calibrated at nominal leaves (um of position over the stroke) when: the airgap grows",
             "0.25 mm with no leaf present; the flag and leaf move 0.25 mm further from the coil together (rigid assembly drift); the",
             "flag-to-leaf clearance is 0.5 mm off nominal (a build tolerance, absorbed by per-unit calibration).",
             "The trim_* columns repeat the metrics with the coil's own direct TX->RX coupling removed, as the LX34311 SSIN/SCOS offset",
             "registers do: that coupling is a constant while the flag signal scales with gap, so it is what turns gap change into error.", "",
             c04.md_table(HEADER, rows), ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))
    print(f"done in {(time.time()-t0)/60:.1f} min -> {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
