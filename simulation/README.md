# indsim — inductive position sensor model

A pure-Python (numpy, scipy, matplotlib) model of planar inductive position sensors of the
Microchip LX34xx kind: a transmit loop, two receive coils in spatial quadrature, and a
conductive target whose eddy currents modulate the coupling. Spec:
`docs/superpowers/specs/2026-09-03-inductive-sensor-simulation-design.md`.

Design reasoning does **not** live here. It lives in the Design Wiki; a vault STUDY record
points at a case script in this directory and carries the result. Scripts state parameters,
not why they were chosen.

## Model

- **Coils** are closed polylines of straight filaments, one `z` per layer, with a sense and
  a turn count. Fields use the analytic finite-segment Biot–Savart expression (`biot.py`).
  A receive coil is a single figure-8 loop: forward along `+A f(x)`, back along `-A f(x)`, so
  lobe senses alternate automatically and even lobe counts have zero net area. Both traces
  change layer at every lobe extremum (Microchip's routing rule, confirmed by the via columns
  on the encoder board), so each layer carries half of every lobe; the via hops are modelled
  as short vertical filaments. `layer_swap=False` gives the one-trace-per-layer variant.
- **Targets and finite planes** are perfectly conducting thin sheets meshed into square
  cells (`sheet.py`). Cell `j` carries a stream-function value `psi_j`, exactly a unit square
  current loop scaled by `psi_j`. The no-normal-flux condition collocated at cell centres
  gives `K psi = -Bz_source`, with `K[i, j]` the field at centre `i` from unit current round
  cell `j` (so the self term is the analytic square-loop centre field). `K` depends only on
  the cell layout, so it is LU-factorised once and reused for every pose. Receive flux from
  the sheet uses reciprocity: `sum_j psi_j Bz_rx(centre_j) a_j^2`.
- **Infinite planes** use the image method (mirror every filament, reverse the sense). With a
  plane present the cell loops get images too, so `K` is rebuilt per plane height.
- **Transmit tank**: Neumann self-inductance with the kernel regularised as
  `1/sqrt(r^2 + a^2)`, `a` = half the trace width, segments refined to length `a` (0.04 % on a
  circular loop against `mu0 R (ln(8R/a) - 2)`; 2 % on a rectangle against Grover). AC
  resistance from trace length, copper thickness and skin depth. Reported against the
  LX34311 window (1–6 MHz, L > 3 µH, Q > 10).
- **Sensor maths** (`sensor.py`): unwrapped `atan2` angle, 4096 counts per electrical period
  with an optional 10 % end reserve, linearity as the residual against a best-fit line, a
  10-segment continuous piecewise-linear correction mimicking the on-chip linearizer,
  harmonic content of the residual (only meaningful over a full period).

### Fast paths (all verified against the direct ones in `tests/test_fast.py`)

- **Toeplitz K build.** Cells sit on a regular lattice, so `K[i, j]` depends only on the
  index difference; one table of a few thousand field values fills the matrix by lookup
  (`sheet.build_k`, ~1 s for 7000 cells against ~30 s direct). Unions of different meshes
  use the lookup inside each mesh and direct evaluation between meshes. `build_k_direct`
  remains as the reference.
- **Polar field tables** (`tables.py`). For a ring sensor with the target moving in its own
  plane, each coil's Bz at the target height is tabulated once on an (r, theta) grid and
  interpolated at the moving cells: 0.07 s per pose against several seconds. Transmit
  n-gons use their exact 360/n period; receive traces use the electrical period, with the
  via hops (which break it) evaluated directly. 0.1 mm radial spacing holds 1e-3.
- **Process pool** (`parallel.pmap`) for independent study conditions; the case scripts
  take `--workers N`.
- The z-only Biot-Savart kernel `biot.bz` forms fewer arrays than `bfield`.

### Limits, stated plainly

- Perfect-conductor sheets: no eddy-loss phase term, no target thickness or resistivity.
  Fine above a few skin depths (copper at 3 MHz: 38 µm).
