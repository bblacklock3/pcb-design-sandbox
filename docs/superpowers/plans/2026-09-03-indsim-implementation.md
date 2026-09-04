# Inductive Sensor Simulation Library — Implementation Plan

Spec: `docs/superpowers/specs/2026-09-03-inductive-sensor-simulation-design.md`
Branch: `feature/indsim`. Tests first, one module at a time, commit after each module passes.

## Review notes on the spec (decisions taken while implementing)

1. **K matrix uses the exact square-loop field for every pair, not a dipole.** A cell with
   stream-function value `psi_j` is exactly a unit square current loop scaled by `psi_j`
   (piecewise-constant stream function ⇒ boundary currents). Evaluating the four-segment
   Biot–Savart field at every other cell's centre is consistent for near and far pairs and
   gives the spec's self term `2*sqrt(2)*mu0/(pi*a)` automatically at `i == j`. No special
   case needed.
2. **K depends only on the sheet's own geometry**, so it is factorised once (LU) per sheet and
   reused for every pose in a sweep; only the source field column changes per pose.
3. **Mesh rule:** cell side `a <= gap/3` for the target; the finite back-plane at 1 mm height
   is under-resolved at `a = 1 mm` and the README says so.
4. **Layer stack is not in the imported `.kicad_pcb`** (Altium import, no stackup block).
   Case 01 assumes a JLC-style 1.6 mm four-layer stack (prepreg 0.2 mm each side) and marks it
   PROVISIONAL. Measured from the board: TX on F.Cu/In1.Cu, 18.0 mm along travel; RX on
   In2.Cu/B.Cu, 15.0 mm along travel (= lambda).
5. **Validation expectation:** an ideal 15 mm period over 10.5 mm of travel is 252 deg of
   electrical angle; the bench saw about 202 deg. The model result is reported against the
   spec's ±15 % band; missing it is information about the target/end effects, not a code
   defect.
6. Regularised Neumann (`1/sqrt(r^2 + a^2)`) for self-inductance; tested against
   `mu0*R*(ln(8R/a) - 2)` within 5 %.

## Tasks

- [x] 1. Skeleton: `simulation/indsim/__init__.py`, `.gitignore` entry for `simulation/out/`, `pytest.ini`/`conftest.py` so `pytest simulation/tests` works.
- [x] 2. `test_biot.py` → `biot.py`: `segment_bfield`, `polyline_bfield`, `mutual_inductance`, `self_inductance`, `mirror_points`. Tests: loop centre field, long wire field, coaxial loops mutual vs elliptic-integral formula, self-inductance of a circular loop.
- [x] 3. `test_geometry.py` → `geometry.py`: `Loop`, `Coil`, `Sheet`, `ImagePlane`; generators `linear_rx_pair`, `rect_tx`, `ring_rx_pair`, `ring_tx`, `rect_sheet`, `sector_sheet`, `disc_sheet`, `plane_sheet`. Tests: zero net signed area, turn count/sense, mm↔m round trip, sheet cell count/area.
- [x] 4. `test_sheet.py` → `sheet.py`: `build_k`, `SheetSolver` (LU), `solve_psi`, `rx_flux_from_sheet`. Tests: K symmetric, distant sheet changes nothing, big sheet reproduces image method within 5 %.
- [x] 5. `test_sensor.py` → `sensor.py`: `electrical_angle`, `counts`, `linearity`, `piecewise_correct`, `harmonics`, `run_sweep`. Tests: ideal sin/cos → zero error; 10-segment fit removes known piecewise error; counts scale.
- [x] 6. `plot.py`: vault conventions (ASCII check, Title Case helper, grid alpha 0.3, one plot per figure, tight_layout, PNG).
- [x] 7. Cases `01_leaf_baseline.py`, `02_yaw_ring.py`, `03_backplane.py`; run each; check outputs land in `out/`.
- [x] 8. `simulation/README.md`: model, limits, run instructions, STUDY handoff.
- [x] 9. Full test run, commit, report validation numbers.
