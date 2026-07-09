// shoot.mjs — self-check by driving the SYSTEM Chrome directly.
//
// Why this exists: `hyperframes render` / `snapshot` shell out to a cached
// chrome-headless-shell that is corrupt on some Windows installs (spawn EFTYPE
// / "Exec format error"). `hyperframes lint` + `validate` still work, but they
// don't give you a picture to eyeball. This script bypasses HF's browser
// entirely: it launches the real installed Chrome via puppeteer-core, loads
// index.html, and screenshots each cue's mid-window.
//
// It faithfully mimics the HF runtime so a bad composition can't hide behind
// the harness: it windows each .clip by its own data-start/data-duration and
// toggles style.visibility — exactly what the runtime does — instead of
// force-showing a scene. If the wrong scene paints, the composition is wrong.
//
// Usage:  node shoot.mjs [comp-id] [t1,t2,...]
//   defaults: comp id "v2hf-almanac", the 5 example cue mid-windows.
//   Set CHROME env to override the Chrome path.
import puppeteer from "puppeteer-core";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { existsSync } from "node:fs";

const here = dirname(fileURLToPath(import.meta.url));

// Prefer $CHROME, else the usual Windows/macOS/Linux install locations. NOT
// HF's cached chrome-headless-shell — that's the one that may be corrupt.
const CHROME_CANDIDATES = [
  process.env.CHROME,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);
const CHROME = CHROME_CANDIDATES.find((p) => existsSync(p));
if (!CHROME) {
  console.error("No system Chrome found. Set CHROME=/path/to/chrome and retry.");
  process.exit(1);
}

const COMP_ID = process.argv[2] || "v2hf-almanac";
const TIMES = (process.argv[3] || "3,9,15,21,27").split(",").map(Number);

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--no-sandbox", "--force-color-profile=srgb", "--hide-scrollbars"],
});
const page = await browser.newPage();
// Read the stage size so the shot matches the composition.
await page.goto("file://" + join(here, "index.html").replace(/\\/g, "/"), {
  waitUntil: "networkidle0",
});
const { w, h } = await page.evaluate(() => {
  const s = document.getElementById("stage");
  return { w: Number(s.dataset.width) || 1920, h: Number(s.dataset.height) || 1080 };
});
await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });

// A checkerboard behind the transparent stage proves alpha: any checker pixel
// showing through = correctly transparent; opaque (fullBleed / card) areas hide
// it. This is only in the harness — the real overlay renders on transparent.
await page.evaluate(() => {
  const bg = document.createElement("div");
  bg.style.cssText =
    "position:fixed;inset:0;z-index:-1;background:" +
    "repeating-conic-gradient(#bbb 0 25%, #eee 0 50%) 0 0/80px 80px";
  document.body.prepend(bg);
});
await page.evaluate(() => document.fonts.ready); // lay out serifs before shooting

for (const t of TIMES) {
  await page.evaluate(
    ({ id, time }) => {
      // Mimic the runtime: window each .clip by its OWN data-start/duration and
      // toggle visibility. No opacity forcing — the composition must be correct.
      document.querySelectorAll(".clip").forEach((el) => {
        const start = parseFloat(el.dataset.start ?? "0") || 0;
        const dur = parseFloat(el.dataset.duration ?? "0") || 0;
        el.style.visibility = time >= start && time < start + dur ? "visible" : "hidden";
      });
      const tl = window.__timelines[id];
      tl.pause();
      // suppressEvents=false so onUpdate (count-ups) fires on this single jump;
      // HF's per-frame seek renders it naturally.
      tl.seek(time, false);
    },
    { id: COMP_ID, time: t },
  );
  await new Promise((r) => setTimeout(r, 120)); // let the paint settle
  const out = join(here, "snapshots", `t${t}s.png`);
  await page.screenshot({ path: out, omitBackground: false });
  console.log("wrote", out);
}

await browser.close();
console.log("done");
