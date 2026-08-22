// Polar placement helpers — FOR BOARD-EDGE CONNECTORS ONLY.
//
// This file holds the MATHS ONLY. Every tuning knob (ring radii, gaps, cluster
// angles) lives at the top of MC3_COL_MAIN_V1.0.tsx, and the board geometry
// lives in boardOutline.ts, so no dimension is written down twice.
//
// The rest of the board is placed in cartesian coordinates by hand. Connectors
// are the one thing polar coordinates genuinely suit: they live on the rim of a
// round board, they want to face outward, and they want even spacing along it.
// Do not spread this back into the blocks — hand-derived trigonometry is what
// made the earlier revisions of this board unplaceable.
//
// GEOMETRY THIS HAS TO RESPECT. The board is a disc with a SQUARE cutout, so
// the room between cutout and rim depends on angle -- the cutout reaches
// half-side/cos(45) on the diagonals versus half-side on the axes. Clusters on
// the diagonals therefore sit on the WORST case. Current numbers are in
// boardOutline.ts; do not duplicate them here, they have moved once already.

import { polarToXY } from "./axes";
export { polarToXY };

/**
 * Lay a row of connectors along an arc, centred on `centreDeg`.
 *
 * Returns one angle per connector, spaced so their *arc widths* clear each
 * other by `gapMm`. Widths differ (a 4-pin encoder is twice a 2-pin motor), so
 * even angular spacing would leave the big ones touching and the small ones
 * far apart — this spaces by physical size instead.
 */
export function arcSlots(
  centreDeg: number,
  radiusMm: number,
  widthsMm: number[],
  gapMm: number,
): number[] {
  const totalArc =
    widthsMm.reduce((a, b) => a + b, 0) + gapMm * (widthsMm.length - 1);
  const degPerMm = 180 / (Math.PI * radiusMm);
  let cursor = -totalArc / 2;
  return widthsMm.map((w) => {
    const centre = cursor + w / 2;
    cursor += w + gapMm;
    return centreDeg + centre * degPerMm;
  });
}

/**
 * Rotation that puts a connector's long axis TANGENTIAL to the rim, so it hugs
 * the board edge rather than pointing at the cutout. The imported connectors
 * have their pin row along +X, so tangential is the board angle + 90.
 */
export const faceOutward = (angleDeg: number) => angleDeg + 90;
