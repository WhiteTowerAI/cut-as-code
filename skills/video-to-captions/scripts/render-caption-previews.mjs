import { existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { previewConfig } from "../examples/preview-config.ts";

const args = new Set(process.argv.slice(2));
const dryRun = args.has("--dry-run");
const gridOnly = args.has("--grid");
const fps = 24;
const frame = Math.round(previewConfig.timeSec * fps);
const entryPoint = "examples/preview-index.tsx";

const required = [entryPoint];
const missing = required.filter((path) => !existsSync(path));
const remotionBin = process.env.REMOTION_BIN ?? (process.platform === "win32" ? "npx.cmd" : "npx");
const remotionArgs = process.env.REMOTION_BIN ? [] : ["remotion"];

if (missing.length > 0 && !dryRun) {
  console.error(`[captions] missing Remotion preview inputs: ${missing.join(", ")}`);
  console.error("[captions] run this from the video-to-captions skill directory.");
  process.exit(1);
}

if (!dryRun) {
  mkdirSync(previewConfig.outputDir, { recursive: true });
  for (const name of readdirSync(previewConfig.outputDir)) {
    if (gridOnly) {
      if (/^preview-grid-.+\.png$/.test(name)) {
        rmSync(`${previewConfig.outputDir}/${name}`);
      }
    } else if (/^(preview-.+\.png|props-.+\.json)$/.test(name)) {
      rmSync(`${previewConfig.outputDir}/${name}`);
    }
  }
}

const runCommand = (command) => {
  if (dryRun) {
    console.log(command.join(" "));
    return;
  }

  const result = spawnSync(command[0], command.slice(1), { stdio: "inherit", shell: process.platform === "win32" });
  if (result.error) {
    console.error(`[captions] failed to run Remotion: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
};

if (gridOnly) {
  const candidateById = new Map(previewConfig.candidates.map((candidate) => [candidate.id, candidate]));
  const contactSheetConfig = {
    grids: Object.entries(previewConfig.grids).map(([gridId, grid]) => ({
      id: gridId,
      columns: grid.columns,
      padding: gridId === "shorts" ? 24 : 24,
      gap: gridId === "shorts" ? 24 : 24,
      outputFile: grid.outputFile,
      items: grid.candidateIds.map((id) => {
        if (!candidateById.has(id)) {
          throw new Error(`[captions] missing preview grid candidate: ${id}`);
        }
        return {
          label: id,
          file: `${previewConfig.outputDir}/preview-${id}.png`,
        };
      }),
    })),
  };
  const contactSheetConfigPath = `${previewConfig.outputDir}/props-contact-sheets.json`;
  if (!dryRun) {
    writeFileSync(contactSheetConfigPath, JSON.stringify(contactSheetConfig, null, 2));
  }
  runCommand([
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "scripts/build-preview-contact-sheets.ps1",
    "-ConfigPath",
    contactSheetConfigPath,
  ]);
  process.exit(0);
}

for (const candidate of previewConfig.candidates) {
  const compositionId = candidate.compositionId ?? "CaptionPreview";
  const out = `${previewConfig.outputDir}/preview-${candidate.id}.png`;
  const props = {
    preset: candidate.preset,
    karaoke: candidate.karaoke,
    overrides: candidate.overrides,
    timeSec: previewConfig.timeSec,
    sampleText: candidate.sampleText ?? previewConfig.sampleText,
  };
  const propsPath = `${previewConfig.outputDir}/props-${candidate.id}.json`;
  if (!dryRun) {
    writeFileSync(propsPath, JSON.stringify(props, null, 2));
  }
  const command = [
    remotionBin,
    ...remotionArgs,
    "still",
    entryPoint,
    compositionId,
    out,
    `--frame=${frame}`,
    `--props=${propsPath}`,
  ];

  runCommand(command);
}
