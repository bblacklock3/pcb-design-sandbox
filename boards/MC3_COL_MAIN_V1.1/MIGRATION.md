# MC3_COL_MAIN_V1.1 — working checklist (24 V-input revision)

**V1.1 is a fork of V1.0 made 2026-08-26** (`git`: Konnect `rename_project`, every sheet's
`(project …)` instance rewritten). V1.0 stays untouched as the 5 V-input fallback. Sections
0–13 below are inherited from V1.0's checklist verbatim and describe the state V1.1 started
from; **§14 is the delta.** The vault build rung for this revision is `Main-Board-02`.

---

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
| Outline | **⌀66 mm OD, 25 × 25 mm R2 cutout** (current CAD export; user 2026-08-22: expected to iterate, not worth reconciling yet) | **Three-way mismatch, owed.** Layout Constraints § Board says ⌀64 disc / 22 × 22 cutout; the vault reviewed `Collimator_Main_PCB_V1.0.DXF` at ⌀60 / 25 × 25 and rejected it ("does not describe this board and needs regenerating from the assembly"); the collimator envelope itself is unreconciled (60 mm in Leaf-Absolute-Inductive vs 65 mm in COL-CALC-0009) |
| Board orientation in the assembly | **Component face toward the mechanism** (user 2026-08-22) | **Not stated anywhere in the vault** — no "mechanism side", no orientation record. Implied by three existing rules (all parts top face; motor + supply pads "Layer: Top, bare copper"; the FFC is right-angle with "the flex lying flat above it"), never written down |
| User-facing items on the back face | J2 SWD, TP1–TP7, J12 CAN pads, J1 supply pads — and SW1 + D2/D3 only if a second SMT pass is accepted | **Conflicts with a hard vault requirement**: Layout Constraints § Board, "Single-sided — every part on the top face. Nothing on the underside", not listed under § Open. No rationale is recorded for it, so it can be overturned — but that is a vault change with an owner |
| SWD connector | 1×6 **right-angle** 2.54 mm header — `C56816` (1×6, $0.04, 4.6 k stock) or `C2334` (1×40 gold strip, 3 A, −55…+105 °C, cut to 6). Right-angle body stands ≈2.5 mm, so it **passes** the 4 mm cap that the vertical header fails | COL-PARAM-0020 lists a 2.54 mm vertical header at ~8.5 mm mated = fails. A **Tag-Connect TC2030 footprint** (bare pads + locating holes, zero parts, zero height) would remove the part and the height question entirely — worth a look before committing |
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

**Vault records owed for this:** ~~new COTS for the STM32F412RET6 superseding COL-COTS-0024~~
**DONE 2026-08-22.** The vault now carries:
- **[[COL-COTS-0029]]** STM32F412RET6, with DS11139 Rev 9 filed at
  `Main-Board-01/Datasheets/PDFs/STM32F412xE-xG.pdf`; COL-COTS-0024 marked superseded.
- **[[COL-COTS-0030]]** TJA1051T/3 CAN transceiver.
- **[[COL-COTS-0031]]** Panasonic AYF530435 encoder FFC — it had been carried as a BOM line with
  "no COTS record (support part)", which was wrong: it is a mechanical interface with a live
  retention risk, not a commodity.
- **Control Electronics § Open Items** — the control-link half is resolved: the machine link is
  **CAN**, and that decision is recorded as what forced the MCU change. The supply-rail half stays
  open, and CAN itself is now flagged as decided-but-uncharacterized.
- **MCU Pinout** — retitled to the F412, with a "What the F412 changed" table (CAN1 on PA11/PA12,
  RC_OUT_leaf4 displaced to PB14), I²C1 assigned to PB8/PB9, the ~70 pF bus-capacitance estimate,
  and USB noted as now foreclosed because CAN took its pins.

Still owed:
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
- [x] Drill/place origin and grid origin at (100, 100) saved in the board (user, 2026-08-22)
- [x] Netclasses in `.kicad_pro` (written with KiCad fully quit): Default 0.2/0.15, VM 2.0,
      MOTOR 1.2, PWR_3V3 0.4, CAN 0.25/0.2, I2C 0.25; 22 net assignments
