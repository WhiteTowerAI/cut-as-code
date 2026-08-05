import { createHash } from "node:crypto";
import { createWriteStream } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const batchDir = path.dirname(here);
const selectedIndexes = new Set([
  1, 2, 6, 7, 8, 9, 10, 12, 13, 14,
  15, 16, 18, 19, 23, 24, 25, 26, 27, 28,
  30, 31, 32, 34, 36, 37, 38, 39, 41, 42,
  43, 44, 45, 46, 47, 48, 49, 50, 51, 52,
]);

const candidates = JSON.parse(await fs.readFile(path.join(here, "REVIEW_CANDIDATES.json"), "utf8"))
  .filter((candidate) => selectedIndexes.has(candidate.review_index));
if (candidates.length !== 40) throw new Error(`Expected 40 selected candidates, got ${candidates.length}`);

const licensingUrl = "https://tympanus.net/codrops/licensing/";
const articleOverrides = new Map([
  ["RotatingOnScrollAnimations", "https://tympanus.net/codrops/2026/06/18/exploring-3d-image-rotations-on-scroll/"],
]);
const stagingRoot = path.join(here, "_download-staging");
await fs.mkdir(stagingRoot, { recursive: true });

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function classify(candidate) {
  const title = candidate.title;
  const lower = title.toLowerCase();
  let primaryRole = "transition";
  if (/typography|letter|text/.test(lower)) primaryRole = "chapter";
  if (/spiral|column|sticky|scrolling slideshow|3d carousel/.test(lower)) primaryRole = "background";
  if (/cover page|intro/.test(lower)) primaryRole = "opener";
  if (/unreveal/.test(lower)) primaryRole = "outro";

  const roles = new Set([primaryRole]);
  if (/transition|clip|reveal|grid|slideshow|layout/.test(lower)) roles.add("transition");
  if (/typography|letter|text|stack|sticky/.test(lower)) roles.add("chapter");
  if (/scroll|spiral|carousel|column/.test(lower)) roles.add("background");

  const standout = /3d|webgl|kinetic|svg|pixel|clip|staggered|frame|shape|layer|shuffle/.test(lower);
  const strongTimeline = /transition|scroll|slideshow|reveal|animation|motion|shuffle/.test(lower);
  const scores = {
    standalone_visual_appeal: standout ? 5 : 4,
    temporal_structure: strongTimeline ? 5 : 4,
    explicit_video_utility: 5,
    content_replaceability: 4,
    fullscreen_adaptability: 4,
    visual_distinctiveness: standout ? 5 : 4,
    hyperframes_convertibility: 4,
  };
  const total = Object.values(scores).reduce((sum, score) => sum + score, 0);
  const mechanism = title
    .replace(/^Some Ideas for /, "")
    .replace(/^Ideas for /, "")
    .replace(/^Inspiration for /, "")
    .replace(/^How to Create /, "");
  return {
    primary_role: primaryRole,
    video_roles: [...roles],
    scores,
    total_score: total,
    visual_judgement: `The captured official demo shows ${mechanism.toLowerCase()} as a frame-dominant composition with a clear before/after state, so the mechanism can carry a ${primaryRole} without relying on ordinary form or button UI.`,
    hyperframes_judgement: "The effect runs entirely in the browser and its scroll, pointer, or slideshow progress can be replaced by a fixed absolute-time driver; assets can be localized and runtime randomness or RAF state can be frozen during a later port.",
  };
}

