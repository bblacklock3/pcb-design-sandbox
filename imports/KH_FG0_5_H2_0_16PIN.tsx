import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["pin1"],
  pin2: ["pin2"],
  pin3: ["pin3"],
  pin4: ["pin4"],
  pin5: ["pin5"],
  pin6: ["pin6"],
  pin7: ["pin7"],
  pin8: ["pin8"],
  pin9: ["pin9"],
  pin10: ["pin10"],
  pin11: ["pin11"],
  pin12: ["pin12"],
  pin13: ["pin13"],
  pin14: ["pin14"],
  pin15: ["pin15"],
  pin16: ["pin16"],
  pin17: ["pin17"],
  pin18: ["pin18"]
} as const

export const KH_FG0_5_H2_0_16PIN = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C2797209"
  ]
}}
      manufacturerPartNumber="KH-FG0.5-H2.0-16PIN"
      footprint={<footprint>
        <smtpad portHints={["pin16"]} pcbX="-3.749929mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin15"]} pcbX="-3.249803mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin14"]} pcbX="-2.749931mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin13"]} pcbX="-2.249805mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin18"]} pcbX="5.449951mm" pcbY="-1.30004185mm" width="1.999996mm" height="1.499997mm" shape="rect" />
<smtpad portHints={["pin17"]} pcbX="-5.449951mm" pcbY="-1.30004185mm" width="1.999996mm" height="1.499997mm" shape="rect" />
<smtpad portHints={["pin12"]} pcbX="-1.749933mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin11"]} pcbX="-1.250061mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin10"]} pcbX="-0.749935mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin9"]} pcbX="-0.250063mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin8"]} pcbX="0.250063mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin7"]} pcbX="0.749935mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin6"]} pcbX="1.250061mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin5"]} pcbX="1.749933mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin4"]} pcbX="2.250059mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin3"]} pcbX="2.749931mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin2"]} pcbX="3.250057mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<smtpad portHints={["pin1"]} pcbX="3.749929mm" pcbY="1.15004215mm" width="0.2999994mm" height="1.7999964mm" shape="rect" />
<silkscreenpath route={[{"x":-6.199911400000019,"y":0.5499671499999295},{"x":-4.130928999999924,"y":0.5499671499999295}]} />
<silkscreenpath route={[{"x":6.200012999999899,"y":0.5499671499999295},{"x":4.131106799999998,"y":0.5499671499999295}]} />
<silkscreenpath route={[{"x":-6.199911400000019,"y":-4.450048250000123},{"x":-6.199911400000019,"y":-2.2811168499999894}]} />
<silkscreenpath route={[{"x":-6.199911400000019,"y":-0.3188398500000176},{"x":-6.199911400000019,"y":0.5499671499999295}]} />
<silkscreenpath route={[{"x":6.200012999999899,"y":-4.450048250000123},{"x":-6.199911400000019,"y":-4.450048250000123}]} />
<silkscreenpath route={[{"x":6.200012999999899,"y":-0.3188906500001849},{"x":6.200012999999899,"y":0.5499671499999295}]} />
<silkscreenpath route={[{"x":6.200012999999899,"y":-4.450048250000123},{"x":6.200012999999899,"y":-2.28119305000007}]} />
<silkscreenpath route={[{"x":4.787010999999893,"y":1.1950001499999416},{"x":4.782683579938521,"y":1.1621301312718515},{"x":4.769996226280455,"y":1.1315001499999653},{"x":4.749813561210658,"y":1.1051975887891103},{"x":4.723510999999917,"y":1.0850149237193136},{"x":4.6928810187280305,"y":1.0723275700611339},{"x":4.66001099999994,"y":1.068000149999989},{"x":4.62714098127185,"y":1.0723275700611339},{"x":4.596510999999964,"y":1.0850149237193136},{"x":4.570208438789223,"y":1.1051975887891103},{"x":4.550025773719426,"y":1.1315001499999653},{"x":4.537338420061133,"y":1.1621301312718515},{"x":4.533010999999988,"y":1.1950001499999416},{"x":4.537338420061133,"y":1.2278701687278044},{"x":4.550025773719426,"y":1.258500149999918},{"x":4.570208438789223,"y":1.2848027112105456},{"x":4.596510999999964,"y":1.304985376280456},{"x":4.62714098127185,"y":1.317672729938522},{"x":4.66001099999994,"y":1.3220001499998943},{"x":4.6928810187280305,"y":1.317672729938522},{"x":4.723510999999917,"y":1.304985376280456},{"x":4.749813561210658,"y":1.2848027112105456},{"x":4.769996226280455,"y":1.258500149999918},{"x":4.782683579938521,"y":1.2278701687278044},{"x":4.787010999999893,"y":1.1950001499999416}]} />
<silkscreentext text="{NAME}" pcbX="0.000381mm" pcbY="3.05352015mm" anchorAlignment="center" fontSize="1mm" />
<courtyardoutline outline={[{"x":-6.701219000000037,"y":2.3035201499999403},{"x":6.7019809999999325,"y":2.3035201499999403},{"x":6.7019809999999325,"y":-4.698879850000026},{"x":-6.701219000000037,"y":-4.698879850000026},{"x":-6.701219000000037,"y":2.3035201499999403}]} />
      </footprint>}
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2797209.obj?uuid=5e5b2a1af50c4b7ca8dd8a0f936934fd",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2797209.step?uuid=5e5b2a1af50c4b7ca8dd8a0f936934fd",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: -0.00007619999996677507, y: -1.1500155499998757, z: 0 },
      }}
      {...props}
    />
  )
}