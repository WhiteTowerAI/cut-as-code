import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join, resolve } from "node:path";
import {
  assertCompositeEvidenceCoverage,
  assertRepresentativeEvidence,
  assertPreviewBindings,
  assertExpressiveTreatmentsBinding,
  assertReviewPageBinding,
  assertSpatialContextBinding,
  assertStyleDefinitionBindings,
  createSpatialContextBinding,
  galleryAssetFiles,
  galleryPath,
  hashFile,
  hashJson,
  parseCaptionPreviewApproval,
  parseCaptionPreviewRevision,
  parseCaptionStyleSummary,
  readInteractionState,
  resolveGallerySelection,
  styleDefinitionPaths,
} from "./caption_interaction_state.mjs";

const rawArgs = process.argv.slice(2);
const command = rawArgs.shift();

const usage = `Usage:
  node caption_interaction.mjs start --state <json> --source <video> --captions <json> [--spatial-context <json>] [--review-dir <dir>] [--decision-mode human|agent] [--delegation-note <text>] [--no-open true] [--force true]
  node caption_interaction.mjs select --state <json> --response <copied-summary|combination-id|skip>
  node caption_interaction.mjs agent-select --state <json> --choice <combination-id> --rationale <text>
  node caption_interaction.mjs preview-ready --state <json> --project-meta <json> --evidence <png1,png2,...> [--evidence-document <captions-evidence.json>] [--comparison-evidence <semantic.png,karaoke.png>] [--review-page <html> --timeline <timeline.json>]
  node caption_interaction.mjs adjust --state <json> --response <copied-summary|user-feedback>
  node caption_interaction.mjs confirm --state <json> --response <copied-summary|approve>
  node caption_interaction.mjs agent-confirm --state <json> [--karaoke on|off] --rationale <text>
  node caption_interaction.mjs status --state <json>`;

const standaloneApprovalResponses = new Set(["approve", "确认渲染"]);
const isStandaloneApproval = (response) => standaloneApprovalResponses.has(response);

const parseArgs = (args) => {
  const parsed = {};
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (!arg.startsWith("--")) {
      throw new Error(`Unexpected argument: ${arg}`);
    }
    const value = args[index + 1];
    if (!value || value.startsWith("--")) {
      throw new Error(`Missing value for ${arg}`);
    }
    const key = arg.slice(2).replaceAll(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    parsed[key] = value;
    index += 1;
  }
  return parsed;
};

const now = () => new Date().toISOString();
const writeState = (statePath, state) => {
  const path = resolve(statePath);
  const temporaryPath = join(dirname(path), `.${basename(path)}.${randomUUID()}.tmp`);
  try {
    writeFileSync(temporaryPath, `${JSON.stringify(state, null, 2)}\n`, "utf8");
    renameSync(temporaryPath, path);
  } catch (error) {
    if (existsSync(temporaryPath)) rmSync(temporaryPath, { force: true });
    throw error;
  }
};

const nextQuestion = (state) => {
  if (state.phase === "awaiting_style_selection") {
    if (state.reviewPage) {
      if (state.decisionMode === "agent") {
        return [
          `Caption style review: ${state.reviewPage.path}`,
          "Inspect the maintained gallery and record one choice with agent-select.",
          "STOP: Do not continue until the gallery has been inspected and a rationale is ready.",
        ].join("\n");
      }
      return [
        `Caption style review: ${state.reviewPage.path}`,
        "Ask the user to select one style and use Copy summary.",
        "Pass the copied summary unchanged to select --response.",
        "STOP: Wait for the user's exact copied summary before continuing.",
      ].join("\n");
    }
    if (state.decisionMode === "agent") {
      return "Agent decision mode is active. Inspect the maintained gallery and record one choice with agent-select.";
    }
    return [
      `Caption style gallery: ${state.galleryPath}`,
      "Inspect the maintained gallery and reply with one combination ID, for example pill-yellow.",
      'Reply exactly "skip" to use the default clean style.',
      "STOP: Wait for a valid combination ID or an explicit skip response before continuing.",
    ].join("\n");
  }
  if (state.phase === "style_selected") {
    return `Caption style ${state.selection.choiceId} is recorded. Generate only a source-backed preview before rendering the complete caption overlay.`;
  }
  if (state.phase === "awaiting_preview_confirmation") {
    if (state.decisionMode === "agent") {
      return "Agent decision mode is active. Inspect every source-backed preview and record the rationale with agent-confirm.";
    }
    if (state.preview?.reviewPagePath) {
      return [
        `Caption preview review: ${state.preview.reviewPagePath}`,
        "Inspect every required preview in the bound review page and use Copy summary.",
        "Pass an approval summary unchanged to confirm --response, or a revision summary unchanged to adjust --response.",
        "STOP: Do not render the complete caption overlay until an exact copied approval summary is recorded.",
      ].join("\n");
    }
    return [
      "Inspect the source-backed caption preview.",
      'Reply exactly "approve" to approve the full caption overlay, or describe the required adjustment.',
      'STOP: Do not render the complete caption overlay until an explicit "approve" response is recorded.',
    ].join("\n");
  }
  return state.decisionMode === "agent"
    ? "Delegated Agent approval is recorded; the complete caption overlay may be rendered."
    : "Human approval is recorded; the complete caption overlay may be rendered.";
};

