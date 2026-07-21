<h1 align="center">agent-cut</h1>

<p align="center">
  <strong>The open skill stack for agentic video editing.</strong>
</p>

agent-cut turns video editing into an inspectable, code-driven workflow. The agent proposes and records editing decisions as readable files; you review the evidence, approve the work, and then render the final videos.

## Demos

### 2h video to shorts

The agent found self-contained moments in the long-form program, extracted them as horizontal shorts, reframed the approved picks for vertical delivery, then added captions and content cards.

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

**Original video:** [Jensen Huang: NVIDIA GTC Taipei 2026 Keynote](https://www.youtube.com/watch?v=wSp6AiNIrsY)

**Prompt:**
> For [video-path], use /video-understand, /video-to-shorts, /video-add-captions, /video-add-content-cards.

### Raw podcast edit

The agent studied the footage, cut a tighter edit, then added captions and content cards with graphic motion.

<p align="center">
  <a href="https://youtu.be/YVmCi59aBPY"><img src="https://img.youtube.com/vi/YVmCi59aBPY/maxresdefault.jpg" alt="Watch the complete agent-cut workflow" width="480"></a>
</p>

<p align="center"><em>Click to view on YouTube.</em></p>

**Original video:** [Elon Musk : How to Build the Future](https://www.youtube.com/watch?v=tnBQmEqBCY0&t=67s)

**Prompt:**
> For [video-path], use /video-understand, /video-rough-cut, /video-add-captions, and /video-add-content-cards.

### Color grading

The agent assessed the footage, generated named looks, then rendered a side-by-side comparison of the original and the selected grade on the same timeline.

<p align="center">
  <a href="https://youtu.be/dF2vhhrf5lI"><img src="https://img.youtube.com/vi/dF2vhhrf5lI/maxresdefault.jpg" alt="Watch the original vs. color-graded comparison" width="480"></a>
</p>

<p align="center"><em>Click to view on YouTube.</em></p>

**Original video:** [DJI MAVIC PRO 2 Ungraded Footage to practice grading](https://www.youtube.com/watch?v=BBJtM_s0HKE)

**Prompt:**
> For [video-path], use /video-color-grade, and /video-edit-compare.

## Why agent-cut?

Timeline editors such as Premiere Pro and CapCut are powerful but complex and time-consuming. agent-cut takes a different approach: it uses the coding ability of AI models so editing tasks can be handled by agents, much like software development. Instead of clicking through timelines, you let agents inspect media, write edit plans, generate review artifacts, run renders, and refine iteratively.

- **Agent-friendly editing.** Agents trim, retime, crop, color grade, caption, add graphics, extract shorts, and export through code instead of manual clicks — working from reusable tools for probing media, transcribing, analyzing speech, and finding key moments.
- **Readable decisions.** Cuts, grades, captions, cards, and shorts are inspectable JSON and Markdown that can be reviewed, diffed, revised, and rendered again.
- **Polished motion.** HyperFrames and code-based renderers create titles, lower thirds, statistics, captions, overlays, and motion graphics in the same workflow.
- **Review before delivery.** Agents generate stills, contact sheets, boundary reels, and short previews before committing to an expensive full render.
- **Composable.** Skills work independently or combined. There is no mandatory global pipeline.

## Skills

Each directory under `skills/` is a self-contained agent skill. Its `SKILL.md` is both the agent playbook and the specification for that skill. 

| Skill | Purpose |
|---|---|
| `video-understand` | Probe media, generate a word-level transcript, analyze speech, and build reusable evidence for downstream skills. |
| `video-rough-cut` | Create reviewed keep/drop decisions, generate the canonical timeline, render a compact first cut, and verify its boundaries. |
| `video-color-grade` | Assess footage, generate named looks, review the alternatives, record a selection, and bake or apply a portable LUT. |
| `video-add-captions` | Render preset-driven, word-timed captions with optional karaoke highlighting. |
| `video-add-content-cards` | Add selective transcript-timed titles, lower thirds, statistics, lists, quotes, chapter cards, and calls to action. |
| `video-to-shorts` | Find and extract approved horizontal shorts, then optionally create reviewed 9:16 vertical deliveries. |
| `video-edit-compare` | Compare the original source with the actual final delivery on the original source clock. |

## Quick Start

Install the skills into your agent:

```bash
npx skills add WhiteTowerAI/agent-cut
```

Then with a prompt, point your agent at a video and name the skills you want:

> For [video-path], use /video-understand, /video-rough-cut, /video-add-captions, and /video-add-content-cards.

## How it works

agent-cut separates the reusable base edit from the packaging applied to each delivery. Every operation is optional: a project can analyze and grade without a rough cut, caption without cards, produce only horizontal shorts, or add captions and cards to vertical shorts after reframing. Creating or revising shorts never forces the main delivery to re-render.

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

1. **Understand the source once.** `video-understand` builds reusable evidence — media metadata, a word-level transcript, objective speech analysis, and evidence-backed semantic understanding. Downstream skills consume the same evidence instead of re-interpreting the source.
2. **Create an optional base edit.** Apply a rough cut, color grade, both, or neither. `video-rough-cut` is used only when content needs to be removed, shortened, or retimed. The result is an approved base program.
3. **Package the main delivery.** The main video can optionally receive captions and then content cards, in that order.
4. **Create derivative shorts.** Shorts start from the approved base program, not from a version that already carries the main delivery's captions and cards — so each short uses caption placement, card timing, and layouts designed for the vertical frame. Order: select moments → extract horizontal → reframe vertical → captions → content cards → verify.
5. **Review before rendering.** Each operation produces focused artifacts (stills, contact sheets, candidate summaries, timeline maps, boundary reels, previews) for review before the next step.
6. **Render and verify.** Approved operations render in one coordinated pass, and results are checked against the plans. Success is never declared from JSON or logs alone — final videos must be visually or mechanically verified.

### One coordinated final render

Approved skills do not repeatedly export full-length videos. Each contributes only what it owns — `video-rough-cut` timing and speed, `video-color-grade` color instructions, `video-add-captions` the caption overlay, `video-add-content-cards` the graphics. agent-cut validates dependencies, combines the contributions into one render plan, and produces the main delivery in a single pass. Shorts remain separate derivative deliveries, prepared and verified independently.

## Project Model

agent-cut does not enforce one fixed global pipeline. Skills declare their dependencies and contributions, and projects use only the operations they need. Only directories for selected operations need to exist.

```text
my-video-project/
|-- START-HERE.md
|-- input/                     # original user-provided media
|   `-- original-video.mp4
|-- review/                    # summaries, stills, contact sheets, previews
|   |-- video-understanding/
|   |-- rough-cut/
|   |-- color-grade/
|   |-- captions/
|   |-- content-cards/
|   |-- shorts/
|   `-- edit-compare/
|-- final/                     # main delivery and derivative shorts
|   |-- final-video.mp4
|   `-- shorts/
|       |-- short-001-horizontal.mp4
|       `-- short-001-vertical.mp4
`-- work/                      # manifests, plans, outputs, evidence
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
    `-- cache/                 # disposable, regenerable files
```

Durable editing decisions and approval records must never live only in `work/cache/`.

- **`work/project.json`** is the shared manifest: available sequences, active operations and dependencies, operation status, integer revision numbers, `based_on` revision checks, review outputs, render contributions, and the final render path and status. Revision checks prevent an operation from silently rendering against stale upstream decisions.
- **`work/timeline.json`** is the canonical source-to-program mapping. Time values are in seconds and ranges are half-open `[start_s, end_s)`. The V1 model stays small and inspectable — chronological clips from one source with linear positive speed, no OpenTimelineIO required.

## How we compare

### vs. OpusClip

[OpusClip](https://www.opus.pro/) is a hosted AI clipping product focused on quickly turning long videos into social clips, with a limited free tier and paid credit-based plans. agent-cut prioritizes control, inspectability, composability, and repeatability instead:

- an open, code-driven skill stack rather than a hosted service;
- editing decisions stored as readable JSON and Markdown, with media and project files kept in your own environment;
- selected boundaries can be inspected and revised before rendering;
- scope covers understanding, rough cutting, color grading, captions, content cards, shorts, and final comparison — not only long-to-short conversion;
- workflows extend by changing or adding skills, not by waiting for a hosted service.

### vs. Premiere Pro and CapCut

Premiere Pro and CapCut are visual timeline editors built for direct human operation. They are powerful, but complex projects require repeated clicking, timeline navigation, parameter adjustment, and manual export management. agent-cut instead represents the edit as readable files and executable operations: agents inspect the media, humans or delegated agents make editorial decisions, scripts handle timing and rendering precision, and review artifacts make decisions visible before delivery. It does not try to reproduce every timeline-editor control — it makes repeatable workflows easier for coding agents to execute.

### vs. one-off coding-agent video workflows

A capable model can already write scripts and assemble custom video workflows for a single project — recent demonstrations like [Claude Fable 5](https://www.anthropic.com/claude/fable) show how much a coding agent can do. agent-cut is not a competing model; it is the reusable workflow layer a model operates. Instead of rebuilding a one-off pipeline per video, it supplies reusable skill contracts, shared project and timeline formats, readable editorial plans, explicit review checkpoints, reproducible render instructions, and verification requirements. The model supplies reasoning and execution; agent-cut supplies the video-editing structure.

## Roadmap

Planned work — these items are not yet available.

- [ ] Make skills easier to install and update.
- [ ] Improve UI & UX design.
- [ ] Continue expanding the collection of composable video-editing skills.

