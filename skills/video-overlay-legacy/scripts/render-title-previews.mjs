import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { titleOverlayConfig } from "../examples/overlay-config.ts";
import { resolveTitleOverlayStyle } from "../examples/overlay-style-resolver.ts";

const args = new Set(process.argv.slice(2));
const themeArg = process.argv.find((arg) => arg.startsWith("--theme="))?.split("=")[1];
const configPath = process.argv.find((arg) => arg.startsWith("--config-json="))?.split("=")[1];
const metaPath = process.argv.find((arg) => arg.startsWith("--source-meta="))?.split("=")[1];
const allThemes = args.has("--all") || !themeArg;
const themes = allThemes ? ["green", "yellow", "orange"] : [themeArg];
const outDir = "out/title-previews";
const activeConfig = configPath ? JSON.parse(readFileSync(configPath, "utf8")) : titleOverlayConfig;
const meta = JSON.parse(readFileSync(metaPath ?? new URL("../examples/source-meta.json.example", import.meta.url), "utf8"));

mkdirSync(outDir, { recursive: true });

const escapeXml = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const estimateCharsPerLine = (fontPx, maxWidthPx) =>
  Math.max(4, Math.floor(maxWidthPx / Math.max(1, fontPx * 0.82)));

const fitFontPx = (fontPx, maxWidthPx, lines) => {
  const longest = Math.max(...lines.map((line) => line.length), 1);
  return Math.floor(Math.min(fontPx, maxWidthPx / Math.max(1, longest * 0.86)));
};

const wrapTitle = (text, maxChars) => {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return { lines: [""], overflow: false };
  }
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
  if (current) {
    lines.push(current);
  }
  return {
    lines,
    overflow: lines.length > 2,
    fullLineCount: lines.length,
  };
};

const alphaHex = (opacity) => {
  const value = Math.max(0, Math.min(255, Math.round(opacity * 255)));
  return value.toString(16).padStart(2, "0");
};

