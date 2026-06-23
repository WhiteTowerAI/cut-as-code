// anim.tsx — global timing knobs (frames @ 24fps)
// tweak these first: every component imports from here, so the whole piece
// keeps one rhythm. Change the feel in one place, not across 11 files.
import { Easing } from "remotion";

export const TIMING = {
  reveal: 13,        // element entrance
  stagger: 4,        // gap between siblings
  overlayIn: 10,     // panel slide-in (~430ms)
  overlayOut: 8,     // fade-out
  emphasisDelay: 3,  // clay words tick in late
};

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
