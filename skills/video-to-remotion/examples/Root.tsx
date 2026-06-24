// Root.tsx — register the composition at the SOURCE's own size (NOT 4K).
//
// The overlays sit ON the talking-head cut (fed in as <OffthreadVideo> inside
// FinalEdit). Match the composition to the source's dimensions and length:
//  - width/height = the source's pixels (ffprobe) → no upscaling a 360p clip to
//    4K (that only blurs it) and the aspect matches → no letterboxing. The cards
//    are vector text, so they stay crisp at any output size; render bigger with
//    `--scale 2` if you want a larger file, don't inflate the composition.
//  - durationInFrames = round(duration_s * fps) — the WHOLE cut, not a fixed 70s.
// Get all four from one probe:
//   ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
//     -show_entries format=duration -of default=nw=1 work/source.mp4
import * as React from "react";
import { Composition } from "remotion";
import { FinalEdit } from "./FinalEdit";

const FPS = 24;
const SRC_W = 1280;        // ← set to the source's width  (ffprobe)
const SRC_H = 596;         // ← set to the source's height (ffprobe; keeps the source aspect)
const DURATION_S = 70;     // ← set to the cut's length in seconds (ffprobe)

export const RemotionRoot: React.FC = () => (
  <Composition
    id="FinalEdit"
    component={FinalEdit}
    durationInFrames={Math.ceil(DURATION_S * FPS)}
    fps={FPS}
    width={SRC_W}
    height={SRC_H}
  />
);
