import { DRV8212DSGR } from "../../imports/DRV8212DSGR";
import { INA240A1DR } from "../../imports/INA240A1DR";
import { HoJLR1206_1W_100mR_1_ as Shunt100mOhm } from "../../imports/HoJLR1206_1W_100mR_1_";

// One motor axis, complete: H-bridge + low-side shunt + sense amplifier.
// Instantiated five times — four leaves plus yaw.
//
// Implements: COL-COTS-0021 (DRV8212 H-bridge) — JLC C2843766 (DSGR, PH/EN), WSON-8 2x2mm
//             COL-COTS-0022 (INA240 sense amp)  — JLC C2060769 (A1, 20 V/V)
//             COL-COTS-0023 (100 mOhm 1206 shunt) — JLC C2903496
// Build rung: Projects/MC3 Collimator/05 Builds/Main-Board-01/
// Layout constraints: docs/design/parts/DRV8212.md, docs/design/parts/INA240.md
//                     (NEITHER WRITTEN YET — datasheets unread)
//
// BLOCKED, do not populate: the two layout-constraint notes above do not exist.
//
// NOT YET IDENTICAL ACROSS AXES. The yaw motor is unselected and its load is two orders
// of magnitude larger than a leaf's (COL-CALC-0008), so it may not share this topology.
// Treat the fifth instance as provisional until the yaw motor exists.
//
// WHY ONE FILE. Splitting the bridge from the sense front-end looks natural and
// is wrong on both counts:
//   * electrically, the driver's GND and thermal pad ARE the shunt's high side
//     (PGND_<axis>), so the split ran a component boundary through the middle
//     of one node;
//   * mechanically, <constraint> resolves a selector to a child's
//     pcb_component_id, which a <group> does not have -- so the shunt could
//     not be constrained relative to the driver at all. The two blocks packed
//     as rigid blobs and stacked to 6.9 x 13.4mm, which does not fit the
//     annulus at the diagonal axes, where a SQUARE cutout reaches further than
//     it does on the axes.
// Merged, all six parts are siblings and constraints work across the channel.
//
// DRV8212 MODE (pin7) strapped HIGH to VCC -> PH/EN interface: EN is the PWM/speed
// pin, PH is the direction pin. MODE=low would select PWM IN1/IN2 instead — a
// firmware-level tradeoff, not a hardware one, if that turns out to be preferred.
//
// Motor is 3V DC, 1.65A stall (COL-COTS-0002). The DRV8212's 1.65-5.5V range and 4A peak
// clear both with margin (41% of peak at stall). With this shunt and gain, stall maps to
// 3.30V (top of a 3.3V ADC) and the 0.83A max-power duty point to 1.66V, mid-scale.
//
// Shunt sits between PGND_<axis> and true board GND, so it reads total bridge current
// regardless of direction. IN_POS is on the PGND (driver) side, IN_NEG on the true-GND
// side — do not swap, or the sign is wrong for the assumed current-flow convention.
// BOTH REF pins -> GND, giving a ground-referenced UNIDIRECTIONAL output.
//
// This follows from where the shunt sits. It is in the bridge RETURN, between
// PGND_<axis> and true board GND, so the current through it is one-way whatever
// the motor is doing -- PH steers direction inside the H-bridge, downstream of
// this node, so it never reverses the return current. There is no negative
// current to represent, and no reason to spend range representing one.
//
// The midsupply method (SLOS954 8.4.3.2, REF1 -> VS, REF2 -> GND) is the wrong
// mode HERE for exactly that reason: it parks OUT at VS/2 = 1.65 V with no
// current flowing and rails at 0.825 A, half of stall, leaving the top half of
// the motor's torque range unreadable. It is the right mode for an inline shunt
// that genuinely sees both polarities -- which this is not.
//
// Do NOT use an external divider on REF. The datasheet is explicit: "use of the
// amplifier output as a single-ended signal in this configuration is not
// recommended because the internal impedance shifts can adversely affect device
// performance specifications." Both-REF-to-GND is a datasheet configuration and
// does not have that problem; an earlier 10k/10k VREF_MID divider did.
//
// Cost of the ground reference: output swing does not reach 0 V, so the lowest
// few mV -- order 10 mA referred to current -- read as zero. Irrelevant against
// a 1.65 A stall, and cheap next to losing half the span.
//
// This block does double duty. Beyond protection, COL-REQ-0013 wants a drive-side signal to
// cross-check the position sensor, and brush current-ripple counting would supply one from
// this shunt — now deprioritized to a "nice to have" (see COL-REQ-0002).

