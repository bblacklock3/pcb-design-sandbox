#!/usr/bin/env node
// Orthographic top view of the board as SVG.
//
// "Orthographic" is free here: a true top view has no perspective by
// construction, so this projects straight down the Z axis. Component bodies
// come from the GLB export, so the silhouettes are the real part geometry
// rather than footprint rectangles, and each one is drawn as a darker side
// silhouette with its lighter top face on top -- which is what gives it a 3D
// read without any perspective.
//
// USAGE
//   node scripts/render-top-view.mjs [options]
//     --circuit <path>   default dist/index/circuit.json
//     --glb <path>       default dist/3d/board.glb   (omit -> flat 2D view)
//     --out <path>       default dist/3d/top-view.svg
//     --px <n>           pixel width hint for raster consumers (default 4000)
//     --no-silkscreen    drop reference designators
//     --no-components    copper and pads only
//     --theme <name>     grey (default) | black

import fs from "node:fs";

const arg = (n, d) => {
  const i = process.argv.indexOf(n);
  return i === -1 ? d : process.argv[i + 1];
};
const has = (n) => process.argv.includes(n);

const CIRCUIT = arg("--circuit", "dist/index/circuit.json");
const GLB = arg("--glb", "dist/3d/board.glb");
const OUT = arg("--out", "dist/3d/top-view.svg");
const PX = +arg("--px", 4000);

// ---- palette -------------------------------------------------------------
// Monochrome by intent: the board is grey, copper is the SAME grey family a
// couple of steps lighter, so traces read as texture rather than as a second
// colour. Pads step up further because they are what you actually inspect.
const THEMES = {
  grey: {
    bg: "#15171a",
    substrate: "#2b2e33",
    substrateEdge: "#1b1e22",
    traceTop: "#3f454e",
    traceBottom: "#24272c", // under the board, barely there
    pour: "#31353b",
    pad: "#b9c0c8",
    padEdge: "#8a9099",
    hole: "#101214",
    via: "#4c525a",
    silk: "#dfe3e8",
    bodyLo: "#4a505842",
    bodySide: "#464c54",
    bodyTop: "#6c747e",
    bodyEdge: "#2f343a",
  },
  black: {
    bg: "#000000",
    substrate: "#121417",
    substrateEdge: "#0a0b0d",
    traceTop: "#262b31",
    traceBottom: "#15181b",
    pour: "#191c20",
    pad: "#aab2bb",
    padEdge: "#767d85",
    hole: "#000000",
    via: "#333940",
    silk: "#d6dade",
    bodySide: "#2b3037",
    bodyTop: "#4d545c",
    bodyEdge: "#1a1d21",
  },
};
const C = THEMES[arg("--theme", "grey")] || THEMES.grey;

const cj = JSON.parse(fs.readFileSync(CIRCUIT, "utf8"));
const of = (t) => cj.filter((e) => e.type === t);

// ---- view box ------------------------------------------------------------
const board = of("pcb_board")[0];
const outline = board.outline || [];
const pad = 1.5;
const xs = outline.map((p) => p.x), ys = outline.map((p) => p.y);
const minX = Math.min(...xs) - pad, maxX = Math.max(...xs) + pad;
const minY = Math.min(...ys) - pad, maxY = Math.max(...ys) + pad;
const W = maxX - minX, H = maxY - minY;

// PCB y is up, SVG y is down.
const fx = (x) => +(x - minX).toFixed(4);
const fy = (y) => +(maxY - y).toFixed(4);

const out = [];
const px = (n) => +n.toFixed(4);

out.push(
  `<svg xmlns="http://www.w3.org/2000/svg" width="${PX}" height="${Math.round((PX * H) / W)}" viewBox="0 0 ${px(W)} ${px(H)}" shape-rendering="geometricPrecision">`,
);
out.push(`<rect width="${px(W)}" height="${px(H)}" fill="${C.bg}"/>`);

// ---- board substrate -----------------------------------------------------
const outlinePath =
  "M " + outline.map((p) => `${fx(p.x)} ${fy(p.y)}`).join(" L ") + " Z";
const cut = of("pcb_cutout")[0];
let substrate = outlinePath;
if (cut && cut.shape === "rect") {
  const hw = cut.width / 2, hh = cut.height / 2, cx = cut.center.x, cy = cut.center.y;
  substrate +=
    ` M ${fx(cx - hw)} ${fy(cy - hh)} L ${fx(cx + hw)} ${fy(cy - hh)}` +
    ` L ${fx(cx + hw)} ${fy(cy + hh)} L ${fx(cx - hw)} ${fy(cy + hh)} Z`;
}
out.push(`<g id="substrate">`);
out.push(`<path d="${substrate}" fill="${C.substrate}" fill-rule="evenodd" stroke="${C.substrateEdge}" stroke-width="0.12"/>`);
out.push(`</g>`);