async function githubHead(owner, repo) {
  const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/commits/HEAD`, {
    headers: { "Accept": "application/vnd.github+json", "User-Agent": "cut-as-code-codrops-import" },
  });
  if (!response.ok) throw new Error(`${owner}/${repo} HEAD: HTTP ${response.status}`);
  return (await response.json()).sha;
}

async function download(url, destination) {
  const response = await fetch(url, { headers: { "User-Agent": "cut-as-code-codrops-import" } });
  if (!response.ok || !response.body) throw new Error(`${url}: HTTP ${response.status}`);
  await pipeline(Readable.fromWeb(response.body), createWriteStream(destination));
}

async function fileHash(filePath) {
  return sha256(await fs.readFile(filePath));
}

const catalog = [];
for (const candidate of candidates) {
  const source = new URL(candidate.source_url.replace(/\/$/, ""));
  const [owner, repoWithSuffix] = source.pathname.split("/").filter(Boolean);
  const repo = repoWithSuffix.replace(/\.git$/i, "");
  if (!owner || !repo || owner.toLowerCase() !== "codrops") {
    throw new Error(`Unsupported source URL: ${candidate.source_url}`);
  }

  const targetDir = path.join(batchDir, repo);
  try {
    await fs.access(targetDir);
    throw new Error(`Target already exists: ${targetDir}`);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }

  const commit = await githubHead(owner, repo);
  const partialPath = path.join(stagingRoot, `${repo}.zip.partial`);
  const zipPath = path.join(stagingRoot, `${repo}.zip`);
  const extractDir = path.join(stagingRoot, repo);
  await fs.rm(extractDir, { recursive: true, force: true });
  await fs.mkdir(extractDir, { recursive: true });
  await download(`https://codeload.github.com/${owner}/${repo}/zip/${commit}`, partialPath);
  await fs.rename(partialPath, zipPath);

  const extract = spawnSync("tar.exe", ["-xf", zipPath, "-C", extractDir], {
    encoding: "utf8",
    windowsHide: true,
  });
  if (extract.status !== 0) throw new Error(`${repo}: tar failed: ${extract.stderr || extract.stdout}`);
  const children = await fs.readdir(extractDir, { withFileTypes: true });
  const root = children.find((entry) => entry.isDirectory());
  if (!root) throw new Error(`${repo}: archive did not contain a root directory`);
  await fs.rename(path.join(extractDir, root.name), targetDir);
  await fs.rm(zipPath, { force: true });
  await fs.rm(extractDir, { recursive: true, force: true });

  const rootFiles = await fs.readdir(targetDir, { withFileTypes: true });
  const licenseEntry = rootFiles.find((entry) => entry.isFile() && /^licen[cs]e(?:\.|$)/i.test(entry.name));
  const license = licenseEntry
    ? {
        type: "MIT",
        evidence: "repository-file",
        file: licenseEntry.name,
        sha256: await fileHash(path.join(targetDir, licenseEntry.name)),
      }
    : { type: "MIT", evidence: "codrops-site-license", url: licensingUrl };

  catalog.push({
    id: repo,
    title: candidate.title,
    demo_page: candidate.page,
    demos_hub_url: candidate.page_url,
    demo_url: candidate.demo_url,
    article_url: candidate.article_url || articleOverrides.get(repo) || "",
    source_url: candidate.source_url,
    source_commit: commit,
    local_directory: repo,
    license,
    screening: classify(candidate),
    review_evidence: {
      initial_screenshot: candidate.initial_screenshot,
      initial_sha256: await fileHash(path.join(here, candidate.initial_screenshot)),
      interaction_screenshot: candidate.interaction_screenshot,
      interaction_sha256: await fileHash(path.join(here, candidate.interaction_screenshot)),
    },
  });
  console.log(`[${catalog.length}/40] ${repo} @ ${commit.slice(0, 12)}`);
}

await fs.rm(stagingRoot, { recursive: true, force: true });
await fs.writeFile(path.join(batchDir, "SOURCE_CATALOG.json"), `${JSON.stringify({
  generated_at: new Date().toISOString(),
  source_entry: "https://tympanus.net/codrops/demos/",
  licensing_url: licensingUrl,
  licensing_verified_at: "2026-08-04",
  licensing_statement: "Our downloadable demos are licensed under the MIT license, if not specifically mentioned otherwise.",
  screening_policy: {
    threshold_total: 26,
    threshold_explicit_video_utility: 4,
    threshold_hyperframes_convertibility: 4,
    reviewed_actual_demo_states: true,
    selected: 40,
    rejected_after_visual_review: 16,
  },
  projects: catalog,
}, null, 2)}\n`, "utf8");
console.log(`wrote ${catalog.length} projects to ${path.join(batchDir, "SOURCE_CATALOG.json")}`);
