<h1 align="center">agent-cut</h1>

<p align="center">
  <strong>The open skill stack for agentic video editing.</strong>
</p>

**Agent-cut** turns video editing into an inspectable, code-driven workflow. The agent proposes and records editing decisions as readable files; you review the evidence, approve the work, and then render the final videos.

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

**Agent-cut** treats editing like software: the edit is not a timeline you scrub but readable JSON and Markdown a coding agent authors, reviews, and re-renders.

- **The edit is code.** Every cut, grade, caption, card, and short is inspectable, diffable JSON you can revise and render again — no scrubbing.
- **Visual, not just a CLI.** Decisions surface in browser review pages — template galleries for caption styles and card themes rendered on your own footage, selectable candidate and boundary reviews — so you see and pick, instead of reading raw output.
- **Safe by construction.** Revision and dependency checks refuse to render against stale decisions, and each delivery self-verifies against the source (duration, dimensions, frames).
- **Review before render.** Stills, contact sheets, boundary reels, and previews gate every step before one coordinated final render of the whole program.
- **Polished motion.** HyperFrames and code-based renderers create titles, lower thirds, statistics, captions, overlays, and motion graphics in the same workflow.
- **Free, local, composable.** Free and open source (MIT), runs entirely on your machine, and skills work alone or combined with no mandatory pipeline.

### How we compare

**vs. OpusClip.** OpusClip is a hosted AI clipper: you upload to their cloud and it returns short clips on a paid, credit-based plan. **Agent-cut** is free, open source, and fully local — nothing is uploaded, no credits — and its scope is a full pipeline (understand, rough cut, color grade, captions, content cards, shorts, comparison), not just long-to-short.

**vs. Premiere Pro and CapCut.** These are GUI editors you scrub, drag, and re-export by hand. In **agent-cut** the edit *is* the file — a validated timeline and per-operation plans an agent authors, checks against stale dependencies, and self-verifies against the source. Built to be driven by a coding agent, not clicked.

**vs. one-off agent scripts.** A capable model can already script a pipeline for one video — but it typically leaves you reading raw JSON and logs. **Agent-cut** is the reusable layer it operates instead: composable skills over a shared, validated protocol, one coordinated render, enforced self-verification, and browser review pages that visualize every decision — template galleries and selectable candidate reviews — so you see and approve, not just trust the output. The model brings reasoning; agent-cut brings structure and visibility that hold across projects.

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

## Project Layout

```text
my-video-project/
|-- START-HERE.md
|-- input/                        # original user-provided media
|   `-- original-video.mp4
|-- review/                       # summaries, stills, contact sheets, previews
|   |-- 00-video-understanding/
|   |-- 01-rough-cut/
|   |-- 02-color-grade/
|   |-- 03-content-cards/
|   |-- 04-edit-compare/
|   |-- 05-captions/
|   `-- 06-shorts/
|-- final/                        # main delivery and derivative shorts
|   |-- final-video.mp4
|   `-- shorts/
|       |-- short-001-horizontal.mp4
|       `-- short-001-vertical.mp4
`-- work/                         # intermediate files for the agents themselves
    |-- project.json
    |-- timeline.json
    |-- understand/
    |-- rough-cut/
    |-- color-grade/
    |-- content-cards/
    |-- edit-compare/
    |-- captions/
    |-- shorts/
    |-- render/
    `-- cache/                    # disposable, regenerable files
```

Durable editing decisions and approval records must never live only in `work/cache/`.

- **`work/project.json`** is the shared manifest: available sequences, active operations and dependencies, operation status, integer revision numbers, `based_on` revision checks, review outputs, render contributions, and the final render path and status. Revision checks prevent an operation from silently rendering against stale upstream decisions.
- **`work/timeline.json`** is the canonical source-to-program mapping. Time values are in seconds and ranges are half-open `[start_s, end_s)`. The V1 model stays small and inspectable — chronological clips from one source with linear positive speed, no OpenTimelineIO required.

## Roadmap

Planned work — these items are not yet available.

- [ ] Make skills easier to install and update.
- [ ] Improve UI & UX design.
- [ ] Continue expanding the collection of composable video-editing skills.

