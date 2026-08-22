// HAND-EDIT: the name silkscreen pcbY is NEGATED from the vendor footprint
// (was +3.0117054mm). On this board the connector is rotated to face outward,
// which maps footprint local +y to RADIALLY INWARD, putting the label on top of
// the pull-up resistor. Negating it puts the label outboard toward the rim.
// A re-import of C425129 will silently revert this.

import type { ChipProps } from "@tscircuit/props"

// Labelled by hand. pin1-4 are the 0.5mm-pitch signal contacts; pin5/pin6 are
// the mechanical hold-down tabs, which carry no signal and are soldered for
// retention only.
const pinLabels = {
  pin1: ["VIN"],
  pin2: ["GND"],
  pin3: ["SIG1"],
  pin4: ["SIG2"],
  pin5: ["MP1"],
  pin6: ["MP2"]
} as const

export const AYF530435 = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C425129"
  ]
}}
      manufacturerPartNumber="AYF530435"
      footprint={<footprint>
        <smtpad portHints={["pin1"]} pcbX="-0.750062mm" pcbY="1.2499594mm" width="0.2999994mm" height="0.7999984mm" shape="rect" />
<smtpad portHints={["pin2"]} pcbX="-0.25019mm" pcbY="1.2499594mm" width="0.2999994mm" height="0.7999984mm" shape="rect" />
<smtpad portHints={["pin3"]} pcbX="0.249936mm" pcbY="1.2499594mm" width="0.2999994mm" height="0.7999984mm" shape="rect" />
<smtpad portHints={["pin4"]} pcbX="0.749808mm" pcbY="1.2499594mm" width="0.2999994mm" height="0.7999984mm" shape="rect" />
<smtpad portHints={["pin6"]} pcbX="-1.75006mm" pcbY="-1.2499086mm" width="0.3999992mm" height="0.8001mm" shape="rect" />
<smtpad portHints={["pin5"]} pcbX="1.75006mm" pcbY="-1.2499086mm" width="0.3999992mm" height="0.8001mm" shape="rect" />
<silkscreenpath route={[{"x":1.9488911999999345,"y":1.3918945999998869},{"x":1.131011199999989,"y":1.3918945999998869}]} />
<silkscreenpath route={[{"x":1.9488911999999345,"y":1.3918945999998869},{"x":1.9489165999999614,"y":-0.618109000000004}]} />
<silkscreenpath route={[{"x":-1.9494500000000698,"y":-0.6197346000000152},{"x":-1.9494500000000698,"y":0.787425399999961},{"x":-1.9494500000000698,"y":1.3919453999999405}]} />
<silkscreenpath route={[{"x":1.3819123999999192,"y":-1.8080990000000838},{"x":-1.382496600000195,"y":-1.8080990000000838}]} />
<silkscreenpath route={[{"x":-1.9501104000001988,"y":1.3918945999998869},{"x":-1.1312652000001435,"y":1.3918945999998869}]} />
<silkscreenpath route={[{"x":-1.1600179999999227,"y":1.8001233999999613},{"x":-1.164449278142797,"y":1.766464500822508},{"x":-1.1774411282887058,"y":1.735099400000081},{"x":-1.1981081773202504,"y":1.7081655773201874},{"x":-1.225042000000144,"y":1.6874985282886428},{"x":-1.256407100822571,"y":1.674506678142734},{"x":-1.2900660000000244,"y":1.6700753999998597},{"x":-1.3237248991775914,"y":1.674506678142734},{"x":-1.3550900000000183,"y":1.6874985282886428},{"x":-1.3820238226797983,"y":1.7081655773201874},{"x":-1.4026908717113429,"y":1.735099400000081},{"x":-1.4156827218572516,"y":1.766464500822508},{"x":-1.4201140000000123,"y":1.8001233999999613},{"x":-1.4156827218572516,"y":1.8337822991774146},{"x":-1.4026908717113429,"y":1.8651473999999553},{"x":-1.3820238226797983,"y":1.8920812226797352},{"x":-1.3550900000000183,"y":1.9127482717112798},{"x":-1.3237248991775914,"y":1.9257401218571886},{"x":-1.2900660000000244,"y":1.930171400000063},{"x":-1.256407100822571,"y":1.9257401218571886},{"x":-1.225042000000144,"y":1.9127482717112798},{"x":-1.1981081773202504,"y":1.8920812226797352},{"x":-1.1774411282887058,"y":1.8651473999999553},{"x":-1.164449278142797,"y":1.8337822991774146},{"x":-1.1600179999999227,"y":1.8001233999999613}]} />
<silkscreentext text="{NAME}" pcbX="-0.01143mm" pcbY="-3.0117054mm" anchorAlignment="center" fontSize="1mm" />
<courtyardoutline outline={[{"x":-2.2807300000000623,"y":2.261705399999869},{"x":2.2578699999999117,"y":2.261705399999869},{"x":2.2578699999999117,"y":-2.0482946000001903},{"x":-2.2807300000000623,"y":-2.0482946000001903},{"x":-2.2807300000000623,"y":2.261705399999869}]} />
      </footprint>}
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C425129.obj?uuid=d5735a7217bf407da74b43d5e0d31d4c",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C425129.step?uuid=d5735a7217bf407da74b43d5e0d31d4c",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: 0.0000762000000804619, y: 0.09997490000000653, z: -0.02 },
      }}
      {...props}
    />
  )
}