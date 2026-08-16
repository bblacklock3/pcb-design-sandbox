import { HBridge } from "./HBridge"
import { CurrentSense } from "./CurrentSense"
import { Connectors } from "./Connectors"

// MC3_COL_MAIN_V1.0 — brushed DC motor driver
// Design context: docs/design/requirements.md, docs/design/parts/
// routingDisabled stays until Gate 1 of docs/design/review-checklist.md passes.
export const MC3_COL_MAIN_V1_0 = () => (
  <board name="MC3_COL_MAIN_V1.0" width="25mm" height="25mm" routingDisabled>
    <HBridge />
    <CurrentSense />
    <Connectors />
  </board>
)
