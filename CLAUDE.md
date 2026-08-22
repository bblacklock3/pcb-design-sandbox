# PCB Design Sandbox

tscircuit project holding the schematics for OXOS boards. Current board:
**MC3_COL_MAIN_V1.0** — the MC3 collimator main control board (`boards/MC3_COL_MAIN_V1.0/`).

## The vault is the authority

Design reasoning does **not** live in this repo. It lives in the Obsidian design wiki:

```
C:\Users\newte\Documents\Design Wiki
```

Specifically, for this board:

| What | Where |
|---|---|
| The split rule — what belongs here vs. the vault | `_System/Process/board-design.md` — **read this first** |
| The subsystem: direction, interfaces, open questions | `Projects/MC3 Collimator/03 Systems/Control Electronics/Control Electronics.md` |
| The build rung this board *is* | `Projects/MC3 Collimator/05 Builds/Main-Board-01/Main-Board-01.md` |
| Part records (identity, JLC number, why it was considered) | `Projects/MC3 Collimator/04 Records/COTS/` |
| Datasheets | `Refs/Datasheets/` |

**Two standing rules:**

1. **Before placing a part, read its COTS record.** Every part on this board has one, and it carries the JLCPCB number, the ordering link and the reason the part is in play. If a part has no record, stop — it needs one before it goes in the schematic.
2. **Before choosing a controlled value, check for a PARAM record.** Rail voltages, current limits, board outline and connector geometry are controlled values in the vault. Cite them; never invent one here.

**Do not recreate a requirements or decisions layer in this repo.** It existed once (`docs/design/requirements.md`, `docs/design/decisions.md`) and was removed: it was a second system of record with no IDs, no register and no link resolution, and it had already drifted from the vault within three commits. If a file here starts accumulating rationale, that content belongs in a vault record — move it and leave a pointer.

## What *does* belong here

Board-mechanical facts, i.e. anything that only means something inside a PCB:

- `boards/<NAME>_V<major>.<minor>/*.tsx` — the netlist, footprints, placement, routing. **tscircuit is the schematic**; the vault never restates it.
- `docs/design/parts/<part>.md` — layout constraints the autorouter cannot infer: bypass adjacency, Kelvin sense pairs, thermal vias, keep-outs, matched pairs, startup/enable behavior that affects placement. **Constraints only** — identity and rationale are in the COTS record, which the note links.
- `docs/design/review-checklist.md` — the placement and routing gates.

## Naming and revisions

Each board lives in `boards/<NAME>_V<major>.<minor>/`, top-level component file named to match
(`MC3_COL_MAIN_V1.0.tsx` exporting `MC3_COL_MAIN_V1_0`, since JS identifiers can't contain dots).

**A board revision is two things at once:** a new versioned directory here, and a new build rung
in the vault. They are one-to-one. Never mutate a version's directory once it has gone to fab —
same discipline as a sealed record.

Each group file opens with a comment naming the vault records it implements:

```tsx
// Implements: COL-COTS-0021 (DRV8210 H-bridge)
// Layout constraints: docs/design/parts/DRV8210.md
```

## Workflow

1. **Read the design context first** — the build rung and the COTS records for every part you are placing or wiring.
2. **Datasheet distillation.** When a datasheet lands, its engineering digest goes in the vault COTS record. What comes *here* is the layout-constraint note in `docs/design/parts/`.
3. **Placement before routing.** `routingDisabled` stays on the `<board />` until placement and the netlist pass Gate 1 of `docs/design/review-checklist.md`.
4. **Build after every change.** Run `tsci build` and fix errors and warnings before moving on. `tsci dev` serves a live preview on http://localhost:3020.
5. **Evidence flows back to the vault** — board previews into the build rung's `Assets/`, stabilized geometry promoted to PARAMs, and the BOM reconciled against the COTS register at each entry gate.

## Environment

- `tsci` runs on Bun. `bun.exe` is at `C:\Users\newte\AppData\Roaming\npm\node_modules\bun\bin` — on PATH, but shells opened before 2026-08-16 may need it added.
- Parts come from JLCPCB: `tsci search --jlcpcb <query>`, `tsci import --jlcpcb <part#>`.
- **`tsci export -f step` needs a patch to work.** Stock, it silently drops every
  component that has an external STEP model — the export "succeeds" and contains only
  the bare board. Run `node scripts/patch-tsci-step.mjs` after any tscircuit update;
  the script explains the bug and is idempotent. Verify with
  `grep -c MAPPED_ITEM out.step` — 0 means broken, one per placed part means good.
  `-f glb` is unaffected and always worked.
- **For 3D printing, `npm run export:3d`.** tsci has no STL/3MF board export — `-f
  component-box-3mf` is a parts-organiser bin generator, not a model of the board — so
  the pipeline goes GLB then `scripts/glb-to-stl.mjs`, which handles the Y-up to Z-up
  rotation and writes binary STL in mm. Outputs land in `dist/3d/` (gitignored):
  `board_full.stl` (board + parts, 64×64×3.35mm) and `pcb_only.stl` (bare board,
  64×64×1.40mm, watertight apart from 6 boundary edges). Pass `--only` / `--exclude`
  to filter by component name, `--list` to see them, `--separate <dir>` for one file
  per part.
- **Orthographic top view: `npm run render:top`** → `dist/3d/top-view.svg`. Copper,
  pads, vias and silkscreen come from `circuit.json`; component bodies are the real
  part geometry projected out of the GLB, drawn as a dark silhouette with a lighter
  top face. `--theme grey|black`, `--no-silkscreen`, `--no-components`, `--px <n>`.
  **The GLB axis mapping is `pcbX = -x`, `pcbY = z`, `height = y`** — not the obvious
  `(x, -z)`, which rotates every body 180° about the board centre. That error is
  nearly invisible on a roughly symmetric board (it just swaps parts across the
  middle), so verify against `pcb_component.center` rather than by eye.