- [x] `update_pcb_from_schematic` over IPC: 101 footprints on the board (the bridged solder
      jumper was swapped for a fitted 0 Ω because custom-shape pads can't be placed over IPC)
- [x] **Placement pass 1 (2026-08-22, via Konnect IPC `move_component`/`rotate_component`):**
      MCU cluster centred KiCad (77.3, 98) = beam (−22.7, +2), rotated 90° so pins 1–16 face
      south / 17–32 east / 49–64 west (vault edge map); drivers beside their own clusters —
      leaf1 U3 (106,79), leaf2 U4 (115,85), leaf3 U5 (94,121), leaf4 U6 (85.5,114.5), yaw U7
      (116.3,116.3) at 45°; motor pads r 25–26 on the 50°/60° and 230°/240° lines + yaw r 28.5
      @315°; FFCs r 28.5 @ 35°/69°/221°/249°; supply pads r 28 @ 12°, CAN pads r 28 @ −10°
      (one loom bundle on the east rim); power chain F1→D1→Q1→U1 inboard of the supply pads;
      CAN transceiver + termination + ESD inboard of the CAN pads; SWD header, LEDs, test points
      in the free NW; decoupling to the vault budgets. Courtyard-clean.
- [x] Board Setup → Constraints → *Minimum through hole* **0.2 mm** (user, 2026-08-22) — the
      WQFN thermal vias are 0.2 mm; JLCPCB 4-layer allows it. The 20 hole-size errors are gone.
- [x] **Placement pass 2 — uniform channel pattern (2026-08-22, user decision).** Rotating each
      channel to face its motor was dropped: every block now sits at *one* orientation, the
      leaf3 block the user arranged by hand being the pattern. Fine (non-90°) rotations are
      therefore no longer wanted anywhere except possibly the rim connectors.
      Anchors were leaf1 U3 (93.9, 82), yaw U7 (101.9, 82), leaf2 U4 (109.9, 82) across the north
      band; leaf3 U5 (93.9, 120.5) and leaf4 U6 (109.9, 120.5) south. TP6/TP7 moved off the new
      motor pads. DRC: no clearance or courtyard violations. **Superseded — see § 7.**
- [ ] **Consequence of the uniform orientation, to review:** on the three north channels the
      motor solder pads now face the aperture, not the rim, and the encoder FFCs J3/J4 no longer
      sit next to their own channel (J3 = ENC_leaf1 is on the east rim, J4 = ENC_leaf2 north).
      Re-home J3–J6 next to their channels once the flex-exit direction is decided — that is the
      open `docs/design/parts/AYF530435.md` note.
- [ ] **Parked off-board (user, WIP):** the whole power block (J1, F1, D1, Q1, U1, C1–C4, R5,
      TP1, TP2) plus J5 (ENC_leaf3) and J6 (ENC_leaf4) sit east/south of the outline and must
      come back inside before Gate 1.
- [ ] **Silkscreen cleanup (GUI — Konnect has no tool for footprint text).** Three parts, in
      this order, because step 2 *resets* hand-placed designator positions:
      1. **Library fix.** The four Konnect-authored footprints (`SolderPads_2x_2.2x1.4mm_P2.6mm`,
         `SolderPads_2x_3.5x2.0mm_P4.2mm`, `SolderPads_3x_2.2x1.4mm_P2.6mm`,
         `Panasonic_AYF530435_FFC-4P_P0.5mm`) were written in the legacy `fp_text reference` /
         `fp_text value` form, which KiCad 10 did not recognise as the Reference/Value fields:
         each instance carries a literal **`REF**` on F.SilkS** (11 of them — these *would print*)
         and the full **footprint name at 1 mm on F.Fab**. Delete both in the Footprint Editor,
         optionally adding `${REFERENCE}` at 0.5 mm on F.Fab as the stock footprints do.
      2. **PCB → Tools → Update Footprints from Library…** for library `MC3_COL_MAIN`. This also
         clears the 101 `lib_footprint_mismatch` DRC warnings (every board copy differs from its
         library copy since KiCad 10 normalised them on load).
      3. **Then** re-do the channel silk. leaf3's hand-arranged designator offsets (footprint-local
         mm) are the pattern: top row R/C at `(2.4, 0)` instead of the default `(0, −1.17)`;
         U at `(0, −2.83)`; 1 µF VM cap at `(0.225, 1.5)`; strap R at `(0, −1.5)`; motor pads J at
         `(0, 2)`. Fastest route now that all five blocks are geometrically identical:
         **Tools → Multichannel → Repeat Layout** with leaf3 as the reference — it copies
         silkscreen text positions (and later the routing) into the other four.
      Also set **Keep upright** on the reference text (Tools → Set Text and Graphics Properties…)
      so no designator can end up mirrored or upside-down. 6 `silk_edge_clearance` warnings
      (silk clipped by the aperture/board edge) to clear in the same pass.
- [ ] **Motor terminations are at the wrong radius on three channels.** COL-CALC-0009 puts the
      motors at **25 mm radius** (lead screws at 19 mm). Measured from the beam axis today:
      J9 leaf3 24.8 mm and J10 leaf4 25.9 mm are right; **J7 leaf1 15.8, J11 yaw 14.6, J8 leaf2
      17.4** — the north row's pads face inboard, ~10 mm short of their motors. Fix inside the
      uniform pattern: mirror the north row to the other 90° step so its pads face outward and
      drop the anchors so the pads land near r = 25.
