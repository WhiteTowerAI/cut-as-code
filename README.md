<h1 align="center">agent-cut</h1>

<p align="center">
  <strong>The open skill stack for agentic video editing.</strong>
</p>

## See it in action

```text
You: Understand this footage, propose the edits, and show me something
     I can review before rendering the final videos.

Agent:
     ✓ Probed the source media
     ✓ Generated a word-level transcript
     ✓ Wrote readable editing decisions
     ✓ Created stills, contact sheets, and short previews
     ✓ Rendered the approved main delivery
     ✓ Selected and extracted short-form moments
     ✓ Reframed the approved shorts for vertical delivery
     ✓ Added captions and content cards to the vertical shorts
     ✓ Verified the final outputs
```

agent-cut turns video editing into an inspectable, code-driven workflow.

The agent proposes and records editing decisions. You review the evidence, approve the work, and then render the final videos.

### Complete long-form workflow

A complete agent-driven editing workflow using an approximately two-hour horizontal video.

**Source footage:** [Watch the original video on YouTube](https://www.youtube.com/watch?v=tnBQmEqBCY0&t=67s)

[![Watch the complete agent-cut workflow](https://img.youtube.com/vi/YVmCi59aBPY/maxresdefault.jpg)](https://youtu.be/YVmCi59aBPY)

The final cut was created with `//video-rough-cut`, `//video-add-captions`, and `//video-add-content-cards`.

### Long-form video to vertical shorts

agent-cut first finds and extracts self-contained short-form moments from the long-form program.

The approved horizontal shorts are then reframed for vertical delivery. Captions and content cards are added only after the vertical versions have been created.

**Source footage:** [Watch the original video on YouTube](https://www.youtube.com/watch?v=wSp6AiNIrsY)

<table>
  <tr>
    <th align="center">Short 01</th>
    <th align="center">Short 02</th>
    <th align="center">Short 03</th>
    <th align="center">Short 04</th>
  </tr>
  <tr>
    <td align="center">
      <video src="https://github.com/user-attachments/assets/828c1800-3914-4077-bc1e-4db4d175311d" width="240" controls muted playsinline></video>
      <br>
      <code>short-01.mp4</code>
    </td>
    <td align="center">
      <video src="https://github.com/user-attachments/assets/9c71db5e-320d-40ca-843b-1656b0f388be" width="240" controls muted playsinline></video>
      <br>
      <code>short-02.mp4</code>
    </td>
    <td align="center">
      <video src="https://github.com/user-attachments/assets/6f3c82a7-f01c-4b94-b059-033b3116165b" width="240" controls muted playsinline></video>
      <br>
      <code>short-03.mp4</code>
    </td>
    <td align="center">
      <video src="https://github.com/user-attachments/assets/6f6a1a16-8b2a-4b46-8081-a77e21a9d986" width="240" controls muted playsinline></video>
      <br>
      <code>short-04.mp4</code>
    </td>
  </tr>
</table>

Each short follows the same reviewable workflow:

```text
approved base program
        |
        v
select short-form moment
        |
        v
extract horizontal short
        |
        v
reframe for vertical delivery
        |
        v
add captions
        |
        v
add content cards
        |
        v
verify final vertical short
```

### Original vs. color graded

This side-by-side demo shows the original footage and the selected color grade on the same timeline.

**Source footage:** [Watch the original video on YouTube](https://www.youtube.com/watch?v=BBJtM_s0HKE)

[![Watch the original vs. color-graded comparison](https://img.youtube.com/vi/dF2vhhrf5lI/maxresdefault.jpg)](https://youtu.be/dF2vhhrf5lI)

The comparison contains two synchronized 16:9 views: the original footage on one side and the graded result on the other.

## Why agent-cut?

agent-cut aims to make video editing as simple as possible.

Timeline editors such as Premiere Pro and CapCut are powerful, but they can also be complex and time-consuming. agent-cut takes a different approach: it uses the coding ability of AI models so that editing tasks can be handled by agents, much like software development.

Instead of clicking through complex timelines, humans can let agents inspect and search media, write edit plans, generate review artifacts, run renders, and refine the result iteratively.

- **Make video editing agent-friendly.** Agents can trim, retime, crop, color grade, caption, add graphics, extract shorts, and export videos through code instead of manual timeline clicks.

- **Let agents understand raw media.** agent-cut provides reusable tools for probing media, generating word-level transcripts, analyzing speech, finding key moments, and identifying material that may need to be removed.

- **Keep editing decisions readable.** Cuts, grades, captions, cards, and shorts are represented by inspectable JSON and Markdown artifacts that can be reviewed, diffed, revised, and rendered again.

- **Bring polished motion into the workflow.** HyperFrames and code-based renderers let agents create titles, lower thirds, statistics, captions, overlays, and motion graphics within the same workflow.

- **Review before delivery.** Agents generate stills, contact sheets, boundary reels, and short previews before committing to an expensive full render.

- **Keep the workflow composable.** Skills can be used independently or combined according to the needs of each project. There is no mandatory global pipeline.

## Quick Start

### 1. Clone agent-cut

```powershell
git clone https://github.com/WhiteTowerAI/agent-cut.git
Set-Location agent-cut

$Repo = (Get-Location).Path
```

### 2. Check the shared dependencies

```powershell
ffmpeg -version
ffprobe -version
python -c "import faster_whisper"
```

Individual skills may require additional dependencies. Read the skill's `SKILL.md` before running its scripts.

### 3. Initialize a video project

```powershell
$Source = "C:\path\to\source-video.mp4"
$Project = Join-Path $Repo "my-video-project"

python "$Repo\skills\video-understand\scripts\init_project.py" `
  $Source `
  $Project

Set-Location $Project
```

This creates the human-facing `input/`, `review/`, and `final/` directories, together with the machine-facing project manifest, timeline, evidence, and cache files under `work/`.

### 4. Build the shared evidence layer

```powershell
ffmpeg -y `
  -i input/original-video.mp4 `
  -ac 1 `
  -ar 16000 `
  work/cache/audio16k.wav

python "$Repo\skills\video-understand\scripts\transcribe.py" `
  work/cache/audio16k.wav `
  work/understand/transcript `
  medium `
  --lang auto `
  --cache-dir work/cache/faster-whisper

python "$Repo\skills\video-understand\scripts\analyze.py" `
  work/understand/transcript.json `
  work/understand/analysis.json
```

### 5. Tell your agent what you want

For a rough cut:

```text
Read skills/video-rough-cut/SKILL.md and use it to turn this project
into a tighter first cut.

Show me the summary, timeline map, and boundary review before rendering
the final delivery.
```

For captions and content cards:

```text
Add captions to the approved program first.

After the captions are approved, add selective content cards without
changing the underlying timeline.
```

For shorts:

```text
Read skills/video-to-shorts/SKILL.md and propose five short-form clips
from the approved base program.

Show me the candidate review artifacts before extraction.

After I approve the horizontal shorts, create vertical versions. Add
captions first and content cards afterward.
```

### 6. Compile and render approved operations

After the selected main-sequence operations are approved and their revision checks pass:

```powershell
python "$Repo\skills\video-understand\scripts\build_render_plan.py" .

python "$Repo\skills\video-understand\scripts\render_project.py" `
  work/render/render-plan.json
```

To compare the actual final pixels against the original source:

```powershell
python "$Repo\skills\video-edit-compare\scripts\make_compare.py" `
  work/timeline.json `
  input/original-video.mp4 `
  final/final-video.mp4 `
  review/edit-compare/original-vs-final-source-time.mp4
```

## Skills

Each directory under `skills/` is a self-contained agent skill.

Its `SKILL.md` is both the agent playbook and the specification for that skill.

| Skill | Purpose |
|---|---|
| `video-understand` | Probe media, generate a word-level transcript, analyze speech, and build reusable evidence for downstream editing skills. |
| `video-rough-cut` | Create reviewed keep/drop decisions, generate the canonical timeline, render a compact first cut, and verify its boundaries. |
| `video-color-grade` | Assess footage, generate named looks, review the alternatives, record a selection, and bake or apply a portable LUT. |
| `video-add-captions` | Render preset-driven, word-timed captions with optional karaoke highlighting. |
| `video-add-content-cards` | Add selective transcript-timed titles, lower thirds, statistics, lists, quotes, chapter cards, and calls to action. |
| `video-to-shorts` | Find and extract approved horizontal shorts, then optionally create reviewed 9:16 vertical deliveries. |
| `video-edit-compare` | Compare the original source with the actual final delivery on the original source clock. |

Skills are optional and composable.

A project can:

- analyze a video without editing it;
- add captions without creating a rough cut;
- color grade a full-length video;
- combine a rough cut, grade, captions, and content cards;
- create horizontal shorts without producing vertical versions;
- create vertical shorts and package them with their own captions and content cards;
- compare the original source against the actual final delivery.

## How it works

agent-cut separates the reusable base edit from the final packaging applied to each delivery.

```text
input/original-video.mp4
          |
          v
   video-understand
   probe + transcript
   objective analysis
          |
          v
   rough cut (optional)
          |
          v
   color grade (optional)
          |
          v
   approved base program
          |
          +--------------------------------+
          |                                |
          v                                v
   main delivery path              shorts delivery path
          |                                |
          v                                v
   captions (optional)               to shorts
          |                                |
          v                                v
   content cards (optional)          horizontal shorts
          |                                |
          v                                v
   final main video                  vertical reframe
                                           |
                                           v
                                     captions (optional)
                                           |
                                           v
                                  content cards (optional)
                                           |
                                           v
                                   final vertical shorts
```

Every operation is optional.

For example:

- a project can analyze and color grade a video without creating a rough cut;
- a project can add captions without adding content cards;
- a project can produce only horizontal shorts;
- a project can turn approved horizontal shorts into vertical videos;
- vertical shorts can receive their own captions and content cards after reframing;
- creating or revising shorts does not need to change the final main delivery.

### 1. Understand the source once

`video-understand` creates reusable evidence for the project:

- media metadata;
- a word-level transcript;
- objective speech analysis;
- evidence-backed semantic understanding.

Downstream skills consume the same evidence instead of independently interpreting the source every time.

### 2. Create an optional base edit

The project may apply a rough cut, color grade, both, or neither.

`video-rough-cut` is used only when the source needs content removed, shortened, or retimed. It is not a mandatory step for every long-form video.

The result is an approved base program that can be used by the main delivery and derivative workflows.

### 3. Package the main delivery

The main video can optionally receive:

1. captions;
2. content cards.

When both are used, captions are prepared first and content cards are added afterward.

### 4. Create derivative shorts

The shorts workflow starts from the approved base program rather than from a version that already contains the main delivery's captions and content cards.

The order is:

```text
select moments
→ extract horizontal shorts
→ create vertical versions
→ add captions
→ add content cards
→ verify final shorts
```

This allows each short to use caption placement, card timing, and graphic layouts designed specifically for the vertical frame.

### 5. Review before rendering

Each operation produces focused review artifacts before the final delivery:

- still images;
- contact sheets;
- candidate summaries;
- timeline maps;
- boundary reels;
- short preview videos.

The user or an explicitly delegated agent reviews these artifacts before approving the next step.

### 6. Render and verify

Approved operations are rendered, and the resulting media is checked against the plans and review evidence.

The workflow does not declare success based only on generated JSON or logs. Final videos must also be visually or mechanically verified.

## Project Model

agent-cut does not enforce one fixed global editing pipeline.

Skills declare their dependencies and contributions, and projects use only the operations they need.

```text
my-video-project/
|-- START-HERE.md
|-- input/
|   `-- original-video.mp4
|-- review/
|   |-- video-understanding/
|   |-- rough-cut/
|   |-- color-grade/
|   |-- captions/
|   |-- content-cards/
|   |-- shorts/
|   `-- edit-compare/
|-- final/
|   |-- final-video.mp4
|   `-- shorts/
|       |-- short-001-horizontal.mp4
|       `-- short-001-vertical.mp4
`-- work/
    |-- project.json
    |-- timeline.json
    |-- understand/
    |-- rough-cut/
    |-- color-grade/
    |-- captions/
    |-- content-cards/
    |-- shorts/
    |-- edit-compare/
    |-- render/
    `-- cache/
```

Only directories for selected operations need to exist.

Durable decisions and review records remain outside `work/cache/`.

### Shared manifest

`work/project.json` is the shared project manifest.

It records:

- available sequences;
- active operations and dependencies;
- operation status;
- integer revision numbers;
- `based_on` revision checks;
- review outputs;
- render contributions;
- the final render path and status.

Revision checks prevent an operation from silently rendering against stale upstream decisions.

### Canonical timeline

`work/timeline.json` is the canonical source-to-program mapping.

Time values use seconds, and ranges are half-open:

```text
[start_s, end_s)
```

The V1 timeline model intentionally stays small and inspectable. It supports chronological clips from one source with linear positive speed.

It does not require OpenTimelineIO.

### Human-facing and machine-facing files

- `input/` contains the original user-provided media.
- `review/` contains summaries, stills, contact sheets, and previews.
- `final/` contains the main delivery and derivative shorts.
- `work/` contains manifests, plans, operation outputs, and machine-facing evidence.
- `work/cache/` contains disposable files that can be regenerated.
- Durable editing decisions and approval records must not live only in the cache.

### Main delivery and derivatives

The main sequence produces:

```text
final/final-video.mp4
```

Shorts are separate derivative deliveries:

```text
final/shorts/
```

Creating, reframing, captioning, or packaging a short does not need to change or re-render the main delivery.

## One coordinated final render

Approved skills do not repeatedly export separate full-length videos.

Instead, each skill contributes only the instructions or assets it owns:

- `video-rough-cut` contributes timing and speed decisions;
- `video-color-grade` contributes color-processing instructions;
- `video-add-captions` contributes the caption overlay;
- `video-add-content-cards` contributes titles, lower thirds, statistics, and other graphics.

agent-cut validates their dependencies, combines the approved contributions into one render plan, and produces the main delivery in one coordinated render.

This avoids repeatedly re-encoding the complete video after every editing operation.

Shorts remain separate derivative deliveries. Their extraction, vertical framing, captions, and content cards are prepared and verified independently from the main delivery.

## How we compare

### vs. OpusClip

[OpusClip](https://www.opus.pro/) is a hosted AI clipping product focused on quickly turning long videos into social-media clips.

It provides a limited free tier, while higher processing capacity and commercial workflows use paid credit-based plans.

agent-cut takes a different approach:

- it is an open, code-driven skill stack rather than a hosted clipping service;
- editing decisions are stored as readable JSON and Markdown artifacts;
- source media and project files can remain in the user's own environment;
- users can inspect and revise selected boundaries before rendering;
- its scope includes understanding, rough cutting, color grading, captions, content cards, shorts, and final comparison—not only long-video-to-short-video conversion;
- workflows can be extended by changing or adding skills instead of waiting for a hosted service to expose a new option.

OpusClip prioritizes speed and convenience.

agent-cut prioritizes control, inspectability, composability, and repeatability.

### vs. Premiere Pro and CapCut

Premiere Pro and CapCut are visual timeline editors designed primarily for direct human operation.

They provide powerful interfaces, but complex projects often require repeated clicking, timeline navigation, parameter adjustment, and manual export management.

agent-cut represents the edit as readable files and executable operations:

- agents inspect the media;
- humans or delegated agents make editorial decisions;
- scripts perform timing and rendering precision;
- review artifacts make decisions visible before delivery;
- the project can be revised and rendered again from the same recorded plans.

agent-cut is not trying to reproduce every timeline-editor control.

It is designed to make repeatable video-editing workflows easier for coding agents to understand and execute.

### vs. one-off coding-agent video workflows

General-purpose AI models can already write scripts, assemble tools, and create custom video workflows for a specific project.

Recent model demonstrations, including [Claude Fable 5](https://www.anthropic.com/claude/fable), show how capable a coding agent can be when it is allowed to inspect assets, generate code, and run media tools.

agent-cut is not a competing AI model.

It is the reusable workflow layer that an AI model or coding agent can operate.

Instead of rebuilding a new one-off pipeline for every video, agent-cut provides:

- reusable skill contracts;
- shared project and timeline formats;
- readable editorial plans;
- explicit review checkpoints;
- reproducible render instructions;
- verification requirements;
- composable operations that can be reused across projects.

A capable model supplies reasoning and execution.

agent-cut supplies the video-editing structure.

## Roadmap

The roadmap describes planned work. Items in this section should not be interpreted as features that are already available.

- [ ] Publish the complete long-form workflow demo on YouTube.
- [ ] Publish the four vertical-short demos.
- [ ] Publish the original-versus-color-graded comparison.
- [ ] Make the full shorts workflow—from horizontal extraction through vertical captions and content cards—a first-class project operation.
- [ ] Make skills easier to install and update.
- [ ] Add more reproducible example projects and review artifacts.
- [ ] Continue expanding the collection of composable video-editing skills.
