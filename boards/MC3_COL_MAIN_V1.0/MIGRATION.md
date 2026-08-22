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

## 2. Schematic (Konnect `sch_*` toolsets) — built 2026-08-22 from the vault pages, not the tsx

Hierarchy: root `MC3_COL_MAIN_V1.0.kicad_sch` → `Power`, `MCU`, `Connectors`, and
`MotorChannel` instantiated ×4 as `leaf1`–`leaf4` (one file, KiCad multi-instance sheet;
per-instance signals through sheet pins, shared rails/bus through global labels).

- [x] `Power` — supply pads J3 → `VIN_PROT` → Q1 AO4407C (drain in, source out, gate pulled
      down by R20 100k) → `VM` → U3 AMS1117-3.3 (C21 10 µF in, C22 22 µF out) → `+3V3`.
      PWR_FLAGs on VIN_PROT, VM, GND.
- [x] `MCU` — U2 STM32F411RET6, decoupling per vault (4×100n VDD, 100n+1µ VDDA, 100n VBAT,
      4.7µ VCAP, 4.7µ bulk), Y1 8 MHz + 2×18 pF, R10 NRST pull-up + SW1, R11 BOOT0 pull-down,
      J2 SWD (DNP). Pin map exactly per vault *MCU Pinout*; unused + yaw-reserved pins NC.
- [x] `MotorChannel` — U1 DRV8214RTER, C1 1 µF VM, C2 100 nF VCC, R1 R_IPROPI, R2/R3 10 k
      pull-ups (nFAULT, RC_OUT), J1 motor pads. VREF = +3V3. Hierarchical pins EN, PH, A1, A0
      (in) and IPROPI, RC_OUT, nFAULT (out).
- [x] `Connectors` — J4–J7 AYF530435 FFCs (VIN=VM, GND, SIG=`ENC_leafN`, spare NC), R30–R33
      10 k SIG pull-ups to +3V3.
- [x] Root — sheet pins → `EN_leafN`, `PH_leafN`, `IPROPI_leafN`, `RC_OUT_leafN`,
      `nFAULT_leafN` global labels; A1/A0 straps as `GND`/`+3V3` global labels per instance.
- [x] ERC (kicad-cli, all severities): **0 errors**; 8 `same_local_global_label` warnings
      (a local label and a global label of the same name on one sheet — deliberate, the
      netlist confirms they merge). Netlist checked: GND 37 nodes, +3V3 29, VM 11; the only
      unconnected nets are the intended NCs.
- [ ] **GUI: Annotate.** The four channel instances share reference designators (U1, C1 …
      in every instance) — KiCad needs per-instance refs and there is no CLI for it. In
      eeschema: Tools → Annotate Schematic → scope *Entire schematic*, *Reset existing
      annotations*, OK; Ctrl+S; **close eeschema** before Konnect edits the schematic again.
- [ ] Snapshot PDF → vault build rung `Assets/` (after annotation)

