import { AXES } from "./axes"
import { STM32F411RET6 } from "../../imports/STM32F411RET6"

// MCU, its support passives and the debug/programming interface.
//
// Resolved 2026-08-16 (COL-SEARCH-0008): STM32F411RET6, LQFP64, JLC C94355 —
// chosen for "ideal for initial development" over staying on the MC2's
// STM32F103 or moving to the motor-control-focused STM32G4 family: cheaper
// than an F103 with the same pin count despite being strictly more capable
// (faster core, 4x flash/RAM, USB OTG vs. F103's device-only, hardware
// quadrature-encoder-input timers — a free head start if the still-open
// sensor mezzanine lands on an incremental encoder). G4's extra op-amps and
// comparators would help ripple counting, but that's now a "nice to have"
// (COL-REQ-0002) and doesn't justify G4's 2.5x cost and thinner stock for a
// first prototype. Same Cortex-M/CubeIDE/HAL tooling family as MC2, so team
// familiarity carries over even though the F103 firmware itself does not —
// MC3's brushed H-bridge control shares little with MC2's three-phase BLDC
// commutation.
//
// Five motor channels, PH/EN interface (HBridge.tsx): EN is a PWM pin per
// axis, PH a plain GPIO. Five ISENSE analog inputs (CurrentSense.tsx) land
// on genuine ADC1-capable pins. Exact timer/AF mapping (which TIMx_CHy each
// EN pin uses) is a firmware/CubeMX decision against the reference manual,
// not a hardware constraint — these are reasonable, not verified-optimal,
// pin choices. #tbd verify AF mapping during firmware bring-up.
//
// The mezzanine's own signal pins are NOT wired here — that connector's
// interior pinout is still undecided (Mezzanine.tsx) and deliberately not
// forced by this MCU choice, beyond leaving spare GPIO/ADC margin.
const EN_PINS: Record<string, string> = {
  leaf1: "PA0",
  leaf2: "PA1",
  leaf3: "PA2",
  leaf4: "PA3",
  yaw: "PA6",
}
const PH_PINS: Record<string, string> = {
  leaf1: "PB0",
  leaf2: "PB1",
  leaf3: "PB2",
  leaf4: "PB10",
  yaw: "PB12",
}
const ISENSE_PINS: Record<string, string> = {
  leaf1: "PC0",
  leaf2: "PC1",
  leaf3: "PC2",
  leaf4: "PC3",
  yaw: "PC4",
}

