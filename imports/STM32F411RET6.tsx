import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["VBAT"],
  pin2: ["PC13"],
  pin3: ["PC14-OSC32_IN"],
  pin4: ["PC15_OSC32_OUT"],
  pin5: ["PH0_OSC_IN"],
  pin6: ["PH1_OSC_OUT"],
  pin7: ["NRST"],
  pin8: ["PC0"],
  pin9: ["PC1"],
  pin10: ["PC2"],
  pin11: ["PC3"],
  pin12: ["VSSA"],
  pin13: ["VDDA"],
  pin14: ["PA0"],
  pin15: ["PA1"],
  pin16: ["PA2"],
  pin17: ["PA3"],
  pin18: ["VSS1"],
  pin19: ["VDD1"],
  pin20: ["PA4"],
  pin21: ["PA5"],
  pin22: ["PA6"],
  pin23: ["PA7"],
  pin24: ["PC4"],
  pin25: ["PC5"],
  pin26: ["PB0"],
  pin27: ["PB1"],
  pin28: ["PB2"],
  pin29: ["PB10"],
  pin30: ["VCAP_1"],
  pin31: ["VSS2"],
  pin32: ["VDD2"],
  pin33: ["PB12"],
  pin34: ["PB13"],
  pin35: ["PB14"],
  pin36: ["PB15"],
  pin37: ["PC6"],
  pin38: ["PC7"],
  pin39: ["PC8"],
  pin40: ["PC9"],
  pin41: ["PA8"],
  pin42: ["PA9"],
  pin43: ["PA10"],
  pin44: ["PA11"],
  pin45: ["PA12"],
  pin46: ["PA13"],
  pin47: ["VSS3"],
  pin48: ["VDD3"],
  pin49: ["PA14"],
  pin50: ["PA15"],
  pin51: ["PC10"],
  pin52: ["PC11"],
  pin53: ["PC12"],
  pin54: ["PD2"],
  pin55: ["PB3"],
  pin56: ["PB4"],
  pin57: ["PB5"],
  pin58: ["PB6"],
  pin59: ["PB7"],
  pin60: ["BOOT0"],
  pin61: ["PB8"],
  pin62: ["PB9"],
  pin63: ["VSS4"],
  pin64: ["VDD4"]
} as const

export const STM32F411RET6 = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C94355"
  ]
}}
      manufacturerPartNumber="STM32F411RET6"
      footprint={<footprint>
        <smtpad portHints={["pin1"]} pcbX="-3.750056mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin2"]} pcbX="-3.24993mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin3"]} pcbX="-2.750058mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin4"]} pcbX="-2.249932mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin5"]} pcbX="-1.75006mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin6"]} pcbX="-1.249934mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin7"]} pcbX="-0.750062mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin8"]} pcbX="-0.249936mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin9"]} pcbX="0.249936mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin10"]} pcbX="0.750062mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin11"]} pcbX="1.249934mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin12"]} pcbX="1.75006mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin13"]} pcbX="2.249932mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin14"]} pcbX="2.750058mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin15"]} pcbX="3.24993mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin16"]} pcbX="3.750056mm" pcbY="-5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin17"]} pcbX="5.700014mm" pcbY="-3.738245mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin18"]} pcbX="5.700014mm" pcbY="-3.238119mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin19"]} pcbX="5.700014mm" pcbY="-2.738247mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin20"]} pcbX="5.700014mm" pcbY="-2.238121mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin21"]} pcbX="5.700014mm" pcbY="-1.738249mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin22"]} pcbX="5.700014mm" pcbY="-1.238123mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin23"]} pcbX="5.700014mm" pcbY="-0.738251mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin24"]} pcbX="5.700014mm" pcbY="-0.238125mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin25"]} pcbX="5.700014mm" pcbY="0.261747mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin26"]} pcbX="5.700014mm" pcbY="0.761873mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin27"]} pcbX="5.700014mm" pcbY="1.261745mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin28"]} pcbX="5.700014mm" pcbY="1.761871mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin29"]} pcbX="5.700014mm" pcbY="2.261743mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin30"]} pcbX="5.700014mm" pcbY="2.761869mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin31"]} pcbX="5.700014mm" pcbY="3.261741mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin32"]} pcbX="5.700014mm" pcbY="3.761867mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin33"]} pcbX="3.750056mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin34"]} pcbX="3.24993mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin35"]} pcbX="2.750058mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin36"]} pcbX="2.249932mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin37"]} pcbX="1.75006mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin38"]} pcbX="1.249934mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin39"]} pcbX="0.750062mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin40"]} pcbX="0.249936mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin41"]} pcbX="-0.249936mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin42"]} pcbX="-0.750062mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin43"]} pcbX="-1.249934mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin44"]} pcbX="-1.75006mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin45"]} pcbX="-2.249932mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin46"]} pcbX="-2.750058mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin47"]} pcbX="-3.24993mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin48"]} pcbX="-3.750056mm" pcbY="5.688203mm" width="0.2999994mm" height="1.499997mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin49"]} pcbX="-5.700014mm" pcbY="3.761867mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin50"]} pcbX="-5.700014mm" pcbY="3.261741mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin51"]} pcbX="-5.700014mm" pcbY="2.761869mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin52"]} pcbX="-5.700014mm" pcbY="2.261743mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin53"]} pcbX="-5.700014mm" pcbY="1.761871mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin54"]} pcbX="-5.700014mm" pcbY="1.261745mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin55"]} pcbX="-5.700014mm" pcbY="0.761873mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin56"]} pcbX="-5.700014mm" pcbY="0.261747mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin57"]} pcbX="-5.700014mm" pcbY="-0.238125mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin58"]} pcbX="-5.700014mm" pcbY="-0.738251mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin59"]} pcbX="-5.700014mm" pcbY="-1.238123mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin60"]} pcbX="-5.700014mm" pcbY="-1.738249mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin61"]} pcbX="-5.700014mm" pcbY="-2.238121mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin62"]} pcbX="-5.700014mm" pcbY="-2.738247mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin63"]} pcbX="-5.700014mm" pcbY="-3.238119mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<smtpad portHints={["pin64"]} pcbX="-5.700014mm" pcbY="-3.738245mm" width="1.499997mm" height="0.2999994mm" radius="0.1499997mm" shape="pill" />
