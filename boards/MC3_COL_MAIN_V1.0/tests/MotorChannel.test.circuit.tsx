import { MotorChannel } from "../MotorChannel"

// Renders the same channel at all four cardinal rotations. Every electrical
// distance (Kelvin pair, decoupling legs) must come out identical at each
// angle -- that is the check that the block rotates as a rigid body.
export default () => (
  <board width="120mm" height="120mm">
    <net name="VM" />
    <net name="V3_3" />
    <net name="GND" />
    <net name="VREF_MID" />
    <MotorChannel name="r0" pos={{ x: -30, y: 30 }} rot={0} />
    <MotorChannel name="r90" pos={{ x: 30, y: 30 }} rot={90} />
    <MotorChannel name="r180" pos={{ x: -30, y: -30 }} rot={180} />
    <MotorChannel name="r270" pos={{ x: 30, y: -30 }} rot={-90} />
  </board>
)
