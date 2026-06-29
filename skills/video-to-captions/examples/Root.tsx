// Root.tsx - register source-matched caption compositions at 24fps.
//
// Match the render length AND dimensions to the SOURCE video so captions cover the
// whole clip and the frame matches the footage.
//
// VERIFY in your Remotion version: getVideoMetadata (@remotion/media-utils) inside
// calculateMetadata works in some setups but not all server-side render paths; the
// current recommendation is often parseMedia from @remotion/media-parser. If it
// throws at render, delete calculateMetadata and rely on the static fields below
// (set width/height to your footage — 1080x1920 for vertical, etc.; the static
// durationInFrames is derived from the last caption, so add tail if needed).
import * as React from "react";
import { Composition } from "remotion";
import { getVideoMetadata } from "@remotion/media-utils";
import { staticFile } from "remotion";
import { Captions } from "./Captions";
import { CaptionsOverlay } from "./CaptionsOverlay";
import captions from "./captions.json";

const FPS = 24;
const lastEnd = captions.length ? captions[captions.length - 1].end : 0;
const fallbackDurationInFrames = Math.ceil(lastEnd * FPS) + FPS;

const matchSourceMetadata = async () => {
  // match the actual source video length + dimensions
  const m = await getVideoMetadata(staticFile("source.mp4"));
  return {
    durationInFrames: Math.ceil(m.durationInSeconds * FPS),
    width: m.width,
    height: m.height,
  };
};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Captions"
      component={Captions}
      fps={FPS}
      width={3840}
      height={2160}
      durationInFrames={fallbackDurationInFrames}
      calculateMetadata={matchSourceMetadata}
    />
    <Composition
      id="CaptionsOverlay"
      component={CaptionsOverlay}
      fps={FPS}
      width={3840}
      height={2160}
      durationInFrames={fallbackDurationInFrames}
      calculateMetadata={matchSourceMetadata}
    />
  </>
);
