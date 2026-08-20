import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import {
  captionBackgroundThemeNames,
  captionExpressiveTreatments,
  captionHighlightThemeNames,
  captionPresetNames,
  captionStrokeThemeNames,
  resolveCaptionStyle,
  resolveKaraoke,
} from "./caption_style_config.mjs";
import {
  hashFile,
  readInteractionState,
  resolveCanonicalReviewEvidence,
  selectionOptionsFromState,
  validateGenerationInteraction,
} from "./caption_interaction_state.mjs";

const rawArgs = process.argv.slice(2);

const usage = `Usage:
  node generate_caption_project.mjs \\
    --video <source-video> \\
    --captions <captions-json> \\
    --out <project-dir> \\
    [--interaction-state <json-file>] \\
    [--spatial-context <caption-spatial-context.json>] \\
    [--approved-plan true] \\
    [--project-root <project-root>] \\
    [--preset ${captionPresetNames.join("|")}] \\
    [--highlight-theme ${captionHighlightThemeNames.join("|")}] \\
    [--background-theme ${captionBackgroundThemeNames.join("|")}] \\
    [--stroke-theme ${captionStrokeThemeNames.join("|")}] \\
    [--karaoke auto|true|false] \\
    [--mode preview|overlay] \\
    [--overrides <json-file>]`;

const parseArgs = (args) => {
  const parsed = { mode: "preview" };
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (!arg.startsWith("--")) {
      throw new Error(`Unexpected argument: ${arg}`);
    }
    const key = arg.slice(2).replaceAll(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    const value = args[index + 1];
    if (!value || value.startsWith("--")) {
      throw new Error(`Missing value for ${arg}`);
    }
    parsed[key] = value;
    index += 1;
  }
  return parsed;
};

const presentationModes = new Set(["standard", "expressive"]);
const layoutVariants = new Set(["bottom-standard", "center-emphasis"]);
const semanticRoles = new Set(["normal", "keyword", "number", "contrast"]);
const heroLineLevels = new Set(["strong", "hero"]);
const resolvedPlacements = new Set(["preset-bottom", "frame-center", "panel-center", "panel-bottom"]);
const isObject = (value) => typeof value === "object" && value !== null && !Array.isArray(value);
const isNumber = (value) => typeof value === "number" && Number.isFinite(value);
const sameTime = (left, right) => isNumber(left) && isNumber(right) && Math.abs(left - right) <= 1e-6;

const rejectHeroLines = (cues, mode) => {
  cues.forEach((cue, position) => {
    if (cue?.hero_lines !== undefined) {
      throw new Error(`Cue at position ${position + 1} uses unsupported hero_lines; use one hero_line.`);
    }
    if (cue?.hero_line !== undefined) {
      throw new Error(`${mode} cue at position ${position + 1} must not contain hero_line.`);
    }
  });
};

const validateHeroLine = (cue, cueIndex) => {
  if (cue.hero_lines !== undefined) {
    throw new Error(`Cue index ${cueIndex} uses unsupported hero_lines; use one hero_line.`);
  }
  if (cue.hero_line === undefined) {
    return null;
  }
  const heroLine = cue.hero_line;
  if (!isObject(heroLine)) {
    throw new Error(`Cue index ${cueIndex} hero_line must be an object.`);
  }
  if (!heroLineLevels.has(heroLine.level)) {
    throw new Error(`Cue index ${cueIndex} hero_line level must be strong or hero.`);
  }
  const indexes = heroLine.word_indexes;
  if (!Array.isArray(indexes) || indexes.length === 0 || indexes.some((value) => !Number.isInteger(value))) {
    throw new Error(`Cue index ${cueIndex} hero_line word_indexes must be a non-empty integer array.`);
  }
  const contiguous = indexes.every((value, position) => value === indexes[0] + position);
  if (!contiguous || indexes[0] < 1 || indexes.at(-1) > cue.words.length) {
    throw new Error(`Cue index ${cueIndex} hero_line word_indexes must be unique, ordered, contiguous, and in range.`);
  }
  if (!String(heroLine.rationale ?? "").trim() || /[\r\n]/.test(heroLine.rationale)) {
    throw new Error(`Cue index ${cueIndex} hero_line rationale must be non-empty single-line text.`);
  }
  return heroLine;
};

