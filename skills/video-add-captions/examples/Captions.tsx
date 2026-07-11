// Captions.tsx - simple, slow fallback: source video + burned-in captions.
//
// <OffthreadVideo> plays the source as the background layer and <Caption> draws
// over it, so `npx remotion render` outputs the final captioned MP4 directly.
// That is convenient for short clips, but slow for long videos because every
// frame seeks/decodes the source.
//
// Default path: render CaptionsOverlay with ProRes 4444, yuva444p10le, and
// --image-format=png, then ffmpeg-overlay onto the source with `-c:a copy`.
// See SKILL.md step 5.
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
