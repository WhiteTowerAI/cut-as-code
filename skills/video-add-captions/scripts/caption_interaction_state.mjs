import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const skillRoot = resolve(scriptDirectory, "..");
const manifestPath = join(skillRoot, "assets", "style-previews", "preview-manifest.json");
const styleConfigPath = join(skillRoot, "scripts", "caption-styles.json");

const readJson = (path) => JSON.parse(readFileSync(path, "utf8").replace(/^\uFEFF/, ""));

const manifest = readJson(manifestPath);
const galleryItems = manifest.groups.flatMap((group) => group.items);
const galleryById = new Map(galleryItems.map((item) => [item.id.toLowerCase(), item]));

export const galleryPath = join(skillRoot, "assets", "style-previews", "index.html");
export const validSelectionIds = galleryItems.map((item) => item.id);
export const galleryAssetFiles = galleryItems.flatMap((item) => [item.image, item.props]);
export const styleDefinitionPaths = [styleConfigPath, manifestPath];

export const hashFile = (path) => createHash("sha256")
  .update(readFileSync(resolve(path)))
  .digest("hex");

export const hashJson = (value) => createHash("sha256")
  .update(JSON.stringify(value))
  .digest("hex");

export const assertExpressiveTreatmentsBinding = (projectMeta) => {
  const binding = projectMeta?.expressiveTreatments;
  const currentValue = readJson(styleConfigPath).expressiveTreatments;
  if (!binding || resolve(binding.configPath ?? "") !== resolve(styleConfigPath)
    || binding.configSha256 !== hashFile(styleConfigPath)
    || !isDeepStrictEqual(binding.value, currentValue)) {
    throw new Error("Expressive treatment project metadata binding is stale.");
  }
  return currentValue;
};

export const resolveGallerySelection = (response) => {
  const rawResponse = String(response ?? "").trim();
  const normalized = rawResponse.toLowerCase();

  if (normalized === "跳过" || normalized === "skip") {
    const clean = galleryById.get("clean");
    return {
      response: rawResponse,
      choiceId: "clean",
      skipped: true,
      preset: clean.preset,
      highlightTheme: null,
      backgroundTheme: null,
      strokeTheme: null,
      karaoke: Boolean(clean.karaoke),
    };
  }

  const item = galleryById.get(normalized);
  if (!item) {
    throw new Error(
      `Style response must be one exact gallery combination ID or the exact word \"skip\". Received: ${rawResponse || "<empty>"}`,
    );
  }

  return {
    response: rawResponse,
    choiceId: item.id,
    skipped: false,
    preset: item.preset,
    highlightTheme: item.themeType === "highlight" ? item.theme : null,
    backgroundTheme: item.themeType === "background" ? item.theme : null,
    strokeTheme: item.themeType === "stroke" ? item.theme : null,
    karaoke: Boolean(item.karaoke),
  };
};

export const parseCaptionStyleSummary = (response, expectedReviewId) => {
  const lines = String(response ?? "").trim().split(/\r?\n/);
  if (lines.shift()?.trim().toLowerCase() !== "caption style review") {
    throw new Error('Caption style response must start with "Caption style review".');
  }

  const fields = new Map();
  for (const line of lines) {
    const separator = line.indexOf(":");
    const name = separator >= 0 ? line.slice(0, separator).trim().toLowerCase() : "";
    const value = separator >= 0 ? line.slice(separator + 1).trim() : "";
    if (!new Set(["review", "decision", "choice"]).has(name)) {
      throw new Error(`Unknown caption style response field: ${name || line.trim() || "<empty>"}`);
    }
    if (fields.has(name)) {
      throw new Error(`Duplicate caption style response field: ${name}`);
    }
    fields.set(name, value);
  }

  const missing = ["review", "decision", "choice"].filter((name) => !fields.get(name));
  if (missing.length) {
    throw new Error(`Missing caption style response fields: ${missing.join(", ")}`);
  }
  if (fields.get("review") !== expectedReviewId) {
    throw new Error("Caption style response review ID does not match the current interaction.");
  }
  if (fields.get("decision") !== "select") {
    throw new Error('Caption style response Decision must be exactly "select".');
  }
  const choiceId = fields.get("choice");
  if (!validSelectionIds.includes(choiceId)) {
    throw new Error(`Caption style response Choice must be one valid combination ID. Received: ${choiceId}`);
  }
  return { reviewId: fields.get("review"), decision: fields.get("decision"), choiceId };
};

