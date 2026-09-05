# Part layout-constraint notes

One file per part: **the constraints an autorouter cannot infer.** Nothing else.

A part may not be placed in a circuit until its note exists here.

## What goes here, and what does not

| | |
|---|---|
| **Here** | Bypass adjacency, Kelvin sense pairs, thermal vias, keep-outs, matched/differential pairs, current-loop compactness, package land pattern quirks, enable/startup behavior that constrains placement |
| **Not here** | What the part is, why it was chosen, what it costs, which alternatives lost, the JLCPCB number, the ordering link — all of that is the part's **COTS record** in the vault |

If a paragraph here starts explaining *why this part*, it belongs in the COTS record. Move it and link the ID instead. See `../../../CLAUDE.md`.

## Template

```markdown
# <Part> — layout constraints

Record: COL-COTS-NNNN · Datasheet: Refs/Datasheets/<name>.md

## Role on this board
## Pinout as used here
## Placement constraints
## Routing constraints
## Gotchas that affect layout
```

## Status

- `DRV8214.md` — COL-COTS-0028, written 2026-08-22 from SLVSH04 §11 and the vault's
  Layout Constraints. (DRV8212 / INA240 / shunt notes are no longer wanted: COL-COTS-0021 is
  superseded and 0022/0023 rejected — the DRV8214 replaces all three.)
- `STM32U595.md` — MCU (lineage F411 → F412 → U595RJT6, swap 2026-08-25; constraints unchanged
  for CAN — pin-identical, **COL-COTS-0029**). The pin map of record is the vault's
  *Main-Board-01 MCU Pinout*.
- `CAN.md` — the CAN link (TJA1051T/3, termination, ESD, pads), written 2026-08-22.
- `LX34311-leaf-coil.md` — the leaf encoder coil for the next coupon (six transmit turns, cosine
  end compensation, airgap stability), written 2026-09-04 from the coil model; PROVISIONAL until a
  STUDY record and coupon measurement.
- `yaw-ring-coil.md` — the yaw ring board (r 17–23, pocketed face, 1 mm standoff), written
  2026-09-04 from the coil model; PROVISIONAL likewise.

## Wanted

- [ ] `AYF530435.md` — encoder FFC: land pattern provenance (JLC footprint vs Panasonic
      drawing, mechanical pads), orientation on the rim, flex exit direction
- [ ] `AMS1117.md` — output-cap ESR/stability question (vault open item) if it changes
      the cap choice