const validatePresentationPlan = (plan) => {
  const presentation = plan.presentation;
  if (presentation === undefined) {
    rejectHeroLines(plan.cues, "Standard");
    return { mode: "standard", layoutBeatCount: 0, heroLines: [] };
  }
  if (!isObject(presentation)) {
    throw new Error("Caption presentation must be an object.");
  }
  if (!presentationModes.has(presentation.mode)) {
    throw new Error("Caption presentation mode must be standard or expressive.");
  }
  if (presentation.mode === "standard") {
    rejectHeroLines(plan.cues, "Standard");
    return { mode: "standard", layoutBeatCount: 0, heroLines: [] };
  }
  if (presentation.schema_version !== 1) {
    throw new Error("Expressive presentation schema_version must be 1.");
  }
  if (presentation.planning_status !== "complete") {
    throw new Error("Expressive plan must be complete before preview generation.");
  }
  if (!isObject(presentation.planner)
    || presentation.planner.actor !== "agent"
    || presentation.planner.scope !== "full-program"
    || !String(presentation.planner.rationale ?? "").trim()) {
    throw new Error("Completed expressive plan requires an Agent full-program planning rationale.");
  }

  const cueById = new Map();
  const cuePositions = new Map();
  const cueIndexes = new Set();
  const heroLines = [];
  let previousCueIndex = 0;
  plan.cues.forEach((cue, position) => {
    const cueIndex = cue?.index;
    if (!Number.isInteger(cueIndex) || cueIndex <= 0) {
      throw new Error(`Expressive cue at position ${position + 1} must have a positive integer index.`);
    }
    if (cueIndexes.has(cueIndex) || cueIndex <= previousCueIndex) {
      throw new Error("Expressive cue indexes must be unique and ascending.");
    }
    previousCueIndex = cueIndex;
    cueIndexes.add(cueIndex);
    const cueId = cue.id;
    if (!String(cueId ?? "").trim() || cueById.has(cueId)) {
      throw new Error(`Expressive cue index ${cueIndex} must have a unique non-empty id.`);
    }
    if (!isNumber(cue.start) || !isNumber(cue.end) || cue.end <= cue.start) {
      throw new Error(`Expressive cue index ${cueIndex} must have a positive time range.`);
    }
    if (!Array.isArray(cue.words) || cue.words.length === 0) {
      throw new Error(`Expressive cue index ${cueIndex} must contain words.`);
    }
    cue.words.forEach((word, wordIndex) => {
      const semanticRole = word?.semantic_role ?? "normal";
      if (!semanticRoles.has(semanticRole)) {
        throw new Error(`Cue index ${cueIndex} word ${wordIndex + 1} has invalid semantic_role: ${semanticRole}`);
      }
    });
    const heroLine = validateHeroLine(cue, cueIndex);
    if (heroLine) {
      heroLines.push({ cueIndex, level: heroLine.level, wordIndexes: [...heroLine.word_indexes] });
    }
    cueById.set(cueId, cue);
    cuePositions.set(cueId, position);
  });

  if (!Array.isArray(presentation.layout_beats) || presentation.layout_beats.length === 0) {
    throw new Error("Completed expressive plan requires layout beats.");
  }
  const beatIds = new Set();
  const coveredCueIds = new Set();
  let previousStart = null;
  let previousEnd = null;
  let previousLastPosition = -1;
  presentation.layout_beats.forEach((beat, beatPosition) => {
    const beatId = beat?.id;
    if (!String(beatId ?? "").trim() || beatIds.has(beatId)) {
      throw new Error(`Layout beat ${beatPosition + 1} must have a unique non-empty id.`);
    }
    beatIds.add(beatId);
    if (beat.variant === "top-statement") {
      throw new Error(
        `Layout beat ${beatId} uses removed variant top-statement; `
        + "the plan must be replanned as bottom-standard or center-emphasis.",
      );
    }
    if (!layoutVariants.has(beat.variant)) {
      throw new Error(`Layout beat ${beatId} has invalid variant: ${beat.variant}`);
    }
    if (!Array.isArray(beat.cue_ids) || beat.cue_ids.length === 0) {
      throw new Error(`Layout beat ${beatId} must reference one or more cue_ids.`);
    }
    const positions = beat.cue_ids.map((cueId) => {
      if (!cueById.has(cueId)) {
        throw new Error(`Layout beat ${beatId} references unknown cue id/index: ${cueId}`);
      }
      if (coveredCueIds.has(cueId)) {
        throw new Error(`Cue ${cueId} is referenced by more than one layout beat.`);
      }
      return cuePositions.get(cueId);
    });
    const expectedPositions = Array.from(
      { length: positions.at(-1) - positions[0] + 1 },
      (_, index) => positions[0] + index,
    );
    if (positions.length !== expectedPositions.length
      || positions.some((position, index) => position !== expectedPositions[index])) {
      throw new Error(`Layout beat ${beatId} cue_ids must be contiguous and ordered.`);
    }
    if (!isObject(beat.program_range)
      || !isNumber(beat.program_range.start_s)
      || !isNumber(beat.program_range.end_s)
      || beat.program_range.end_s <= beat.program_range.start_s) {
      throw new Error(`Layout beat ${beatId} must have a positive program_range.`);
    }
    const firstCue = cueById.get(beat.cue_ids[0]);
    const lastCue = cueById.get(beat.cue_ids.at(-1));
    if (!sameTime(beat.program_range.start_s, firstCue.start)
      || !sameTime(beat.program_range.end_s, lastCue.end)) {
      throw new Error(`Layout beat ${beatId} starts or ends inside a cue.`);
    }
    if (previousStart !== null && beat.program_range.start_s < previousStart) {
      throw new Error("Layout beats must be sorted by time.");
    }
    if (previousEnd !== null && beat.program_range.start_s < previousEnd) {
      throw new Error(`Layout beat ${beatId} overlaps the previous layout beat.`);
    }
    if (positions[0] <= previousLastPosition) {
      throw new Error("Layout beats must follow cue order.");
    }
    if (!String(beat.rationale ?? "").trim()) {
      throw new Error(`Completed layout beat ${beatId} requires a rationale.`);
    }
    beat.cue_ids.forEach((cueId) => coveredCueIds.add(cueId));
    previousStart = beat.program_range.start_s;
    previousEnd = beat.program_range.end_s;
    previousLastPosition = positions.at(-1);
  });
  if (coveredCueIds.size !== cueById.size || [...cueById.keys()].some((cueId) => !coveredCueIds.has(cueId))) {
    throw new Error("Completed expressive plan must cover every cue exactly once.");
  }
  return { mode: "expressive", layoutBeatCount: presentation.layout_beats.length, heroLines };
};

let options;
try {
  options = parseArgs(rawArgs);
} catch (error) {
  console.error(error.message);
  console.error(usage);
  process.exit(1);
}

const approvedPlanMode = options.approvedPlan === "true";
if (options.approvedPlan && !new Set(["true", "false"]).has(options.approvedPlan)) {
  throw new Error("--approved-plan must be true or false.");
}
if (!options.video || !options.captions || !options.out || (!approvedPlanMode && !options.interactionState)) {
  console.error(usage);
  process.exit(1);
}

const sourceVideo = resolve(options.video);
const captionsPath = resolve(options.captions);
const projectDir = resolve(options.out);
const assetsDir = join(projectDir, "assets");
const scriptDir = dirname(fileURLToPath(import.meta.url));
const skillRoot = resolve(scriptDir, "..");
const fontSource = join(skillRoot, "public", "fonts", "CalSans-Regular.ttf");
const gsapSource = join(skillRoot, "public", "gsap.min.js");
const captionStyleConfigPath = join(scriptDir, "caption-styles.json");
const projectRoot = options.projectRoot ? resolve(options.projectRoot) : null;
const overridesPath = options.overrides ? resolve(options.overrides) : null;
const overrides = overridesPath
  ? JSON.parse(readFileSync(overridesPath, "utf8").replace(/^\uFEFF/, ""))
  : undefined;
const mode = options.mode ?? "preview";
if (!new Set(["preview", "overlay"]).has(mode)) {
  throw new Error(`[captions] invalid render mode: ${mode}`);
}

