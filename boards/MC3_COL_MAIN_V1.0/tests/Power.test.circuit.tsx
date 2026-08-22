import { Power } from "../Power"

// Standalone harness for the power block. Not routingDisabled: that flag also
// skips the decoupling max-trace-length check.
export default () => (
  <board width="40mm" height="40mm">
    <Power />
  </board>
)