// --- Measured footprint geometry (from built Circuit JSON, not datasheets) ---
// Sizes come from pcb_courtyard_rect where one exists, because that is what the
// overlap check uses and it is both larger than the pad extents and offset from
// the component centre.
const DRV_CY_HALF_W = 1.5; // 3.00mm courtyard (pad extents are only 2.42mm)
const DRV_CY_HALF_H = 1.35; // 2.70mm courtyard
const C0402_CY_HALF_W = 0.93;
const C0402_CY_HALF_H = 0.47;
const CLEAR = 0.4;

// DRV8212 pads, chip-local. VM and VCC are on OPPOSITE sides.
const VM_PAD = { x: -0.95, y: 0.75 };
const VCC_PAD = { x: 0.95, y: 0.75 };
// Chip courtyard reaches +1.175mm above centre, the 0603's -0.905mm below its
// own, so 2.5mm of centre offset clears by ~0.42mm.
const VM_CAP_ABOVE = 2.5;

// INA240 (SOIC-8) and the 1206 shunt.
// INA_PAD_HALF_W is the measured PAD extent (+-2.88mm), not the 2.19mm body
// half-width. Sizing neighbours against the body under-clears them: the
// pads stick out 0.69mm further on each side than pcb_component.width implies.
const C0603_CY_HALF_W = 1.48;
const INA_PAD_HALF_W = 2.88;
const INA_HALF_H = 3.68;
const SHUNT_HALF_W_ROT = 0.85; // 1.70mm once turned 90deg
const VS_PAD = { x: 0.635, y: 2.705 };