const captionDocument = JSON.parse(readFileSync(captionsPath, "utf8").replace(/^\uFEFF/, ""));
const canonicalPlan = Array.isArray(captionDocument) ? null : captionDocument;
const captions = canonicalPlan?.cues ?? captionDocument;
if (!Array.isArray(captions) || captions.length === 0) {
  throw new Error("Caption JSON must contain a non-empty cue array or a canonical plan with cues");
}
if (canonicalPlan && (
  canonicalPlan.schema_version !== 1
  || canonicalPlan.target !== "overlay"
  || canonicalPlan.timebase !== "program"
)) {
  throw new Error("Canonical caption plan must be schema_version 1, target overlay, and program timebase");
}
if (!canonicalPlan) {
  rejectHeroLines(captions, "Legacy");
}
const presentationSummary = canonicalPlan
  ? validatePresentationPlan(canonicalPlan)
  : { mode: "standard", layoutBeatCount: 0, heroLines: [] };
const expressiveEnabled = presentationSummary.mode === "expressive";
const layoutBeatByCueId = new Map();
if (expressiveEnabled) {
  canonicalPlan.presentation.layout_beats.forEach((beat) => {
    beat.cue_ids.forEach((cueId) => layoutBeatByCueId.set(cueId, beat));
  });
}

const loadSpatialContext = () => {
  const binding = canonicalPlan?.spatial_context;
  if (!binding) {
    if (options.spatialContext) {
      throw new Error("--spatial-context is not allowed when the caption plan has no spatial_context binding.");
    }
    return null;
  }
  if (!options.spatialContext) {
    throw new Error("Caption plan has spatial_context binding; --spatial-context is required.");
  }
  if (!isObject(binding) || binding.policy !== "composite-aware" || binding.source_operation !== "b-roll") {
    throw new Error("Caption plan spatial_context binding is invalid.");
  }
  const contextPath = resolve(options.spatialContext);
  const expectedPath = isAbsolute(binding.path)
    ? resolve(binding.path)
    : projectRoot
      ? resolve(projectRoot, "work", binding.path)
      : null;
  if (expectedPath && contextPath !== expectedPath) {
    throw new Error("--spatial-context does not match the caption plan binding path.");
  }
  if (!existsSync(contextPath) || hashFile(contextPath) !== binding.sha256) {
    throw new Error("Caption spatial context is missing or its SHA-256 is stale.");
  }
  const context = JSON.parse(readFileSync(contextPath, "utf8").replace(/^\uFEFF/, ""));
  if (context.schema_version !== 1 || context.policy !== "composite-aware") {
    throw new Error("Caption spatial context schema/policy is invalid.");
  }
  if (context.timeline_id !== canonicalPlan.timeline_id) {
    throw new Error("Caption spatial context timeline does not match the caption plan.");
  }
  if (context.source?.operation_id !== "b-roll"
    || context.source?.operation_revision !== binding.source_revision) {
    throw new Error("Caption spatial context B-roll revision is stale.");
  }

  if (projectRoot) {
    const sharedProjectPath = resolve(projectRoot, "work", "project.json");
    if (!existsSync(sharedProjectPath)) {
      throw new Error("Caption spatial context requires work/project.json.");
    }
    const sharedProject = JSON.parse(readFileSync(sharedProjectPath, "utf8").replace(/^\uFEFF/, ""));
    const operations = Array.isArray(sharedProject.operations)
      ? sharedProject.operations
      : Object.values(sharedProject.operations ?? {});
    const operation = operations.find((item) => item?.id === "b-roll");
    const active = sharedProject.sequences?.main?.operations ?? [];
    if (!operation || !active.includes("b-roll") || !new Set(["approved", "verified"]).has(operation.status)
      || operation.revision !== binding.source_revision) {
      throw new Error("Caption spatial context B-roll operation is inactive, unapproved, or stale.");
    }
  }

  const cueIds = captions.map((cue) => cue.id);
  const cueById = new Map(captions.map((cue) => [cue.id, cue]));
  if (cueIds.some((cueId) => !String(cueId ?? "").trim()) || new Set(cueIds).size !== cueIds.length) {
    throw new Error("Spatial caption cues require unique non-empty ids.");
  }
  const flattened = [];
  const beatByCueId = new Map();
  let previousEnd = null;
  for (const beat of context.placement_beats ?? []) {
    if (!isObject(beat) || !Array.isArray(beat.cue_ids) || beat.cue_ids.length === 0
      || !resolvedPlacements.has(beat.resolved_placement)) {
      throw new Error("Caption spatial placement beat is invalid.");
    }
    if (!isObject(beat.program_range) || !isNumber(beat.program_range.start_s)
      || !isNumber(beat.program_range.end_s) || beat.program_range.end_s <= beat.program_range.start_s) {
      throw new Error(`Caption spatial beat ${beat.id ?? "unknown"} has an invalid program range.`);
    }
    if (previousEnd !== null && beat.program_range.start_s < previousEnd - 1e-6) {
      throw new Error("Caption spatial placement beats overlap or are out of order.");
    }
    previousEnd = beat.program_range.end_s;
    if (beat.visual_context === "focused-panel"
      && !new Set(["panel-center", "panel-bottom"]).has(beat.resolved_placement)) {
      throw new Error(`Caption spatial beat ${beat.id} must resolve focused-panel to panel-center.`);
    }
    if (beat.resolved_placement === "panel-bottom"
      && !beat.cue_ids.every((cueId) => cueById.get(cueId)?.unsplittable_word_boundary)) {
      throw new Error(`Caption spatial beat ${beat.id} uses panel-bottom without an unsplittable word boundary.`);
    }
    if (new Set(["panel-center", "panel-bottom"]).has(beat.resolved_placement)) {
      const rect = beat.allowed_rect;
      const anchor = beat.anchor;
      if (!isObject(rect) || !isObject(anchor)
        || !sameTime(anchor.x, rect.x + rect.width / 2)
        || !sameTime(anchor.y, rect.y + rect.height / 2)) {
        throw new Error(`Caption spatial beat ${beat.id} ${beat.resolved_placement} anchor is stale.`);
      }
    }
    if (beat.background) {
      if (!projectRoot) {
        throw new Error("Caption spatial background validation requires --project-root.");
      }
      const backgroundPath = isAbsolute(beat.background.path)
        ? resolve(beat.background.path)
        : resolve(projectRoot, "work", beat.background.path);
      if (!existsSync(backgroundPath) || hashFile(backgroundPath) !== beat.background.sha256) {
        throw new Error(`Caption spatial beat ${beat.id} background is missing or stale.`);
      }
    }
    for (const cueId of beat.cue_ids) {
      if (!cueIds.includes(cueId) || beatByCueId.has(cueId)) {
        throw new Error(`Caption spatial beat ${beat.id} has unknown or duplicate cue coverage.`);
      }
      flattened.push(cueId);
      beatByCueId.set(cueId, beat);
    }
  }
  if (flattened.length !== cueIds.length || flattened.some((cueId, index) => cueId !== cueIds[index])) {
    throw new Error("Caption spatial placement beats must cover every cue exactly once in order.");
  }
  return { path: contextPath, sha256: binding.sha256, context, beatByCueId };
};

