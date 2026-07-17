import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, extname, resolve } from "node:path";
import {
  galleryPath,
  hashFile,
  hashJson,
  readInteractionState,
  resolveGallerySelection,
} from "./caption_interaction_state.mjs";

const rawArgs = process.argv.slice(2);
const command = rawArgs.shift();

const usage = `Usage:
  node caption_interaction.mjs start --state <json> --source <video> --captions <json> [--no-open true] [--force true]
  node caption_interaction.mjs select --state <json> --response <combination-id|跳过>
  node caption_interaction.mjs preview-ready --state <json> --project-meta <json> --evidence <png1,png2,png3,png4,...>
  node caption_interaction.mjs adjust --state <json> --response <user-feedback>
  node caption_interaction.mjs confirm --state <json> --response 确认渲染
  node caption_interaction.mjs status --state <json>`;

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
  writeFileSync(resolve(statePath), `${JSON.stringify(state, null, 2)}\n`, "utf8");
};

const nextQuestion = (state) => {
  if (state.phase === "awaiting_style_selection") {
    return [
      "字幕样式库已在系统浏览器中打开。",
      "请浏览全部 25 种样式，然后只回复一个组合 ID，例如 pill-yellow。",
      "如果不想选择样式，请明确回复：跳过。此时采用默认 clean。",
      "收到有效组合 ID 或明确的“跳过”之前，流程不会继续。",
    ].join("\n");
  }
  if (state.phase === "style_selected") {
    return `已记录样式 ${state.selection.choiceId}。现在只能生成真实视频预览，不能生成完整成片。`;
  }
  if (state.phase === "awaiting_preview_confirmation") {
    return [
      "请检查真实视频上的字幕预览。",
      "满意时请明确回复：确认渲染。",
      "不满意时请说明需要调整的字号、位置、颜色、背景、描边或 Karaoke。",
      "收到明确的“确认渲染”之前，不会生成完整字幕层和最终视频。",
    ].join("\n");
  }
  return "用户已经明确确认渲染，可以生成完整字幕层和最终视频。";
};

const appendHistory = (state, event, details = {}) => {
  state.history.push({ event, at: now(), ...details });
};

const openGallery = () => {
  const escapedPath = galleryPath.replaceAll("'", "''");
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

    const state = {
      schemaVersion: 1,
      skill: "video-add-captions",
      phase: "awaiting_style_selection",
      createdAt: now(),
      updatedAt: now(),
      galleryPath,
      sourceVideo: { path: sourceVideo, sha256: hashFile(sourceVideo) },
      captions: { path: captions, sha256: hashFile(captions) },
      selection: null,
      preview: null,
      approval: null,
      history: [],
    };
    appendHistory(state, "interaction_started");
    writeState(statePath, state);
    if (options.noOpen !== "true") {
      openGallery();
    }
    console.log(nextQuestion(state));
    console.log(`[caption-interaction] state=${statePath}`);
  } else if (command === "select") {
    const statePath = requireOption(options, "state");
    const { state } = readInteractionState(statePath);
    if (!new Set(["awaiting_style_selection", "style_selected"]).has(state.phase)) {
      throw new Error(`Style selection is not allowed during phase ${state.phase}.`);
    }
    const selection = resolveGallerySelection(requireOption(options, "response"));
    state.phase = "style_selected";
    state.updatedAt = now();
    state.selection = { ...selection, recordedAt: now() };
    state.preview = null;
    state.approval = null;
    appendHistory(state, "style_selected", {
      response: selection.response,
      choiceId: selection.choiceId,
      skipped: selection.skipped,
    });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "preview-ready") {
    const statePath = requireOption(options, "state");
    const { state, statePath: resolvedStatePath } = readInteractionState(statePath);
    if (state.phase !== "style_selected") {
      throw new Error(`Preview evidence can only be recorded during phase style_selected. Current phase: ${state.phase}`);
    }
    const projectMetaPath = resolve(requireOption(options, "projectMeta"));
    const evidencePaths = requireOption(options, "evidence")
      .split(",")
      .map((value) => resolve(value.trim()))
      .filter(Boolean);
    if (evidencePaths.length < 4) {
      throw new Error("At least four preview screenshots are required: early, middle, late, and no-caption.");
    }
    for (const evidencePath of evidencePaths) {
      if (!existsSync(evidencePath) || !new Set([".png", ".jpg", ".jpeg", ".webp"]).has(extname(evidencePath).toLowerCase())) {
        throw new Error(`Preview evidence must be an existing image: ${evidencePath}`);
      }
    }
    const projectMeta = JSON.parse(readFileSync(projectMetaPath, "utf8"));
    if (resolve(projectMeta.interaction?.statePath ?? "") !== resolvedStatePath) {
      throw new Error("Preview project metadata is not bound to this interaction state.");
    }
    if (projectMeta.interaction?.selectionId !== state.selection.choiceId) {
      throw new Error("Preview project selection differs from the user's recorded selection.");
    }

    state.phase = "awaiting_preview_confirmation";
    state.updatedAt = now();
    state.preview = {
      recordedAt: now(),
      projectMetaPath,
      projectMetaSha256: hashFile(projectMetaPath),
      overridesSha256: projectMeta.interaction.overridesSha256 ?? null,
      evidence: evidencePaths.map((path) => ({ path, sha256: hashFile(path) })),
      evidenceSignature: hashJson(evidencePaths.map((path) => ({ path, sha256: hashFile(path) }))),
    };
    state.approval = null;
    appendHistory(state, "preview_presented", { evidenceCount: evidencePaths.length });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "adjust") {
    const statePath = requireOption(options, "state");
    const { state } = readInteractionState(statePath);
    if (state.phase !== "awaiting_preview_confirmation") {
      throw new Error(`Adjustment feedback is only accepted while awaiting preview confirmation. Current phase: ${state.phase}`);
    }
    const response = requireOption(options, "response").trim();
    if (!response || response === "确认渲染") {
      throw new Error("Adjustment feedback must describe a change and cannot equal the render confirmation phrase.");
    }
    state.phase = "style_selected";
    state.updatedAt = now();
    state.preview = null;
    state.approval = null;
    appendHistory(state, "preview_adjustment_requested", { response });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "confirm") {
    const statePath = requireOption(options, "state");
    const { state } = readInteractionState(statePath);
    if (state.phase !== "awaiting_preview_confirmation") {
      throw new Error(`Render confirmation is only accepted after preview evidence. Current phase: ${state.phase}`);
    }
    const response = requireOption(options, "response").trim();
    if (response !== "确认渲染") {
      throw new Error('Render approval requires the exact user response "确认渲染".');
    }
    state.phase = "render_approved";
    state.updatedAt = now();
    state.approval = {
      response,
      recordedAt: now(),
      selectionId: state.selection.choiceId,
      previewEvidenceSignature: state.preview.evidenceSignature,
    };
    appendHistory(state, "render_approved", { response });
    writeState(statePath, state);
    console.log(nextQuestion(state));
  } else if (command === "status") {
    const { state, statePath } = readInteractionState(requireOption(options, "state"));
    console.log(JSON.stringify({
      statePath,
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
