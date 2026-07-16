import { registerRoot, Composition } from "remotion";
import * as React from "react";
import { CaptionPreview } from "./CaptionPreview";
import { CaptionPreviewGrid } from "./CaptionPreviewGrid";

const FPS = 24;

const PreviewRoot: React.FC = () => (
  <>
    <Composition
      id="CaptionPreview"
      component={CaptionPreview}
      fps={FPS}
      width={1280}
      height={720}
      durationInFrames={FPS * 8}
    />
    <Composition
      id="CaptionPreviewVertical"
      component={CaptionPreview}
      fps={FPS}
      width={1080}
      height={1920}
      durationInFrames={FPS * 8}
    />
    <Composition
      id="CaptionPreviewGridLandscape"
      component={CaptionPreviewGrid}
      fps={FPS}
      width={1920}
      height={1080}
      durationInFrames={FPS * 8}
      defaultProps={{ gridId: "landscape" }}
    />
    <Composition
      id="CaptionPreviewGridShorts"
      component={CaptionPreviewGrid}
      fps={FPS}
      width={3240}
      height={1920}
      durationInFrames={FPS * 8}
      defaultProps={{ gridId: "shorts" }}
    />
  </>
);

registerRoot(PreviewRoot);
