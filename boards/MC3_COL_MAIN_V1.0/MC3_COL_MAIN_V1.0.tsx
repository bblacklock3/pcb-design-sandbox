import React from "react";
import { arcSlots, polarToXY, faceOutward } from "./connectorLayout";
import { MotorChannel } from "./MotorChannel";
import { Power } from "./Power";
import { MCU } from "./MCU";
// Mezzanine.tsx is deliberately NOT rendered here. It sizes a 16-pin FPC for the
// RAW sin/cos sensor branch (COL-COTS-0003, 10-14 conductors). This board takes
// the INTEGRATED branch instead — LX34311 computes position on-chip and emits one
// digital signal, so the per-leaf FFCs in Connectors.tsx ARE the sensor interface
// and the mezzanine is redundant. The file stays because that branch can reopen;
// if it does, these connectors are what goes.
import { MotorPads, PowerPads, EncoderConnector } from "./Connectors";
import { boardOutline, CUTOUT_HALF_SIDE_MM } from "./boardOutline";

// MC3_COL_MAIN_V1.0 — MC3 collimator main control board.
//
// Vault build rung:  Projects/MC3 Collimator/05 Builds/Main-Board-01/
// Vault system:      Projects/MC3 Collimator/03 Systems/Control Electronics/
// The split of what lives where: _System/Process/board-design.md
//
// Five brushed DC axes — four leaves plus yaw. The MC2 drove two BLDC motors through
// three-phase drivers; MC3 motors are brushed (COL-COTS-0002), so commutation leaves the
// board and each channel becomes a single H-bridge. Axis count goes 2 -> 5.
//
// The sensor front-end is on a mezzanine card, not here — see Mezzanine.tsx.
//
// Board shape (boardOutline.ts):
// a 64mm-diameter round board with a 22x22mm beam-path cutout through its centre, both
// centred on the beam axis at (0,0). Components live in the 11-32mm-radius annulus.
// Note the cutout is SQUARE, so the room between it and the board edge depends on
// angle: 21.00mm along the axes, but only 16.44mm on a true 45-degree diagonal.
//
// THIS FILE OWNS PLACEMENT. Each block below defines only its own internal relative
// layout and has no opinion about where it sits; every board position is set here via
// the `pos` (and `rot`) props. All blocks currently sit at the origin — they will
// overlap until real positions are assigned.
// ===========================================================================
// LAYOUT TUNING — every number that positions something lives here.
// ===========================================================================
//
// Board is a 64mm disc (r=32) with a 22x22mm SQUARE cutout. Because the cutout
// is square, the usable radial band depends on angle:
//     on-axis (0/90/180/270)   11.00 -> 32mm   = 21.00mm of room
//     diagonal (45/135/...)    15.56 -> 32mm   = 16.44mm of room
// The connector clusters sit on the diagonals, i.e. the worst case.

/** Blocks, placed by hand in cartesian mm. */
const BLOCK_POS = {
  mcu: { x: -21, y: 2 },
  power: { x: 19.5, y: -2 },
  leaf1: { pos: { x: -12, y: 20 }, rot: 90 },
  leaf2: { pos: { x: 0, y: 20 }, rot: 90 },
  leaf3: { pos: { x: 0, y: -20 }, rot: -90 },
  leaf4: { pos: { x: 12, y: -20 }, rot: -90 },
  /** Board supply solder pads. Sized for the whole board current, so they want
   *  to be near the regulator and the bridges rather than tucked anywhere. */
  powerPads: { x: 27.4, y: 5.8 },
};

/** THREE RINGS. Within a cluster the two FFCs spread apart along the arc,
 *  while both leaves' motor pads stack RADIALLY on the cluster centreline.
 *
 *  That split follows the parts. The pads are bare copper — no body, no cable
 *  strain, nothing to get a finger to — so they tolerate being buried on the
 *  inside and stacked on top of each other. The FFCs need their tails to run
 *  clear off the rim without crossing each other, so they get the outer ring
 *  and the angular separation.
 *
 *  Radial budget on the diagonal is 15.56 .. 32.00mm = 16.44mm, which is
 *  comfortable now that nothing here is a wire-to-board connector. */
const CONN_RING_MM = {
  /** Both leaves' motor pads, stacked on the cluster centreline. */
  motorInner: 25.6,
  motorOuter: 28.6,
  /** FFCs, spread either side of the centreline. */
  encoder: 28,
};

/** Arc gap between the two FFCs in a cluster. This is the "spread" knob —
 *  raise it to push them further apart, lower it to tighten the cluster. */
const CONN_GAP_MM = 10;

/** Rendered footprint widths, measured from the built Circuit JSON.
 *  These are MEASUREMENTS, not preferences — re-measure if a part changes. */
const CONN_W = {
  motor: 4.8, // bare solder pads
  encoder: 3.5, // 0.5mm FFC, 4-pin + hold-down tabs
};

/** Two mirrored clusters on the diagonals, each carrying two leaves. */
const CLUSTERS = [
  { centreDeg: 55, axes: ["leaf1", "leaf2"] },
  { centreDeg: 235, axes: ["leaf3", "leaf4"] },
] as const;

/** Only the FFCs are laid out along the arc now — the motor pads sit on the
 *  centreline and need no slot — so the arc is spaced by FFC width alone. */
const CLUSTER_WIDTHS = [CONN_W.encoder, CONN_W.encoder];