const makeSvg = (theme) => {
  const style = resolveTitleOverlayStyle({
    preset: activeConfig.style.preset,
    theme,
    overrides: activeConfig.style.overrides,
  });
  const width = meta.width;
  const height = meta.height;
  const baseFontPx = Math.round(height * style.font.sizeRatio);
  const maxWidthPx = Math.round(width * style.layout.maxWidthRatio);
  const chars = estimateCharsPerLine(baseFontPx, maxWidthPx);
  const wrap = wrapTitle(activeConfig.title.text, chars);
  const fontPx = fitFontPx(baseFontPx, maxWidthPx, wrap.lines);
  const lineHeight = fontPx * style.font.lineHeight;
  const titleBlockHeight = lineHeight * wrap.lines.length;
  const safeTop = height * (1 - style.layout.bottomCaptionSafeAreaRatio);
  const x = width / 2;
  const centerYRatio = activeConfig.layout.position === "top"
    ? null
    : activeConfig.layout.position === "custom"
      ? activeConfig.layout.customYRatio ?? style.layout.yRatio
      : style.layout.yRatio;
  const y = activeConfig.layout.position === "top"
    ? height * 0.02
    : Math.max(0, Math.min(height * centerYRatio - titleBlockHeight / 2, safeTop - titleBlockHeight));
  const strokePx = Math.max(1, Math.round(width * style.effects.stroke.widthRatio));
  const shadowY = Math.round(height * style.effects.shadow.offsetYRatio);
  const captionSafeY = Math.round(height * (1 - style.layout.bottomCaptionSafeAreaRatio));
  const textRows = wrap.lines.map((line, index) => {
    const ty = y + (index + 0.82) * lineHeight;
    const rectWidth = Math.min(maxWidthPx, Math.max(fontPx * 2.5, line.length * fontPx * 0.62 + fontPx * 0.18));
    const rectHeight = fontPx * 1.02;
    const rectX = x - rectWidth / 2;
    const rectY = ty - fontPx * 0.82;
    return `
      <rect x="${rectX.toFixed(1)}" y="${rectY.toFixed(1)}" width="${rectWidth.toFixed(1)}" height="${rectHeight.toFixed(1)}" rx="${Math.round(fontPx * 0.08)}" fill="${style.accent.backgroundColor}${alphaHex(style.accent.backgroundOpacity)}"/>
      <text x="${x}" y="${ty.toFixed(1)}" text-anchor="middle"
        font-family="Arial Black, Impact, Arial, sans-serif"
        font-size="${fontPx}" font-weight="${style.font.weight}"
        fill="${style.font.color}"
        stroke="${style.effects.stroke.color}" stroke-width="${strokePx}" paint-order="stroke fill"
        style="filter:url(#shadow);letter-spacing:${style.font.letterSpacing}px">${escapeXml(line)}</text>`;
  }).join("\n");

  const warning = wrap.overflow
    ? `Title wrapped to ${wrap.fullLineCount} estimated lines; preview keeps all lines. Consider shortening if it feels too tall.`
    : "";

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <linearGradient id="bg" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color="#263241"/>
      <stop offset="45%" stop-color="#52606d"/>
      <stop offset="100%" stop-color="#151922"/>
    </linearGradient>
    <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="${shadowY}" stdDeviation="${Math.round(height * style.effects.shadow.blurRatio * 0.35)}" flood-color="#000000" flood-opacity="${style.effects.shadow.opacity}"/>
    </filter>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <rect x="${Math.round(width * 0.11)}" y="${Math.round(height * 0.08)}" width="${Math.round(width * 0.78)}" height="${Math.round(height * 0.53)}" rx="${Math.round(width * 0.03)}" fill="#ffffff14" stroke="#ffffff38" stroke-width="2"/>
  <rect x="${Math.round(width * 0.1)}" y="${Math.round(captionSafeY + height * 0.05)}" width="${Math.round(width * 0.8)}" height="${Math.round(height * 0.1)}" rx="${Math.round(width * 0.015)}" fill="#00000030" stroke="#ffffff66" stroke-width="2" stroke-dasharray="12 10"/>
  <text x="${Math.round(width * 0.5)}" y="${Math.round(captionSafeY + height * 0.105)}" text-anchor="middle" font-family="Arial, sans-serif" font-size="${Math.round(height * 0.022)}" fill="#ffffff99">bottom captions safe area</text>
  ${textRows}
</svg>`;

  return {
    svg,
    warning,
    summary: {
      theme,
      preset: style.preset,
      width,
      height,
      position: activeConfig.layout.position,
      centerYRatio: centerYRatio === null ? null : Number(centerYRatio.toFixed(3)),
      topYRatio: Number((y / height).toFixed(3)),
      bottomCaptionSafeAreaRatio: style.layout.bottomCaptionSafeAreaRatio,
      titleLines: wrap.lines,
      overflow: wrap.overflow,
      warning,
      accentColor: style.accent.color,
      accentOpacity: style.accent.backgroundOpacity,
      fontSizePx: fontPx,
      maxWidthPx,
    },
  };
};

const renderPngFromSvg = (svgPath, pngPath) => {
  const ps = `
Add-Type -AssemblyName System.Drawing
$svg = Get-Content -Raw -LiteralPath '${svgPath.replaceAll("'", "''")}'
if ($svg -notmatch 'width="(?<w>\\d+)" height="(?<h>\\d+)"') { throw 'SVG width/height not found' }
$w = [int]$Matches.w
$h = [int]$Matches.h
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush ([System.Drawing.Rectangle]::new(0,0,$w,$h)), ([System.Drawing.Color]::FromArgb(255,38,50,65)), ([System.Drawing.Color]::FromArgb(255,21,25,34)), 90
$g.FillRectangle($bg, 0, 0, $w, $h)
$panelPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(56,255,255,255)), 2
$panelBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(20,255,255,255))
$g.FillRectangle($panelBrush, [int]($w*.11), [int]($h*.08), [int]($w*.78), [int]($h*.53))
$g.DrawRectangle($panelPen, [int]($w*.11), [int]($h*.08), [int]($w*.78), [int]($h*.53))
$safeY = [int]($h * 0.68)
$safePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(102,255,255,255)), 2
$safePen.DashPattern = @(12,10)
$safeBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(48,0,0,0))
$g.FillRectangle($safeBrush, [int]($w*.1), [int]($safeY + $h*.05), [int]($w*.8), [int]($h*.1))
$g.DrawRectangle($safePen, [int]($w*.1), [int]($safeY + $h*.05), [int]($w*.8), [int]($h*.1))
$fontSmall = New-Object System.Drawing.Font 'Arial', ([single]($h*.022)), ([System.Drawing.FontStyle]::Regular), ([System.Drawing.GraphicsUnit]::Pixel)
$smallBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(153,255,255,255))
$fmt = New-Object System.Drawing.StringFormat
$fmt.Alignment = [System.Drawing.StringAlignment]::Center
$g.DrawString('bottom captions safe area', $fontSmall, $smallBrush, [System.Drawing.RectangleF]::new(0, [single]($safeY + $h*.085), [single]$w, [single]80), $fmt)
$summary = Get-Content -Raw -LiteralPath '${pngPath.replaceAll(".png", ".json").replaceAll("'", "''")}' | ConvertFrom-Json
$font = New-Object System.Drawing.Font 'Arial Black', ([single]$summary.fontSizePx), ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$textFmt = New-Object System.Drawing.StringFormat
$textFmt.Alignment = [System.Drawing.StringAlignment]::Center
$textFmt.LineAlignment = [System.Drawing.StringAlignment]::Center
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
  $drawRect = [System.Drawing.RectangleF]::new(0, [single]($y - $summary.fontSizePx*.05 + $h*.014), [single]$w, $lineHeight)
  $g.DrawString($line, $font, $shadowBrush, $drawRect, $textFmt)
  $drawRect = [System.Drawing.RectangleF]::new(0, [single]($y - $summary.fontSizePx*.05), [single]$w, $lineHeight)
  $g.DrawString($line, $font, $textBrush, $drawRect, $textFmt)
}
$bmp.Save('${pngPath.replaceAll("'", "''")}', [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
`;
  const result = spawnSync("powershell", ["-NoProfile", "-Command", ps], { stdio: "inherit" });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
};

const outputs = [];
for (const theme of themes) {
  const { svg, summary } = makeSvg(theme);
  const svgPath = `${outDir}/preview-${theme}.svg`;
  const pngPath = `${outDir}/preview-${theme}.png`;
  const summaryPath = `${outDir}/preview-${theme}.json`;
  writeFileSync(svgPath, svg, "utf8");
  writeFileSync(summaryPath, JSON.stringify(summary, null, 2), "utf8");
  renderPngFromSvg(svgPath, pngPath);
  outputs.push({ theme, pngPath, svgPath, summaryPath, warning: summary.warning });
}

console.log("[video-overlay] title preview generated");
console.log(JSON.stringify(outputs, null, 2));