const spatial = loadSpatialContext();
if (approvedPlanMode && !canonicalPlan) {
  throw new Error("--approved-plan requires a canonical caption plan, not a legacy cue array.");
}

let interaction = null;
let requestedSelection;
let style;
let karaoke;
if (approvedPlanMode) {
  if (canonicalPlan.style?.status !== "approved" || canonicalPlan.review?.status !== "approved") {
    throw new Error("--approved-plan requires approved style and review records.");
  }
  if (!canonicalPlan.style.resolved || typeof canonicalPlan.style.resolved !== "object") {
    throw new Error("Approved caption plan is missing the resolved style.");
  }
  requestedSelection = {
    preset: canonicalPlan.style.preset,
    highlightTheme: canonicalPlan.style.highlight_theme ?? null,
    backgroundTheme: canonicalPlan.style.background_theme ?? null,
    strokeTheme: canonicalPlan.style.stroke_theme ?? null,
    karaoke: String(Boolean(canonicalPlan.style.karaoke)),
  };
  style = canonicalPlan.style.resolved;
  karaoke = Boolean(canonicalPlan.style.karaoke);
} else {
  const interactionState = readInteractionState(options.interactionState);
  const recordedSelection = selectionOptionsFromState(interactionState.state.selection ?? {});
  const approvedExpressiveKaraoke = mode === "overlay" && expressiveEnabled
    ? interactionState.state.approval?.karaoke
    : undefined;
  requestedSelection = {
    preset: options.preset ?? recordedSelection.preset,
    highlightTheme: options.highlightTheme ?? recordedSelection.highlightTheme,
    backgroundTheme: options.backgroundTheme ?? recordedSelection.backgroundTheme,
    strokeTheme: options.strokeTheme ?? recordedSelection.strokeTheme,
    karaoke: options.karaoke ?? (typeof approvedExpressiveKaraoke === "boolean"
      ? String(approvedExpressiveKaraoke)
      : recordedSelection.karaoke),
  };
  interaction = validateGenerationInteraction({
    statePath: options.interactionState,
    mode,
    sourceVideo,
    captionsPath,
    spatialContextPath: spatial?.path ?? null,
    requestedSelection: mode === "preview" && expressiveEnabled
      ? { ...requestedSelection, karaoke: recordedSelection.karaoke }
      : requestedSelection,
    overridesPath,
  });
  style = resolveCaptionStyle({
    preset: requestedSelection.preset,
    highlightTheme: requestedSelection.highlightTheme,
    backgroundTheme: requestedSelection.backgroundTheme,
    strokeTheme: requestedSelection.strokeTheme,
    overrides,
  });
  karaoke = resolveKaraoke(requestedSelection.karaoke, style);
}

const probe = JSON.parse(execFileSync("ffprobe", [
  "-v", "error",
  "-select_streams", "v:0",
  "-show_entries", "stream=width,height,r_frame_rate",
  "-show_entries", "format=duration",
  "-of", "json",
  sourceVideo,
], { encoding: "utf8" }));

const stream = probe.streams?.[0];
const probedDuration = Number(probe.format?.duration);
if (!stream || !Number.isFinite(probedDuration)) {
  throw new Error("Unable to read source video metadata");
}

const [probedFpsNumerator, probedFpsDenominator] = String(stream.r_frame_rate).split("/").map(Number);
const planFps = canonicalPlan?.renderer_recipe?.fps;
const fpsNumerator = Number(planFps?.num ?? probedFpsNumerator);
const fpsDenominator = Number(planFps?.den ?? probedFpsDenominator);
if (
  !Number.isInteger(fpsNumerator)
  || !Number.isInteger(fpsDenominator)
  || fpsNumerator <= 0
  || fpsDenominator <= 0
) {
  throw new Error("Caption FPS must be a positive rational {num, den}.");
}
const fps = fpsNumerator / fpsDenominator;
if (fpsNumerator * probedFpsDenominator !== probedFpsNumerator * fpsDenominator) {
  throw new Error("Caption plan FPS does not match the source video FPS.");
}
const width = Number(stream.width);
const height = Number(stream.height);
const duration = Number(canonicalPlan?.program_duration_s ?? probedDuration);
if (!Number.isFinite(duration) || duration <= 0) {
  throw new Error("Caption duration must be positive.");
}

const runtimeAssets = [
  { path: "assets/gsap.min.js", sha256: hashFile(gsapSource) },
  { path: "assets/CalSans-Regular.ttf", sha256: hashFile(fontSource) },
];
if (approvedPlanMode) {
  const approvedAssets = new Map(
    (canonicalPlan.renderer_recipe?.runtime_assets ?? []).map((asset) => [asset.path, asset.sha256]),
  );
  for (const asset of runtimeAssets) {
    if (approvedAssets.get(asset.path) !== asset.sha256) {
      throw new Error(`Approved runtime asset is missing or changed: ${asset.path}`);
    }
  }
}