- No permeable materials, no AGC or oscillator amplitude prediction, no trace-width effects
  beyond the inductance regularisation, no exact copper import from `.kicad_pcb`.
- Collocation at cell centres: keep the cell side at or below a third of the distance to the
  nearest coil. The finite back-plane in case 03 is meshed at 1.2 mm and is under-resolved at
  heights below about 3 mm; the image-method curve is the reference there.
- The direct TX→RX coupling is reported and *included* in the receive flux. It is exactly
  zero for a coil with zero net area under a uniform field and is not zero under a real,
  non-uniform TX field; that is what compresses the swept angle in case 01.
- The layer stack of the imported encoder board is not in its `.kicad_pcb`; case 01 assumes
  a JLC-style 1.6 mm four-layer stack and marks it PROVISIONAL.

### Vendor rule of thumb the model can check

Microchip's inductive-sensor coil design course (video series, viewed 2026-09-03) states that
a ground plane must be at least **three times the airgap** away from the sense coils to keep
static influence on the target reading small, alongside the tank requirements (L >= 3 uH,
Q >= 10, OSC1/OSC2 in antiphase, primary length = sensor length plus a margin for magnetic
end effects). Case 03 sweeps a back-plane through and beyond that distance so the rule can be
checked against the model for the ring geometry; the vault yaw design page carries the rule
and its consequence for the ring-board standoff.

## Running

```
cd simulation
python -m pytest                      # ~7 s
python cases/01_leaf_baseline.py      # ~6 s
python cases/02_yaw_ring.py [--fast]  # minutes; --fast for a smoke run
python cases/03_backplane.py [--fast]
```

Each case has its parameters at the top, prints a summary, and writes ASCII-labelled PNG
figures (one plot per figure, grid alpha 0.3), CSVs and `summary.txt` to
`out/<case>/`. `out/` is gitignored.

## Validation (case 01 against COL-TEST-0005)

| Quantity | Measured | Model | Band |
|---|---|---|---|
| Electrical angle over the 10.5 mm stroke | ~202 deg (~2300 counts) | 198.5 deg (2258 counts) | 172–232 deg |
| Position sensitivity | ~4.6 um/count | 4.65 um/count | consistent |
| Monotonic, single-valued | yes | yes | required |
| Tank frequency, 600 pF effective | inside 1–6 MHz | 4.83 MHz (L = 1.81 uH) | required |

The model also puts the transmit inductance below the 3 µH the LX34311 recommends, which is
consistent with the oscillator-undervoltage diagnostic seen on the bench.

## Handing results to the vault

1. Run the case; copy the figures you need from `out/<case>/` into the project's
   `09 Assets/` renamed `<STUDY-ID> <Descriptive Name>.png`.
2. In the STUDY record: parameters as an inputs table, results in the body, `tool` =
   `indsim`, `model_ref` = the script path plus the git commit hash
   (`git rev-parse --short HEAD`), `bracketed_by` = the hand CALC (the transformer-ratio
   area model from Microchip's coil course is the natural bracket for signal amplitude).
3. A materially different analysis is a new script or a parameter change committed under a
   new record ID, never a silent edit of a script a sealed record points at.

## Layout

```
indsim/geometry.py   Loop, Coil, Sheet, ImagePlane; linear_rx_pair, rect_tx, ring_rx_pair,
                     ring_tx, rect_sheet, sector_sheet, disc_sheet, union
indsim/biot.py       bfield, mutual_inductance, self_inductance, mirror, trace_resistance
indsim/sheet.py      build_k, SheetSolver, rx_flux
indsim/sensor.py     electrical_angle, counts, linearity, piecewise_correct, harmonics,
                     run_sweep, tank
indsim/plot.py       vault plot conventions
cases/               01_leaf_baseline, 02_yaw_ring, 03_backplane
tests/               pytest, one file per module
```
