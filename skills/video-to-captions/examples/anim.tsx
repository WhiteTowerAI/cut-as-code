// anim.tsx — global caption timing knobs (frames @ 24fps). Tweak these first.
import { Easing } from "remotion";

export const TIMING = {
  popIn: 6,        // caption entrance (frames)
  popOut: 4,       // exit
};

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);

// palette
export const CREAM = "#F5F4ED";   // spoken / default text
export const CLAY = "#FF7A45";    // current word (karaoke highlight)
export const DIM = 0.55;          // not-yet-spoken word opacity
