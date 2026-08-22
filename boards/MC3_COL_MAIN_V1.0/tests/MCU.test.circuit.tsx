import { MCU } from "../MCU"

// Standalone harness for the MCU block. Builds the group by itself on a plain
// rectangular board so its internal placement can be checked without any
// interference from the round outline, the centre cutout or the other blocks.
// Run: tsci build boards/MC3_COL_MAIN_V1.0/tests/MCU.test.circuit.tsx
export default () => (
  <board width="90mm" height="90mm">
    <MCU />
  </board>
)
