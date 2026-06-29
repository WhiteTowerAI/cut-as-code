// Root.tsx - register source-sized compositions (NOT 4K).
//
// The default FinalEditOverlay composition renders transparent graphics only;
// ffmpeg composites it onto the talking-head cut. Both compositions match the
// source's dimensions and length so nothing is upscaled or letterboxed (the
// cards are vector text and stay crisp at any size; render bigger with
// `--scale 2` rather than inflating the composition).
//
// Dimensions/duration come from src/source-meta.json, written by
// `python scripts/probe.py work/source.mp4`. This replaces the old hand-edited
// SRC_W / SRC_H / DURATION_S placeholders (forget to edit them → wrong output).
// Run probe.py before `remotion render`; if you can't, hand-write
// source-meta.json with the real { width, height, durationInSeconds }.
import * as React from "react";
import { Composition } from "remotion";
import { FinalEdit, FinalEditOverlay } from "./FinalEdit";
import meta from "./source-meta.json";

const FPS = 24;
const durationInFrames = Math.ceil(meta.durationInSeconds * FPS);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="FinalEditOverlay"
      component={FinalEditOverlay}
      durationInFrames={durationInFrames}
      fps={FPS}
      width={meta.width}
      height={meta.height}
    />
    <Composition
      id="FinalEdit"
      component={FinalEdit}
      durationInFrames={durationInFrames}
      fps={FPS}
      width={meta.width}
      height={meta.height}
    />
  </>
);
