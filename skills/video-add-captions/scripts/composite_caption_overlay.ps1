param(
  [Parameter(Mandatory = $true)]
  [string]$SourceVideo,

  [Parameter(Mandatory = $true)]
  [string]$OverlayVideo,

  [Parameter(Mandatory = $true)]
  [string]$OutputVideo
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$source = (Resolve-Path -LiteralPath $SourceVideo).Path
$overlay = (Resolve-Path -LiteralPath $OverlayVideo).Path
$output = [System.IO.Path]::GetFullPath($OutputVideo)

if ($output -eq $source -or $output -eq $overlay) {
  throw "OutputVideo must not overwrite either input"
}

$outputDir = Split-Path -Parent $output
if (-not (Test-Path -LiteralPath $outputDir)) {
  New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$overlayIsWebm = [System.IO.Path]::GetExtension($overlay).Equals(".webm", [System.StringComparison]::OrdinalIgnoreCase)
$overlayFormat = if ($overlayIsWebm) { "yuv420" } else { "auto" }

$ffmpegArgs = @("-y", "-i", $source)
if ($overlayIsWebm) {
  $ffmpegArgs += @("-c:v", "libvpx-vp9")
}
$ffmpegArgs += @(
  "-i", $overlay,
  "-filter_complex", "[0:v][1:v]overlay=0:0:format=${overlayFormat}:eof_action=pass[v]",
  "-map", "[v]",
  "-map", "0:a?",
  "-c:v", "libx264",
  "-preset", "medium",
  "-crf", "18",
  "-pix_fmt", "yuv420p",
  "-color_range", "tv",
  "-colorspace", "bt709",
  "-color_trc", "bt709",
  "-color_primaries", "bt709",
  "-c:a", "copy",
  $output
)

& ffmpeg @ffmpegArgs

if ($LASTEXITCODE -ne 0) {
  throw "ffmpeg caption overlay composite failed with exit code $LASTEXITCODE"
}

Write-Host "[captions] wrote composited video: $output"
