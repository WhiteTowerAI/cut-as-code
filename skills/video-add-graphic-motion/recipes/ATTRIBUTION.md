# Graphic motion recipe attribution

The recipes in this directory were vendored from
[nexu-io/motion-anything](https://github.com/nexu-io/motion-anything) at revision
`b016900d9ee92fc2d3e4dc520359cc8999d2ed4e`. Converted HyperFrames files retain credit comments found in their
original recipe implementation files.

## Upstream attribution

# ATTRIBUTION.md — third-party sources & credits

motion-anything is Apache-2.0 (see [LICENSE](LICENSE)). Portions of the library and tooling
build on the work of others. This file records every external source, its license, and how
it is used. If you believe something is misattributed, please open an issue.

## Motion effects

- **react-bits** (<https://reactbits.dev>) — 35 recipes in `recipes/web/` are faithful,
  dependency-free ports of react-bits effects (original GLSL shaders and effect logic,
  re-hosted on our zero-dependency runners; the React wrappers are fully rewritten).
  The source components are vendored under `recipes/imported/` for reference and future ports.
  **Used and redistributed with the author's permission.** The remaining `rb-*` entries in the
  library are reference cards that link back to reactbits.dev.
- **Open Design** (<https://github.com/nexu-io/open-design>, Apache-2.0) — sibling project in
  the nexu.io family. Shared here: agent engine icons (`app/agent-icons/`), design-system
  brand packs, video/HTML template collections, and the ACP runtime integration patterns
  (`docs/new-agent-runtime-acp.md`, `apps/daemon/src/acp.ts`).

## Vendored libraries (in `app/video/vendor/`)

- **mp4-muxer** — MIT. In-browser MP4 muxing for the WebCodecs export pipeline.
- **gifenc** © Matt DesLauriers — MIT. GIF encoding for the animated-GIF export.

## Bundled skills (in `skills/`)

- **web-clone** — MIT, vendored with LICENSE + ATTRIBUTION in its folder.
- **gsap skill** — GreenSock, MIT-licensed skill content, vendored with LICENSE in its folder.
- Other companion skills (text-to-lottie, web-shader-extractor, Web-to-Design-md, Toolcraft)
  are **not** vendored — the router defers to them if the user installs them; see
  [INTEGRATIONS.md](INTEGRATIONS.md).

## Reference cards

Library entries marked `ref` (with a "Get from …" link) are pointers to upstream libraries and
demos (GSAP, Motion.dev, Anime.js, LottieFiles, Rive, ShaderGradient, three.js ecosystem, …).
They embed no upstream code — each card links to the original source and license.

## Icons & fonts

- **reicon** icon set — bundled per its upstream license (see `app/data/` provenance notes).
- System font stacks only; no bundled fonts.

## Codrops Kinetic Images

- **Kinetic Images** by Dominik Fojcik / Codrops is bundled as
  `codrops/KineticImages` from
  [DGFX/codrops-kinetic-images](https://github.com/DGFX/codrops-kinetic-images)
  at revision `965dda362a8f9e5d522ed675493897200d273e49`.
- Codrops publishes downloadable demos under the MIT License unless otherwise stated:
  <https://tympanus.net/codrops/licensing/>.
- The recipe preserves the original Next.js / React Three Fiber source and assets under
`upstream/`; `LICENSE.codrops` contains the required notice. The deterministic HyperFrames
  port uses a local Three.js r175 runtime, whose own MIT notice is stored beside that runtime.

## Source-backed sticker recipes

The five directories below add 1,258 independently selectable recipes. Each directory contains one
source-level license and a machine-readable `SOURCE.json`; every converted recipe copies both into
its `hyperframes/source/` directory.

- **canvas-confetti**: 10 curated recipes under `canvas-confetti/`, using
  [catdad/canvas-confetti](https://github.com/catdad/canvas-confetti) revision
  `20eebad51dde793070c373d594099a7ed8d96e22` and npm `canvas-confetti@1.9.4`.
  License: ISC. Demo: <https://catdad.github.io/canvas-confetti/>.
- **mo.js**: 10 curated recipes under `mojs/`, using [mojs/mojs](https://github.com/mojs/mojs)
  revision `0a9cf9a87dd5637e6fa770755e79048489bcf817` and npm `@mojs/core@1.7.1`.
  License: MIT. Demo: <https://mojs.github.io/tutorials/>.
- **Line MD**: all 1,218 icons and 4 upstream aliases as 1,222 recipes under `line-md/`, using
  [cyberalien/line-md](https://github.com/cyberalien/line-md) revision
  `2ed22555cee9c1e50d4269865681d01ee8cffd7c` (`line-md@3.0.5`). License: MIT.
  Demo: <https://icon-sets.iconify.design/line-md/>.
- **Meteocons**: 12 recipes under `meteocons/`, using
  [basmilius/weather-icons](https://github.com/basmilius/weather-icons) revision
  `70dfb1d6e30dc9e791cfb0e4c5b5e5e60e972aa0` and npm `@meteocons/svg@0.1.0`.
  License: MIT. Demo: <https://meteocons.com/>.
- **tsParticles**: 4 recipes under `tsparticles/`, using official preset configurations from
  [tsparticles/tsparticles](https://github.com/tsparticles/tsparticles) revision
  `d38e87725cb0fa7108481b39064e067203068bac`. License: MIT.
Official demos: [fireworks](https://particles.js.org/demos/recipes/fireworks),
[fountain](https://particles.js.org/demos/recipes/fountain),
[firefly](https://particles.js.org/demos/recipes/firefly), and
[links](https://particles.js.org/demos/recipes/links). These recipes are deterministic Canvas ports of the
  preserved preset configurations; they do not claim to execute the asynchronous engine unchanged.

No Noto Emoji, party-js, Lucide Animated, AnimateIcons, Animated Fluent Emojis, or
react-useanimations source is included in this sticker collection.
