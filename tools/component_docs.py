# -*- coding: utf-8 -*-
"""Sync per-refdes component pages in the vault from the KiCad netlist.

One page per component, 1:1 with the schematic, in the build rung's
Components/ folder. Facts (frontmatter + the block between the gen markers)
are machine-owned and rewritten on every run; everything else on the page is
human-owned and preserved. Pages whose refdes left the design are moved to
Components/_retired/. Format spec: vault _System/Process/component-docs.md.

Usage: python tools/component_docs.py [--check]
  --check  report what would change, write nothing (used by CI/hook dry runs)
"""
import io, os, re, subprocess, sys, tempfile, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
BOARDS = [
    {
        "name": "Main-Board-01",
        "sch": os.path.join(REPO, "boards", "MC3_COL_MAIN_V1.1", "MC3_COL_MAIN_V1.1.kicad_sch"),
        "vault_dir": r"C:\Users\newte\Documents\Design Wiki\Projects\MC3 Collimator\05 Builds\Main-Board-01\Components",
    },
]
GEN_BEGIN = "<!-- component-docs:begin — machine-owned, rewritten by tools/component_docs.py -->"
GEN_END = "<!-- component-docs:end -->"

# Instance roles for the engineering parts. Applied when a page is created or
# while its Role is still #tbd; a human edit to Role is never overwritten.
SEED = {
    "U1": "The 3.3 V LDO (AMS1117-3.3) off `VM` through FB4 — its tab is the output *and* the heatsink; see [[Main-Board-01 Power]] § Derived Rails.",
    "U2": "The MCU — [[COL-COTS-0035]] STM32U595RJT6. Pin assignment is owned by [[Main-Board-01 MCU Pinout]].",
    "U8": "CAN transceiver [[COL-COTS-0030]] TJA1051T/3: 5 V `VCAN5` supply, 3.3 V `VIO`.",
    "U9": "Yaw incremental encoder [[COL-COTS-0032]] AEDR-8300, underside, reading the M10899 ring; A/B to TIM2.",
    "U10": "Yaw homing interrupter [[COL-COTS-0034]] GP1S094 — flag present = `YAW_HOME` high; hand-solder only.",
    "U11": "Yaw far-limit interrupter [[COL-COTS-0034]] GP1S094, 180° from U10, `YAW_LIM` EXTI.",
    "U12": "The 24 V→5.02 V synchronous buck [[COL-COTS-0039]] LM61460, SYNC-locked at 1.00 MHz (50× motor PWM). Chain and rationale: [[Main-Board-01 Power]]; layout: `docs/design/parts/LM61460.md`.",
    "Q1": "Reverse-polarity P-FET (AO4421, −60 V): drain to the input, source to `VIN_SW`; body diode bootstraps it. Gate clamped by D7.",
    "F1": "Input polyfuse, 0.75 A hold / 33 V, 1812. Sizing vs all-stall + 70 °C derating is an open item — [[Main-Board-01 Power]] § Current Budget.",
    "D1": "Input TVS SMAJ28A on `VIN_PROT` (behind the fuse, so a failed-short TVS is fused). Sets the 28 V input ceiling.",
    "D4": "CAN ESD clamp PESD1CAN at the bus pads.",
    "D7": "12 V zener BZT52C12 clamping Q1's gate–source (|V_GS| would be 24 V against a ±20 V rating).",
    "D2": "Heartbeat LED (green, PA5).",
    "D3": "Power LED (red, on +3V3).",
    "D5": "Addressable status pixel 1 of 2 ([[COL-COTS-0036]] XL-1010RGBC), on `VM`, underside; data from PB5/SPI1_MOSI.",
    "D6": "Addressable status pixel 2 of 2 ([[COL-COTS-0036]]), chained from D5.",
    "L1": "Buck inductor [[COL-COTS-0040]] XAL5030-222 (2.2 µH, 3.1 mm tall — tallest part on top).",
    "Y1": "8 MHz HSE crystal (CL = 20 pF, 33 pF load caps).",
    "SW1": "MCU reset button, underside.",
    "J2": "SWD header 1×6, underside, DNP-class bring-up fixture; pin 6 carries `DBG_TX`.",
    "J12": "Machine CAN bare pads (CANH/CANL/GND), underside — kept as the fallback to J13.",
    "J13": "The machine harness connector [[COL-COTS-0041]] TE 84952-6 (1.0 mm 6-way FPC, ZIF, underside): 24 V supply, CAN, and the yaw motor pair on one flat cable.",
    "JP1": "CAN termination enable — bridged solder jumper (bridged = this node is a bus end).",
    "R5": "Q1 gate pull-down 100 k; sets ~120 µA through D7.",
    "J3": "Leaf 2 encoder FFC ([[COL-COTS-0031]] AYF530435, 0.5 mm 4-way): VSENS / GND / SIG / RC_OUT share — see [[Main-Board-01 Encoder Interface]].",
    "J4": "Leaf 1 encoder FFC ([[COL-COTS-0031]]): VSENS / GND / SIG / RC_OUT share.",
    "J5": "Leaf 4 encoder FFC ([[COL-COTS-0031]]): VSENS / GND / SIG / RC_OUT share.",
    "J6": "Leaf 3 encoder FFC ([[COL-COTS-0031]]): VSENS / GND / SIG / RC_OUT share.",
    "R31": "CAN split termination, high side (62 Ω class) — CANH→`TERM_MID`.",
    "R32": "CAN split termination, low side — `TERM_MID`→CANL.",
    "C30": "CAN termination centre cap (common-mode drain) on `TERM_MID`.",
    "R33": "AEDR-8300 LED current set (~15 mA from `VSENS`).",
    "R40": "Pixel data series resistor (470R) at the MCU end of the D5–D6 chain.",
    "R41": "Buck RT: 13.3 k → free-running ≈ 1 MHz (#tbd confirm vs the RT equation).",
    "R42": "Buck UVLO divider, top (100 k from `VIN_SW`).",
    "R43": "Buck UVLO divider, bottom (8.66 k) — rising threshold ≈ 15.8 V.",
    "R44": "RBOOT 0 R — the SW-edge slow-down knob if bench EMI asks for it.",
    "R45": "Buck FB divider, top (100 k from `VM` at the output caps).",
    "R46": "Buck FB divider, bottom (24.9 k) — V_out = 5.02 V.",
    "R47": "Feedforward series 1 k (with C55) from `VM` into the FB node.",
    "C51": "SYNC coupling 1 nF — `BUCK_SYNC` (PB4/LPTIM1, 1.00 MHz) AC-coupled into EN/SYNC.",
    "C52": "Bootstrap cap 100 nF, BOOT→SW through R44.",
    "C53": "Buck VCC 1 µF at pin 2 / AGND.",
    "C54": "Buck BIAS decoupler at pin 1 (BIAS rides `VM` for efficiency).",
    "C55": "Feedforward 4.7 pF (with R47) across the FB top divider.",
    "C50": "Buck input 100 nF 50 V — the closest cap to a VIN/PGND pair; the hot loop starts here.",
    "C48": "Buck input bulk 10 µF 50 V (pair with C49) on `VIN_SW`.",
    "C49": "Buck input bulk 10 µF 50 V (pair with C48) on `VIN_SW`.",
    "C56": "Buck output 22 µF (pair with C57) at the `VM` trunk entry — the FB sense point.",
    "C57": "Buck output 22 µF (pair with C56).",
    "C2": "LDO output 22 µF tantalum — the ESR is what stabilises the AMS1117 (#tbd window unchecked).",
    "C32": "LDO input 10 µF on `VM_LDO` behind FB4 (LC resonance ≈115 kHz — see [[Main-Board-01 Power]] § Open).",
    "C17": "`VSENS` rail cap 4.7 µF — one cap serves all four encoder connectors.",
    "FB1": "VDDA feed bead (600 Ω @ 100 MHz).",
    "FB2": "`VSENS` feed bead from `VM` (600 Ω @ 100 MHz) — the encoder supply filter.",
    "FB3": "`VCAN5` feed bead from `VM` (600 Ω @ 100 MHz).",
    "FB4": "LDO input bead from `VM` (120 Ω @ 100 MHz, 2 A class — the 600 Ω bead is too small here).",
    "R1": "I²C address strap (A1/A0 tri-level) — per-instance value on the root sheet.",
    "R2": "I²C address strap (A1/A0 tri-level) — per-instance value on the root sheet.",
    "R3": "I²C address strap (A1/A0 tri-level) — per-instance value on the root sheet.",
    "R4": "I²C address strap (A1/A0 tri-level) — per-instance value on the root sheet.",
}