mkdirSync(assetsDir, { recursive: true });
copyFileSync(fontSource, join(assetsDir, "CalSans-Regular.ttf"));
copyFileSync(gsapSource, join(assetsDir, "gsap.min.js"));

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const toRgba = (color, opacity) => {
  if (!String(color).startsWith("#")) {
    return color;
  }
  const raw = String(color).slice(1);
  const hex = raw.length === 3 ? raw.split("").map((character) => character + character).join("") : raw;
  const value = Number.parseInt(hex, 16);
  if (!Number.isFinite(value) || hex.length !== 6) {
    return color;
  }
  return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${opacity})`;
};

const isShorts = style.preset === "shorts";
const karaokeEnabled = karaoke && style.wordHighlight.enabled && style.wordHighlight.mode !== "none";
const formatWord = (word) => isShorts ? word.toUpperCase() : word;
const semanticScaleByRole = captionExpressiveTreatments.semanticScaleByRole;
const heroTreatment = captionExpressiveTreatments.heroLine;
const semanticRole = (word) => word.semantic_role ?? "normal";
const semanticColor = (role) => role === "normal" ? style.font.color : style.wordHighlight.activeColor;
const combinedScaleRule = "effective scale = max(semantic scale, karaoke active scale); active transform factor = effective / semantic";
const heroLineByCueId = new Map(
  expressiveEnabled
    ? captions.filter((cue) => cue.hero_line).map((cue) => [cue.id, cue.hero_line])
    : [],
);
const heroLineForWord = (cue, wordIndex) => {
  const heroLine = heroLineByCueId.get(cue.id);
  return heroLine?.word_indexes.includes(wordIndex + 1) ? heroLine : null;
};

const wordMarkup = (cue, cueId, word, wordIndex) => {
  const role = semanticRole(word);
  const heroLine = expressiveEnabled ? heroLineForWord(cue, wordIndex) : null;
  const classes = ["caption-word"];
  const attributes = [];
  if (expressiveEnabled) {
    classes.push(`semantic-${role}`);
    attributes.push(`data-semantic-role="${role}"`);
    attributes.push(`style="--semantic-scale:${heroLine ? 1 : semanticScaleByRole[role]};--semantic-color:${heroLine ? heroTreatment.color : semanticColor(role)}"`);
  }
  const attributeSuffix = attributes.length ? ` ${attributes.join(" ")}` : "";
  return `<span id="${cueId}-word-${wordIndex + 1}" class="${classes.join(" ")}"${attributeSuffix}>${escapeHtml(formatWord(String(word.word).trim()))}</span>`;
};

const cueMarkup = captions.map((cue, cueIndex) => {
  const cueId = `caption-cue-${cueIndex + 1}`;
  const beat = expressiveEnabled ? layoutBeatByCueId.get(cue.id) : null;
  const heroLine = heroLineByCueId.get(cue.id);
  const chunks = [];
  for (let wordIndex = 0; wordIndex < cue.words.length; wordIndex += 1) {
    if (heroLine && wordIndex + 1 === heroLine.word_indexes[0]) {
      const heroWords = heroLine.word_indexes.map((oneBasedIndex) => (
        wordMarkup(cue, cueId, cue.words[oneBasedIndex - 1], oneBasedIndex - 1)
      )).join(" ");
      chunks.push(`<span class="caption-hero-line hero-level-${heroLine.level}" data-hero-level="${heroLine.level}">${heroWords}</span>`);
      wordIndex = heroLine.word_indexes.at(-1) - 1;
    } else {
      chunks.push(wordMarkup(cue, cueId, cue.words[wordIndex], wordIndex));
    }
  }
  const spatialBeat = spatial?.beatByCueId.get(cue.id) ?? null;
  const classes = ["caption-cue", "clip"];
  const attributes = [];
  if (expressiveEnabled) {
    classes.push("expressive-cue", `layout-${beat.variant}`);
    attributes.push(`data-layout-beat-id="${escapeHtml(beat.id)}"`, `data-layout-variant="${beat.variant}"`);
  }
  if (spatialBeat) {
    classes.push(`placement-${spatialBeat.resolved_placement}`);
    attributes.push(
      `data-spatial-beat-id="${escapeHtml(spatialBeat.id)}"`,
      `data-resolved-placement="${spatialBeat.resolved_placement}"`,
      `data-visual-context="${spatialBeat.visual_context}"`,
    );
    if (new Set(["panel-center", "panel-bottom"]).has(spatialBeat.resolved_placement)) {
      const rect = spatialBeat.allowed_rect;
      attributes.push(
        `data-allowed-x="${rect.x}"`,
        `data-allowed-y="${rect.y}"`,
        `data-allowed-width="${rect.width}"`,
        `data-allowed-height="${rect.height}"`,
        `style="--placement-x:${spatialBeat.anchor.x * 100}%;--placement-y:${spatialBeat.anchor.y * 100}%;--placement-max-width:${rect.width * 100}%"`,
      );
    }
  }
  const cueDuration = Math.max(0.001, Number(cue.end) - Number(cue.start));
  const attributeSuffix = attributes.length ? ` ${attributes.join(" ")}` : "";
  return `<div id="${cueId}" class="${classes.join(" ")}"${attributeSuffix} data-start="${Number(cue.start).toFixed(3)}" data-duration="${cueDuration.toFixed(3)}" data-track-index="2">${chunks.join(" ")}</div>`;
}).join("\n        ");

const cueAnimation = (cueId, start) => {
  const durationSeconds = style.animation.popInFrames / fps;
  if (style.animation.type === "none") {
    return `timeline.set("#${cueId}", { opacity: 1, "--caption-motion-y": "0px" }, ${start.toFixed(3)});`;
  }
  if (style.animation.type === "fade") {
    return `timeline.fromTo("#${cueId}", { opacity: 0, "--caption-motion-y": "0px" }, { opacity: 1, "--caption-motion-y": "0px", duration: ${durationSeconds.toFixed(6)}, ease: "none" }, ${start.toFixed(3)});`;
  }
  return `timeline.fromTo("#${cueId}", { opacity: 0, "--caption-motion-y": "${style.animation.translateYPx}px" }, { opacity: 1, "--caption-motion-y": "0px", duration: ${durationSeconds.toFixed(6)}, ease: "power4.out" }, ${start.toFixed(3)});`;
};

const activeWordProps = style.wordHighlight.mode === "background"
  ? `{ color: "${style.font.color}", opacity: 1, backgroundColor: "${toRgba(style.wordHighlight.backgroundColor, style.wordHighlight.backgroundOpacity)}" }`
  : `{ color: "${style.wordHighlight.activeColor}", opacity: 1, backgroundColor: "transparent" }`;
const completedWordProps = `{ color: "${style.font.color}", opacity: 1, backgroundColor: "transparent" }`;
const expressiveWordProps = (cue, word, wordIndex, phase) => {
  const role = semanticRole(word);
  const heroLine = heroLineForWord(cue, wordIndex);
  const scale = heroLine
    ? heroTreatment.levels[heroLine.level].scale
    : semanticScaleByRole[role];
  if (phase === "active") {
    const karaokeScale = Number(style.wordHighlight.activeScale ?? 1);
    const effectiveScale = Math.max(scale, karaokeScale);
    return JSON.stringify({
      color: heroLine ? heroTreatment.color : style.wordHighlight.activeColor,
      opacity: 1,
      backgroundColor: !heroLine && style.wordHighlight.mode === "background"
        ? toRgba(style.wordHighlight.backgroundColor, style.wordHighlight.backgroundOpacity)
        : "transparent",
      scale: effectiveScale / scale,
    });
  }
  return JSON.stringify({
    color: heroLine ? heroTreatment.color : semanticColor(role),
    opacity: 1,
    backgroundColor: "transparent",
    scale: 1,
  });
};

const timelineCode = captions.map((cue, cueIndex) => {
  const cueId = `caption-cue-${cueIndex + 1}`;
  const start = Number(cue.start);
  const lines = [cueAnimation(cueId, start)];

  if (karaokeEnabled) {
    cue.words.forEach((word, wordIndex) => {
      const wordId = `${cueId}-word-${wordIndex + 1}`;
      const wordStart = Math.max(start, Number(word.start));
      const wordEnd = Math.max(wordStart + 0.001, Number(word.end));
      const wordActiveProps = expressiveEnabled
        ? expressiveWordProps(cue, word, wordIndex, "active")
        : activeWordProps;
      const wordCompletedProps = expressiveEnabled
        ? expressiveWordProps(cue, word, wordIndex, "completed")
        : completedWordProps;
      lines.push(`timeline.set("#${wordId}", ${wordActiveProps}, ${wordStart.toFixed(3)});`);
      lines.push(`timeline.set("#${wordId}", ${wordCompletedProps}, ${wordEnd.toFixed(3)});`);
    });
  }

  lines.push(`timeline.set("#${cueId}", { opacity: 0 }, ${Number(cue.end).toFixed(3)});`);

  return lines.join("\n        ");
}).join("\n\n        ");

const fontSize = Math.max(1, Math.round(height * style.font.sizeRatio));
const renderFontFamily = style.font.family.includes("system-ui")
  ? `"Caption_System", ${style.font.family}`
  : style.font.family;
const paddingBottom = Math.round(height * style.layout.paddingBottomRatio);
const backgroundPaddingX = Math.round(height * style.background.paddingXRatio);
const backgroundPaddingY = Math.round(height * style.background.paddingYRatio);
const backgroundRadius = style.background.shape === "square"
  ? 0
  : style.background.shape === "pill"
    ? 9999
    : Math.round(height * style.background.radiusRatio);
const shadowOffset = Math.round(height * style.effects.shadow.offsetYRatio);
const shadowBlur = Math.round(height * style.effects.shadow.blurRatio);
const strokeWidth = style.stroke.widthPx ?? Math.round(height * style.stroke.widthRatio);
const verticalPosition = style.layout.anchor === "top"
  ? `top: 0; bottom: auto;`
  : style.layout.anchor === "center"
    ? `top: 50%; bottom: auto;`
    : `top: auto; bottom: ${paddingBottom}px;`;
const horizontalPosition = style.layout.align === "left"
  ? `left: 0; right: auto;`
  : style.layout.align === "right"
    ? `left: auto; right: 0;`
    : `left: 50%; right: auto;`;
const staticTranslateX = style.layout.align === "center" ? "-50%" : "0";
const staticTranslateY = style.layout.anchor === "center" ? "-50%" : "0";
const initialWordOpacity = karaokeEnabled ? style.wordHighlight.upcomingOpacity : 1;
const compositionSuffix = [
  style.preset,
  requestedSelection.highlightTheme,
  requestedSelection.backgroundTheme,
  requestedSelection.strokeTheme,
]
  .filter(Boolean)
  .join("-")
  .replaceAll(/[^a-zA-Z0-9-]/g, "-");
const compositionId = `video-add-captions-${compositionSuffix || style.preset}`;
const pageBackground = "transparent";
const expressiveCss = expressiveEnabled ? `
      .caption-cue.expressive-cue {
        width: 88%;
        max-width: 88%;
        text-align: center;
      }

      .caption-cue.layout-bottom-standard {
        ${verticalPosition}
        ${horizontalPosition}
        translate: ${staticTranslateX} ${staticTranslateY};
      }

      .caption-cue.layout-center-emphasis {
        top: 50%;
        bottom: auto;
        left: 50%;
        right: auto;
        translate: -50% -50%;
        font-size: ${Math.max(1, Math.round(fontSize * 1.08))}px;
        line-height: 1.1;
      }

      .expressive-cue .caption-word {
        transform-origin: center center;
        font-size: calc(1em * var(--semantic-scale, 1));
        line-height: 1.35;
        overflow: visible;
        color: var(--semantic-color, ${style.font.color});
      }

      .expressive-cue .caption-word:not(.semantic-normal) {
        text-shadow: 0 0 ${Math.max(2, Math.round(height * 0.012))}px ${toRgba(style.wordHighlight.activeColor, 0.72)}, 0 ${shadowOffset}px ${shadowBlur}px ${toRgba(style.effects.shadow.color, style.effects.shadow.opacity)};
      }

      .caption-hero-line {
        display: block;
        width: 100%;
        color: ${heroTreatment.color};
        font-size: ${heroTreatment.levels[heroTreatment.canonicalLevel].scale}em;
        line-height: ${heroTreatment.lineHeight};
        text-align: center;
        white-space: nowrap;
      }

      .caption-hero-line .caption-word {
        color: inherit;
        font-size: 1em;
      }