const appendHistory = (state, event, details = {}) => {
  state.history.push({ event, at: now(), ...details });
};

const openGallery = (path) => {
  const escapedPath = path.replaceAll("'", "''");
  execFileSync("powershell.exe", [
    "-NoProfile",
    "-Command",
    `Start-Process -FilePath '${escapedPath}'`,
  ], { stdio: "ignore" });
};

const requireOption = (options, key) => {
  if (!options[key]) {
    throw new Error(`Missing required option --${key.replaceAll(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}`);
  }
  return options[key];
};

const readBoundInteractionState = (statePath) => {
  const loaded = readInteractionState(statePath);
  assertSpatialContextBinding(loaded.state);
  return loaded;
};

const reviewMarker = "__CAPTION_STYLE_REVIEW_DATA__";
const galleryBase = '<base href="./">';
const createReviewPage = (reviewDirectory, context, force) => {
  const directory = resolve(reviewDirectory);
  mkdirSync(directory, { recursive: true });
  const aliasPath = join(directory, "captions-style-review.html");
  const existingReview = readdirSync(directory).find((name) => /^captions-style-review-[0-9a-f-]+\.html$/i.test(name));
  if ((existsSync(aliasPath) || existingReview) && !force) {
    throw new Error(`Caption style review already exists in ${directory}. Use --force true to replace it deliberately.`);
  }
  const pagePath = join(directory, `captions-style-review-${context.review_id}.html`);
  const sourceHtml = readFileSync(galleryPath, "utf8");
  if (sourceHtml.split(reviewMarker).length !== 2) {
    throw new Error(`Caption style gallery must contain exactly one ${reviewMarker} marker.`);
  }
  if (sourceHtml.split(galleryBase).length !== 2) {
    throw new Error("Caption style gallery must contain exactly one relative base element.");
  }
  const payload = Buffer.from(JSON.stringify(context), "utf8").toString("base64");
  const assetDirectoryName = `captions-style-review-assets-${context.review_id}`;
  const assetDirectory = join(directory, assetDirectoryName);
  const stagedAssetDirectory = join(directory, `.${assetDirectoryName}.tmp`);
  const stagedPagePath = join(directory, `.captions-style-review-${context.review_id}.tmp`);
  let assetsPublished = false;
  try {
    mkdirSync(stagedAssetDirectory);
    for (const fileName of galleryAssetFiles) {
      copyFileSync(join(dirname(galleryPath), fileName), join(stagedAssetDirectory, fileName));
    }
    const pageHtml = sourceHtml
      .replace(reviewMarker, payload)
      .replace(galleryBase, `<base href="./${assetDirectoryName}/">`);
    writeFileSync(stagedPagePath, pageHtml, "utf8");
    const pageSha256 = hashFile(stagedPagePath);
    const assetHashes = new Map(galleryAssetFiles.map((fileName) => [
      fileName,
      hashFile(join(stagedAssetDirectory, fileName)),
    ]));

    renameSync(stagedAssetDirectory, assetDirectory);
    assetsPublished = true;
    renameSync(stagedPagePath, pagePath);
    return {
      path: pagePath,
      sha256: pageSha256,
      assets: galleryAssetFiles.map((fileName) => ({
        path: join(assetDirectory, fileName),
        sha256: assetHashes.get(fileName),
      })),
    };
  } catch (error) {
    if (existsSync(stagedPagePath)) rmSync(stagedPagePath, { force: true });
    if (existsSync(stagedAssetDirectory)) rmSync(stagedAssetDirectory, { recursive: true, force: true });
    if (assetsPublished && existsSync(assetDirectory)) rmSync(assetDirectory, { recursive: true, force: true });
    throw error;
  }
};

