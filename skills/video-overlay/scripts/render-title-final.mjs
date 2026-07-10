import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { titleOverlayConfig as defaultTitleOverlayConfig } from "../examples/overlay-config.ts";
import { resolveTitleOverlayStyle } from "../examples/overlay-style-resolver.ts";

const argv = process.argv.slice(2);
const getArg = (name) => argv.find((arg) => arg.startsWith(`${name}=`))?.slice(name.length + 1);
const hasArg = (name) => argv.includes(name);

const defaultFfmpeg = "F:/project/open-recut/TEST/videos/color-grade/after/2/.tools/ffmpeg-8.1.2-essentials_build/bin/ffmpeg.exe";
const defaultFfprobe = "F:/project/open-recut/TEST/videos/color-grade/after/2/.tools/ffmpeg-8.1.2-essentials_build/bin/ffprobe.exe";
const ffmpeg = getArg("--ffmpeg") ?? (existsSync(defaultFfmpeg) ? defaultFfmpeg : "ffmpeg");
const ffprobe = getArg("--ffprobe") ?? (existsSync(defaultFfprobe) ? defaultFfprobe : "ffprobe");
const outDir = getArg("--out-dir") ?? "out/title-final";
const configPath = getArg("--config-json");
const titleOverlayConfig = configPath ? JSON.parse(readFileSync(configPath, "utf8")) : defaultTitleOverlayConfig;
const mockSource = hasArg("--mock-source");
const inputPath = getArg("--input") ?? (mockSource ? `${outDir}/mock-source.mp4` : titleOverlayConfig.source.videoPath);
const outputPath = getArg("--output") ?? `${outDir}/titled.mp4`;
const overlayMovPath = `${outDir}/title-overlay.mov`;
const overlayPngPath = `${outDir}/title-overlay.png`;
const summaryPath = `${outDir}/title-overlay-render-summary.json`;
const theme = getArg("--theme") ?? titleOverlayConfig.style.theme;
const spotTimesArg = getArg("--spot-times");

mkdirSync(outDir, { recursive: true });

const run = (command, label) => {
  const result = spawnSync(command[0], command.slice(1), { stdio: "pipe", encoding: "utf8", shell: false });
  if (result.status !== 0) {
    throw new Error([
      `[video-overlay] ${label} failed`,
      `command: ${command.join(" ")}`,
      result.stdout,
      result.stderr,
    ].filter(Boolean).join("\n"));
  }
  return result.stdout;
};

const runInherit = (command, label) => {
  const result = spawnSync(command[0], command.slice(1), { stdio: "inherit", shell: false });
  if (result.status !== 0) {
    throw new Error(`[video-overlay] ${label} failed: ${command.join(" ")}`);
  }
};

const ffNum = (value) => {
  if (typeof value !== "string") return Number(value);
  if (value.includes("/")) {
    const [a, b] = value.split("/").map(Number);
    return b ? a / b : 0;
  }
  return Number(value);
};

const probe = (path) => {
  const raw = run([
    ffprobe,
    "-v", "error",
    "-print_format", "json",
    "-show_streams",
    "-show_format",
    path,
  ], "ffprobe");
  const data = JSON.parse(raw);
  const video = data.streams.find((stream) => stream.codec_type === "video");
  const audio = data.streams.find((stream) => stream.codec_type === "audio");
  if (!video) {
    throw new Error(`[video-overlay] input has no video stream: ${path}`);
  }
  const duration = Number(data.format?.duration ?? video.duration ?? 0);
  return {
    width: Number(video.width),
    height: Number(video.height),
    fps: ffNum(video.avg_frame_rate || video.r_frame_rate || "0"),
    duration,
    hasAudio: Boolean(audio),
    audioCodec: audio?.codec_name ?? null,
    videoCodec: video.codec_name ?? null,
  };
};

const ensureVertical = (meta, path) => {
  if (!(meta.height > meta.width)) {
    throw new Error(
      `[video-overlay] input is not vertical (${meta.width}x${meta.height}): ${path}. Run video-vertical-reframe first.`
    );
  }
};

const createMockSource = (path) => {
  mkdirSync(dirname(path), { recursive: true });
  runInherit([
    ffmpeg,
    "-y",
    "-f", "lavfi",
    "-i", "testsrc2=size=1080x1920:rate=30:duration=6",
    "-f", "lavfi",
    "-i", "sine=frequency=440:duration=6",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-shortest",
    path,
  ], "mock source generation");
};

const escapePs = (value) => String(value).replaceAll("'", "''");

const estimateCharsPerLine = (fontPx, maxWidthPx) =>
  Math.max(4, Math.floor(maxWidthPx / Math.max(1, fontPx * 0.82)));

const fitFontPx = (fontPx, maxWidthPx, lines) => {
  const longest = Math.max(...lines.map((line) => line.length), 1);
  return Math.floor(Math.min(fontPx, maxWidthPx / Math.max(1, longest * 0.86)));
};

