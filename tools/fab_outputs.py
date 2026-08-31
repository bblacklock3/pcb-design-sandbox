# -*- coding: utf-8 -*-
"""Generate the complete, traceable fab package: gerbers + drill + BOM + CPL + zip.

Everything is plotted/generated fresh from the on-disk board in one run, so the
files in a package can never be from different saves. The zip is named
<board>_fab_<YYYYMMDD-HHMM>_<git-hash>[-dirty].zip — the hash is the traceability
key (an exact recoverable design state), the datetime is for humans, and -dirty
means the board files had uncommitted changes (fine for iteration, never for the
zip you actually upload). A MANIFEST.txt inside records the commit, timestamp and
per-file SHA-256. The script warns if KiCad holds the project open (a .lck file),
since it cannot see unsaved editor state.

BOM comes from the schematic netlist (kicad-cli, read-only); components whose
symbol carries an `Assembly` field are kept in the BOM but marked
DO NOT ASSEMBLE and are stripped from the centroid file. Footprints with no
purchasable identity (bare pads, holes, test points, jumpers, silkscreen
logos) are excluded from both. Gerbers use the plot settings stored in the
board (--board-plot-params); drill is Excellon, absolute origin, PTH/NPTH split.

Usage: python tools/fab_outputs.py            -> full package + zip into fab/
       python tools/fab_outputs.py --no-zip   -> loose files only (iteration)
"""
import csv, glob, hashlib, io, os, re, subprocess, sys, tempfile, zipfile
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
BOARD_DIR = os.path.join(REPO, "boards", "MC3_COL_MAIN_V1.1")
SCH = os.path.join(BOARD_DIR, "MC3_COL_MAIN_V1.1.kicad_sch")
PCB = os.path.join(BOARD_DIR, "MC3_COL_MAIN_V1.1.kicad_pcb")
OUT = os.path.join(BOARD_DIR, "fab")
NAME = "MC3_COL_MAIN_V1.1"
SKIP_FP = ("SolderPads", "MountingHole", "TestPoint", "SolderJumper", "LOGO")


def cli(*args):
    exe = KICAD_CLI if os.path.exists(KICAD_CLI) else "kicad-cli"
    subprocess.run([exe, *args], check=True, capture_output=True)


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip()


def design_state():
    """(short-hash, dirty) for the board directory; dirty = uncommitted changes."""
    h = git("rev-parse", "--short", "HEAD") or "nogit"
    status = git("status", "--porcelain", "--", os.path.relpath(BOARD_DIR, REPO))
    # untracked files (??) are reference material, not design state
    dirty = any(ln and not ln.startswith("??") for ln in status.split("\n"))
    return h, dirty


def plot_gerbers():
    for f in glob.glob(os.path.join(OUT, "*.g*")) + glob.glob(os.path.join(OUT, "*.drl")):
        os.remove(f)  # never let a stale layer survive into a package
    cli("pcb", "export", "gerbers", "--board-plot-params", "-o", OUT + os.sep, PCB)
    cli("pcb", "export", "drill", "--excellon-separate-th",
        "--drill-origin", "absolute", "-o", OUT + os.sep, PCB)


def make_zip(stamp_files):
    h, dirty = design_state()
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    tag = f"{h}-dirty" if dirty else h
    zpath = os.path.join(OUT, f"{NAME}_fab_{ts}_{tag}.zip")
    manifest = [f"board: {NAME}", f"generated: {datetime.now().isoformat(timespec='seconds')}",
                f"git: {git('rev-parse', 'HEAD') or 'no repository'}{' (DIRTY board tree)' if dirty else ''}",
                ""]
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(stamp_files):
            data = open(p, "rb").read()
            manifest.append(f"{hashlib.sha256(data).hexdigest()}  {os.path.basename(p)}")
            z.writestr(os.path.basename(p), data)
        z.writestr("MANIFEST.txt", "\n".join(manifest) + "\n")
    print(f"[fab] ZIP: {zpath}")
    if dirty:
        print("[fab] WARNING: board tree has uncommitted changes — this zip is for "
              "iteration only. Commit (and tag) before uploading to a fab.")
    return zpath


