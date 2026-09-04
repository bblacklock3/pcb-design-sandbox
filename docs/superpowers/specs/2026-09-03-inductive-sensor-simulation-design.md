# Inductive Sensor Simulation Library — Design

Date: 2026-09-03
Status: approved in discussion, spec for review
Location: `simulation/` in this repo

## Purpose

A reproducible, pure-Python model of planar inductive position sensors of the Microchip LX34xx kind: a transmit loop, two receive coils in spatial quadrature, and a conductive target whose eddy currents modulate the coupling. It exists to

1. reproduce what the built single-leaf encoder board (`boards/MC3_ENC_V1.0`, Microchip-drawn, tested in vault record `COL-TEST-0005`) does, so the model earns trust against hardware,
2. iterate yaw-axis ring coil options (vault design `Yaw-Absolute-Inductive`) before any board is drawn, and
3. quantify how nearby conductors — chiefly the main board behind a ring sensor — distort the reading as a function of spacing.

The vault (`C:\Users\newte\Documents\Design Wiki`) remains the authority for design reasoning. This library is the reproduction aid a vault STUDY record points at; the record captures the result and carries the figures under its own ID.

## Scope

In scope, in three rounds:

- **Round 1 — leaf baseline.** Parametric regeneration of the leaf coil and validation against measured behavior.
- **Round 2 — yaw ring.** Parametric N-period ring coils with sector targets; sweeps over period count, radii, sector angle, airgap and eccentricity.
- **Round 3 — disturbances.** Conductive planes and finite sheets behind or beside the coil, swept in height; the main board approximated as a plane with a central hole.

Out of scope for this spec (later rounds, separate specs): importing exact copper from `.kicad_pcb` files; ferrite or other permeable materials; finite-conductivity (phase/loss) targets; the LX34311's AGC, filter and quantization behavior beyond a ratiometric 12-bit angle.

## Physics Model

Quasi-static magnetics. All conductors are filaments or perfectly conducting thin sheets; frequency enters only through the tank and loss estimates, never through position.

**Coils** are polylines of straight filaments, each polyline at a fixed `z` (layer) with a sense (+1/−1) and a turn count. Fields come from the analytic finite-segment Biot–Savart expression, vectorized over segments and field points.

**Targets and finite disturbances** are thin sheets meshed into square cells of side `a`. Each cell carries an unknown stream-function value `psi_j`, equivalent to a magnetic dipole of moment `psi_j * a^2` normal to the sheet (a dipole layer). The perfect-conductor condition is that no normal flux threads the sheet:

    sum_j K[i, j] * psi[j] + Bz_source[i] = 0     for every cell i

where `K[i, j]` is the normal field at cell `i` from a unit dipole at cell `j`, and the self term `K[i, i]` is the exact center field of a square current loop of side `a` (`2*sqrt(2)*mu0 / (pi*a)` per unit current). Dense solve; typical sizes 500–3000 cells.

**Receive flux** by reciprocity: the flux a receive coil sees from the sheet is `sum_j psi_j * Bz_RX(j) * a^2`, where `Bz_RX(j)` is the field at cell `j` from unit current in that receive coil. Total receive flux per pose is the direct TX→RX mutual plus the sheet term. The direct term should be near zero for a well-balanced differential coil and is reported as a diagnostic.

**Infinite planes** (a uniform back-plane at height `h`) use the image method: mirror every filament at `2h` with reversed sense. This is exact for an infinite perfect plane and is the fast path for round 3; a finite sheet with a hole uses the cell solver.

**Transmit tank.** Self-inductance of the TX polyline set by Neumann's double integral over filaments with a wire-radius regularization equal to half the trace width, plus the image-plane correction when a plane is present. AC resistance from trace length, copper thickness and skin depth at the operating frequency. Reported against the LX34311 window: 1–6 MHz, L > 3 µH recommended, Q > 10, given the tank capacitance.

Known limits, stated in the README: perfect-conductor targets (no eddy-loss phase term), no permeable materials, no AGC or oscillator amplitude prediction, no trace-width effects beyond the inductance regularization.

## Sensor Model

For a pose sweep the model returns `Phi_sin(pose)` and `Phi_cos(pose)`. Electrical angle is `atan2(Phi_sin, Phi_cos)`. Counts are `4096 * angle / (2*pi)` over one electrical period, with an optional 10 % end reserve to match the Microchip library convention (409–3685). Linearity error is the residual against a best-fit line over the stated stroke or range, reported raw and after an optional 10-segment piecewise-linear correction that mimics the on-chip linearizer. The residual's harmonic content (in electrical angle) is reported to guide target sizing.

Amplitude normalization is ratiometric — no AGC model. Absolute flux values are still exposed so relative signal strength between geometries can be compared.

## Geometry Generators

- **Linear sin/cos coil.** Period `lambda`, lobe amplitude `A`, lobe count for the sine coil (even), cosine coil as the same pattern shifted `lambda/4` with half-lobe ends so its net area is zero; trace crossovers are ignored (each coil is an ideal planar loop on its layer set). TX as a rounded rectangle of `n` turns per layer at given pitch on a given list of layer `z` values.
- **Ring coil.** Inner and outer radius, `N` periods. Receive lobes `r(theta) = r_m ± A*sin(N*theta)` with the cosine coil shifted by a quarter period. TX as `n` concentric turns near `r_out` and `n` near `r_in` in opposite sense, so the drive flux is confined to the annulus.
- **Targets.** Rectangle (leaf flag); annular sector or a set of `k` identical sectors (ring target); disc with a central hole and optional slots (library-style targets). All as sheets at a `z` (airgap) with optional in-plane offset (eccentricity) and rotation.
- **Disturbances.** Infinite plane at `z`; finite plane (rectangle or disc) with an optional central hole at `z`.

