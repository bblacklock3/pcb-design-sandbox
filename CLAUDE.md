# PCB Design Sandbox

tscircuit project. Current board: **MC3_COL_MAIN_V1.0** — brushed DC motor driver
(`boards/MC3_COL_MAIN_V1.0/`).

## Naming convention

Each design lives in `boards/<NAME>_V<major>.<minor>/` with the top-level component file
named to match (e.g. `MC3_COL_MAIN_V1.0.tsx`, exporting `MC3_COL_MAIN_V1_0` since JS
identifiers can't contain dots). A new board revision gets a new versioned directory;
don't mutate an old version's directory once it has been sent to fab.

## Workflow rules — read before editing any circuit file

1. **Read the design context first.** Before touching a `.tsx` circuit file, read
   `docs/design/requirements.md` and the part notes in `docs/design/parts/` for every
   component you are placing or wiring. If a part has no note yet, stop and create one
   from its datasheet before using the part.

2. **Datasheet distillation.** When a new PDF appears in `docs/datasheets/`, read it and
   write `docs/design/parts/<part>.md` capturing what matters for this design:
   - Pinout and pin functions
   - Absolute max ratings and operating ranges relevant to our rails
   - Layout constraints the autorouter can't know (bypass cap placement, Kelvin/matched
     pairs, thermal pads, keepouts)
   - Gotchas (sleep/enable behavior, startup states, common-mode limits)

3. **Log decisions.** Every chosen value (shunt resistance, gain variant, connector
   series, pinout) gets an entry in `docs/design/decisions.md` with the reasoning and
   the datasheet numbers behind it.

4. **Placement before routing.** Keep `routingDisabled` on the `<board />` until
   placement and the netlist pass review against `docs/design/review-checklist.md`.
   Only then enable routing.

5. **Build after every change.** Run `tsci build` and fix errors/warnings before moving
   on. The dev server (`tsci dev`, http://localhost:3020) live-reloads on save.

## Environment notes

- The `tsci` CLI runs on Bun. `bun.exe` lives at
  `C:\Users\newte\AppData\Roaming\npm\node_modules\bun\bin` — it is on the user PATH,
  but shells opened before 2026-08-16 may need `$env:PATH += ";C:\Users\newte\AppData\Roaming\npm\node_modules\bun\bin"`.
- Parts are sourced from JLCPCB: `tsci search --jlcpcb <query>`, `tsci import --jlcpcb <part#>`.
