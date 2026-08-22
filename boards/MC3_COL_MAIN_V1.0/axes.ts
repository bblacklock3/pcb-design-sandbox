// Shared axis list and polar-placement helpers for the round board (see
// boardOutline.ts). Its own module so MCU.tsx/Connectors.tsx don't have to
// import back from MC3_COL_MAIN_V1.0.tsx (that was a circular import).
export const AXES = ["leaf1", "leaf2", "leaf3", "leaf4", "yaw"] as const

// Five motor channels, evenly spaced 72 degrees apart around the board.
// The 72-degree gaps between them hold MCU/Power/connectors (see below).
export const AXIS_ANGLE_DEG: Record<string, number> = {
  leaf1: 90,
  leaf2: 162,
  leaf3: 234,
  leaf4: 306,
  yaw: 18,
}

// Angles for the non-motor clusters, one per inter-channel gap.
// A SQUARE cutout reaches further on the diagonals than on the axes, so the
// axis directions (0/90/180/270) have the most radial room and the diagonals
// the least. See boardOutline.ts for the current numbers.
export const MCU_ANGLE_DEG = 270
export const POWER_ANGLE_DEG = 198 // between leaf2 (162) and leaf3 (234)
export const MACHINE_CONNECTOR_ANGLE_DEG = 54 // between yaw (18) and leaf1 (90)
export const MEZZANINE_ANGLE_DEG = 342 // between leaf4 (306) and yaw (18+360)

// Converts (radius from board center, angle in degrees, 0=+X axis, CCW) to
// board-local pcbX/pcbY. Matches boardOutline.ts's coordinate frame, which is
// the beam axis (boardOutline.ts).
export function polarToXY(radiusMm: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180
  return { x: radiusMm * Math.cos(rad), y: radiusMm * Math.sin(rad) }
}
