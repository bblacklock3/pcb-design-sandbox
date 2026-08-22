import React from "react";
import { AYF530435 as FFC_4P } from "../../imports/AYF530435";

// Board-edge connectors: motor leads, the machine-side interface, and the
// per-leaf encoder leads.
//
// The sensor MEZZANINE is a different thing and lives in Mezzanine.tsx.
//
// HEIGHT IS THE BINDING CONSTRAINT, not footprint area.
//
// COL-PARAM-0020 caps assembled height at 4mm HARD, measured mated. That rules
// out every wire-to-board family surveyed: JST-XH vertical ~11mm, JST-PH
// vertical ~6mm, JST-PH right-angle ~4.5-5mm. Right-angle does not rescue them
// -- laying the housing on its side makes the height roughly the body WIDTH,
// still over budget, and it grows the X/Y footprint because the cable exits
// sideways. It solves the wrong axis.
//
//   MOTOR LEADS  -> bare solder pads, 0mm. Nothing stands off the board at all.
//                   The leads never come apart in service, so a connector buys
//                   nothing here except height.
//   ENCODERS     -> 0.5mm-pitch FFC, 1mm tall. Flat by construction.
//
// This follows the vault's own precedent: Inductive-Encoder-01 already reasons
// that 0.5mm FFC is "sourceable, hand-solderable and reworkable" and rejects
// 0.3mm as none of those.
//
//   MACHINE SUPPLY -> bare solder pads too, sized for the whole board current.
// The control-link protocol is still unwritten (Control Electronics.md), so no
// signal pads are placed for it yet.
//
// LAYOUT: each connector is exported SEPARATELY and takes its own pos/rot.
// These are edge-mounted parts whose positions are mechanical decisions — which
// side the loom leaves from, which motor sits where — so there is no sensible
// internal arrangement to define, and grouping them only got in the way (as one
// group they came out in a fixed 9.12mm vertical stack, 47mm tall).
// See .claude/skills/tscircuit/LAYOUT.md.

// NO WRAPPER <group> ON THESE. A group containing a SINGLE positioned
// component discards that component pcbX/pcbY, and on the full board that
// cascaded into every other block losing its position too -- the MCU collapsed
// from x=-21 to x=-0.5 and everything landed in the cutout. EncoderConnector
// survived only because its group happens to hold two components (the
// connector and its pull-up). Fragments have no such failure mode.
// See .claude/skills/tscircuit/LAYOUT.md.

type Placement = {
  /** Where this connector sits on the board. */
  pos?: { x: number; y: number };
  rot?: number;
};

/**
 * One motor's two leads, as BARE SOLDER PADS — no connector.
 *
 * Zero height, which is the whole point (COL-PARAM-0020). Accepted cost: eight
 * wires soldered by hand in production, and no strain relief from a housing, so
 * the leads want anchoring mechanically near the board. #tbd how the loom is
 * retained.
 *
 * Pads are 2.2 x 1.4mm on a 2.6mm pitch: room to lay a 24-26 AWG conductor flat
 * with a fillet either side, and far more copper than 0.83A continuous needs.
 */
const PAD_W = 2.2;
const PAD_H = 1.4;
const PAD_PITCH = 2.6;

export const MotorPads = ({
  axis = "leaf1",
  pos = { x: 0, y: 0 },
  rot = 0,
}: Placement & { axis?: string }) => (
  <chip
    name={`J_${axis}`}
    pcbX={pos.x}
    pcbY={pos.y}
    pcbRotation={((rot % 360) + 360) % 360}
    pinLabels={{ pin1: ["MOTOR_A"], pin2: ["MOTOR_B"] }}
    footprint={
      <footprint>
        <smtpad
          portHints={["pin1"]}
          pcbX={`${-PAD_PITCH / 2}mm`}
          pcbY="0mm"
          width={`${PAD_W}mm`}
          height={`${PAD_H}mm`}
          shape="rect"
          layer="top"
        />
        <smtpad
          portHints={["pin2"]}
          pcbX={`${PAD_PITCH / 2}mm`}
          pcbY="0mm"
          width={`${PAD_W}mm`}
          height={`${PAD_H}mm`}
          shape="rect"
          layer="top"
        />
        <silkscreentext text="{NAME}" pcbY="1.6mm" fontSize="0.7mm" />
      </footprint>
    }
    connections={{
      pin1: `net.MOTOR_A_${axis}`,
      pin2: `net.MOTOR_B_${axis}`,
    }}
  />
);

