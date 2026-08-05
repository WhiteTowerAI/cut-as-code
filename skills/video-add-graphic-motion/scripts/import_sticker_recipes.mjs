import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { convertRecipe } from "./convert_motion_anything_recipes.mjs";
import {
  CANVAS_CONFETTI_RECIPES,
  METEOCONS_ICONS,
  MOJS_RECIPES,
  STICKER_COUNTS,
  STICKER_TOTAL,
  TSPARTICLES_RECIPES,
} from "./sticker_recipe_catalog.mjs";

const SOURCE_SPECS = Object.freeze({
  "canvas-confetti": {
    display_name: "canvas-confetti",
    website: "https://catdad.github.io/canvas-confetti/",
    repository: "https://github.com/catdad/canvas-confetti",
    revision: "20eebad51dde793070c373d594099a7ed8d96e22",
    branch: "master",
    package_name: "canvas-confetti",
    package_version: "1.9.4",
    package_file: "canvas-confetti-1.9.4.tgz",
    license: "ISC",
    author: "Kiril Vatev",
  },
  mojs: {
    display_name: "mo.js",
    website: "https://mojs.github.io/tutorials/",
    repository: "https://github.com/mojs/mojs",
    revision: "0a9cf9a87dd5637e6fa770755e79048489bcf817",
    branch: "main",
    package_name: "@mojs/core",
    package_version: "1.7.1",
    package_file: "mojs-core-1.7.1.tgz",
    license: "MIT",
    author: "Oleg Solomka and mo.js contributors",
  },
  "line-md": {
    display_name: "Line MD",
    website: "https://icon-sets.iconify.design/line-md/",
    repository: "https://github.com/cyberalien/line-md",
    revision: "2ed22555cee9c1e50d4269865681d01ee8cffd7c",
    branch: "main",
    package_name: "line-md",
    package_version: "3.0.5",
    license: "MIT",
    author: "Vjacheslav Trushkin",
  },
  meteocons: {
    display_name: "Meteocons",
    website: "https://meteocons.com/",
    repository: "https://github.com/basmilius/weather-icons",
    revision: "70dfb1d6e30dc9e791cfb0e4c5b5e5e60e972aa0",
    branch: "main",
    package_name: "@meteocons/svg",
    package_version: "0.1.0",
    package_file: "meteocons-svg-0.1.0.tgz",
    license: "MIT",
    author: "Bas Milius",
  },
  tsparticles: {
    display_name: "tsParticles",
    website: "https://particles.js.org/",
    repository: "https://github.com/tsparticles/tsparticles",
    revision: "d38e87725cb0fa7108481b39064e067203068bac",
    branch: "main",
    package_name: "tsparticles",
    package_version: "4.3.2",
    package_file: "tsparticles-4.3.2.tgz",
    license: "MIT",
    author: "Matteo Bruni",
  },
});

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function titleCase(value) {
  return value.split("-").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

function inlineList(values) {
  return `[${values.map((value) => JSON.stringify(value)).join(", ")}]`;
}

function manifestSourceUrl(sourceId, assetPath = "") {
  const source = SOURCE_SPECS[sourceId];
  if (sourceId === "meteocons") {
    return `https://www.npmjs.com/package/@meteocons/svg/v/${source.package_version}`;
  }
  const suffix = assetPath ? `/${assetPath.replaceAll("\\", "/")}` : "";
  return `${source.repository}/blob/${source.revision}${suffix}`;
}

function recipeManifest({
  sourceId,
  id,
  name,
  description,
  category,
  runtime,
  tags,
  bestFor,
  avoidWhen,
  implementationFiles,
  upstreamAsset,
  durationMs = 6000,
}) {
  const source = SOURCE_SPECS[sourceId];
  return `spec_version: 1
id: ${id}
name: ${JSON.stringify(name)}
description: ${JSON.stringify(description)}
surfaces: [video]
category: ${category}
tech: ${runtime.includes("svg-smil") ? "[svg]" : "[js]"}
canvas: [video]
target: [overlay]
intent: ${category}
runtime: ${inlineList(runtime)}
export: [skill, html]
dependencies: []
tags: ${inlineList(tags)}
intent_keywords:
${tags.map((tag) => `  - ${JSON.stringify(tag)}`).join("\n")}
best_for:
${bestFor.map((item) => `  - ${JSON.stringify(item)}`).join("\n")}
avoid_when:
${avoidWhen.map((item) => `  - ${JSON.stringify(item)}`).join("\n")}
restraint:
  max_per_view: 1
  notes: "Use as one selective semantic sticker; keep the full animated path outside visible faces."
motion:
  duration_ms: ${durationMs}
  easing: linear
  reduced_motion: freeze
  gpu_safe: true
entry: preview.html
implementations:
  - tech: ${runtime.includes("svg-smil") ? "svg-smil" : "js"}
    files: ${inlineList(implementationFiles)}
    usage: "Materialize the converted HyperFrames directory, then adapt placement, scale, palette, and timing to the shot."
license:
  spdx: ${source.license}
  upstream: ${JSON.stringify(manifestSourceUrl(sourceId, upstreamAsset))}
  attribution_required: true
author:
  name: ${JSON.stringify(source.author)}
  url: ${JSON.stringify(source.repository)}
version: ${source.package_version}
`;
}

function recipeSkill({ id, name, sourceId }) {
  return `---
name: ${id}
description: Adapt the bundled ${name} sticker from ${SOURCE_SPECS[sourceId].display_name} as a selective HyperFrames overlay.
---

# ${name}

Use the preconverted \`hyperframes/\` composition as the immutable base. Preserve the recognizable
source motion, keep every animated pixel outside visible faces, and remove any element that does not
carry the cue's meaning.
`;
}

function canvasPreview() {
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:transparent}
#sticker-canvas{display:block;width:1920px;height:1080px;background:transparent}
</style></head><body>
<canvas id="sticker-canvas" class="clip" data-start="0" data-duration="6" data-track-index="1" width="1920" height="1080"></canvas>
<script src="vendor.js"></script><script src="effect.js"></script>
</body></html>
`;
}

function canvasBursts(entry) {
  const base = { colors: entry.colors, disableForReducedMotion: false, ticks: 180, zIndex: 0 };
  const at = (delay, options) => ({ delay, options: { ...base, ...options } });
  switch (entry.pattern) {
    case "side-cannons":
      return [
        at(0, { particleCount: 90, angle: 55, spread: 55, startVelocity: 65, origin: { x: 0, y: 0.82 } }),
        at(0, { particleCount: 90, angle: 125, spread: 55, startVelocity: 65, origin: { x: 1, y: 0.82 } }),
      ];
    case "top-rain":
      return Array.from({ length: 8 }, (_, index) => at(index * 180, {
        particleCount: 24, angle: 270, spread: 70, startVelocity: 18, gravity: 1.15,
        origin: { x: 0.08 + index * 0.12, y: 0.02 }, scalar: 0.9,
      }));
    case "bottom-fountain":
      return Array.from({ length: 7 }, (_, index) => at(index * 150, {
        particleCount: 28, angle: 90, spread: 34 + index * 3, startVelocity: 62,
        gravity: 1.25, origin: { x: 0.5, y: 1 }, scalar: 0.9,
      }));
    case "left-stream":
      return [at(0, { particleCount: 150, angle: 18, spread: 38, startVelocity: 58, origin: { x: 0, y: 0.65 } })];
    case "right-stream":
      return [at(0, { particleCount: 150, angle: 162, spread: 38, startVelocity: 58, origin: { x: 1, y: 0.65 } })];
    case "firework-pair":
      return [
        at(250, { particleCount: 100, spread: 360, startVelocity: 48, gravity: 0.65, origin: { x: 0.34, y: 0.38 } }),
        at(750, { particleCount: 100, spread: 360, startVelocity: 48, gravity: 0.65, origin: { x: 0.68, y: 0.3 } }),
      ];
    case "firework-triple":
      return [[0.25, 0.42], [0.5, 0.26], [0.76, 0.42]].map((origin, index) => at(index * 360, {
        particleCount: 85, spread: 360, startVelocity: 44, gravity: 0.7, origin: { x: origin[0], y: origin[1] },
      }));
    case "snowfall":
      return Array.from({ length: 10 }, (_, index) => at(index * 170, {
        particleCount: 18, angle: 270, spread: 180, startVelocity: 9, gravity: 0.42,
        drift: index % 2 ? 0.8 : -0.8, origin: { x: 0.1 + (index % 9) * 0.1, y: 0 },
        scalar: 0.65, shapes: ["circle"], ticks: 340,
      }));
    case "school-pride":
      return Array.from({ length: 6 }, (_, index) => at(index * 220, {
        particleCount: 40, angle: index % 2 ? 130 : 50, spread: 45, startVelocity: 52,
        origin: { x: index % 2 ? 1 : 0, y: 0.72 - index * 0.035 },
      }));
    case "realistic":
      return [
        at(0, { particleCount: 80, spread: 28, startVelocity: 55, scalar: 1.2, origin: { x: 0.5, y: 0.64 } }),
        at(60, { particleCount: 70, spread: 90, startVelocity: 42, scalar: 0.85, origin: { x: 0.5, y: 0.64 } }),
        at(120, { particleCount: 40, spread: 120, startVelocity: 30, scalar: 1.45, origin: { x: 0.5, y: 0.64 } }),
      ];
    case "mini-pop":
      return [at(0, { particleCount: 42, spread: 55, startVelocity: 36, scalar: 0.72, origin: { x: 0.5, y: 0.55 } })];
    case "mega-pop":
      return [at(0, { particleCount: 260, spread: 125, startVelocity: 68, scalar: 1.25, origin: { x: 0.5, y: 0.62 } })];
    case "slow-fall":
      return [at(0, { particleCount: 170, spread: 120, startVelocity: 32, gravity: 0.45, ticks: 360, origin: { x: 0.5, y: 0.28 } })];
    case "fast-cannon":
      return [at(0, { particleCount: 125, angle: 70, spread: 22, startVelocity: 92, gravity: 1.3, origin: { x: 0.08, y: 0.88 } })];
    case "diagonal-cross":
      return [
        at(0, { particleCount: 110, angle: 32, spread: 28, startVelocity: 72, origin: { x: 0, y: 0.92 } }),
        at(0, { particleCount: 110, angle: 148, spread: 28, startVelocity: 72, origin: { x: 1, y: 0.92 } }),
      ];
    case "celebration-wave":
      return Array.from({ length: 9 }, (_, index) => at(index * 125, {
        particleCount: 28, spread: 45, startVelocity: 48,
        origin: { x: 0.1 + index * 0.1, y: 0.72 - Math.sin(index / 2) * 0.12 },
      }));
    case "starfield":
      return Array.from({ length: 12 }, (_, index) => at(index * 120, {
        particleCount: 12, angle: 270, spread: 55, startVelocity: 14, gravity: 0.5,
        ticks: 300, scalar: 0.9 + (index % 3) * 0.2, origin: { x: 0.05 + index * 0.08, y: 0.02 },
      }));
    default:
      return [at(0, { particleCount: 150, spread: 90, startVelocity: 58, origin: { x: 0.5, y: 0.58 } })];
  }
}

function canvasEffect(entry) {
  return `/* Adapted from canvas-confetti ${SOURCE_SPECS["canvas-confetti"].package_version}; see vendor.js and shared license. */
const canvas = document.getElementById("sticker-canvas");
const fire = confetti.create(canvas, { resize: false, useWorker: false });
const customShapes = {
  star: confetti.shapeFromPath({ path: "M10 0L12.35 6.76L19.51 6.91L13.8 11.24L15.88 18.09L10 14L4.12 18.09L6.2 11.24L0.49 6.91L7.65 6.76Z" }),
  heart: confetti.shapeFromPath({ path: "M10 18S1 12.7 1 6.8C1 3.6 4.8 1.8 7.2 4.1L10 6.8L12.8 4.1C15.2 1.8 19 3.6 19 6.8C19 12.7 10 18 10 18Z" }),
};
const bursts = ${JSON.stringify(canvasBursts(entry))};
for (const burst of bursts) {
  setTimeout(() => {
    const options = { ...burst.options };
    ${entry.shape ? `options.shapes = [customShapes[${JSON.stringify(entry.shape)}]];` : ""}
    fire(options);
  }, burst.delay);
}
`;
}

function mojsPreview() {
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:transparent}
#sticker-stage{position:relative;width:1920px;height:1080px;overflow:hidden}
#sticker-stage svg{overflow:visible}
</style></head><body>
<div id="sticker-stage" class="clip" data-start="0" data-duration="6" data-track-index="1"></div>
<script src="vendor.js"></script><script src="effect.js"></script>
</body></html>
`;
}

