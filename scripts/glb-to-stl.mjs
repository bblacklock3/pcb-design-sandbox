#!/usr/bin/env node
// GLB -> binary STL, for getting a tscircuit board onto a 3D printer.
//
// WHY: tsci has no STL/3MF board export. `-f component-box-3mf` is a
// parts-organiser bin generator, not a model of the board. `-f step` is CAD,
// not a mesh, and it instances parts via MAPPED_ITEM so it is not a
// slicer-friendly soup of triangles either. GLB is the only export that is
// already a mesh, so this converts it.
//
// AXES: glTF is Y-up; slicers are Z-up with the bed at Z=0. This applies
//   (x, y, z) -> (x, -z, y)
// which is a proper rotation (det = +1), so winding and normals stay correct.
// Result lands the board flat in XY with thickness along Z.
//
// UNITS: tscircuit's GLB is already in millimetres (the 64mm board measures
// 64.0), and STL is unitless with slicers assuming mm. So no scaling.
//
// USAGE
//   node scripts/glb-to-stl.mjs in.glb out.stl [options]
//     --only <regex>      keep only nodes whose name matches
//     --exclude <regex>   drop nodes whose name matches
//     --list              print node names and exit
//     --separate <dir>    also write one STL per node
//
// EXAMPLES
//   node scripts/glb-to-stl.mjs board.glb board.stl
//   node scripts/glb-to-stl.mjs board.glb pcb.stl --only '^Box0$'
//   node scripts/glb-to-stl.mjs board.glb parts.stl --exclude '^Box0$'

import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const flag = (name) => {
  const i = args.indexOf(name);
  return i === -1 ? null : args[i + 1];
};
const has = (name) => args.includes(name);

const [inPath, outPath] = args.filter((a, i) => !a.startsWith("--") && !(i > 0 && args[i - 1]?.startsWith("--") && !["--list"].includes(args[i - 1])));
if (!inPath) {
  console.error("usage: node scripts/glb-to-stl.mjs in.glb out.stl [--only re] [--exclude re] [--list] [--separate dir]");
  process.exit(1);
}

// ---- parse GLB container -------------------------------------------------
const buf = fs.readFileSync(inPath);
if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error("not a GLB (bad magic)");
const jsonLen = buf.readUInt32LE(12);
const gltf = JSON.parse(buf.slice(20, 20 + jsonLen).toString("utf8"));
// BIN chunk follows the JSON chunk, 4-byte aligned
let off = 20 + jsonLen;
off += (4 - (off % 4)) % 4;
const binLen = buf.readUInt32LE(off);
const bin = buf.slice(off + 8, off + 8 + binLen);

const viewOf = (i) => {
  const v = gltf.bufferViews[i];
  const start = v.byteOffset || 0;
  return bin.slice(start, start + v.byteLength);
};

