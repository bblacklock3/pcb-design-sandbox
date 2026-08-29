# -*- coding: utf-8 -*-
"""Sync per-refdes component pages in the vault from the KiCad netlist.

Fully one-way: KiCad is the source. Each symbol's per-instance Description
field is the component's Role; the generator renders it, plus the pin→net
table and identity facts, into one vault page per refdes. Where no
Description is set, the role is auto-classified from the net pattern
(decouplers, filters, pull-ups, beads, test points…) and #tbd otherwise —
set the Description on the symbol in eeschema to fix a #tbd, never the page.
Anything a human writes BELOW the end marker on a page is preserved.
Pages whose refdes left the design move to Components/_retired/.
Format spec: vault _System/Process/component-docs.md.

Usage: python tools/component_docs.py [--check]
"""
import io, os, re, subprocess, sys, tempfile, shutil
from html import unescape

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
TBD = "#tbd — set the Description field on the symbol in eeschema."

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
        g = lambda pat: (unescape(re.search(pat, body).group(1)) if re.search(pat, body) else "")
        fields = {k: unescape(v) for k, v in re.findall(r'<field name="([^"]+)">([^<]*)</field>', body)}
        comps[ref] = {
            "value": g(r"<value>([^<]*)</value>"),
            "footprint": g(r"<footprint>([^<]*)</footprint>"),
            "lib": g(r'<libsource lib="[^"]*" part="([^"]*)"'),
            "sheet": g(r'<sheetpath names="([^"]*)"') or "/",
            "desc": g(r"<description>([^<]*)</description>"),
            "note": fields.get("Note", ""),
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
    """Net-pattern classification for parts with no Description set."""
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
            return prefix + f"{c['value']} pull-up on `{other}` to +3V3."
        if "GND" in nets:
            other = nets[0] if nets[1] == "GND" else nets[1]
            return prefix + f"{c['value']} to GND on `{other}` (pull-down / set resistor)."
        return prefix + f"{c['value']} series element `{nets[0]}` → `{nets[1]}`."
    if kind == "FB" and len(nets) == 2:
        return prefix + f"Ferrite bead `{nets[0]}` → `{nets[1]}`."
    if kind == "D" and "LED" in c["lib"].upper():
        return prefix + "Indicator LED."
    return TBD


def gen_block(ref, c):
    role = c["desc"] or auto_role(ref, c)
    src = "symbol Description" if c["desc"] else ("auto-classified" if role != TBD else "—")
    cots_link = f"[[{c['cots']}]]" if c["cots"] else "—"
    rows = [
        "| | |", "|---|---|",
        f"| **Role** | {role} *({src})* |",
    ]
    if c["note"]:
        rows.append(f"| Note | {c['note']} |")
    rows += [
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
    return role, "\n".join([GEN_BEGIN, ""] + rows + pins + ["", GEN_END])


def frontmatter(ref, c, board, role):
    esc = lambda s: s.replace('"', "'")
    return "\n".join([
        "---", "type: component", f"board: {board}", f"refdes: {ref}",
        f'value: "{esc(c["value"])}"', f'sheet: "{c["sheet"]}"',
        f'description: "{esc(role)}"',
        f'lcsc: "{c["lcsc"]}"', f'cots: "{c["cots"]}"',
        f"dnp: {'true' if c['dnp'] else 'false'}",
        "tags:", "  - component", "---",
    ])


def sync(board, check=False):
    comps = parse(run_netlist(board["sch"]))
    vdir = board["vault_dir"]
    os.makedirs(vdir, exist_ok=True)
    written = unchanged = 0
    tbd = []
    for ref, c in sorted(comps.items()):
        path = os.path.join(vdir, f"{board['name']} {ref}.md")
        role, gen = gen_block(ref, c)
        tail = ""
        if os.path.exists(path):
            old = io.open(path, encoding="utf-8").read()
            i = old.find(GEN_END)
            if i >= 0:
                tail = old[i + len(GEN_END):].strip("\n")
        body = f"{frontmatter(ref, c, board['name'], role)}\n# {board['name']} {ref}\n\n{gen}\n"
        if tail:
            body += "\n" + tail + "\n"
        assert not CTRL.search(body), f"control char in {ref}"
        if os.path.exists(path) and io.open(path, encoding="utf-8").read() == body:
            unchanged += 1
        else:
            if not check:
                io.open(path, "w", encoding="utf-8", newline="\n").write(body)
            written += 1
        if role == TBD:
            tbd.append(ref)
    retired = []
    for fn in os.listdir(vdir):
        m = re.match(re.escape(board["name"]) + r" (\S+)\.md$", fn)
        if m and m.group(1) not in comps:
            retired.append(m.group(1))
            if not check:
                rdir = os.path.join(vdir, "_retired")
                os.makedirs(rdir, exist_ok=True)
                dst = os.path.join(rdir, fn)
                shutil.move(os.path.join(vdir, fn), dst)
                t = io.open(dst, encoding="utf-8").read()
                io.open(dst, "w", encoding="utf-8", newline="\n").write(
                    t + "\n> Retired: this refdes is no longer in the design.\n")
    print(f"[component-docs] {board['name']}: {len(comps)} components — "
          f"{written} written, {unchanged} unchanged, retired {retired or 'none'}, "
          f"{len(tbd)} without a Description" + (f" {tbd}" if tbd else ""))


if __name__ == "__main__":
    check = "--check" in sys.argv
    for b in BOARDS:
        sync(b, check)
