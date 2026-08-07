---
name: cut-as-code
description: >
  Use when any cut-as-code request involves understanding, cutting, color grading,
  adding B-roll, graphic motion, content cards, captions, creating shorts,
  comparing, rendering, or resuming a Project Protocol V1 video project.
---

# Cut as Code Entry Point

Use this as the mandatory entry point for cut-as-code video work. Own routing and
project-state recovery only. The selected leaf skill owns editorial decisions,
review gates, scripts, rendering details, and self-checks.

## 1. Start From Project State

Apply the first matching row. Do not evaluate lower rows.

| State | Action |
|---|---|
| The user names a specific operation on an existing project | Inspect only the state needed for that operation, then load its owning skill. Skip general intake. |
| An explicit project root contains `work/project.json` | Read `work/project.json`, `work/timeline.json`, and only the selected operation's plan/evidence. Resume from recorded state. If the owner is not unique, ask one routing-only question. |
| The user supplies a source file or URL, no project, and a clear deliverable | Load `/video-understand` to initialize the project and shared evidence, then continue to the requested operation. |
| No project/source or no intended deliverable is identifiable | Ask one concise question requesting the missing project/source and desired result. Do not start a skill yet. |

The project root must be explicit; never treat the repository root as a video
project. Treat `work/project.json` as the only shared manifest. Determine progress
from operation `status`, `revision`, `based_on`, `check`, and render state, not from
directory presence. Do not re-run verified work. If a dependency is missing or
stale, complete that dependency first and then resume the requested operation.

Routing is read-only. Never repair, reset, approve, remove, or activate an operation
while deciding where to send the task.

## 2. Route by Deliverable

Match the requested output, not a keyword mentioned in passing.

| Requested result | Owning skill or workflow |
|---|---|
| Probe, transcript, objective analysis, semantic understanding, or new project initialization | `/video-understand` |
| Tighten, shorten, remove weak sections, or create a first/rough cut | `/video-cut` after `/video-understand` |
| Correct color, create/select a look, or deliver/apply a LUT | `/video-color-grade`; use its standalone path only when the user explicitly wants no Project Protocol delivery |
| Add transcript-timed visual cutaways | `/video-add-b-roll` after `/video-understand` |
| Add sourced motion graphics or animated semantic overlays | `/video-add-graphic-motion` after `/video-understand` |
| Add titles, lower-thirds, statistics, quotes, chapters, or calls to action | `/video-add-content-cards` after `/video-understand` |
| Add subtitles, captions, or karaoke captions | `/video-add-captions` after `/video-understand` |
| Compare the original with actual final pixels in source time | `/video-edit-compare` after the verified main delivery exists |
| Select, review, and plan short-form ranges | `/video-to-shorts` after `/video-understand`; do this before requested content cards and captions |
| Finalize and extract approved horizontal or vertical short-form derivatives | Resume `/video-to-shorts` after the verified main delivery exists |
| Compile or render an existing Project Protocol delivery | Use `build_render_plan.py` and `render_project.py` from `/video-understand` after every selected active operation passes its own gate |

A generic request such as "edit this video" does not uniquely select `/video-cut`.
Ask one routing question unless the desired output is clear from existing project
state or the surrounding request.

## 3. Orchestrate Multi-Operation Requests

Freeze only the operations the user requested; never turn the route table into a
default package. Run the shared understanding prerequisite once. Execute selected
main-sequence operations in canonical order:

```text
cut -> color-grade -> b-roll -> captions -> content-cards -> graphic-motion
```

For a request that includes Shorts, content cards, or captions, use this staged flow:

```text
/video-understand
-> /video-to-shorts plan and candidate review only
-> /video-add-captions
-> /video-add-content-cards
-> /video-add-graphic-motion
-> compile and render the shared main delivery once
-> /video-to-shorts finalize and extract approved derivatives
```

Complete any requested timeline-changing operation, such as `/video-cut`, before
Shorts planning; a changed `work/timeline.json` invalidates candidate approval.
Shorts planning writes shared plan/review state and must not create `final.mp4` or
anything under `final/shorts/`. Captions, content cards, and graphic motion then add
their own shared plans and overlay contributions in that relative order. The same
order applies when only any pair is selected: captions first, content cards second,
graphic motion last. Re-read `work/project.json` before each handoff. Do not
run leaf skills concurrently when they can write `work/project.json`,
`work/timeline.json`, an operation plan, or shared render artifacts. Build and render
the main delivery once, after all selected active operations validate. Run
`/video-edit-compare` and only the finalization/extraction phase of
`/video-to-shorts` against that verified delivery; shorts remain outside
`sequences.main.operations`.

For `/video-add-content-cards` and `/video-add-graphic-motion`, reserve the visible face
and head silhouette of every primary or foreground person, speaker, presenter, interviewee,
or semantically important person for the complete cue. Incidental background-only people
who are not a narrative or visual focus are exempt; protect uncertain cases. If an overlay
touches a protected face or head, reposition it first, then scale or redesign it; skip the
cue when no compliant placement exists.

An all-skipped or zero-cue result is valid when the owning skill permits it. Do not
invent filler work to keep an operation active.

## 4. Hand Off, Then Leave

Read the selected skill's complete `SKILL.md` and every required sub-skill before
acting. For one operation, hand off once and leave this entry point. For a requested
multi-operation run, enter one owner at a time; after its self-check, recover project
state and continue to the next frozen operation without reopening intake.

Do not ask the user to approve a route that is already unambiguous. User interaction
belongs only to missing inputs, genuine routing ambiguity, credentials, or the
editorial/review decisions required by the owning skill. Never substitute an Agent
decision for a required human decision unless the user explicitly delegates it.

## Example

For "continue this understood and cut project by adding captions," read the current
project and timeline revisions, then enter `/video-add-captions`. Do not re-transcribe,
re-cut, or ask whether captions are the intended route. An unrelated pending operation
does not change the route, though an active unverified operation may block the final
shared render and must be reported by the compiler.

## Failure Rules

- Invalid project state: report the exact validation problem; never reinitialize over it.
- Missing leaf skill or prerequisite: stop and name it; do not reconstruct it from memory.
- Missing source/project path: ask for it in the single routing question.
- Conflicting requested outputs: ask which deliverable owns the current run.
- Existing user changes or artifacts: preserve them and work with the recorded state.