const wrapTitle = (text, maxChars) => {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= maxChars || current === "") {
      current = next;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return {
    lines,
    overflow: lines.length > 2,
    fullLineCount: lines.length,
  };
};

const renderTransparentPng = (pngPath, meta) => {
  const style = resolveTitleOverlayStyle({
    preset: titleOverlayConfig.style.preset,
    theme,
    overrides: titleOverlayConfig.style.overrides,
  });
  const baseFontPx = Math.round(meta.height * style.font.sizeRatio);
  const maxWidthPx = Math.round(meta.width * style.layout.maxWidthRatio);
  const wrap = wrapTitle(titleOverlayConfig.title.text, estimateCharsPerLine(baseFontPx, maxWidthPx));
  const fontPx = fitFontPx(baseFontPx, maxWidthPx, wrap.lines);
  const lineHeight = fontPx * style.font.lineHeight;
  const titleBlockHeight = lineHeight * wrap.lines.length;
  const safeTop = meta.height * (1 - style.layout.bottomCaptionSafeAreaRatio);
  const centerYRatio = titleOverlayConfig.layout.position === "top"
    ? null
    : titleOverlayConfig.layout.position === "custom"
      ? titleOverlayConfig.layout.customYRatio ?? style.layout.yRatio
      : style.layout.yRatio;
  const topYRatio = titleOverlayConfig.layout.position === "top"
    ? 0.02
    : Math.max(0, Math.min(meta.height * centerYRatio - titleBlockHeight / 2, safeTop - titleBlockHeight)) / meta.height;
  const layoutSummary = {
    theme,
    preset: style.preset,
    titleLines: wrap.lines,
    overflow: wrap.overflow,
    warning: wrap.overflow ? `Title wrapped to ${wrap.fullLineCount} estimated lines; final render keeps all lines. Consider shortening if it feels too tall.` : "",
    centerYRatio,
    topYRatio,
    bottomCaptionSafeAreaRatio: style.layout.bottomCaptionSafeAreaRatio,
    accentColor: style.accent.color,
    accentOpacity: style.accent.backgroundOpacity,
    fontSizePx: fontPx,
    maxWidthPx,
  };
  const layoutPath = pngPath.replace(/\.png$/i, ".json");
  writeFileSync(layoutPath, JSON.stringify(layoutSummary, null, 2), "utf8");

  const ps = `
Add-Type -AssemblyName System.Drawing
$summary = Get-Content -Raw -LiteralPath '${escapePs(layoutPath)}' | ConvertFrom-Json
$w = ${meta.width}
$h = ${meta.height}
$bmp = New-Object System.Drawing.Bitmap $w, $h, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::FromArgb(0,0,0,0))
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$font = New-Object System.Drawing.Font 'Arial Black', ([single]$summary.fontSizePx), ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$fmt = New-Object System.Drawing.StringFormat
$fmt.Alignment = [System.Drawing.StringAlignment]::Center
$fmt.LineAlignment = [System.Drawing.StringAlignment]::Center
$accent = [System.Drawing.ColorTranslator]::FromHtml($summary.accentColor)
$accentAlpha = [Math]::Max(0, [Math]::Min(255, [int]([double]$summary.accentOpacity * 255)))
$accentBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb($accentAlpha, $accent.R, $accent.G, $accent.B))
$textBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$shadowBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(190,0,0,0))
$lineHeight = [single]($summary.fontSizePx * 1.02)
$startY = [single]($h * $summary.topYRatio)
for ($i=0; $i -lt $summary.titleLines.Count; $i++) {
  $line = [string]$summary.titleLines[$i]
  $y = $startY + ($i * $lineHeight)
  $rectW = [Math]::Min([single]$summary.maxWidthPx, [Math]::Max([single]($summary.fontSizePx*2.5), [single]($line.Length*$summary.fontSizePx*.62 + $summary.fontSizePx*.18)))
  $rect = [System.Drawing.RectangleF]::new([single](($w-$rectW)/2), $y, $rectW, [single]($summary.fontSizePx*1.02))
  $g.FillRectangle($accentBrush, $rect)
  $shadowRect = [System.Drawing.RectangleF]::new(0, [single]($y - $summary.fontSizePx*.05 + $h*.014), [single]$w, $lineHeight)
  $g.DrawString($line, $font, $shadowBrush, $shadowRect, $fmt)
  $textRect = [System.Drawing.RectangleF]::new(0, [single]($y - $summary.fontSizePx*.05), [single]$w, $lineHeight)
  $g.DrawString($line, $font, $textBrush, $textRect, $fmt)
}
$bmp.Save('${escapePs(pngPath)}', [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
`;
  runInherit(["powershell", "-NoProfile", "-Command", ps], "transparent title PNG render");
  return { style, layoutSummary, layoutPath };
};