// One leaf's inductive position sensor, on a remote bar board.
//
// CONDUCTOR COUNT comes straight from the Inductive-Encoder-01 build rung, not
// from a guess: the integrated part (COL-COTS-0016, LX34311) computes position
// on-chip and emits it as a SINGLE digital signal, so it is
// "1 signal + power = 3" per channel. A 4-pin connector carries that with one
// spare, and also covers the 4-conductor case if a connector ever serves a
// two-channel bar board.
//
// This is the INTEGRATED branch. The raw sin/cos alternative (COL-COTS-0003,
// LX34070) needs 10-14 conductors and could not use this connector at all —
// that is the branch the 16-pin FPC mezzanine (Mezzanine.tsx, COL-COTS-0027)
// was sized for. If these connectors are the sensor interface, the mezzanine is
// redundant; if the branch reopens, these are.
//
// VERIFIED against the datasheet (DS2006851A, Refs/Datasheets/LX34311.pdf),
// not assumed:
//
//   * SUPPLY IS 5V, NOT 3.3V. Recommended operating range is VIN 4.0 / 5.0 /
//     6.0 V (min/typ/max). 3.3V is below the minimum and below the undervoltage
//     lockout — the part would not run. This net therefore goes to VIN_RAW, the
//     5V rail from the machine connector, NOT to V3_3.
//     Note 3.3V would NOT work here, which is the easy mistake to make when
//     every other rail on this board is 3.3V.
//
//   * OUTPUTS ARE OPEN-DRAIN. IO1/IO2/IO3 are open-drain (VOL 0.1V max with a
//     10k pull-up), so the SIGNAL LEVEL IS SET BY THE PULL-UP RAIL, not by the
//     sensor's 5V supply. Pulling up to V3_3 on this board means the MCU sees
//     clean 3.3V logic even though the sensor runs at 5V — no level shifter and
//     no reliance on pin 5V-tolerance. IO1/IO2 absolute max is -0.5 to 7.5V, so
//     a 3.3V pull-up is well inside rating.
//     The pull-up therefore belongs HERE, on the MCU's rail — not on the remote
//     sensor board, where it would be referenced to the wrong supply.
//
//   * SIGNAL is PWM or SENT, both single-wire. Preferred over the 0-5V analog
//     DAC output, which gives up common-mode rejection over a flex
//     (COL-COTS-0016). At the 2 kHz update rate this needs timer input capture,
//     so all four land on timer capture channels in MCU.tsx — split TIM2/TIM1
//     rather than one timer, because these four connectors sit on the polar
//     ring at bearings that no single timer's pins can all face. See the
//     ENC_PINS note in MCU.tsx for why that split costs nothing.
const ENC_PULLUP = "10k"; // datasheet's own reference load for VOL

