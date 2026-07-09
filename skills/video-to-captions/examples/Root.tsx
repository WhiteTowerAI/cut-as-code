// Root.tsx - register source-matched caption compositions at 24fps.
//
// Match the render length AND dimensions to the SOURCE video so captions cover
// the whole clip and the frame matches the footage.
//
// Dimensions/duration come from src/source-meta.json, written by
// `python scripts/probe.py public/source.mp4`. This replaces the old static
// 3840x2160 fields + the runtime getVideoMetadata() call (which failed on some
// server-side render paths and silently fell back to a 4K render). Run probe.py
// before `remotion render`; if you can't, hand-write source-meta.json with the
// real { width, height, durationInSeconds }.
import * as React from "react";
import { Composition } from "remotion";
import { Captions } from "./Captions";
import { CaptionsOverlay } from "./CaptionsOverlay";
import { CaptionPreview } from "./CaptionPreview";
import meta from "./source-meta.json";

const FPS = 24;
const durationInFrames = Math.ceil(meta.durationInSeconds * FPS);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Captions"
      component={Captions}
      fps={FPS}
      width={meta.width}
      height={meta.height}
      durationInFrames={durationInFrames}
    />
    <Composition
      id="CaptionsOverlay"
      component={CaptionsOverlay}
      fps={FPS}
      width={meta.width}
      height={meta.height}
      durationInFrames={durationInFrames}
    />
    <Composition
      id="CaptionPreview"
      component={CaptionPreview}
      fps={FPS}
      width={meta.width}
      height={meta.height}
      durationInFrames={durationInFrames}
    />
  </>
);