const renderOverlayMov = (meta) => {
  runInherit([
    ffmpeg,
    "-y",
    "-loop", "1",
    "-framerate", String(Math.max(1, Math.round(meta.fps || 30))),
    "-t", String(meta.duration),
    "-i", overlayPngPath,
    "-c:v", "qtrle",
    "-pix_fmt", "argb",
    overlayMovPath,
  ], "transparent overlay video render");
};

const compositeFinal = (sourcePath, meta) => {
  const visibility = titleOverlayConfig.visibility;
  const overlayFilter = visibility.mode === "first-n-seconds"
    ? `[0:v][1:v]overlay=shortest=1:format=auto:enable='between(t,0,${visibility.durationSec})'[v]`
    : visibility.mode === "time-range"
      ? `[0:v][1:v]overlay=shortest=1:format=auto:enable='between(t,${visibility.startTimeSec},${visibility.endTimeSec})'[v]`
    : "[0:v][1:v]overlay=shortest=1:format=auto[v]";
  const command = [
    ffmpeg,
    "-y",
    "-i", sourcePath,
    "-i", overlayMovPath,
    "-filter_complex", overlayFilter,
    "-map", "[v]",
    "-map", "0:a?",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", "18",
    "-preset", "veryfast",
    "-c:a", "copy",
    "-movflags", "+faststart",
    outputPath,
  ];
  runInherit(command, "ffmpeg composite");
};

const spotName = (time) => String(time).replace(".", "p").replace(/[^0-9p-]/g, "");

const writeSpotChecks = (sourcePath, meta) => {
  const times = spotTimesArg
    ? Object.fromEntries(spotTimesArg.split(",").map((raw) => {
      const time = Number(raw.trim());
      return [`t${spotName(time)}`, Math.max(0, Math.min(time, Math.max(0, meta.duration - 0.05)))];
    }))
    : {
      early: Math.min(0.5, Math.max(0, meta.duration * 0.1)),
      middle: Math.max(0, meta.duration * 0.5),
      late: Math.max(0, meta.duration - 0.5),
    };
  const stills = {};
  for (const [name, time] of Object.entries(times)) {
    const path = `${outDir}/spot-${name}.png`;
    runInherit([
      ffmpeg,
      "-y",
      "-ss", String(time),
      "-i", sourcePath,
      "-frames:v", "1",
      "-update", "1",
      path,
    ], `spot check ${name}`);
    stills[name] = path;
  }
  return stills;
};

const maybeUseRemotion = () => {
  const remotionBin = process.env.REMOTION_BIN;
  if (!remotionBin || !existsSync(remotionBin)) {
    return { used: false, reason: "REMOTION_BIN not set; used transparent PNG fallback for local verification" };
  }
  return { used: false, reason: "Remotion path is reserved for scaffolded projects; used transparent PNG fallback in skill fixture" };
};

if (mockSource || !existsSync(inputPath)) {
  if (!mockSource) {
    throw new Error(`[video-overlay] input not found: ${inputPath}. Pass --input=VIDEO or --mock-source for fixture render.`);
  }
  createMockSource(inputPath);
}

const inputMeta = probe(inputPath);
ensureVertical(inputMeta, inputPath);

const remotion = maybeUseRemotion();
const { layoutSummary } = renderTransparentPng(overlayPngPath, inputMeta);
renderOverlayMov(inputMeta);
compositeFinal(inputPath, inputMeta);
const outputMeta = probe(outputPath);
const spotChecks = writeSpotChecks(outputPath, outputMeta);

const durationDelta = Math.abs(outputMeta.duration - inputMeta.duration);
const verified = {
  dimensionsMatch: outputMeta.width === inputMeta.width && outputMeta.height === inputMeta.height,
  fpsClose: Math.abs(outputMeta.fps - inputMeta.fps) < 0.05,
  durationClose: durationDelta < 0.15,
  audioCopied: inputMeta.hasAudio && outputMeta.hasAudio,
};

const summary = {
  inputPath,
  outputPath,
  configPath: configPath ?? null,
  generatedConfig: titleOverlayConfig,
  overlayPath: overlayMovPath,
  overlayRenderer: remotion.used ? "remotion" : "transparent-png-fallback",
  overlayRendererNote: remotion.reason,
  title: titleOverlayConfig.title.text,
  titleSource: titleOverlayConfig.title.source,
  theme,
  position: titleOverlayConfig.layout.position,
  visibility: titleOverlayConfig.visibility,
  input: inputMeta,
  output: outputMeta,
  audioCopyStatus: verified.audioCopied ? "copied from input with -c:a copy" : "no input audio stream copied",
  previewPaths: {
    green: "out/title-previews/preview-green.png",
    yellow: "out/title-previews/preview-yellow.png",
    orange: "out/title-previews/preview-orange.png",
  },
  spotCheckStills: spotChecks,
  layout: layoutSummary,
  verification: verified,
};

writeFileSync(summaryPath, JSON.stringify(summary, null, 2), "utf8");
console.log("[video-overlay] final render complete");
console.log(JSON.stringify({ outputPath, summaryPath, spotCheckStills: spotChecks, verification: verified }, null, 2));