// clip everything else to the board so nothing bleeds past the rim
out.push(`<defs><clipPath id="brd"><path d="${substrate}" clip-rule="evenodd"/></clipPath></defs>`);
out.push(`<g clip-path="url(#brd)">`);

// ---- copper pours (inner + bottom; none on top in this design) ------------
const pours = of("pcb_copper_pour").filter((p) => p.layer === "bottom");
if (pours.length) {
  out.push(`<g id="pour" opacity="0.5">`);
  for (const p of pours) {
    const r = p.brep_shape?.outer_ring?.vertices;
    if (!r) continue;
    out.push(`<path d="M ${r.map((v) => `${fx(v.x)} ${fy(v.y)}`).join(" L ")} Z" fill="${C.pour}"/>`);
  }
  out.push(`</g>`);
}

// ---- traces --------------------------------------------------------------
// Split each trace at layer changes so a via-hop does not draw a phantom
// segment across the board in the wrong shade.
function traceGroups(layer, color, opacity) {
  const paths = [];
  for (const t of of("pcb_trace")) {
    let run = [];
    for (const r of t.route || []) {
      if (r.route_type === "via" || r.layer !== layer) {
        if (run.length > 1) paths.push(run);
        run = [];
        continue;
      }
      run.push(r);
    }
    if (run.length > 1) paths.push(run);
  }
  if (!paths.length) return;
  out.push(`<g id="trace-${layer}" fill="none" stroke="${color}" stroke-linecap="round" stroke-linejoin="round" opacity="${opacity}">`);
  for (const run of paths) {
    const w = run[0].width || 0.15;
    out.push(`<path d="M ${run.map((p) => `${fx(p.x)} ${fy(p.y)}`).join(" L ")}" stroke-width="${px(w)}"/>`);
  }
  out.push(`</g>`);
}
traceGroups("bottom", C.traceBottom, 0.85);
traceGroups("top", C.traceTop, 1);

// ---- vias ----------------------------------------------------------------
out.push(`<g id="vias">`);
for (const v of of("pcb_via")) {
  out.push(`<circle cx="${fx(v.x)}" cy="${fy(v.y)}" r="${px(v.outer_diameter / 2)}" fill="${C.via}"/>`);
  out.push(`<circle cx="${fx(v.x)}" cy="${fy(v.y)}" r="${px(v.hole_diameter / 2)}" fill="${C.hole}"/>`);
}
out.push(`</g>`);

// ---- SMD pads ------------------------------------------------------------
out.push(`<g id="pads" fill="${C.pad}" stroke="${C.padEdge}" stroke-width="0.02">`);
for (const p of of("pcb_smtpad")) {
  if (p.layer !== "top") continue;
  const rot = p.ccw_rotation || 0;
  const w = p.width, h = p.height;
  const rx = p.shape.includes("pill") ? Math.min(w, h) / 2 : 0.02;
  const tf = rot ? ` transform="rotate(${-rot} ${fx(p.x)} ${fy(p.y)})"` : "";
  out.push(
    `<rect x="${px(fx(p.x) - w / 2)}" y="${px(fy(p.y) - h / 2)}" width="${px(w)}" height="${px(h)}" rx="${px(rx)}"${tf}/>`,
  );
}
out.push(`</g>`);

// ---- plated holes --------------------------------------------------------
out.push(`<g id="plated-holes">`);
for (const h of of("pcb_plated_hole")) {
  const w = h.rect_pad_width ?? h.outer_diameter ?? 1.5;
  const hh = h.rect_pad_height ?? h.outer_diameter ?? 1.5;
  if (h.shape && h.shape.includes("rect_pad"))
    out.push(`<rect x="${px(fx(h.x) - w / 2)}" y="${px(fy(h.y) - hh / 2)}" width="${px(w)}" height="${px(hh)}" fill="${C.pad}"/>`);
  else out.push(`<circle cx="${fx(h.x)}" cy="${fy(h.y)}" r="${px(w / 2)}" fill="${C.pad}"/>`);
  out.push(`<circle cx="${fx(h.x)}" cy="${fy(h.y)}" r="${px(h.hole_diameter / 2)}" fill="${C.hole}"/>`);
}
out.push(`</g>`);

// ---- component bodies, projected from the GLB ----------------------------
function hull(pts) {
  if (pts.length < 3) return pts;
  const p = [...pts].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const half = (src) => {
    const h = [];
    for (const q of src) {
      while (h.length >= 2 && cross(h[h.length - 2], h[h.length - 1], q) <= 0) h.pop();
      h.push(q);
    }
    h.pop();
    return h;
  };
  return [...half(p), ...half(p.reverse())];
}

