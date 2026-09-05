# LX34311 leaf coil — layout constraints

Record: COL-COTS-0016 (LX34311) · Design: vault *Leaf-Absolute-Inductive* · Build: vault *Inductive-Encoder-01*
· Model: `simulation/cases/01_leaf_baseline.py`, `10_leaf_with_tungsten.py`, `11_leaf_coil_variants.py`,
`12_leaf_gap_sensitivity.py` (commit `30b0f88`)

Constraints only. Why each value is what it is lives in the vault pages above; the numbers here are
what the next coil coupon has to be drawn to. Values from the coil model carry PROVISIONAL until a
STUDY record and a coupon measurement confirm them.

## Role on this board

One transmit loop and two receive coils per leaf axis, read by an LX34311 (or pin-identical
LX34312 / LX34070) on the same board. Target: a 5 × 10 × 0.8 mm aluminium flag on the leaf
carrier at a 1.0 mm airgap, with the 2 mm tungsten leaf 1.7 mm behind the flag.

## Coil geometry (as built on MC3_ENC_V1.0, with the two changes for the next coupon)

| Item | Value | Status |
|---|---|---|
| Electrical period λ | 15.0 mm along travel | as built |
| Receive lobe height (peak to peak) | 7.6 mm across travel | as built |
| Receive coils | sine: two full lobes; cosine: half / full / half over the same 15 mm span | as built |
| Receive layer changes | at every lobe extremum (λ/4 and 3λ/4 on the sine coil, λ/2 on the cosine coil); the two traces cross at the zeros on opposite layers | as built, Microchip rule |
| **Cosine end half-lobes** | **0.87 × the lobe amplitude** with the six-turn transmit loop (0.85 with four turns) | **PROVISIONAL, change** |
| Transmit loop outer centreline | 18.0 × 9.6 mm, 1 mm corner radius | as built |
| **Transmit turns** | **6 per layer** on two layers, 6 mil trace, 6 mil gap, stepping inward | **PROVISIONAL, change** (4 as built) |
| Layers | receive on the two layers nearest the flag; transmit on the two farthest | as built |
| Trace | 6 mil (0.1524 mm), 35 µm copper | as built |

The cosine end taper nulls the coil's direct coupling to the transmit loop in copper (end
compensation). Recompute it if the transmit loop's turn count, size or layer changes: it is the
factor that makes `biot.mutual_inductance(tx, cos)` zero in the model. Verify on the coupon with a
circle fit to the raw sine and cosine over a sweep: the centre should sit within 5 % of the radius.

## Placement constraints

- Nothing conductive within 3 × the airgap (3 mm) of the receive coils, in plane or behind, other
  than the flag and what the vault accepts behind it (Microchip rule; a conductor behind the coil
  at 3 mm costs the leaf coil measurable inductance and adds a gap-dependent offset).
- Airgap datum: the copper face nearest the flag. Nominal 1.0 mm (0.75 to 1.0 acceptable);
  **stability of ±0.1 mm over the stroke and over life is the constraint that matters**, not the
  nominal. Components on the face away from the flag only.
- Tank capacitors and the IC as close to the transmit loop's terminals as the pocket allows; the
  breakout pair drops to an inner layer immediately and routes as a tight pair.

## Routing constraints

- Transmit terminals at one end, joined turnaround at the other; that asymmetry is unavoidable and
  should be the only one.
- Via hops at the lobe extrema carry the full receive current: keep them short and paired, one per
  trace per extremum, as the built board has them.

## Tank (for the BOM, not the layout)

Six turns per layer give about 3.3 µH bare, 3.4 MHz at 2 × 1200 pF; about 2 × 950 pF for 4 MHz.
The as-built four-turn coil (1.8 µH) is under the LX34311's 3 µH floor; on those boards 2 × 820 pF
raises the tank impedance about 40 % (PROVISIONAL, case 01).

## Gotchas that affect layout

- The tungsten leaf behind the flag is a second target. It does not change the tank, but it
  compresses the electrical angle over the stroke and doubles the airgap sensitivity. If the frame
  design allows, an aluminium shield on the carrier close behind the flag makes the second conductor
  a controlled part.
- Every bench result to date used a plastic surrogate leaf.
