import type { ChipProps } from "@tscircuit/props"

// Provisional pinout — the machine-side supply/control interface is not yet
// specified at either end (Control Electronics.md open item). VIN/GND carry
// board power; SIG1/SIG2 are spare until a control-link protocol is chosen.
const pinLabels = {
  pin1: ["VIN"],
  pin2: ["GND"],
  pin3: ["SIG1"],
  pin4: ["SIG2"]
} as const

export const B4B_XH_A_LF__SN_ = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C144395"
  ]
}}
      manufacturerPartNumber="B4B-XH-A(LF)(SN)"
      footprint={<footprint>
        <platedhole  portHints={["pin1"]} pcbX="3.750056mm" pcbY="0mm" outerDiameter="1.6999966mm" holeDiameter="0.999998mm" shape="circle" />
<platedhole  portHints={["pin2"]} pcbX="1.249934mm" pcbY="0mm" outerDiameter="1.6999966mm" holeDiameter="0.999998mm" shape="circle" />
<platedhole  portHints={["pin3"]} pcbX="-1.249934mm" pcbY="0mm" outerDiameter="1.6999966mm" holeDiameter="0.999998mm" shape="circle" />
<platedhole  portHints={["pin4"]} pcbX="-3.750056mm" pcbY="0mm" outerDiameter="1.6999966mm" holeDiameter="0.999998mm" shape="circle" />
<silkscreenpath route={[{"x":-6.223000000000184,"y":-2.158999999999878},{"x":-6.223000000000184,"y":-2.413000000000011},{"x":-4.9529999999999745,"y":-2.413000000000011}]} />
<silkscreenpath route={[{"x":6.222999999999956,"y":3.4289999999999736},{"x":6.222999999999956,"y":-1.0159999999999627}]} />
<silkscreenpath route={[{"x":4.698999999999955,"y":-2.413000000000011},{"x":6.222999999999956,"y":-2.413000000000011},{"x":6.222999999999956,"y":-2.158999999999878}]} />
<silkscreenpath route={[{"x":-2.7940000000000964,"y":-2.413000000000011},{"x":2.53999999999985,"y":-2.413000000000011}]} />
<silkscreenpath route={[{"x":6.222999999999956,"y":3.4289999999999736},{"x":-6.223000000000184,"y":3.4289999999999736},{"x":-6.223000000000184,"y":-1.0159999999999627}]} />
<silkscreentext text="{NAME}" pcbX="0mm" pcbY="4.556mm" anchorAlignment="center" fontSize="1mm" />
<courtyardoutline outline={[{"x":-6.600000000000136,"y":3.80600000000004},{"x":6.599999999999909,"y":3.80600000000004},{"x":6.599999999999909,"y":-2.7899999999999636},{"x":-6.600000000000136,"y":-2.7899999999999636},{"x":-6.600000000000136,"y":3.80600000000004}]} />
      </footprint>}
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C144395.obj?uuid=3dc2be3da48b4d969f321a0c2c608d12",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C144395.step?uuid=3dc2be3da48b4d969f321a0c2c608d12",
        pcbRotationOffset: 180,
        modelOriginPosition: { x: 3.7499872999999297, y: 2.700499100000014, z: -1.800005 },
      }}
      {...props}
    />
  )
}