export const MCU = () => (
  <group name="mcu">
    <STM32F411RET6 name="U_MCU" schX={0} schY={14} pcbX={0} pcbY={14} />

    {/* Power */}
    <trace from="U_MCU.VDD1" to="net.V3_3" />
    <trace from="U_MCU.VDD2" to="net.V3_3" />
    <trace from="U_MCU.VDD3" to="net.V3_3" />
    <trace from="U_MCU.VDD4" to="net.V3_3" />
    <trace from="U_MCU.VSS1" to="net.GND" />
    <trace from="U_MCU.VSS2" to="net.GND" />
    <trace from="U_MCU.VSS3" to="net.GND" />
    <trace from="U_MCU.VSS4" to="net.GND" />
    <trace from="U_MCU.VBAT" to="net.V3_3" />
    <trace from="U_MCU.VDDA" to="net.V3_3" />
    <trace from="U_MCU.VSSA" to="net.GND" />
    {[1, 2, 3, 4].map((i) => (
      <capacitor
        key={i}
        name={`C_MCU_VDD${i}`}
        capacitance="100nF"
        footprint="0402"
        schX={-9 + i * 3}
        schY={26}
        pcbX={-9 + i * 3}
        pcbY={26}
        decouplingFor={`U_MCU.VDD${i}`}
        decouplingTo="net.GND"
      />
    ))}
    <capacitor
      name="C_MCU_VDDA"
      capacitance="1uF"
      footprint="0603"
      schX={6}
      schY={26}
      pcbX={6}
      pcbY={26}
      decouplingFor="U_MCU.VDDA"
      decouplingTo="net.GND"
    />
    <capacitor
      name="C_MCU_VCAP"
      capacitance="2.2uF"
      footprint="0603"
      schX={10}
      schY={26}
      pcbX={10}
      pcbY={26}
    />
    <trace from="U_MCU.VCAP_1" to="C_MCU_VCAP.pos" />
    <trace from="net.GND" to="C_MCU_VCAP.neg" />

    {/* NRST: pull-up + reset button, standard bring-up convenience */}
    <resistor
      name="R_NRST"
      resistance="10k"
      footprint="0402"
      schX={-18}
      schY={14}
      pcbX={-18}
      pcbY={14}
      pullupFor="U_MCU.NRST"
      pullupTo="net.V3_3"
    />
    <pushbutton
      name="SW_RESET"
      footprint="pushbutton"
      schX={-24}
      schY={14}
      pcbX={-24}
      pcbY={14}
    />
    <trace from="U_MCU.NRST" to="SW_RESET.pin1" />
    <trace from="net.GND" to="SW_RESET.pin2" />

    {/* BOOT0: pulled low -> always boots from flash. SWD is the sole
        programming/debug path for this prototype, no bootloader jumper. */}
    <resistor
      name="R_BOOT0"
      resistance="10k"
      footprint="0402"
      schX={-18}
      schY={8}
      pcbX={-18}
      pcbY={8}
      pulldownFor="U_MCU.BOOT0"
      pulldownTo="net.GND"
    />

    {/* HSE crystal — 8MHz, standard load caps */}
    <crystal
      name="XT1"
      frequency="8MHz"
      loadCapacitance="18pF"
      footprint="crystal_3225_4pin"
      schX={18}
      schY={14}
      pcbX={18}
      pcbY={14}
    />
    <trace from="XT1.pin1" to="U_MCU.PH0_OSC_IN" />
    <trace from="XT1.pin2" to="U_MCU.PH1_OSC_OUT" />
    <capacitor
      name="C_XT1_A"
      capacitance="18pF"
      footprint="0402"
      schX={16}
      schY={8}
      pcbX={16}
      pcbY={8}
    />
    <capacitor
      name="C_XT1_B"
      capacitance="18pF"
      footprint="0402"
      schX={20}
      schY={8}
      pcbX={20}
      pcbY={8}
    />
    <trace from="XT1.pin1" to="C_XT1_A.pos" />
    <trace from="net.GND" to="C_XT1_A.neg" />
    <trace from="XT1.pin2" to="C_XT1_B.pos" />
    <trace from="net.GND" to="C_XT1_B.neg" />

    {/* SWD debug/programming header — the primary dev interface */}
    <pinheader
      name="J_SWD"
      pinCount={4}
      gender="male"
      pitch="2.54mm"
      footprint="pinrow4"
      showSilkscreenPinLabels
      pinLabels={["V3_3", "SWDIO", "SWCLK", "GND"]}
      schX={26}
      schY={20}
      pcbX={26}
      pcbY={20}
    />
    <trace from="J_SWD.V3_3" to="net.V3_3" />
    <trace from="J_SWD.SWDIO" to="U_MCU.PA13" />
    <trace from="J_SWD.SWCLK" to="U_MCU.PA14" />
    <trace from="J_SWD.GND" to="net.GND" />

    {/* Per-axis motor control and current-sense wiring */}
    {AXES.map((axis) => (
      <group key={axis}>
        <trace from={`U_MCU.${EN_PINS[axis]}`} to={`net.EN_${axis}`} />
        <trace from={`U_MCU.${PH_PINS[axis]}`} to={`net.PH_${axis}`} />
        <trace
          from={`U_MCU.${ISENSE_PINS[axis]}`}
          to={`net.ISENSE_${axis}`}
        />
      </group>
    ))}
  </group>
)
