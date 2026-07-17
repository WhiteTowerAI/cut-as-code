---
name: video-add-captions
description: >
  Add preset-driven, word-timed captions to a finished video with optional
  Karaoke highlighting. Use when an agent must build readable caption cues,
  present the offline style gallery, generate and validate a transparent
  HyperFrames overlay, and composite it onto the source while copying the
  original audio stream.
---

# Video Add Captions

## Scope

Use this skill to:

- Add every-line captions to a video whose editorial edit is already complete.
- Convert word-level transcript timing into readable caption cues.
- Render captions from official presets, themes, and optional JSON overrides.
- Keep each word as an indivisible layout and Karaoke timing unit.
- Generate a transparent caption-only overlay at the source dimensions, frame rate, and duration.
- Composite the overlay onto the source video while copying the original audio stream.

Do not use this skill for:

- Rough cuts or editorial trimming.
- Removing silence or filler content.
- Choosing which content should remain in the video.
- Lower thirds, statistics cards, chapter cards, title cards, or other selective motion graphics.
- Reframing, color grading, or changing the source video's duration.

## Safe Edit Points

### Ordinary style feedback may change

- The selected `preset`, theme, and Karaoke option passed to the generator.
- A job-specific overrides JSON passed with `--overrides`.
- Preview candidates used for human review.
- Caption text only when correcting a clear speech-recognition error. Keep cue `text`, `lines`, and `words[].word` synchronized and preserve timing unless the timing itself is demonstrably wrong.

### Ordinary style feedback must not change

- `scripts/generate_caption_project.mjs`
- `scripts/caption_style_config.mjs`
- Style resolver behavior.
- `scripts/composite_caption_overlay.ps1`
- Caption grouping, cue timing, or word timing merely to make a style fit.

### Style-system development may change

- `scripts/caption-styles.json`
- Theme definitions.
- Official preset defaults.
- The maintained gallery candidate list and formal preview assets when the task explicitly requests style-system work.

### Rendering-defect work may change

- Generated caption DOM structure.
- Caption CSS layout and wrapping behavior.
- Karaoke timing implementation.
- Overlay generation or compositing behavior when a reproducible rendering defect requires it.

Do not edit generator code as a response to ordinary feedback such as "bigger", "lower", "less transparent", or "use blue". Express those requests through preset selection, themes, Karaoke, or overrides.

## Inputs

Required inputs:

- A finished source video.
- A working output directory that does not overwrite the source.
- An interaction state created by `scripts/caption_interaction.mjs`.
- The user's exact gallery combination ID, or the exact response `跳过` to choose `clean`.
- The user's exact response `确认渲染` after reviewing source-backed preview evidence.

Optional inputs:

- `backgroundTheme`, `strokeTheme`, or `highlightTheme`.
- Karaoke as `auto`, `true`, or `false`.
- A JSON overrides file.
- Existing caption text corrections approved by the user.

When caption cues need to be built from word timing, `scripts/build_captions.py` consumes this structure:

```json
{
  "segments": [
    {
      "words": [
        { "word": "This", "start": 0.5, "end": 0.82 },
        { "word": "works", "start": 0.82, "end": 1.2 }
      ]
    }
  ]
}
```

## Caption Data

Build caption cues with this skill's own grouping script:

```powershell
# Run from the repository root.
$RepoRoot = (Resolve-Path ".").Path
$SkillRoot = Join-Path $RepoRoot "skills\video-add-captions"
$JobRoot = Join-Path $RepoRoot "work\video-add-captions"
$Transcript = Join-Path $JobRoot "transcript.json"
$CaptionsJson = Join-Path $JobRoot "captions.json"
$CaptionsSrt = Join-Path $JobRoot "captions.srt"

New-Item -ItemType Directory -Path $JobRoot -Force | Out-Null

py -3 "$SkillRoot\scripts\build_captions.py" `
  $Transcript `
  $CaptionsJson `
  $CaptionsSrt `
  --max-chars 42 `
  --max-lines 2 `
  --max-dur 6 `
  --gap 0.6