CHANNEL_SHEETS = {"/leaf1/", "/leaf2/", "/leaf3/", "/leaf4/", "/yaw/"}
RAILS = {"+3V3", "VM", "VSENS", "/CAN/VCAN5", "/MCU/VDDA", "/Power/VM_LDO", "/Power/VIN_SW", "VIN_PAD", "VIN_PROT", "GND"}
CTRL = re.compile("[" + "".join(chr(c) for c in range(0x20) if c != 0x0A) + "]")


def run_netlist(sch):
    out = os.path.join(tempfile.gettempdir(), "component_docs_net.xml")
    cli = KICAD_CLI if os.path.exists(KICAD_CLI) else "kicad-cli"
    subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, sch],
                   check=True, capture_output=True)
    return io.open(out, encoding="utf-8").read()


def parse(xml):
    comps = {}
    for m in re.finditer(r'<comp ref="([^"]+)">([\s\S]*?)</comp>', xml):
        ref, body = m.group(1), m.group(2)
        g = lambda pat: (re.search(pat, body).group(1) if re.search(pat, body) else "")
        fields = dict(re.findall(r'<field name="([^"]+)">([^<]*)</field>', body))
        comps[ref] = {
            "value": g(r"<value>([^<]*)</value>"),
            "footprint": g(r"<footprint>([^<]*)</footprint>"),
            "lib": g(r'<libsource lib="[^"]*" part="([^"]*)"'),
            "sheet": g(r'<sheetpath names="([^"]*)"') or "/",
            "dnp": ('<property name="dnp"' in body),
            "lcsc": fields.get("LCSC", ""),
            "mpn": fields.get("MPN", ""),
            "cots": next((v for v in fields.values() if re.match(r"COL-COTS-\d+", v)), ""),
            "pins": [],
        }
    for m in re.finditer(r'<net code="\d+" name="([^"]+)"[^>]*>([\s\S]*?)</net>', xml):
        net = m.group(1)
        for ref, pin, fn in re.findall(r'<node ref="([^"]+)" pin="([^"]*)"(?: pinfunction="([^"]*)")?', m.group(2)):
            if ref in comps:
                comps[ref]["pins"].append((pin, fn, net))
    for c in comps.values():
        c["pins"].sort(key=lambda p: (len(p[0]), p[0]))
    return comps


