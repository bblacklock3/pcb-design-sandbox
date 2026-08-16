import { DRV8212DSGR } from "../../imports/DRV8212DSGR"

// DRV8212 H-bridge + bypass caps, one per axis.
//
// Implements: COL-COTS-0021 (DRV8212) — JLC C2843766 (DSGR, PH/EN), WSON-8 2x2mm
// Layout constraints: docs/design/parts/DRV8212.md  (NOT YET WRITTEN — datasheet unread)
//
// Resolved: motor is 3V DC, 1.65A stall (COL-COTS-0002). This part's 1.65-5.5V range
// and 4A peak clear both with margin (41% of peak at stall). No 24V-rail risk — the MC3
// does not inherit the MC2's motor rail, which was sized for a different motor class.
//
// MODE (pin7) strapped HIGH to VCC here -> PH/EN interface: EN is the PWM/speed
// pin, PH is the direction pin. MODE=low would select PWM IN1/IN2 instead — a
// firmware-level tradeoff, not a hardware one, if that turns out to be preferred.
//
// Low-side current sense: GND (pin4) and the thermal pad EP (pin9) are the SAME
// net as CurrentSense.tsx's shunt high side — NOT tied to true board GND directly.
// Tying EP to true GND here would bypass the shunt and corrupt the current reading.
export const HBridge = ({
  axis,
  index,
}: {
  axis: string
  index: number
}) => {
  const x = -36 + index * 18
  const schX0 = -24 + index * 12
  return (
    <group name={`${axis}_bridge`}>
      <DRV8212DSGR
        name={`U_${axis}_DRV`}
        schX={schX0}
        schY={-4}
        pcbX={x}
        pcbY={-5}
      />
      <trace from={`U_${axis}_DRV.VM`} to="net.VM" />
      <trace from={`U_${axis}_DRV.VCC`} to="net.V3_3" />
      <trace from={`U_${axis}_DRV.MODE`} to="net.V3_3" />
      <trace from={`U_${axis}_DRV.GND`} to={`net.PGND_${axis}`} />
      <trace from={`U_${axis}_DRV.EP`} to={`net.PGND_${axis}`} />
      <trace from={`U_${axis}_DRV.OUT1`} to={`net.MOTOR_A_${axis}`} />
      <trace from={`U_${axis}_DRV.OUT2`} to={`net.MOTOR_B_${axis}`} />
      <trace from={`U_${axis}_DRV.EN`} to={`net.EN_${axis}`} />
      <trace from={`U_${axis}_DRV.PH`} to={`net.PH_${axis}`} />

      <capacitor
        name={`C_${axis}_VM`}
        capacitance="1uF"
        footprint="0603"
        schX={schX0 - 3}
        schY={-8}
        pcbX={x - 5}
        pcbY={-5}
        decouplingFor={`U_${axis}_DRV.VM`}
        decouplingTo={`net.PGND_${axis}`}
      />
      <capacitor
        name={`C_${axis}_VCC`}
        capacitance="100nF"
        footprint="0402"
        schX={schX0 + 3}
        schY={-8}
        pcbX={x + 5}
        pcbY={-5}
        decouplingFor={`U_${axis}_DRV.VCC`}
        decouplingTo={`net.PGND_${axis}`}
      />
    </group>
  )
}