const parseSummaryFields = (response, title, allowedFields) => {
  const lines = String(response ?? "").trim().split(/\r?\n/);
  if (lines.shift()?.trim().toLowerCase() !== title.toLowerCase()) {
    throw new Error(`Caption preview response must start with "${title}".`);
  }
  const fields = new Map();
  for (const line of lines) {
    const separator = line.indexOf(":");
    const name = separator >= 0 ? line.slice(0, separator).trim().toLowerCase() : "";
    const value = separator >= 0 ? line.slice(separator + 1).trim() : "";
    if (!allowedFields.includes(name)) {
      throw new Error(`Unknown caption preview response field: ${name || line.trim() || "<empty>"}`);
    }
    if (fields.has(name)) throw new Error(`Duplicate caption preview response field: ${name}`);
    fields.set(name, value);
  }
  const missing = allowedFields.filter((name) => !fields.get(name));
  if (missing.length) throw new Error(`Missing caption preview response fields: ${missing.join(", ")}`);
  return fields;
};

const assertPreviewReview = (fields, expectedReviewId, decision) => {
  if (fields.get("review") !== expectedReviewId) {
    throw new Error("Caption preview response review ID does not match the current interaction.");
  }
  if (fields.get("decision") !== decision) {
    throw new Error(`Caption preview response Decision must be exactly "${decision}".`);
  }
};

export const parseCaptionPreviewApproval = (
  response, expectedReviewId, expectedEvidence = "standard-four", presentationMode = "standard",
) => {
  const expressive = presentationMode === "expressive" || expectedEvidence === "expressive-layout-beats";
  const fields = parseSummaryFields(
    response, "Caption preview review",
    expressive ? ["review", "decision", "evidence", "karaoke"] : ["review", "decision", "evidence"],
  );
  assertPreviewReview(fields, expectedReviewId, "approve");
  if (expectedEvidence === "composite-aware") {
    if (fields.get("evidence").trim().toLowerCase() !== "composite-aware") {
      throw new Error('Composite-aware caption approval Evidence must be exactly "composite-aware".');
    }
    let karaoke;
    if (expressive) {
      karaoke = fields.get("karaoke").trim();
      if (!new Set(["on", "off"]).has(karaoke)) {
        throw new Error('Expressive caption preview approval Karaoke must be exactly "on" or "off".');
      }
    }
    return {
      reviewId: fields.get("review"), decision: "approve",
      evidence: ["composite-aware"],
      ...(expressive ? { karaoke: karaoke === "on" } : {}),
    };
  }
  if (expressive) {
    if (fields.get("evidence").trim().toLowerCase() !== "expressive-layout-beats") {
      throw new Error('Expressive caption preview approval Evidence must be exactly "expressive-layout-beats".');
    }
    const karaoke = fields.get("karaoke").trim();
    if (!new Set(["on", "off"]).has(karaoke)) {
      throw new Error('Expressive caption preview approval Karaoke must be exactly "on" or "off".');
    }
    return {
      reviewId: fields.get("review"), decision: "approve",
      evidence: ["expressive-layout-beats"], karaoke: karaoke === "on",
    };
  }
  const evidence = fields.get("evidence").split(",").map((value) => value.trim().toLowerCase());
  const required = ["early", "middle", "late", "no-caption"];
  if (evidence.length !== required.length || new Set(evidence).size !== required.length
    || required.some((label) => !evidence.includes(label))) {
    throw new Error("Caption preview approval Evidence must contain exactly early, middle, late, and no-caption once each.");
  }
  return { reviewId: fields.get("review"), decision: "approve", evidence };
};

export const parseCaptionPreviewRevision = (response, expectedReviewId) => {
  const fields = parseSummaryFields(
    response, "Caption preview review", ["review", "decision", "changes"],
  );
  assertPreviewReview(fields, expectedReviewId, "revise");
  return { reviewId: fields.get("review"), decision: "revise", changes: fields.get("changes") };
};