function mojsEffect(entry) {
  const spec = {
    count: entry.count,
    radius: entry.radius,
    childShape: entry.childShape,
    childRadius: entry.childRadius,
    childPoints: entry.childPoints,
    rings: entry.rings,
    degree: entry.degree ?? 360,
    angle: entry.angle ?? 0,
    positions: entry.positions ?? [[960, 540]],
    colors: entry.colors,
  };
  return `/* Adapted from @mojs/core ${SOURCE_SPECS.mojs.package_version}; see vendor.js and shared license. */
const spec = ${JSON.stringify(spec)};
const parent = document.getElementById("sticker-stage");
spec.positions.forEach(([x, y], positionIndex) => {
  const shiftX = x - 960;
  const shiftY = y - 540;
  setTimeout(() => {
    if (spec.count > 0) {
      new mojs.Burst({
        parent, x: shiftX, y: shiftY, count: spec.count, degree: spec.degree, angle: spec.angle,
        radius: { 0: spec.radius }, duration: 1250,
        children: {
          shape: spec.childShape || "circle", points: spec.childPoints || 5,
          radius: { [spec.childRadius || 10]: 0 }, fill: spec.colors,
          stroke: spec.childShape === "line" ? spec.colors : "none",
          strokeWidth: spec.childShape === "line" ? { 5: 0 } : 0,
          duration: 1150, easing: "quad.out",
        },
      }).play();
    }
    for (let ring = 0; ring < spec.rings; ring += 1) {
      new mojs.Shape({
        parent, x: shiftX, y: shiftY, shape: "circle", fill: "none", stroke: spec.colors[ring % spec.colors.length],
        radius: { 0: spec.radius * (0.58 + ring * 0.13) }, strokeWidth: { [14 - ring * 2]: 0 },
        duration: 900 + ring * 180, delay: ring * 90, easing: "cubic.out",
      }).play();
    }
  }, positionIndex * 220);
});
`;
}

