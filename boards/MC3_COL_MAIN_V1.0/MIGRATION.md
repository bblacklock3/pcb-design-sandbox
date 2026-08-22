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
- [x] Opened once in KiCad 10 GUI — loads clean, no library warnings. (Save wrote nothing:
      KiCad only rewrites on a dirty save, so `.kicad_pro` keeps Konnect's minimal
      `design_settings: {}` until board setup is first changed — harmless, KiCad uses defaults.)
- [x] Konnect ↔ KiCad IPC verified (`open_project` → "IPC is available") after adding
      `ipc_address` to `%APPDATA%\konnect\config.toml` — see `CLAUDE.md` → Environment

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

- [x] Layers: F.Cu, In1.Cu (power — the continuous GND plane), In2.Cu (mixed — VM fill),
      B.Cu via Konnect `add_layer` (vault: Layout Constraints → Layers 4)
- [ ] Fab-floor rules: clearance 0.15, track 0.15, via 0.3 drill / 0.6 dia, hole-to-hole
      0.5 mm — JLCPCB 4-layer capability floors (Konnect's JLCPCB preset), not design
      values; per-net widths come later as netclasses sized to the vault's current table.
      (Set once via Konnect `set_design_rules`, then lost when KiCad rewrote `.kicad_pro` on
      project close — see `CLAUDE.md` consequence 2. Re-enter in **Board Setup →
      Constraints** while there for the edge clearance, or close the project and re-run.)
- [ ] **GUI (no Konnect tool):** Board Setup → Physical Stackup. **Conflict found
      2026-08-22:** the vault says 1.4 mm (Layout Constraints → Thickness; BOM "Bare board"
      line in Main-Board-01.md) but JLCPCB's 4-layer thickness menu is 0.4/0.6/0.8/1.0/1.2/
      1.6/2.0 mm — 1.4 is not offered, and the vault carries no rationale for it (h_board_max
      is measured from the board face, so thickness doesn't eat it). Recommendation: 1.6 mm,
      JLCPCB's standard 4-layer stackup **JLC04161H-7628** (F.Cu 0.035 / 7628 prepreg 0.2104 /
      In1 0.0152 / core 1.065 / In2 0.0152 / 7628 prepreg 0.2104 / B.Cu 0.035), entered so the
      KiCad stackup is honest rather than the 0.48/0.48/0.48 default. **Vault correction owed**
      (user decision): Layout Constraints thickness 1.4 → 1.6 (or 1.2 if the assembly needs
      thinner). Note the inner copper is 0.5 oz on that stackup — relevant to the VM fill on
      In2 carrying 4.15 A; size against it or pay for 1 oz inner.
- [ ] **GUI:** Board Setup → Constraints → copper-to-edge clearance **0.2 mm** (vault:
      Layout Constraints → Clearances)
- [x] **Outline imported from the assembly CAD** (2026-08-22, user): **⌀66 mm disc, 25×25 mm
      cutout with R2 internal fillets**, on Edge.Cuts. This supersedes both the old
      `mechanical/` DXF (⌀60) and the ⌀64 / 22×22 stand-in I generated from the vault numbers
      — and it means the vault's Layout Constraints table (⌀64, 22×22 square) and
      `Main-Board-01.md` § Board geometry are **stale against CAD**; a vault update is owed
      (user). The user expects the outline may be revised again — treat it as provisional.
- [x] CAD export committed as `mechanical/Collimator_Main_PCB.DXF` (replaces the old
      `_V1.0.DXF` and my stand-in); verified ⌀66 circle + 25×25 R2 cutout at DXF (0,0), mm
- [x] **Origin convention:** outline moved so **board centre = KiCad (100, 100)** (it was at
      the page corner). **Beam-axis coordinate = KiCad coordinate − (100, 100).** Every
      Konnect `place_component` / `add_zone` call must add that offset to the vault / legacy
      numbers.
- [ ] **GUI:** Place → Drill/Place File Origin at (100, 100) and Place → Grid Origin at
      (100, 100), then View → Display Origin → grid origin, Ctrl+S. (Not in the saved file
      yet — no `aux_axis_origin` / `grid_origin` in `.kicad_pcb`.) Makes fab outputs and the
      status-bar coordinates beam-axis-relative.
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
