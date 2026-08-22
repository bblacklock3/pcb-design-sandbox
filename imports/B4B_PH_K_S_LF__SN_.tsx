import type { ChipProps } from "@tscircuit/props"

// Labelled by hand to match the XH 4-pin convention used for the machine
// interface. For the encoder this is VIN / GND / signal / spare.
const pinLabels = {
  pin1: ["VIN"],
  pin2: ["GND"],
  pin3: ["SIG1"],
  pin4: ["SIG2"]
} as const

export const B4B_PH_K_S_LF__SN_ = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C131334"
  ]
}}
      manufacturerPartNumber="B4B-PH-K-S(LF)(SN)"
      footprint={<footprint>
        <platedhole  portHints={["pin2"]} pcbX="0.999998mm" pcbY="0mm" outerDiameter="1.5999968mm" holeDiameter="0.999998mm" shape="circle" />
<platedhole  portHints={["pin1"]} pcbX="2.999994mm" pcbY="0mm" outerDiameter="1.5999968mm" holeDiameter="0.999998mm" shape="circle" />
<platedhole  portHints={["pin3"]} pcbX="-0.999998mm" pcbY="0mm" outerDiameter="1.5999968mm" holeDiameter="0.999998mm" shape="circle" />
<platedhole  portHints={["pin4"]} pcbX="-2.999994mm" pcbY="0mm" outerDiameter="1.5999968mm" holeDiameter="0.999998mm" shape="circle" />
<silkscreenpath route={[{"x":4.6451520000001665,"y":-1.0159999999999627},{"x":4.632914056066738,"y":-1.1089564129629252},{"x":4.597034219921738,"y":-1.1955780000000686},{"x":4.5399576431038895,"y":-1.2699616431038976},{"x":4.465573999999947,"y":-1.3270382199217465},{"x":4.378952412963031,"y":-1.3629180560666327},{"x":4.285996000000068,"y":-1.3751560000000609},{"x":4.193039587037106,"y":-1.3629180560666327},{"x":4.106417999999962,"y":-1.3270382199217465},{"x":4.032034356896133,"y":-1.2699616431038976},{"x":3.974957780078398,"y":-1.1955780000000686},{"x":3.9390779439333983,"y":-1.1089564129629252},{"x":3.92683999999997,"y":-1.0159999999999627},{"x":3.9390779439333983,"y":-0.9230435870371139},{"x":3.974957780078398,"y":-0.8364220000000842},{"x":4.032034356896133,"y":-0.7620383568961415},{"x":4.106417999999962,"y":-0.7049617800784063},{"x":4.193039587037106,"y":-0.6690819439334064},{"x":4.285996000000068,"y":-0.6568439999999782},{"x":4.378952412963031,"y":-0.6690819439334064},{"x":4.465573999999947,"y":-0.7049617800784063},{"x":4.5399576431038895,"y":-0.7620383568961415},{"x":4.597034219921738,"y":-0.8364220000000842},{"x":4.632914056066738,"y":-0.9230435870371139},{"x":4.6451520000001665,"y":-1.0159999999999627}]} />
<silkscreentext text="{NAME}" pcbX="0.009398mm" pcbY="3.794mm" anchorAlignment="center" fontSize="1mm" />
<courtyardoutline outline={[{"x":-5.244401999999923,"y":3.0439999999999827},{"x":5.263198000000102,"y":3.0439999999999827},{"x":5.263198000000102,"y":-1.9517999999999347},{"x":-5.244401999999923,"y":-1.9517999999999347},{"x":-5.244401999999923,"y":3.0439999999999827}]} />
      </footprint>}
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C131334.obj?uuid=3b95b8b4d5d24ff4a871a43c952e432a",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C131334.step?uuid=3b95b8b4d5d24ff4a871a43c952e432a",
        pcbRotationOffset: 180,
        modelOriginPosition: { x: 2.9999873000000434, y: -0.0000013000000308460713, z: -0.000005999999999950489 },
      }}
      {...props}
    />
  )
}