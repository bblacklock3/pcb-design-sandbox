import React from "react";
import { AXES } from "./axes";
import { STM32F411RET6 } from "../../imports/STM32F411RET6";
import { SKRKAEE020 } from "../../imports/SKRKAEE020";
import { X32258MSB4SI } from "../../imports/X32258MSB4SI";

// MCU, its support passives and the debug/programming interface.
//
// LAYOUT: relative only. This block arranges its own parts with respect to the
// chip and carries no board position — where it lands is decided by whoever
// instantiates it. Decoupling caps (VDD1-4, VDDA) sit at the chip's REAL
// per-pin coordinates (read from imports/STM32F411RET6.tsx's footprint, not
// guessed) plus a small outward nudge, because capacitor decouplingFor/
// decouplingTo enforces a real maxDecouplingTraceLength (default ~1mm).
//
// FIT NOTE, still open. The LQFP64 is 13.1 x 13.25mm and the packed cluster is
// ~21 x 25mm including SW_RESET (6 x 8mm) and J_SWD (9.1mm). The annulus
// between the 22mm cutout and the 64mm board edge is 21.0mm wide on-axis and
// 16.44mm on a diagonal. The cluster is ~17.7 x 24.3mm, so it fits on-axis in
// width but not in length -- dropping SW_RESET (NRST is already on the SWD
// header) or moving J_SWD out of the cluster is the cheapest fix. #tbd
//
// Resolved 2026-08-16 (COL-SEARCH-0008): STM32F411RET6, LQFP64, JLC C94355 —
// chosen for "ideal for initial development" over staying on the MC2's
// STM32F103 or moving to the motor-control-focused STM32G4 family: cheaper
// than an F103 with the same pin count despite being strictly more capable
// (faster core, 4x flash/RAM, USB OTG vs. F103's device-only, hardware
// quadrature-encoder-input timers — a free head start if the still-open
// sensor mezzanine lands on an incremental encoder). G4's extra op-amps and
// comparators would help ripple counting, but that's now a "nice to have"
// (COL-REQ-0002) and doesn't justify G4's 2.5x cost and thinner stock for a
// first prototype. Same Cortex-M/CubeIDE/HAL tooling family as MC2, so team
// familiarity carries over even though the F103 firmware itself does not —
// MC3's brushed H-bridge control shares little with MC2's three-phase BLDC
// commutation. Reopened 2026-08-16 (COL-COTS-0024, Firmware.md) pending a
// COL-SEARCH-0008 successor against package fit + the new logging requirement
// (COL-REQ-0014) -- this file keeps the part for now, not a final decision.
//
// Five motor channels, PH/EN interface (MotorChannel.tsx): EN is a PWM pin per
// axis, PH a plain GPIO. Five ISENSE analog inputs (MotorChannel.tsx) land on
// genuine ADC1-capable pins.
//
// ===========================================================================
// PIN ASSIGNMENT IS A LAYOUT DECISION, NOT JUST A FIRMWARE ONE.
// ===========================================================================
// These pins are chosen against WHICH EDGE OF THE PACKAGE faces the thing they
// drive. That is not cosmetic. An earlier revision assigned them in tidy
// numeric order (EN=PA0-3, PH=PB0-2/PB10, ISENSE=PC0-3, ENC=PB6-9) with no
// reference to the physical layout, and 12 of 16 leaf signals then left the
// package on an edge pointing away from their load. The router's only way out
// was to dive to an inner layer immediately and cross back under the die --
// which is how a via ended up sitting inside U_MCU.PA0's own SMD pad, and why
// signal traces were being cut through the inner1 ground plane.
//
// The board geometry that drives all of this: the MCU sits at (-21, 2), i.e.
// on the WEST side of the disc, and every one of the five channels is EAST of
// it. So:
//     E edge  best for everything; faces all four leaves
//     N edge  leaf1 / leaf2 (drivers at y = +25.2)
//     S edge  leaf3 / leaf4 (drivers at y = -25.2)
//     W edge  faces the board rim. Nothing useful. Deliberately left empty.
//
// AF mapping below is VERIFIED against the STM32F411xC/xE datasheet
// (Refs/Datasheets/STM32F411xC-xE.pdf), Table 9 alternate-function map and the
// pin-definition table -- not assumed. Two constraints did real work:
//
//   1. THERE ARE NO ADC PINS ON THE N EDGE. ADC1 is PA0-PA7, PB0, PB1 and
//      PC0-PC5; the N edge carries only PA8-PA13, PC6-PC9 and PB12-PB15. So
//      ISENSE_leaf1 CANNOT exit toward its amplifier at (-12, 20) no matter
//      how the pins are shuffled. It takes PB1, the northernmost ADC pin on
//      the E edge, and accepts a corner turn. This is a silicon limit.
//   2. TIM3 IS THE ONLY 4-CHANNEL TIMER THAT REACHES BOTH THE N AND E EDGES.
//      Its channels can each be taken from two different pins --
//      CH1 {PA6|PC6}, CH2 {PA7|PC7}, CH3 {PB0|PC8}, CH4 {PB1|PC9} -- and
//      mixing them per channel is legal. That is what lets all four EN PWMs
//      stay on ONE timer while still exiting on the correct side.
//
// Keeping the four EN pins on a single timer is worth protecting: this MCU has
// exactly one ADC, so the four ISENSE readings are one scan sequence, and that
// scan has to be triggered inside the PWM on-time to read motor current rather
// than a duty-modulated average. One timer means one TRGO drives it. Split
// across two timers it needs a master/slave chain to stay coherent.
//
// The mezzanine's own signal pins are NOT wired here — that connector's
// interior pinout is still undecided (Mezzanine.tsx) and deliberately not
// forced by this MCU choice, beyond leaving spare GPIO/ADC margin.

