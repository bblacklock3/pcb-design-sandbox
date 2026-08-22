# PCB Design Sandbox

KiCad 10 project repo for OXOS boards, edited through the **Konnect** MCP server. Current board:
**MC3_COL_MAIN_V1.0** — the MC3 collimator main control board (`boards/MC3_COL_MAIN_V1.0/`).

> **Migration in progress (branch `kicad-migration`).** This board started life in tscircuit.
> The `.tsx` files under `boards/`, `imports/`, `scripts/`, `manual-edits.json`,
> `*.circuit.tsx` and `.claude/skills/tscircuit/` are the **legacy source** kept for
> reference while the netlist is rebuilt in KiCad. They are not the design of record and
> are deleted when `boards/MC3_COL_MAIN_V1.0/MIGRATION.md` is fully ticked. Don't extend them.

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

1. **Before placing a part, read its COTS record.** Every *engineering* part on this board has one, and it carries the JLCPCB number, the ordering link and the reason the part is in play. If such a part has no record, stop — it needs one before it goes in the schematic. **Exception (decided 2026-08-22): commodity support parts** — LDO, reverse-polarity FET, crystal, reset switch, FFC connector, bare pads, passives — are listed in the build rung's BOM with LCSC numbers and deliberately carry no COTS record, so the COTS register isn't clogged with support parts. They go in on the strength of the BOM line; the LCSC number and "no record" are noted on the symbol instance.
2. **Before choosing a controlled value, check for a PARAM record.** Rail voltages, current limits, board outline and connector geometry are controlled values in the vault. Cite them; never invent one here. Where the schematic needs a value the vault hasn't set (a pull-up, a strap, a pin not yet assigned), choose provisionally, mark it `PROVISIONAL` in the symbol's fields / sheet notes, and list it in `boards/<NAME>/MIGRATION.md` → "Decisions owed to the vault" so it gets promoted or overturned there.

These rules are also registered as Konnect project design rules in
`boards/MC3_COL_MAIN_V1.0/.konnect/project.json`, so `list_design_rules` surfaces them.

**Standard symbols exception.** KiCad's own `Device:R`, `Device:C`, `Device:Crystal*`,
`Device:LED`, `power:*` and `Connector*` symbols may be used from the global libraries —
KiCad embeds a copy of every symbol into the `.kicad_sch`, so the schematic stays
self-contained. Everything that is *ours* (ICs, custom connectors, pads) lives in the
project library. Footprints are always copied into the project `.pretty` (stock ones
verbatim via `cp`), so the board carries a pinned copy.

**Do not recreate a requirements or decisions layer in this repo.** It existed once (`docs/design/requirements.md`, `docs/design/decisions.md`) and was removed: it was a second system of record with no IDs, no register and no link resolution, and it had already drifted from the vault within three commits. If a file here starts accumulating rationale, that content belongs in a vault record — move it and leave a pointer.

## What *does* belong here

Board-mechanical facts, i.e. anything that only means something inside a PCB:

- `boards/<NAME>_V<major>.<minor>/` — one KiCad project per board revision:
  `<NAME>_V<major>.<minor>.kicad_pro` / `.kicad_sch` / `.kicad_pcb`, the project-local
  `sym-lib-table` / `fp-lib-table`, and `lib/` holding the project's own symbols
  (`lib/<NAME>.kicad_sym`) and footprints (`lib/<NAME>.pretty/`). **KiCad is the
  schematic**; the vault never restates it. `mechanical/` holds the DXF the outline is
  imported from.
- `boards/<NAME>/.konnect/project.json` — Konnect's per-project config (design rules,
  fab house). Committed.
- `docs/design/parts/<part>.md` — layout constraints the router cannot infer: bypass adjacency, Kelvin sense pairs, thermal vias, keep-outs, matched pairs, startup/enable behavior that affects placement. **Constraints only** — identity and rationale are in the COTS record, which the note links.
- `docs/design/review-checklist.md` — the placement and routing gates.

**Every part lives in the project-local library**, not the global KiCad libraries — the repo
has to be self-contained and reproducible on another machine. Custom symbols/footprints are
created through Konnect's `library` toolset; JLCPCB parts come in through its `integration`
toolset. Each symbol carries the COTS record ID and the LCSC `C`-number as fields.

## Naming and revisions

Each board lives in `boards/<NAME>_V<major>.<minor>/`, project file named to match.

**A board revision is two things at once:** a new versioned directory here, and a new build rung
in the vault. They are one-to-one. Never mutate a version's directory once it has gone to fab —
same discipline as a sealed record. Fab outputs (Gerbers, BOM, PnP) are generated at a tagged
commit and attached to the build rung in the vault; they are not committed here.

Schematic sheets and symbol descriptions name the vault records they implement, e.g. a sheet
title-block comment `Implements: COL-COTS-0021 (DRV8212 H-bridge) · Layout: docs/design/parts/DRV8212.md`.

## Editing rules — Konnect is the only writer