```

The resulting `captions.json` is an array of cues:

```json
[
  {
    "index": 1,
    "start": 0.5,
    "end": 2.1,
    "text": "This is a caption",
    "lines": ["This is a caption"],
    "words": [
      { "word": "This", "start": 0.5, "end": 0.8 },
      { "word": "is", "start": 0.8, "end": 1.0 },
      { "word": "a", "start": 1.0, "end": 1.2 },
      { "word": "caption", "start": 1.2, "end": 2.1 }
    ]
  }
]
```

Caption data rules:

- `start` and `end` define cue visibility.
- `words[].start` and `words[].end` drive Karaoke highlighting.
- `text` must represent the complete ordered word sequence.
- `lines` must contain the same text in display-line form.
- Do not split an English word across lines.
- Do not change cue grouping or timing to solve a style preference.
- If correcting a clear recognition error, update `text`, `lines`, and the matching `words[].word` value together.

Read `reference/caption-rules.md` before changing grouping limits or correcting caption data.

## Source Metadata

`scripts/generate_caption_project.mjs` reads the source video with `ffprobe`. It uses:

- Video width and height.
- Frame rate from `r_frame_rate`.
- Total duration.

The generated project writes `project-meta.json` containing:

- Absolute source video and captions paths.
- Width, height, frame rate, and duration.
- Caption cue count.
- Selected preset, themes, Karaoke value, and render mode.
- The complete resolved style.

Inspect source metadata before project generation when diagnosing unusual media:

```powershell
$SourceVideo = Join-Path $JobRoot "source.mp4"

ffprobe -v error `
  -select_streams v:0 `
  -show_entries stream=width,height,r_frame_rate `
  -show_entries format=duration `
  -of json `
  $SourceVideo
```

Do not hard-code width, height, frame rate, or duration into a generated project. Regenerate the project from the actual source video.

## Official Presets

The only official presets are:

| Preset | Intended use |
| --- | --- |
| `clean` | Default clean white captions without a caption background. |
| `minimal` | Smaller, restrained captions. |
| `social-bold` | Large, high-impact social captions. |
| `pill` | Rounded capsule background captions. |
| `boxed` | Rounded rectangular background captions. |
| `stroked` | Background-free captions with a colored outline. |
| `shorts` | Vertical-video captions with Cal Sans, uppercase text, outline, and active-word color. |

These are combination IDs, not official presets:

- `pill-yellow` = `preset: pill` + `backgroundTheme: yellow`
- `boxed-green` = `preset: boxed` + `backgroundTheme: green`
- `stroked-blue` = `preset: stroked` + `strokeTheme: blue`
- `shorts-pink` = `preset: shorts` + `highlightTheme: pink`
- `shorts-purple` = `preset: shorts` + `highlightTheme: purple`
- `social-bold-karaoke` = `preset: social-bold` + `karaoke: true`

Never add a combination ID to the official preset list.

## Themes and Options

### Background themes

- `gray`
- `yellow`
- `blue`
- `pink`
- `green`

Use with `pill` or `boxed` through `--background-theme`.

### Stroke themes

- `black`
- `yellow`
- `blue`
- `pink`
- `green`

Use with `stroked` through `--stroke-theme`.

### Shorts themes

- `yellow`
- `green`
- `orange`
- `purple`
- `blue`
- `pink`

Use with `shorts` through `--highlight-theme`.

### Karaoke

- Karaoke is an option, not an official preset.
- It accepts `true`, `false`, or `auto`.
- `auto` follows the resolved style's `wordHighlight.enabled` value.
- `true` requests word-timed highlighting.
- `false` disables word-timed highlighting without creating another preset.

Style configuration is stored at:

`scripts/caption-styles.json`

Read `reference/caption-style-themes.md` for the configuration vocabulary and `reference/caption-feedback-mapping.md` for feedback-to-config guidance.

## Style Selection Workflow

Full rendering requires two recorded human decisions. These gates are mandatory, and `scripts/generate_caption_project.mjs` rejects attempts to bypass them.

### Gate 1: interview the user about style

1. Prepare the source video, caption cues, and source metadata.
2. Start the interaction state with `scripts/caption_interaction.mjs start`. By default this opens `assets/style-previews/index.html` in the Windows system browser with `Start-Process`; do not substitute a Codex in-app `file://` link for the external browser window.
3. Ask exactly this question, preserving the decision rules:

   > 字幕样式库已在系统浏览器中打开。
   > 请浏览全部 25 种样式，然后只回复一个组合 ID，例如 `pill-yellow`。
   > 如果不想选择样式，请明确回复：`跳过`。此时采用默认 `clean`。
   > 收到有效组合 ID 或明确的“跳过”之前，流程不会继续。

