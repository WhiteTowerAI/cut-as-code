<h1 align="center">Open-Recut</h1>

<p align="center"><strong>The open skill stack for agentic video editing.</strong></p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Codex-supported-10A37F" alt="Codex supported">
  <img src="https://img.shields.io/badge/Claude%20Code-supported-D97757" alt="Claude Code supported">
</p>

Open-Recut is a collection of self-contained agent skills, not a timeline-editor application. Agents inspect media, write readable JSON edit decisions, generate review artifacts, and render with ffmpeg or HyperFrames.

## Project Model

Editing skills are optional and composable. A project can add content cards directly, or run rough cut, color grade, and cards in sequence. There is no fixed global pipeline.

```text
source -> video-understand -> optional edit operations -> final render -> compare
                              rough cut / grade / cards
```

`work/project.json` records active operations, dependencies, integer `revision` values, and `based_on` checks. `work/timeline.json` is a small custom source-to-program mapping; OpenTimelineIO is not required. Approved render contributions are compiled once so the final video is encoded in one delivery pass.

```text
my-video-project/
|-- START-HERE.md
|-- input/original-video.mp4
|-- review/                         # summaries, stills, and short previews
|-- final/final-video.mp4
`-- work/                           # machine-facing JSON and disposable cache
    |-- project.json
    |-- timeline.json
    |-- understand/
    |-- rough-cut/
    |-- color-grade/
    |-- content-cards/
    |-- edit-compare/
    |-- render/
    `-- cache/
```

Only directories for selected operations need to exist. Durable decisions stay outside `work/cache/`.

## Skills

| Skill | Purpose |
|---|---|
| `video-understand` | Probe, transcribe, analyze, and author evidence-backed semantic understanding. |
| `video-rough-cut` | Make hand-reviewed keep/drop decisions, generate the canonical timeline, and verify a compact cut. |
| `video-color-grade` | Assess footage, present named looks, record the human selection, and bake/apply a LUT. |
| `video-add-content-cards` | Map semantic moments to HyperFrames cards and render a transparent graphics overlay. |
| `video-edit-compare` | Compare original and actual final pixels on the original source clock. |
| `video-add-captions` | Render styled every-line captions with optional karaoke timing. |
| `video-to-shorts` | Find, review, and render short vertical clips from long-form video. |

Read a skill's `SKILL.md` before running its scripts. Editorial choices remain human-reviewed; scripts handle timestamp precision, compositing, and checks.

## Quick Start

Check the shared dependencies:

```powershell
ffmpeg -version
ffprobe -version
python -c "import faster_whisper"
```

Initialize the understandable user/machine directory layout, then run the shared evidence layer:

```powershell
python skills/video-understand/scripts/init_project.py path/to/source.mp4 my-video-project
Set-Location my-video-project
ffmpeg -y -i input/original-video.mp4 -ac 1 -ar 16000 work/cache/audio16k.wav
python skills/video-understand/scripts/transcribe.py work/cache/audio16k.wav work/understand/transcript
python skills/video-understand/scripts/analyze.py work/understand/transcript.json work/understand/analysis.json
```

After selected operations are approved and revision checks pass:

```powershell
python skills/video-understand/scripts/build_render_plan.py .
python skills/video-understand/scripts/render_project.py work/render/render-plan.json
python skills/video-edit-compare/scripts/make_compare.py work/timeline.json input/original-video.mp4 final/final-video.mp4 review/04-edit-compare/original-vs-final-source-time.mp4
```

Each skill still supports focused review artifacts and compatibility adapters where documented. Do not use a full delivery render as the default preview.
