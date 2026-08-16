import { AMS1117_3_3 } from "../../imports/AMS1117_3_3"

// Power input and rails — PROTOTYPE architecture, not a final decision.
//
// The board's true incoming supply is still unspecified at the machine end
// (Control Electronics.md open item) and the MC2's 24VDC rail is explicitly
// NOT a default here (that rail was sized for the MC2's BLDC motors, a
// different class than this board's brushed leaf motors — COL-COTS-0021).
//
// For this first prototype: 5V in via the machine-interface connector
// (Connectors.tsx), used directly as VM for all five DRV8212 bridges
// (COL-COTS-0021, 1.65-5.5V range) and regulated down to 3.3V logic for the
// MCU and analog. The motor's own 3V rating is reached by PWM duty control
// in firmware, not by a separate regulated motor rail — this is the normal
// mode of operation for a PWM H-bridge driver, not a simplification that
// costs anything. Revisit this file once the machine-side supply is real.
export const Power = () => (
  <group name="power">
    <net name="VIN_RAW" />
    <net name="VM" />
    <net name="V3_3" />
    <net name="GND" />

    {/* VM = VIN directly. DRV8212 firmware duty-cycles down to the motor's
        3V rating; see comment above. */}
    <trace from="net.VIN_RAW" to="net.VM" />

    <capacitor
      name="C_BULK_IN"
      capacitance="10uF"
      footprint="0805"
      schX={-46}
      schY={4}
      pcbX={-46}
      pcbY={4}
    />
    <trace from="net.VIN_RAW" to="C_BULK_IN.pos" />
    <trace from="net.GND" to="C_BULK_IN.neg" />

    <AMS1117_3_3
      name="U_REG"
      schX={-38}
      schY={4}
      pcbX={-38}
      pcbY={4}
    />
    <trace from="net.VIN_RAW" to="U_REG.VIN" />
    <trace from="net.GND" to="U_REG.GND" />
    <trace from="net.V3_3" to="U_REG.VOUT1" />
    <trace from="net.V3_3" to="U_REG.VOUT2" />

    <capacitor
      name="C_REG_IN"
      capacitance="1uF"
      footprint="0402"
      schX={-42}
      schY={-4}
      pcbX={-42}
      pcbY={-4}
      decouplingFor="U_REG.VIN"
      decouplingTo="net.GND"
    />
    <capacitor
      name="C_REG_OUT"
      capacitance="10uF"
      footprint="0805"
      schX={-34}
      schY={-4}
      pcbX={-34}
      pcbY={-4}
      decouplingFor="U_REG.VOUT1"
      decouplingTo="net.GND"
    />

    {/* Shared VCC/2 reference for all five INA240 bidirectional current-sense
        amps (CurrentSense.tsx) — generated once here, not per-channel, so the
        five channels don't fight over five independent divider outputs on one
        net. Simple resistor-divider reference, not buffered — an accepted
        simplification for a first prototype (see COL-COTS-0022). */}
    <net name="VREF_MID" />
    <resistor
      name="R_VREF_HI"
      resistance="10k"
      footprint="0402"
      schX={-26}
      schY={4}
      pcbX={-26}
      pcbY={4}
    />
    <resistor
      name="R_VREF_LO"
      resistance="10k"
      footprint="0402"
      schX={-26}
      schY={-4}
      pcbX={-26}
      pcbY={-4}
    />
    <trace from="net.V3_3" to="R_VREF_HI.pin1" />
    <trace from="R_VREF_HI.pin2" to="net.VREF_MID" />
    <trace from="R_VREF_LO.pin1" to="net.VREF_MID" />
    <trace from="R_VREF_LO.pin2" to="net.GND" />
    <capacitor
      name="C_VREF"
      capacitance="100nF"
      footprint="0402"
      schX={-20}
      schY={0}
      pcbX={-20}
      pcbY={0}
      decouplingFor="R_VREF_LO.pin1"
      decouplingTo="net.GND"
    />
  </group>
)