4. Stop and wait. Do not call the `select` command on the user's behalf.
5. Record the user's response verbatim with `caption_interaction.mjs select --response`.
6. A response is valid only when it is one exact gallery combination ID or exactly `跳过`/`skip`. Silence, "随便", inferred preference, or an Agent-selected value is invalid.
7. `跳过` records an explicit user decision and resolves to `clean`; it is not an automatic fallback.
8. Until Gate 1 is recorded, preview generation and full overlay generation must fail.

### Gate 2: interview the user about the real-video preview

1. Generate a source-backed preview project using the recorded selection.
2. Capture at least four representative preview images: early caption, middle caption, late caption, and no-caption. When Karaoke is enabled, also include a frame inside an active word.
3. Record the actual image paths with `caption_interaction.mjs preview-ready`.
4. Show the images to the user and ask exactly this question:

   > 请检查真实视频上的字幕预览。
   > 满意时请明确回复：`确认渲染`。
   > 不满意时请说明需要调整的字号、位置、颜色、背景、描边或 Karaoke。
   > 收到明确的“确认渲染”之前，不会生成完整字幕层和最终视频。

5. Stop and wait. Do not call the `confirm` command on the user's behalf.
6. If the user requests a change, record the response with `caption_interaction.mjs adjust`, apply the selection or overrides change, regenerate preview evidence, and return to Gate 2.
7. Only the exact response `确认渲染` creates final render approval.
8. Any changed source video, captions JSON, selection, overrides file, or preview cycle invalidates the previous approval.
9. Render the complete overlay and final video only while the interaction state is `render_approved`.

The absence of a reply is never approval. An Agent must not simulate either user response during a real skill invocation.

## Natural Language Mapping Examples

| User request | Selection or override |
| --- | --- |
| Clean white text, no background | `--preset clean` |
| More restrained and smaller | `--preset minimal` |
| Large social-media captions | `--preset social-bold` |
| Yellow pill | `--preset pill --background-theme yellow` |
| Blue boxed | `--preset boxed --background-theme blue` |
| Black stroked | `--preset stroked --stroke-theme black` |
| Green shorts | `--preset shorts --highlight-theme green` |
| Pink shorts | `--preset shorts --highlight-theme pink` |
| Purple shorts | `--preset shorts --highlight-theme purple` |
| Turn Karaoke on | `--karaoke true` |
| Turn Karaoke off | `--karaoke false` |
| Use the resolved default | `--karaoke auto` |
| Make the font larger | `{"font":{"sizeRatio":0.05}}` in the overrides JSON |
| Move bottom captions lower | Reduce `layout.paddingBottomRatio` in the overrides JSON |
| Make the background more transparent | Reduce `background.opacity` in the overrides JSON |

Example job-specific overrides file:

```json
{
  "font": {
    "sizeRatio": 0.05
  },
  "layout": {
    "paddingBottomRatio": 0.05
  },
  "background": {
    "opacity": 0.5
  }
}
```

Pass it with:

```powershell
--overrides "$JobRoot\caption-overrides.json"
```

If the user says only "I don't like it", offer a limited set of directions:

- Cleaner.
- More eye-catching.
- Bigger or smaller.
- Stronger or weaker background.
- Different color.
- Outline.
- Shorts treatment.
- Karaoke on or off.

Do not ask the user to edit generator code.

## Working Layout

Skill layout:

```text
video-add-captions/
├── SKILL.md
├── assets/
│   └── style-previews/
│       ├── index.html
│       ├── preview-manifest.json
│       ├── preview-*.png
│       └── props-*.json
├── public/
│   └── fonts/
│       └── CalSans-Regular.ttf
├── reference/
│   ├── caption-feedback-mapping.md
│   ├── caption-rules.md
│   └── caption-style-themes.md
└── scripts/
    ├── build_captions.py
    ├── caption-styles.json
    ├── caption_interaction.mjs
    ├── caption_interaction_state.mjs
    ├── caption_style_config.mjs
    ├── check_caption_style_config.mjs
    ├── composite_caption_overlay.ps1
    ├── generate_caption_project.mjs
    └── render_style_previews.ps1
```

Recommended job layout:

```text
current-job/
├── source.mp4
├── transcript.json
├── captions.json
├── captions.srt
├── caption-interaction.json
├── caption-overrides.json
├── preview-project/
│   ├── index.html
│   ├── project-meta.json
│   └── assets/
├── preview-snapshots/
├── overlay-project/
│   ├── index.html
│   ├── project-meta.json
│   └── assets/
├── caption-overlay-frames/
└── captioned.mp4
```

