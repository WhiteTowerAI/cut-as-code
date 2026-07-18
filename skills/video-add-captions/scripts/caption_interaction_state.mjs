import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const skillRoot = resolve(scriptDirectory, "..");
const manifestPath = join(skillRoot, "assets", "style-previews", "preview-manifest.json");

const readJson = (path) => JSON.parse(readFileSync(path, "utf8").replace(/^\uFEFF/, ""));

const manifest = readJson(manifestPath);
const galleryItems = manifest.groups.flatMap((group) => group.items);
const galleryById = new Map(galleryItems.map((item) => [item.id.toLowerCase(), item]));

export const galleryPath = join(skillRoot, "assets", "style-previews", "index.html");
export const validSelectionIds = galleryItems.map((item) => item.id);

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

export const assertPreviewBindings = (preview) => {
  if (!preview || !preview.projectMetaPath || !preview.projectMetaSha256) {
    throw new Error("Preview project metadata binding is missing. Generate a new preview.");
  }
  if (!Array.isArray(preview.evidence) || preview.evidence.length < 4) {
    throw new Error("Preview evidence bindings are incomplete. Generate a new preview.");
  }

  assertBoundFile(
    { path: preview.projectMetaPath, sha256: preview.projectMetaSha256 },
    preview.projectMetaPath,
    "Preview project metadata",
  );
  preview.evidence.forEach((binding, index) => {
    assertBoundFile(binding, binding.path, `Preview evidence ${index + 1}`);
  });
  if (preview.evidenceSignature !== hashJson(preview.evidence)) {
    throw new Error("Preview evidence signature differs from the interaction state. Generate a new preview.");
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

  const expectedSelection = selectionOptionsFromState(state.selection);
  for (const key of ["preset", "highlightTheme", "backgroundTheme", "strokeTheme", "karaoke"]) {
    if (normalizeNullable(requestedSelection[key]) !== normalizeNullable(expectedSelection[key])) {
      throw new Error(
        `Requested ${key} does not match the user's recorded selection ${state.selection.choiceId}.`,
      );
    }
  }

  const currentOverridesHash = overridesHash(overridesPath);
  if (mode === "overlay") {
    if (!state.preview || !state.approval) {
      throw new Error("The interaction state has no confirmed preview evidence.");
    }
    assertPreviewBindings(state.preview);
    if (state.approval.actor && state.approval.actor !== state.decisionMode) {
      throw new Error("Render approval actor does not match the interaction decision mode.");
    }
    if (state.preview.overridesSha256 !== currentOverridesHash) {
      throw new Error("Overrides changed after preview confirmation. Generate and confirm a new preview.");
    }
  }

  return {
    ...loaded,
    expectedSelection,
    currentOverridesHash,
  };
};