def main():
    if glob.glob(os.path.join(BOARD_DIR, "~*.lck")):
        print("[fab] WARNING: KiCad has this project open — make sure the board is SAVED, "
              "or this package is of the last save, not what you see on screen.")
    os.makedirs(OUT, exist_ok=True)
    plot_gerbers()
    net = os.path.join(tempfile.gettempdir(), "fab_net.xml")
    cli("sch", "export", "netlist", "--format", "kicadxml", "-o", net, SCH)
    xml = io.open(net, encoding="utf-8").read()

    comps = {}
    for m in re.finditer(r'<comp ref="([^"]+)">([\s\S]*?)</comp>', xml):
        ref, body = m.group(1), m.group(2)
        g = lambda p: (re.search(p, body).group(1) if re.search(p, body) else "")
        fp = g(r"<footprint>([^<]*)</footprint>")
        if any(k in fp for k in SKIP_FP):
            continue
        fields = dict(re.findall(r'<field name="([^"]+)">([^<]*)</field>', body))
        comps[ref] = {
            "value": g(r"<value>([^<]*)</value>"),
            "package": fp.split(":")[-1],
            "mpn": fields.get("MPN", ""),
            "lcsc": fields.get("LCSC", ""),
            "assembly": fields.get("Assembly", ""),
            "dnp": ('<property name="dnp"' in body),
        }

    # ---- BOM: group by identity, hand-solder lines marked, never bought ----
    groups = {}
    for ref, c in comps.items():
        key = (c["value"], c["package"], c["mpn"], c["lcsc"], bool(c["assembly"]), c["dnp"])
        groups.setdefault(key, []).append(ref)
    bom_path = os.path.join(OUT, f"BOM_{NAME}.csv")
    with open(bom_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Item", "Designator", "Qty", "Value", "Package/Footprint",
                    "Manufacturer Part Number", "LCSC Part Number", "Assembly"])
        n = 0
        for (val, pkg, mpn, lcsc, hand, dnp), refs in sorted(
                groups.items(), key=lambda kv: kv[1][0]):
            n += 1
            note = "DO NOT ASSEMBLE - customer installed" if hand else ("DNP" if dnp else "")
            w.writerow([n, ",".join(sorted(refs)), len(refs), val, pkg, mpn, lcsc, note])

    # ---- centroid: kicad-cli pos, then strip hand-solder refs ----
    pos_raw = os.path.join(tempfile.gettempdir(), "fab_pos.csv")
    cli("pcb", "export", "pos", "--format", "csv", "--units", "mm",
        "--side", "both", "-o", pos_raw, PCB)
    hand = {r for r, c in comps.items() if c["assembly"]}
    cpl_path = os.path.join(OUT, f"CPL_{NAME}.csv")
    kept = dropped = 0
    with open(pos_raw, newline="", encoding="utf-8") as fin, \
         open(cpl_path, "w", newline="", encoding="utf-8-sig") as fout:
        r, w = csv.reader(fin), csv.writer(fout)
        header = next(r)
        w.writerow(["Designator", "Value", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
        for row in r:
            ref = row[0]
            if ref in hand or any(k in row[2] for k in SKIP_FP) or ref not in comps:
                dropped += 1
                continue
            # kicad-cli order: Ref, Val, Package, PosX, PosY, Rot, Side
            w.writerow([row[0], row[1], row[2], row[3], row[4], row[5],
                        "Top" if row[6].lower().startswith("top") else "Bottom"])
            kept += 1
    print(f"[fab] BOM: {bom_path} ({n} lines, {sum(len(v) for v in groups.values())} components)")
    print(f"[fab] CPL: {cpl_path} ({kept} placements, {dropped} hand-solder refs stripped: {sorted(hand)})")
    if "--no-zip" not in sys.argv:
        gerbers = [p for p in glob.glob(os.path.join(OUT, "*"))
                   if os.path.splitext(p)[1].lower() not in (".csv", ".zip")]
        make_zip(gerbers)


if __name__ == "__main__":
    main()
