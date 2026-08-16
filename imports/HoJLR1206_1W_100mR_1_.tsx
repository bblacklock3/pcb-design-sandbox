import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["pin1"],
  pin2: ["pin2"]
} as const

export const HoJLR1206_1W_100mR_1_ = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C2903496"
  ]
}}
      manufacturerPartNumber="HoJLR1206-1W-100mR-1%"
      footprint="res_p2.9576mm_pw1.2075mm_ph1.701mm"
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2903496.obj?uuid=f10f45bb694d451d9aaa692fc429b395",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2903496.step?uuid=f10f45bb694d451d9aaa692fc429b395",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: 0, y: 0, z: -0.6 },
      }}
      {...props}
    />
  )
}