import { KH_FG0_5_H2_0_16PIN } from "../../imports/KH_FG0_5_H2_0_16PIN"

// Mezzanine connector — the sensor front-end site.
//
// System: Projects/MC3 Collimator/03 Systems/Control Electronics/
//
// WHY THIS EXISTS. The sensor front-end is deliberately NOT on this board. Six sensing
// branches are live under the Sensing system and nothing is chosen, and the choice swings
// the conductor count by more than 3x: COL-COTS-0003 (LX34070, raw sin/cos) needs 10
// conductors minimum per bar board and 12-14 with interleaved grounds, while COL-COTS-0016
// (LX34311, integrated) needs 4.
//
// Resolved 2026-08-16 (COL-SEARCH-0009): a fixed 16-pin, 0.5mm-pitch hinged-lid FPC
// connector (COL-COTS-0027, JLC C2797209) is placed now so the board is buildable — it
// covers the worst-case 12-14 conductor branch with 2-4 spare, matching the vault's prior
// art on Inductive-Encoder-01 (0.5mm FPC chosen there as sourceable/hand-solderable/
// reworkable, 0.3mm back-flip rejected). Only power/ground are wired below; the signal
// pins are deliberately left unconnected — populating them means picking the sensing
// branch, which has not happened. Do that in Sensing.md / a SEL record, not here.
export const Mezzanine = () => (
  <group name="mezzanine">
    <KH_FG0_5_H2_0_16PIN
      name="J_MEZZ"
      schX={-40}
      schY={-14}
      pcbX={-46}
      pcbY={-18}
    />
    <trace from="J_MEZZ.pin1" to="net.V3_3" />
    <trace from="J_MEZZ.pin2" to="net.GND" />
    <trace from="J_MEZZ.pin15" to="net.GND" />
    <trace from="J_MEZZ.pin16" to="net.GND" />
    {/* pin3-pin14: reserved for whatever the sensing decision needs. #tbd */}
  </group>
)