Keep generated projects, snapshots, logs, and test media outside `assets/style-previews`. That directory is reserved for maintained gallery assets.

## Preview Commands

Set job paths:

```powershell
# Run from the repository root.
$RepoRoot = (Resolve-Path ".").Path
$SkillRoot = Join-Path $RepoRoot "skills\video-add-captions"
$JobRoot = Join-Path $RepoRoot "work\video-add-captions"
$SourceVideo = Join-Path $JobRoot "source.mp4"
$CaptionsJson = Join-Path $JobRoot "captions.json"
$InteractionState = Join-Path $JobRoot "caption-interaction.json"
$PreviewProject = Join-Path $JobRoot "preview-project"
$PreviewSnapshots = Join-Path $JobRoot "preview-snapshots"
```

Start Gate 1 and open the offline gallery in the Windows system browser:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" start `
  --state $InteractionState `
  --source $SourceVideo `
  --captions $CaptionsJson
```

Print the command output as the user interview, then stop. After the user replies, record the response verbatim:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" select `
  --state $InteractionState `
  --response "pill-yellow"
```

Use `--response "跳过"` only when that was the user's explicit reply.

Run the style configuration guardrail:

```powershell
node "$SkillRoot\scripts\check_caption_style_config.mjs"
```

Generate a source-backed preview project after a style has been selected:

```powershell
node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo `
  --captions $CaptionsJson `
  --out $PreviewProject `
  --interaction-state $InteractionState `
  --mode preview
```

The generator reads the selected preset, theme, and Karaoke value from the interaction state. Passing conflicting selection flags fails. Add `--overrides` only for job-specific adjustments.

Check the generated project:

```powershell
npx.cmd hyperframes check $PreviewProject `
  --at 1.55 `
  --timeout 10000 `
  --no-contrast
```

Capture representative frames:

```powershell
npx.cmd hyperframes snapshot $PreviewProject `
  --at 0,1,4,7 `
  --no-end `
  --timeout 60000 `
  --describe false `
  --output $PreviewSnapshots
```

Choose timestamps that include an early cue, a middle cue, a late cue, an active Karaoke word when enabled, and a frame with no visible caption. Adjust the example timestamps to the actual source duration.

Record the exact preview evidence paths and enter Gate 2:

```powershell
$Evidence = @(
  "$PreviewSnapshots\frame-01-at-0s.png",
  "$PreviewSnapshots\frame-02-at-1s.png",
  "$PreviewSnapshots\frame-03-at-4s.png",
  "$PreviewSnapshots\frame-04-at-7s.png"
) -join ","

node "$SkillRoot\scripts\caption_interaction.mjs" preview-ready `
  --state $InteractionState `
  --project-meta "$PreviewProject\project-meta.json" `
  --evidence $Evidence
```

Print the command output as the second user interview, show the preview images, and stop. If the user requests changes:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" adjust `
  --state $InteractionState `
  --response "字幕再大一点"
```

After applying the change, regenerate and re-record preview evidence. If the user replies exactly `确认渲染`:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" confirm `
  --state $InteractionState `
  --response "确认渲染"
```

For explicit gallery-asset maintenance, provide deterministic landscape and vertical fixtures plus `preview-captions.json`, then run:

```powershell
$GalleryReview = Join-Path $JobRoot "style-preview-review"

powershell.exe -ExecutionPolicy Bypass `
  -File "$SkillRoot\scripts\render_style_previews.ps1" `
  -OutputDirectory "$SkillRoot\assets\style-previews" `
  -ReviewDirectory $GalleryReview `
  -LandscapeVideo "$GalleryReview\fixtures\preview-landscape.mp4" `
  -ShortsVideo "$GalleryReview\fixtures\preview-shorts.mp4" `
  -Force
```

Do not regenerate the full gallery for an ordinary one-video style choice.

## Render Commands

Generate a transparent overlay project with the confirmed selection:

```powershell
$OverlayProject = Join-Path $JobRoot "overlay-project"
$OverlayFrames = Join-Path $JobRoot "caption-overlay-frames"
$FinalVideo = Join-Path $JobRoot "captioned.mp4"

node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo `
  --captions $CaptionsJson `
  --out $OverlayProject `
  --interaction-state $InteractionState `
  --mode overlay
```

Run the project check before rendering:

```powershell
npx.cmd hyperframes check $OverlayProject `
  --at 1.55 `
  --timeout 10000 `
  --no-contrast
