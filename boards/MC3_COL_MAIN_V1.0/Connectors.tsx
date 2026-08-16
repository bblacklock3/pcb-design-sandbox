import { AXES } from "./axes"
import { B2B_XH_A_LF__SN_ as JST_XH_2P } from "../../imports/B2B_XH_A_LF__SN_"
import { B4B_XH_A_LF__SN_ as JST_XH_4P } from "../../imports/B4B_XH_A_LF__SN_"

// Motor connectors (5x) and the machine-side power/control interface.
//
// The sensor connection is NOT here — it goes through Mezzanine.tsx.
//
// Resolved 2026-08-16 (COL-SEARCH-0009): JST-XH 2-pin, COL-COTS-0025 —
// 2.5mm pitch, 3A rated against this motor's 1.65A stall (COL-COTS-0002),
// ~82% margin. JST-PH was considered and rejected here for only ~21%
// margin at 2A — the same thin-margin lesson as the DRV8210->DRV8212 swap.
// Same connector used for all five channels; the yaw motor is unselected
// and may be a much larger load (COL-CALC-0008) — ASSUMPTION, flagged in
// the vault, not a verified fit for whatever yaw motor is eventually picked.
//
// Machine interface: JST-XH 4-pin, COL-COTS-0026, provisional pinout
// (VIN/GND/2 spare) — the actual supply and control-link spec is still
// unwritten (Control Electronics.md open item).
export const Connectors = () => (
  <group name="connectors">
    {AXES.map((axis, i) => (
      <group key={axis}>
        <JST_XH_2P
          name={`J_${axis}`}
          schX={-24 + i * 12}
          schY={-30}
          pcbX={-36 + i * 18}
          pcbY={-33}
        />
        <trace from={`J_${axis}.MOTOR_A`} to={`net.MOTOR_A_${axis}`} />
        <trace from={`J_${axis}.MOTOR_B`} to={`net.MOTOR_B_${axis}`} />
      </group>
    ))}

    <JST_XH_4P
      name="J_MACHINE"
      schX={40}
      schY={20}
      pcbX={44}
      pcbY={20}
    />
    <trace from="J_MACHINE.VIN" to="net.VIN_RAW" />
    <trace from="J_MACHINE.GND" to="net.GND" />
    {/* SIG1/SIG2 spare — no control-link protocol chosen yet. */}
  </group>
)