KiCad files (`*.kicad_sch`, `*.kicad_pcb`, `*.kicad_pro`, `*.kicad_sym`, `*.kicad_mod`,
`*-lib-table`) are serialised object graphs with UUIDs and cross-references. **Never edit
them with text tools** (Edit/Write/sed). All changes go through the Konnect MCP tools
(`mcp__konnect__*`; `list_toolboxes` → `load_toolset(...)`). The installed `konnect` skill
carries the full operating rules and the decision tree — it loads automatically on KiCad work.
If the Konnect tools are not available in a session, stop and say so; do not fall back to
file edits.

Konnect reaches KiCad three different ways, and that decides when the file on disk changes:

| Edit | Path | KiCad needed? | When it hits disk |
|---|---|---|---|
| Schematic, libraries, lib tables | Konnect's own S-expression engine | No | Immediately (atomic write) |
| PCB **board setup** — `add_layer`, `set_design_rules` (→ `.kicad_pro`), `create_netclass` (→ `.kicad_pro`) | Konnect's file engine, **even when IPC is up** | No — and the board/project must be **closed or reverted** in KiCad afterwards | Immediately |
| PCB items (place/move/route/zones/text) | KiCad 10 IPC into the running PCB editor | Yes, board open, API enabled | When **you save in KiCad** |
| Exports, ERC, DRC | `kicad-cli` | No | n/a (read-only) |

Four consequences:

1. **Don't have eeschema open on a sheet Konnect is editing.** It won't see the write, and
   saving from eeschema afterwards overwrites it. Close the sheet or reload it (File → Revert)
   after Konnect writes.
2. **Board-setup tools bypass the open editor.** After `add_layer` / `set_design_rules` /
   `create_netclass`, KiCad's in-memory board and project settings are stale.
   - `.kicad_pcb` changes (`add_layer`): KiCad writes the board only on an explicit save, so
     **reopen the board before the next Ctrl+S** and the change survives.
   - `.kicad_pro` changes (`set_design_rules`, `create_netclass`): KiCad **rewrites
     `.kicad_pro` on project close**, so a Konnect write made while the project is open is
     lost the moment you close it. Verified 2026-08-22: rules 0.15/0.15/0.6/0.5 reverted to
     0.0/0.2/0.5/0.25 on close/reopen. **Close the project in KiCad first, then let Konnect
     write `.kicad_pro`, then reopen** — or enter those values in Board Setup yourself.
3. **Save in KiCad (Ctrl+S) before `git commit`** after IPC-path PCB work, or the commit
   misses it.
4. **Git is the undo for schematic and board-setup work** — Konnect has no undo stack. Commit
   small and often while Konnect is editing.

`.mcp.json` (committed) points Claude Code at the Konnect binary via `${USERPROFILE}`;
`konnect init` (one-time, per machine) installs the skills/agents/hooks into `~/.claude`.

## Workflow

1. **Read the design context first** — the build rung and the COTS records for every part you are placing or wiring.
2. **Datasheet distillation.** When a datasheet lands, its engineering digest goes in the vault COTS record. What comes *here* is the layout-constraint note in `docs/design/parts/`.
3. **Placement before routing.** No traces until placement and the netlist pass Gate 1 of `docs/design/review-checklist.md`.
4. **Check after every change.** Run ERC (`verification` toolset → `run_erc`) after schematic edits and DRC (`run_drc`) after PCB edits; fix errors and understood-warnings before moving on. `snapshot_project` writes PDF checkpoints.
5. **Evidence flows back to the vault** — schematic/board PDFs and renders into the build rung's `Assets/`, stabilized geometry promoted to PARAMs, and the BOM reconciled against the COTS register at each entry gate.

## Environment

- KiCad 10 at `C:\Program Files\KiCad\10.0\` (`kicad-cli.exe` in `bin\`). The KiCad API
  must be on (Preferences → Plugins → Enable KiCad API) for PCB tools; it is on this machine.
- Konnect binary: `%USERPROFILE%\Documents\KiCad\10.0\3rdparty\plugins\com_github_mixelpixx_konnect\bin\konnect.exe`
  (installed via KiCad's Plugin and Content Manager). `konnect status` shows what's installed;
  `konnect transaction status <project-dir>` shows any interrupted multi-file write.
- **Konnect only finds KiCad's IPC socket if told where it is.** When Claude Code launches
  Konnect, `KICAD_API_SOCKET` isn't set (KiCad sets it only when *it* launches the server), so
  `%APPDATA%\konnect\config.toml` must carry
  `ipc_address = 'ipc://C:\Users\<you>\AppData\Local\Temp\kicad\api.sock'` — the address
  shown under Preferences → Plugins. Per machine, one-time, like `konnect init`. Backslashes
  are significant (the path becomes the Windows named-pipe name verbatim). Symptom when it's
  missing: `open_project` reports `ipc_address: ""` / "IPC is not reachable" while KiCad is
  plainly running. Restart Claude Code after editing it. The same file must also carry
  `kicad_cli = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'` (and `kicad_binary`): once a
  `config.toml` exists Konnect stops auto-detecting, and `run_drc`/`run_erc`/exports fail
  with "Failed to spawn kicad-cli".
- Konnect is AGPL-3.0. Internal design use; do not build/redistribute tooling on it without
  checking licensing.
