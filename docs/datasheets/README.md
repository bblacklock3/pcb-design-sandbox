# Datasheets live in the vault

**Do not drop PDFs here.** Datasheets are vault-global reference material, cited by many
projects and many records, so they live in one place:

```
C:\Users\newte\Documents\Design Wiki\Refs\Datasheets\
```

Each PDF gets a `REF` note beside it recording publisher, URL, revision and retrieval date —
datasheets change silently, so the retrieval date is load-bearing.

## The flow

1. PDF and its `REF` note land in `Refs/Datasheets/`.
2. The **engineering digest** — what the datasheet changes about the design — goes into the
   part's `COTS` record in the vault. That is where "the part cannot do X" is argued.
3. Only the **layout constraints** come back here, as `docs/design/parts/<part>.md`.

See `_System/Process/board-design.md` in the vault for why the line sits there.

## Wanted for this board

Neither part on `MC3_COL_MAIN_V1.0` has had its datasheet read. Both COTS records are
product-page and JLC-parametric only, which is why several board decisions are still open.

- [ ] DRV8212 — TI H-bridge (COL-COTS-0021). Motor-supply ceiling and stall-current margin
      are resolved; still blocking: PH/EN vs PWM variant choice, thermal derating for five
      bridges in one enclosure
- [ ] INA240 — TI current-sense amplifier (COL-COTS-0022). Gain and shunt value are resolved;
      still blocking: sense bandwidth against the brush-ripple counting idea, input filter
      requirements
- [ ] Leaf motor — NFP-617-5.14-0675 (COL-COTS-0002). Supply voltage and stall current are
      now recorded; ambient temperature rating is still not published
- [ ] Yaw motor — not selected
- [ ] MCU — not selected