// EN = PWM speed input. ALL FOUR LEAVES ON TIM3 (see above), mixing the timer's
// N-edge and E-edge pin options so each one exits toward its own driver.
// leaf3's driver is due S and TIM3 has no S-edge mapping, so it takes the
// southernmost E-edge channel and turns the corner -- the one place where
// holding the single-timer property costs an edge.
const EN_PINS: Record<string, string> = {
  leaf1: "PC9", // TIM3_CH4 · N edge -> driver at (-12, 25.2) N
  leaf2: "PC8", // TIM3_CH3 · N edge -> driver at (  0, 25.2) N
  leaf3: "PA6", // TIM3_CH1 · E edge -> driver at (  0,-25.2) S (corner turn)
  leaf4: "PA7", // TIM3_CH2 · E edge -> driver at ( 12,-25.2) E
  yaw: "PA9", // TIM1_CH2 · N edge · yaw channel not yet routed
};
// PH = direction. Plain GPIO, so these are placed purely by geometry.
// NOTE leaf3 moved off PB2 deliberately: PB2 is BOOT1 on this part (verified in
// the pin-definition table), and a boot-mode strap is not somewhere to hang an
// H-bridge direction line.
const PH_PINS: Record<string, string> = {
  leaf1: "PC7", // N edge, alongside its own EN
  leaf2: "PC6", // N edge, east of leaf1 as the drivers are
  leaf3: "PC3", // S edge, east end -> driver at (0, -25.2)
  leaf4: "PA3", // E edge, southernmost pin -> driver at (12, -25.2)
  yaw: "PB12", // N edge, unchanged
};
// Inductive position sensor inputs, one per leaf (Connectors.tsx,
// COL-COTS-0016). The integrated LX34311 emits position as a single digital
// signal at up to 2 kHz, so each of these needs timer input capture, not a
// plain GPIO.
//
// These follow the ENCODER CONNECTORS, which sit on the polar ring and do NOT
// share bearings with the drivers: leaf1/leaf2 connectors are E and NE, while
// leaf3/leaf4 connectors are S. So unlike EN, one timer cannot serve all four
// without sending half of them the wrong way. They are split TIM2 + TIM1, which
// costs nothing: each channel decodes an independent PWM/SENT stream, so there
// is no cross-channel timing relationship to preserve. (The previous PB6-PB9 /
// TIM4 block did keep all four on one timer -- but PB6-PB9 are the W edge,
// pointing at the rim, away from all four connectors.)
//
// The sensor runs at 5V but its outputs are OPEN-DRAIN, pulled up to V3_3 on
// this board (Connectors.tsx), so these pins see 3.3V logic -- no level shifter
// and no dependence on 5V-tolerance. Yaw has no entry: no yaw channel yet.
const ENC_PINS: Record<string, string> = {
  leaf1: "PB10", // TIM2_CH3 · E edge, north end -> connector at ( 21.4,  18.8)
  leaf2: "PA8", // TIM1_CH1 · N edge, east end  -> connector at ( 10.6,  26.3)
  leaf3: "PA0", // TIM2_CH1 · S edge            -> connector at (-21.4, -18.8)
  leaf4: "PA1", // TIM2_CH2 · S edge            -> connector at (-10.6, -26.3)
};
// ISENSE = INA240 output, so these MUST be ADC1 pins. Ordered against each
// amplifier's position, subject to the no-ADC-on-the-N-edge limit noted above.
const ISENSE_PINS: Record<string, string> = {
  leaf1: "PB1", // ADC1_9  · E edge, northernmost ADC -> amp at (-12,  20) N
  leaf2: "PB0", // ADC1_8  · E edge, next north       -> amp at (  0,  20) E
  leaf3: "PA2", // ADC1_2  · S edge, east end         -> amp at (  0, -20) S
  leaf4: "PA4", // ADC1_4  · E edge, south            -> amp at ( 12, -20) E
  yaw: "PC4", // ADC1_14 · E edge · yaw channel not yet routed
};