const readAccessor = (i) => {
  const a = gltf.accessors[i];
  if (a.sparse) throw new Error("sparse accessors not supported");
  const v = gltf.bufferViews[a.bufferView];
  if (v.byteStride) throw new Error("interleaved bufferViews not supported");
  const b = viewOf(a.bufferView);
  const base = a.byteOffset || 0;
  const n = a.count * { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[a.type];
  const width = { 5126: 4, 5125: 4, 5123: 2, 5121: 1 }[a.componentType];
  if (!width) throw new Error(`unhandled componentType ${a.componentType}`);
  // Buffer slices sit at an arbitrary offset inside a shared ArrayBuffer, which
  // typed arrays refuse unless it happens to be aligned. Copy into a fresh one.
  const src = b.subarray(base, base + n * width);
  const ab = new ArrayBuffer(src.length);
  new Uint8Array(ab).set(src);
  switch (a.componentType) {
    case 5126: return new Float32Array(ab, 0, n);
    case 5125: return new Uint32Array(ab, 0, n);
    case 5123: return new Uint16Array(ab, 0, n);
    case 5121: return new Uint8Array(ab, 0, n);
  }
};

// ---- collect triangles ---------------------------------------------------
const only = flag("--only") ? new RegExp(flag("--only")) : null;
const exclude = flag("--exclude") ? new RegExp(flag("--exclude")) : null;

const nodes = (gltf.nodes || []).filter((n) => n.mesh !== undefined);
if (has("--list")) {
  for (const n of nodes) console.log(n.name || "(unnamed)");
  process.exit(0);
}

/** glTF Y-up -> STL Z-up, in true PCB coordinates.
 *
 *  The axis mapping is NOT the obvious (x, -z, y). Verified against
 *  circuit.json: U_MCU sits at glTF [21, 0.7, 2] and pcb (-21, 2), so
 *      pcbX = -x,  pcbY = z,  height = y
 *  Getting this wrong yields a board rotated 180 degrees about Z. That is
 *  self-consistent and prints identically, so it is invisible in the mesh --
 *  it only shows up when you register the result against the DXF or drop it
 *  into a CAD assembly. det = +1, so winding and normals are preserved. */
const toZUp = (x, y, z) => [-x, z, y];

function trianglesFor(node) {
  const t = node.translation || [0, 0, 0];
  const tris = [];
  for (const prim of gltf.meshes[node.mesh].primitives) {
    if ((prim.mode ?? 4) !== 4) continue; // triangles only
    const pos = readAccessor(prim.attributes.POSITION);
    const idx = prim.indices !== undefined
      ? readAccessor(prim.indices)
      : { length: pos.length / 3, [Symbol.iterator]: null };
    const count = prim.indices !== undefined ? idx.length : pos.length / 3;
    for (let i = 0; i < count; i += 3) {
      const v = [];
      for (let k = 0; k < 3; k++) {
        const vi = (prim.indices !== undefined ? idx[i + k] : i + k) * 3;
        v.push(toZUp(pos[vi] + t[0], pos[vi + 1] + t[1], pos[vi + 2] + t[2]));
      }
      tris.push(v);
    }
  }
  return tris;
}

function writeSTL(tris, file, header) {
  const out = Buffer.alloc(84 + tris.length * 50);
  out.write(header.slice(0, 79), 0, "ascii");
  out.writeUInt32LE(tris.length, 80);
  let p = 84;
  for (const [a, b, c] of tris) {
    const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
    const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const len = Math.hypot(nx, ny, nz) || 1;
    nx /= len; ny /= len; nz /= len;
    for (const f of [nx, ny, nz, ...a, ...b, ...c]) { out.writeFloatLE(f, p); p += 4; }
    out.writeUInt16LE(0, p); p += 2;
  }
  fs.writeFileSync(file, out);
  return out.length;
}

const kept = nodes.filter((n) => {
  const name = n.name || "";
  if (only && !only.test(name)) return false;
  if (exclude && exclude.test(name)) return false;
  return true;
});

const all = [];
const bbox = { mn: [1e9, 1e9, 1e9], mx: [-1e9, -1e9, -1e9] };
const sepDir = flag("--separate");
if (sepDir) fs.mkdirSync(sepDir, { recursive: true });

for (const n of kept) {
  const tris = trianglesFor(n);
  for (const t of tris) all.push(t); // not push(...tris): blows the stack on big meshes
  if (sepDir) {
    const safe = (n.name || "node").replace(/[^A-Za-z0-9_.-]/g, "_");
    writeSTL(tris, path.join(sepDir, `${safe}.stl`), `tscircuit ${n.name}`);
  }
  for (const v of tris) for (const p of v) for (let i = 0; i < 3; i++) {
    bbox.mn[i] = Math.min(bbox.mn[i], p[i]);
    bbox.mx[i] = Math.max(bbox.mx[i], p[i]);
  }
}

if (!outPath) { console.error("no output path given"); process.exit(1); }
const bytes = writeSTL(all, outPath, "tscircuit board export");

console.log(`nodes: ${kept.length}/${nodes.length}   triangles: ${all.length}`);
console.log(`bbox  X ${bbox.mn[0].toFixed(2)}..${bbox.mx[0].toFixed(2)}   Y ${bbox.mn[1].toFixed(2)}..${bbox.mx[1].toFixed(2)}   Z ${bbox.mn[2].toFixed(2)}..${bbox.mx[2].toFixed(2)} (mm)`);
console.log(`size  ${(bbox.mx[0] - bbox.mn[0]).toFixed(2)} x ${(bbox.mx[1] - bbox.mn[1]).toFixed(2)} x ${(bbox.mx[2] - bbox.mn[2]).toFixed(2)} mm`);
console.log(`wrote ${outPath} (${(bytes / 1e6).toFixed(2)} MB)`);
