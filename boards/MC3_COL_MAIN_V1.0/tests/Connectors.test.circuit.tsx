import { MotorPads, PowerPads, EncoderConnector } from "../Connectors"

// Each connector is placed individually by whoever instantiates it, so this
// harness just spreads them out to confirm they build and wire correctly.
export default () => (
  <board width="80mm" height="80mm">
    <net name="VIN_PROT" />
    <net name="VIN_RAW" />
    <net name="V3_3" />
    <net name="GND" />
    <MotorPads axis="leaf1" pos={{ x: -22, y: 18 }} />
    <MotorPads axis="leaf2" pos={{ x: -22, y: 6 }} />
    <MotorPads axis="leaf3" pos={{ x: -22, y: -6 }} />
    <MotorPads axis="leaf4" pos={{ x: -22, y: -18 }} />
    <EncoderConnector axis="leaf1" pos={{ x: 10, y: 18 }} />
    <EncoderConnector axis="leaf2" pos={{ x: 10, y: 6 }} />
    <PowerPads pos={{ x: 15, y: -15 }} />
  </board>
)