// Pin pad coordinates below are read from imports/STM32F411RET6.tsx own
// smtpad definitions, local to the LQFP64 body centre. Decoupling caps are
// held at their own pin position because decouplingFor/decouplingTo enforces
// a real maxDecouplingTraceLength (default ~1mm).
const PIN_LOCAL = {
  VDD1: { x: 5.700014, y: -2.738247 }, // pin19, right edge
  VDD2: { x: 5.700014, y: 3.761867 }, // pin32, right edge
  VDD3: { x: -3.750056, y: 5.688203 }, // pin48, top edge
  VDD4: { x: -5.700014, y: -3.738245 }, // pin64, left edge
  VDDA: { x: 2.249932, y: -5.688203 }, // pin13, bottom edge
  VCAP_1: { x: 5.700014, y: 2.761869 }, // pin30, right edge
};

// Chip courtyard half-extent is ~6.45mm; a 0402 is 1.56 x 0.64. 7.6mm puts the
// cap body clear of the chip courtyard with margin, at ~1.9mm from the pad.
const CAP_OUT = 7.6;

// Explicit block-local layout. Positions are written straight to pcbX/pcbY
// rather than expressed as <constraint>s: constraints are only applied inside
// the pack pass, and letting the packer choose meant it decided where J_SWD
// and SW_RESET went (J_SWD ended up off to one side rather than stacked above
// the chip). A child WITH explicit pcbX/pcbY is static, so these are final.
//
// Right edge: VDD1/VDD2 + VCAP. Left: VDD4. Top: VDD3 then the SWD header.
// Bottom row 1: the crystal trio and VDDA. Bottom row 2: reset + straps.
const P = {
  U_MCU: { x: 0, y: 0 },
  C_MCU_VDD1: { x: CAP_OUT, y: PIN_LOCAL.VDD1.y },
  C_MCU_VDD2: { x: CAP_OUT, y: PIN_LOCAL.VDD2.y },
  C_MCU_VDD3: { x: PIN_LOCAL.VDD3.x, y: CAP_OUT },
  C_MCU_VDD4: { x: -CAP_OUT, y: PIN_LOCAL.VDD4.y },
  // 1mm further out than the others: at the shared radius the router had to
  // thread V3_3 between the chip edge and PC13. Still 2.96mm to its pad.
  // VDDA gets BOTH caps ST specifies. The 100nF does the HF work and must be
  // tight (1.81mm); the 1uF is a mid-frequency reservoir and tolerates 3.9mm,
  // so it is pushed sideways into space that already exists.
  C_MCU_VDDA_HF: { x: PIN_LOCAL.VDDA.x, y: -7.5 },
  C_MCU_VDDA: { x: 4.8, y: -8.6 },
  // VBAT is tied to V3_3 with no battery fitted and does not switch, so its
  // cap has no meaningful di/dt to serve -- it is there because ST's power
  // scheme calls for one. Parked in the bottom row at 6.9mm, inside the left
  // extent the VDD4 cap already sets, so it costs no extra area.
  C_MCU_VBAT: { x: -7.0, y: -11.8 },
  // Bulk reservoir for the whole 3.3V rail at the MCU. Works at kHz-to-low-MHz
  // where a few mm of trace inductance is irrelevant, so placement is free --
  // tucked into the bottom row, inside the extent J_SWD and VCAP already set.
  C_MCU_BULK: { x: 7.5, y: -11.8 },
  // VCAP_1 and VDD2 are only 1mm apart on the same edge, so this 0603 is
  // shifted 1mm along the edge and 0.5mm further out (its courtyard is
  // 2.45mm wide vs the 0402s 1.86mm, and clipped the chip pads at CAP_OUT).
  C_MCU_VCAP: { x: CAP_OUT + 0.5, y: PIN_LOCAL.VCAP_1.y - 1.0 },
  // Crystal sits under the OSC pins (pin5/pin6, bottom edge at x=-1.5) to
  // keep the oscillator loop short. Load caps flank it at +-3.1mm.
  Y1: { x: -3.0, y: -8.6 },
  C_XT1_A: { x: -6.1, y: -8.6 },
  C_XT1_B: { x: 0.1, y: -8.6 },
  // Second row, clear of the crystal row above it.
  SW_RESET: { x: -3.0, y: -11.8 },
  R_NRST: { x: 1.5, y: -11.8 },
  R_BOOT0: { x: 4.0, y: -11.8 },
  // SWD header stacked ABOVE the chip, clear of the VDD3 cap at y=+7.6.
  J_SWD: { x: 3.5, y: 9 },
};

