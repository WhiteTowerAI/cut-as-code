param(
  [Parameter(Mandatory = $true)]
  [string]$ConfigPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

function Resolve-LocalPath {
  param([string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return $Path
  }
  return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Path))
}

function New-Brush {
  param([string]$Hex)
  return New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml($Hex))
}

$configFile = Resolve-LocalPath $ConfigPath
$config = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json

$backgroundBrush = New-Brush "#10131A"
$cellBrush = New-Brush "#171B24"
$labelBrush = New-Brush "#F7F7F2"
$mutedBrush = New-Brush "#242A36"
$fontFamily = New-Object System.Drawing.FontFamily "Arial"

foreach ($grid in $config.grids) {
  $columns = [int]$grid.columns
  $padding = [int]$grid.padding
  $gap = [int]$grid.gap
  $items = @($grid.items)
  if ($items.Count -eq 0) {
    throw "[captions] contact sheet grid has no items: $($grid.id)"
  }

  $loaded = @()
  foreach ($item in $items) {
    $imagePath = Resolve-LocalPath $item.file
    if (-not (Test-Path -LiteralPath $imagePath)) {
      throw "[captions] missing preview image for contact sheet: $imagePath"
    }
    $image = [System.Drawing.Image]::FromFile($imagePath)
    $loaded += [PSCustomObject]@{
      Label = [string]$item.label
      Image = $image
      File = $imagePath
    }
  }

  try {
    $cellImageWidth = ($loaded | ForEach-Object { $_.Image.Width } | Measure-Object -Maximum).Maximum
    $cellImageHeight = ($loaded | ForEach-Object { $_.Image.Height } | Measure-Object -Maximum).Maximum
    $labelHeight = [Math]::Max(48, [Math]::Round($cellImageHeight * 0.035))
    $cellWidth = [int]$cellImageWidth
    $cellHeight = [int]($labelHeight + $cellImageHeight)
    $rows = [int][Math]::Ceiling($loaded.Count / $columns)
    $sheetWidth = [int]($padding * 2 + $columns * $cellWidth + ($columns - 1) * $gap)
    $sheetHeight = [int]($padding * 2 + $rows * $cellHeight + ($rows - 1) * $gap)

    $sheet = New-Object System.Drawing.Bitmap $sheetWidth, $sheetHeight
    $graphics = [System.Drawing.Graphics]::FromImage($sheet)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

    try {
      $graphics.FillRectangle($backgroundBrush, 0, 0, $sheetWidth, $sheetHeight)
      $labelFont = New-Object System.Drawing.Font $fontFamily, ([Math]::Max(26, [Math]::Round($labelHeight * 0.42))), ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)

      for ($index = 0; $index -lt $loaded.Count; $index++) {
        $row = [int][Math]::Floor($index / $columns)
        $column = $index % $columns
        $x = [int]($padding + $column * ($cellWidth + $gap))
        $y = [int]($padding + $row * ($cellHeight + $gap))
        $item = $loaded[$index]

        $graphics.FillRectangle($cellBrush, $x, $y, $cellWidth, $cellHeight)
        $graphics.FillRectangle($mutedBrush, $x, $y, $cellWidth, $labelHeight)
        $graphics.DrawString($item.Label, $labelFont, $labelBrush, ($x + 18), ($y + [Math]::Round($labelHeight * 0.24)))

        $imageX = [int]($x + [Math]::Round(($cellWidth - $item.Image.Width) / 2))
        $imageY = [int]($y + $labelHeight + [Math]::Round(($cellImageHeight - $item.Image.Height) / 2))
        $graphics.DrawImage($item.Image, $imageX, $imageY, $item.Image.Width, $item.Image.Height)
      }

      $outPath = Resolve-LocalPath $grid.outputFile
      $outDir = Split-Path -Parent $outPath
      if (-not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir | Out-Null
      }
      $sheet.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
      Write-Host "[captions] wrote contact sheet: $outPath"
    } finally {
      if ($labelFont) { $labelFont.Dispose() }
      if ($graphics) { $graphics.Dispose() }
      if ($sheet) { $sheet.Dispose() }
    }
  } finally {
    foreach ($item in $loaded) {
      $item.Image.Dispose()
    }
  }
}

$backgroundBrush.Dispose()
$cellBrush.Dispose()
$labelBrush.Dispose()
$mutedBrush.Dispose()
$fontFamily.Dispose()
