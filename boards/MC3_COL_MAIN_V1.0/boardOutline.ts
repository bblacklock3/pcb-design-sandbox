// Board outline — a 64mm-diameter disc with a 22x22mm square beam-path cutout,
// both centred on the beam axis at (0,0).
//
// THIS FILE IS THE BOARD GEOMETRY. It is the only place the two dimensions are
// written down; everything else derives from them. Component placement lives in
// MC3_COL_MAIN_V1.0.tsx and reads these exports.
//
// Usable annulus, which is what placement actually has to respect:
//     on-axis (0/90/180/270)   11.00 -> 32mm  =  21.00mm of room
//     diagonal (45/135/...)    15.56 -> 32mm  =  16.44mm of room
// The cutout is SQUARE, so it reaches half-side/cos(45) on the diagonals versus
// half-side on the axes. The connector clusters sit on the diagonals, i.e. the
// worst case.
//
// The cutout is modelled as a sharp rectangle; the real one has 2mm corner
// radii. That is deliberate and conservative — a sharp rect keep-out is very
// slightly LARGER than the true cutout, never smaller, so nothing encroaches on
// the real hole.
//
// Relationship to the mechanical model: mechanical/Collimator_Main_PCB_V1.0.DXF
// is a SolidWorks export describing a 30mm-radius board with a 25x25mm cutout.
// Nothing in the build reads it — these dimensions are set here directly, and
// the two are free to differ while the design is in flux. Reconcile them before
// fab, in whichever direction is right by then. #tbd
//
// Mounting holes are not modelled yet — to be added as <platedhole /> elements
// once positions are settled.

export const BOARD_OUTER_RADIUS_MM = 32;
export const CUTOUT_HALF_SIDE_MM = 11;

// A regular polygon approximation of the circular board edge.
// 64 segments is smooth enough for both PCB fab and rendering.
const OUTLINE_SEGMENTS = 64;
export const boardOutline = Array.from({ length: OUTLINE_SEGMENTS }, (_, i) => {
  const angle = (i / OUTLINE_SEGMENTS) * 2 * Math.PI;
  return {
    x: BOARD_OUTER_RADIUS_MM * Math.cos(angle),
    y: BOARD_OUTER_RADIUS_MM * Math.sin(angle),
  };
});