<silkscreenpath route={[{"x":-4.999989999999997,"y":-4.119397400000011},{"x":-4.999964599999998,"y":-4.119397400000011},{"x":-4.131183000000021,"y":-4.9881790000000095}]} />
<silkscreenpath route={[{"x":4.999989999999968,"y":5.011800999999991},{"x":4.131208399999991,"y":5.011800999999991}]} />
<silkscreenpath route={[{"x":4.999989999999968,"y":5.011800999999991},{"x":4.999989999999968,"y":4.142993999999987}]} />
<silkscreenpath route={[{"x":-4.999989999999997,"y":4.142993999999987},{"x":-4.999989999999997,"y":5.011800999999991},{"x":-4.131183000000021,"y":5.011800999999991}]} />
<silkscreenpath route={[{"x":-4.131183000000021,"y":-4.9881790000000095},{"x":-4.999989999999997,"y":-4.9881790000000095},{"x":-4.999989999999997,"y":-4.119397400000011}]} />
<silkscreenpath route={[{"x":4.999989999999968,"y":-4.119397400000011},{"x":4.999989999999968,"y":-4.9881790000000095},{"x":4.131182999999993,"y":-4.9881790000000095}]} />
<silkscreenpath route={[{"x":-4.2500042000000064,"y":4.261815199999987},{"x":-4.2500042000000064,"y":-4.238193200000012},{"x":4.2500042000000064,"y":-4.238193200000012},{"x":4.2500042000000064,"y":4.261815199999987},{"x":-4.2500042000000064,"y":4.261815199999987}]} />
<silkscreenpath route={[{"x":-3.2994600000000105,"y":-3.013329000000013},{"x":-3.510394378607913,"y":-2.9241206405700666},{"x":-3.5969167117677614,"y":-2.712070341500585},{"x":-3.508602117039061,"y":-2.500760200170852},{"x":-3.2969200000000285,"y":-2.413340952880887},{"x":-3.0852378829609677,"y":-2.500760200170852},{"x":-2.996923288232267,"y":-2.712070341500585},{"x":-3.0834456213921158,"y":-2.9241206405700666},{"x":-3.294380000000018,"y":-3.013329000000013}]} />
<silkscreenpath route={[{"x":-4.361256200000014,"y":-5.47817040000001},{"x":-4.509997255997689,"y":-5.327528370296079},{"x":-4.359986200000009,"y":-5.178150975985275},{"x":-4.209975144002357,"y":-5.327528370296079},{"x":-4.3587162000000035,"y":-5.47817040000001}]} />
<silkscreentext text="{NAME}" pcbX="0mm" pcbY="7.285611mm" anchorAlignment="center" fontSize="1mm" />
<courtyardoutline outline={[{"x":-6.549200000000013,"y":6.535610999999989},{"x":6.549199999999985,"y":6.535610999999989},{"x":6.549199999999985,"y":-6.715189000000009},{"x":-6.549200000000013,"y":-6.715189000000009},{"x":-6.549200000000013,"y":6.535610999999989}]} />
      </footprint>}
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C94355.obj?uuid=7e9b9111dcfd48d3add0eab11d882721",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C94355.step?uuid=7e9b9111dcfd48d3add0eab11d882721",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: 0, y: -0.011810999999994465, z: 0.000795 },
      }}
      {...props}
    />
  )
}