const updateReviewAlias = (pagePath) => {
  const directory = dirname(pagePath);
  const aliasPath = join(directory, "captions-style-review.html");
  const temporaryPath = join(directory, `.captions-style-review.${randomUUID()}.tmp`);
  try {
    copyFileSync(pagePath, temporaryPath);
    renameSync(temporaryPath, aliasPath);
  } catch (error) {
    if (existsSync(temporaryPath)) rmSync(temporaryPath, { force: true });
    console.warn(`[caption-interaction] warning: could not update latest review alias: ${error.message}`);
  }
};

const removePublishedReview = (reviewPage) => {
  if (!reviewPage) return;
  rmSync(reviewPage.path, { force: true });
  for (const directory of new Set(reviewPage.assets.map((asset) => dirname(asset.path)))) {
    rmSync(directory, { recursive: true, force: true });
  }
};

const requireDecisionMode = (state, expected, commandName) => {
  if ((state.decisionMode ?? "human") !== expected) {
    const required = state.decisionMode === "agent" ? `agent-${commandName}` : commandName;
    throw new Error(`${state.decisionMode ?? "human"} decision mode cannot use this command. Use ${required}.`);
  }
};

const requireRationale = (options) => {
  const rationale = requireOption(options, "rationale").trim();
  if (!rationale) {
    throw new Error("Agent decisions require a non-empty rationale.");
  }
  return rationale;
};

