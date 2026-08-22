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

**The vault BOM has moved past the tscircuit design.** `Main-Board-01.md` § BOM is the list
to build from: DRV8212 (COL-COTS-0021) is *Superseded* by **DRV8214** (COL-COTS-0028, one
part per axis with integrated current sense, ripple counting and current regulation over
I²C); INA240 (0022) and the 100 mΩ shunt (0023) are *Rejected* — **no external sense amp and
no shunt anywhere on the board**. The legacy `imports/*.tsx` are reference only for the
parts that survive (MCU, LDO, P-FET, crystal, switch, FFC, pads).

How parts get into the library (CLAUDE.md: project-local, never global):
- **Standard packages**: KiCad's own footprint copied verbatim into `lib/MC3_COL_MAIN.pretty/`
  (`cp` — a file copy, not a text edit; the 3D-model reference stays `${KICAD10_3DMODEL_DIR}`).
- **Symbols**: Konnect `create_symbol` from the datasheet pin table. Konnect can't set custom
  symbol fields, so **`COTS` / `LCSC` / `Footprint` are set on the schematic instances**
  (`edit_schematic_component`) — that is what the BOM export reads anyway.
- **Custom land patterns** (bare pads, FFC): Konnect `create_footprint` from the drawing.

| Part | Qty | COTS | LCSC | Symbol | Footprint |
|---|---|---|---|---|---|
| DRV8214RTER H-bridge | 4 | COL-COTS-0028 | C22427938 | [x] `MC3_COL_MAIN:DRV8214RTER` (SLVSH04 Table 6-1) | [x] `WQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm_ThermalVias` (TI RTE0016C; EP 1.68 and via field per SLVSH04 §11 / vault) |
| STM32F411RET6 | 1 | COL-COTS-0024 | C94355 | [x] `MC3_COL_MAIN:STM32F411RET6` (pin types per KiCad `MCU_ST_STM32F4`, names per vault MCU Pinout) | [x] `LQFP-64_10x10mm_P0.5mm` |
| AMS1117-3.3 LDO | 1 | **none** | C6186 | [ ] | [ ] `SOT-223-3_TabPin2` |
| AO4407C P-FET | 1 | **none** | C469397 | [ ] | [ ] `SOIC-8_3.9x4.9mm_P1.27mm` |
| X32258MSB4SI crystal 8 MHz | 1 | **none** | C2682774 | [ ] | [ ] 3.2×2.5 4-pad (datasheet) |
| SKRKAEE020 reset switch | 1 | **none** — vault: *may be deleted* | C115357 | [ ] | [ ] |
| AYF530435 FFC 0.5 mm 4P | 4 | **none** | C425129 | [ ] | [ ] custom (Panasonic drawing) |
| Motor lead pads 2.2×1.4 @ 2.6 | 4 | **none** (#tbd in vault) | — | [ ] | [ ] custom |
| Machine supply pads 3.5×2.0 @ 4.2 | 1 | — | — | [ ] | [ ] custom |
| SWD header, bare PTH ×4, DNP | 1 | — | — | [ ] | [ ] custom |
| R/C passives | — | — | — | `Device:R` / `Device:C` | [ ] `R_0402`, `C_0402`, `C_0603`, `C_0805` copied in |

**Blocked on a vault decision:** the bold "none" rows have no COTS record. CLAUDE.md and the
Konnect project rule say a part with no record doesn't go in; the vault's own entry gate
("Every part in the BOM carries a record …") lists these same parts as the gap. Either
records get written (commodity-part records) or the rule is relaxed for support parts —
user's call.

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