function iconPreview({ svg, viewBox, color = "#ffffff", nativeDuration = 30, size = 440 }) {
  const inlineSvg = svg.replace(
    /<svg\b/i,
    `<svg id="sticker-icon" class="clip" data-start="0" data-duration="6" data-track-index="1" data-native-duration="${nativeDuration}"`,
  ).replace(/viewBox="[^"]+"/i, `viewBox="${viewBox}"`);
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:transparent}
body{display:flex;align-items:center;justify-content:center;color:${color}}
svg{display:block;width:${size}px;height:${size}px;overflow:visible}
</style></head><body>${inlineSvg}</body></html>
`;
}

function lineMdColor(name) {
  if (/alert/.test(name)) return "#ff5a5f";
  if (/confirm|check/.test(name)) return "#2dc653";
  if (/heart/.test(name)) return "#ff4d6d";
  if (/star|coffee/.test(name)) return "#ffd166";
  if (/download|upload|cloud|location|link/.test(name)) return "#4cc9f0";
  if (/play|pause/.test(name)) return "#9b5de5";
  return "#ffffff";
}

function tsParticlesPreview() {
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:transparent}
#sticker-canvas{display:block;width:1920px;height:1080px;background:transparent}
</style></head><body>
<canvas id="sticker-canvas" class="clip" data-start="0" data-duration="6" data-track-index="1" width="1920" height="1080"></canvas>
<script src="effect.js"></script>
</body></html>
`;
}

