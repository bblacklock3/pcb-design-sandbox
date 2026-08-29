# Placement & routing review checklist

Gate 1 must fully pass (no traces on the board) before routing starts.

## Gate 1 — netlist + placement (routing disabled)

- [ ] ERC clean (Konnect `run_erc`); all warnings understood
- [ ] Every part has a JLCPCB part number and matching footprint
- [ ] Every controlled value cites a vault PARAM; every part cites its COTS record — no invented values
- [ ] DRV8212 bypass cap adjacent to its supply pins, same side, no via between
- [ ] Shunt placed in the low-side motor current path; sense pads face the INA240
- [ ] INA240 within short reach of the shunt; sense pair length-matched by placement
- [ ] Motor current loop (VMOT → bridge → motor → shunt → GND) is physically compact
- [ ] Connectors on board edge; JST orientation matches cable exit direction
- [ ] Board outline ≤ 25 × 25 mm with mounting consideration

## Gate 2 — after routing

- [ ] Sense traces routed as a matched pair, Kelvin from shunt pads, no vias if possible,
      never sharing a segment with the motor current path
- [ ] Motor current traces sized for stall current (width calc lives in the vault PARAM)
- [ ] Bypass cap connections did not get rerouted through vias
- [ ] Ground return for motor current does not flow under the INA240 inputs
- [ ] DRC clean (Konnect `run_drc`); Gerbers export without errors (`pcb_export` toolset)
