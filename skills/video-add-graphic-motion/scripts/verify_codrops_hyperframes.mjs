import crypto from "node:crypto";
import { execFile } from "node:child_process";
import { createServer } from "node:http";
import {
  access,
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  symlink,
  writeFile,
} from "node:fs/promises";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);
const compareNames = (left, right) => left.localeCompare(right, "en", { numeric: true });
const FRAME_WIDTH = 320;
const FRAME_HEIGHT = 180;
const CONTROL_SELECTORS = [
  ".effects",
  ".trigger",
  ".slidenav",
  ".slides-nav",
  ".nav__arrow",
  ".cover__button",
  ".content__enter",
  ".enter",
  ".item__enter",
  ".frame__title-back",
  ".frame__prev",
];

export function parseFirstJson(source) {
  const start = source.indexOf("{");
  if (start < 0) throw new Error("CLI output does not contain JSON");
  let depth = 0;
  let quoted = false;
  let escaped = false;
  for (let index = start; index < source.length; index += 1) {
    const character = source[index];
    if (quoted) {
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === '"') quoted = false;
      continue;
    }
    if (character === '"') quoted = true;
    else if (character === "{") depth += 1;
    else if (character === "}" && --depth === 0) {
      return JSON.parse(source.slice(start, index + 1));
    }
  }
  throw new Error("CLI JSON envelope is incomplete");
}

export function summarizeVisualAudit({
  frames,
  repeatHash,
  repeatChangedPixelRatio,
  changedPixelRatios,
  errors,
  requestFailures,
  cursorHidden,
  visibleTextFlags,
  visibleControls,
}) {
  const nonblank = frames.every((frame) => frame.range >= 4 && frame.paintedRatio >= 0.001);
  const changed = Math.max(0, ...changedPixelRatios) >= 0.001;
  const deterministic = frames[1]?.hash === repeatHash || repeatChangedPixelRatio === 0;
  const runtimeClean = errors.length === 0 && requestFailures.length === 0;
  const chromeClean = visibleTextFlags.length === 0 && visibleControls.length === 0;
  return {
    nonblank,
    changed,
    deterministic,
    runtimeClean,
    cursorHidden,
    chromeClean,
    ok: nonblank && changed && deterministic && runtimeClean && cursorHidden && chromeClean,
  };
}

function optionValue(args, name, fallback = null) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
}

async function exists(target) {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
}

export async function discoverJobs(importsRoot, filter = "") {
  const jobs = [];
  for (const entry of (await readdir(importsRoot, { withFileTypes: true }))
    .filter((item) => item.isDirectory() && item.name !== "_review")
    .sort((a, b) => compareNames(a.name, b.name))) {
    const hyperframesDir = path.join(importsRoot, entry.name, "hyperframes");
    const receiptPath = path.join(hyperframesDir, "conversion.json");
    if (!(await exists(receiptPath))) continue;
    const receipt = JSON.parse(await readFile(receiptPath, "utf8"));
    if (!receipt.project_id || !Array.isArray(receipt.variants)) continue;
    for (const variant of receipt.variants) {
      const key = `${receipt.project_id}/${variant.name}`;
      if (filter && !key.toLowerCase().includes(filter.toLowerCase())) continue;
      jobs.push({
        key,
        projectId: receipt.project_id,
        variantName: variant.name,
        duration: variant.duration_s,
        interaction: variant.interaction,
        hyperframesDir,
      });
    }
  }
  return jobs;
}

function contentType(target) {
  return {
    ".css": "text/css; charset=utf-8",
    ".gif": "image/gif",
    ".html": "text/html; charset=utf-8",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
  }[path.extname(target).toLowerCase()] || "application/octet-stream";
}

