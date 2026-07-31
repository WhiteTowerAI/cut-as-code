import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

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
      `Style response must be one exact gallery combination ID or the exact word \"跳过\". Received: ${rawResponse || "<empty>"}`,
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

export const parseCaptionPreviewApproval = (response, expectedReviewId, expectedEvidence = "standard-four") => {
  const expressive = expectedEvidence === "expressive-layout-beats";
  const fields = parseSummaryFields(
    response, "Caption preview review",
    expressive ? ["review", "decision", "evidence", "karaoke"] : ["review", "decision", "evidence"],
  );
  assertPreviewReview(fields, expectedReviewId, "approve");
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

export const assertPreviewBindings = (preview, state = null) => {
  if (!preview || !preview.projectMetaPath || !preview.projectMetaSha256) {
    throw new Error("Preview project metadata binding is missing. Generate a new preview.");
  }
  const minimumEvidence = preview.approvalEvidence === "expressive-layout-beats" ? 2 : 4;
  if (!Array.isArray(preview.evidence) || preview.evidence.length < minimumEvidence) {
    throw new Error("Preview evidence bindings are incomplete. Generate a new preview.");
  }

  if (state) {
    assertBoundFile(state.sourceVideo, state.sourceVideo.path, "Source video");
    assertBoundFile(state.captions, state.captions.path, "Captions JSON");
    if (state.reviewId || state.reviewPage || state.styleDefinitions) assertStyleDefinitionBindings(state);
    if (state.reviewPage) assertReviewPageBinding(state);
  }

  assertBoundFile(
    { path: preview.projectMetaPath, sha256: preview.projectMetaSha256 },
    preview.projectMetaPath,
    "Preview project metadata",
  );
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
    if (preview.approvalEvidence === "expressive-layout-beats") {
      if (labels.length < 2 || labels.at(-1) !== "no-caption" || new Set(labels).size !== labels.length
        || preview.evidence.slice(0, -1).some((binding) => !binding.beatId || !binding.variant)) {
        throw new Error("Expressive caption preview evidence must bind unique layout beats followed by no-caption.");
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
      || state.approval.previewEvidenceSignature !== state.preview.evidenceSignature) {
      throw new Error("Approval no longer matches the selected style and preview evidence.");
    }
  }

  return {
    ...loaded,
    expectedSelection,
    currentOverridesHash,
  };
};
