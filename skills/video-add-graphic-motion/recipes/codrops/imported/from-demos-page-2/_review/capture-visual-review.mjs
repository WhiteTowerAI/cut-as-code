import fs from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const browser = process.argv[2];
if (!browser) throw new Error("Pass the absolute agent-browser.cmd path");

const wantedTitles = [
  "3D Image Rotations on Scroll",
  "WebGL Scroll Spiral",
  '"Design Samsung" Grid Loading Effect',
  "Thumbnail Grid with Expanding Preview",
  "Grid Item Animation Layout",
  "Preview to Full Content Page Transition",
  "Layer Motion Slideshow",
  "Image To Grid Transition",
  "Alternate Column Scroll Animation",
  "Animated SVG Frame Slideshow",
  "Text Trail Effect",
  "Decorative Letter Animations",
  "Shape Slideshow with Clip-path",
  "Inspiration for Letter Effects",
  "Kinetic Typography Page Transition",
  "On-Scroll Letter Animations",
  "Sketch 008: Image Motion Trail (Circle)",
  "Lines to Content Layout Animation",
  "Hover Motion Intro Animation",
  "Letter Effects and Interaction Ideas",
  "Sketch 005: Image Motion Trail (Opaque)",
  "Image Trail Effects",
  "On-Scroll 3D Carousel",
  "Animating in Frames: Repeating Image Transition",
  "Consecutive Scroll Animations with One Element",
  "Staggered (3D) Grid Animations with Scroll-Triggered Effects",
  "Exploration of On-Scroll Layout Formations",
  "Blurry Text Reveal on Scroll",
  "Some On-Scroll Text Highlight Animations",
  "On-Scroll Expanding Image Animation within Typography",
  "On-Scroll 3D Stack Motion Effect",
  "On-Scroll Animation Ideas for Sticky Sections",
  "On-Scroll Shape Morph Animations",
  "Image Layer Animations with Clip-Path",
  "Ideas for Image Motion Trail Animations",
  "Some Ideas for Fullscreen Image Slideshow Animations",
  "Connected Grid Layout Animation",
  "On-Scroll Column & Row Animations",
  "On-Scroll Perspective Grid Animations",
  "Grid Flow Animation",
  "Scroll-Based Layout Animations",
  "Inspiration for Text Block Transitions",
  "On-Scroll SVG Filter Effect",
  "On-Scroll Pixelated Image Loading Effect",
  "Ideas for Grid to Slideshow Switch Animations",
  "Ideas for Pixel Page Transitions",
  "How to Create a Cover Page Transition",
  "Unreveal Effects for Content Previews",
  "Fullscreen Scrolling Slideshow",
  "Fullscreen Clip Animation",
  "On-Scroll Typography Animations",
  "Shuffling Typography Animation",
  "Sketch 029: Infinite Loop Scrolling (3D Animation)",
  "Smooth Panel Scroll Effects",
  "Large Image to Content Page Transition",
  "3D Perspective Glitch Hover Effect"
];

const all = JSON.parse(await fs.readFile(path.join(here, "CANDIDATES_RAW.json"), "utf8"));
const byTitle = new Map(all.map((item) => [item.title, item]));
const missing = wantedTitles.filter((title) => !byTitle.has(title));
if (missing.length) throw new Error(`Missing candidates: ${missing.join(" | ")}`);

const visualsDir = path.join(here, "visuals");
await fs.mkdir(visualsDir, { recursive: true });
const candidates = wantedTitles.map((title, index) => ({
  review_index: index + 1,
  ...byTitle.get(title),
  initial_screenshot: `visuals/frame-${String(index * 2).padStart(3, "0")}.png`,
  interaction_screenshot: `visuals/frame-${String(index * 2 + 1).padStart(3, "0")}.png`,
}));
await fs.writeFile(path.join(here, "REVIEW_CANDIDATES.json"), `${JSON.stringify(candidates, null, 2)}\n`);

const commands = [["set", "viewport", "1280", "720"]];
for (const candidate of candidates) {
  commands.push(["open", candidate.demo_url]);
  commands.push(["wait", "1800"]);
  commands.push(["screenshot", path.join(here, candidate.initial_screenshot)]);
  commands.push(["mouse", "move", "350", "420"]);
  commands.push(["mouse", "move", "900", "260"]);
  commands.push(["scroll", "down", "650"]);
  commands.push(["wait", "1000"]);
  commands.push(["screenshot", path.join(here, candidate.interaction_screenshot)]);
}

const child = spawn(browser, ["--session", "codrops-visual-review", "batch", "--json"], {
  cwd: here,
  shell: true,
  windowsHide: true,
  stdio: ["pipe", "pipe", "pipe"],
});
child.stdin.end(JSON.stringify(commands));
child.stdout.pipe(process.stdout);
child.stderr.pipe(process.stderr);
const exitCode = await new Promise((resolve, reject) => {
  child.once("error", reject);
  child.once("exit", resolve);
});
if (exitCode !== 0) process.exit(exitCode || 1);