export const MC3_COL_MAIN_V1_0 = () => (
  // Routing is ON. Placement reached 0 errors and the ground/power pours are
  // in, so routing now has a return plane to use rather than being redone.
  <board
    name="MC3_COL_MAIN_V1.0"
    outline={boardOutline}
    layers={4}
    // NO VIA TUNING HERE, and that is deliberate — two obvious knobs do nothing
    // and it is worth recording so nobody re-adds them:
    //   * autorouter={{ allowViaInPad: false }} is accepted, reaches
    //     SimpleRouteJson, and the router ignores it.
    //   * pcbStyle={{ viaPadDiameter, viaHoleDiameter }} is accepted and does
    //     not change routed vias either; the autorouter takes its via size from
    //     board.min_via_pad_diameter, hardcoded to 0.3mm in @tscircuit/core with
    //     no prop feeding it. pcbStyle only reaches explicit <via> elements.
    // The via that used to land inside U_MCU.PA0 was a SYMPTOM. Its real cause
    // was MCU pin assignment sending signals out the wrong side of the package,
    // forcing the router under the die — fixed in MCU.tsx, and the error went
    // away on its own once the pins faced their loads.
  >
    <cutout
      shape="rect"
      width={`${CUTOUT_HALF_SIDE_MM * 2}mm`}
      height={`${CUTOUT_HALF_SIDE_MM * 2}mm`}
      pcbX={0}
      pcbY={0}
    />

    {/* ---- STACKUP ----
        top     signal + every component (all parts are top-side)
        inner1  ground fill  + signal   <-- NOT a solid plane. See below.
        inner2  VM fill      + signal   <-- likewise
        bottom  signal + ground fill

        INTENT was inner1 = solid ground directly under the component layer, so
        every top-side signal has an unbroken return one dielectric away. That
        matters here because four H-bridges switch alongside four analog
        current-sense lines feeding the position loop, and shared return copper
        is the classic way sense noise gets in.

        WHAT ACTUALLY HAPPENS: <copperpour> fills leftover space on a layer. It
        does NOT reserve the layer from the autorouter, and there is no
        AutorouterConfig option that does. Measured on the current build, the
        router puts ~143 trace segments through inner1 and ~168 through inner2.
        So both "planes" are perforated by signal routing, and the ground plane
        is not continuous.

        THIS IS NOT YET RESOLVED, and it undercuts specific numbers written
        elsewhere in this design: the MCU VBAT/bulk caps, the INA240 VS cap at
        6mm and the DRV VCC cap at 4mm are each justified by "the return is a
        via to plane, not a trace". That argument holds only where the plane
        under those parts survives intact — which has to be checked per part,
        not assumed. #tbd either constrain the router to top/bottom (no such
        prop exists today), hand-route with <tracehint>, or accept a fill rather
        than a plane and re-derive those decoupling budgets.

        cutoutMargin keeps copper off the 22mm beam-path hole; boardEdgeMargin
        keeps it off the rim. Both matter on a board that is mostly edge. */}
    <copperpour
      name="POUR_GND_INNER"
      connectsTo="net.GND"
      layer="inner1"
      clearance="0.2mm"
      boardEdgeMargin="0.5mm"
      cutoutMargin="0.5mm"
    />
    <copperpour
      name="POUR_VM_INNER"
      connectsTo="net.VM"
      layer="inner2"
      clearance="0.2mm"
      boardEdgeMargin="0.5mm"
      cutoutMargin="0.5mm"
    />
    <copperpour
      name="POUR_GND_BOTTOM"
      connectsTo="net.GND"
      layer="bottom"
      clearance="0.2mm"
      boardEdgeMargin="0.5mm"
      cutoutMargin="0.5mm"
    />
    {/* --- placed, do not move --- */}
    <MCU pos={BLOCK_POS.mcu} />
    <MotorChannel name="leaf1" index={0} pos={{ x: -12, y: 20 }} rot={90} />
    <MotorChannel name="leaf2" index={1} pos={{ x: 0, y: 20 }} rot={90} />
    <MotorChannel name="leaf3" index={2} pos={{ x: 0, y: -20 }} rot={-90} />
    <MotorChannel name="leaf4" index={3} pos={{ x: 12, y: -20 }} rot={-90} />

    <Power pos={BLOCK_POS.power} />
    <PowerPads pos={BLOCK_POS.powerPads} rot={102} />

    {/* --- connector ring, polar ---
        Two mirrored clusters on the diagonals: leaf1+leaf2 in quadrant 1,
        leaf3+leaf4 in quadrant 3.
        Within a cluster the two FFCs spread along the OUTER arc, spaced by
        CONN_GAP_MM, so their flex tails leave the rim without crossing. Both
        leaves' motor pads sit on the cluster CENTRELINE, stacked radially on
        two inner rings — bare copper stacks happily where a connector body
        could not.
        Tune CONN_RING_MM / CONN_GAP_MM at the top of this file. */}
    {CLUSTERS.map(({ centreDeg, axes }) => {
      const ffc = arcSlots(
        centreDeg,
        CONN_RING_MM.encoder,
        CLUSTER_WIDTHS,
        CONN_GAP_MM,
      );
      const padRing = [CONN_RING_MM.motorInner, CONN_RING_MM.motorOuter];
      return (
        <React.Fragment key={centreDeg}>
          {axes.map((axis, i) => (
            <React.Fragment key={axis}>
              <MotorPads
                axis={axis}
                pos={polarToXY(padRing[i], centreDeg)}
                rot={faceOutward(centreDeg)}
              />
              <EncoderConnector
                axis={axis}
                pos={polarToXY(CONN_RING_MM.encoder, ffc[i])}
                rot={faceOutward(ffc[i])}
              />
            </React.Fragment>
          ))}
        </React.Fragment>
      );
    })}
  </board>
);
