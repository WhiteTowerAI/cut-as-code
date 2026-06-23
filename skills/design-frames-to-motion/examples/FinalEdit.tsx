// FinalEdit.tsx — overlays land on the word
//
// The edit is a cue sheet, not a timeline. Each cue says WHICH overlay fires,
// at WHAT second, for HOW long. To time a cue you do NOT scrub a timeline — you
// grep the word-level transcript (work/transcript.json) for the phrase, read
// its start time, and paste it into `at`. Claude moves cues by editing text.
import * as React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { KeypointLedger } from "./KeypointLedger";

// Sibling overlays are built the same way as KeypointLedger (one PNG -> one
// parametric component). Stubbed here so the cue sheet reads end-to-end.
const LowerThird: React.FC = () => <AbsoluteFill />;
const ThreeWays: React.FC = () => <AbsoluteFill />;

const CUES = [
  // "…it's Thariq from the Claude Code team"
  { id: "lower-third", at: 1.2,  dur: 4.5 },
  // "Is Claude doing the right work?"
  { id: "keypoint",    at: 12.2, dur: 25.6 },
  { id: "three-ways",  at: 43.0, dur: 15.8 },
] as const;

const REGISTRY: Record<string, React.ReactNode> = {
  "lower-third": <LowerThird />,
  // Frame 295 is the word "right." (295 / 24fps ≈ 12.3s, inside the cue below).
  "keypoint": <KeypointLedger beat2At={295} />,
  "three-ways": <ThreeWays />,
};

export const FinalEdit: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      {CUES.map((cue) => (
        <Sequence
          key={cue.id}
          from={Math.round(cue.at * fps)}
          durationInFrames={Math.round(cue.dur * fps)}
        >
          {REGISTRY[cue.id]}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
