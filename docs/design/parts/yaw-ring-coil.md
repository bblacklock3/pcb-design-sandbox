# Yaw ring coil — layout constraints

Record: COL-COTS-0016 (LX34311) · Design: vault *Yaw-Absolute-Inductive* · Model:
`simulation/cases/07_yaw_ring_final.py` (configuration), `04`–`06` (the sweeps behind it),
`08`/`09` (field maps) at commit `30b0f88`

Constraints only; all values PROVISIONAL from the coil model until a STUDY record and a coupon
confirm them. Why the ring is where it is, and why the target is a pocketed face, is the vault page.

## Role

A separate two-layer ring board under the main board, centred on the beam axis, carrying the
transmit loop, two receive coils and the LX34311. Target: an aluminium frame face with two 60°
pockets. Absolute over 180° (N = 2 electrical periods).

## Geometry

| Item | Value |
|---|---|
| Board | two-layer, 1.0 mm, ⌀30 mm beam hole, about ⌀50 mm outside |
| Copper band | r 17 to 23 mm |
| Transmit | 4 turns per edge per layer: outer turns stepping inward from r 23, inner turns stepping outward from r 17, opposite senses; 8 mil trace, 6 mil gap; both layers |
| Receive | N = 2; r = 20 ± 1.28 mm × sin(2θ) and the cosine pattern advanced 45°; 6 mil; layer changes at every lobe extremum; 0.3 mm clearance to the transmit turns |
| Target | face with two 60° pockets, metal from r 15 to 25 mm (2 mm overhang each side of the band) |
| Airgap | 1.0 mm nominal from the copper face nearest the target |
| Main board behind | solid, uniform pour over the ring's footprint, 1.0 mm behind the ring board's back face (2.0 mm from the receive copper); no traces, pour gaps or parts inside r ≈ 27 mm on that face |
| Tank | about 3.8 µH at the operating point (with pour and target), Q ≈ 12 copper-only; 2 × 1470 pF C0G 50 V for 3 MHz |

## Placement and routing constraints

- The transmit turn count and trace width are set by the pour behind the board: fewer turns or
  narrower traces put the tank under the LX34311's 3 µH / Q 10 floors at 1 mm standoff.
- Receive via hops at the lobe extrema, short and paired; the closing hops at θ = 0 are the only
  non-periodic feature and should stay at one azimuth.
- IC, tank capacitors and connector outside the copper band on the outer rim, on the face away
  from the target.
- Standoff 1.0 mm is the clearance to the nearest copper: no part on the main board's underside
  taller than the standoff inside the ring's footprint.

## Gotchas

- Stack from coil face to main-board copper is 3.0 mm; the model's sensitivities (≤ 0.03° per
  0.25 mm of plane or gap movement through a dense LUT) assume the pour is uniform.
- The pocket angle is a sharp optimum at 60° (a third of the period); 45° or 75° pockets are
  several times more sensitive to gap change.
