# Layout: automatic placement, relative positioning, and manual edits

**Read this before hand-computing any `pcbX`/`pcbY` coordinate**, especially
on a dense or non-rectangular board. Manually deriving trigonometry (polar
coordinates, pin-offset math read off a footprint file) to avoid overlaps is
almost always the wrong tool — tscircuit has first-class mechanisms for
exactly this, and hand math does not converge reliably once components are
sub-mm apart (decoupling caps next to IC pins, connectors on a curved edge,
etc.). If a change requires computing where another component's edge or pin
physically is, that is the signal to reach for one of the tools below instead
of reading raw footprint coordinates and adding offsets by hand.

## THE RULE (verified, tsci CLI 0.0.2351) — read this before anything else

### A `<group>` silently discards its children's `pcbX`/`pcbY`

This is the single most important fact on this page, and it invalidates the
obvious mental model. A `<group>` with no explicit layout mode does **not**
act as a transparent container that passes child coordinates through.

Minimal reproduction, run in this project:

```tsx
// board WITHOUT groups -- coordinates honored exactly
<board width="60mm" height="60mm">
  <resistor name="R1" pcbX={0}   pcbY={20} ... />   // lands at (0, 20)   OK
  <resistor name="R2" pcbX={-20} pcbY={0}  ... />   // lands at (-20, 0)  OK
</board>

// SAME components, each wrapped in a <group> -- coordinates IGNORED
<board width="60mm" height="60mm">
  <group name="a"><resistor name="R1" pcbX={0}   pcbY={20} ... /></group>
  <group name="b"><resistor name="R2" pcbX={-20} pcbY={0}  ... /></group>
</board>
// R1 lands at (0, 0). R2 lands at (0, -1.94). No error, no warning.
```

There is no error and no warning — the board just comes out scrambled. If a
design is organised into per-block group components (`<Power/>`, `<MCU/>`,
`<Connectors/>`, each returning a `<group>`), then **every hand-computed
coordinate in the entire design is silently thrown away**. Hours can be lost
tuning offsets that were never being applied.

**Symptom to watch for:** components sitting at or near (0, 0), or a whole
board that looks "shuffled" rather than subtly wrong. Diagnose by dumping
actual positions from the built Circuit JSON (see §5) and comparing them
against what the source asked for — never by eye, and never by trusting that
a prop you passed took effect.

### The reliable pattern: pack the group, constrain what matters

Give the group an explicit layout mode and let the solver place the children:

```tsx
<group name="mcu" pcbPack pcbPackGap="0.4mm" pcbX={clusterX} pcbY={clusterY}>
  <SomeChip name="U_MCU" />              {/* NO pcbX/pcbY on children */}
  <capacitor name="C1" decouplingFor="U_MCU.VDD1" decouplingTo="net.GND" />
  <constraint pcb centerToCenter xDist={7.6}  left=".U_MCU" right=".C1" />
  <constraint pcb centerToCenter yDist={2.74} top=".U_MCU"  bottom=".C1" />
</group>
```

- Children must have **no** `pcbX`/`pcbY`. A child that has them is flagged
  `isRelativelyPositioned()` in core and is excluded from packing as *static*
  — so a fully hand-placed group packs nothing and overlaps exactly as before.
- The **group's own** `pcbX`/`pcbY` then translates the whole solved cluster
  to its place on the board. This works correctly.
- `pcbPack` on one group does **not** disturb hand-placed sibling groups
  (verified). If the rest of the board also moved, that is the group bug
  above, not the packer.

### Why `<constraint>` is mandatory for decoupling

`pcbPack` minimises area; it does not read `decouplingFor` /
`maxDecouplingTraceLength`. Packing an MCU plus five decoupling caps on its
own left caps up to **10mm** from their pins — electrically useless — and
raised no error. Adding `<constraint>` per cap fixed it: every cap landed
**1.90mm** from its pin with zero overlaps.

`applyComponentConstraintClusters` in core unions constrained components into
a rigid sub-cluster (solved with kiwi) that the packer then places as one
unit. That is the intended mechanism for "this part must sit exactly here
relative to that part."

Sign conventions, which are easy to get backwards:
- `xDist` is `right.x - left.x`
- `yDist` is `top.y  - bottom.y`

Sizing an offset: read `pcb_courtyard_rect` from the built Circuit JSON.
**Not** the datasheet body size, and **not** `pcb_component.width/height`
either — the courtyard is a separate, larger rectangle that is also *offset*
from the component centre. Measured on this project's DFN8 driver:

| source | width | note |
|---|---|---|
| datasheet body | 2.0mm | far too small |
| `pcb_component` | 2.42mm | pad extents only |
| `pcb_courtyard_rect` | **3.00mm** | what the overlap check actually uses, centre shifted +0.472mm in x |