` : "";

const placementCss = spatial ? `
      .caption-cue.placement-preset-bottom {
        ${verticalPosition}
        ${horizontalPosition}
        translate: ${staticTranslateX} ${staticTranslateY};
      }

      .caption-cue.placement-frame-center {
        top: 50%;
        bottom: auto;
        left: 50%;
        right: auto;
        translate: -50% -50%;
      }

      .caption-cue.placement-panel-center,
      .caption-cue.placement-panel-bottom {
        top: var(--placement-y);
        bottom: auto;
        left: var(--placement-x);
        right: auto;
        translate: -50% -50%;
        max-width: var(--placement-max-width);
      }
` : "";

const diagnosticsCode = spatial ? `
      window.__captionDiagnostics = () => [...document.querySelectorAll(".caption-cue")]
        .filter((cue) => Number.parseFloat(getComputedStyle(cue).opacity) > 0)
        .map((cue) => {
          const cueRect = cue.getBoundingClientRect();
          const hero = cue.querySelector(".caption-hero-line");
          const heroRect = hero?.getBoundingClientRect() ?? null;
          const allowedRect = cue.dataset.allowedWidth === undefined ? null : {
            x: Number(cue.dataset.allowedX) * ${width},
            y: Number(cue.dataset.allowedY) * ${height},
            width: Number(cue.dataset.allowedWidth) * ${width},
            height: Number(cue.dataset.allowedHeight) * ${height},
          };
          const box = (rect) => rect ? ({ x: rect.x, y: rect.y, width: rect.width, height: rect.height }) : null;
          return {
            cueId: cue.id,
            spatialBeatId: cue.dataset.spatialBeatId,
            visualContext: cue.dataset.visualContext,
            resolvedPlacement: cue.dataset.resolvedPlacement,
            allowedRect,
            cueBbox: box(cueRect),
            heroBbox: box(heroRect),
          };
        });
