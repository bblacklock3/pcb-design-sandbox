import type { CrystalProps } from "@tscircuit/props"

type ImportedCrystalProps = Omit<CrystalProps, "frequency" | "pinVariant">

export const X32258MSB4SI = (props: ImportedCrystalProps) => {
  const { name = "X1", ...restProps } = props

  return (
    <crystal
      name={name}
      frequency="8MHz"
      pinVariant="four_pin"
      supplierPartNumbers={{
  "jlcpcb": [
    "C2682774"
  ]
}}
      manufacturerPartNumber="X32258MSB4SI"
      footprint="crystal"
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2682774.obj?uuid=02485e56ba8d4732a26526d2983fc729",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2682774.step?uuid=02485e56ba8d4732a26526d2983fc729",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: 0, y: -0.000012700000070253736, z: 0 },
      }}
      {...restProps}
    />
  )
}