import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import {
  captionBackgroundThemeNames,
  captionHighlightThemeNames,
  captionPresetNames,
  captionStrokeThemeNames,
  resolveCaptionStyle,
  resolveKaraoke,
} from "./caption_style_config.mjs";
import {
  hashFile,
  readInteractionState,
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
  requestedSelection = {
    preset: options.preset ?? recordedSelection.preset,
    highlightTheme: options.highlightTheme ?? recordedSelection.highlightTheme,
    backgroundTheme: options.backgroundTheme ?? recordedSelection.backgroundTheme,
    strokeTheme: options.strokeTheme ?? recordedSelection.strokeTheme,
    karaoke: options.karaoke ?? recordedSelection.karaoke,
  };
  interaction = validateGenerationInteraction({
    statePath: options.interactionState,
    mode,
    sourceVideo,
    captionsPath,
    requestedSelection,
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

const cueMarkup = captions.map((cue, cueIndex) => {
  const cueId = `caption-cue-${cueIndex + 1}`;
  const words = cue.words.map((word, wordIndex) => (
    `<span id="${cueId}-word-${wordIndex + 1}" class="caption-word">${escapeHtml(formatWord(String(word.word).trim()))}</span>`
  )).join(" ");
  const cueDuration = Math.max(0.001, Number(cue.end) - Number(cue.start));
  return `<div id="${cueId}" class="caption-cue clip" data-start="${Number(cue.start).toFixed(3)}" data-duration="${cueDuration.toFixed(3)}" data-track-index="2">${words}</div>`;
}).join("\n        ");

const cueAnimation = (cueId, start) => {
  const durationSeconds = style.animation.popInFrames / fps;
  if (style.animation.type === "none") {
    return `timeline.set("#${cueId}", { opacity: 1, y: 0 }, ${start.toFixed(3)});`;
  }
  if (style.animation.type === "fade") {
    return `timeline.fromTo("#${cueId}", { opacity: 0, y: 0 }, { opacity: 1, y: 0, duration: ${durationSeconds.toFixed(6)}, ease: "none" }, ${start.toFixed(3)});`;
  }
  return `timeline.fromTo("#${cueId}", { opacity: 0, y: ${style.animation.translateYPx} }, { opacity: 1, y: 0, duration: ${durationSeconds.toFixed(6)}, ease: "power4.out" }, ${start.toFixed(3)});`;
};

const activeWordProps = style.wordHighlight.mode === "background"
  ? `{ color: "${style.font.color}", opacity: 1, backgroundColor: "${toRgba(style.wordHighlight.backgroundColor, style.wordHighlight.backgroundOpacity)}" }`
  : `{ color: "${style.wordHighlight.activeColor}", opacity: 1, backgroundColor: "transparent" }`;
const completedWordProps = `{ color: "${style.font.color}", opacity: 1, backgroundColor: "transparent" }`;

const timelineCode = captions.map((cue, cueIndex) => {
  const cueId = `caption-cue-${cueIndex + 1}`;
  const start = Number(cue.start);
  const lines = [cueAnimation(cueId, start)];

  if (karaokeEnabled) {
    cue.words.forEach((word, wordIndex) => {
      const wordId = `${cueId}-word-${wordIndex + 1}`;
      const wordStart = Math.max(start, Number(word.start));
      const wordEnd = Math.max(wordStart + 0.001, Number(word.end));
      lines.push(`timeline.set("#${wordId}", ${activeWordProps}, ${wordStart.toFixed(3)});`);
      lines.push(`timeline.set("#${wordId}", ${completedWordProps}, ${wordEnd.toFixed(3)});`);
    });
  }

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
        transform: translateY(${style.animation.type === "fade" || style.animation.type === "none" ? 0 : style.animation.translateYPx}px);
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
      window.__timelines["${compositionId}"] = timeline;
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
    evidence: interaction.state.preview.evidence.map((item) => toPlanPath(item.path)),
    evidence_details: interaction.state.preview.evidence.map((item) => ({
      path: toPlanPath(item.path),
      sha256: item.sha256,
    })),
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
}, null, 2), "utf8");

console.log(`[hyperframes-captions] generated ${captions.length} cues`);
console.log(`[hyperframes-captions] selection=${selectionRecord.choiceId} style=${style.preset} karaoke=${karaoke} mode=${mode}`);
console.log(`[hyperframes-captions] ${width}x${height} @ ${fps}fps, ${duration.toFixed(3)}s`);
console.log(`[hyperframes-captions] ${join(projectDir, "index.html")}`);
