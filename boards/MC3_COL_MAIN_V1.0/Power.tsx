import { AMS1117_3_3 } from "../../imports/AMS1117_3_3";
// AO4407C declared inline rather than via imports/AO4407C.tsx: that import maps
// its pins to labels (S1-S3, G, D1-D4) and referencing them fails inside core
// with "issue finding the port pin8". Plain numeric pins on a soic8 footprint
// avoid the problem entirely. SOIC-8 MOSFET convention: 1-3 source, 4 gate,
// 5-8 drain.
const AO4407C = ({ name }: { name: string }) => (
  <chip
    name={name}
    footprint="soic8"
    manufacturerPartNumber="AO4407C"
    supplierPartNumbers={{ jlcpcb: ["C469397"] }}
    pinLabels={{
      pin1: ["S1"],
      pin2: ["S2"],
      pin3: ["S3"],
      pin4: ["G"],
      pin5: ["D4"],
      pin6: ["D3"],
      pin7: ["D2"],
      pin8: ["D1"],
    }}
    connections={{
      pin1: "net.VIN_RAW",
      pin2: "net.VIN_RAW",
      pin3: "net.VIN_RAW",
      pin5: "net.VIN_PROT",
      pin6: "net.VIN_PROT",
      pin7: "net.VIN_PROT",
      pin8: "net.VIN_PROT",
    }}
  />
);

// Power input and rails — PROTOTYPE architecture, not a final decision.
//
// The board's true incoming supply is still unspecified at the machine end
// (Control Electronics.md open item) and the MC2's 24VDC rail is explicitly
// NOT a default here (that rail was sized for the MC2's BLDC motors, a
// different class than this board's brushed leaf motors — COL-COTS-0021).
//
// For this first prototype: 5V in via the machine-interface connector
// (Connectors.tsx), used directly as VM for all five DRV8212 bridges
// (COL-COTS-0021, 1.65-5.5V range) and regulated down to 3.3V logic for the
// MCU and analog. The motor's own 3V rating is reached by PWM duty control
// in firmware, not by a separate regulated motor rail — this is the normal
// mode of operation for a PWM H-bridge driver, not a simplification that
// costs anything. Revisit this file once the machine-side supply is real.
//
// LAYOUT: relative only. This block defines where its parts sit with respect
// to each other and nothing else — it carries no board position, no polar
// maths and no schX/schY. Where the block lands on the board is decided by
// whoever instantiates it. See .claude/skills/tscircuit/LAYOUT.md.

// --- Measured footprint geometry (from the built Circuit JSON) ---
// AMS1117 is SOT-223: three pads on the right at x=+2.93 (VIN/VOUT1/GND) and
// the tab on the left at x=-3.01.
//
// It emits NO pcb_courtyard_rect, but the overlap check still gives it one --
// synthesised from its bounds (8.36 x 5.70) plus ~0.5mm of margin per side.
// Sizing neighbours against the raw bounds put every one of them exactly
// 0.1mm inside that synthesised courtyard, so these are bounds + 0.5.
const REG_CY_HALF_W = 4.18 + 0.5;
const REG_CY_HALF_H = 2.85 + 0.5;
const VIN_PAD = { x: 2.93, y: 2.3 };
const VOUT1_PAD = { x: 2.93, y: 0 };
const C0402_CY_HALF_W = 0.93;
const C0402_CY_HALF_H = 0.47;
const C0805_CY_HALF_W = 1.68;
const C0805_CY_HALF_H = 0.95;
const CLEAR = 0.4;

// VREF divider row sits below the regulator. 0402 courtyards are 1.86mm wide,
// so 2.5mm of pitch clears with 0.64mm to spare.
const VREF_ROW_Y = -(REG_CY_HALF_H + C0402_CY_HALF_H + CLEAR + 0.9);
const VREF_PITCH = 2.5;

