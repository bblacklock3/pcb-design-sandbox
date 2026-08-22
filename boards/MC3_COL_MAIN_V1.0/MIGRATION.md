# MC3_COL_MAIN_V1.0 — tscircuit → KiCad migration checklist

Working checklist for the `kicad-migration` branch. **Transient**: delete this file in the
commit that removes the last tscircuit source. No rationale here — the *why* of every part
and value is in the vault (see `CLAUDE.md`).

Source of truth for what to rebuild: the snapshot commit `9e1e1ef` ("Snapshot tscircuit WIP
before KiCad migration") — the `.tsx` files are readable as a netlist even without tsci.

## 0. Scaffold (done 2026-08-22)

- [x] `MC3_COL_MAIN_V1.0.kicad_pro` / `.kicad_sch` / `.kicad_pcb` created via Konnect `create_project`
- [x] Project-local libraries `lib/MC3_COL_MAIN.kicad_sym` + `lib/MC3_COL_MAIN.pretty/`,
      registered in `sym-lib-table` / `fp-lib-table` as `MC3_COL_MAIN` (`${KIPRJMOD}` URIs)
- [x] Vault rules + fab house registered in `.konnect/project.json`
- [x] `.gitignore`, `.mcp.json`, `CLAUDE.md` updated
- [ ] Open the project once in KiCad 10 GUI, confirm it loads without library warnings,
      save (KiCad fills in the default `.kicad_pro` design settings on first save), commit

## 1. Library — one symbol + footprint per part (Konnect `library` / `integration` toolsets)

Each needs a COTS record first; fields on the symbol: `COTS` (record ID), `LCSC` (C-number).
The legacy `imports/*.tsx` give the pin map and land pattern that was used; the JLC/LCSC
number is in the COTS record.

| Part | Legacy import | COTS | Symbol | Footprint |
|---|---|---|---|---|
| STM32F411RET6 (MCU) | `imports/STM32F411RET6.tsx` | COL-COTS-0024 | [ ] | [ ] LQFP-64 |
| DRV8212DSGR (H-bridge ×4) | `imports/DRV8212DSGR.tsx` | COL-COTS-0021 | [ ] | [ ] WSON-8 |
| INA240A1DR (sense amp ×4) | `imports/INA240A1DR.tsx` | COL-COTS-0022 | [ ] | [ ] SOIC-8 |
| 100 mΩ 1 W 1206 shunt (×4) | `imports/HoJLR1206_1W_100mR_1_.tsx` | — | [ ] | [ ] 1206 |
| AMS1117-3.3 (LDO) | `imports/AMS1117_3_3.tsx` | — | [ ] | [ ] SOT-223 |
| AO4407C (P-FET, reverse-polarity) | inline in `Power.tsx` | — | [ ] | [ ] SOIC-8 |
| X32258MSB4SI (crystal) | `imports/X32258MSB4SI.tsx` | — | [ ] | [ ] |
| SKRKAEE020 (tact switch) | `imports/SKRKAEE020.tsx` | — | [ ] | [ ] |
| AYF530435 (0.5 mm FFC 4P, encoder ×4) | `imports/AYF530435.tsx` | — | [ ] | [ ] |
| Motor solder pads (×4) / power pads | `Connectors.tsx` | — | [ ] | [ ] custom pad footprint |
| Passives (R/C) | inline | — | use `Device:R` / `Device:C` symbols, project-local 0402/0603 footprints |
| *Not on this board:* KH-FG0.5-H2.0-16PIN, B2B/B4B-PH/XH | `Mezzanine.tsx`, `imports/` | COL-COTS-0003 | skip — mezzanine branch not taken | |

Fill in the `—` COTS IDs from the vault register before creating the symbol; a part with no
record does not go in.

## 2. Schematic (Konnect `sch_*` toolsets) — hierarchical, one sheet per legacy group file

- [ ] Root sheet: title block, sheet symbols, power flags
- [ ] `MCU` sheet ← `MCU.tsx` (STM32F411 + decoupling per `docs/design/parts/STM32F411.md`,
      crystal, reset switch, BOOT0, SWD header; pin assignment by axis per `axes.ts`)
- [ ] `Power` sheet ← `Power.tsx` (VM in → reverse-polarity FET → AMS1117 → 3V3; bulk caps)
- [ ] `MotorChannel` sheet ← `MotorChannel.tsx`, instantiated ×4 (leaf1–leaf4):
      DRV8212 + low-side shunt + INA240; nets per axis
- [ ] `Connectors` sheet ← `Connectors.tsx` (motor pads ×4, power pads, encoder FFC ×4)
- [ ] ERC clean (`run_erc`); net names match the legacy names (`VM`, `GND`, `3V3`, per-axis
      `PH_n`/`EN_n`/`ISENSE_n`/encoder lines) so `docs/design/parts/` notes still read true
- [ ] Snapshot PDF → vault build rung `Assets/`

## 3. PCB (Konnect `pcb_*` toolsets; KiCad open, IPC on)

- [ ] Board setup: 4 layers, 1.6 mm, JLCPCB 4-layer design rules (clearance, min track,
      via 0.3/0.6)
- [ ] Outline from `mechanical/Collimator_Main_PCB_V1.0.DXF` on Edge.Cuts — 64 mm disc,
      22×22 mm square beam-path cutout at centre (cite the PARAM)
- [ ] Placement from legacy `MC3_COL_MAIN_V1.0.tsx` `BLOCK_POS` / `CONN_RING_MM` /
      `CLUSTERS` (MCU at (-21, 2), power at (19.5, -2), leaves at ±12/0, ±20, connector
      clusters on 55° / 235° diagonals, rings 25.6 / 28.6 / 28 mm)
- [ ] Gate 1 of `docs/design/review-checklist.md` passes before any routing
- [ ] Zones: GND on In1, VM on In2, GND on bottom — **solid planes**, router kept off
      inner layers (the tscircuit-era problem of perforated planes goes away here; the
      decoupling budgets in `docs/design/parts/` assume an intact plane)
- [ ] Route; Gate 2; DRC clean

## 4. Retire tscircuit (final commit on the branch)

- [ ] Delete `boards/MC3_COL_MAIN_V1.0/*.tsx`, `*.ts`, `tests/`, `imports/`, `scripts/`,
      `manual-edits.json`, `postest.circuit.tsx`, `index.circuit.tsx`, `tscircuit.config.json`,
      `.claude/skills/tscircuit/`
- [ ] Replace `package.json` (drop tscircuit deps/scripts) or remove it if nothing else needs Node
- [ ] Drop the "Migration in progress" banner and the `.tscircuit/` ignore from `CLAUDE.md` / `.gitignore`
- [ ] Delete this file
- [ ] Update the vault build rung `Main-Board-01` with the new tooling and the PDF snapshot