// NOTE: no `rot` here. pcbRotation is not a supported prop on <group> and is
// silently mis-applied (see MotorChannel.tsx). Rotating this block would mean
// rotating each component and its offsets, as MotorChannel does.
export const MCU = ({
  pos = { x: 0, y: 0 },
}: {
  /** Where this block sits on the board. The block itself has no opinion. */
  pos?: { x: number; y: number };
} = {}) => (
  <group name="mcu" schAutoLayoutEnabled pcbX={pos.x} pcbY={pos.y}>
    <STM32F411RET6 name="U_MCU" pcbX={P.U_MCU.x} pcbY={P.U_MCU.y} />

    {/* Power */}
    <trace from="U_MCU.VDD1" to="net.V3_3" />
    <trace from="U_MCU.VDD2" to="net.V3_3" />
    <trace from="U_MCU.VDD3" to="net.V3_3" />
    <trace from="U_MCU.VDD4" to="net.V3_3" />
    <trace from="U_MCU.VSS1" to="net.GND" />
    <trace from="U_MCU.VSS2" to="net.GND" />
    <trace from="U_MCU.VSS3" to="net.GND" />
    <trace from="U_MCU.VSS4" to="net.GND" />
    <trace from="U_MCU.VBAT" to="net.V3_3" />
    <trace from="U_MCU.VDDA" to="net.V3_3" />
    <trace from="U_MCU.VSSA" to="net.GND" />

    {/* Each cap sits on its own pin edge, at that pin coordinate along the edge. */}
    <capacitor
      name="C_MCU_VDD1"
      pcbX={P.C_MCU_VDD1.x}
      pcbY={P.C_MCU_VDD1.y}
      capacitance="100nF"
      footprint="0402"
      decouplingFor="U_MCU.VDD1"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="3mm"
    />

    <capacitor
      name="C_MCU_VDD2"
      pcbX={P.C_MCU_VDD2.x}
      pcbY={P.C_MCU_VDD2.y}
      capacitance="100nF"
      footprint="0402"
      decouplingFor="U_MCU.VDD2"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="3mm"
    />

    <capacitor
      name="C_MCU_VDD3"
      pcbX={P.C_MCU_VDD3.x}
      pcbY={P.C_MCU_VDD3.y}
      capacitance="100nF"
      footprint="0402"
      decouplingFor="U_MCU.VDD3"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="3mm"
    />

    <capacitor
      name="C_MCU_VDD4"
      pcbX={P.C_MCU_VDD4.x}
      pcbY={P.C_MCU_VDD4.y}
      capacitance="100nF"
      footprint="0402"
      decouplingFor="U_MCU.VDD4"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="3mm"
    />

    {/* VDDA feeds the ADC and the PLL, and ST's power scheme calls for BOTH a
        100nF and a 1uF here -- the 1uF alone is too slow to cover HF. That
        matters more on this board than on most: all five motor-current
        channels land on this ADC, so VDDA noise sets the current-sense floor
        directly (COL-COTS-0022 / MotorChannel.tsx). */}
    <capacitor
      name="C_MCU_VDDA_HF"
      pcbX={P.C_MCU_VDDA_HF.x}
      pcbY={P.C_MCU_VDDA_HF.y}
      capacitance="100nF"
      footprint="0402"
      decouplingFor="U_MCU.VDDA"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="3mm"
    />
    <capacitor
      name="C_MCU_VDDA"
      pcbX={P.C_MCU_VDDA.x}
      pcbY={P.C_MCU_VDDA.y}
      capacitance="1uF"
      footprint="0402"
      decouplingFor="U_MCU.VDDA"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="6mm"
    />

    {/* VBAT strapped to V3_3 (no backup cell fitted). Deliberately loose --
        see the position table for why this one does not need to be near. */}
    <capacitor
      name="C_MCU_VBAT"
      pcbX={P.C_MCU_VBAT.x}
      pcbY={P.C_MCU_VBAT.y}
      capacitance="100nF"
      footprint="0402"
      decouplingFor="U_MCU.VBAT"
      decouplingTo="net.GND"
      maxDecouplingTraceLength="9mm"
    />

    {/* Bulk reservoir for the 3.3V rail AT the MCU. Without it the four 100nF
        caps have nothing local to recharge from between transients -- the only
        other bulk is C_REG_OUT, which lives in the Power block and will be
        centimetres away once the board is placed. No decouplingFor: a
        reservoir has no proximity requirement, so it imposes no constraint. */}
    <capacitor
      name="C_MCU_BULK"
      pcbX={P.C_MCU_BULK.x}
      pcbY={P.C_MCU_BULK.y}
      capacitance="4.7uF"
      footprint="0805"
    />
    <trace from="net.V3_3" to="C_MCU_BULK.pos" />
    <trace from="net.GND" to="C_MCU_BULK.neg" />
    {/* 1mm further out than the other decoupling caps. At the shared CAP_OUT
        radius the router had to thread the V3_3 run to this cap between the
        chip edge and PC13, producing a pad-to-trace clearance violation and a
        via 0.03mm inside PC13's pad. Backing the cap off opens that channel.
        Still 2.9mm to the VDDA pad, inside the 3mm budget. */}

    {/* VCAP has no decouplingFor, but core still applies an AUTOMATIC
        max-decoupling-trace-length (~1mm) to any capacitor sitting on a chip
        pin, so it needs an explicit budget like the rest.
        VCAP_1 and VDD2 are only 1mm apart on the same edge and a 0603
        courtyard is 2.45 x 0.95mm, so rather than push this cap outward
        (which blew the length budget at 4.27mm) it is shifted 1mm ALONG the
        edge, away from VDD2's cap. It also needs +0.5mm more standoff than
        the 0402s: CAP_OUT is sized for a 1.56mm-wide courtyard and this one
        is 2.45mm, so at plain CAP_OUT its pad clipped the chip's PB1/PB2/PB10
        pads. Net result: ~2.6mm to its pin, clear of chip and neighbours. */}
    <capacitor
      name="C_MCU_VCAP"
      pcbX={P.C_MCU_VCAP.x}
      pcbY={P.C_MCU_VCAP.y}
      capacitance="4.7uF"
      footprint="0603"
      maxDecouplingTraceLength="3mm"
    />
    {/* 4.7uF, NOT the 2.2uF usually quoted for this family. DS10314 Table 16:
        "Capacitance of external capacitor with a SINGLE VCAP pin available =
        4.7 uF, ESR < 1 ohm". The familiar 2.2uF figure is the value for
        packages that expose TWO VCAP pins (the table footnote refers to "the
        two 2.2 uF VCAP capacitors"). LQFP64 exposes ONE (VCAP_1, pin 30), so
        it takes a single 4.7uF -- quoting 2.2uF would be applying a two-pin
        package spec to a one-pin package.
        ESR < 1 ohm means X5R/X7R ceramic — do not substitute a tantalum. */}
    <trace from="U_MCU.VCAP_1" to="C_MCU_VCAP.pos" />
    <trace from="net.GND" to="C_MCU_VCAP.neg" />

    {/* NRST: pull-up + reset button. pullupFor/pulldownFor carry no enforced
        max-trace-length (unlike capacitor decouplingFor), so these can sit in
        the looser outer/inner cluster without tripping the same check. */}
    <resistor
      name="R_NRST"
      pcbX={P.R_NRST.x}
      pcbY={P.R_NRST.y}
      resistance="10k"
      footprint="0402"
      pullupFor="U_MCU.NRST"
      pullupTo="net.V3_3"
    />
    {/* ALPS SKRKAEE020 (JLC C115357), 3.9 x 2.9mm SMD tact switch, replacing
        both the original 6 x 8mm through-hole part and the obscure TS2306A that
        briefly stood in for it. Branded part with a real English datasheet.
        The deciding spec is temperature, not size: the TS2306A was rated
        -20 to +70 C, and COL-PARAM-0010 puts ambient AT 70 C -- zero margin.
        This part is -40 to +85 C, and doubles cycle life to 200,000.
        Still a commodity support part, so no COTS record (same treatment as
        the AMS1117) -- it is a BOM line on Main-Board-01. */}
    {/* schX/schY set by hand: auto-layout parked this symbol at (5.08, 1.90),
        directly on top of the MCU's left-side pin-label column at x=5.30, so
        the ISENSE_leaf2/3/4 labels rendered inside the switch body. Explicit
        schematic coordinates are honoured even inside a schAutoLayoutEnabled
        group -- match-adapt places only the symbols that lack them. */}
    <SKRKAEE020 name="SW_RESET" pcbX={P.SW_RESET.x} pcbY={P.SW_RESET.y} />
    <trace from="U_MCU.NRST" to="SW_RESET.pin1" />
    <trace from="net.GND" to="SW_RESET.pin2" />

    {/* BOOT0: pulled low -> always boots from flash. SWD is the sole
        programming/debug path for this prototype, no bootloader jumper. */}
    <resistor
      name="R_BOOT0"
      pcbX={P.R_BOOT0.x}
      pcbY={P.R_BOOT0.y}
      resistance="10k"
      footprint="0402"
      pulldownFor="U_MCU.BOOT0"
      pulldownTo="net.GND"
    />

    {/* HSE crystal — X32258MSB4SI, 8MHz, 3225 4-pad, JLC C2682774.
        A real part rather than a generic <crystal>, because LOAD CAPACITANCE IS
        A PROPERTY OF THE CRYSTAL: the C_XT1_A/B values below are only correct
        for this one, and change if the part does.
        8MHz suits the F411's PLL cleanly for both the 100MHz core and the 48MHz
        USB clock, should the logging path ever use USB (COL-REQ-0014). */}
    <X32258MSB4SI
      name="Y1"
      pcbX={P.Y1.x}
      pcbY={P.Y1.y}
      loadCapacitance="18pF"
    />
    {/* Refdes Y1, not XT1: the checker accepts X or Y as a crystal prefix and
        reads "XT" as neither.
        The crystal is pinned below the OSC pins (pin5/pin6 sit on the bottom
        edge at x=-1.5) rather than left to the packer, both to keep the
        oscillator loop short and because a free-packed XT1 lands on top of
        C_MCU_VDDA, which is constrained onto that same edge at x=+2.25.
        x=-3.0 keeps XT1's right-hand load cap clear of it. */}
    <trace name="T_XTAL_IN" from="Y1.pin1" to="U_MCU.PH0_OSC_IN" />
    <trace name="T_XTAL_OUT" from="Y1.pin2" to="U_MCU.PH1_OSC_OUT" />
    {/* pin3/pin4 are the CAN, not signal. Grounding them is not optional
        housekeeping: an ungrounded metal can over an oscillator is a floating
        electrode that couples the 8MHz loop into everything around it, and on
        this board that includes four analog current-sense lines. */}
    <trace name="T_XTAL_CASE1" from="Y1.pin3" to="net.GND" />
    <trace name="T_XTAL_CASE2" from="Y1.pin4" to="net.GND" />
    {/* Load caps flank the crystal, staying a rigid trio wherever the packer
        puts it. XT1's courtyard measures 3.60 x 2.90mm and a 0402 is 1.56mm
        wide, so centres need >2.58mm; 3.1mm leaves real clearance. */}
    <capacitor
      name="C_XT1_A"
      pcbX={P.C_XT1_A.x}
      pcbY={P.C_XT1_A.y}
      capacitance="18pF"
      footprint="0402"
    />
    <capacitor
      name="C_XT1_B"
      pcbX={P.C_XT1_B.x}
      pcbY={P.C_XT1_B.y}
      capacitance="18pF"
      footprint="0402"
    />
    <trace name="T_XTAL_CA" from="Y1.pin1" to="C_XT1_A.pos" />
    <trace name="T_XTAL_CA_GND" from="net.GND" to="C_XT1_A.neg" />
    <trace name="T_XTAL_CB" from="Y1.pin2" to="C_XT1_B.pos" />
    <trace name="T_XTAL_CB_GND" from="net.GND" to="C_XT1_B.neg" />

    {/* SWD debug/programming header — the primary dev interface */}
    {/* Left unrotated: pinrow4 is ALREADY horizontal at rotation 0 (9.12 x 1.50).
        An earlier pcbRotation={90} here turned it into a 9.12mm vertical column,
        which is the opposite of what was wanted. Stacked above the chip, clear
        of the VDD3 cap. */}
    {/* NOT POPULATED — bare plated holes only. doNotPlace keeps the footprint
        and the netlist while leaving the part off the assembly.
        A 2.54mm header stands ~8.5mm proud, and COL-PARAM-0020 caps assembled
        height at 4mm HARD, so no header can be fitted in the machine. Bare
        holes are 0mm: solder flying leads for bring-up, or push a male header
        (or pogo adapter) in only while a probe is attached, then remove it.
        The board artwork is unchanged either way — pinrow4 IS four plated
        holes — so this costs nothing to keep. */}
    <pinheader
      name="J_SWD"
      pcbX={P.J_SWD.x}
      pcbY={P.J_SWD.y}
      pinCount={4}
      gender="male"
      pitch="2.54mm"
      footprint="pinrow4"
      doNotPlace
      showSilkscreenPinLabels
      pinLabels={["V3_3", "SWDIO", "SWCLK", "GND"]}
    />
    <trace from="J_SWD.V3_3" to="net.V3_3" />
    <trace from="J_SWD.SWDIO" to="U_MCU.PA13" />
    <trace from="J_SWD.SWCLK" to="U_MCU.PA14" />
    <trace from="J_SWD.GND" to="net.GND" />

    {/* Per-axis motor control and current-sense wiring */}
    {/* Fragments, not <group>s -- a nested group inside a packed group becomes
        another thing for the packer to place, and these hold only traces. */}
    {AXES.map((axis) => (
      <React.Fragment key={axis}>
        <trace from={`U_MCU.${EN_PINS[axis]}`} to={`net.EN_${axis}`} />
        <trace from={`U_MCU.${PH_PINS[axis]}`} to={`net.PH_${axis}`} />
        <trace from={`U_MCU.${ISENSE_PINS[axis]}`} to={`net.ISENSE_${axis}`} />
        {ENC_PINS[axis] ? (
          <trace from={`U_MCU.${ENC_PINS[axis]}`} to={`net.ENC_${axis}`} />
        ) : null}
      </React.Fragment>
    ))}
  </group>
);
