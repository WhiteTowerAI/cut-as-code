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

$overlayIsDirectory = Test-Path -LiteralPath $overlay -PathType Container
$overlayIsWebm = -not $overlayIsDirectory -and [System.IO.Path]::GetExtension($overlay).Equals(".webm", [System.StringComparison]::OrdinalIgnoreCase)
$overlayFormat = if ($overlayIsWebm) { "yuv420" } else { "rgb" }

$ffmpegArgs = @("-y", "-i", $source)
if ($overlayIsDirectory) {
  $firstFrame = Get-ChildItem -LiteralPath $overlay -Filter "frame_*.png" -File | Sort-Object Name | Select-Object -First 1
  if (-not $firstFrame) {
    throw "Overlay frame directory contains no frame_*.png files: $overlay"
  }
  $frameRate = (& ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 $source).Trim()
  if ($LASTEXITCODE -ne 0 -or -not $frameRate) {
    throw "Could not read source frame rate"
  }
  $ffmpegArgs += @("-framerate", $frameRate, "-start_number", "1", "-i", (Join-Path $overlay "frame_%06d.png"))
}
elseif ($overlayIsWebm) {
  $ffmpegArgs += @("-c:v", "libvpx-vp9")
  $ffmpegArgs += @("-i", $overlay)
}
else {
  $ffmpegArgs += @("-i", $overlay)
}
$ffmpegArgs += @(
  "-filter_complex", "[0:v][1:v]overlay=0:0:format=${overlayFormat}:eof_action=pass[v]",
  "-map", "[v]",
  "-map", "0:a?",
  "-c:v", "libx264",
  "-preset", "medium",
  "-crf", "18",
  "-pix_fmt", "yuv420p",
  "-c:a", "copy",
  "-movflags", "+faststart",
  $output
)

& ffmpeg @ffmpegArgs

if ($LASTEXITCODE -ne 0) {
  throw "ffmpeg caption overlay composite failed with exit code $LASTEXITCODE"
}

Write-Host "[captions] wrote composited video: $output"
