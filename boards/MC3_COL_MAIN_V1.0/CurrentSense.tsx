import { INA240A1DR } from "../../imports/INA240A1DR"
import { HoJLR1206_1W_100mR_1_ as Shunt100mOhm } from "../../imports/HoJLR1206_1W_100mR_1_"

// Low-side shunt + INA240 current sense, one per axis.
//
// Implements: COL-COTS-0022 (INA240) — JLC C2060769 (A1, 20 V/V)
//             COL-COTS-0023 (100 mOhm 1206 shunt) — JLC C2903496
// Layout constraints: docs/design/parts/INA240.md  (NOT YET WRITTEN — datasheet unread)
//
// Resolved: motor stall current is 1.65A (COL-COTS-0002). With this shunt and gain, stall
// maps to 3.30V (top of a 3.3V ADC) and the 0.83A max-power duty point to 1.66V, mid-scale.
//
// Shunt sits between PGND_<axis> (the DRV8212's own GND/EP net — see HBridge.tsx) and true
// board GND, so it reads total bridge current regardless of direction. IN_POS is on the
// PGND (driver) side, IN_NEG on the true-GND side — do not swap, or the sign is wrong for
// the assumed current-flow convention (not that it breaks the bidirectional amp, just the
// polarity of the ripple/mismatch reading downstream). REF1/REF2 share one VCC/2 divider
// generated once in Power.tsx, not duplicated per channel.
//
// BLOCKED, do not populate: docs/design/parts/INA240.md does not exist yet.
//
// This block does double duty. Beyond protection, COL-REQ-0013 wants a drive-side signal to
// cross-check the position sensor, and brush current-ripple counting would supply one from
// this shunt — now deprioritized to a "nice to have" (see COL-REQ-0002's velocity/dynamics
// digest for the more promising angle on that idea).
export const CurrentSense = ({
  axis,
  index,
}: {
  axis: string
  index: number
}) => {
  const x = -36 + index * 18
  const schX0 = -24 + index * 12
  return (
    <group name={`${axis}_sense`}>
      <Shunt100mOhm
        name={`R_${axis}_SHUNT`}
        schX={schX0}
        schY={-14}
        pcbX={x}
        pcbY={-16}
      />
      <trace from={`R_${axis}_SHUNT.pin1`} to={`net.PGND_${axis}`} />
      <trace from={`R_${axis}_SHUNT.pin2`} to="net.GND" />

      <INA240A1DR
        name={`U_${axis}_ISENSE`}
        schX={schX0}
        schY={-22}
        pcbX={x}
        pcbY={-28}
      />
      <trace from={`U_${axis}_ISENSE.IN_POS`} to={`net.PGND_${axis}`} />
      <trace from={`U_${axis}_ISENSE.IN_NEG`} to="net.GND" />
      <trace from={`U_${axis}_ISENSE.VS`} to="net.V3_3" />
      <trace from={`U_${axis}_ISENSE.GND`} to="net.GND" />
      <trace from={`U_${axis}_ISENSE.REF1`} to="net.VREF_MID" />
      <trace from={`U_${axis}_ISENSE.REF2`} to="net.VREF_MID" />
      <trace from={`U_${axis}_ISENSE.OUT`} to={`net.ISENSE_${axis}`} />

      <capacitor
        name={`C_${axis}_ISENSE_VS`}
        capacitance="100nF"
        footprint="0402"
        schX={schX0 + 4}
        schY={-22}
        pcbX={x + 6}
        pcbY={-28}
        decouplingFor={`U_${axis}_ISENSE.VS`}
        decouplingTo="net.GND"
      />
    </group>
  )
}