Sizing against `pcb_component` still produced overlap errors. Half of each
*courtyard* plus the pack gap is the true minimum centre-to-centre separation.
The centre offset was identical across every part in that group, so it
cancelled out — verify that before relying on it.

Dump them with:

```js
j.filter(e => e.type === 'pcb_courtyard_rect')
```

Also check which side a pin is actually on before choosing a direction. On the
DRV8212, VM sits at x=-0.95 and VCC at x=+0.95 — opposite sides — and an
earlier revision had each bypass cap on the far side of the chip from its own
pin. That is an electrical defect (a bypass cap only works with a short loop
back to its pin), and no placement check catches it.

### Schematic auto-layout is ON by default — and ONE `schX` disables it

The schematic has its own layout engine, entirely separate from the PCB one.
`pcbPack` does **nothing** for the schematic. From core's
`_getSchematicLayoutMode()`:

```js
const anyLayoutChildHasSchCoords = this.children.some(child =>
  participatesInAutoLayout && (cProps?.schX !== undefined || cProps?.schY !== undefined))

if (schAutoLayoutEnabled && !hasManualEdits) return "match-adapt"   // forced ON
if (!anyLayoutChildHasSchCoords && !hasManualEdits) return "match-adapt"  // default ON
return "relative"                                                    // manual
```

Auto-layout ("match-adapt") is the **default**, but a single child anywhere in
the group carrying `schX` *or* `schY` flips the whole group to `"relative"` —
pure manual placement. It is all-or-nothing per group, and there is no
warning. Hand-placing "just a couple" of parts silently disables organisation
for every part in that group.

Setting `schAutoLayoutEnabled` on the group is worth doing even when no child
has coordinates: that check runs *first*, so the group stays auto-laid-out
even if someone later adds a stray `schX`.

Verified on this project's MCU group: with hand-set `schX`/`schY` the
schematic was strung across a huge canvas with metre-long wires; deleting all
24 of them (and setting `schAutoLayoutEnabled`) clustered every passive around
its chip with short traces. The PCB layout was unaffected — the two are
independent.

`schPack` is declared in `@tscircuit/props` but **has no implementation in
core** (`grep schPack node_modules/@tscircuit/core/dist/index.js` returns
nothing). It is a silent no-op; don't reach for it. The real modes are
`schMatchAdapt`, `schFlex`, `schGrid`, plus `schSectionName` (which takes
priority over all of them) for grouping by function.

### `calc()` silently no-ops on `<capacitor>`

Build output showed `Invalid pcbX value for Capacitor: component-relative
calc references are not supported for footprint elements (Capacitor); pcbX
will be ignored.` for every `calc()` on a capacitor's `pcbX`/`pcbY` — it
falls back to another position instead of failing loudly. Use `<constraint>`
instead for capacitors. Treat every `calc()` usage as unverified until the
build output is checked for `Invalid ... calc` / `ignored`.

### Standing discipline

After **every** placement change, dump the actual positions from the Circuit
JSON and check them against intent. A silent no-op prop and a correct one
look identical in the source. Three separate mechanisms on this page fail
quietly rather than loudly; the build exiting `code 0` proves nothing.

## 1) `calc()` — relative positioning (NOT usable on capacitors here, see above)

`pcbX`/`pcbY` (and their schematic equivalents) accept a `calc(...)`
expression that references other components' bounds or pins directly. The
framework resolves the actual geometry — you never read or copy a raw pad
coordinate.

Available references inside `calc(...)`:

- Component bounds: `R1.x`, `R1.y`, `R1.maxX`, `R1.minX`, `R1.maxY`, `R1.minY`
- Pin/pad bounds: `U1.pin1.x`, `U1.pin1.y`, `R1.pin2.maxX`, etc.
- Board bounds: `board.minX`, `board.maxX`, `board.minY`, `board.maxY`
- Board edge anchors: `pcbLeftEdgeX`, `pcbRightEdgeX`, `pcbTopEdgeY`, `pcbBottomEdgeY`

```tsx
// A decoupling cap 1.5mm off a specific pin -- no manual coordinate reading:
<capacitor
  name="C_DEC"
  footprint="0402"
  pcbX="calc(U1.pin19.x + 1.5mm)"
  pcbY="calc(U1.pin19.y)"
  decouplingFor="U1.VDD"
  decouplingTo="net.GND"
/>

// A row of resistors spaced automatically:
<resistor name="R2" pcbX="calc(R1.maxX + 2mm)" pcbY="calc(R1.y)" ... />

// A part locked to a board edge with a fixed margin:
<resistor name="R_EDGE" pcbLeftEdgeX="calc(board.minX + 2mm)" pcbY="0mm" ... />
```

This is the fix for "place this decoupling cap right at this pin" — the exact
task that caused repeated overlap errors when done by hand on this project.
`calc()` also stays correct if the referenced part moves or its footprint
changes; hand-copied coordinates silently go stale.