Every generator takes SI units in millimeters at the API boundary and converts internally to meters; every geometry object can render itself to a top-view figure for a visual check.

## Package Layout

    simulation/
      README.md            model, limits, how to run a case, how a STUDY cites it
      indsim/
        __init__.py
        geometry.py        Coil, Sheet, ImagePlane dataclasses and the generators above
        biot.py            segment field, dipole field, mutual and self inductance, images
        sheet.py           cell meshing, K matrix, solve, receive flux by reciprocity
        sensor.py          pose sweep, atan2, counts, linearity, 10-segment fit, harmonics
        plot.py            vault plot conventions (ASCII text, Title Case, units, one plot per figure, grid alpha 0.3)
      cases/
        01_leaf_baseline.py
        02_yaw_ring.py
        03_backplane.py
      tests/
        test_biot.py
        test_sheet.py
        test_geometry.py
        test_sensor.py
      out/                 generated figures and CSVs, gitignored

Dependencies: numpy, scipy (dense solve, optional), matplotlib, pytest. Nothing else.

## Case Scripts

Each case is a plain script with its parameters at the top, writes figures and a CSV of the sweep to `out/`, and prints a short summary. Figures obey the vault's plot rules so they can be copied into a STUDY under that record's ID without editing.

**01_leaf_baseline.** The leaf coil from its extracted parameters: lambda 15.0 mm, lobe width 7.6 mm, sine 2 lobes, cosine half/full/half, TX 4 turns on each of two layers at 6 mil trace and gap, outer 9.6 × 18.0 mm, layer stack from the 1.6 mm four-layer board; target 5 × 10 × 1 mm aluminum at 1.0 mm gap; sweep 10.5 mm of travel. Outputs: sin/cos flux vs position, electrical angle vs position, counts vs position, linearity error raw and calibrated, TX inductance and tank frequency at 2 × 1200 pF.

**02_yaw_ring.** Ring coil at r 17–29 mm (⌀30 mm hole board, ⌀60 mm outer), N = 2 default with N = 3, 4 available; two opposite sectors of configurable angle (default 60°) with radial overhang; gap 2.0 mm default. Sweeps: angle over one period; sector angle 30–90°; gap 1–3 mm; eccentricity 0–0.3 mm. Outputs: signal amplitude, linearity raw and calibrated, first-harmonic error vs eccentricity, tank estimate.

**03_backplane.** The ring sensor with a uniform conducting plane behind the coil at heights 1–12 mm (image method), then a finite plane with a ⌀30 mm hole (cell solver) at the same heights. Outputs: TX inductance and Q vs height, receive offset (direct TX→RX coupling) vs height, calibrated linearity vs height.

## Validation Targets

Round 1 must reproduce, within the stated tolerance, from `COL-TEST-0005`:

| Quantity | Measured | Tolerance for "reproduced" |
|---|---|---|
| Electrical angle swept over the 10.5 mm stroke | about 56 % of a period (≈ 202°, 2300 of 4096 counts) | ±15 % of the swept angle |
| Position sensitivity | ≈ 4.6 µm per count | consistent with the above |
| Monotonic, single-valued over the stroke | yes | required |
| Tank frequency with 2 × 1200 pF (600 pF effective) | inside 1–6 MHz | required |

A full-stroke camera sweep, when taken, replaces this table with a curve comparison; the case script writes the model curve in a form that comparison can read (CSV: position mm, counts).

## Testing

Tests are written before the code they test.

- `test_biot`: circular loop center field equals `mu0*I/(2R)`; long straight segment field equals `mu0*I/(2*pi*d)` far from its ends; coaxial circular loops' mutual inductance matches the elliptic-integral formula; self-inductance of a circular loop matches `mu0*R*(ln(8R/a) - 2)` within a few percent.
- `test_sheet`: a large square sheet under a small loop reproduces the image-method flux change within 5 %; reciprocity — the K matrix is symmetric; a sheet far from the coil changes nothing.
- `test_geometry`: generated receive coils enclose zero net signed area (sine and cosine, linear and ring); TX turns have the declared count and sense; unit conversions round-trip.
- `test_sensor`: an ideal sinusoidal flux pair yields zero linearity error; the 10-segment fit removes a known piecewise error; counts scale to 4096 per period.

## Outputs and the Vault

Figures and CSVs land in `simulation/out/` and are not committed. A vault STUDY record for each case copies its figures into the project's `09 Assets/` under the record's ID, states the parameters and results in the record body, and sets `model_ref` to the script path and the git commit hash. The library's README documents this handoff. Scripts here carry no design rationale — that stays in the vault, per this repo's `CLAUDE.md`.

## Non-Goals

No GUI. No KiCad round-trip (import or export) in this spec. No attempt to predict oscillator amplitude or the OSC-undervoltage diagnostic beyond L and Q. No optimization loop — sweeps only; choosing values is the engineer's job in the vault.