export const EncoderConnector = ({
  axis = "leaf1",
  pos = { x: 0, y: 0 },
  rot = 0,
}: Placement & { axis?: string }) => {
  const rotN = ((rot % 360) + 360) % 360;
  // The pull-up tucks RADIALLY INWARD of its connector, and turns with it.
  //
  // Radial rather than tangential, and rotated 90deg off the connector, because
  // both choices make the cluster SKINNIER in the angular direction — which is
  // the direction that costs arc, and therefore how many leaves fit in a
  // quadrant. A 0402 measures 1.86 x 0.94mm:
  //     tangential, alongside  ->  adds 1.86mm of arc + its gap
  //     radial, tucked behind  ->  adds 0.94mm, and none of it arc
  // Behind the connector the FFC's own 3.5mm still sets the slot width, so the
  // resistor costs nothing angularly at all.
  //
  // In the rotated frame +y maps to radially inward (the connectors are placed
  // with faceOutward, i.e. angle+90), so a positive y offset pulls it inboard.
  const rad = (rotN * Math.PI) / 180;
  /** Rotate a connector-local offset into board coordinates. */
  const place = (o: { x: number; y: number }) => ({
    x: pos.x + o.x * Math.cos(rad) - o.y * Math.sin(rad),
    y: pos.y + o.x * Math.sin(rad) + o.y * Math.cos(rad),
  });
  const pull = place({ x: 0, y: 4 });
  // The name label is flipped to local -y inside imports/AYF530435.tsx so it
  // lands outboard rather than on top of the pull-up — see the note there.
  return (
    <React.Fragment>
      <FFC_4P
        name={`J_ENC_${axis}`}
        pcbX={pos.x}
        pcbY={pos.y}
        pcbRotation={rotN}
      />
      <trace
        name={`T_ENC_${axis}_VCC`}
        from={`J_ENC_${axis}.VIN`}
        to="net.VIN_RAW"
      />
      <trace
        name={`T_ENC_${axis}_GND`}
        from={`J_ENC_${axis}.GND`}
        to="net.GND"
      />
      <trace
        name={`T_ENC_${axis}_SIG`}
        from={`J_ENC_${axis}.SIG1`}
        to={`net.ENC_${axis}`}
      />
      {/* Open-drain pull-up. Sets the logic level the MCU sees — see above. */}
      <resistor
        name={`R_ENC_${axis}`}
        resistance={ENC_PULLUP}
        footprint="0402"
        pullupFor={`net.ENC_${axis}`}
        pullupTo="net.V3_3"
        pcbX={pull.x}
        pcbY={pull.y}
        pcbRotation={(rotN + 90) % 360}
      />
      {/* Mechanical hold-down tabs. Soldered to GND for retention — they carry
          no signal, and grounding them is the usual treatment. */}
      <trace
        name={`T_ENC_${axis}_MP1`}
        from={`J_ENC_${axis}.MP1`}
        to="net.GND"
      />
      <trace
        name={`T_ENC_${axis}_MP2`}
        from={`J_ENC_${axis}.MP2`}
        to="net.GND"
      />
      {/* SIG2 spare — second channel if a bar board ever serves two leaves. */}
    </React.Fragment>
  );
};

/**
 * Machine-side supply, as BARE SOLDER PADS — no connector, same reasoning as
 * the motor leads (COL-PARAM-0020, 4mm assembled height).
 *
 * These pads carry the WHOLE BOARD, which is why they are bigger than the motor
 * ones: four leaves at the 0.83A max-power duty point is 3.32A continuous, and
 * an all-stall transient is 6.6A. That wants a 20-22 AWG conductor, not the
 * 24-26 AWG the motor pads are sized for.
 *
 * Two pads only. The provisional 2 spare signal pins are dropped: the
 * control-link protocol is still unwritten (Control Electronics.md), and
 * inventing pad positions for it now would just have to be undone.
 */
const PWR_PAD_W = 3.5;
const PWR_PAD_H = 2.0;
const PWR_PAD_PITCH = 4.2;

export const PowerPads = ({ pos = { x: 0, y: 0 }, rot = 0 }: Placement) => (
  <chip
    name="J_PWR"
    pcbX={pos.x}
    pcbY={pos.y}
    pcbRotation={((rot % 360) + 360) % 360}
    pinLabels={{ pin1: ["VIN"], pin2: ["GND"] }}
    footprint={
      <footprint>
        <smtpad
          portHints={["pin1"]}
          pcbX={`${-PWR_PAD_PITCH / 2}mm`}
          pcbY="0mm"
          width={`${PWR_PAD_W}mm`}
          height={`${PWR_PAD_H}mm`}
          shape="rect"
          layer="top"
        />
        <smtpad
          portHints={["pin2"]}
          pcbX={`${PWR_PAD_PITCH / 2}mm`}
          pcbY="0mm"
          width={`${PWR_PAD_W}mm`}
          height={`${PWR_PAD_H}mm`}
          shape="rect"
          layer="top"
        />
        <silkscreentext text="{NAME}" pcbY="-2.2mm" fontSize="0.8mm" />
      </footprint>
    }
    connections={{ pin1: "net.VIN_PROT", pin2: "net.GND" }}
  />
);
