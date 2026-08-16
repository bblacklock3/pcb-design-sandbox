import { HBridge } from "./HBridge"
import { CurrentSense } from "./CurrentSense"

// One axis: H-bridge + low-side shunt + sense amplifier.
// Instantiated five times — four leaves plus yaw.
//
// Implements: COL-COTS-0021 (DRV8212 H-bridge) · COL-COTS-0022 (INA240 sense amp) · COL-COTS-0023 (shunt)
// Build rung: Projects/MC3 Collimator/05 Builds/Main-Board-01/
//
// NOT YET IDENTICAL ACROSS AXES. The yaw motor is unselected and its load is two orders
// of magnitude larger than a leaf's (COL-CALC-0008), so it may not share this topology.
// Treat the fifth instance as provisional until the yaw motor exists.
export const MotorChannel = ({
  name,
  index,
}: {
  name: string
  index: number
}) => (
  <group name={name}>
    <HBridge axis={name} index={index} />
    <CurrentSense axis={name} index={index} />
  </group>
)