## 2) `pcbPositionAnchor` — anchor by pin or footprint boundary, not center

By default `pcbX`/`pcbY` position a component by its **center**. Set
`pcbPositionAnchor` to align a specific pin (`"pin1"`, `"pin2"`, ...) or a
named boundary point (`"top_left"`, `"top_center"`, `"top_right"`,
`"center_left"`, `"center"`, `"center_right"`, `"bottom_left"`,
`"bottom_center"`, `"bottom_right"`) to the given coordinate instead.

```tsx
<resistor name="R1" pcbX={8} pcbY={14} pcbPositionAnchor="pin1" ... />
```

Combine with `calc()` when the anchor point itself should track another part.

## 3) Automatic layout modes — `pcbPack`, `pcbGrid`, `pcbFlex`

For a **cluster** of related parts (an IC and its support passives, a
connector row), let the layout engine solve placement instead of assigning
every coordinate:

- **`pcbPack`** — packs children to minimize space while avoiding overlaps.
  Best default for a dense, irregularly-shaped cluster (an MCU with its
  decoupling network is exactly this case).
  ```tsx
  <board pcbPack pcbGap="1mm">
    <chip name="U1" footprint="soic8" connections={{ pin1: "R1.pin1" }} />
    <resistor name="R1" resistance="1k" footprint="0402" />
  </board>
  ```
  `pcbPack` (and `pack` on a `<group>`) uses each part's `connections` prop to
  understand what's related — this is a legitimate, documented use of
  `connections`, not the unreliable shortcut it can look like when reached
  for casually on a `<chip>` in place of explicit `<trace>` elements.
- **`pcbGrid`** — regular grid arrangement (matrix keyboards, LED arrays,
  connector banks). `pcbGridGap`, `pcbGridColumns`, etc.
- **`pcbFlex`** — single-axis flow, CSS-flexbox-like (`pcbFlexDirection`,
  `pcbFlexGap`).

When `layoutMode="none"` (the default once you set explicit `pcbX`/`pcbY`),
components keep their manual positions — mixing manual and automatic layout
in the same group is possible but should be deliberate, not accidental.

## 4) Manual edits — drag placement in `tsci dev`

`tsci dev` has an edit mode (pencil icon, schematic viewer; "Move Components"
mode, PCB viewer). Dragging a component writes an entry to
**`manual-edits.json`** (`pcb_placements`, `schematic_placements`,
`manual_trace_hints`) that overrides whatever `pcbX`/`pcbY` the code
specifies. This file must be imported and passed to `<board manualEdits={...}>`
for edits to take effect — check for that import if drag edits don't seem to
apply.

This is the right tool when the arrangement is a matter of taste/readability
rather than a precise electrical requirement (decoupling proximity, cutout
clearance) — use `calc()`/`pcbPositionAnchor` for the latter, drag-and-drop
for the former. **Before adding more manual edits, check what's already in
`manual-edits.json`** — stray entries from an earlier session can silently
override new code changes and look like the code isn't taking effect.

## 5) Measuring how much space a group actually needs

For choosing a board size (or a carrier/enclosure) programmatically, render a
group in isolation with `RootCircuit`, wait for `renderUntilSettled()`, and
read the `pcb_board` / `pcb_group` bounds from the resulting Circuit JSON.
Packing failures surface as elements whose `type` ends in `_error`
(`pcb_placement_error`, `pcb_footprint_overlap_error`,
`pcb_component_outside_board_error`) — scan for these before trusting a
bounding box. See the `RootCircuit` guide (programmatic building) for the
exact snippet; this is for board-sizing decisions, not day-to-day placement.

## Decision guide

| Situation | Use |
|---|---|
| **Anything inside a `<group>`** | `pcbPack` on the group + `pcbX`/`pcbY` on the group itself — child coordinates are discarded |
| Schematic looks scattered / long wires | Delete **every** `schX`/`schY` in the group and set `schAutoLayoutEnabled` — one stray coord disables auto-layout group-wide |
| Place a cap/resistor right at a specific IC pin | `<constraint pcb centerToCenter …>` (NOT `calc()` — it no-ops on capacitors) |
| A cluster of parts (IC + its passives) that just needs to not overlap | `pcbPack` on a wrapping `<group>`, children with no coordinates |
| A regular array (connectors, LEDs, keys) | `pcbGrid` or `pcbFlex` |
| Fixed margin from the board edge | `pcbLeftEdgeX`/`pcbRightEdgeX`/`pcbTopEdgeY`/`pcbBottomEdgeY` with `calc(board.minX + Nmm)` etc. |
| Fine-tuning by eye, no precise electrical constraint | Drag in `tsci dev`, lands in `manual-edits.json` |
| Non-rectangular board (cutouts, curved edges) with several dense clusters | `pcbPack` per cluster + `calc()`/anchors for pin-critical parts — **not** hand-derived polar/trig coordinates |