export const readInteractionState = (statePath) => {
  const resolvedStatePath = resolve(statePath);
  if (!existsSync(resolvedStatePath)) {
    throw new Error(`Interaction state does not exist: ${resolvedStatePath}`);
  }

  const state = readJson(resolvedStatePath);
  if (state.schemaVersion !== 1 || state.skill !== "video-add-captions") {
    throw new Error(`Invalid video-add-captions interaction state: ${resolvedStatePath}`);
  }
  state.decisionMode ??= "human";
  state.reviewId ??= null;
  state.reviewPage ??= null;
  if (state.approval && state.selection && state.preview) {
    state.approval.selectionId ??= state.selection.choiceId;
    state.approval.previewEvidenceSignature ??= state.preview.evidenceSignature;
  }
  if (!new Set(["human", "agent"]).has(state.decisionMode)) {
    throw new Error(`Invalid caption decision mode: ${state.decisionMode}`);
  }
  return { state, statePath: resolvedStatePath };
};

const assertBoundFile = (binding, actualPath, label) => {
  const resolvedPath = resolve(actualPath);
  if (binding.path !== resolvedPath) {
    throw new Error(`${label} path differs from the interaction state. Start a new interaction.`);
  }
  if (binding.sha256 !== hashFile(resolvedPath)) {
    throw new Error(`${label} content changed after the interaction started. Start a new interaction.`);
  }
};

const findWorkRoot = (contextPath) => {
  let current = dirname(resolve(contextPath));
  while (true) {
    if (basename(current).toLowerCase() === "work" && existsSync(join(current, "project.json"))) {
      return current;
    }
    if (existsSync(join(current, "work", "project.json"))) {
      return join(current, "work");
    }
    const parent = dirname(current);
    if (parent === current) return null;
    current = parent;
  }
};

const operationById = (project, id) => {
  const operations = Array.isArray(project.operations)
    ? project.operations
    : Object.values(project.operations ?? {});
  return operations.find((operation) => operation?.id === id) ?? null;
};

export const assertSpatialContextBinding = (state, actualPath = state.spatialContext?.path) => {
  const captionsPlan = readJson(state.captions.path);
  const planBinding = captionsPlan.spatial_context;
  if (!state.spatialContext) {
    if (planBinding) throw new Error("Captions JSON gained a spatial_context after the interaction started.");
    if (actualPath) throw new Error("A spatial context was supplied to an interaction that did not bind one.");
    return null;
  }
  if (!planBinding) {
    throw new Error("Captions JSON lost its spatial_context binding. Start a new interaction.");
  }
  if (!actualPath) {
    throw new Error("The interaction requires the bound spatial context path.");
  }
  assertBoundFile(state.spatialContext, actualPath, "Caption spatial context");
  if (planBinding.policy !== "composite-aware"
    || planBinding.sha256 !== state.spatialContext.sha256
    || planBinding.source_operation !== state.spatialContext.sourceOperation
    || planBinding.source_revision !== state.spatialContext.sourceRevision) {
    throw new Error("Caption spatial context differs from the captions plan binding. Start a new interaction.");
  }
  const context = readJson(state.spatialContext.path);
  if (context.policy !== "composite-aware"
    || context.source?.operation_id !== state.spatialContext.sourceOperation
    || context.source?.operation_revision !== state.spatialContext.sourceRevision) {
    throw new Error("Caption spatial context source binding is stale. Start a new interaction.");
  }

  const workRoot = findWorkRoot(state.spatialContext.path);
  if (!workRoot) {
    throw new Error("Caption spatial context is not inside a project with work/project.json.");
  }
  const project = readJson(join(workRoot, "project.json"));
  const operation = operationById(project, "b-roll");
  if (!operation || !(project.sequences?.main?.operations ?? []).includes("b-roll")
    || !new Set(["approved", "verified"]).has(operation.status)
    || operation.revision !== state.spatialContext.sourceRevision) {
    throw new Error("Caption spatial context B-roll operation is inactive, unapproved, or stale.");
  }
  const activeOperations = project.sequences?.main?.operations ?? [];
  if (activeOperations.includes("captions")) {
    const captionsOperation = operationById(project, "captions");
    if (!captionsOperation || !(captionsOperation.depends_on ?? []).includes("b-roll")) {
      throw new Error("Active captions operation depends_on must include b-roll for spatial context.");
    }
    if (captionsOperation.based_on?.["b-roll"] !== state.spatialContext.sourceRevision) {
      throw new Error("Active captions operation based_on b-roll revision is stale.");
    }
  }
  const brollPlanPath = resolve(workRoot, context.source.plan_path);
  if (!existsSync(brollPlanPath) || hashFile(brollPlanPath) !== context.source.plan_sha256) {
    throw new Error("Caption spatial context B-roll plan binding is stale.");
  }
  const brollPlan = readJson(brollPlanPath);
  const artifacts = brollPlan.speaker_inset ?? brollPlan.speaker_inset_bindings;
  for (const [field, sourceField] of [
    ["analysis", "analysis_sha256"],
    ["agent_input", "agent_input_sha256"],
    ["preview", "preview_sha256"],
    ["clearance", "clearance_sha256"],
  ]) {
    const binding = artifacts?.[field] ?? (field === "agent_input" ? artifacts?.["agent-input"] : null);
    const artifactPath = binding?.path ? resolve(workRoot, binding.path) : null;
    if (!artifactPath || !existsSync(artifactPath) || binding.sha256 !== context.source[sourceField]
      || hashFile(artifactPath) !== binding.sha256) {
      throw new Error(`Caption spatial context ${field} binding is stale.`);
    }
  }
  for (const collection of [context.visual_intervals ?? [], context.placement_beats ?? []]) {
    for (const item of collection) {
      if (!item.background) continue;
      const backgroundPath = resolve(workRoot, item.background.path);
      if (!existsSync(backgroundPath) || hashFile(backgroundPath) !== item.background.sha256) {
        throw new Error(`Caption spatial context background for ${item.id} is stale.`);
      }
    }
  }
  return context;
};