async function startProjectServer() {
  let activeRoot = null;
  const server = createServer(async (request, response) => {
    try {
      if (!activeRoot) throw new Error("no active project root");
      const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
      const relative = pathname.replace(/^\/+/, "") || "index.html";
      let target = path.resolve(activeRoot, relative);
      const boundary = `${path.resolve(activeRoot)}${path.sep}`;
      if (target !== path.resolve(activeRoot) && !target.startsWith(boundary)) {
        response.writeHead(403).end("Forbidden");
        return;
      }
      if ((await stat(target)).isDirectory()) target = path.join(target, "index.html");
      response.writeHead(200, {
        "cache-control": "no-store",
        "content-type": contentType(target),
      });
      response.end(await readFile(target));
    } catch {
      response.writeHead(404).end("Not found");
    }
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return {
    port: server.address().port,
    setRoot(root) { activeRoot = path.resolve(root); },
    close() { return new Promise((resolve) => server.close(resolve)); },
  };
}

async function frameMetric(sharp, png) {
  const { data, info } = await sharp(png)
    .resize(FRAME_WIDTH, FRAME_HEIGHT, { fit: "fill" })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  let minimum = 255;
  let maximum = 0;
  let nonBlack = 0;
  let nonWhite = 0;
  const pixels = info.width * info.height;
  for (let offset = 0; offset < data.length; offset += info.channels) {
    const red = data[offset];
    const green = data[offset + 1];
    const blue = data[offset + 2];
    minimum = Math.min(minimum, red, green, blue);
    maximum = Math.max(maximum, red, green, blue);
    if (Math.max(red, green, blue) > 8) nonBlack += 1;
    if (Math.min(red, green, blue) < 247) nonWhite += 1;
  }
  return {
    hash: crypto.createHash("sha256").update(data).digest("hex"),
    range: maximum - minimum,
    paintedRatio: Number((Math.min(nonBlack, nonWhite) / pixels).toFixed(6)),
    pixels: data,
    channels: info.channels,
  };
}

function changedPixelRatio(left, right) {
  const pixels = left.length / 3;
  let changed = 0;
  for (let offset = 0; offset < left.length; offset += 3) {
    const delta = Math.max(
      Math.abs(left[offset] - right[offset]),
      Math.abs(left[offset + 1] - right[offset + 1]),
      Math.abs(left[offset + 2] - right[offset + 2]),
    );
    if (delta >= 8) changed += 1;
  }
  return Number((changed / pixels).toFixed(6));
}

export async function seekAndCapture(page, time) {
  await page.evaluate(async (target) => {
    const pending = [];
    window.dispatchEvent(new CustomEvent("hf-seek", {
      detail: {
        time: target,
        waitUntil(promise) { pending.push(Promise.resolve(promise)); },
      },
    }));
    await Promise.all(pending);
    await Promise.resolve();
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, time);
  return Buffer.from(await page.screenshot({ type: "png", omitBackground: false }));
}

async function browserAudit({ jobs, modulesDir, chromePath, outDir }) {
  const requireFromRuntime = createRequire(path.join(path.dirname(modulesDir), "codrops-audit.cjs"));
  const puppeteer = requireFromRuntime("puppeteer-core");
  const sharp = requireFromRuntime("sharp");
  const server = await startProjectServer();
  const browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args: ["--no-sandbox", "--force-color-profile=srgb", "--hide-scrollbars"],
  });
  const results = [];
  const tiles = [];
  try {
    for (const [index, job] of jobs.entries()) {
      server.setRoot(job.hyperframesDir);
      const page = await browser.newPage();
      await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
      const errors = [];
      const requestFailures = [];
      page.on("pageerror", (error) => errors.push(error.stack || error.message));
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });
      page.on("requestfailed", (request) => {
        requestFailures.push(`${request.url()}: ${request.failure()?.errorText || "failed"}`);
      });
      page.on("response", (response) => {
        if (response.status() >= 400) requestFailures.push(`${response.url()}: HTTP ${response.status()}`);
      });
      let result;
      try {
        const url = `http://127.0.0.1:${server.port}/${job.variantName}/index.html`;
        await page.goto(url, { waitUntil: "networkidle0", timeout: 45000 });
        await page.evaluate(() => document.fonts?.ready || Promise.resolve());
        const times = [0.1, job.duration / 2, Math.max(0.1, job.duration - 0.1)]
          .map((time) => Number(time.toFixed(3)));
        const pngs = [];
        const metrics = [];
        for (const time of times) {
          const png = await seekAndCapture(page, time);
          pngs.push(png);
          metrics.push(await frameMetric(sharp, png));
        }
        const repeatPng = await seekAndCapture(page, times[1]);
        const repeatMetric = await frameMetric(sharp, repeatPng);
        const pageState = await page.evaluate((selectors) => {
          const visible = (element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.display !== "none"
              && style.visibility !== "hidden"
              && Number(style.opacity || 1) > 0.01
              && rect.width > 0
              && rect.height > 0;
          };
          const textPattern = /(?:made by @codrops|created by @codrops|@codrops\s*2021|about this demo|github|codrops collective|based on this demo|this demo is powered by|if you enjoyed this demo|let us know via @codrops)/i;
          const visibleTextFlags = [...new Set(
            document.body.innerText.split(/\r?\n/).map((line) => line.trim()).filter((line) => line && textPattern.test(line)),
          )].slice(0, 20);
          const visibleControls = selectors.filter((selector) =>
            [...document.querySelectorAll(selector)].some(visible));
          const center = document.elementFromPoint(innerWidth / 2, innerHeight / 2) || document.body;
          return {
            cursorHidden: [document.body, center].every((element) => getComputedStyle(element).cursor === "none"),
            visibleTextFlags,
            visibleControls,
          };
        }, CONTROL_SELECTORS);
        const changedPixelRatios = [
          changedPixelRatio(metrics[0].pixels, metrics[1].pixels),
          changedPixelRatio(metrics[1].pixels, metrics[2].pixels),
        ];
        const repeatChangedPixelRatio = changedPixelRatio(metrics[1].pixels, repeatMetric.pixels);
        const frames = metrics.map(({ pixels, channels, ...metric }, metricIndex) => ({
          ...metric,
          time: times[metricIndex],
        }));
        const summary = summarizeVisualAudit({
          frames,
          repeatHash: repeatMetric.hash,
          repeatChangedPixelRatio,
          changedPixelRatios,
          errors,
          requestFailures,
          ...pageState,
        });
        result = {
          key: job.key,
          times,
          frames,
          repeatHash: repeatMetric.hash,
          repeatChangedPixelRatio,
          changedPixelRatios,
          errors: [...new Set(errors)],
          requestFailures: [...new Set(requestFailures)],
          ...pageState,
          ...summary,
        };
        tiles.push({ key: job.key, png: pngs[1] });
        if (!summary.ok) {
          const failureDir = path.join(outDir, "failures", job.projectId, job.variantName);
          await mkdir(failureDir, { recursive: true });
          await Promise.all(pngs.map((png, pngIndex) =>
            writeFile(path.join(failureDir, `t-${times[pngIndex]}.png`), png)));
          await writeFile(path.join(failureDir, `t-${times[1]}-repeat.png`), repeatPng);
        }
      } catch (error) {
        result = {
          key: job.key,
          ok: false,
          nonblank: false,
          changed: false,
          deterministic: false,
          runtimeClean: false,
          cursorHidden: false,
          chromeClean: false,
          errors: [...new Set([...errors, error.stack || error.message])],
          requestFailures: [...new Set(requestFailures)],
        };
      } finally {
        await page.close();
      }
      results.push(result);
      console.log(`[visual ${index + 1}/${jobs.length}] ${job.key}: ${result.ok ? "ok" : "FAIL"}`);
    }
  } finally {
    await browser.close();
    await server.close();
  }
  await writeContactSheets(sharp, tiles, outDir);
  return results;
}