function tsParticlesEffect(profile) {
  return `/* Deterministic HyperFrames canvas port of the tsParticles ${profile} preset; see upstream-options.ts. */
const canvas = document.getElementById("sticker-canvas");
const ctx = canvas.getContext("2d");
const width = canvas.width;
const height = canvas.height;
const profile = ${JSON.stringify(profile)};
const colors = ["#ff4d6d", "#ffd166", "#06d6a0", "#4cc9f0", "#9b5de5", "#ffffff"];
const particles = Array.from({ length: profile === "links" ? 64 : profile === "fireflies" ? 80 : 150 }, (_, index) => ({
  index,
  x: Math.random() * width,
  y: Math.random() * height,
  vx: (Math.random() - 0.5) * 95,
  vy: (Math.random() - 0.5) * 95,
  speed: 110 + Math.random() * 240,
  angle: Math.random() * Math.PI * 2,
  phase: Math.random() * 4.8,
  life: 1.2 + Math.random() * 2.2,
  radius: 2 + Math.random() * 5,
  color: colors[index % colors.length],
}));

function dot(x, y, radius, color, alpha = 1) {
  ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
}

function renderFireworks(t) {
  const centers = [[420, 390], [960, 260], [1500, 420], [720, 520], [1240, 560]];
  particles.forEach((particle) => {
    const burst = particle.index % centers.length;
    const start = 0.25 + burst * 0.62;
    const age = t - start;
    if (age < 0 || age > particle.life) return;
    const center = centers[burst];
    const x = center[0] + Math.cos(particle.angle) * particle.speed * age;
    const y = center[1] + Math.sin(particle.angle) * particle.speed * age + 58 * age * age;
    dot(x, y, particle.radius, particle.color, 1 - age / particle.life);
  });
}

function renderFountain(t) {
  particles.forEach((particle) => {
    const age = (t + particle.phase) % particle.life;
    const x = width / 2 + particle.vx * age + Math.sin(particle.phase * 4) * 55;
    const y = height - 25 - particle.speed * age + 170 * age * age;
    dot(x, y, particle.radius, particle.color, 1 - age / particle.life);
  });
}

function renderFireflies(t) {
  particles.forEach((particle) => {
    const x = (particle.x + Math.sin(t * 0.8 + particle.phase) * 110 + width) % width;
    const y = (particle.y + Math.cos(t * 0.65 + particle.phase) * 75 + height) % height;
    const pulse = 0.25 + 0.75 * Math.abs(Math.sin(t * 1.8 + particle.phase));
    dot(x, y, particle.radius * 2.8, particle.color, pulse * 0.14);
    dot(x, y, particle.radius, particle.color, pulse);
  });
}

function renderLinks(t) {
  const points = particles.map((particle) => ({
    x: (particle.x + Math.sin(t * 0.34 + particle.phase) * 125 + width) % width,
    y: (particle.y + Math.cos(t * 0.29 + particle.phase) * 90 + height) % height,
    particle,
  }));
  ctx.lineWidth = 1.5;
  for (let i = 0; i < points.length; i += 1) {
    for (let j = i + 1; j < points.length; j += 1) {
      const dx = points[i].x - points[j].x;
      const dy = points[i].y - points[j].y;
      const distance = Math.hypot(dx, dy);
      if (distance > 180) continue;
      ctx.globalAlpha = (1 - distance / 180) * 0.45;
      ctx.strokeStyle = "#4cc9f0";
      ctx.beginPath();
      ctx.moveTo(points[i].x, points[i].y);
      ctx.lineTo(points[j].x, points[j].y);
      ctx.stroke();
    }
  }
  points.forEach(({ x, y, particle }) => dot(x, y, particle.radius, particle.color, 0.9));
}

function frame(milliseconds) {
  const t = milliseconds / 1000;
  ctx.clearRect(0, 0, width, height);
  if (profile === "fireworks") renderFireworks(t);
  else if (profile === "fountain") renderFountain(t);
  else if (profile === "fireflies") renderFireflies(t);
  else renderLinks(t);
  ctx.globalAlpha = 1;
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
`;
}