const readCaptionReviewPage = (
  pagePath, state, evidencePaths, comparisonEvidencePaths, timelineBinding, projectMetaPath,
  evidenceDocumentPath = null,
) => {
  const path = resolve(pagePath);
  if (!existsSync(path) || extname(path).toLowerCase() !== ".html") {
    throw new Error(`Caption preview review page must be an existing HTML file: ${path}`);
  }
  const html = readFileSync(path, "utf8");
  const matches = [...html.matchAll(/const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)";/g)];
  if (matches.length !== 1) throw new Error("Caption preview review page must contain exactly one base64 payload.");
  let payload;
  try {
    payload = JSON.parse(Buffer.from(matches[0][1], "base64").toString("utf8"));
  } catch {
    throw new Error("Caption preview review page payload is invalid.");
  }
  if (payload.schema_version !== 1 || payload.review_id !== state.reviewId) {
    throw new Error("Caption preview review page does not match the current review ID.");
  }
  if (payload.selection_id !== state.selection.choiceId) {
    throw new Error("Caption preview review page does not match the selected caption style.");
  }
  if (payload.timeline_id !== timelineBinding.timelineId
    || payload.timeline_sha256 !== timelineBinding.sha256) {
    throw new Error("Caption preview review page timeline differs from --timeline.");
  }
  if (payload.plan_sha256 && payload.plan_sha256 !== state.captions.sha256) {
    throw new Error("Caption preview review page plan differs from the current interaction.");
  }
  const presentationMode = payload.presentation_mode ?? "standard";
  const approvalEvidence = payload.approval_evidence ?? "standard-four";
  const representativeMode = approvalEvidence !== "standard-four" && Array.isArray(payload.review_samples);
  const primarySamples = representativeMode ? payload.review_samples : payload.samples;
  if (!Array.isArray(payload.samples) || !Array.isArray(primarySamples)
    || primarySamples.length !== evidencePaths.length) {
    throw new Error("Caption preview review page evidence count differs from --evidence.");
  }
  if (payload.primary_evidence_count !== undefined
    && payload.primary_evidence_count !== primarySamples.length) {
    throw new Error("Caption preview review page primary evidence count is invalid.");
  }
  if (payload.machine_evidence_count !== undefined
    && payload.machine_evidence_count !== payload.samples.length) {
    throw new Error("Caption preview review page machine evidence count is invalid.");
  }
  let machineEvidence = null;
  if (representativeMode) {
    if (!evidenceDocumentPath || !existsSync(evidenceDocumentPath)
      || extname(evidenceDocumentPath).toLowerCase() !== ".json") {
      throw new Error("Representative caption review requires --evidence-document captions-evidence.json.");
    }
    const document = JSON.parse(readFileSync(evidenceDocumentPath, "utf8"));
    for (const field of ["timeline_id", "timeline_sha256", "samples", "review_samples",
      "machine_evidence_count", "primary_evidence_count"]) {
      if (JSON.stringify(document[field]) !== JSON.stringify(payload[field])) {
        throw new Error(`Caption machine evidence document differs from the review page at ${field}.`);
      }
    }
    assertRepresentativeEvidence(payload.samples, primarySamples);
    machineEvidence = {
      path: evidenceDocumentPath,
      sha256: hashFile(evidenceDocumentPath),
      sampleCount: payload.samples.length,
    };
  }
  if (approvalEvidence === "composite-aware") {
    const context = assertSpatialContextBinding(state);
    if (!payload.spatial_context
      || payload.spatial_context.sha256 !== state.spatialContext?.sha256
      || payload.spatial_context.source?.operation_revision !== state.spatialContext?.sourceRevision) {
      throw new Error("Composite-aware caption review page spatial binding is stale.");
    }
    const labels = payload.samples.map((sample) => sample.label);
    if (labels.length === 0 || new Set(labels).size !== labels.length || !labels.includes("no-caption")) {
      throw new Error("Composite-aware caption review requires unique dynamic evidence and no-caption.");
    }
    assertCompositeEvidenceCoverage(context, payload.samples);
    const plan = JSON.parse(readFileSync(state.captions.path, "utf8"));
    const heroCueIndexes = (plan.cues ?? []).filter((cue) => cue.hero_line).map((cue) => cue.index);
    if (heroCueIndexes.some((cueIndex) => !payload.samples.some(
      (sample) => sample.cue_index === cueIndex && sample.hero_line,
    ))) {
      throw new Error("Composite-aware caption review does not cover every hero-line cue.");
    }
    if (payload.samples.some((sample) => sample.clearance_status !== "pass")) {
      throw new Error("Composite-aware caption review contains failed or missing clearance evidence.");
    }
    if (presentationMode === "expressive") {
      const comparison = payload.experimental_comparison;
      if (!comparison?.experimental || comparisonEvidencePaths.length !== 2
        || comparison.samples?.length !== 2
        || comparison.samples[0]?.mode !== "semantic-only" || comparison.samples[0]?.karaoke !== false
        || comparison.samples[1]?.mode !== "semantic-plus-karaoke" || comparison.samples[1]?.karaoke !== true) {
        throw new Error("Expressive caption preview page must bind the separate coexistence comparison pair.");
      }
      const projectBinding = comparison.project_binding;
      if (!projectBinding
        || resolve(projectBinding.primary_project_meta) !== projectMetaPath
        || projectBinding.primary_project_meta_sha256 !== hashFile(projectMetaPath)
        || !existsSync(projectBinding.comparison_project_meta)
        || projectBinding.comparison_project_meta_sha256 !== hashFile(projectBinding.comparison_project_meta)) {
        throw new Error("Expressive comparison project metadata binding is invalid.");
      }
    } else if (comparisonEvidencePaths.length) {
      throw new Error("Standard composite-aware review must not bind Expressive comparison evidence.");
    }
  } else if (presentationMode === "standard") {
    const labels = ["early", "middle", "late", "no-caption"];
    if (approvalEvidence !== "standard-four" || payload.samples.length !== labels.length
      || payload.samples.some((sample, index) => sample.label !== labels[index])
      || comparisonEvidencePaths.length) {
      throw new Error("Caption preview review page must bind early, middle, late, and no-caption evidence.");
    }
  } else if (presentationMode === "expressive") {
    const plan = JSON.parse(readFileSync(state.captions.path, "utf8"));
    const beats = plan.presentation?.mode === "expressive" ? plan.presentation.layout_beats : null;
    if (approvalEvidence !== "expressive-layout-beats" || !Array.isArray(beats)
      || !payload.samples.some((sample) => sample.label === "no-caption")) {
      throw new Error("Expressive caption preview page must bind every layout beat plus no-caption.");
    }
    beats.forEach((beat) => {
      const sample = payload.samples.find((item) => item.beat_id === beat.id);
      if (!sample || sample.kind !== "layout-beat" || sample.label !== beat.id || sample.beat_id !== beat.id
        || sample.variant !== beat.variant || JSON.stringify(sample.cue_ids) !== JSON.stringify(beat.cue_ids)) {
        throw new Error(`Expressive caption preview page differs at layout beat ${beat.id}.`);
      }
    });
    const heroCueIndexes = (plan.cues ?? []).filter((cue) => cue.hero_line).map((cue) => cue.index);
    if (heroCueIndexes.some((cueIndex) => !payload.samples.some(
      (sample) => sample.cue_index === cueIndex && sample.hero_line,
    ))) {
      throw new Error("Expressive caption preview page does not cover every hero-line cue.");
    }
    const comparison = payload.experimental_comparison;
    if (!comparison?.experimental || comparisonEvidencePaths.length !== 2
      || comparison.samples?.length !== 2
      || comparison.samples[0]?.mode !== "semantic-only" || comparison.samples[0]?.karaoke !== false
      || comparison.samples[1]?.mode !== "semantic-plus-karaoke" || comparison.samples[1]?.karaoke !== true) {
      throw new Error("Expressive caption preview page must bind the separate coexistence comparison pair.");
    }
    const projectBinding = comparison.project_binding;
    if (!projectBinding
      || resolve(projectBinding.primary_project_meta) !== projectMetaPath
      || projectBinding.primary_project_meta_sha256 !== hashFile(projectMetaPath)
      || !existsSync(projectBinding.comparison_project_meta)
      || projectBinding.comparison_project_meta_sha256 !== hashFile(projectBinding.comparison_project_meta)) {
      throw new Error("Expressive comparison project metadata binding is invalid.");
    }
  } else {
    throw new Error(`Unsupported caption preview presentation mode: ${presentationMode}`);
  }
  const evidence = primarySamples.map((sample, index) => {
    const evidencePath = evidencePaths[index];
    if (resolve(dirname(path), sample.preview) !== evidencePath || sample.sha256 !== hashFile(evidencePath)) {
      throw new Error(`Caption preview review page evidence differs at ${sample.sample_label ?? sample.label}.`);
    }
    return {
      label: sample.sample_label ?? sample.label,
      sampleLabel: sample.sample_label ?? sample.label,
      path: evidencePath,
      sha256: sample.sha256,
      categories: sample.categories ?? [],
      kind: sample.kind,
      cueIndex: sample.cue_index ?? null,
      purposes: sample.purposes ?? [],
      ...(sample.clearance_status !== undefined ? { clearanceStatus: sample.clearance_status } : {}),
      ...(sample.beat_id ? { beatId: sample.beat_id, variant: sample.variant } : {}),
      ...(sample.spatial_beat_id ? {
        spatialBeatId: sample.spatial_beat_id,
        visualContext: sample.visual_context,
        requestedVariant: sample.requested_variant,
        resolvedPlacement: sample.resolved_placement,
        backgroundSha256: sample.background_sha256,
        captionBbox: sample.caption_bbox,
        heroBbox: sample.hero_bbox,
      } : {}),
      ...(sample.hero_line ? { heroLine: sample.hero_line } : {}),
    };
  });
  const comparisonEvidence = presentationMode === "expressive"
    ? payload.experimental_comparison.samples.map((sample, index) => {
      const evidencePath = comparisonEvidencePaths[index];
      if (resolve(dirname(path), sample.preview) !== evidencePath || sample.sha256 !== hashFile(evidencePath)) {
        throw new Error(`Caption preview comparison evidence differs at ${sample.mode}.`);
      }
      return { mode: sample.mode, path: evidencePath, sha256: sample.sha256 };
    })
    : null;
  return {
    path,
    sha256: hashFile(path),
    evidence,
    machineEvidence,
    comparisonEvidence,
    presentationMode,
    approvalEvidence,
    timelineId: payload.timeline_id,
    timelineSha256: payload.timeline_sha256,
  };
};

const readPngDimensions = (path) => {
  const bytes = readFileSync(path);
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (bytes.length < 57 || !bytes.subarray(0, 8).equals(signature)) {
    throw new Error(`Preview evidence is not a valid PNG: ${path}`);
  }
  let offset = 8;
  let first = true;
  let width = 0;
  let height = 0;
  let hasImageData = false;
  let hasEnd = false;
  while (offset + 12 <= bytes.length) {
    const length = bytes.readUInt32BE(offset);
    const end = offset + 12 + length;
    if (end > bytes.length) throw new Error(`Preview PNG has a truncated chunk: ${path}`);
    const type = bytes.toString("ascii", offset + 4, offset + 8);
    if (first) {
      if (type !== "IHDR" || length !== 13) throw new Error(`Preview PNG must start with IHDR: ${path}`);
      width = bytes.readUInt32BE(offset + 8);
      height = bytes.readUInt32BE(offset + 12);
      if (!width || !height) throw new Error(`Preview PNG dimensions must be positive: ${path}`);
      first = false;
    } else if (type === "IDAT" && length > 0) {
      hasImageData = true;
    } else if (type === "IEND" && length === 0) {
      hasEnd = true;
      break;
    }
    offset = end;
  }
  if (!hasImageData || !hasEnd) throw new Error(`Preview PNG is missing image data or IEND: ${path}`);
  return { width, height };
};

try {
  const options = parseArgs(rawArgs);
  if (command === "start") {
    const statePath = resolve(requireOption(options, "state"));
    const sourceVideo = resolve(requireOption(options, "source"));
    const captions = resolve(requireOption(options, "captions"));
    if (!existsSync(sourceVideo) || !existsSync(captions)) {
      throw new Error("Source video and captions JSON must exist before the interaction starts.");
    }
    if (existsSync(statePath) && options.force !== "true") {
      throw new Error(`Interaction state already exists: ${statePath}. Use --force true to restart deliberately.`);
    }
    const decisionMode = options.decisionMode ?? "human";
    if (!new Set(["human", "agent"]).has(decisionMode)) {
      throw new Error("--decision-mode must be human or agent.");
    }
    const delegationNote = String(options.delegationNote ?? "").trim();
    if (decisionMode === "agent" && !delegationNote) {
      throw new Error("Agent decision mode requires --delegation-note.");
    }
    const spatialContext = createSpatialContextBinding(captions, options.spatialContext);

    const reviewId = randomUUID();
    const reviewPage = options.reviewDir
      ? createReviewPage(options.reviewDir, {
        schema_version: 1,
        review_id: reviewId,
        source_name: basename(sourceVideo),
        decision_mode: decisionMode,
        default_choice: "clean",
      }, options.force === "true")
      : null;

    const state = {
      schemaVersion: 1,
      skill: "video-add-captions",
      decisionMode,
      delegationNote: delegationNote || null,
      phase: "awaiting_style_selection",
      createdAt: now(),
      updatedAt: now(),
      reviewId,
      reviewPage,
      galleryPath: reviewPage?.path ?? galleryPath,
      sourceVideo: { path: sourceVideo, sha256: hashFile(sourceVideo) },
      captions: { path: captions, sha256: hashFile(captions) },
      spatialContext,
      styleDefinitions: styleDefinitionPaths.map((path) => ({ path, sha256: hashFile(path) })),
      selection: null,
      preview: null,
      approval: null,
      history: [],
    };
    assertSpatialContextBinding(state);
    appendHistory(state, "interaction_started", {
      decisionMode,
      spatialContextSha256: spatialContext?.sha256 ?? null,
    });
    try {
      writeState(statePath, state);
    } catch (error) {
      removePublishedReview(reviewPage);
      throw error;
    }
    if (reviewPage) updateReviewAlias(reviewPage.path);
    if (options.noOpen !== "true") {
      openGallery(state.galleryPath);
    }
    console.log(nextQuestion(state));
    console.log(`[caption-interaction] state=${statePath}`);
  } else if (command === "select") {
    const statePath = requireOption(options, "state");
    const { state } = readBoundInteractionState(statePath);
    requireDecisionMode(state, "human", "select");
    if (!new Set(["awaiting_style_selection", "style_selected"]).has(state.phase)) {
      throw new Error(`Style selection is not allowed during phase ${state.phase}.`);
    }
    const response = requireOption(options, "response");
    if (state.reviewPage) {
      assertReviewPageBinding(state);
    }
    const selection = state.reviewPage
      ? resolveGallerySelection(parseCaptionStyleSummary(response, state.reviewId).choiceId)
      : resolveGallerySelection(response);
    if (state.reviewPage) selection.response = response.trim();
    state.phase = "style_selected";
    state.updatedAt = now();
    state.selection = { ...selection, actor: "human", recordedAt: now() };
    state.preview = null;
    state.approval = null;
    appendHistory(state, "style_selected", {
      response: selection.response,
      choiceId: selection.choiceId,
      skipped: selection.skipped,
    });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "agent-select") {
    const statePath = requireOption(options, "state");
    const { state } = readBoundInteractionState(statePath);
    requireDecisionMode(state, "agent", "select");
    if (!new Set(["awaiting_style_selection", "style_selected"]).has(state.phase)) {
      throw new Error(`Agent style selection is not allowed during phase ${state.phase}.`);
    }
    const rationale = requireRationale(options);
    if (state.reviewPage) {
      assertReviewPageBinding(state);
    }
    const { response: _response, ...selection } = resolveGallerySelection(requireOption(options, "choice"));
    state.phase = "style_selected";
    state.updatedAt = now();
    state.selection = { ...selection, actor: "agent", rationale, recordedAt: now() };
    state.preview = null;
    state.approval = null;
    appendHistory(state, "style_selected", {
      actor: "agent",
      choiceId: selection.choiceId,
      rationale,
    });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "preview-ready") {
    const statePath = requireOption(options, "state");
    const { state, statePath: resolvedStatePath } = readBoundInteractionState(statePath);
    if (state.phase !== "style_selected") {
      throw new Error(`Preview evidence can only be recorded during phase style_selected. Current phase: ${state.phase}`);
    }
    const projectMetaPath = resolve(requireOption(options, "projectMeta"));
    const evidencePaths = requireOption(options, "evidence")
      .split(",")
      .map((value) => resolve(value.trim()))
      .filter(Boolean);
    const comparisonEvidencePaths = String(options.comparisonEvidence ?? "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean)
      .map((value) => resolve(value));
    const evidenceDocumentPath = options.evidenceDocument
      ? resolve(options.evidenceDocument) : null;
    const boundReview = Boolean(state.reviewPage);
    if ((boundReview && evidencePaths.length < 1) || (!boundReview && evidencePaths.length < 4)) {
      throw new Error("At least four preview screenshots are required: early, middle, late, and no-caption.");
    }
    const dimensions = [...evidencePaths, ...comparisonEvidencePaths].map((evidencePath) => {
      if (!existsSync(evidencePath) || extname(evidencePath).toLowerCase() !== ".png") {
        throw new Error(`Preview evidence must be an existing PNG: ${evidencePath}`);
      }
      return readPngDimensions(evidencePath);
    });
    if (dimensions.some(({ width, height }) => width !== dimensions[0].width || height !== dimensions[0].height)) {
      throw new Error("All caption preview evidence PNGs must have identical dimensions.");
    }
    assertStyleDefinitionBindings(state);
    let timelineBinding = null;
    if (boundReview) {
      const timelinePath = resolve(requireOption(options, "timeline"));
      if (!existsSync(timelinePath) || extname(timelinePath).toLowerCase() !== ".json") {
        throw new Error(`Caption preview timeline must be an existing JSON file: ${timelinePath}`);
      }
      const timeline = JSON.parse(readFileSync(timelinePath, "utf8"));
      const captionsPlan = JSON.parse(readFileSync(state.captions.path, "utf8"));
      if (hashFile(state.captions.path) !== state.captions.sha256) {
        throw new Error("Captions JSON changed after the interaction started. Start a new interaction.");
      }
      if (!timeline.timeline_id || timeline.timeline_id !== captionsPlan.timeline_id) {
        throw new Error("Caption preview timeline_id must match the bound captions plan timeline_id.");
      }
      timelineBinding = {
        path: timelinePath,
        sha256: hashFile(timelinePath),
        timelineId: timeline.timeline_id,
      };
    }
    const projectMeta = JSON.parse(readFileSync(projectMetaPath, "utf8"));
    if (resolve(projectMeta.interaction?.statePath ?? "") !== resolvedStatePath) {
      throw new Error("Preview project metadata is not bound to this interaction state.");
    }
    if (projectMeta.interaction?.selectionId !== state.selection.choiceId) {
      throw new Error("Preview project selection differs from the user's recorded selection.");
    }
    if ((projectMeta.spatialContext?.sha256 ?? null) !== (state.spatialContext?.sha256 ?? null)) {
      throw new Error("Preview project spatial context differs from the interaction binding.");
    }
    if (projectMeta.interaction?.reviewId && projectMeta.interaction.reviewId !== state.reviewId) {
      throw new Error("Preview project review ID differs from the current interaction.");
    }
    const previewPlan = JSON.parse(readFileSync(state.captions.path, "utf8"));
    if (previewPlan.presentation?.mode === "expressive") {
      assertExpressiveTreatmentsBinding(projectMeta);
    }
    let reviewBinding = null;
    let evidenceBindings;
    if (boundReview) {
      assertReviewPageBinding(state);
      reviewBinding = readCaptionReviewPage(
        requireOption(options, "reviewPage"), state, evidencePaths, comparisonEvidencePaths,
        timelineBinding, projectMetaPath, evidenceDocumentPath,
      );
      evidenceBindings = reviewBinding.evidence;
    } else {
      evidenceBindings = evidencePaths.map((path) => ({ path, sha256: hashFile(path) }));
    }

    state.phase = "awaiting_preview_confirmation";
    state.updatedAt = now();
    state.preview = {
      recordedAt: now(),
      projectMetaPath,
      projectMetaSha256: hashFile(projectMetaPath),
      overridesSha256: projectMeta.interaction.overridesSha256 ?? null,
      spatialContextSha256: state.spatialContext?.sha256 ?? null,
      timeline: timelineBinding,
      reviewPagePath: reviewBinding?.path ?? null,
      reviewPageSha256: reviewBinding?.sha256 ?? null,
      evidence: evidenceBindings,
      evidenceSignature: hashJson(evidenceBindings),
      machineEvidence: reviewBinding?.machineEvidence ?? null,
      presentationMode: reviewBinding?.presentationMode ?? "standard",
      approvalEvidence: reviewBinding?.approvalEvidence ?? "standard-four",
      comparisonEvidence: reviewBinding?.comparisonEvidence ?? null,
      comparisonEvidenceSignature: reviewBinding?.comparisonEvidence
        ? hashJson(reviewBinding.comparisonEvidence) : null,
    };
    state.approval = null;
    appendHistory(state, "preview_presented", {
      evidenceCount: evidencePaths.length,
      machineEvidenceCount: reviewBinding?.machineEvidence?.sampleCount ?? evidencePaths.length,
      comparisonEvidenceCount: comparisonEvidencePaths.length,
    });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "adjust") {
    const statePath = requireOption(options, "state");
    const { state } = readBoundInteractionState(statePath);
    if (state.phase !== "awaiting_preview_confirmation") {
      throw new Error(`Adjustment feedback is only accepted while awaiting preview confirmation. Current phase: ${state.phase}`);
    }
    requireDecisionMode(state, "human", "adjust");
    const response = requireOption(options, "response").trim();
    const revision = state.preview?.reviewPagePath
      ? parseCaptionPreviewRevision(response, state.reviewId)
      : { changes: response };
    if (!revision.changes
      || (!state.preview?.reviewPagePath && isStandaloneApproval(response))) {
      throw new Error("Adjustment feedback must describe a change and cannot equal a standalone approval token.");
    }
    state.phase = "style_selected";
    state.updatedAt = now();
    state.preview = null;
    state.approval = null;
    appendHistory(state, "preview_adjustment_requested", { response, changes: revision.changes });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "confirm") {
    const statePath = requireOption(options, "state");
    const { state } = readBoundInteractionState(statePath);
    requireDecisionMode(state, "human", "confirm");
    if (state.phase !== "awaiting_preview_confirmation") {
      throw new Error(`Render confirmation is only accepted after preview evidence. Current phase: ${state.phase}`);
    }
    const response = requireOption(options, "response").trim();
    let approvalDecision = null;
    if (state.preview?.reviewPagePath) {
      approvalDecision = parseCaptionPreviewApproval(
        response, state.reviewId, state.preview.approvalEvidence, state.preview.presentationMode,
      );
    } else if (!isStandaloneApproval(response)) {
      throw new Error('Standalone render approval requires the exact response "approve".');
    }
    assertPreviewBindings(state.preview, state);
    state.phase = "render_approved";
    state.updatedAt = now();
    state.approval = {
      response,
      actor: "human",
      recordedAt: now(),
      selectionId: state.selection.choiceId,
      previewEvidenceSignature: state.preview.evidenceSignature,
      machineEvidenceSha256: state.preview.machineEvidence?.sha256 ?? null,
      ...(approvalDecision?.karaoke !== undefined ? {
        karaoke: approvalDecision.karaoke,
        comparisonEvidenceSignature: state.preview.comparisonEvidenceSignature,
      } : {}),
    };
    appendHistory(state, "render_approved", { response });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "agent-confirm") {
    const statePath = requireOption(options, "state");
    const { state } = readBoundInteractionState(statePath);
    requireDecisionMode(state, "agent", "confirm");
    if (state.phase !== "awaiting_preview_confirmation") {
      throw new Error(`Agent render approval requires preview evidence. Current phase: ${state.phase}`);
    }
    const rationale = requireRationale(options);
    let karaoke = null;
    if (state.preview?.presentationMode === "expressive") {
      const karaokeOption = requireOption(options, "karaoke").trim();
      if (!new Set(["on", "off"]).has(karaokeOption)) {
        throw new Error('--karaoke must be exactly "on" or "off" for Expressive approval.');
      }
      karaoke = karaokeOption === "on";
    }
    assertPreviewBindings(state.preview, state);
    state.phase = "render_approved";
    state.updatedAt = now();
    state.approval = {
      actor: "agent",
      rationale,
      recordedAt: now(),
      selectionId: state.selection.choiceId,
      previewEvidenceSignature: state.preview.evidenceSignature,
      machineEvidenceSha256: state.preview.machineEvidence?.sha256 ?? null,
      ...(karaoke !== null ? {
        karaoke,
        comparisonEvidenceSignature: state.preview.comparisonEvidenceSignature,
      } : {}),
    };
    appendHistory(state, "render_approved", { actor: "agent", rationale });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "status") {
    const { state, statePath } = readBoundInteractionState(requireOption(options, "state"));
    console.log(JSON.stringify({
      statePath,
      decisionMode: state.decisionMode,
      phase: state.phase,
      selection: state.selection,
      previewEvidenceCount: state.preview?.evidence.length ?? 0,
      approved: state.phase === "render_approved",
      nextQuestion: nextQuestion(state),
    }, null, 2));
  } else {
    throw new Error(usage);
  }
} catch (error) {
  console.error(`[caption-interaction] ${error.message}`);
  if (!command) {
    console.error(usage);
  }
  process.exit(1);
}
