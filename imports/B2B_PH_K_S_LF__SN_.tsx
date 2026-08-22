import type { ChipProps } from "@tscircuit/props"

// Labelled by hand to match the XH part this replaces, so the schematic reads
// as a motor lead rather than pin1/pin2.
const pinLabels = {
  pin1: ["MOTOR_A"],
  pin2: ["MOTOR_B"]
} as const

export const B2B_PH_K_S_LF__SN_ = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C131337"
  ]
}}
      manufacturerPartNumber="B2B-PH-K-S(LF)(SN)"
      footprint={<footprint>
        <platedhole  portHints={["pin2"]} pcbX="-0.999998mm" pcbY="0mm" outerDiameter="1.5999968mm" holeDiameter="0.9000236mm" shape="circle" />
<platedhole  portHints={["pin1"]} pcbX="0.999998mm" pcbY="0mm" outerDiameter="1.5999968mm" holeDiameter="0.9000236mm" shape="circle" />
<silkscreenpath route={[{"x":-2.921000000000049,"y":0.2540000000000191},{"x":-2.413000000000011,"y":0.2540000000000191},{"x":-2.413000000000011,"y":2.158999999999992},{"x":2.53999999999985,"y":2.158999999999992},{"x":2.53999999999985,"y":0.2540000000000191},{"x":2.9209999999998217,"y":0.2540000000000191}]} />
<silkscreenpath route={[{"x":3.000044799999955,"y":-0.3810000000000855},{"x":2.4920448000000306,"y":-0.3810000000000855},{"x":2.4920448000000306,"y":-1.1430000000001428},{"x":0.3330447999999251,"y":-1.1430000000001428},{"x":0.3330447999999251,"y":-1.6510000000000673}]} />
<silkscreenpath route={[{"x":-2.921000000000049,"y":-0.3810000000000855},{"x":-2.413000000000011,"y":-0.3810000000000855},{"x":-2.413000000000011,"y":-1.1430000000001428},{"x":-0.2540000000001328,"y":-1.1430000000001428},{"x":-0.2540000000001328,"y":-1.6510000000000673}]} />
<silkscreentext text="{NAME}" pcbX="0.016002mm" pcbY="3.8956mm" anchorAlignment="center" fontSize="1mm" />
<courtyardoutline outline={[{"x":-3.2565980000001673,"y":3.145599999999945},{"x":3.288601999999969,"y":3.145599999999945},{"x":3.288601999999969,"y":-1.9517999999999347},{"x":-3.2565980000001673,"y":-1.9517999999999347},{"x":-3.2565980000001673,"y":3.145599999999945}]} />
      </footprint>}
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C131337.obj?uuid=ee6b32b5c03144688a5663b32f9648c4",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C131337.step?uuid=ee6b32b5c03144688a5663b32f9648c4",
        pcbRotationOffset: 180,
        modelOriginPosition: { x: -0.9995, y: -0.0000012000000196854543, z: -0.000006999999999646178 },
      }}
      {...props}
    />
  )
}