async function readRevision(repositoryDir, branch) {
  const direct = path.join(repositoryDir, ".git", "refs", "heads", branch);
  try {
    return (await readFile(direct, "utf8")).trim();
  } catch {
    const packed = await readFile(path.join(repositoryDir, ".git", "packed-refs"), "utf8");
    return packed.split(/\r?\n/).find((line) => line.endsWith(` refs/heads/${branch}`))?.split(" ")[0] || "";
  }
}

async function writeGroupProvenance({ groupDir, sourceId, licenseSource, packageCache, sourceCache }) {
  const source = SOURCE_SPECS[sourceId];
  await rm(groupDir, { recursive: true, force: true });
  await mkdir(groupDir, { recursive: true });
  await cp(licenseSource, path.join(groupDir, `LICENSE.${sourceId}`));
  const packagePath = source.package_file ? path.join(packageCache, source.package_file) : null;
  const sourceData = {
    schema_version: 1,
    source_id: sourceId,
    display_name: source.display_name,
    website: source.website,
    repository: source.repository,
    revision: source.revision,
    package: source.package_name ? {
      name: source.package_name,
      version: source.package_version,
      tarball_file: source.package_file || null,
      tarball_sha256: packagePath ? sha256(await readFile(packagePath)) : null,
    } : null,
    license: { spdx: source.license, file: `LICENSE.${sourceId}` },
    selection_count: STICKER_COUNTS[sourceId],
    conversion: sourceId === "tsparticles"
      ? "Official preset configuration preserved with a deterministic HyperFrames canvas port."
      : "Original implementation or SVG preserved and wrapped for deterministic HyperFrames seeking.",
  };
  await writeFile(path.join(groupDir, "SOURCE.json"), `${JSON.stringify(sourceData, null, 2)}\n`, "utf8");

  const revision = await readRevision(path.join(sourceCache, sourceId), source.branch);
  if (revision !== source.revision) {
    throw new Error(`${sourceId}: expected revision ${source.revision}, got ${revision || "missing"}`);
  }
}

