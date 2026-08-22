# CAN link — layout constraints

Records: transceiver COTS record owed (TJA1051T/3, LCSC C38695) · Control-link decision owed to the
vault (Control Electronics § open items: "no control link to the machine specified") · Sheet:
`CAN.kicad_sch` · MCU: STM32F412RET6 CAN1 (PA11 RX / PA12 TX, AF9)

Constraints only. Why CAN and why this transceiver belong in the vault records above.

## Role on this board

The machine-side control link, prototype form: classic CAN at 500 kbit/s, one node on the bench
talking to a USB-CAN adapter (PEAK PCAN-USB or CANable 2.0), later the Monoblock bus.

## Parts on the sheet

| Ref | Part | Net side |
|---|---|---|
| U70 | TJA1051T/3 (SOIC-8), VCC = VCAN5 (VM through FB62 + 100 n + 4.7 µ), VIO = +3V3, S = GND | TXD ← CAN1_TX, RXD → CAN1_RX |
| JP70 + R70/R71 + C72 | solder jumper (bridged) → 62 Ω + 62 Ω split termination, 4.7 nF centre to GND | CANH … CANL |
| D70 | PESD1CAN (SOT-23) | CANH/CANL → GND |
| J70 | 3 bare pads: 1 CANH, 2 CANL, 3 GND (2.2×1.4 mm on 2.6 mm) | to the machine / adapter |

## Placement constraints

- **CANH/CANL are a differential pair** from U70 pins 6/7 to the pads: route them together,
  same length within a few mm, no layer changes if possible, over the GND plane.
- **D70 nearest the pads**, between pads and transceiver, so the surge sees the clamp before the
  part; its GND pin straight into the plane.
- **Termination (JP70, R70, R71, C72) right at the pads** — it terminates the line end, not the
  transceiver.
- U70 close behind them; C70 (100 nF) within 3 mm of U70 pin 3 with its return to the plane;
  FB62/C71 can sit a little further out.
- J70 pads on the rim next to the supply pads (J1) so the machine loom is one bundle:
  VIN, GND, CANH, CANL (+ CAN GND) — this is the provisional 4-pin machine interface of
  COL-COTS-0026 with its two spare signals now defined.
- Keep the pair away from the motor OUTx traces and the VM trunk.

## Routing constraints

- Pair width/spacing: netclass `CAN`, 0.25 mm, 0.2 mm gap is fine at this length; impedance
  control is not needed on a <30 mm stub but keep it symmetric.
- GND reference: continuous In1 plane under the pair; one GND via pair next to D70.

## Gotchas

- **JP70 bridged = terminated.** The board is a bus end on the bench. If it ever sits mid-bus in
  the machine, cut the jumper (or fit 0 Ω links instead of the bridge).
- S (pin 8) tied to GND = normal mode; leave it unconnected and the part is in silent mode.
- VCAN5 is the motor rail through a bead: if VM becomes a noisy or >5.5 V rail, the transceiver
  supply needs its own regulator (4.5–5.5 V).
- Adapter cable (DE-9, CiA 303-1): 7 = CANH, 2 = CANL, 3 = GND. Turn the adapter's 120 Ω on.