export const createSpatialContextBinding = (captionsPath, spatialContextPath) => {
  const plan = readJson(resolve(captionsPath));
  const planBinding = Array.isArray(plan) ? null : plan.spatial_context;
  if (!planBinding) {
    if (spatialContextPath) {
      throw new Error("--spatial-context is not allowed when captions have no spatial_context binding.");
    }
    return null;
  }
  if (!spatialContextPath) {
    throw new Error("Captions have a spatial_context binding; --spatial-context is required.");
  }
  const path = resolve(spatialContextPath);
  if (!existsSync(path) || hashFile(path) !== planBinding.sha256) {
    throw new Error("Caption spatial context is missing or differs from the captions plan binding.");
  }
  const context = readJson(path);
  if (context.policy !== "composite-aware" || context.source?.operation_id !== "b-roll"
    || context.source?.operation_revision !== planBinding.source_revision) {
    throw new Error("Caption spatial context source differs from the captions plan binding.");
  }
  return {
    path,
    sha256: planBinding.sha256,
    sourceOperation: "b-roll",
    sourceRevision: planBinding.source_revision,
  };
};

export const assertReviewPageBinding = (state) => {
  if (!state.reviewId || !state.reviewPage?.path || !state.reviewPage?.sha256) {
    throw new Error("Caption style review page binding is missing. Start a new interaction.");
  }
  assertBoundFile(state.reviewPage, state.reviewPage.path, "Caption style review page");
  if (!Array.isArray(state.reviewPage.assets) || state.reviewPage.assets.length !== galleryAssetFiles.length) {
    throw new Error("Caption style review asset bindings are incomplete. Start a new interaction.");
  }
  const boundNames = state.reviewPage.assets.map((binding) => basename(binding.path));
  if (new Set(boundNames).size !== galleryAssetFiles.length
    || galleryAssetFiles.some((fileName) => !boundNames.includes(fileName))) {
    throw new Error("Caption style review asset bindings do not match the gallery. Start a new interaction.");
  }
  state.reviewPage.assets.forEach((binding) => {
    assertBoundFile(binding, binding.path, `Caption style review asset ${basename(binding.path)}`);
  });
};

export const assertStyleDefinitionBindings = (state) => {
  if (!Array.isArray(state.styleDefinitions) || state.styleDefinitions.length !== styleDefinitionPaths.length) {
    throw new Error("Maintained caption style definition bindings are incomplete. Start a new interaction.");
  }
  const expectedNames = styleDefinitionPaths.map((path) => basename(path));
  const boundNames = state.styleDefinitions.map((binding) => basename(binding.path));
  if (new Set(boundNames).size !== expectedNames.length
    || expectedNames.some((name) => !boundNames.includes(name))) {
    throw new Error("Maintained caption style definition bindings are invalid. Start a new interaction.");
  }
  state.styleDefinitions.forEach((binding) => {
    assertBoundFile(binding, binding.path, `Caption style definition ${basename(binding.path)}`);
  });
};

