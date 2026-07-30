# Porting Guide

Preserve DOM/SVG structure, shader math, visual hierarchy, easing, and choreography. Allowed
changes are content binding, timeline sizing/placement, transparency, local assets,
deterministic timing, recorded random seeds, selector namespacing, and uniform retiming.
Record them in `adaptation.patch` and `change_categories`.

The selected source owns the runtime. Record it as `source.runtime`; `port.motion_model` must
match its HyperFrames adapter (`canvas`, `webgl`, `lottie`, and `typegpu` use `hf-seek`). Do not translate Anime.js to WAAPI/GSAP/CSS or otherwise replace the source runtime. If
the original runtime cannot become deterministic without losing signature structure or
choreography, reject that candidate and search again.

| Source behavior | Native HyperFrames mapping |
| --- | --- |
| Finite CSS animation | Finite CSS adapter animation with explicit fill state; add `data-no-timeline` to a CSS-only root |
| WAAPI | Set `currentTime` through the WAAPI adapter |
| Anime.js | Disable autoplay, register once, seek milliseconds |
| GSAP | Register one paused timeline under the exact composition ID |
| hover/focus/press | Finite rest, activate, hold, release arc |
| scroll | Map normalized cue time from 0 to 1 |
| drag/pointer | Author a deterministic time-based path |
| tabs/carousel | Timed sequence of only meaningful states |
| Three.js/WebGL | Derive parameters solely from HyperFrames seek time |
| infinite loop | Finite repeats plus explicit hold or exit |

Adapt or reject `requestAnimationFrame`, `performance.now`, `Date.now`, timers, random values,
network requests, pointer state, credential/storage access, workers/worklets, or mutable WebGL
clocks. The adapted files must contain no
HTTP(S) or protocol-relative URL, fetch, XHR, WebSocket, telemetry, navigation/form egress,
dynamic import, or undeclared asset. Every file under the cue port directory must appear in
`port.files`, `adaptation_patch`, or `runtime_assets`; every local HTML/CSS/JS reference must
resolve to one of those bindings, including every `srcset` and `imagesrcset` candidate.
Binding paths are project-relative; absolute paths are invalid even when they currently point
inside the project root.

Do not port motion-anything's iframe wrapper, `window.__hf`, `__maTimeline`, `foreignObject`
capture, WebCodecs exporter, or fixed 30 FPS / 6 second assumptions. Do not invent a separate
ready gate: registration must be synchronous enough for native HyperFrames checks. Reject an
effect that requires unsupported async initialization or cannot become a pure function of
cue time without materially changing its design.

For a CSS-only composition with no `window.__timelines` entry, put `data-no-timeline` on the
root so HyperFrames does not wait for a timeline that will never exist. Keep every animated
element finite with `animation-fill-mode: both`; HyperFrames owns CSS seeking. Fonts, images,
scripts, and other browser assets are local files in the port and appear as hashed runtime
assets in the plan. Do not rely on compiler-downloaded fonts.

Run `graphic_motion_plan.validate_port(cue, project_root)` before HyperFrames opens the port.
This is a static fail-closed preflight, not an execution sandbox.

Run `npx hyperframes check`, snapshot the first visible, key interaction, final-minus-hold,
and final poses at strictly increasing cue-local times, run `npx hyperframes keyframes` and one
focused `--shot`, save a normalized
`{status: "pass", composition_id: cue-id}` check receipt,
then render the transparent sequence. Bind every contiguous RGBA PNG at the media-probe
dimensions; frame count is `ceil(duration * fps_num / fps_den)`. Review those pixels over the actual
upstream video, not on transparency alone. Source fidelity, three composites, and four snapshots
must be eight distinct files with distinct SHA-256 values.

Freeze an actual official or isolated-browser source screenshot as `source.preview` beside the
source files. Build the source-fidelity comparison from that image and a port snapshot at the
same normalized cue time: source pixels unscaled on the left, port pixels unscaled on the right,
RGB PNG, top-aligned, with black padding below the shorter image. Bind those two inputs and the
normalized time in `review.evidence.source_fidelity_inputs`. Metadata text or port pixels alone
are not source evidence.

Use [the CSS port fixture](../examples/hyperframes-port/index.html) only as a technical
contract example: sized transparent root, rational FPS, finite seekable animation, and local
assets. It is not a visual fallback and must never replace a licensed selected source.