function escapeXml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

async function writeContactSheets(sharp, tiles, outDir) {
  const columns = 5;
  const perSheet = 20;
  const tileHeight = FRAME_HEIGHT + 30;
  for (let offset = 0; offset < tiles.length; offset += perSheet) {
    const batch = tiles.slice(offset, offset + perSheet);
    const rows = Math.ceil(batch.length / columns);
    const composites = [];
    for (const [index, tile] of batch.entries()) {
      const left = (index % columns) * FRAME_WIDTH;
      const top = Math.floor(index / columns) * tileHeight;
      const frame = await sharp(tile.png).resize(FRAME_WIDTH, FRAME_HEIGHT, { fit: "cover" }).png().toBuffer();
      const label = Buffer.from(`<svg width="${FRAME_WIDTH}" height="30" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#111"/><text x="8" y="20" fill="#fff" font-family="Arial" font-size="14">${escapeXml(tile.key)}</text></svg>`);
      composites.push({ input: frame, left, top });
      composites.push({ input: label, left, top: top + FRAME_HEIGHT });
    }
    const fileName = `contact-sheet-${String(offset / perSheet + 1).padStart(2, "0")}.png`;
    await sharp({
      create: { width: columns * FRAME_WIDTH, height: rows * tileHeight, channels: 3, background: "#222" },
    }).composite(composites).png().toFile(path.join(outDir, fileName));
  }
}