def auto_role(ref, c):
    if ref in SEED:
        return SEED[ref]
    nets = [p[2] for p in c["pins"]]
    kind = re.match(r"[A-Za-z]+", ref).group(0)
    chan = c["sheet"] in CHANNEL_SHEETS
    prefix = f"Motor-channel instance (`{c['sheet'].strip('/')}` — see [[Main-Board-01 Motor Channel]]): " if chan else ""
    if kind == "H":
        return "M2 mounting hole."
    if kind == "TP":
        return f"Test point on `{nets[0]}`." if nets else "Test point."
    if kind == "C" and len(nets) == 2 and "GND" in nets:
        other = nets[0] if nets[1] == "GND" else nets[1]
        if other in RAILS or other.startswith("+"):
            return prefix + f"{c['value']} decoupling/bulk on `{other}`."
        return prefix + f"{c['value']} filter cap on `{other}` to GND."
    if kind == "R" and len(nets) == 2:
        if "+3V3" in nets:
            other = nets[0] if nets[1] == "+3V3" else nets[1]
            if other == "GND":
                return prefix + "Strap to rail."
            return prefix + f"{c['value']} pull-up on `{other}` to +3V3."
        if "GND" in nets:
            other = nets[0] if nets[1] == "GND" else nets[1]
            return prefix + f"{c['value']} to GND on `{other}` (pull-down / set resistor)."
        return prefix + f"{c['value']} series element `{nets[0]}` → `{nets[1]}`."
    if kind == "FB" and len(nets) == 2:
        return prefix + f"Ferrite bead `{nets[0]}` → `{nets[1]}`."
    if kind == "D" and "LED" in c["lib"].upper():
        return prefix + "Indicator LED."
    if chan:
        return prefix + "#tbd — instance role."
    return "#tbd — one line: why this part is here (identity/rationale belong in the COTS record)."


