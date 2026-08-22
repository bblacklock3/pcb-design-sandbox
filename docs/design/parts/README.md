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

## Wanted

The two driver/sense parts are backed only by vendor product pages and JLC parametrics —
neither datasheet has been read, so neither note can be written yet. This blocks an entry
gate on the `Main-Board-01` build rung.

`STM32F411.md` exists but is also datasheet-light: its decoupling scheme is distilled
from ST published power-supply guidance recorded in COL-COTS-0024, not from a read of
the datasheet itself.

- [ ] `DRV8212.md` — COL-COTS-0021. Needs: bypass placement, thermal pad handling, PH/EN
      pin behavior at startup, current-loop layout
- [ ] `INA240.md` — COL-COTS-0022. Needs: Kelvin sense geometry, input filter placement,
      common-mode limits at this rail, reference pin handling