` : "";

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>${escapeHtml(style.preset)} captions</title>
    <script src="assets/gsap.min.js"></script>
    <style>
      @font-face {
        font-family: "Caption_System";
        src: url("assets/CalSans-Regular.ttf") format("truetype");
        font-weight: 100 900;
        font-style: normal;
        unicode-range: U+E000;
      }

      @font-face {
        font-family: "Cal_Sans";
        src: url("assets/CalSans-Regular.ttf") format("truetype");
        font-weight: 900;
        font-style: normal;
      }

      html,
      body {
        margin: 0;
        width: ${width}px;
        height: ${height}px;
        overflow: hidden;
        background: ${pageBackground};
      }

      #stage {
        position: relative;
        width: ${width}px;
        height: ${height}px;
        overflow: hidden;
        background: ${pageBackground};
      }

      .caption-cue {
        position: absolute;
        ${verticalPosition}
        ${horizontalPosition}
        translate: ${staticTranslateX} ${staticTranslateY};
        width: ${style.background.enabled ? "max-content" : `${style.layout.maxWidth * 100}%`};
        max-width: ${style.layout.maxWidth * 100}%;
        box-sizing: border-box;
        color: ${style.font.color};
        font-family: ${renderFontFamily};
        font-size: ${fontSize}px;
        font-weight: ${style.font.weight};
        line-height: ${style.font.lineHeight};
        letter-spacing: ${style.font.letterSpacing}px;
        text-align: ${style.layout.align};
        opacity: ${style.animation.type === "none" ? 1 : 0};
        transform: translateY(var(--caption-motion-y, ${style.animation.type === "fade" || style.animation.type === "none" ? 0 : style.animation.translateYPx}px));
        background: ${style.background.enabled ? toRgba(style.background.color, style.background.opacity) : "transparent"};
        border-radius: ${style.background.enabled ? backgroundRadius : 0}px;
        padding: ${style.background.enabled ? `${backgroundPaddingY}px ${backgroundPaddingX}px` : "0"};
        -webkit-text-stroke: ${style.stroke.enabled ? `${strokeWidth}px ${toRgba(style.stroke.color, style.stroke.opacity)}` : "0 transparent"};
        paint-order: ${style.stroke.enabled ? "stroke fill" : "normal"};
        text-shadow: ${style.effects.shadow.strength === "none" ? "none" : `0 ${shadowOffset}px ${shadowBlur}px ${toRgba(style.effects.shadow.color, style.effects.shadow.opacity)}, 0 0 2px ${toRgba(style.effects.shadow.color, style.effects.shadow.opacity * 0.83)}`};
      }

      .caption-word {
        display: inline-block;
        max-width: ${Math.round(width * style.layout.maxWidth)}px;
        overflow: hidden;
        color: ${style.font.color};
        opacity: ${initialWordOpacity};
        white-space: nowrap;
        overflow-wrap: normal;
        word-break: normal;
        border-radius: ${Math.round(height * style.wordHighlight.backgroundRadiusRatio)}px;
        padding: ${style.wordHighlight.mode === "background" ? "0 0.08em" : "0"};
      }
${expressiveCss}${placementCss}
    </style>
  </head>
  <body>
    <div
      id="stage"
      data-composition-id="${compositionId}"
      data-start="0"
      data-duration="${duration.toFixed(3)}"
      data-fps="${fpsNumerator}/${fpsDenominator}"
      data-width="${width}"
      data-height="${height}"
    >
      ${cueMarkup}
    </div>
    <script>
      const timeline = gsap.timeline({ paused: true });
      ${timelineCode}
      window.__timelines = window.__timelines || {};
      window.__timelines["${compositionId}"] = timeline;${diagnosticsCode}
    </script>
  </body>
</html>
`;