let bodies = 0;
if (!has("--no-components") && fs.existsSync(GLB)) {
  const buf = fs.readFileSync(GLB);
  const g = JSON.parse(buf.slice(20, 20 + buf.readUInt32LE(12)).toString("utf8"));
  let off = 20 + buf.readUInt32LE(12);
  off += (4 - (off % 4)) % 4;
  const bin = buf.slice(off + 8, off + 8 + buf.readUInt32LE(off));
  const readAcc = (i) => {
    const a = g.accessors[i], v = g.bufferViews[a.bufferView];
    const width = { 5126: 4, 5125: 4, 5123: 2, 5121: 1 }[a.componentType];
    const n = a.count * { SCALAR: 1, VEC3: 3, VEC2: 2, VEC4: 4 }[a.type];
    const src = bin.subarray((v.byteOffset || 0) + (a.byteOffset || 0), (v.byteOffset || 0) + (a.byteOffset || 0) + n * width);
    const ab = new ArrayBuffer(src.length);
    new Uint8Array(ab).set(src);
    return a.componentType === 5126 ? new Float32Array(ab) : a.componentType === 5125 ? new Uint32Array(ab) : new Uint16Array(ab);
  };

  const parts = [];
  for (const n of g.nodes || []) {
    if (n.mesh === undefined || n.name === "Box0") continue;
    const t = n.translation || [0, 0, 0];
    const all = [], top = [];
    let zmax = -1e9;
    const verts = [];
    for (const prim of g.meshes[n.mesh].primitives) {
      const pos = readAcc(prim.attributes.POSITION);
      for (let i = 0; i < pos.length; i += 3) {
        // glTF is Y-up, and the in-plane mapping is NOT the obvious one.
        // Verified against circuit.json: U_MCU is glTF [21, 0.7, 2] and
        // pcb (-21, 2), so pcbX = -x, pcbY = z, height = y. Using (x, -z)
        // rotates every body 180 degrees about the board centre, which looks
        // plausible on a roughly symmetric board -- it just puts U_REG's body
        // on the MCU and the MCU's on the regulator.
        const X = -(pos[i] + t[0]), Zh = pos[i + 1] + t[1], Y = pos[i + 2] + t[2];
        verts.push([X, Y, Zh]);
        if (Zh > zmax) zmax = Zh;
      }
    }
    for (const v of verts) {
      all.push([v[0], v[1]]);
      if (v[2] > zmax - 0.06) top.push([v[0], v[1]]);
    }
    if (all.length < 3) continue;
    parts.push({ name: n.name, zmax, side: hull(all), top: hull(top) });
  }
  // Painter's order: shortest first, so a tall part overlaps a short neighbour
  // the way it would from above.
  parts.sort((a, b) => a.zmax - b.zmax);
  out.push(`<g id="components">`);
  for (const p of parts) {
    const d = (h) => `M ${h.map((q) => `${fx(q[0])} ${fy(q[1])}`).join(" L ")} Z`;
    out.push(`<path d="${d(p.side)}" fill="${C.bodySide}" stroke="${C.bodyEdge}" stroke-width="0.05"/>`);
    if (p.top.length >= 3)
      out.push(`<path d="${d(p.top)}" fill="${C.bodyTop}" stroke="${C.bodyEdge}" stroke-width="0.03"/>`);
    bodies++;
  }
  out.push(`</g>`);
}

// ---- silkscreen ----------------------------------------------------------
if (!has("--no-silkscreen")) {
  out.push(`<g id="silkscreen" stroke="${C.silk}" fill="none" stroke-linecap="round" opacity="0.75">`);
  for (const s of of("pcb_silkscreen_path")) {
    if (s.layer !== "top" || !s.route?.length) continue;
    out.push(`<path d="M ${s.route.map((p) => `${fx(p.x)} ${fy(p.y)}`).join(" L ")}" stroke-width="${px(s.stroke_width || 0.1)}"/>`);
  }
  out.push(`</g>`);
  out.push(`<g id="silkscreen-text" fill="${C.silk}" opacity="0.9" font-family="DejaVu Sans Mono, Consolas, monospace">`);
  for (const s of of("pcb_silkscreen_text")) {
    if (s.layer !== "top") continue;
    const a = s.anchor_position, r = s.ccw_rotation || 0;
    const tf = r ? ` transform="rotate(${-r} ${fx(a.x)} ${fy(a.y)})"` : "";
    const t = String(s.text).replace(/&/g, "&amp;").replace(/</g, "&lt;");
    out.push(
      `<text x="${fx(a.x)}" y="${fy(a.y)}" font-size="${px(s.font_size || 1)}" text-anchor="middle" dominant-baseline="central"${tf}>${t}</text>`,
    );
  }
  out.push(`</g>`);
}

out.push(`</g></svg>`);
fs.writeFileSync(OUT, out.join("\n"));

console.log(`wrote ${OUT}`);
console.log(`  board      ${W.toFixed(1)} x ${H.toFixed(1)} mm  ->  ${PX} x ${Math.round((PX * H) / W)} px`);
console.log(`  traces     ${of("pcb_trace").length}   pads ${of("pcb_smtpad").length}   vias ${of("pcb_via").length}`);
console.log(`  bodies     ${bodies}`);
console.log(`  size       ${(fs.statSync(OUT).size / 1e6).toFixed(2)} MB`);
