# Source Catalog And Prior Art Report

This report turns the research in `docs/referencing repo or websites.txt` and the
motion-anything/html-video audits into the source policy for this skill. Popularity numbers
are research snapshots from 2026-07-27, useful for discovery ranking but never a license or
quality guarantee.

## Selection Criteria

A catalog source must expose a copyable HTML entry point, use inline or local CSS/JavaScript,
fit a native HyperFrames adapter without a framework rewrite, show a high craft ceiling, and
have an exact permissive license that survives freezing at an immutable revision. One failed
criterion rejects the exact candidate even when the parent project is popular.

## Automatic Search Catalog

| Catalog ID | Framework / corpus | Popularity evidence | HyperFrames fit | Copy policy |
| --- | --- | ---: | --- | --- |
| `motion-anything` | Agent recipes; mixed HTML/CSS/JS | 614 stars; 218 audited manifests | Strong discovery vocabulary; runtime varies by recipe | Discovery only. Verify the exact recipe or upstream source; reject Hippocratic-2.1, missing-license, and special-permission entries. |
| `anime-examples` | Framework-agnostic HTML + Anime.js | 71,539 stars; 82 HTML examples | Direct `window.__hfAnime`/paused-instance mapping | Copy only a frozen exact MIT example and its local dependencies. |
| `uiverse-galaxy` | Plain HTML/CSS snippets | 11,687 stars; 3,802 snippets | Direct DOM/CSS port; interaction needs finite video choreography | Verify the exact submitted files and MIT license at the frozen revision. |
| `codrops` | HTML/CSS/SVG/Canvas/WebGL demos | 500+ public demos; high-end experimental corpus | Highest visual ceiling; accept only demos that become pure functions of cue time | Copy only a specific downloadable demo/repository with an explicit compatible license. |

Official search entry points:

- `motion-anything`: https://github.com/nexu-io/motion-anything
- `anime-examples`: https://github.com/juliangarnier/anime
- `uiverse-galaxy`: https://github.com/uiverse-io/galaxy and https://uiverse.io/
- `codrops`: https://github.com/codrops and https://tympanus.net/codrops/demos/

Permitted SPDX identifiers are `MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, `ISC`,
and `CC0-1.0`. Preserve copyright and attribution requirements.

Automatic copying accepts only immutable GitHub `blob/<hex-revision>/...` URLs under
`nexu-io/motion-anything`, `juliangarnier/anime`, `uiverse-io/galaxy`, or a `codrops/*`
repository. The source and license URL must name the same repository and revision. Freeze the
exact `LICENSE`, `COPYING`, or `NOTICE` bytes beside the HTML, hash that file, and record the
required attribution. The frozen bytes must match the declared SPDX license. Because
`motion-anything` is mixed-license, its license URL must be in the selected recipe directory;
the repository-root license is insufficient. Website and mutable branch URLs remain discovery leads.

Popular sources not in the automatic range:

- `transitions.dev` is the best intent-named, copy-ready CSS packaging precedent, but no exact
  compatible repository license was verified during research. Learn from the interface; do
  not copy its code.
- Animate.css is portable and popular, but its generic entrance/exit classes rarely meet the
  requested high-end, content-specific quality bar. It is not a candidate corpus for this
  skill even when its exact MIT license is verified.
- Hover.css has commercial-use restrictions outside its free license.
- React Bits, Magic UI, Aceternity UI, Motion Primitives, Animate UI, Inspira UI, Remotion
  templates, and other framework-first libraries require a material rewrite rather than a
  minimal HTML port.
- Hubs, galleries, CodePen pages, and copied snippets without exact source and license evidence
  are discovery leads only.

## Prior Art

### motion-anything

The audit at commit `b016900` found 218 recipe manifests: 45 Apache-2.0, 14 MIT,
94 Hippocratic-2.1, and 65 without SPDX. Therefore the repository is not one uniformly
Apache-licensed copy source. Reuse only its model of a seekable artifact and its runtime
classification: CSS/WAAPI are directly seekable; GSAP/Anime/Three map to native adapters;
wall clocks, pointer state, random values, and WebGL clocks require deterministic conversion
or rejection. Do not port `hfWrapperHtml`, `window.__hf`, `__maTimeline`, iframe capture,
`foreignObject`, WebCodecs export, or fixed 30 FPS / 6 second assumptions.

### html-video

The audited html-video implementation usefully separates untrusted-source handling, local
resource freezing, readiness, alpha, exact FPS, and error propagation. Those are the right
questions, but its capture/runtime code is not a direct fit: arbitrary-page execution and a
second renderer would duplicate HyperFrames and it has no Project Protocol revision or review
contract. This skill reuses the boundaries, not the code: inspect before execution, localize
assets, require synchronous native registration, let HyperFrames own alpha/FPS/rendering, and
let `projectlib` propagate stale-plan errors.

### transitions.dev and iart-ai/motion-skills

`transitions.dev` demonstrates search by named motion intent followed by copying one exact
recipe. `iart-ai/motion-skills` demonstrates deliver-and-verify with stills, contact sheets,
and probes. This skill combines those ideas: intent first, compare exact candidates, minimally
port one, then review source fidelity and in-context pixels.

### Native HyperFrames and this repository

HyperFrames already owns seekable CSS, WAAPI, Anime.js, GSAP, Three.js, TypeGPU, transparent
PNG sequences, rational FPS, browser checks, snapshots, and rendering. `video-add-captions`
proves the PNG-overlay render family; `video-add-b-roll` proves immutable provenance and
evidence-bound review. The implementation reuses those contracts instead of adding a browser
bridge, downloader, converter, or renderer.

## Agent Search Brief

1. Bind the cue to transcript words and the understanding contact sheet. Write content,
   effect, interaction mapping, compositing mode, half-open time range, and timing rationale.
2. Timestamp the intent before searching. Search the catalog with literal visual/mechanical
   terms, not broad style adjectives.
3. Keep two or three exact candidates. Record source URL, catalog, exact license,
   popularity evidence, adaptation cost, selection/rejection decision, and a concrete reason.
4. Fail closed on license before scoring. Among licensed candidates, choose for semantic fit,
   source craft, preservation under a minimal port, readability over the actual footage, and
   non-repetition with other cues. Stars break discovery ties; they never override fit.
5. If no candidate clears the bar without redesign, skip the cue. Never substitute a generic
   fade, loader, or random decorative effect.
