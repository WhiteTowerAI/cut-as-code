// FinalEdit.tsx - cue sheet timed by the transcript.
//
// Default render path: FinalEditOverlay renders only transparent graphics, then
// ffmpeg overlays it onto the source while copying audio. FinalEdit keeps the
// simple, slow one-pass fallback with <OffthreadVideo> as the background.
//
// staticFile() needs the file in public/  →  copy work/source.mp4 to
// public/source.mp4 for the one-pass fallback. Composition dims match the source
// (Root.tsx), so the video fills the frame with no upscale / no bars.
//
// CUES is seeded by draft_cues.py, then PRUNED and — crucially — REWRITTEN by
// hand: line1/line2/kicker/title are editorial copy you WRITE from the
// transcript (correct ASR-garbled names, add a one-line gloss), not raw
// fragments. Nudge each `at` onto the spoken word. The whole edit stays text.
import * as React from "react";
import {
  AbsoluteFill, Sequence, OffthreadVideo, staticFile, useVideoConfig,
} from "remotion";
import { Intro } from "./components/Intro";
import { SectionCard } from "./components/SectionCard";
import { LowerThird } from "./components/LowerThird";
import { StatCallout } from "./components/StatCallout";
import { KeypointCallout } from "./components/KeypointCallout";
import { ListReveal } from "./components/ListReveal";
import { Outro } from "./components/Outro";
// almanac 主题的卡(THEME="almanac" 时手工放进 CUES;深色主题不用它们)。TitleBumper/Outro
// 是 fullBleed 整屏接管;Checklist≈ListReveal、ReframeCard≈KeypointCallout 的 almanac 味渲染器。
import { TitleBumper } from "./components/TitleBumper";
import { BeforeAfter } from "./components/BeforeAfter";
import { Checklist } from "./components/Checklist";
import { CommandChips } from "./components/CommandChips";
import { PromptCard } from "./components/PromptCard";
import { ReframeCard } from "./components/ReframeCard";

const COMPONENTS: Record<string, React.FC<any>> = {
  Intro, SectionCard, LowerThird, StatCallout, KeypointCallout, ListReveal, Outro,
  TitleBumper, BeforeAfter, Checklist, CommandChips, PromptCard, ReframeCard,
};

// One design language, four card jobs (intro / chapter / lower-third / outro),
// each grounded in what's said. Copy is WRITTEN, names are corrected.
const CUES = [
  { id: "intro-1",   component: "Intro",       at: 0.6,    dur: 5.5, props: { kicker: "MONDAY MORNING MEETING · EP 14", title: "HS TOP 200", sub: "with Herschel Fruean — NZ Schoolboy Rugby" } },
  { id: "chapter-1", component: "SectionCard", at: 78.5,   dur: 5.0, props: { kicker: "PART 1", title: "The Christchurch Trip" } },
  { id: "lt-1",      component: "LowerThird",  at: 238.0,  dur: 7.0, props: { line1: "St Bede's vs Christ's", line2: "His two best teams down south" } },
  { id: "stat-1",    component: "StatCallout", at: 1316.0, dur: 4.5, props: { value: "62", label: "points — a blowout" } },
  { id: "outro-1",   component: "Outro",       at: 1861.0, dur: 8.0, props: { title: "HS TOP 200", sub: "Thanks for watching", small: "Monday Morning Meeting Podcast" } },
] as const;

const OverlayCues: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <>
      {CUES.map((cue) => {
        const C = COMPONENTS[cue.component];
        const durFrames = Math.round(cue.dur * fps);
        return (
          <Sequence key={cue.id} from={Math.round(cue.at * fps)} durationInFrames={durFrames}>
            <C {...cue.props} durFrames={durFrames} />
          </Sequence>
        );
      })}
    </>
  );
};

export const FinalEditOverlay: React.FC = () => (
  <AbsoluteFill>
    <OverlayCues />
  </AbsoluteFill>
);

export const FinalEdit: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "black" }}>
    <OffthreadVideo
      src={staticFile("source.mp4")}
      style={{ width: "100%", height: "100%", objectFit: "cover" }}
    />
    <OverlayCues />
  </AbsoluteFill>
);