async function writeRecipe({ groupDir, sourceId, id, name, manifest, files, upstreamAsset }) {
  const recipeDir = path.join(groupDir, id);
  await rm(recipeDir, { recursive: true, force: true });
  await mkdir(recipeDir, { recursive: true });
  await writeFile(path.join(recipeDir, "recipe.motion.yaml"), manifest, "utf8");
  await writeFile(path.join(recipeDir, "SKILL.md"), recipeSkill({ id, name, sourceId }), "utf8");
  for (const [relativePath, contents] of Object.entries(files)) {
    const target = path.join(recipeDir, relativePath);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, contents);
  }
  const receipt = {
    schema_version: 1,
    recipe_id: id,
    source_id: sourceId,
    upstream_asset: upstreamAsset,
    source_files: Object.fromEntries(
      Object.entries(files).map(([relativePath, contents]) => [relativePath, sha256(contents)]),
    ),
  };
  await writeFile(path.join(recipeDir, "source-receipt.json"), `${JSON.stringify(receipt, null, 2)}\n`, "utf8");
  await convertRecipe({ recipesRoot: path.dirname(groupDir), recipeDir });
  return recipeDir;
}

async function generateCanvasConfetti({ recipesRoot, sourceCache, packageCache }) {
  const sourceId = "canvas-confetti";
  const groupDir = path.join(recipesRoot, sourceId);
  const packageRoot = path.join(packageCache, sourceId, "package");
  const vendor = await readFile(path.join(packageRoot, "dist", "confetti.browser.js"));
  await writeGroupProvenance({
    groupDir, sourceId, sourceCache, packageCache,
    licenseSource: path.join(packageRoot, "LICENSE"),
  });
  for (const entry of CANVAS_CONFETTI_RECIPES) {
    const effect = canvasEffect(entry);
    await writeRecipe({
      groupDir, sourceId, id: entry.id, name: entry.name,
      upstreamAsset: "dist/confetti.browser.js",
      manifest: recipeManifest({
        sourceId, id: entry.id, name: entry.name,
        description: `${entry.name} rendered with the original canvas-confetti engine.`,
        category: "sticker-celebration", runtime: ["js"],
        tags: ["sticker", "confetti", "celebration", entry.pattern],
        bestFor: ["Wins, launches, reveals, milestones, and celebratory transitions"],
        avoidWhen: ["The cue is neutral, serious, or already visually dense", "Any particle path would cross a visible face"],
        implementationFiles: ["vendor.js", "effect.js"], upstreamAsset: "dist/confetti.browser.js",
      }),
      files: { "preview.html": canvasPreview(), "vendor.js": vendor, "effect.js": effect },
    });
  }
}

async function generateMojs({ recipesRoot, sourceCache, packageCache }) {
  const sourceId = "mojs";
  const groupDir = path.join(recipesRoot, sourceId);
  const packageRoot = path.join(packageCache, sourceId, "package");
  const vendor = await readFile(path.join(packageRoot, "dist", "mo.umd.js"));
  await writeGroupProvenance({
    groupDir, sourceId, sourceCache, packageCache,
    licenseSource: path.join(packageRoot, "LICENSE.md"),
  });
  for (const entry of MOJS_RECIPES) {
    await writeRecipe({
      groupDir, sourceId, id: entry.id, name: entry.name,
      upstreamAsset: "dist/mo.umd.js",
      manifest: recipeManifest({
        sourceId, id: entry.id, name: entry.name,
        description: `${entry.name} built from mo.js Burst and Shape primitives.`,
        category: "sticker-impact", runtime: ["js"],
        tags: ["sticker", "mojs", "burst", entry.childShape || "ring"],
        bestFor: ["Impact beats, confirmations, emphasis hits, and compact celebration cues"],
        avoidWhen: ["The cue needs literal information rather than an abstract impact", "Any ring or particle path would cross a visible face"],
        implementationFiles: ["vendor.js", "effect.js"], upstreamAsset: "dist/mo.umd.js",
      }),
      files: { "preview.html": mojsPreview(), "vendor.js": vendor, "effect.js": mojsEffect(entry) },
    });
  }
}

