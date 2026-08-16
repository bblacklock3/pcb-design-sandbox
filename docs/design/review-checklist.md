# Placement & routing review checklist

Gate 1 must fully pass (with `routingDisabled` still set) before routing is enabled.

## Gate 1 — netlist + placement (routing disabled)

- [ ] `tsci build` passes with no errors; all warnings understood
- [ ] Every part has a JLCPCB part number and matching footprint
- [ ] All decisions in `decisions.md` — no unlogged component values
- [ ] DRV8212 bypass cap adjacent to its supply pins, same side, no via between
- [ ] Shunt placed in the low-side motor current path; sense pads face the INA240
- [ ] INA240 within short reach of the shunt; sense pair length-matched by placement
- [ ] Motor current loop (VMOT → bridge → motor → shunt → GND) is physically compact
- [ ] Connectors on board edge; JST orientation matches cable exit direction
- [ ] Board outline ≤ 25 × 25 mm with mounting consideration

## Gate 2 — after routing

- [ ] Sense traces routed as a matched pair, Kelvin from shunt pads, no vias if possible,
      never sharing a segment with the motor current path
- [ ] Motor current traces sized for stall current (check width calc in decisions.md)
- [ ] Bypass cap connections did not get rerouted through vias
- [ ] Ground return for motor current does not flow under the INA240 inputs
- [ ] DRC clean; `tsci export` gerbers generate without errors
