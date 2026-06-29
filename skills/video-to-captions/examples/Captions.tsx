// Captions.tsx — the deliverable composition: source video + burned-in captions.
//
// This is where the graphics actually go INTO the video: <OffthreadVideo> plays
// the source as the background layer (it carries the original audio through the
// render), and <Caption> draws over it. `npx remotion render` outputs the final
// captioned MP4 directly — no separate ffmpeg compositing pass needed.
//
// (Alternative, lossless path: render CaptionsOverlay with ProRes 4444,
//  yuva444p10le, and --image-format=png, then ffmpeg-overlay onto the source with
//  `-c:a copy`. See SKILL.md step 5.)
import * as React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import captions from "./captions.json";
import { Caption, Cue } from "./Caption";

export const Captions: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "black" }}>
    <OffthreadVideo src={staticFile("source.mp4")} />
    <Caption captions={captions as Cue[]} karaoke />
  </AbsoluteFill>
);