async function readLineMdEntries(sourceCache) {
  const repositoryRoot = path.join(sourceCache, "line-md");
  const data = JSON.parse(await readFile(path.join(repositoryRoot, "line-md.json"), "utf8"));
  const icons = Object.entries(data.icons || {});
  const aliases = Object.entries(data.aliases || {});
  if (icons.length !== 1218 || aliases.length !== 4) {
    throw new Error(`line-md: expected 1218 icons and 4 aliases, got ${icons.length} and ${aliases.length}`);
  }

  const entries = icons.map(([name, icon]) => ({ name, icon, alias: null }));
  for (const [name, alias] of aliases) {
    if (alias.rotate || alias.hFlip || alias.vFlip) {
      throw new Error(`line-md: unsupported transformed alias ${name}`);
    }
    const icon = data.icons[alias.parent];
    if (!icon) throw new Error(`line-md: alias ${name} has missing parent ${alias.parent}`);
    entries.push({ name, icon, alias });
  }
  if (new Set(entries.map((entry) => entry.name)).size !== 1222) {
    throw new Error("line-md: icon and alias names must be unique");
  }
  return { data, entries };
}

async function generateLineMd({ recipesRoot, sourceCache, packageCache, lineMd }) {
  const sourceId = "line-md";
  const groupDir = path.join(recipesRoot, sourceId);
  const repositoryRoot = path.join(sourceCache, sourceId);
  const { data, entries } = lineMd;
  await writeGroupProvenance({
    groupDir, sourceId, sourceCache, packageCache,
    licenseSource: path.join(repositoryRoot, "license.txt"),
  });
  for (const { name: iconName, icon, alias } of entries) {
    if (!icon?.body) throw new Error(`line-md: missing icon body ${iconName}`);
    const id = `line-md-${iconName}`;
    const name = `Line MD ${titleCase(iconName)}`;
    const sourceIcon = `${JSON.stringify({
      prefix: data.prefix,
      name: iconName,
      ...(alias ? { alias, parent: { name: alias.parent, ...icon } } : icon),
    }, null, 2)}\n`;
    const svg = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">${icon.body}</svg>`;
    await writeRecipe({
      groupDir, sourceId, id, name,
      upstreamAsset: "line-md.json",
      manifest: recipeManifest({
        sourceId, id, name,
        description: alias
          ? `Animated ${titleCase(iconName)} alias of ${titleCase(alias.parent)} from Line MD.`
          : `Animated ${titleCase(iconName)} semantic sticker from the original Line MD SVG body.`,
        category: "sticker-semantic-icon", runtime: ["svg-smil"],
        tags: ["sticker", "line-md", ...iconName.split("-")],
        bestFor: ["Literal status, action, notification, or object cues where the icon meaning is immediately clear"],
        avoidWhen: ["The icon meaning is ambiguous in the transcript context", "The animated icon cannot remain fully outside visible faces"],
        implementationFiles: ["icon.svg", "upstream-icon.json"], upstreamAsset: "line-md.json",
      }),
      files: {
        "preview.html": iconPreview({ svg, viewBox: "0 0 24 24", color: lineMdColor(iconName) }),
        "icon.svg": svg,
        "upstream-icon.json": sourceIcon,
      },
    });
  }
}