def gen_block(ref, c, board):
    cots_link = f"[[{c['cots']}]]" if c["cots"] else "—"
    rows = [
        "| | |", "|---|---|",
        f"| Value | `{c['value']}` |",
        f"| Footprint | `{c['footprint']}` |",
        f"| Symbol | `{c['lib']}` |",
        f"| Sheet | `{c['sheet']}` |",
        f"| LCSC / MPN | {c['lcsc'] or '—'} / {c['mpn'] or '—'} |",
        f"| COTS record | {cots_link} |",
        f"| Fitted | {'**DNP**' if c['dnp'] else 'yes'} |",
    ]
    pins = ["", "| Pin | Function | Net |", "|---|---|---|"]
    for pin, fn, net in c["pins"]:
        pins.append(f"| {pin} | {fn or ''} | `{net}` |")
    return "\n".join([GEN_BEGIN] + rows + pins + [GEN_END])


def frontmatter(ref, c, board):
    esc = lambda s: s.replace('"', "'")
    return "\n".join([
        "---", "type: component", f"board: {board}", f"refdes: {ref}",
        f'value: "{esc(c["value"])}"', f'sheet: "{c["sheet"]}"',
        f'lcsc: "{c["lcsc"]}"', f'cots: "{c["cots"]}"',
        f"dnp: {'true' if c['dnp'] else 'false'}",
        "tags:", "  - component", "---",
    ])


def sync(board, check=False):
    xml = run_netlist(board["sch"])
    comps = parse(xml)
    vdir = board["vault_dir"]
    retired_dir = os.path.join(vdir, "_retired")
    os.makedirs(vdir, exist_ok=True)
    created = updated = unchanged = 0
    tbd = []
    for ref, c in sorted(comps.items()):
        path = os.path.join(vdir, f"{board['name']} {ref}.md")
        fm, gen = frontmatter(ref, c, board["name"]), gen_block(ref, c, board["name"])
        if os.path.exists(path):
            old = io.open(path, encoding="utf-8").read()
            m = re.search(r"## Role\n([\s\S]*?)\n## Facts", old)
            role = m.group(1).strip() if m else auto_role(ref, c)
            auto = auto_role(ref, c)
            if "#tbd" in role and auto != role and "#tbd" not in auto:
                role = auto
        else:
            role = auto_role(ref, c)
        body = f"{fm}\n# {board['name']} {ref}\n\n## Role\n\n{role}\n\n## Facts\n\n{gen}\n"
        assert not CTRL.search(body), f"control char in {ref}"
        if os.path.exists(path) and io.open(path, encoding="utf-8").read() == body:
            unchanged += 1
        else:
            if not check:
                io.open(path, "w", encoding="utf-8", newline="\n").write(body)
            created += 0 if os.path.exists(path) else 1
            updated += 1
        if role.startswith("#tbd"):
            tbd.append(ref)
    # retire pages whose refdes left the design
    retired = []
    for fn in os.listdir(vdir):
        m = re.match(re.escape(board["name"]) + r" (\S+)\.md$", fn)
        if m and m.group(1) not in comps:
            retired.append(m.group(1))
            if not check:
                os.makedirs(retired_dir, exist_ok=True)
                dst = os.path.join(retired_dir, fn)
                shutil.move(os.path.join(vdir, fn), dst)
                t = io.open(dst, encoding="utf-8").read()
                io.open(dst, "w", encoding="utf-8", newline="\n").write(
                    t + "\n> Retired: this refdes is no longer in the design.\n")
    print(f"[component-docs] {board['name']}: {len(comps)} components — "
          f"{updated} written, {unchanged} unchanged, retired {retired or 'none'}, "
          f"{len(tbd)} roles still #tbd" + (f" ({', '.join(tbd[:10])}…)" if len(tbd) > 10 else f" {tbd}" if tbd else ""))


if __name__ == "__main__":
    check = "--check" in sys.argv
    for b in BOARDS:
        sync(b, check)