export const Power = ({
  pos = { x: 0, y: 0 },
  rot = 0,
}: {
  /** Where this block sits on the board. The block itself has no opinion. */
  pos?: { x: number; y: number };
  rot?: number;
} = {}) => (
  <group
    name="power"
    schAutoLayoutEnabled
    pcbPack
    pcbPackGap="0.4mm"
    pcbX={pos.x}
    pcbY={pos.y}
    pcbRotation={rot}
  >
    {/* VIN_PROT is the raw input from the pads; VIN_RAW is downstream of the
        reverse-polarity FET and is what the rest of the board runs on. */}
    <net name="VIN_PROT" />
    <net name="VIN_RAW" />
    <net name="VM" />
    <net name="V3_3" />
    <net name="GND" />

    {/* REVERSE-POLARITY PROTECTION — high-side P-channel MOSFET.
        A series diode was not an option: at 3.32A continuous a Schottky drops
        ~0.4V and burns 1.3W, and the 5V rail cannot spare the headroom either.
        This FET is 11.5mohm, so ~0.13W and ~40mV of drop.

        Orientation matters and is easy to get backwards. DRAIN faces the input,
        SOURCE faces the board:
          - correct polarity: the body diode (drain->source) conducts first, the
            source rises to ~VIN, Vgs = 0 - VIN = -5V, the FET turns fully ON and
            shunts its own body diode.
          - reversed: source sits below gate, Vgs positive, FET stays OFF, and
            the body diode is reverse-biased. Nothing downstream sees voltage.
        Gate is pulled to GND through R_POL. Vgs never exceeds the 5V rail so no
        gate zener is needed; add one if the input rail ever rises above ~12V. */}
    <AO4407C name="Q_POL" />
    <resistor
      name="R_POL"
      resistance="100k"
      footprint="0402"
      pulldownFor="Q_POL.G"
      pulldownTo="net.GND"
    />
    <constraint pcb centerToCenter xDist={0} left=".Q_POL" right=".R_POL" />
    <constraint pcb centerToCenter yDist={-4.2} top=".Q_POL" bottom=".R_POL" />

    {/* VM = VIN directly, downstream of protection. DRV8212 firmware
        duty-cycles down to the motor's 3V rating; see comment above. */}
    <trace name="T_VIN_VM" from="net.VIN_RAW" to="net.VM" />

    <AMS1117_3_3 name="U_REG" />
    
    {/* FET sits ABOVE the regulator, not inboard of it. Inboard pushes it
        toward the board centre, and on a board with a 22mm square hole through
        the middle that walks it straight into the cutout. */}
    <constraint pcb centerToCenter xDist={0} left=".U_REG" right=".Q_POL" />
    <constraint pcb centerToCenter yDist={-10.3} top=".U_REG" bottom=".Q_POL" />
    <trace name="T_REG_VIN" from="net.VIN_RAW" to="U_REG.VIN" />
    <trace name="T_REG_GND" from="net.GND" to="U_REG.GND" />
    <trace name="T_REG_VOUT1" from="net.V3_3" to="U_REG.VOUT1" />
    <trace name="T_REG_VOUT2" from="net.V3_3" to="U_REG.VOUT2" />

    {/* Input cap centred directly OVER the VIN pad, one row above the package.
        Centring on the pad rather than sitting beside it makes both terminals
        equidistant (~1.51mm), so the enforced decoupling length does not
        depend on which way round the solver rotates a symmetric two-pad
        part — the same trap that bit the H-bridge's VM cap. */}
    <capacitor
      name="C_REG_IN"
      capacitance="1uF"
      footprint="0402"
      decouplingFor="U_REG.VIN"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="7mm"
    />
    <constraint
      pcb
      centerToCenter
      xDist={VIN_PAD.x}
      left=".U_REG"
      right=".C_REG_IN"
    />
    <constraint
      pcb
      centerToCenter
      yDist={-(REG_CY_HALF_H + C0402_CY_HALF_H + CLEAR)}
      top=".U_REG"
      bottom=".C_REG_IN"
    />

    {/* 22uF. This is a COMPENSATION component, not just bypass — the AMS1117
        datasheet: "The circuit design used in the AMS1117 series REQUIRES the
        use of an output capacitor as part of the device frequency
        compensation. The addition of 22uF solid tantalum on the output will
        ensure stability for all operating conditions." Undersizing it can make
        the regulator oscillate.
        OPEN: the datasheet specifies TANTALUM and gives NO ESR window at all.
        A ceramic is fitted, and near-zero ESR is the classic instability mode
        for 1117-family parts. The value follows the datasheet; the dielectric
        question is unresolved. #tbd confirm on hardware, or fit a tantalum.
        Output cap to the right of the package, level with VOUT1. An 0805 is
        too wide to sit over the pad without clashing with C_REG_IN, so this
        one is beside it. The VOUT1 leg is ~2.3mm; the 6mm budget covers the
        pin2->GND return at 5.27mm, GND being on the far side of the package. */}
    <capacitor
      name="C_REG_OUT"
      capacitance="22uF"
      footprint="0805"
      decouplingFor="U_REG.VOUT1"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="6mm"
    />
    <constraint
      pcb
      centerToCenter
      xDist={REG_CY_HALF_W + C0805_CY_HALF_W + CLEAR}
      left=".U_REG"
      right=".C_REG_OUT"
    />
    <constraint
      pcb
      centerToCenter
      yDist={-VOUT1_PAD.y}
      top=".U_REG"
      bottom=".C_REG_OUT"
    />

    {/* Bulk input reservoir. No decouplingFor — it is a reservoir, not a
        bypass, so it has no enforced proximity requirement and sits on the
        tab side where there is room. */}
    <capacitor name="C_BULK_IN" capacitance="10uF" footprint="0805" />
    <constraint
      pcb
      centerToCenter
      xDist={-VIN_PAD.x}
      left=".U_REG"
      right=".C_BULK_IN"
    />
    <constraint
      pcb
      centerToCenter
      yDist={-(REG_CY_HALF_H + C0805_CY_HALF_H + CLEAR)}
      top=".U_REG"
      bottom=".C_BULK_IN"
    />
    <trace name="T_BULK_POS" from="net.VIN_RAW" to="C_BULK_IN.pos" />
    <trace name="T_BULK_NEG" from="net.GND" to="C_BULK_IN.neg" />

    {/* NO VREF DIVIDER HERE, deliberately. Generating VCC/2 from a shared
        10k/10k divider for the sense amps is the obvious approach, and the
        INA240 datasheet (SLOS954) advises against it when the amp output is
        read single-ended, as ours is:

          "The REF pins can be connected together and biased using a resistor
           divider ... use the output as a differential signal with respect to
           the resistor divider voltage. Use of the amplifier output as a
           single-ended signal in this configuration is not recommended because
           the internal impedance shifts can adversely affect device
           performance specifications."

        The REF pins feed an internal gain network, so an external divider
        source impedance (5k) sits inside that network and shifts gain/offset.
        Each channel uses the datasheet own midsupply method instead --
        REF1 to VS, REF2 to GND (MotorChannel.tsx, section 8.4.3.2) -- which
        needs no external parts, is ratiometric to the supply so it tracks the
        ADC reference, and leaves no shared net for the channels to contend
        over. */}
  </group>
);