async function runCliCommand(cliPath, args, cwd) {
  try {
    const result = await execFileAsync(process.execPath, [cliPath, ...args], {
      cwd,
      timeout: 180000,
      maxBuffer: 32 * 1024 * 1024,
      windowsHide: true,
    });
    return { ok: true, json: parseFirstJson(result.stdout), stderr: result.stderr.trim() };
  } catch (error) {
    let json = null;
    try { json = parseFirstJson(error.stdout || ""); } catch {}
    return {
      ok: false,
      json,
      error: error.message,
      stderr: String(error.stderr || "").trim(),
    };
  }
}

function cliErrorFindings(checkJson) {
  return ["lint", "runtime", "layout", "motion", "contrast"]
    .flatMap((section) => checkJson?.[section]?.findings || [])
    .filter((finding) => finding.severity === "error");
}

export function shouldRetryCliAttempt(result) {
  if (!result?.check) return false;
  if (result.check.json === null || result.check.json === undefined) return true;
  const errors = cliErrorFindings(result.check.json);
  if (errors.length !== 1 || errors[0].code !== "check_runtime_failure") return false;
  const diagnostic = [errors[0].message, result.check.error, result.check.stderr]
    .filter(Boolean)
    .join(" ");
  return /navigation.*(?:timeout|timed out)|(?:timeout|timed out).*navigation/i.test(diagnostic);
}

function cliAttemptEvidence(result, attempt) {
  return {
    attempt,
    ok: result.ok === true,
    check_ok: result.check?.ok === true,
    check_json_ok: result.check?.json?.ok ?? null,
    check_error: result.check?.error || null,
    check_stderr: result.check?.stderr || "",
    keyframes_ok: result.keyframes?.ok === true,
    cleanup: result.cleanup,
  };
}

export async function runCliAuditWithRetry(runAttempt) {
  const attempts = [];
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    const result = await runAttempt(attempt);
    attempts.push(cliAttemptEvidence(result, attempt));
    if (result.ok || !shouldRetryCliAttempt(result) || attempt === 2) {
      return { ...result, attempts };
    }
  }
  throw new Error("unreachable CLI retry state");
}

export async function cleanupCliStage(stage, rmImpl = rm) {
  const tempBoundary = `${path.resolve(os.tmpdir())}${path.sep}`;
  if (!path.resolve(stage).startsWith(tempBoundary) || !path.basename(stage).startsWith("codrops-hf-cli-")) {
    throw new Error(`refusing to remove unsafe staging path: ${stage}`);
  }
  try {
    await rmImpl(stage, { recursive: true, force: true, maxRetries: 8, retryDelay: 100 });
    return { ok: true };
  } catch (error) {
    return { ok: false, error: `${error.code ? `${error.code}: ` : ""}${error.message}` };
  }
}

