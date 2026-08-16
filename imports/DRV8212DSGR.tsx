import type { ChipProps } from "@tscircuit/props"

// MODE strapped high (to VCC) in this design -> PH/EN interface:
// pin5 = EN (was IN2/EN), pin6 = PH (was IN1/PH). MODE=low would select PWM
// IN1/IN2 instead; MODE floating selects independent half-bridge.
const pinLabels = {
  pin1: ["VM"],
  pin2: ["OUT1"],
  pin3: ["OUT2"],
  pin4: ["GND"],
  pin5: ["EN"],
  pin6: ["PH"],
  pin7: ["MODE"],
  pin8: ["VCC"],
  pin9: ["EP"]
} as const

const footprinterPinLabels = {
  ...pinLabels,
  "pin9": [...pinLabels["pin9"], "thermalpad"],
} as const

export const DRV8212DSGR = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={footprinterPinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C2843766"
  ]
}}
      manufacturerPartNumber="DRV8212DSGR"
      footprint="dfn8_thermalpad0.9mmx1.6mm_p0.5001mm_w2.4209mm_pw0.25mm_pl0.521mm"
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2843766.obj?uuid=2be2baea8d8242eebd2ce617314d92a1",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2843766.step?uuid=2be2baea8d8242eebd2ce617314d92a1",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: 0, y: 0, z: 0 },
      }}
      {...props}
    />
  )
}