export const assertCompositeEvidenceCoverage = (context, evidence) => {
  const samples = Array.isArray(evidence) ? evidence : [];
  const sampleBeatId = (sample) => sample.spatialBeatId ?? sample.spatial_beat_id ?? null;
  const requiredDensePurposes = ["spatial-1", "spatial-2", "spatial-3", "spatial-4", "spatial-5"];
  for (const beat of context?.placement_beats ?? []) {
    if (!beat.background) continue;
    const purposes = new Set(samples
      .filter((sample) => sampleBeatId(sample) === beat.id)
      .flatMap((sample) => sample.purposes ?? []));
    for (const purpose of requiredDensePurposes) {
      if (!purposes.has(purpose)) {
        throw new Error(`Composite-aware caption evidence for ${beat.id} is missing required purpose ${purpose}.`);
      }
    }
  }

  const boundaries = [...new Set((context?.visual_intervals ?? []).flatMap((interval) => {
    const start = Number(interval?.program_range?.start_s);
    const end = Number(interval?.program_range?.end_s);
    return Number.isFinite(start) && Number.isFinite(end) && end > start ? [start, end] : [];
  }))].sort((a, b) => a - b);
  const purposes = new Set(samples.flatMap((sample) => sample.purposes ?? []));
  boundaries.forEach((_, index) => {
    for (const side of ["before", "after"]) {
      const purpose = `spatial-boundary-${String(index + 1).padStart(3, "0")}-${side}`;
      if (!purposes.has(purpose)) {
        throw new Error(`Composite-aware caption evidence is missing required purpose ${purpose}.`);
      }
    }
  });
};

const reviewCategories = (sample) => {
  const categories = [];
  const requested = sample.requested_variant ?? sample.requestedVariant ?? sample.variant ?? null;
  if (["bottom-standard", "center-emphasis"].includes(requested)) categories.push(requested);
  let placement = sample.resolved_placement ?? sample.resolvedPlacement ?? null;
  if (!placement && requested) {
    placement = requested === "center-emphasis" ? "frame-center" : "preset-bottom";
  }
  if (["preset-bottom", "frame-center", "panel-center"].includes(placement)) categories.push(placement);
  if (sample.hero_line ?? sample.heroLine) categories.push("hero-1.5x");
  return categories;
};

export const assertRepresentativeEvidence = (machineSamples, reviewSamples) => {
  if (!Array.isArray(machineSamples) || !Array.isArray(reviewSamples) || reviewSamples.length > 6) {
    throw new Error("Caption representative evidence is invalid.");
  }
  const byLabel = new Map(machineSamples.map((sample) => [sample.label, sample]));
  const expectedCategories = new Set(machineSamples.flatMap(reviewCategories));
  const seenCategories = new Set();
  const seenPixels = new Set();
  for (const sample of reviewSamples) {
    const source = byLabel.get(sample.sample_label);
    const categories = sample.categories;
    const pixelKey = `${sample.preview}\0${sample.sha256}`;
    if (!source || source.preview !== sample.preview || source.sha256 !== sample.sha256
      || !Array.isArray(categories) || categories.length === 0 || seenPixels.has(pixelKey)) {
      throw new Error("Caption representative evidence does not match machine evidence.");
    }
    seenPixels.add(pixelKey);
    for (const category of categories) {
      if (!expectedCategories.has(category) || seenCategories.has(category)) {
        throw new Error("Caption representative evidence categories are invalid or duplicated.");
      }
      seenCategories.add(category);
    }
  }
  if (expectedCategories.size !== seenCategories.size
    || [...expectedCategories].some((category) => !seenCategories.has(category))) {
    throw new Error("Caption representative evidence does not cover every maintained category.");
  }
};

