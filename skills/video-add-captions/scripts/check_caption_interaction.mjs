import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";

import * as interactionState from "./caption_interaction_state.mjs";

const markers = [
  "__CAPTION_STYLE_REVIEW_DATA__",
  "__CAPTION_EVIDENCE_REVIEW_DATA__",
  "__SHORTS_CANDIDATE_REVIEW_DATA__",
  "__SHORTS_VERTICAL_REVIEW_DATA__",
];
const tokens = {
  bg: "#151719",
  band: "#1d2023",
  surface: "#24282b",
  line: "#3b4145",
  text: "#f2eee5",
  muted: "#aeb4b7",
  accent: "#4fc3b4",
  warning: "#f3bd5b",
};
const requiredIds = ["review-status", "review-form", "copy-summary", "summary-output", "review-errors"];
const skillRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const galleryPath = resolve(skillRoot, "assets/style-previews/index.html");
const manifestPath = resolve(skillRoot, "assets/style-previews/preview-manifest.json");
const styleConfigPath = resolve(skillRoot, "scripts/caption-styles.json");
const interactionPath = resolve(skillRoot, "scripts/caption_interaction.mjs");
const failures = [];

function check(name, callback) {
  try {
    callback();
    console.log(`[caption-interaction] PASS ${name}`);
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

function checkTemplate(path, marker) {
  assert.ok(existsSync(path), `template missing: ${path}`);
  const html = readFileSync(path, "utf8");
  for (const [name, value] of Object.entries(tokens)) {
    assert.match(html, new RegExp(`--${name}\\s*:\\s*${value}\\s*(?:;|})`), `${path}: missing --${name}: ${value}`);
  }
  assert.match(html, /width\s*:\s*min\(1180px,\s*calc\(100%\s*-\s*32px\)\)/, `${path}: missing review width`);
  assert.match(html, /\.toolbar\s*\{[^}]*position\s*:\s*sticky\b/s, `${path}: toolbar must be sticky`);
  for (const id of requiredIds) {
    assert.match(html, new RegExp(`id=["']${id}["']`), `${path}: missing #${id}`);
  }
  assert.match(html, /min-height\s*:\s*38px\b/, `${path}: missing 38px control height`);
  assert.match(html, /@media\s*\(max-width\s*:\s*1100px\)/, `${path}: missing 1100px breakpoint`);
  assert.match(html, /@media\s*\(max-width\s*:\s*780px\)/, `${path}: missing 780px breakpoint`);
  assert.equal(html.split(marker).length - 1, 1, `${path}: expected exactly one ${marker}`);
  assert.equal(markers.reduce((count, value) => count + html.split(value).length - 1, 0), 1,
    `${path}: expected exactly one page-specific payload marker`);
}

function runInteraction(args, expectedStatus = 0) {
  const result = spawnSync(process.execPath, [interactionPath, ...args], { encoding: "utf8" });
  assert.equal(result.status, expectedStatus, [result.stdout, result.stderr].filter(Boolean).join("\n"));
  return result;
}

function readState(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function readBoundContext(path) {
  const html = readFileSync(path, "utf8");
  const match = html.match(/const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)";/);
  assert.ok(match, "bound page must contain one base64 review payload");
  return JSON.parse(Buffer.from(match[1], "base64").toString("utf8"));
}

function summary(reviewId, choice = "pill-yellow") {
  return `Caption style review\nReview: ${reviewId}\nDecision: select\nChoice: ${choice}`;
}

function previewSummary(reviewId, decision, detail) {
  return decision === "approve"
    ? `Caption preview review\nReview: ${reviewId}\nDecision: approve\nEvidence: ${detail ?? "early, middle, late, no-caption"}`
    : `Caption preview review\nReview: ${reviewId}\nDecision: revise\nChanges: ${detail ?? "Raise the captions above the lower third."}`;
}

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const name = Buffer.from(type, "ascii");
  const chunk = Buffer.alloc(data.length + 12);
  chunk.writeUInt32BE(data.length, 0);
  name.copy(chunk, 4);
  data.copy(chunk, 8);
  chunk.writeUInt32BE(crc32(Buffer.concat([name, data])), data.length + 8);
  return chunk;
}

function tinyPng(width = 1, height = 1) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header.set([8, 6, 0, 0, 0], 8);
  const row = Buffer.alloc(1 + width * 4);
  const pixels = Buffer.concat(Array.from({ length: height }, () => row));
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    pngChunk("IHDR", header), pngChunk("IDAT", deflateSync(pixels)), pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

check("manifest has exactly 25 unique combination IDs", () => {
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8").replace(/^\uFEFF/, ""));
  const ids = manifest.groups.flatMap((group) => group.items.map((item) => item.id));
  assert.equal(manifest.total, 25);
  assert.equal(ids.length, 25);
  assert.equal(new Set(ids).size, 25);
  assert.deepEqual(interactionState.validSelectionIds, ids);
});

check("generic gallery implements the shared review shell", () => {
  checkTemplate(galleryPath, markers[0]);
});

check("gallery uses one native single-selection group", () => {
  const html = readFileSync(galleryPath, "utf8");
  assert.equal((html.match(/type="radio"\s+name="caption-style"/g) ?? []).length, 25);
  assert.match(html, /const selected = form\.querySelector\('[^']*caption-style[^']*:checked'\)/);
});

check("focused radios visibly outline the entire style card", () => {
  const html = readFileSync(galleryPath, "utf8");
  assert.match(html, /\.style-card:(?:focus-within|has\(input:focus-visible\))\s*\{[^}]*outline\s*:/s);
});

check("generic and bound galleries expose the correct copy action", () => {
  const html = readFileSync(galleryPath, "utf8");
  assert.match(html, /reviewData\.review_id\s*\?\s*"Copy summary"\s*:\s*"Copy ID"/);
  assert.match(html, /Caption style review\\nReview: \$\{reviewData\.review_id\}\\nDecision: select\\nChoice: \$\{selected\.value\}/);
});

check("gallery includes an explicit clean default button", () => {
  const html = readFileSync(galleryPath, "utf8");
  assert.match(html, /id="select-default"[^>]*>\s*Use clean default\s*</);
  assert.match(html, /select-default[\s\S]*value\s*===\s*reviewData\.default_choice/);
});

check("dialog close returns focus to its trigger", () => {
  const html = readFileSync(galleryPath, "utf8");
  assert.match(html, /previewDialog\.addEventListener\("close",[\s\S]*lastTrigger\.focus\(\{ preventScroll: true \}\)/);
});

check("structured response parser is strict", () => {
  const parse = interactionState.parseCaptionStyleSummary;
  assert.equal(typeof parse, "function", "parseCaptionStyleSummary export is missing");
  const reviewId = "f82e20c8-8049-45d6-b31d-8f55f90f778e";
  assert.deepEqual(parse(summary(reviewId), reviewId), { reviewId, decision: "select", choiceId: "pill-yellow" });
  assert.deepEqual(parse("CAPTION STYLE REVIEW\nrEvIeW: f82e20c8-8049-45d6-b31d-8f55f90f778e\nDECISION: select\nchoice:  pill-yellow  ", reviewId), {
    reviewId,
    decision: "select",
    choiceId: "pill-yellow",
  });
  assert.throws(() => parse(summary("wrong-review"), reviewId), /review id/i);
  assert.throws(() => parse(`${summary(reviewId)}\nChoice: clean`, reviewId), /duplicate/i);
  assert.throws(() => parse(`${summary(reviewId)}\nNote: nope`, reviewId), /unknown/i);
  assert.throws(() => parse(`Caption style review\nReview: ${reviewId}\nDecision: select`, reviewId), /missing/i);
});

check("preview response parsers are strict", () => {
  const parseApprove = interactionState.parseCaptionPreviewApproval;
  const parseRevise = interactionState.parseCaptionPreviewRevision;
  assert.equal(typeof parseApprove, "function", "parseCaptionPreviewApproval export is missing");
  assert.equal(typeof parseRevise, "function", "parseCaptionPreviewRevision export is missing");
  const reviewId = "f82e20c8-8049-45d6-b31d-8f55f90f778e";
  assert.deepEqual(parseApprove(previewSummary(reviewId, "approve"), reviewId), {
    reviewId, decision: "approve", evidence: ["early", "middle", "late", "no-caption"],
  });
  assert.deepEqual(parseApprove(
    `CAPTION PREVIEW REVIEW\nrEvIeW: ${reviewId}\nDECISION: approve\nEVIDENCE: late, early, no-caption, middle`,
    reviewId,
  ).evidence.sort(), ["early", "late", "middle", "no-caption"]);
  assert.deepEqual(parseRevise(previewSummary(reviewId, "revise"), reviewId), {
    reviewId, decision: "revise", changes: "Raise the captions above the lower third.",
  });
  for (const invalid of [
    previewSummary("wrong-review", "approve"),
    previewSummary(reviewId, "approve", "early, middle, late"),
    previewSummary(reviewId, "approve", "early, middle, late, late"),
    `${previewSummary(reviewId, "approve")}\nEvidence: early, middle, late, no-caption`,
    `${previewSummary(reviewId, "approve")}\nNote: no`,
  ]) assert.throws(() => parseApprove(invalid, reviewId));
  for (const invalid of [
    previewSummary("wrong-review", "revise"),
    `Caption preview review\nReview: ${reviewId}\nDecision: revise\nChanges:   `,
    `${previewSummary(reviewId, "revise")}\nUnknown: no`,
  ]) assert.throws(() => parseRevise(invalid, reviewId));
});

const tempRoot = mkdtempSync(join(tmpdir(), "caption-interaction-check-"));
try {
  const sourcePath = join(tempRoot, "source & sample.mp4");
  const captionsPath = join(tempRoot, "captions.json");
  const timelinePath = join(tempRoot, "timeline.json");
  writeFileSync(sourcePath, "source", "utf8");
  writeFileSync(captionsPath, '{"timeline_id":"main"}\n', "utf8");
  writeFileSync(timelinePath, '{"schema_version":1,"timeline_id":"main"}\n', "utf8");

  check("bound start creates a hash-bound page without selecting", () => {
    const statePath = join(tempRoot, "bound-state.json");
    const reviewDir = join(tempRoot, "review");
    const result = runInteraction([
      "start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--no-open", "true",
    ]);
    const state = readState(statePath);
    const pagePath = state.reviewPage.path;
    const aliasPath = join(reviewDir, "captions-style-review.html");
    assert.ok(existsSync(pagePath));
    assert.match(state.reviewId, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    assert.equal(state.phase, "awaiting_style_selection");
    assert.equal(state.selection, null);
    assert.equal(state.reviewPage.path, resolve(pagePath));
    assert.equal(basename(pagePath), `captions-style-review-${state.reviewId}.html`);
    assert.match(state.reviewPage.sha256, /^[0-9a-f]{64}$/);
    assert.equal(state.reviewPage.assets.length, interactionState.galleryAssetFiles.length);
    assert.deepEqual(state.styleDefinitions, [styleConfigPath, manifestPath].map((path) => ({
      path,
      sha256: interactionState.hashFile(path),
    })));
    assert.equal(new Set(state.reviewPage.assets.map((binding) => dirname(binding.path))).size, 1);
    const assetDirectory = dirname(state.reviewPage.assets[0].path);
    assert.match(basename(assetDirectory), new RegExp(state.reviewId));
    for (const binding of state.reviewPage.assets) {
      assert.ok(existsSync(binding.path));
      assert.equal(binding.sha256, interactionState.hashFile(binding.path));
    }
    assert.match(result.stdout, new RegExp(pagePath.replaceAll("\\", "\\\\")));
    assert.match(result.stdout, /STOP/i);
    const pageHtml = readFileSync(pagePath, "utf8");
    assert.equal(readFileSync(aliasPath, "utf8"), pageHtml);
    assert.equal(pageHtml.includes(markers[0]), false);
    assert.match(pageHtml, new RegExp(`<base href="\\./${basename(assetDirectory)}/">`));
    assert.deepEqual(readBoundContext(pagePath), {
      schema_version: 1,
      review_id: state.reviewId,
      source_name: basename(sourcePath),
      decision_mode: "human",
      default_choice: "clean",
    });
  });

  check("bound human selection accepts only the matching structured summary", () => {
    const statePath = join(tempRoot, "strict-state.json");
    const reviewDir = join(tempRoot, "strict-review");
    runInteraction(["start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--no-open", "true"]);
    const reviewId = readState(statePath).reviewId;
    for (const response of [
      summary("wrong-review"),
      `${summary(reviewId)}\nChoice: clean`,
      `${summary(reviewId)}\nUnknown: value`,
      `Caption style review\nReview: ${reviewId}\nDecision: select`,
      "pill-yellow",
      "skip",
    ]) {
      runInteraction(["select", "--state", statePath, "--response", response], 1);
    }
    const acceptedResponse = summary(reviewId, "stroked-blue");
    runInteraction(["select", "--state", statePath, "--response", acceptedResponse]);
    const selectedState = readState(statePath);
    assert.equal(selectedState.selection.choiceId, "stroked-blue");
    assert.equal(selectedState.selection.response, acceptedResponse);
  });

  check("bound selection rejects a changed review page", () => {
    const statePath = join(tempRoot, "tampered-state.json");
    const reviewDir = join(tempRoot, "tampered-review");
    runInteraction(["start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--no-open", "true"]);
    const state = readState(statePath);
    writeFileSync(state.reviewPage.path, `${readFileSync(state.reviewPage.path, "utf8")}\n<!-- changed -->\n`, "utf8");
    runInteraction(["select", "--state", statePath, "--response", summary(state.reviewId)], 1);
  });

  for (const [label, fileName] of [["PNG", "preview-clean.png"], ["props JSON", "props-clean.json"]]) {
    check(`bound selection rejects changed ${label}`, () => {
      const statePath = join(tempRoot, `tampered-${label.replaceAll(" ", "-")}.json`);
      const reviewDir = join(tempRoot, `tampered-${label.replaceAll(" ", "-")}-review`);
      runInteraction(["start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath,
        "--review-dir", reviewDir, "--no-open", "true"]);
      const state = readState(statePath);
      const binding = state.reviewPage.assets?.find((asset) => basename(asset.path) === fileName);
      const assetPath = binding?.path ?? join(reviewDir, fileName);
      writeFileSync(assetPath, `${readFileSync(assetPath)}changed`, "utf8");
      runInteraction(["select", "--state", statePath, "--response", summary(state.reviewId)], 1);
    });
  }

  check("a different state cannot replace an existing bound review without force", () => {
    const firstStatePath = join(tempRoot, "collision-first.json");
    const secondStatePath = join(tempRoot, "collision-second.json");
    const reviewDir = join(tempRoot, "collision-review");
    runInteraction(["start", "--state", firstStatePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--no-open", "true"]);
    const originalPage = readFileSync(join(reviewDir, "captions-style-review.html"), "utf8");
    runInteraction(["start", "--state", secondStatePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--no-open", "true"], 1);
    assert.equal(existsSync(secondStatePath), false);
    assert.equal(readFileSync(join(reviewDir, "captions-style-review.html"), "utf8"), originalPage);
    assert.deepEqual(readdirSync(reviewDir).filter((name) => name.includes(".tmp")), []);
  });

  check("force restart creates a new review ID and page binding", () => {
    const statePath = join(tempRoot, "force-state.json");
    const reviewDir = join(tempRoot, "force-review");
    const args = ["start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--no-open", "true"];
    runInteraction(args);
    const before = readState(statePath);
    const beforeStateText = readFileSync(statePath, "utf8");
    const beforePageText = readFileSync(before.reviewPage.path, "utf8");
    const beforePageHash = interactionState.hashFile(before.reviewPage.path);
    runInteraction([...args, "--force", "true"]);
    const after = readState(statePath);
    assert.notEqual(after.reviewId, before.reviewId);
    assert.notEqual(after.reviewPage.path, before.reviewPage.path);
    assert.equal(basename(after.reviewPage.path), `captions-style-review-${after.reviewId}.html`);
    assert.notEqual(after.reviewPage.sha256, before.reviewPage.sha256);
    assert.notEqual(dirname(after.reviewPage.assets[0].path), dirname(before.reviewPage.assets[0].path));
    assert.notEqual(readFileSync(statePath, "utf8"), beforeStateText);
    assert.equal(readFileSync(before.reviewPage.path, "utf8"), beforePageText);
    assert.equal(interactionState.hashFile(before.reviewPage.path), beforePageHash);
    assert.equal(before.reviewPage.sha256, beforePageHash);
    assert.ok(existsSync(before.reviewPage.assets[0].path));
    assert.ok(existsSync(after.reviewPage.assets[0].path));
    assert.equal(
      readFileSync(join(reviewDir, "captions-style-review.html"), "utf8"),
      readFileSync(after.reviewPage.path, "utf8"),
    );
    assert.deepEqual(readdirSync(reviewDir).filter((name) => name.includes(".tmp")), []);
    runInteraction(["select", "--state", statePath, "--response", summary(before.reviewId)], 1);
  });

  check("failed state persistence leaves the previous state, page, and alias authoritative", () => {
    const oldStatePath = join(tempRoot, "persist-old.json");
    const failingStatePath = join(tempRoot, "persist-target");
    const reviewDir = join(tempRoot, "persist-review");
    runInteraction(["start", "--state", oldStatePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--no-open", "true"]);
    const oldStateText = readFileSync(oldStatePath, "utf8");
    const oldState = JSON.parse(oldStateText);
    const oldPageText = readFileSync(oldState.reviewPage.path, "utf8");
    const aliasPath = join(reviewDir, "captions-style-review.html");
    const oldAliasText = readFileSync(aliasPath, "utf8");
    mkdirSync(failingStatePath);

    runInteraction(["start", "--state", failingStatePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--force", "true", "--no-open", "true"], 1);

    assert.equal(readFileSync(oldStatePath, "utf8"), oldStateText);
    assert.equal(readFileSync(oldState.reviewPage.path, "utf8"), oldPageText);
    assert.equal(interactionState.hashFile(oldState.reviewPage.path), oldState.reviewPage.sha256);
    assert.equal(readFileSync(aliasPath, "utf8"), oldAliasText);
    assert.deepEqual(readdirSync(reviewDir).filter((name) => name.includes(".tmp")), []);
    assert.deepEqual(readdirSync(tempRoot).filter((name) => name.includes(".tmp")), []);
  });

  check("failed initial state persistence removes the new review and permits retry", () => {
    const stateDirectory = join(tempRoot, "retry-state-parent");
    const statePath = join(stateDirectory, "state.json");
    const reviewDir = join(tempRoot, "retry-review");
    const args = ["start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--no-open", "true"];
    runInteraction(args, 1);
    assert.equal(existsSync(statePath), false);
    assert.deepEqual(
      readdirSync(reviewDir).filter((name) => /^captions-style-review(?:-assets)?-/i.test(name)),
      [],
    );
    assert.deepEqual(readdirSync(reviewDir).filter((name) => name.includes(".tmp")), []);
    assert.equal(existsSync(join(reviewDir, "captions-style-review.html")), false);

    mkdirSync(stateDirectory);
    runInteraction(args);
    assert.ok(existsSync(statePath));
    assert.ok(existsSync(readState(statePath).reviewPage.path));
  });

  check("standalone mode retains exact ID and skip compatibility", () => {
    for (const [name, response, expected] of [["id", "pill-yellow", "pill-yellow"], ["skip", "skip", "clean"]]) {
      const statePath = join(tempRoot, `standalone-${name}.json`);
      runInteraction(["start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath, "--no-open", "true"]);
      runInteraction(["select", "--state", statePath, "--response", response]);
      const state = readState(statePath);
      assert.equal(state.reviewPage, null);
      assert.equal(state.selection.choiceId, expected);
    }
  });

  check("agent mode cannot consume a human summary", () => {
    const statePath = join(tempRoot, "agent-state.json");
    const reviewDir = join(tempRoot, "agent-review");
    runInteraction(["start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--decision-mode", "agent", "--delegation-note", "Delegated for check.", "--no-open", "true"]);
    const state = readState(statePath);
    runInteraction(["select", "--state", statePath, "--response", summary(state.reviewId)], 1);
    runInteraction(["agent-select", "--state", statePath, "--choice", "clean", "--rationale", "Readable default."]);
    assert.equal(readState(statePath).selection.actor, "agent");
  });

  const preparePreview = (
    name,
    decisionMode = "human",
    evidenceFactory = () => tinyPng(),
    reviewTimelinePath = timelinePath,
  ) => {
    const statePath = join(tempRoot, `${name}-state.json`);
    const reviewDir = join(tempRoot, `${name}-style-review`);
    const startArgs = ["start", "--state", statePath, "--source", sourcePath, "--captions", captionsPath,
      "--review-dir", reviewDir, "--decision-mode", decisionMode, "--no-open", "true"];
    if (decisionMode === "agent") startArgs.push("--delegation-note", "Delegated for interaction check.");
    runInteraction(startArgs);
    let state = readState(statePath);
    if (decisionMode === "human") {
      runInteraction(["select", "--state", statePath, "--response", summary(state.reviewId, "clean")]);
    } else {
      runInteraction(["agent-select", "--state", statePath, "--choice", "clean", "--rationale", "Readable default."]);
    }
    state = readState(statePath);
    const evidenceDir = join(tempRoot, `${name}-evidence`);
    mkdirSync(evidenceDir);
    const evidence = ["early", "middle", "late", "no-caption"].map((label) => {
      const path = join(evidenceDir, `preview-${label}.png`);
      writeFileSync(path, evidenceFactory(label));
      return path;
    });
    const reviewPage = join(evidenceDir, "captions-review.html");
    const payload = Buffer.from(JSON.stringify({
      schema_version: 1,
      review_id: state.reviewId,
      selection_id: state.selection.choiceId,
      timeline_id: JSON.parse(readFileSync(reviewTimelinePath, "utf8")).timeline_id,
      timeline_sha256: interactionState.hashFile(reviewTimelinePath),
      samples: evidence.map((path, index) => ({
        label: ["early", "middle", "late", "no-caption"][index],
        preview: basename(path),
        sha256: interactionState.hashFile(path),
      })),
    }), "utf8").toString("base64");
    writeFileSync(reviewPage, `<script>const REVIEW_DATA_B64 = "${payload}";</script>`, "utf8");
    const projectMetaPath = join(evidenceDir, "project-meta.json");
    writeFileSync(projectMetaPath, JSON.stringify({ interaction: {
      statePath: resolve(statePath), selectionId: state.selection.choiceId, overridesSha256: null,
    } }), "utf8");
    return {
      statePath,
      reviewPage,
      projectMetaPath,
      evidence,
      reviewId: state.reviewId,
      timelinePath: reviewTimelinePath,
    };
  };

  check("bound preview requires and binds its review page and exact evidence", () => {
    const fixture = preparePreview("bound-preview");
    const baseArgs = ["preview-ready", "--state", fixture.statePath, "--project-meta", fixture.projectMetaPath,
      "--evidence", fixture.evidence.join(",")];
    runInteraction(baseArgs, 1);
    runInteraction([...baseArgs, "--review-page", fixture.reviewPage], 1);
    runInteraction([...baseArgs, "--review-page", fixture.reviewPage, "--timeline", fixture.timelinePath]);
    const state = readState(fixture.statePath);
    assert.equal(state.phase, "awaiting_preview_confirmation");
    assert.equal(state.preview.reviewPagePath, resolve(fixture.reviewPage));
    assert.equal(state.preview.reviewPageSha256, interactionState.hashFile(fixture.reviewPage));
    assert.deepEqual(state.preview.evidence.map((item) => item.label), ["early", "middle", "late", "no-caption"]);
    assert.match(state.preview.evidenceSignature, /^[0-9a-f]{64}$/);
    assert.deepEqual(state.preview.timeline, {
      path: resolve(fixture.timelinePath),
      sha256: interactionState.hashFile(fixture.timelinePath),
      timelineId: "main",
    });
  });

  check("bound preview rejects a same-ID timeline that differs from the review page", () => {
    const timelineA = join(tempRoot, "timeline-a.json");
    const timelineB = join(tempRoot, "timeline-b.json");
    writeFileSync(timelineA, '{"schema_version":1,"timeline_id":"main","revision":"a"}\n', "utf8");
    writeFileSync(timelineB, '{"schema_version":1,"timeline_id":"main","revision":"b"}\n', "utf8");
    const fixture = preparePreview("timeline-cross-binding", "human", () => tinyPng(), timelineA);
    runInteraction(["preview-ready", "--state", fixture.statePath, "--project-meta", fixture.projectMetaPath,
      "--evidence", fixture.evidence.join(","), "--review-page", fixture.reviewPage,
      "--timeline", timelineB], 1);
    assert.equal(readState(fixture.statePath).phase, "style_selected");
  });

  check("preview-ready rejects corrupt and dimension-mismatched PNG evidence", () => {
    const corrupt = preparePreview("corrupt-png", "human", () => Buffer.from("not a png"));
    runInteraction(["preview-ready", "--state", corrupt.statePath, "--project-meta", corrupt.projectMetaPath,
      "--evidence", corrupt.evidence.join(","), "--review-page", corrupt.reviewPage,
      "--timeline", corrupt.timelinePath], 1);

    const mismatched = preparePreview(
      "mismatched-png", "human", label => tinyPng(label === "late" ? 2 : 1, 1),
    );
    runInteraction(["preview-ready", "--state", mismatched.statePath, "--project-meta", mismatched.projectMetaPath,
      "--evidence", mismatched.evidence.join(","), "--review-page", mismatched.reviewPage,
      "--timeline", mismatched.timelinePath], 1);
  });

  check("bound human approve and revise consume only matching structured summaries", () => {
    const approve = preparePreview("human-approve");
    runInteraction(["preview-ready", "--state", approve.statePath, "--project-meta", approve.projectMetaPath,
      "--evidence", approve.evidence.join(","), "--review-page", approve.reviewPage,
      "--timeline", approve.timelinePath]);
    runInteraction(["confirm", "--state", approve.statePath, "--response", "confirm render"], 1);
    runInteraction(["confirm", "--state", approve.statePath, "--response", previewSummary(approve.reviewId, "approve")]);
    assert.equal(readState(approve.statePath).phase, "render_approved");

    const revise = preparePreview("human-revise");
    runInteraction(["preview-ready", "--state", revise.statePath, "--project-meta", revise.projectMetaPath,
      "--evidence", revise.evidence.join(","), "--review-page", revise.reviewPage,
      "--timeline", revise.timelinePath]);
    runInteraction(["adjust", "--state", revise.statePath, "--response", "move it"], 1);
    const response = previewSummary(revise.reviewId, "revise", "Raise captions 20 pixels.");
    runInteraction(["adjust", "--state", revise.statePath, "--response", response]);
    const state = readState(revise.statePath);
    assert.equal(state.phase, "style_selected");
    assert.equal(state.preview, null);
    assert.equal(state.approval, null);
    assert.equal(state.history.at(-1).response, response);
  });

  check("agent preview decisions cannot consume human summaries", () => {
    const fixture = preparePreview("agent-preview", "agent");
    runInteraction(["preview-ready", "--state", fixture.statePath, "--project-meta", fixture.projectMetaPath,
      "--evidence", fixture.evidence.join(","), "--review-page", fixture.reviewPage,
      "--timeline", fixture.timelinePath]);
    runInteraction(["confirm", "--state", fixture.statePath, "--response", previewSummary(fixture.reviewId, "approve")], 1);
    runInteraction(["adjust", "--state", fixture.statePath, "--response", previewSummary(fixture.reviewId, "revise")], 1);
    runInteraction(["agent-confirm", "--state", fixture.statePath, "--rationale", "All four frames are readable."]);
    assert.equal(readState(fixture.statePath).approval.actor, "agent");
  });

  check("preview binding mutations block overlay generation", () => {
    for (const mutation of ["page", "style-page", "evidence", "meta", "override", "signature"]) {
      const fixture = preparePreview(`mutation-${mutation}`);
      runInteraction(["preview-ready", "--state", fixture.statePath, "--project-meta", fixture.projectMetaPath,
        "--evidence", fixture.evidence.join(","), "--review-page", fixture.reviewPage,
        "--timeline", fixture.timelinePath]);
      runInteraction(["confirm", "--state", fixture.statePath,
        "--response", previewSummary(fixture.reviewId, "approve")]);
      if (mutation === "page") writeFileSync(fixture.reviewPage, `${readFileSync(fixture.reviewPage)}changed`);
      if (mutation === "style-page") {
        const state = readState(fixture.statePath);
        writeFileSync(state.reviewPage.path, `${readFileSync(state.reviewPage.path)}changed`);
      }
      if (mutation === "evidence") writeFileSync(fixture.evidence[0], "changed");
      if (mutation === "meta") writeFileSync(fixture.projectMetaPath, "{}");
      if (mutation === "signature") {
        const state = readState(fixture.statePath);
        state.approval.previewEvidenceSignature = "0".repeat(64);
        writeFileSync(fixture.statePath, JSON.stringify(state), "utf8");
      }
      const overridesPath = mutation === "override" ? join(tempRoot, "changed-overrides.json") : null;
      if (overridesPath) writeFileSync(overridesPath, "{}", "utf8");
      assert.throws(() => interactionState.validateGenerationInteraction({
        statePath: fixture.statePath,
        mode: "overlay",
        sourceVideo: sourcePath,
        captionsPath,
        requestedSelection: {
          preset: "clean", highlightTheme: null, backgroundTheme: null, strokeTheme: null, karaoke: "false",
        },
        overridesPath,
      }));
    }
  });

  const bindStyleDefinitionCopies = (statePath, name) => {
    const state = readState(statePath);
    const directory = join(tempRoot, `${name}-style-definitions`);
    mkdirSync(directory);
    state.styleDefinitions = state.styleDefinitions.map((binding) => {
      const path = join(directory, basename(binding.path));
      copyFileSync(binding.path, path);
      return { path: resolve(path), sha256: interactionState.hashFile(path) };
    });
    writeFileSync(statePath, JSON.stringify(state), "utf8");
    return state.styleDefinitions.map((binding) => binding.path);
  };

  check("maintained style definition mutations block preview and overlay validation", () => {
    for (const definitionName of ["caption-styles.json", "preview-manifest.json"]) {
      const preview = preparePreview(`style-preview-${definitionName}`);
      const previewCopies = bindStyleDefinitionCopies(preview.statePath, `preview-${definitionName}`);
      const previewDefinition = previewCopies.find((path) => basename(path) === definitionName);
      writeFileSync(previewDefinition, `${readFileSync(previewDefinition, "utf8")}\n`);
      assert.throws(() => interactionState.validateGenerationInteraction({
        statePath: preview.statePath,
        mode: "preview",
        sourceVideo: sourcePath,
        captionsPath,
        requestedSelection: {
          preset: "clean", highlightTheme: null, backgroundTheme: null, strokeTheme: null, karaoke: "false",
        },
      }), /style definition/i);

      const overlay = preparePreview(`style-overlay-${definitionName}`);
      runInteraction(["preview-ready", "--state", overlay.statePath, "--project-meta", overlay.projectMetaPath,
        "--evidence", overlay.evidence.join(","), "--review-page", overlay.reviewPage,
        "--timeline", overlay.timelinePath]);
      runInteraction(["confirm", "--state", overlay.statePath,
        "--response", previewSummary(overlay.reviewId, "approve")]);
      const overlayCopies = bindStyleDefinitionCopies(overlay.statePath, `overlay-${definitionName}`);
      const overlayDefinition = overlayCopies.find((path) => basename(path) === definitionName);
      writeFileSync(overlayDefinition, `${readFileSync(overlayDefinition, "utf8")}\n`);
      assert.throws(() => interactionState.validateGenerationInteraction({
        statePath: overlay.statePath,
        mode: "overlay",
        sourceVideo: sourcePath,
        captionsPath,
        requestedSelection: {
          preset: "clean", highlightTheme: null, backgroundTheme: null, strokeTheme: null, karaoke: "false",
        },
      }), /style definition/i);
    }
  });

  check("timeline mutation after preview approval blocks overlay validation", () => {
    const fixture = preparePreview("timeline-mutation");
    runInteraction(["preview-ready", "--state", fixture.statePath, "--project-meta", fixture.projectMetaPath,
      "--evidence", fixture.evidence.join(","), "--review-page", fixture.reviewPage,
      "--timeline", fixture.timelinePath]);
    runInteraction(["confirm", "--state", fixture.statePath,
      "--response", previewSummary(fixture.reviewId, "approve")]);
    writeFileSync(fixture.timelinePath, '{"schema_version":1,"timeline_id":"main","changed":true}\n', "utf8");
    assert.throws(() => interactionState.validateGenerationInteraction({
      statePath: fixture.statePath,
      mode: "overlay",
      sourceVideo: sourcePath,
      captionsPath,
      requestedSelection: {
        preset: "clean", highlightTheme: null, backgroundTheme: null, strokeTheme: null, karaoke: "false",
      },
    }), /timeline/i);
  });

  check("legacy unbound v1 status and generation validation normalize derived approval bindings", () => {
    const statePath = join(tempRoot, "legacy-v1-state.json");
    const projectMetaPath = join(tempRoot, "legacy-v1-project-meta.json");
    const evidence = ["early", "middle", "late", "no-caption"].map((label) => {
      const path = join(tempRoot, `legacy-v1-${label}.png`);
      writeFileSync(path, tinyPng());
      return { path: resolve(path), sha256: interactionState.hashFile(path) };
    });
    const evidenceSignature = interactionState.hashJson(evidence);
    writeFileSync(projectMetaPath, "{}\n", "utf8");
    writeFileSync(statePath, JSON.stringify({
      schemaVersion: 1,
      skill: "video-add-captions",
      decisionMode: "human",
      phase: "render_approved",
      sourceVideo: { path: resolve(sourcePath), sha256: interactionState.hashFile(sourcePath) },
      captions: { path: resolve(captionsPath), sha256: interactionState.hashFile(captionsPath) },
      selection: {
        choiceId: "clean",
        preset: "clean",
        highlightTheme: null,
        backgroundTheme: null,
        strokeTheme: null,
        karaoke: false,
        actor: "human",
      },
      preview: {
        projectMetaPath: resolve(projectMetaPath),
        projectMetaSha256: interactionState.hashFile(projectMetaPath),
        overridesSha256: null,
        reviewPagePath: null,
        reviewPageSha256: null,
        evidence,
        evidenceSignature,
      },
      approval: { actor: "human", response: "legacy approval" },
      history: [],
    }), "utf8");

    const status = runInteraction(["status", "--state", statePath]);
    assert.equal(JSON.parse(status.stdout).approved, true);
    const validated = interactionState.validateGenerationInteraction({
      statePath,
      mode: "overlay",
      sourceVideo: sourcePath,
      captionsPath,
      requestedSelection: {
        preset: "clean", highlightTheme: null, backgroundTheme: null, strokeTheme: null, karaoke: "false",
      },
    });
    assert.equal(validated.state.approval.selectionId, "clean");
    assert.equal(validated.state.approval.previewEvidenceSignature, evidenceSignature);
  });

  check("bound v1 state cannot omit maintained style definitions", () => {
    const fixture = preparePreview("bound-missing-style-definitions");
    const state = readState(fixture.statePath);
    delete state.styleDefinitions;
    writeFileSync(fixture.statePath, JSON.stringify(state), "utf8");
    assert.throws(() => interactionState.validateGenerationInteraction({
      statePath: fixture.statePath,
      mode: "preview",
      sourceVideo: sourcePath,
      captionsPath,
      requestedSelection: {
        preset: "clean", highlightTheme: null, backgroundTheme: null, strokeTheme: null, karaoke: "false",
      },
    }), /style definition/i);
  });
} finally {
  rmSync(tempRoot, { recursive: true, force: true });
}

assert.deepEqual(failures, [], `[caption-interaction] failures:\n- ${failures.join("\n- ")}`);
console.log("[caption-interaction] all checks passed");
