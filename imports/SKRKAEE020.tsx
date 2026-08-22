import type { PushButtonProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["pin1"],
  pin2: ["pin2"]
} as const

export const SKRKAEE020 = (props: PushButtonProps<typeof pinLabels>) => {
  const { name = "SW1", ...restProps } = props

  return (
    <pushbutton
      name={name}
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C115357"
  ]
}}
      manufacturerPartNumber="SKRKAEE020"
      footprint="res_p4.3698mm_pw1.23mm_ph1.86mm"
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C115357.obj?uuid=2e35dca8e7854ed683469f8d54d1ef17",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C115357.step?uuid=2e35dca8e7854ed683469f8d54d1ef17",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: 0, y: -0.000012700000070253736, z: 0 },
      }}
      {...restProps}
    />
  )
}