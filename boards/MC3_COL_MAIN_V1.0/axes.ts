// Shared axis list — its own module so MCU.tsx/Connectors.tsx don't have to
// import back from MC3_COL_MAIN_V1.0.tsx (that was a circular import).
export const AXES = ["leaf1", "leaf2", "leaf3", "leaf4", "yaw"] as const
