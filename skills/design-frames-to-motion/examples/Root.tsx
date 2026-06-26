// Root.tsx — register the composition at 4K / 24fps
//
// durationInFrames is the length of the cut you are dressing (here 4,334 frames
// ≈ 3m at 24fps). width/height are 4K. `npx remotion render FinalEdit` reads this.
import * as React from "react";
import { Composition } from "remotion";
import { FinalEdit } from "./FinalEdit";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="FinalEdit"
    component={FinalEdit}
    durationInFrames={4334}
    fps={24}
    width={3840}
    height={2160}
  />
);
