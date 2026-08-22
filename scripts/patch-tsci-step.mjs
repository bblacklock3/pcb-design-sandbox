#!/usr/bin/env node
// Re-apply the STEP-export fix to the globally installed tscircuit CLI.
//
// WHY THIS EXISTS
// ---------------
// `tsci export -f step` silently drops EVERY component that has an external
// STEP model. The board exports, the file looks plausible, and not one part is
// in it. On MC3_COL_MAIN_V1.0 that was all 20 JLC-sourced parts -- the MCU,
// four drivers, four amplifiers, four shunts, four FFC connectors, the
// regulator, the crystal and the reset button.
//
// The cause is a regex in the CLI's STEP tokenizer:
//
//     /#\d+\s*=\s*([A-Z0-9_]+)\s*\(([\s\S]*)\);/
//                                        ^^^^  requires ")" then ";" with
//                                              NOTHING between them
//
// SolidWorks writes entities as `... ) ;` with a space, and every model the
// JLC parts engine serves is SolidWorks-exported. So the tokenizer throws on
// entity #1 of every file. Measured on C2843766.step: 21,109 entities end
// `) ;` against 1,978 ending `);`.
//
// The failure is reported as a per-model warning on stderr and the export then
// "succeeds", which is why it is easy to miss. Check for it with:
//     grep -c MAPPED_ITEM board.step     # 0 = broken, one per placed part = OK
//
// This does NOT need <cadmodel> declarations, and supplying your own .step
// would fail identically -- user-supplied models go through the same
// tokenizeSTEP path.
//
// Run this after any `npm i -g tscircuit` / update. Idempotent.

import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const REPLACEMENTS = [
  // simple entity:  #12 = CARTESIAN_POINT ( 'NONE', ( 1.0, 2.0, 3.0 ) ) ;
  [String.raw`([A-Z0-9_]+)\s*\(([\s\S]*)\);`, String.raw`([A-Z0-9_]+)\s*\(([\s\S]*)\)\s*;`],
  // complex entity: #12 = ( NAMED_UNIT ( * ) SI_UNIT ( .MILLI., .METRE. ) ) ;
  [String.raw`#\d+\s*=\s*\(([\s\S]*)\);`, String.raw`#\d+\s*=\s*\(([\s\S]*)\)\s*;`],
];

function findMain() {
  const root = execSync("npm root -g", { encoding: "utf8" }).trim();
  const p = path.join(root, "tscircuit/node_modules/@tscircuit/cli/dist/cli/main.js");
  if (!fs.existsSync(p)) throw new Error(`CLI bundle not found at ${p}`);
  return p;
}

const target = findMain();
let src = fs.readFileSync(target, "utf8");

let applied = 0;
let already = 0;
for (const [from, to] of REPLACEMENTS) {
  if (src.includes(to)) {
    already++;
    continue;
  }
  const n = src.split(from).length - 1;
  if (n === 0) {
    console.error(`  ! pattern not found (upstream may have changed):\n    ${from}`);
    continue;
  }
  if (n > 1) {
    console.error(`  ! pattern matched ${n} times, expected 1 -- not patching:\n    ${from}`);
    continue;
  }
  src = src.split(from).join(to);
  applied++;
}

if (applied === 0) {
  console.log(
    already === REPLACEMENTS.length
      ? "Already patched, nothing to do."
      : "Nothing applied -- see warnings above.",
  );
  process.exit(already === REPLACEMENTS.length ? 0 : 1);
}

if (!fs.existsSync(`${target}.bak`)) fs.copyFileSync(target, `${target}.bak`);
fs.writeFileSync(target, src);
console.log(`Patched ${applied} regex(es) in ${target}`);
console.log(`Backup: ${target}.bak`);
console.log("Verify:  tsci export <file> -f step -o out.step && grep -c MAPPED_ITEM out.step");