export const assertPreviewBindings = (preview, state = null) => {
  if (!preview || !preview.projectMetaPath || !preview.projectMetaSha256) {
    throw new Error("Preview project metadata binding is missing. Generate a new preview.");
  }
  const minimumEvidence = preview.approvalEvidence === "composite-aware"
    ? 1
    : preview.approvalEvidence === "expressive-layout-beats" ? 2 : 4;
  if (!Array.isArray(preview.evidence) || preview.evidence.length < minimumEvidence) {
    throw new Error("Preview evidence bindings are incomplete. Generate a new preview.");
  }

  if (state) {
    assertBoundFile(state.sourceVideo, state.sourceVideo.path, "Source video");
    assertBoundFile(state.captions, state.captions.path, "Captions JSON");
    assertSpatialContextBinding(state);
    if ((preview.spatialContextSha256 ?? null) !== (state.spatialContext?.sha256 ?? null)) {
      throw new Error("Preview spatial context differs from the interaction state. Generate a new preview.");
    }
    if (state.reviewId || state.reviewPage || state.styleDefinitions) assertStyleDefinitionBindings(state);
    if (state.reviewPage) assertReviewPageBinding(state);
  }

  assertBoundFile(
    { path: preview.projectMetaPath, sha256: preview.projectMetaSha256 },
    preview.projectMetaPath,
    "Preview project metadata",
  );
  let machineDocument = null;
  if (preview.machineEvidence) {
    assertBoundFile(preview.machineEvidence, preview.machineEvidence.path, "Caption machine evidence document");
    machineDocument = readJson(preview.machineEvidence.path);
    if (!Array.isArray(machineDocument.samples)
      || preview.machineEvidence.sampleCount !== machineDocument.samples.length) {
      throw new Error("Caption machine evidence count is stale.");
    }
    if (Array.isArray(machineDocument.review_samples)) {
      assertRepresentativeEvidence(machineDocument.samples, machineDocument.review_samples);
    }
  }
  if (preview.reviewPagePath || preview.reviewPageSha256) {
    if (!preview.reviewPagePath || !preview.reviewPageSha256) {
      throw new Error("Caption preview review page binding is incomplete. Generate a new preview.");
    }
    assertBoundFile(
      { path: preview.reviewPagePath, sha256: preview.reviewPageSha256 },
      preview.reviewPagePath,
      "Caption preview review page",
    );
    if (!preview.timeline?.path || !preview.timeline?.sha256 || !preview.timeline?.timelineId) {
      throw new Error("Caption preview timeline binding is missing. Generate a new preview.");
    }
    assertBoundFile(preview.timeline, preview.timeline.path, "Caption preview timeline");
    const timeline = readJson(preview.timeline.path);
    if (timeline.timeline_id !== preview.timeline.timelineId) {
      throw new Error("Caption preview timeline identity changed. Generate a new preview.");
    }
    const labels = preview.evidence.map((binding) => binding.label);
    const machineSamples = machineDocument?.samples ?? preview.evidence;
    if (preview.approvalEvidence === "composite-aware") {
      const context = assertSpatialContextBinding(state);
      assertCompositeEvidenceCoverage(context, machineSamples);
      const invalidClearance = machineSamples.some((binding) => {
        const clearance = binding.clearance_status ?? binding.clearanceStatus;
        const cueIndex = binding.cue_index ?? binding.cueIndex ?? null;
        const spatialBeatId = binding.spatial_beat_id ?? binding.spatialBeatId ?? null;
        if (clearance === "pass") return false;
        const legacyUncaptionedSample = clearance === undefined
          && cueIndex === null && !spatialBeatId
          && ((binding.kind === "no-caption" && binding.purposes?.includes("no-caption"))
            || (binding.kind === "spatial-boundary"
              && binding.purposes?.some((purpose) => purpose.startsWith("spatial-boundary-"))));
        return !legacyUncaptionedSample;
      });
      const machineLabels = machineSamples.map((sample) => sample.label);
      if (labels.length !== new Set(labels).size || !machineLabels.includes("no-caption")
        || invalidClearance) {
        throw new Error("Composite-aware caption preview evidence coverage or clearance is invalid.");
      }
      const plan = readJson(state.captions.path);
      const heroCueIndexes = (plan.cues ?? []).filter((cue) => cue.hero_line).map((cue) => cue.index);
      if (heroCueIndexes.some((cueIndex) => !machineSamples.some(
        (binding) => (binding.cue_index ?? binding.cueIndex) === cueIndex
          && (binding.hero_line ?? binding.heroLine),
      ))) {
        throw new Error("Composite-aware caption preview evidence does not cover every hero-line cue.");
      }
      if (preview.presentationMode === "expressive"
        && (!Array.isArray(preview.comparisonEvidence) || preview.comparisonEvidence.length !== 2)) {
        throw new Error("Expressive coexistence comparison evidence bindings are incomplete.");
      }
    } else if (preview.approvalEvidence === "expressive-layout-beats") {
      const plan = readJson(state.captions.path);
      const beatIds = plan.presentation?.layout_beats?.map((beat) => beat.id) ?? [];
      const boundBeatIds = new Set(machineSamples
        .map((binding) => binding.beat_id ?? binding.beatId).filter(Boolean));
      const heroCueIndexes = (plan.cues ?? []).filter((cue) => cue.hero_line).map((cue) => cue.index);
      const machineLabels = machineSamples.map((sample) => sample.label);
      if (labels.length < 1 || !machineLabels.includes("no-caption") || new Set(labels).size !== labels.length
        || beatIds.some((beatId) => !boundBeatIds.has(beatId))
        || heroCueIndexes.some((cueIndex) => !machineSamples.some(
          (binding) => (binding.cue_index ?? binding.cueIndex) === cueIndex
            && (binding.hero_line ?? binding.heroLine),
        ))) {
        throw new Error("Expressive caption preview evidence must bind every layout beat, hero-line, and no-caption.");
      }
      if (!Array.isArray(preview.comparisonEvidence) || preview.comparisonEvidence.length !== 2) {
        throw new Error("Expressive coexistence comparison evidence bindings are incomplete.");
      }
    } else {
      const requiredLabels = ["early", "middle", "late", "no-caption"];
      if (labels.length !== requiredLabels.length || new Set(labels).size !== requiredLabels.length
        || requiredLabels.some((label) => !labels.includes(label))) {
        throw new Error("Caption preview evidence labels must be exactly early, middle, late, and no-caption.");
      }
    }
  }
  preview.evidence.forEach((binding, index) => {
    assertBoundFile(binding, binding.path, `Preview evidence ${index + 1}`);
  });
  if (preview.evidenceSignature !== hashJson(preview.evidence)) {
    throw new Error("Preview evidence signature differs from the interaction state. Generate a new preview.");
  }
  if (preview.comparisonEvidence) {
    preview.comparisonEvidence.forEach((binding, index) => {
      assertBoundFile(binding, binding.path, `Coexistence comparison evidence ${index + 1}`);
    });
    if (preview.comparisonEvidenceSignature !== hashJson(preview.comparisonEvidence)) {
      throw new Error("Coexistence comparison evidence signature differs from the interaction state.");
    }
  }
};