**Net naming vs the vault:** vault `V3_3` = KiCad `+3V3` (standard power symbol); vault
`VIN_RAW` = KiCad `VM` (same copper: the rail downstream of the reverse-polarity FET feeds
the drivers' VM and the sensor VIN).

### Decisions owed to the vault (all marked PROVISIONAL on the instances)

| Decision | Chosen here | Vault home |
|---|---|---|
| I²C bus pins | I2C1 on PB8 (SCL) / PB9 (SDA); pull-ups 4.7 k (not yet placed — see below) | MCU Pinout § Open (bus pins, pull-up sizing, topology) |
| `nSLEEP` | one shared net `DRV_nSLEEP` to PC5 | MCU Pinout (unassigned) |
| `nFAULT` | four separate inputs PC0/PC1/PC2/PC10, 10 k pull-ups | MCU Pinout § Open |
| `RC_OUT` | per channel to PB6/PB7 (TIM4 CH1/2), PA10/PA11 (TIM1 CH3/4), 10 k pull-ups | MCU Pinout § Open (timer vs I²C read) |
| A1/A0 address straps (SLVSH04 Table 8-28) | leaf1 0/0 → 0x60, leaf2 0/1 → 0x64, leaf3 1/0 → 0x6C, leaf4 1/1 → 0x70, yaw Z/0 → 0x66 (write addr; read = +1). High straps through 2.2 k (R40–R43) per TI; low straps tied to GND; Hi-Z open | Motor Channel / COTS-0028 § Open — also the firmware address table |
| VREF | tied to +3V3 (TI typical application) | Motor Channel |
| R_IPROPI | 8.45 k (SLVSH04 Table 9-1 example) | needs a CALC: CS_GAIN_SEL=000b range vs ADC full scale |
| Board thickness | 1.6 mm (JLC standard; 1.4 not offered) | Layout Constraints |
| Outline | CAD export ⌀66 / 25×25 R2 | Layout Constraints / Main-Board-01 § Board geometry |
| Sensor VIN rail | = VM (5 V prototype assumption) | Encoder Interface § Supply / entry gate |

I²C pull-ups (one set, 4.7 k to +3V3) placed on the MCU sheet.

### Design review 2026-08-22 — changes applied (all committed, ERC 0 errors)

| # | Finding | Change | Vault item |
|---|---|---|---|
| 1 | HSE caps wrong for crystal | C19/C20 18 pF → **33 pF** (X32258MSB4SI is CL = 20 pF, LCSC C2682774) | BOM line "18 pF load caps" is wrong → correct |
| 2 | R_IPROPI not deliberate | 8.45 k → **6.8 k**: I_TRIP = V_VREF/(R·A_IPROPI) = 3.3/(6.8 k × 244 µA/A) = **1.99 A** (≈ DRV8214 2 A RMS); V_IPROPI at 1.65 A stall = 2.74 V | CALC record: R_IPROPI / I_TRIP / ADC scaling |
| 3 | No VM bulk | C61/C62 2× 22 µF 10 V 0805 at the VM trunk | supply/bulk sizing once the rail is specified |
| 4 | Sensor rail shares motor ripple | FFC VIN now `VSENS` = VM via FB61 (600 Ω@100 MHz) + C63 4.7 µF | Encoder Interface § Supply |
| 5 | No input protection | F60 polyfuse (PROVISIONAL 2.5 A hold, 1206) in series; D62 SMAJ5.0A TVS VIN_PROT→GND after the fuse | "no input protection" open item |
| 6 | NRST bare | C60 100 nF NRST→GND | — |
| 7 | J2 not really DNP | `DNP` field set; **GUI: set the DNP / exclude-from-BOM / exclude-from-pos attributes on J2** | — |
| 8 | LDO output cap ESR | C2 → tantalum 22 µF 10 V case A (3216), `Device:C_Polarized`; LCSC TBD | AMS1117 ESR open item → closed if tantalum fitted |
| 9 | Debug/logging channel | SWD header 6-pin: +3V3, SWDIO, SWCLK, GND, **NRST, SWO (PB3)** — SWV trace is the logging channel instead of USB | MCU Pinout: SWO on PB3; USB stays out (height cap) |
| 10 | Test points | TP60–64 (+3V3, SCL, SDA, IPROPI_leaf1, GND), TP65 VM, TP66 VIN_PROT — 1.0 mm pads | — |
| 11 | Indicators | D60/R60 heartbeat LED on PA5, D61/R61 power LED on +3V3 (0603, 1 k) | MCU Pinout: PA5 = LED |
| 12 | VDDA filtering | VDDA split from +3V3 through FB60 (+ PWR_FLAG); C8/C9 (100 n + 1 µ) on the VDDA side | — |

**USB-C decision:** not this revision — power is redundant, the vault already excludes USB, and a
USB-C receptacle + plug exceeds the 4 mm mated-height cap (COL-PARAM-0020). Data link = SWO via
the header; a UART on PA11/PA12 (USART6) to pads is the later option (costs RC_OUT_leaf4's pin).

**LCSC numbers assigned** (from Konnect's JLCPCB database snapshot, all verified in stock
2026-08-22; `LCSC` + `MPN` fields on every instance): resistors 0402 Basic — 10 k C25744,
4.7 k C25900, 2.2 k C25879, 1 k C11702, 100 k C25741; 6.8 k R_IPROPI C93940 (Yageo, Extended —
the Basic 6.8 k is out of stock); caps Basic — 100 nF 0402 C1525, 33 pF 0402 C1562, 1 µF 0402
C52923, 1 µF 0603 C15849, 4.7 µF 0603 C19666, 4.7 µF 0805 C1779, 10 µF 0805 C15850,
22 µF 0805 25 V C45783; ferrite 0603 600 Ω GZ1608D601TF C1002 (Basic, 200 mA);
LEDs red KT-0603R C2286 (Basic), green KT-0603G C12624 (Extended); tantalum 22 µF 10 V A-case
TAJA226K010RNJ C11366 (Extended); TVS SMAJ5.0A/TR13 C78401 (Extended); polyfuse 1206L200/12NR
C19078716 (2 A hold / 3.5 A trip, Extended, PROVISIONAL sizing). No COTS records for any of
these (support parts, by decision).

### MCU change + CAN link — 2026-08-22 (user decision)

- **MCU: STM32F411RET6 → STM32F412RET6** (LCSC C89374). Reason: the F411 has no CAN controller;
  the F412 is its pin-identical Access-line sibling (verified pin-for-pin against KiCad's ST
  symbols — same VDD/VSS/VCAP_1/NRST/BOOT0/HSE pins), adds bxCAN ×2 and 256 KB RAM (the vault's
  "RAM is the binding constraint for logging" note). Same AF/timer/ADC map → the vault MCU Pinout
  page holds; only additions: **CAN1_RX PA11, CAN1_TX PA12** (AF9), `RC_OUT_leaf4` moved
  PA11 → PB14 (EXTI). Alternatives weighed (JLC stock): F446RE (0 live), F405RG (pin 47 becomes
  VCAP_2), F413RG, F302/303/L431/G431 (pin map redo), F103 (downgrade).
- **Control link = CAN** (classic, 500 kbit/s): new `CAN` sheet — TJA1051T/3 transceiver
  (5 V from VM via ferrite, 3.3 V I/O), split termination 62 Ω + 62 Ω + 4.7 nF behind a bridged
  solder jumper (board = bus end on the bench), PESD1CAN ESD, three bare pads CANH/CANL/GND next
  to the supply pads = the provisional 4-pin machine interface (COTS-0026) with its two spares
  now defined. Bench adapter: PEAK PCAN-USB (IPEH-002021/-002022 isolated) or CANable 2.0;
  DE-9 7/2/3 = CANH/CANL/GND; adapter termination on. Layout note: `docs/design/parts/CAN.md`.
- **USB-C**: no (see above).

**Vault records owed for this:** new COTS for the STM32F412RET6 superseding COL-COTS-0024
(and COL-SEARCH-0008 addendum: CAN requirement → F412); COTS for the TJA1051T/3; the
control-link decision in Control Electronics (§ machine interface) and an update to
COL-COTS-0026 / Connectors page (CANH/CANL on the machine interface); MCU Pinout page (CAN1 on
PA11/PA12, RC_OUT_leaf4 on PB14, SWO PB3, PA5 LED, PC12/PB13 yaw).

### GUI items outstanding (user)
- Re-annotate (new parts carry R60…/C60…/TP60… placeholders): Tools → Annotate, entire schematic,
  reset; save; close eeschema.
- J2: set DNP / exclude from BOM / exclude from position files attributes.
- Optional tidy: drag-move the new LED/FB/TP symbols where their label text overlaps neighbours.

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

## 4. Retire tscircuit — done 2026-08-22

- [x] All tscircuit sources, imports, scripts, configs, Node tooling, snapshots and the
      tscircuit skills deleted; `.gitignore` and `CLAUDE.md` updated; `STM32F411.md` rewritten
- [x] This file is kept (renamed in purpose, not in name) as the board's working status
      checklist and the register of decisions owed to the vault — delete it when those are
      promoted and the board has gone to fab
- [ ] Update the vault build rung `Main-Board-01` with the new tooling, the schematic PDF and
      the decisions table above

## 5. Yaw channel — fitted 2026-08-22 (user decision)

- [x] Fifth `MotorChannel` instance `yaw` on the root; EN PA9 / PH PB12 / IPROPI PC4 per the
      vault's reserved pins; PROVISIONAL nFAULT_yaw PC12, RC_OUT_yaw PB13 (no free timer
      capture channel — count by EXTI or read `RC_CNT` over I²C); address A1 = Hi-Z, A0 = GND
- [ ] Vault: Main-Board-01 ("four fitted, yaw reserved") and the yaw-motor sizing caveat —
      the channel assumes the yaw motor lands inside the DRV8214's 4 A peak / 2 A RMS
- [ ] **GUI: re-annotate** (the new instance duplicates references) — eeschema Tools →
      Annotate, entire schematic, reset; save; close
