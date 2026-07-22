<h1 align="center">cut-as-code</h1>

<p align="center">
  <strong>The open skill stack for agentic video editing.</strong>
</p>

**Cut-as-code** turns video editing into an inspectable, code-driven workflow you can drive with AI coding agents like Claude Code, Codex, and OpenClaw. The agent proposes and records editing decisions as readable files; you review them in browser pages and template galleries, approve the work, and then render the final videos — all free, open source (MIT), and with nothing uploaded to a cloud service.

- ✂️ **Cut** — reviewed keep/drop decisions and a compact first cut.
- 🎨 **Color grade** — candidate looks to review, then a baked LUT.
- 💬 **Captions** — word-timed, preset styles with optional karaoke.
- 🃏 **Graphic motion cards** — titles, lower thirds, stats, quotes, and calls to action.
- 📱 **To shorts** — extract moments and reframe them for 9:16 vertical.

## Demos

### 1. 2h video to shorts

> **Prompt:** For [video-path], use /video-understand, /video-to-shorts, /video-add-captions, and /video-add-content-cards.
>
> **Agent:** Proposes short-form candidates, and displays captions and content cards with graphic motion for your review, and delivers the final edit.

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

Original video: [Jensen Huang: NVIDIA GTC Taipei 2026 Keynote](https://www.youtube.com/watch?v=wSp6AiNIrsY)

### 2. Cut, caption & card an interview

> **Prompt:** For [video-path], use /video-understand, /video-cut, /video-add-captions, and /video-add-content-cards.
>
> **Agent:** Displays a few captions and content cards candidates for your review, then delivers the final edit.

<p align="center">
  <a href="https://youtu.be/YVmCi59aBPY"><img src="https://img.youtube.com/vi/YVmCi59aBPY/maxresdefault.jpg" alt="Watch the complete cut-as-code workflow" width="480"></a>
</p>

<p align="center">
  <a href="https://youtu.be/YVmCi59aBPY"><img src="https://img.shields.io/badge/Watch%20on-YouTube-FF0000?logo=youtube&logoColor=white" alt="Watch on YouTube"></a>
</p>

Original video: [Elon Musk : How to Build the Future](https://www.youtube.com/watch?v=tnBQmEqBCY0&t=67s)

### 3. Color grading

> **Prompt:** For [video-path], use /video-color-grade, and /video-edit-compare.
>
> **Agent:** Displays a few candidate grading options for your review, then do the final grading.

[![Watch the original vs. color-graded comparison](https://img.youtube.com/vi/dF2vhhrf5lI/maxresdefault.jpg)](https://youtu.be/dF2vhhrf5lI)

<p align="center">
  <a href="https://youtu.be/dF2vhhrf5lI"><img src="https://img.shields.io/badge/Watch%20on-YouTube-FF0000?logo=youtube&logoColor=white" alt="Watch on YouTube"></a>
</p>

Original video: [DJI MAVIC PRO 2 Ungraded Footage to practice grading](https://www.youtube.com/watch?v=BBJtM_s0HKE)


## Skills

Each directory under `skills/` is a self-contained agent skill. Its `SKILL.md` is both the agent playbook and the specification for that skill. 

| Skill | Purpose |
|---|---|
| `/video-understand` | Probe media, generate a word-level transcript, analyze speech, and build reusable evidence for downstream skills. |
| `/video-cut` | Create reviewed keep/drop decisions, generate the canonical timeline, render a compact first cut, and verify its boundaries. |
| `/video-color-grade` | Assess footage, generate named looks, review the alternatives, record a selection, and bake or apply a portable LUT. |
| `/video-add-captions` | Render preset-driven, word-timed captions with optional karaoke highlighting. |
| `/video-add-content-cards` | Add selective transcript-timed titles, lower thirds, statistics, lists, quotes, chapter cards, and calls to action. |
| `/video-to-shorts` | Find and extract approved horizontal shorts, then optionally create reviewed 9:16 vertical deliveries. |
| `/video-edit-compare` | Compare the original source with the actual final delivery on the original source clock. |

## Quick Start

Install the skills into your agent:

```bash
npx skills add WhiteTowerAI/cut-as-code
```

Then with a prompt, point your agent at a video and name the skills you want:

> For [video-path], use /video-understand, /video-cut, /video-add-captions, and /video-add-content-cards.

## Project Layout

```text
my-video-project/
|-- START-HERE.md
|-- input/                        # original user-provided media
|   `-- original-video.mp4
|-- review/                       # summaries, stills, contact sheets, previews
|   |-- 00-video-understanding/
|   |-- 01-cut/
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
    |-- cut/
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