export const resolveCanonicalReviewEvidence = (state, canonicalPlan) => {
  assertPreviewBindings(state?.preview, state);
  const representative = state.preview.evidence;
  const binding = state.preview.machineEvidence;
  const machineDocument = binding?.path && binding.sha256 ? {
    path: resolve(binding.path),
    sha256: binding.sha256,
    sampleCount: binding.sampleCount,
  } : null;
  if (canonicalPlan?.presentation?.mode !== "expressive") {
    return { representative, delivery: representative, machineDocument };
  }

  if (!machineDocument) {
    return { representative, delivery: representative, machineDocument: null };
  }
  const documentPath = machineDocument.path;
  const document = readJson(documentPath);
  const samples = Array.isArray(document.samples) ? document.samples : [];
  const beatIds = canonicalPlan.presentation.layout_beats?.map((beat) => beat.id) ?? [];
  const selected = beatIds.map((beatId) => {
    const matches = samples.filter((sample) => sample.kind === "layout-beat"
      && (sample.beat_id ?? sample.beatId) === beatId);
    if (matches.length !== 1) {
      throw new Error(`Expressive canonical review requires exactly one machine sample for ${beatId}.`);
    }
    return matches[0];
  });
  const noCaption = samples.filter((sample) => sample.kind === "no-caption");
  if (noCaption.length !== 1) {
    throw new Error("Expressive canonical review requires exactly one no-caption machine sample.");
  }

  const delivery = [...selected, noCaption[0]].map((sample) => {
    const path = resolve(dirname(documentPath), sample.preview ?? "");
    if (!sample.preview || sample.sha256 !== hashFile(path)) {
      throw new Error(`Expressive canonical review evidence is stale: ${sample.label ?? sample.preview}.`);
    }
    return { ...sample, path };
  });
  return {
    representative,
    delivery,
    machineDocument,
  };
};

