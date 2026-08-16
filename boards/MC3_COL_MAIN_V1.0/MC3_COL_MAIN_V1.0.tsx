import { MotorChannel } from "./MotorChannel"
import { Power } from "./Power"
import { MCU } from "./MCU"
import { Mezzanine } from "./Mezzanine"
import { Connectors } from "./Connectors"
import { AXES } from "./axes"

// MC3_COL_MAIN_V1.0 — MC3 collimator main control board.
//
// Vault build rung:  Projects/MC3 Collimator/05 Builds/Main-Board-01/
// Vault system:      Projects/MC3 Collimator/03 Systems/Control Electronics/
// The split of what lives where: _System/Process/board-design.md
//
// Five brushed DC axes — four leaves plus yaw. The MC2 drove two BLDC motors through
// three-phase drivers; MC3 motors are brushed (COL-COTS-0002), so commutation leaves the
// board and each channel becomes a single H-bridge. Axis count goes 2 -> 5.
//
// The sensor front-end is on a mezzanine card, not here — see Mezzanine.tsx.
//
// STATUS: first prototype pass, 2026-08-16. Driver/current-sense (COL-COTS-0021/0022/0023),
// MCU (STM32F411RET6) and connectors (motor/machine/mezzanine) are now placed and wired —
// see COL-SEARCH-0007 (driver/sense) and COL-SEARCH-0008 (MCU). Still genuinely open:
// the mezzanine's own signal pinout (sensing branch unchosen), the yaw channel's connector/
// driver fit (yaw motor unselected, load may be 2 orders of magnitude larger), and the
// machine-interface connector's real pin count (control-link protocol unwritten).

export const MC3_COL_MAIN_V1_0 = () => (
  // Size is PROVISIONAL and deliberately generous for a first prototype — NOT sized to the
  // collimator's mechanical envelope, which is itself unreconciled (60mm in
  // Leaf-Absolute-Inductive against 65mm in COL-CALC-0009). Shrink once placement is real.
  // routingDisabled stays until Gate 1 of docs/design/review-checklist.md passes.
  <board name="MC3_COL_MAIN_V1.0" width="100mm" height="70mm" routingDisabled>
    <Power />
    <MCU />
    {AXES.map((axis, index) => (
      <MotorChannel key={axis} name={axis} index={index} />
    ))}
    <Mezzanine />
    <Connectors />
  </board>
)