- [ ] Mounting holes — still awaiting positions from the assembly CAD. The vault flags these
      three separate times as **undrawn**, and notes they compete with the connector clusters on
      the diagonals where radial room is tightest. Fastener type, count, diameter, what the board
      screws to, and whether it fastens from the top or bottom face are all unrecorded.
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


## 6. Board orientation and side allocation — 2026-08-22

**Decision (user):** the board is **not** made double-sided for the motor domain. Instead the
component face is mounted **toward the collimator mechanism**, and only *user-facing* items move
to the back so they stay reachable once the board is in the assembly.

Why this way round: the encoder FFC (AYF530435) is **right-angle SMD**, so the flex lies flat
across whichever face carries the connector. Point the component face away from the mechanism and
all four leaf flexes have to wrap the board edge — the exact thing the change was meant to avoid.
Keeping the motor domain on F.Cu also keeps it 0.21 mm above the solid In1 GND plane (the good
side of the stackup: F.Cu / 0.21 / In1 GND / 1.065 / In2 VM / 0.21 / B.Cu) and leaves the compact
motor loop and the ≤4 mm VM-cap rule untouched.

### What moving to the back actually costs

| Item | Type | Cost of moving to B.Cu |
|---|---|---|
| J1 supply pads, J12 CAN pads, TP1–TP7 | bare copper, no part | **none** — nothing to place |
| J2 SWD header | through-hole, DNP | **none** — the holes go through; it is hand-fitted either way |
| SW1 reset, D2/D3 LEDs | SMT | **second stencil + reflow pass** at JLC |

So the pads and the SWD header can move without touching the assembly process at all; only the
switch and the LEDs turn the board into a genuine double-sided build. Note the vault's rule reads
"every part on the top face" — an SMT statement — while bare pads and a hand-fitted THT header
arguably do not violate its intent, only its letter. Either way it needs saying in the vault.

### Mechanics of doing it

`flip_component` **requires KiCad closed** — it refuses while IPC is reachable. So the sequence is
quit KiCad → Konnect flips → reopen, and it must happen **before** the silkscreen pass (§ 3), since
flipping moves the text to B.SilkS.

### Gaps the 2026-08-22 vault sweep found (all owed)