async function cliAuditAttempt(job, cliPath) {
  const stage = await mkdtemp(path.join(os.tmpdir(), "codrops-hf-cli-"));
  let result;
  try {
    await copyFile(
      path.join(job.hyperframesDir, job.variantName, "index.html"),
      path.join(stage, "index.html"),
    );
    await symlink(path.join(job.hyperframesDir, "source"), path.join(stage, "source"), "junction");
    await symlink(
      path.join(job.hyperframesDir, job.variantName),
      path.join(stage, job.variantName),
      "junction",
    );
    const check = await runCliCommand(cliPath, ["check", stage, "--json"], stage);
    const keyframes = await runCliCommand(cliPath, ["keyframes", stage, "--json"], stage);
    result = {
      key: job.key,
      ok: check.ok && check.json?.ok === true && keyframes.ok,
      check,
      keyframes,
    };
  } finally {
    const cleanup = await cleanupCliStage(stage);
    if (result) result.cleanup = cleanup;
  }
  return result;
}

async function cliAuditJob(job, cliPath) {
  return runCliAuditWithRetry(() => cliAuditAttempt(job, cliPath));
}

async function cliAudit({ jobs, cliPath, workers }) {
  const results = new Array(jobs.length);
  let cursor = 0;
  let completed = 0;
  await Promise.all(Array.from({ length: Math.min(workers, jobs.length) }, async () => {
    while (cursor < jobs.length) {
      const index = cursor++;
      const result = await cliAuditJob(jobs[index], cliPath);
      results[index] = result;
      completed += 1;
      console.log(`[cli ${completed}/${jobs.length}] ${jobs[index].key}: ${result.ok ? "ok" : "FAIL"}`);
    }
  }));
  return results;
}

async function main() {
  const args = process.argv.slice(2);
  const importsRoot = path.resolve(args[0] || path.join(
    path.dirname(fileURLToPath(import.meta.url)),
    "../recipes/codrops",
  ));
  const modulesDir = path.resolve(optionValue(args, "--modules", ""));
  const cliPath = path.resolve(optionValue(args, "--cli", ""));
  const chromePath = path.resolve(optionValue(
    args,
    "--chrome",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  ));
  const outDir = path.resolve(optionValue(
    args,
    "--out",
    path.join(importsRoot, "_review", "hyperframes-verification"),
  ));
  const workers = Math.max(1, Number(optionValue(args, "--workers", "3")) || 3);
  const filter = optionValue(args, "--filter", "");
  const skipVisual = args.includes("--skip-visual");
  const skipCli = args.includes("--skip-cli");
  if (!skipVisual && !(await exists(path.join(modulesDir, "puppeteer-core")))) {
    throw new Error("--modules must point to a node_modules directory containing puppeteer-core and sharp");
  }
  if (!skipVisual && !(await exists(chromePath))) throw new Error(`Chrome not found: ${chromePath}`);
  if (!skipCli && !(await exists(cliPath))) throw new Error(`HyperFrames CLI not found: ${cliPath}`);
  const jobs = await discoverJobs(importsRoot, filter);
  if (jobs.length === 0) throw new Error("no Codrops HyperFrames variants discovered");
  await mkdir(outDir, { recursive: true });
  const report = {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    imports_root: importsRoot,
    total_variants: jobs.length,
    visual: skipVisual ? [] : await browserAudit({ jobs, modulesDir, chromePath, outDir }),
    cli: skipCli ? [] : await cliAudit({ jobs, cliPath, workers }),
  };
  report.summary = {
    visual_passed: report.visual.filter((item) => item.ok).length,
    visual_failed: report.visual.filter((item) => !item.ok).length,
    cli_passed: report.cli.filter((item) => item.ok).length,
    cli_failed: report.cli.filter((item) => !item.ok).length,
  };
  await writeFile(path.join(outDir, "verification.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report.summary));
  if (report.summary.visual_failed || report.summary.cli_failed) process.exitCode = 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  });
}