// name/index default to leaf1 so previewing the bare component in `tsci dev`
// renders a real channel instead of "U_undefined_DRV" with NaN coordinates.
export const MotorChannel = ({
  name = "leaf1",
  index = 0,
  pos = { x: 0, y: 0 },
  rot = 0,
}: {
  name?: string;
  index?: number;
  /** Where this channel sits on the board. The block itself has no opinion. */
  pos?: { x: number; y: number };
  rot?: number;
}) => {
  const drv = `U_${name}_DRV`;
  const vmCap = `C_${name}_VM`;
  const vccCap = `C_${name}_VCC`;
  const shunt = `R_${name}_SHUNT`;
  const isense = `U_${name}_ISENSE`;
  const vsCap = `C_${name}_ISENSE_VS`;

  // ROTATION.  is NOT a supported prop on <group> -- it is not
  // declared in @tscircuit/props at all, and setting it there silently
  // mis-rotates the block: +-90 came back as component rotation 180 on every
  // part with footprint geometry left untransformed (pads stayed 1.95 x 0.57
  // instead of becoming 0.57 x 1.95). That is what made rotated channels show
  // unrotated pads.
  //
  // So rotation is applied per COMPONENT, which IS supported, and every offset
  // is rotated by the same angle so the arrangement turns as a rigid body.
  //
  // Positions are computed here and written straight to pcbX/pcbY rather than
  // expressed as <constraint>s. Constraints are only applied inside the pack
  // pass, and PackSolver2 re-orients constrained clusters to minimise area --
  // it silently flattened 90 and 270 back to 0 (180 survived only because it
  // has the same bounding box). A child WITH explicit pcbX/pcbY is marked
  // static and excluded from packing, so these coordinates are final.
  const rotN = ((rot % 360) + 360) % 360;
  const rad = (rotN * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  /** Rotate a block-local offset into the group frame. */
  const place = (x: number, y: number) => ({
    pcbX: x * cos - y * sin,
    pcbY: x * sin + y * cos,
  });

  // Block-local layout, all measured from the sense amp at the origin.
  const DRV_X =
    INA_PAD_HALF_W + CLEAR + C0603_CY_HALF_W + Math.abs(VM_PAD.x) - 0.5;
  const P_INA = { x: 0, y: 0 };
  const P_DRV = { x: DRV_X, y: 0 };
  const P_VMCAP = {
    x: P_DRV.x + VM_PAD.x + 1,
    y: P_DRV.y + VM_CAP_ABOVE + 0.3,
  };
  // VCC cap tucked BELOW the driver rather than out to its right, where it
  // stuck out past everything else. Sat under its own pad's x, so both
  // terminals stay equidistant and the placement is rotation-independent.
  // Cost of the move: the VCC decoupling loop goes from 1.37mm to ~3.0mm,
  // because the pad is on the driver's TOP edge (y=+0.75) and the cap is now
  // below the package. Still inside the 4mm budget, but it is a real trade of
  // electrical quality for tidiness -- revert if VCC ever looks noisy.
  const P_VCCCAP = {
    x: P_DRV.x + VCC_PAD.x - 1.5,
    y: P_DRV.y - (DRV_CY_HALF_H + C0402_CY_HALF_H + CLEAR),
  };
  const P_SHUNT = { x: -(INA_PAD_HALF_W + SHUNT_HALF_W_ROT + CLEAR), y: 0 };
  const P_VSCAP = { x: VS_PAD.x, y: INA_HALF_H + 0.47 + CLEAR };

  return (
    <group name={name} schAutoLayoutEnabled pcbX={pos.x} pcbY={pos.y}>
      <DRV8212DSGR name={drv} pcbRotation={rotN} {...place(P_DRV.x, P_DRV.y)} />
      {/* The INA's auto name label is suppressed and re-emitted below, because
          it was the one label that did not track the chip.
          Why: core picks the silkscreen rotation as
            props.pcbRotation !== 0 ? props.pcbRotation : <global transform>
          The soic8 footprinter emits this part's name text with a NON-ZERO
          pcbRotation (90deg, because the package is tall), which takes the
          first branch and pins the label to a literal angle instead of letting
          it follow the parent. Every other part here is wide, gets 0, and falls
          through to the tracking branch -- hence only this one misbehaved
          (it read 90/90/270/180 against rotations of 0/90/180/270).
          A standalone <silkscreentext> takes the rotation we give it. */}
      <INA240A1DR
        name={isense}
        pcbRotation={rotN}
        {...place(P_INA.x, P_INA.y)}
        pcbStyle={{ silkscreenTextVisibility: "hidden" }}
      />
      <silkscreentext
        text={isense}
        pcbRotation={rotN}
        fontSize="0.8mm"
        {...place(P_INA.x, P_INA.y - (INA_HALF_H + 1.0))}
      />

      {/* Driver BESIDE the amplifier, not above it -- this is the constraint
          the old two-group split made impossible, and the whole reason for
          merging. Left to pack freely the two clusters stack, giving a channel
          ~12.9mm on its long axis, against a diagonal band of 16.44mm of radial
          room at the diagonal axes, so a stacked channel has to be oriented
          perfectly to fit at all. Side by side the channel is ~8.7mm radially,
          which fits at every axis with real margin.
          The binding part is NOT the driver itself but its VM cap, which hangs
          0.95mm off the driver's left side and is 2.96mm wide. So the offset is
          INA pad edge 2.88 + gap 0.5 + VM cap half-width 1.48 + VM cap offset
          0.95 = 5.81mm; 5.9 leaves a little slack. */}

      {/* ---- H-bridge ---- */}
      <trace name={`T_${name}_VM`} from={`${drv}.VM`} to="net.VM" />
      <trace name={`T_${name}_VCC`} from={`${drv}.VCC`} to="net.V3_3" />
      <trace name={`T_${name}_MODE`} from={`${drv}.MODE`} to="net.V3_3" />
      <trace
        name={`T_${name}_GND`}
        from={`${drv}.GND`}
        to={`net.PGND_${name}`}
      />
      <trace name={`T_${name}_EP`} from={`${drv}.EP`} to={`net.PGND_${name}`} />
      <trace
        name={`T_${name}_OUT1`}
        from={`${drv}.OUT1`}
        to={`net.MOTOR_A_${name}`}
      />
      <trace
        name={`T_${name}_OUT2`}
        from={`${drv}.OUT2`}
        to={`net.MOTOR_B_${name}`}
      />
      <trace name={`T_${name}_EN`} from={`${drv}.EN`} to={`net.EN_${name}`} />
      <trace name={`T_${name}_PH`} from={`${drv}.PH`} to={`net.PH_${name}`} />

      {/* VM bulk cap sits directly ABOVE its pad, not beside it. The decoupling
          length is measured from the cap's pin1, not its centre, and rotation
          is the solver's to choose -- a pcbRotation={180} attempt to swap the
          terminals was silently normalised away on this symmetric two-pad
          footprint. Centred over the pad, both terminals are equidistant
          (1.93mm), so the result cannot depend on the rotation chosen. */}
      <capacitor
        name={vmCap}
        capacitance="1uF"
        footprint="0603"
        pcbRotation={rotN}
        {...place(P_VMCAP.x, P_VMCAP.y)}
        decouplingFor={`${drv}.VM`}
        decouplingTo={`net.PGND_${name}`}
        maxDecouplingTraceLength="3mm"
      />

      {/* VCC cap on the VCC side. 4mm budget covers the pin2->PGND return
          (3.42mm, limited by the thermal pad sitting under the package); the
          leg that governs HF decoupling, pin1 to the VCC pad, is 1.37mm.
          Do NOT raise this to silence a violation on the pin1 side. */}
      <capacitor
        name={vccCap}
        capacitance="100nF"
        footprint="0402"
        pcbRotation={rotN}
        {...place(P_VCCCAP.x, P_VCCCAP.y)}
        decouplingFor={`${drv}.VCC`}
        decouplingTo={`net.PGND_${name}`}
        maxDecouplingTraceLength="4mm"
      />

      {/* ---- Shunt + sense amp ---- */}
      {/* KELVIN. The INA240's sense inputs are on OPPOSITE rows of the SOIC-8,
          IN_POS at (-1.905, +2.705) and IN_NEG at (-1.905, -2.705). Turning the
          shunt 90deg and centring it on the amplifier's y-axis makes the two
          sense runs mirror images about y=0 -- equal by construction, which is
          what a differential shunt amp needs. Left in its default orientation
          the runs are 5.14mm and 3.05mm: a ~2mm mismatch on a pair whose whole
          job is common-mode rejection. (pcbRotation IS honoured here, unlike
          the symmetric-cap case above.) */}
      <Shunt100mOhm
        name={shunt}
        pcbRotation={(rotN + 90) % 360}
        {...place(P_SHUNT.x, P_SHUNT.y)}
      />

      <trace
        name={`T_${name}_SHUNT_HI`}
        from={`${shunt}.pin1`}
        to={`net.PGND_${name}`}
      />
      <trace name={`T_${name}_SHUNT_LO`} from={`${shunt}.pin2`} to="net.GND" />

      {/* Sense inputs land ON THE SHUNT PADS, not on the nets those pads belong
          to. Routing IN_POS to "net.PGND" would let the autorouter satisfy it
          at ANY point on that net -- the driver's thermal pad, say -- so the
          sensed voltage would include the IR drop of the copper in between.
          IN_NEG to "net.GND" is worse, GND being the largest net on the board.
          Both would read high under load, silently. Same net membership either
          way; what changes is the physical endpoint. */}
      <trace
        name={`T_${name}_SENSE_P`}
        from={`${isense}.IN_POS`}
        to={`${shunt}.pin1`}
      />
      <trace
        name={`T_${name}_SENSE_N`}
        from={`${isense}.IN_NEG`}
        to={`${shunt}.pin2`}
      />

      <trace name={`T_${name}_ISENSE_VS`} from={`${isense}.VS`} to="net.V3_3" />
      <trace
        name={`T_${name}_ISENSE_GND`}
        from={`${isense}.GND`}
        to="net.GND"
      />
      {/* BOTH REF pins to GND -> ground-referenced, UNIDIRECTIONAL output.
          This is what makes the gain sizing work: 0 A -> 0 V, stall 1.65 A ->
          3.30 V, i.e. the full ADC span. Tying REF1 to VS instead selects the
          datasheet's midsupply mode, which parks the output at 1.65 V with no
          current flowing and rails at 0.825 A -- half of stall, with the top
          half of the motor's torque range unreadable. */}
      <trace name={`T_${name}_REF1`} from={`${isense}.REF1`} to="net.GND" />
      <trace name={`T_${name}_REF2`} from={`${isense}.REF2`} to="net.GND" />
      <trace
        name={`T_${name}_ISENSE_OUT`}
        from={`${isense}.OUT`}
        to={`net.ISENSE_${name}`}
      />

      {/* VS cap centred over the VS pad so both terminals are equidistant
          (1.91mm). 7mm budget covers the pin2->GND return, which measures
          6.10mm here: VS is on the top row of the SOIC-8 and GND on the
          bottom, so no position is close to both. Proximity to the supply pin
          wins; that return is a via to plane, not a 6mm trace.
          Do NOT raise this to silence a violation on the VS leg. */}
      <capacitor
        name={vsCap}
        capacitance="100nF"
        footprint="0402"
        pcbRotation={rotN}
        {...place(P_VSCAP.x, P_VSCAP.y)}
        decouplingFor={`${isense}.VS`}
        decouplingTo="net.GND"
        maxDecouplingTraceLength="7mm"
      />
    </group>
  );
};