const normalizeNullable = (value) => value ?? null;

export const selectionOptionsFromState = (selection) => ({
  preset: selection.preset,
  highlightTheme: normalizeNullable(selection.highlightTheme),
  backgroundTheme: normalizeNullable(selection.backgroundTheme),
  strokeTheme: normalizeNullable(selection.strokeTheme),
  karaoke: String(selection.karaoke),
});

export const overridesHash = (overridesPath) => overridesPath
  ? hashFile(resolve(overridesPath))
  : null;

export const validateGenerationInteraction = ({
  statePath,
  mode,
  sourceVideo,
  captionsPath,
  spatialContextPath,
  requestedSelection,
  overridesPath,
}) => {
  if (!statePath) {
    throw new Error("--interaction-state is required. Caption generation cannot bypass the user interview gates.");
  }

  const loaded = readInteractionState(statePath);
  const { state } = loaded;
  const requiredPhase = mode === "overlay" ? "render_approved" : "style_selected";
  if (state.phase !== requiredPhase) {
    throw new Error(
      mode === "overlay"
        ? `Full overlay rendering requires phase render_approved. Current phase: ${state.phase}`
        : `Preview generation requires phase style_selected. Current phase: ${state.phase}`,
    );
  }

  if (!state.selection) {
    throw new Error("The interaction state has no explicit style selection.");
  }

  assertBoundFile(state.sourceVideo, sourceVideo, "Source video");
  assertBoundFile(state.captions, captionsPath, "Captions JSON");
  assertSpatialContextBinding(state, spatialContextPath);
  if (state.reviewId || state.reviewPage || state.styleDefinitions) {
    assertStyleDefinitionBindings(state);
  }
  if (state.reviewPage) assertReviewPageBinding(state);

  const expectedSelection = selectionOptionsFromState(state.selection);
  const expressiveOverlay = mode === "overlay" && state.preview?.presentationMode === "expressive";
  if (expressiveOverlay) {
    if (typeof state.approval?.karaoke !== "boolean") {
      throw new Error("Expressive overlay rendering requires an approved Karaoke on/off choice.");
    }
    if (!state.preview.comparisonEvidenceSignature
      || state.approval.comparisonEvidenceSignature !== state.preview.comparisonEvidenceSignature) {
      throw new Error("Expressive approval no longer matches the comparison evidence.");
    }
    expectedSelection.karaoke = String(state.approval.karaoke);
  }
  for (const key of ["preset", "highlightTheme", "backgroundTheme", "strokeTheme", "karaoke"]) {
    if (normalizeNullable(requestedSelection[key]) !== normalizeNullable(expectedSelection[key])) {
      throw new Error(
        expressiveOverlay && key === "karaoke"
          ? "Requested Karaoke does not match the preview-approved Expressive choice."
          : `Requested ${key} does not match the user's recorded selection ${state.selection.choiceId}.`,
      );
    }
  }

  const currentOverridesHash = overridesHash(overridesPath);
  if (mode === "overlay") {
    if (!state.preview || !state.approval) {
      throw new Error("The interaction state has no confirmed preview evidence.");
    }
    assertPreviewBindings(state.preview, state);
    if (state.approval.actor && state.approval.actor !== state.decisionMode) {
      throw new Error("Render approval actor does not match the interaction decision mode.");
    }
    if (state.preview.overridesSha256 !== currentOverridesHash) {
      throw new Error("Overrides changed after preview confirmation. Generate and confirm a new preview.");
    }
    if (state.approval.selectionId !== state.selection.choiceId
      || state.approval.previewEvidenceSignature !== state.preview.evidenceSignature
      || (state.approval.machineEvidenceSha256 ?? null)
        !== (state.preview.machineEvidence?.sha256 ?? null)) {
      throw new Error("Approval no longer matches the selected style and preview evidence.");
    }
  }

  return {
    ...loaded,
    expectedSelection,
    currentOverridesHash,
  };
};
