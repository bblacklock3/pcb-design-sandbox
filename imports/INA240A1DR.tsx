import type { ChipProps } from "@tscircuit/props";

const pinLabels = {
  pin1: ["IN_NEG"],
  pin2: ["GND"],
  pin3: ["REF2"],
  pin4: ["NC"],
  pin5: ["OUT"],
  pin6: ["VS"],
  pin7: ["REF1"],
  pin8: ["IN_POS"],
} as const;

export const INA240A1DR = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
        jlcpcb: ["C2060769"],
      }}
      manufacturerPartNumber="INA240A1DR"
      footprint="soic8_pillpads_w7.3604mm_pw0.5684mm_pl1.9502mm_pin1location(leftside,bottom)"
      cadModel={{
        objUrl:
          "https://modelcdn.tscircuit.com/easyeda_models/assets/C2060769.obj?uuid=7abc64c95a1a4a04a4ef38f9097c870b",
        stepUrl:
          "https://modelcdn.tscircuit.com/easyeda_models/assets/C2060769.step?uuid=7abc64c95a1a4a04a4ef38f9097c870b",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: 0.0, y: 0, z: 0 },
      }}
      {...props}
    />
  );
};