async function generateMeteocons({ recipesRoot, sourceCache, packageCache }) {
  const sourceId = "meteocons";
  const groupDir = path.join(recipesRoot, sourceId);
  const packageRoot = path.join(packageCache, sourceId, "package");
  await writeGroupProvenance({
    groupDir, sourceId, sourceCache, packageCache,
    licenseSource: path.join(sourceCache, sourceId, "LICENSE"),
  });
  for (const iconName of METEOCONS_ICONS) {
    const assetPath = path.join("fill", `${iconName}.svg`);
    const svg = await readFile(path.join(packageRoot, assetPath), "utf8");
    const id = `meteocons-${iconName}`;
    const name = `Meteocons ${titleCase(iconName)}`;
    await writeRecipe({
      groupDir, sourceId, id, name, upstreamAsset: assetPath.replaceAll("\\", "/"),
      manifest: recipeManifest({
        sourceId, id, name,
        description: `Animated ${titleCase(iconName)} weather sticker from the original Meteocons fill SVG.`,
        category: "sticker-weather", runtime: ["svg-smil"],
        tags: ["sticker", "weather", "meteocons", ...iconName.split("-")],
        bestFor: ["Literal weather, climate, forecast, or environmental references"],
        avoidWhen: ["Weather is only metaphorical or unrelated to the spoken meaning", "The icon cannot remain fully outside visible faces"],
        implementationFiles: ["icon.svg"], upstreamAsset: assetPath,
      }),
      files: {
        "preview.html": iconPreview({ svg, viewBox: "0 0 128 128", nativeDuration: 30, size: 500 }),
        "icon.svg": svg,
      },
    });
  }
}

async function generateTsParticles({ recipesRoot, sourceCache, packageCache }) {
  const sourceId = "tsparticles";
  const groupDir = path.join(recipesRoot, sourceId);
  const repositoryRoot = path.join(sourceCache, sourceId);
  await writeGroupProvenance({
    groupDir, sourceId, sourceCache, packageCache,
    licenseSource: path.join(repositoryRoot, "LICENSE"),
  });
  for (const entry of TSPARTICLES_RECIPES) {
    const assetPath = path.join("presets", entry.preset, "src", "options.ts");
    const upstreamOptions = await readFile(path.join(repositoryRoot, assetPath), "utf8");
    await writeRecipe({
      groupDir, sourceId, id: entry.id, name: entry.name,
      upstreamAsset: assetPath.replaceAll("\\", "/"),
      manifest: recipeManifest({
        sourceId, id: entry.id, name: entry.name,
        description: `${entry.name} as a deterministic canvas port of the official tsParticles ${entry.preset} preset.`,
        category: "sticker-complex-particles", runtime: ["js"],
        tags: ["sticker", "tsparticles", "particles", entry.profile],
        bestFor: ["Complex particle fields whose behavior is not covered by the smaller confetti or burst recipes"],
        avoidWhen: ["A simpler canvas-confetti or mo.js recipe communicates the same cue", "The particle field would obscure faces or required footage detail"],
        implementationFiles: ["effect.js", "upstream-options.ts"], upstreamAsset: assetPath,
      }),
      files: {
        "preview.html": tsParticlesPreview(),
        "effect.js": tsParticlesEffect(entry.profile),
        "upstream-options.ts": upstreamOptions,
      },
    });
  }
}

export async function generateStickerRecipes({ recipesRoot, sourceCache, packageCache }) {
  if (STICKER_TOTAL !== 1258) throw new Error(`Sticker catalog must contain 1258 recipes, got ${STICKER_TOTAL}`);
  const lineMd = await readLineMdEntries(sourceCache);
  const ids = [
    ...CANVAS_CONFETTI_RECIPES.map((entry) => entry.id),
    ...MOJS_RECIPES.map((entry) => entry.id),
    ...lineMd.entries.map((entry) => `line-md-${entry.name}`),
    ...METEOCONS_ICONS.map((name) => `meteocons-${name}`),
    ...TSPARTICLES_RECIPES.map((entry) => entry.id),
  ];
  if (new Set(ids).size !== ids.length) throw new Error("Sticker catalog contains duplicate recipe IDs");

  await generateCanvasConfetti({ recipesRoot, sourceCache, packageCache });
  await generateMojs({ recipesRoot, sourceCache, packageCache });
  await generateLineMd({ recipesRoot, sourceCache, packageCache, lineMd });
  await generateMeteocons({ recipesRoot, sourceCache, packageCache });
  await generateTsParticles({ recipesRoot, sourceCache, packageCache });
  return { recipe_count: STICKER_TOTAL, counts: STICKER_COUNTS };
}

async function main() {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const skillRoot = path.resolve(scriptDir, "..");
  const repoRoot = path.resolve(skillRoot, "..", "..");
  const result = await generateStickerRecipes({
    recipesRoot: path.join(skillRoot, "recipes"),
    sourceCache: path.join(repoRoot, "work", "cache", "sticker-sources"),
    packageCache: path.join(repoRoot, "work", "cache", "sticker-packages"),
  });
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  });
}
