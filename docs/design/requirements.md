# MC3_COL_MAIN_V1.0 — requirements

## Goal

Driver board for a 6mm coreless geared DC motor (3V nominal) with current sensing,
controlled by an external MCU. Compact enough to live next to the motor.

## Fixed requirements

- **H-bridge:** TI DRV8210 driving the motor
- **Current sense:** INA240 with an external shunt, low-side of the motor current path
- **Motor/encoder connection:** JST connector(s)
- **Control:** pin header to an external MCU board
- **Sourcing:** all parts orderable/assemblable via JLCPCB (SMD assembly — avoid
  hand-soldering constraints)
- **Board:** 2 layers, ≤ 25 × 25 mm

## Layout constraints (non-negotiable, enforced via review-checklist.md)

- Shunt sense traces: short, matched, Kelvin-connected from the shunt pads to the
  INA240 inputs. The sense pair must not share copper with the motor current path.
- DRV8210 bypass capacitor: directly against the supply pins, no vias between cap
  and pins.

## Open questions — resolve before schematic capture

1. **Power architecture:** single 3.3V rail from the MCU header vs. separate VMOT
   input (e.g., 1S LiPo) vs. 5V in + onboard regulator. Determines regulator need and
   INA240 supply (INA240 needs ≥ 2.7V).
2. **Motor stall current:** needed to size the shunt and pick the INA240 gain variant
   (A1 = 20 V/V, A2 = 50, A3 = 100, A4 = 200). Waiting on motor datasheet.
3. **Connector scheme:** "4-pin JST" — motor is 2 wires; a quadrature encoder typically
   needs 4 (V+, GND, A, B). One 6-pin, or two connectors, or a 2-wire encoder?
4. **JST series:** SH (1.0 mm), GH (1.25 mm), or PH (2.0 mm) — depends on mating
   cable/motor pigtail.
5. **MCU header pinout:** IN1/IN2 (PWM), current-sense analog out, encoder passthrough
   (or does the encoder go straight to the MCU?), 3V3, GND, nSLEEP?
6. **Encoder signal path:** does the encoder route through this board to the MCU
   header, or connect to the MCU directly?
