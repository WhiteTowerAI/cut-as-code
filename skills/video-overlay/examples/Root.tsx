import * as React from "react";
import { Composition } from "remotion";
import { TitleOverlay } from "./TitleOverlay";
import { TitleVideo } from "./TitleVideo";
import { TitlePreview } from "./TitlePreview";
import sourceMeta from "./source-meta.json.example";

const FPS = sourceMeta.fps ?? 24;
const durationInFrames = Math.ceil(sourceMeta.durationInSeconds * FPS);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="TitleOverlay"
      component={TitleOverlay}
      fps={FPS}
      width={sourceMeta.width}
      height={sourceMeta.height}
      durationInFrames={durationInFrames}
    />
    <Composition
      id="TitleVideo"
      component={TitleVideo}
      fps={FPS}
      width={sourceMeta.width}
      height={sourceMeta.height}
      durationInFrames={durationInFrames}
    />
    <Composition
      id="TitlePreview"
      component={TitlePreview}
      fps={FPS}
      width={sourceMeta.width}
      height={sourceMeta.height}
      durationInFrames={durationInFrames}
    />
  </>
);