```

Render the caption-only RGBA PNG sequence. This preserves the exact browser-rendered font pixels and alpha values used by the approved preview:

```powershell
Push-Location $OverlayProject
try {
  npx.cmd hyperframes render `
    --format png-sequence `
    --output $OverlayFrames
}
finally {
  Pop-Location
}
```

Composite the overlay onto the source and copy the original audio:

```powershell
powershell.exe -ExecutionPolicy Bypass `
  -File "$SkillRoot\scripts\composite_caption_overlay.ps1" `
  -SourceVideo $SourceVideo `
  -OverlayVideo $OverlayFrames `
  -OutputVideo $FinalVideo
```

The compositing script refuses to overwrite either input, accepts the RGBA PNG frame directory, encodes lossless RGB H.264, and uses `-c:a copy` for source audio.

## Testing Guidance

Use this section during preview iteration to choose representative tests, diagnose failures, and decide whether another adjustment is needed. `Self Check` is the mandatory final completion gate after the selected style has been rendered.

Test the smallest representative project before the full render.

### Caption correctness

- Read `captions.srt` for obvious recognition and grouping errors.
- Confirm cue `text`, `lines`, and ordered `words` agree.
- Confirm every word has finite start and end times within its cue.
- Confirm caption cues stay within the source duration.

### Visual snapshots

- Inspect at least three visible-caption timestamps: early, middle, and late.
- Inspect one frame with no caption.
- When Karaoke is enabled, inspect at least one timestamp inside an active word, not at a cue boundary.
- Confirm English words wrap only between words.
- Confirm long words remain intact even if an extreme word must overflow.
- Confirm captions remain inside the safe area and are not cropped by the frame edge.
- Confirm the expected font loaded, especially Cal Sans for `shorts`.

### Overlay and final video

- Confirm the overlay dimensions, frame rate, and duration match the source metadata.
- Confirm the overlay background is transparent outside caption pixels.
- Confirm a no-caption frame does not introduce a visible wash, black fill, or lifted average brightness.
- Confirm the final video contains the original audio stream.
- Confirm the final video duration remains aligned with the source.
- Watch the beginning, a middle section, and the ending for sync and caption visibility.

## Self Check

Complete all checks before reporting success.

1. Run the style configuration check:

   ```powershell
   node "$SkillRoot\scripts\check_caption_style_config.mjs"
   ```

2. Inspect the interaction status and require `render_approved`:

   ```powershell
   node "$SkillRoot\scripts\caption_interaction.mjs" status --state $InteractionState
   ```

3. Run the generated project's HyperFrames check:

   ```powershell
   npx.cmd hyperframes check $OverlayProject --at 1.55 --timeout 10000 --no-contrast
   ```

4. View at least three representative caption timestamps and one no-caption timestamp.
5. Check that wrapping occurs between words and never inside a normal English word.
6. Check caption safe-area placement and frame-edge clipping.
7. Check Karaoke timing against `words[].start` and `words[].end` when enabled.
8. Check that the no-caption frame is visually empty in the overlay.
9. Inspect a representative overlay frame and require RGBA pixels:

   ```powershell
     ffprobe -v error `
       -show_entries stream=codec_name,pix_fmt,width,height `
       -of json `
       "$OverlayFrames\frame_000001.png"
   ```

10. Confirm source and final audio packet hashes match:

   ```powershell
   ffmpeg -v error -i $SourceVideo -map "0:a:0?" -c copy -f hash -hash sha256 -
   ffmpeg -v error -i $FinalVideo -map "0:a:0?" -c copy -f hash -hash sha256 -
   ```

11. Check that black levels or average brightness are not abnormally raised. Run path-taking filters from the report directory and use basename output files:

    ```powershell
    Push-Location $JobRoot
    try {
      ffmpeg -v error -i $SourceVideo `
        -vf "signalstats,metadata=print:file=source-signalstats.txt" `
        -an -f null NUL

      ffmpeg -v error -i $FinalVideo `
        -vf "signalstats,metadata=print:file=final-signalstats.txt" `
        -an -f null NUL
    }
    finally {
      Pop-Location
    }
    ```

    Compare `YAVG` values at no-caption timestamps and visually compare the matching source and final frames. Small encoding differences are acceptable; a systematic brightness lift or dark overlay is not.

12. Confirm the final output exists, is non-zero, is not either input path, and plays with synchronized source audio.
13. Report both recorded user responses, the selected preset, themes, Karaoke value, overrides path, preview evidence, overlay path, final video path, and every validation result.