- Axial clearance on the **second** face: no figure exists anywhere. COL-PARAM-0020's 4 mm is
  quoted "from the board face" (singular) and is itself unsourced (`maturity: est`, "#tbd — has no
  drawing behind it").
- The axial stack board → motors → leaf plane. Only radii are recorded (motors 25 mm, screws 19 mm);
  nothing says whether the motors sit above, below or coplanar with the board.
- FFC length, exit direction and bend radius; motor lead length and routing. Loom retention is
  explicitly unowned ("nothing currently owns it").
- Whether the main board rides the **rotating** frame at all — treated as rotating in
  Main-Board-01 Connectors, but COL-CALC-0009 argues the opposite ("Anything that can live on the
  stationary frame instead of the rotating one should… Boards are not negligible at 14%").
- **The encoder FFC has no COTS record.** It is a BOM line and a spec table only, and sits on the
  "no datasheet held" list — which trips the standing rule in `CLAUDE.md`. A record is owed before
  the next revision, and the vault already flags the retention risk (no solder tabs, no hold-downs,
  four 0.5 mm joints take the whole insertion/extraction force on a rotating board).


## 7. Side allocation applied, and the channel pattern of record — 2026-08-22

### Flipped to B.Cu (Konnect `flip_component`, KiCad closed)

**J2** SWD · **SW1** reset · **D2/D3** LEDs · **J1** supply pads · **J12** CAN pads ·
**TP1–TP7**. 13 footprints; 88 remain on F.Cu. DRC after: 275 unconnected (nothing routed) and
**no new errors**; warnings 296 → 229 as the hand-deleted `REF**` texts came out.

Assembly consequence: J1, J12 and TP1–TP7 are bare copper and J2 is through-hole, so **none of
those affect the SMT process**. **SW1, D2 and D3 are what make this a genuine two-sided build** —
if the second reflow pass is unwanted, those three come back to F.Cu and everything else stays.

`flip_component` has no IPC path — it writes the board file directly and refuses while KiCad is
reachable. So any further flip is a quit-KiCad operation, and KiCad must be reopened afterwards to
pick the change up.

### The channel pattern of record (user's leaf3, 2026-08-22)

The user rotated the whole leaf3 block one 90° step and moved it outboard: driver now at
**r = 25.2 mm** and the motor pads at **r = 26.6 mm**, pointing away from the aperture and close to
the 25 mm motor radius of COL-CALC-0009. The internal geometry is unchanged — every offset is the
§ 3 pattern turned 90°. Relative to the driver anchor (U at rot **180**):

| part | Δx | Δy | rot |
|---|---|---|---|
| DRV8214 U | 0 | 0 | 180 |
| 1 µF VM (C) | −1.00 | −3.00 | 180 |
| A1 strap 2.2 k (R) | +1.50 | −3.00 | 0 |
| A0 strap 2.2 k (R) | +1.50 | −4.34 | 0 |
| 10 k nFAULT (R) | +3.50 | −2.50 | 0 |
| 10 k RC_OUT (R) | +3.50 | −1.16 | 0 |
| 100 nF +3V3 (C) | +3.50 | +0.17 | 0 |
| 6.8 k IPROPI (R) | +3.50 | +1.50 | 0 |
| motor pads (J) | −3.50 | −0.20 | −90 |

**leaf1, leaf2, leaf4 and yaw are the user's to place** (decision 2026-08-22) — the angular
positions are a mechanical call, not a layout one, and the vault does not fix them. The table
above is the block to keep consistent; check each channel against it before Gate 1.

The two things that were going to drive an automated re-placement still stand as review items:
motor pads want to land near **r = 25**, and each channel's pads want to face the rim rather than
the aperture.


## 8. Motor-noise isolation on the 3.3 V rail — 2026-08-22 (user decision)

Two parts added to the schematic. ERC after: **0 errors**, the same 8 intentional
`same_local_global` warnings as before.

### 8.1 Local VM bulk, one per channel — `MotorChannel.kicad_sch`

`C31` (pre-annotation ref), **10 µF 0805 25 V X5R, LCSC C15850**, VM → GND, placed beside the
existing 1 µF. One symbol in the shared sheet, so it lands **five times** on the board.

Why: SLVSH04 asks for 0.1 µF **plus bulk** at VM. The board's bulk (C3/C4, 2 × 22 µF) lives in the
power block, so every switching edge from five H-bridges was being supplied through the length of
the VM trunk. 25 V part on a 5 V rail keeps most of its capacitance under DC bias.

### 8.2 LDO input filter — `Power.kicad_sch`

New net **`VM_LDO`**: `VM → FB4 → VM_LDO → U1 pin 3 (VI)`, with `C32` 10 µF from VM_LDO to GND and
a `PWR_FLAG` on the new net (ERC needs one — U1 pin 3 is a power *input* and VM_LDO has no source).
C1/C3/C4 stay on VM ahead of the bead; C2 stays on the output.

- **FB4 = `C14709`, Murata BLM18PG121SN1D, 120 Ω @ 100 MHz, 2 A, 50 mΩ, 0603, JLC Basic.**
- **Do not use C1002 here.** The 600 Ω GZ1608D601TF used on VDDA and VCAN5 is rated **200 mA /
  450 mΩ**, and the LDO input carries the entire +3V3 load (~150–250 mA). It would have been
  marginal on current and eaten ~110 mV of the AMS1117's 1.7 V dropout headroom. FB4 costs ~12 mV.

Why: the AMS1117's PSRR is ~60 dB at low frequency but collapses to roughly 30 dB by 100 kHz, so
motor PWM ripple on VM was walking through the regulator onto the +3V3 plane that feeds the MCU,
all five drivers' logic, the pull-ups and the CAN transceiver.

**Open — the filter has a resonance.** FB4 is ≈0.19 µH below its ferrite region; with C32 at 10 µF
that is **f₀ ≈ 115 kHz, Q ≈ 2.8 (~9 dB of peaking)**. If the motor PWM or its low harmonics land
there the filter *amplifies* rather than attenuates. To close it: get the PWM frequency from the
firmware page, then either confirm it is far from 115 kHz, or damp the LC — swap C32 for a
tantalum (ESR does the damping), or add a series-R damping leg in parallel with C32. **Do not
just shrink C32** — lowering C raises Q. #tbd

### What this leaves owed

- [ ] **GUI: re-annotate** — eeschema Tools → Annotate, **"Keep existing annotations"** so only the
      six new symbols get refs and nothing already placed renumbers.
- [ ] **`update_pcb_from_schematic`** (needs KiCad open, IPC), then place the 6 new footprints:
      five 0805 caps (one per channel, beside each 1 µF) and FB4 + C32 at the LDO input.
- [ ] Vault: both parts are **PROVISIONAL** and owed as decisions — the per-channel bulk value has
      no CALC behind it, and the LDO input filter is a new element of the power chain that
      *Main-Board-01* does not describe. The resonance question above goes with them.


## 9. I²C: one bus or several — decided 2026-08-22

**Stay on one bus (I2C1).** The vault already assumes this — *Main-Board-01 MCU Pinout*: "Five
COL-COTS-0028 devices need one bus. I2C1 on PB6/PB7 or PB8/PB9 is the clean option." Nothing found
while laying out argues against it.

### Closing the vault's open item on bus capacitance

*MCU Pinout* lists bus capacitance as open. Estimated here:

| contributor | value |
|---|---|
| 5 × DRV8214 SDA/SCL pin | ~50 pF |
| MCU pin | ~5 pF |
| tangential loop round the annulus, ~13 cm over a plane | ~13 pF |
| **total** | **≈ 70 pF** against the I²C spec limit of 400 pF |

With the fitted **4.7 k** pull-ups (R6/R7), rise time ≈ 0.847·R·C ≈ **280 ns** against Fast-mode's
300 ns budget — inside, but only ~7 % margin. **Dropping to 2.2 k gives ~130 ns** and would also
allow Fast-mode Plus at 1 MHz. Cheap insurance; worth doing if the scan rate ever matters.

### Why not multiple buses

- **Bandwidth is not the constraint.** At 400 kHz a 2-byte register read is ~50 µs, so a full
  five-device scan is ~250 µs — about a 4 kHz whole-board update rate. Far beyond what a leaf needs.
- **Addresses are already solved** — 0x60 / 0x64 / 0x6C / 0x70 / 0x66 via the DRV8214's tri-level
  A1/A0, documented on the root sheet.
- **Firmware is strictly simpler**: one peripheral, one bus mutex, one recovery path, one DMA
  stream. Splitting means N of each plus a channel→bus map.
- **Layout is simpler**: one tangential loop touching each driver instead of two or three runs.

**The one genuine cost, recorded rather than designed around:** a single driver latching SDA low
takes out all five channels. On this rung that is a power-cycle recovery. If a later revision wants
fault isolation, splitting 3+2 across two buses is the lever — not capacitance or speed. #tbd

**Now verified (2026-08-22):** DS11139 Rev 9 cover page states **"Up to 4x I²C interfaces
(SMBus/PMBus)"** and **"2x CAN (2.0B Active)"**. So four I²C are available and one is used; the CAN
count also confirms the reason for the part swap. Datasheet filed in the vault at
`Main-Board-01/Datasheets/PDFs/STM32F412xE-xG.pdf`, noted as [[ST STM32F412xE-xG datasheet]].

## 10. Promoted to the vault — 2026-08-23

The board pages in the vault had drifted badly against the design (F411 MCU, four channels, ⌀64
outline, single-sided assembly, "no input protection"). Swept and resynced, and the following
came off the "decisions owed" register above.

### New vault page

**`05 Builds/Main-Board-01/Main-Board-01 Power.md`** — there was no power page. It now carries the
supply interface, the input chain, every derived rail, the per-channel motor-voltage story and the
current budget.

### Resolved

| Owed item | Where it landed |
|---|---|
| Sensor VIN rail = VM | Power § Derived Rails. Net is `VSENS`, not `VIN_RAW` — Connectors § Pinout corrected |
| Board thickness 1.6 mm | Layout Constraints § Board — 1.606 mm, JLC04161H-7628, full stackup table added |
| Outline ⌀66 / 25 × 25 R2 | Layout Constraints § Board, and Main-Board-01 § Findings. The three-way mismatch is now *stated in the vault* as the open item rather than living only here |
| Board orientation (component face toward the mechanism) | Layout Constraints § Side Allocation — was previously written nowhere |
| User-facing items on the back face | Layout Constraints § Board now reads "Double-sided", replacing the "single-sided, nothing on the underside" hard requirement. The conflict is closed by changing the vault, which was the right owner |

### The supply rail — resolved on the board side

**The board requires 4.75–5.5 V at `J1`.** Three fitted parts set it and none is a motor: TJA1051T/3
`VCC` (4.5–5.5 V), AMS1117 dropout (~4.4 V floor), sensor rail (4.0–6.0 V). The 4.75 V floor is
where the transceiver and the LDO collide.

This corrects a framing this file and the vault both carried — that VM was "nominally 5 V by
assumption" because the machine rail was unknown. The motors were never the unknown: leaf is
3 V / 1.65 A stall / 1.82 Ω ([[COL-COTS-0002]]), yaw is 4.5 V / 0.83 A stall / 5.4 Ω
([[COL-COTS-0001]]), both recorded since August. VM is set by the board's own 5 V consumers, and
the DRV8214's per-channel voltage regulation is what lets two different motors share one rail.
`Control Electronics` § Open updated; the machine half stays open.

### Newly opened, from the sync

- **`F1` (2 A hold / 3.5 A trip) contradicts Layout Constraints' old "4.15 A continuous" figure.**
  Four leaves plus yaw stalled is ~4.7 A of VM current, above the trip. Recorded in Power § Current
  Budget and as an entry gate. The 4.15 A figure had no derivation behind it and was deleted.
- **`J2` (SWD header) overhangs the rim** — courtyard to 33.29 mm against a 33.00 mm edge. `J1`
  clears by 0.11 mm against a 0.2 mm rule.
- **No gate clamp on `Q1`** — bare 100 k, and V_GS max is ±20 V.
- **No local decoupling at the encoder connectors** — one 4.7 µF serves all four across the board.
- **`INV_R` / `KMC` for yaw are underived** — COTS-0028 tabulates leaf values only.

### Retracted

The 10 k pull-ups to +3V3 on `ENC_leaf1..4` were queried here as only valid if the sensor outputs
are open-drain. `Control Electronics` already answers it: they are, and that is the stated reason
the interface needs no level shifter. Not an open item.


## 11. Yaw sensing added — 2026-08-24 (user decision)

The yaw axis gets an incremental encoder now and an absolute encoder later (user: "temporary
measure"), plus a homing interrupter because the AEDR-8300 has no index. Schematic-only per the
user's instruction — **no PCB placement or routing was done**; parts sit in free area on the MCU
sheet. ERC is at the 9 expected `same_local_global_label` warnings, 0 errors; new nets verified
in the exported netlist.

### What went in (MCU.kicad_sch)

| Ref | Part | LCSC | Role |
|---|---|---|---|
| U9 | AEDR-8300-1Q0 | C22453800 | yaw quadrature, `YAW_ENC_A/B` → PA15/PB3 (TIM2 CH1/CH2) |
| R33 | 220R 0402 | C25091 | R_LED, ~15 mA from VSENS |
| R34/R35 | 2.2k 0402 | C25879 | A/B pull-ups to +3V3 (TTL V_OH margin; reuses a stocked value instead of the datasheet's 2.7k) |
| C37 | 100nF 0402 | C1525 | U9 decoupling (renamed from C33 — collided with a MotorChannel instance ref; #PWR010-013 similarly renamed to #PWR0107-0110) |
| U10 | GP1S094HCZ0F | C920601 | homing interrupter + one stop (3 mm slot, through-hole), `YAW_HOME` → PB7 (TIM4_CH2 capture) |
| U11 + R38/R39 | GP1S094HCZ0F + 100R/47k | C920601, C25076, C25792 | second interrupter 180° opposite — far-stop soft limit, `YAW_LIM` → PC12 (EXTI); added 2026-08-24 |
| R36 | 100R 0402 | C25076 | interrupter LED, ~20 mA from +3V3 (worst-case CTR 0.8 %) |
| R37 | 47k 0402 | C25792 | phototransistor pull-up (sized for I_C min 160 uA at I_F 20 mA) |
| TP8 | test point | — | `DBG_RX` |

SWO is gone: PB3 → `YAW_ENC_B`; logging is RTT over SWD + USART3 on PC10/PC11 (`DBG_TX`/`DBG_RX`).
`J2` pin 6 (the old SWO position — where debug probes put their VCOM UART) carries `DBG_TX`.
`VSENS` was promoted from a Connectors-sheet local label to a global net so it reaches U9; the
netclass pattern `VSENS` was added to PWR_3V3 in `.kicad_pro` (the stale `/Connectors/VSENS`
pattern is still listed there and matches nothing — harmless, remove on the next `.kicad_pro` pass).
Also applied while KiCad was closed: **MOTOR 1.2 → 0.8 mm and Default 0.2 → 0.25 mm** — these were
decided earlier but had been wiped by KiCad's close-rewrite of `.kicad_pro`; verified in the file now.

### Decisions owed to the vault (marked PROVISIONAL on the instances)

| Decision | Chosen here | Vault home |
|---|---|---|
| Yaw encoder = AEDR-8300-1Q0 | fitted as U9; M10899 disk track at r ≈ 25.87 mm → 4608 counts/rev, 0.078°/count | COL-COTS-0032 (updated to the on-hand disk); mechanical mounting is what remains |
| Homing interrupter = GP1S094HCZ0F | 3 mm slot, 0.3 mm aperture, through-hole (user chose slot clearance over SMD, 2026-08-24) | COL-COTS-0034 + [[Sharp GP1S094HCZ0F datasheet]] held 2026-08-24: pins 1=A/2=C/3=E/4=K, footprint `GP1S094HCZ0F` built (4.55×2.0 grid, 1.2 mm boss NPTH — verify grid against a physical part before fab); flag present = YAW_HOME HIGH; **no reflow** — hand-solder |
| TIM2 shared: yaw quadrature vs ENC_leaf2 capture | **resolved 2026-08-24: ENC_leaf2 keeps the hardware capture; yaw quadrature decoded in software** (leaves symmetric; path deleted with the temporary encoder) | Firmware-01 § Decisions Of Record + MCU Pinout § Yaw Sensing |
| 2.2k output pull-ups (not 2.7k) | stocked-value reuse, same margin math | on the symbol Notes |

### PCB steps owed (user, then Konnect)

- eeschema: F8 *Update PCB from Schematic* pulls U9/U10/R33–R37/C37/TP8 in; all footprints exist.
- Place U9 on **B.Cu** at the code-ring radius (gap 2.0 mm typ, ±0.38 mm placement, emitter side
  toward the rotation centre); U10 on B.Cu where the flag sweep crosses; route.
- No 3D model for the AEDR-8300 ships with the board (SnapEDA/UltraLibrarian hold one behind
  accounts).


## 12. MCU swap: F412RET6 → STM32U595RJT6 — 2026-08-25 (user decision)

Driven by CAN-FD and telemetry RAM (COL-SEARCH-0010; COL-COTS-0035). **Copper-free**: the non-Q
U595 LQFP64 reproduces the F412 pin skeleton exactly (sole delta pin 48 VDD→VDDUSB, already on
+3V3 with C7 at the pad). Verified by netlist diff — all 64 U2 pins on identical nets pre/post.
Symbol cloned from the F412's exact pin geometry (2 pin renames); footprint unchanged
(`LQFP-64_10x10mm_P0.5mm`); ERC at the 9-warning baseline. COL-COTS-0029 marked Superseded.

- **Order the bare `STM32U595RJT6` (DigiKey)** — the `Q`/SMPS variant sacrifices PC4/PC5/PB9 and is unusable.
- Firmware: AF renumbering; TIM12→TIM15 for RC_OUT_leaf1/2; 5 V tolerance of PA15/PB3 verified (FT_c/FT_fa).
- User: F8 should report **no copper changes** — field updates on U2 only.

### CubeMX validation — passed 2026-08-25

`firmware/MC3_COL_MAIN_U595.ioc` + generated skeleton (committed): all 41 pin assignments accepted
by ST's device database (10/51 GPIOs unused — exact count match), clock tree solved 8 MHz HSE
→ ×40 ÷2 → 160 MHz, all six timers + FDCAN1/I2C1/USART3 configured and generated. The negative
test also fired: CubeMX blocked TIM1_CH4 over PA11/FDCAN — the tool demonstrably catches
conflicts. TIM2 encoder mode + CH3 capture verified coexisting (mechanically; CH3 then latches
position, not time — the firmware decision stands). Remaining proof tiers: compile in CubeIDE,
then silicon.

## 13. Addressable status pixels — 2026-08-26 (user decision)

Two XINGLIGHT XL-1010RGBC-WS2812B pixels (COL-COTS-0036, LCSC C5349953) as a chain on the
MCU sheet: `D5`→`D6`, `R40` 470R series at the MCU end, `C44`/`C45` 100 nF one per pixel
(datasheet-mandatory). Placed as four, cut to two the same day — only two fit the underside. **Supply is `VM`, not +3V3** — the part is 3.5–5.5 V; its input
threshold is an absolute 2.8 V so PB5 drives it at 3.3 V directly. `LED_DATA` on **PB5 =
SPI1_MOSI (AF5)** — transmit-only SPI + DMA, no timer consumed, nothing bit-banged. PB5's
no-connect flag removed; `D6` DO carries one. Symbol + `LED_XL-1010RGBC` footprint (datasheet
p.11 pattern, 0.40×0.45 pads) added to the project library. ERC unchanged at 9 warnings.

### Decisions owed to the vault (marked PROVISIONAL on the instances)

| Decision | Basis | Where |
|---|---|---|
| PB5 / SPI1_MOSI as `LED_DATA` | only free pin with a DMA-capable serializer; PB4/LPTIM1_CH2 fallback | COTS-0036 § As Intended; MCU Pinout page updated |
| Two pixels | board space; chain grows free if it ever matters | COTS-0036 |
| 470R series (C25117, verify) | datasheet 20R–2k, ~500R | R40 Note |
| Footprint pin-1 orientation | datasheet p.11 recommended pattern, pin 1 = DO at chamfered corner | verify against JLC's footprint before fab |

### PCB steps owed (user)

- F8 to import D5–D6, R40, C44–C45; all **underside**, pixels in the rim region visible through
  the enclosure, chain order = physical order; each C at its pixel's VDD pad; R40 at U2.
- `VM` to the pixels can be a 0.25 mm trace (30 mA max) — no MOTOR-class width needed.


## 14. 24 V input via LM61460 synchronous buck — 2026-08-26 (user decision, V1.1 only)

Harness current ÷5 and the fragile "4.75–5.5 V delivered at the pads across a rotating joint"
contract replaced by "18–28 V into a buck" (`Main-Board-02 Power`; COL-PARAM-0021). Everything
downstream of `VM = 5 V` is untouched — drivers, LDO, `VSENS`, `VCAN5`, sensing, CAN.

### What changed (Power.kicad_sch)

| Item | V1.0 | V1.1 |
|---|---|---|
| `Q1` source net | `VM` | **`VIN_SW`** (24 V, switched through the reverse-polarity FET) |
| `U12` LM61460AANRJRR + `L1` XAL5030-222 | — | **new**: `VIN_SW` → 5 V `VM`, 6 A, ~1 MHz (`R41` RT 13.3k), **synchronized** to `BUCK_SYNC` via `C51` 1 nF AC-coupling into EN/SYNC |
| `C48`/`C49`/`C50` | — | input caps 2× 10 µF 50 V 1210 + 100 nF 50 V 0603 (hot loop) |
| `C52`/`R44`/`C53`/`C54` | — | CBOOT 100 nF, RBOOT 0R, VCC 1 µF, BIAS 100 nF (BIAS on `VM`) |
| `R42`/`R43` | — | EN UVLO divider 100k/8.66k → rising ~15.8 V |
| `R45`/`R46` + `C55`/`R47` | — | FB 100k/24.9k → 5.02 V; feedforward 4.7 pF + 1k (datasheet Table 9-2, 1 MHz/5 V row) |
| `C56`/`C57` | — | 2× 22 µF 25 V output caps at `L1` (plus the inherited `C1`/`C3`/`C4` bulk) |
| `F1` | 1206L200 (2 A, 6–8 V) | **0.75 A hold / 33 V** polyfuse (1812L075/33 class) — PROVISIONAL |
| `D1` | SMAJ5.0A | **SMAJ28A** (standoff 28 V, clamp 45 V) — sets the 28 V ceiling |
| `Q1` | AO4407C (−30 V) | **AO4421** (−60 V, 6.2 A, 40 mΩ), same SO-8 |
| `D7` | — | 12 V zener BZT52C12 gate–source clamp on `Q1` (|V_GS| would be 24 V against ±20 V) |
| `U2` PB4 | no-connect | **`BUCK_SYNC`** (LPTIM1_CH2, 1.00 MHz = 50 × PWM) |
| netclasses | — | `VIN24` 0.5 mm / 0.3 mm clearance for `VIN_PAD`/`VIN_PROT`/`VIN_SW`; `BUCK_SW` in `VM` (2.0 mm) |

ERC: **0 errors**; the same label-name warnings as V1.0. `U12` footprint = TI's own Ultra Librarian
export `MC3_COL_MAIN:VQFN-HR14_RJR_TEX` (pads checked against the datasheet land pattern: left column
at x = −1.85, 0.525 pitch, SW pad 0.41 × 2.39, VIN 0.41 × 0.99, PGND 0.41 × 0.81) with TI's `RJR0014A.step`
attached — rotation unverified until the board is viewed in 3D.

### Why the input range is 18–28 V, not 18–30 V

LM61460: 36 V operating, 42 V absolute maximum. A TVS that stands off 30 V (SMAJ30A) clamps at
48 V — above the abs max — so 28 V (SMAJ28A, clamp 45 V, breakdown ≥31 V) is the highest input the
part can be protected at. A 30 V ceiling means a 60 V buck (TPS54560B, non-synchronous, catch
diode) instead. PROVISIONAL — COL-PARAM-0021 carries the range.

### Current sensing and the switcher

`IPROPI` path: 244 µA/A × 6.8 k = 1.66 V/A with 1 nF → 23 kHz pole → −33 dB at 1 MHz; with SYNC
the residual ripple is phase-locked to the ADC sample and becomes a calibrated offset. Decided
2026-08-26 **not** to add a second RC pole per channel on this spin (5 R + 5 C + relabels);
escalation ladder if the bench disagrees: second RC at the ADC pins → LC post-filter on `VM` →
`R44` RBOOT > 0 to slow SW edges.

### Decisions owed to the vault (marked PROVISIONAL on the instances)

| Decision | Basis | Where |
|---|---|---|
| Input range 18–28 V | TVS-vs-abs-max arithmetic above | COL-PARAM-0021 |
| `R41` 13.3k for ~1 MHz | 400 kHz ↔ 33.2k, 2.2 MHz ↔ 5.76k interpolation | confirm against the RT equation |
| UVLO 15.8 V rising | keeps the buck off on a sagging harness rather than browning out `VM` | R42/R43 Notes |
| `F1` 0.75 A / 33 V | 1/5 of the 5 V design's current, ≥30 V rating | pick exact part + LCSC |
| BUCK_SYNC AC-coupled, EN from divider | datasheet pin 7: SYNC on EN/SYNC, cap-coupled | C51 Note |

### PCB steps owed (user)

- F8; place `U12` + hot loop (`C50` nearest VIN1/PGND1, `C48`/`C49` flanking, `L1`, `C56`/`C57`)
  in the input corner by `J1`/`Q1`; thermal vias under `U12`; `R45`/`R46`/`C55`/`R47` FB node short and
  away from `L1`. Keep the whole cluster away from the `IPROPI` resistors and the encoder connectors.
- `D7` beside `Q1`; `F1` footprint is now **1812**, `D1` unchanged (SMA).
- CubeMX: PB4 → LPTIM1_CH2 PWM, 160 MHz / 160 → 1.00 MHz; regenerate.
- Library: done — `VQFN-HR14_RJR_TEX` + STEP from TI. Check the 3D orientation after F8; `docs/design/parts/LM61460.md` layout note.