writeFileSync(join(projectDir, "index.html"), html, "utf8");
if (canonicalPlan && mode === "overlay" && !approvedPlanMode) {
  const toPlanPath = (path) => {
    if (!projectRoot) {
      return resolve(path).split(sep).join("/");
    }
    return relative(join(projectRoot, "work"), resolve(path)).split(sep).join("/");
  };
  const selection = interaction.state.selection;
  const approval = interaction.state.approval;
  const canonicalReviewEvidence = resolveCanonicalReviewEvidence(interaction.state, canonicalPlan);
  const evidenceDetails = (item) => {
    const spatialBeatId = item.spatialBeatId ?? item.spatial_beat_id;
    return {
      path: toPlanPath(item.path),
      sha256: item.sha256,
      ...(item.purposes?.length ? { purposes: item.purposes } : {}),
      ...(spatialBeatId ? {
        spatial_beat_id: spatialBeatId,
        visual_context: item.visualContext ?? item.visual_context,
        requested_variant: item.requestedVariant ?? item.requested_variant,
        resolved_placement: item.resolvedPlacement ?? item.resolved_placement,
        background_sha256: item.backgroundSha256 ?? item.background_sha256,
        caption_bbox: item.captionBbox ?? item.caption_bbox,
        hero_bbox: item.heroBbox ?? item.hero_bbox,
        clearance_status: item.clearanceStatus ?? item.clearance_status,
      } : {}),
      ...((item.heroLine ?? item.hero_line) ? { hero_line: item.heroLine ?? item.hero_line } : {}),
    };
  };
  canonicalPlan.style = {
    status: "approved",
    selection_mode: interaction.state.decisionMode,
    selection_rationale: selection.rationale ?? `Human selected ${selection.choiceId}.`,
    choice_id: selection.choiceId,
    preset: style.preset,
    highlight_theme: requestedSelection.highlightTheme ?? null,
    background_theme: requestedSelection.backgroundTheme ?? null,
    stroke_theme: requestedSelection.strokeTheme ?? null,
    karaoke,
    resolved: style,
  };
  canonicalPlan.review = {
    status: "approved",
    approval_actor: approval.actor ?? interaction.state.decisionMode,
    approval_rationale: approval.rationale ?? "Human approval recorded by the caption interaction receipt.",
    approved_at: approval.recordedAt,
    evidence: canonicalReviewEvidence.delivery.map((item) => toPlanPath(item.path)),
    evidence_details: canonicalReviewEvidence.delivery.map(evidenceDetails),
    ...(canonicalReviewEvidence.machineDocument ? {
      representative_evidence: canonicalReviewEvidence.representative.map((item) => toPlanPath(item.path)),
      representative_evidence_details: canonicalReviewEvidence.representative.map(evidenceDetails),
      machine_evidence_document: {
        path: toPlanPath(canonicalReviewEvidence.machineDocument.path),
        sha256: canonicalReviewEvidence.machineDocument.sha256,
        sample_count: canonicalReviewEvidence.machineDocument.sampleCount,
      },
    } : {}),
    ...(spatial ? { spatial_context_sha256: spatial.sha256 } : {}),
  };
  canonicalPlan.renderer_recipe = {
    ...canonicalPlan.renderer_recipe,
    engine: "hyperframes",
    composition: canonicalPlan.renderer_recipe?.composition ?? "cache/captions/index.html",
    asset: canonicalPlan.renderer_recipe?.asset ?? "cache/captions/overlay-frames",
    asset_type: "image-sequence",
    pattern: canonicalPlan.renderer_recipe?.pattern ?? "frame_%06d.png",
    start_number: canonicalPlan.renderer_recipe?.start_number ?? 1,
    fps: { num: fpsNumerator, den: fpsDenominator },
    runtime_assets: runtimeAssets,
  };
  writeFileSync(captionsPath, `${JSON.stringify(canonicalPlan, null, 2)}\n`, "utf8");
  if (projectRoot) {
    const summaryDir = join(projectRoot, "review", "05-captions");
    const summaryPath = join(summaryDir, "captions-summary.md");
    mkdirSync(summaryDir, { recursive: true });
    const existing = existsSync(summaryPath) ? readFileSync(summaryPath, "utf8") : "# Caption Review\n";
    const base = existing.split(/\r?\n## Approval\r?\n/, 1)[0].trimEnd();
    const oneLine = (value) => String(value ?? "").replaceAll(/\s+/g, " ").trim();
    const approvalLines = [
      base,
      "",
      "## Approval",
      "",
      `- Style: \`${selection.choiceId}\``,
      `- Preset: \`${style.preset}\``,
      `- Karaoke: \`${karaoke ? "on" : "off"}\``,
      `- Decision mode: \`${interaction.state.decisionMode}\``,
      `- Selection rationale: ${oneLine(canonicalPlan.style.selection_rationale)}`,
      `- Approval actor: \`${canonicalPlan.review.approval_actor}\``,
      `- Approval rationale: ${oneLine(canonicalPlan.review.approval_rationale)}`,
      `- Preview evidence: ${canonicalPlan.review.evidence.length} hash-bound files`,
      "- Approval binding validation: pass",
      "- Formal overlay project generation: pass",
      "- Rendered-frame and shared-delivery checks remain required before operation verification.",
      "",
    ];
    writeFileSync(summaryPath, approvalLines.join("\n"), "utf8");
  }
}

const selectionRecord = interaction?.state.selection ?? {
  choiceId: canonicalPlan.style.choice_id,
  skipped: false,
};
const interactionMeta = interaction ? {
  statePath: interaction.statePath,
  phase: interaction.state.phase,
  decisionMode: interaction.state.decisionMode,
  selectionId: interaction.state.selection.choiceId,
  selectionResponse: interaction.state.selection.response ?? null,
  sourceSha256: interaction.state.sourceVideo.sha256,
  captionsSha256: interaction.state.captions.sha256,
  overridesPath,
  overridesSha256: interaction.currentOverridesHash,
} : null;
writeFileSync(join(projectDir, "project-meta.json"), JSON.stringify({
  sourceVideo,
  captionsPath,
  width,
  height,
  fps,
  fpsRational: { num: fpsNumerator, den: fpsDenominator },
  duration,
  cueCount: captions.length,
  approvedPlan: approvedPlanMode,
  selection: {
    choiceId: selectionRecord.choiceId,
    skipped: selectionRecord.skipped,
    preset: style.preset,
    highlightTheme: requestedSelection.highlightTheme ?? null,
    backgroundTheme: requestedSelection.backgroundTheme ?? null,
    strokeTheme: requestedSelection.strokeTheme ?? null,
    karaoke,
    mode,
  },
  interaction: interactionMeta,
  runtimeAssets,
  resolvedStyle: style,
  ...(spatial ? {
    spatialContext: {
      path: spatial.path,
      sha256: spatial.sha256,
      placementBeats: spatial.context.placement_beats,
    },
  } : {}),
  ...(expressiveEnabled ? {
    expressiveTreatments: {
      configPath: captionStyleConfigPath,
      configSha256: hashFile(captionStyleConfigPath),
      value: captionExpressiveTreatments,
    },
    presentation: {
      mode: "expressive",
      layoutBeatCount: presentationSummary.layoutBeatCount,
      layoutBeats: canonicalPlan.presentation.layout_beats,
      heroLines: presentationSummary.heroLines,
      semanticRoles: [...semanticRoles],
      coexistenceMode: karaokeEnabled ? "semantic-plus-karaoke" : "semantic-only",
      combinedScaleRule: karaokeEnabled ? combinedScaleRule : null,
    },
  } : {}),
}, null, 2), "utf8");

console.log(`[hyperframes-captions] generated ${captions.length} cues`);
console.log(`[hyperframes-captions] selection=${selectionRecord.choiceId} style=${style.preset} karaoke=${karaoke} mode=${mode}`);
if (presentationSummary.mode === "expressive") {
  console.log(`[hyperframes-captions] presentation=expressive layout-beats=${presentationSummary.layoutBeatCount} coexistence=${karaokeEnabled ? "semantic-plus-karaoke" : "semantic-only"}`);
  if (karaokeEnabled) console.log(`[hyperframes-captions] combined-scale-rule=${combinedScaleRule}`);
}
console.log(`[hyperframes-captions] ${width}x${height} @ ${fps}fps, ${duration.toFixed(3)}s`);
console.log(`[hyperframes-captions] ${join(projectDir, "index.html")}`);
