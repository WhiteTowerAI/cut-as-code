# Pitfalls & fixes (hard-won)

The traps that cost real time on the first run. Read before starting.

## Download
- **"Video not available" / DRM / sign-in.** The default/ios/tv/web_creator player
  clients frequently fail. The reliable path:
  `yt-dlp --extractor-args "youtube:player_client=android"`. If that still can't reach
  HD, the muxed 360p (format 18) is usually the highest accessible without login —
  accept it and **document the quality ceiling** in the report. HD DASH streams are
  often DRM/login-gated; cookies may not help.

## Transcription
- **Whisper omits most vocalized "um/uh".** Disfluencies are largely absent from the
  transcript text. Therefore: detect fillers by **lexical word-search + silence-gap
  analysis combined**, never assume the transcript text reflects actual filler load.
- **Second-pass transcription noise.** Re-transcribing the cut can mis-hear repetitive
  / mumbled speech, dropping difflib similarity below 0.90 with scary-looking
  mismatches. This is transcription drift, NOT dropped content. Verify by checking
  keyword presence + a silencedetect pass (0 dead air) before blaming the edit.

## Editorial boundaries
- **Mid-sentence / stammer boundaries.** Coarse blocks set by eyeballing timestamps
  often start on a half-word ("kid.", "first", "I don't think I don't think..."). Run
  `inspect_bounds.py` and move every boundary onto a clean sentence/clause end.
- **Tiling mismatch.** A drop `in` that is 0.1s off the previous keep `out` leaves a
  sliver uncovered (or overlapping). Keep ∪ drop must exactly cover [0, duration].

## Render (the big one)
- **Memory blow-up.** Trimming N segments from ONE decoded input forces ffmpeg to
  buffer the entire decoded stream — tens of GB for a 60-min 360p video; it will thrash
  or OOM. **Fix (mandatory):** give each segment its OWN input with input-seek
  (`-ss <in> -t <dur> -i src`), then join with the `concat` filter and a single
  re-encode. Memory stays ~constant (each input decodes its small range on demand),
  it's frame-accurate, and A/V stays locked per segment. This is what `cut_render.py`
  does — do not "optimize" it back to one input.
- **Too many micro-cuts.** With SPLIT_GAP=0.6 a slow, deliberate speaker gets hundreds
  of twitchy segments. Raise SPLIT_GAP (build_edit.py 4th arg) to ~1.5s for far fewer,
  smoother cuts. Tune to the speaker's pacing.

## Auto-speed (varispeed)
- **Self-check joins must use the POST-speed duration.** A join in the output lands at
  the cumulative sum of `out_dur` = `(out-in)/speed`, NOT `(out-in)`. `selfcheck_frames.py`
  already reads `out_dur`; if you compute join times anywhere else, use it too or every
  frame-check validates the wrong frame and silently "passes".
- **`atempo`, never `asetrate`, for audio.** `atempo` changes tempo and preserves pitch;
  `asetrate` (or naive resampling) chipmunks/deepens the voice. `atempo` only accepts
  0.5–2.0 per instance — `cut_render.py` chains it for factors outside that, but the
  default 1.0–1.3 clamp stays well inside one instance.
- **Normalize per input before concat.** Different `speed` values give different frame
  cadence; without per-input `fps`/`settb`/`aresample`+`asetpts` the concat filter can
  glitch or drift A/V at joins. `cut_render.py` does this only on the varispeed path and
  keeps the original graph untouched when every speed is 1.0 (no regression).
- **Don't over-flatten.** Normalizing every render segment independently to a target kills
  natural rhythm and makes joins audibly "pumpy". `assign_speed.py` instead groups segments
  by `decision_ref`, moves out-of-band blocks only to the nearest deadband edge, clamps to
  1.0–1.3, and limits adjacent decision blocks to a 0.08x speed delta. Widen the deadband
  or lower `max_speed` before reaching for a bigger correction.
- **WPM is wrong for CJK.** Chinese/Japanese/Korean have no word spaces; Whisper emits
  per-char tokens, so words/min is meaningless. `assign_speed.py` auto-detects CJK
  (transcript `language` + char scan) and switches to chars/min with a CJK deadband.
- **Verify sync on a multi-segment clip, not a single one.** Small per-segment duration
  quantization can accumulate across many concat inputs. The A/V-duration check on the
  full cut is the real test — confirmed within ~1ms across varied-speed segments, but
  re-confirm if you change the filter graph.

## Self-check interpretation
- **Single static talking-head ⇒ jump cuts are expected.** The frame self-check hunts
  black / frozen / torn frames at joins, NOT head-position jumps. A visible head-jump
  at a cut is normal for a one-shot video and is not a defect.
- **"Almost no fillers" is unachievable at paragraph granularity.** Per-minute filler
  density can rise after cutting (you removed dead air & slow intro, not words). State
  this honestly; word-level excision is a P1/P2 polish pass and would make a one-shot
  video choppy.

## Playback (delivering the file)
- The output is H.264 High@L3.0 + AAC-LC, yuv420p, faststart — maximally compatible.
- If the user "can't open it", the cause is player-side, not the file. Common on
  **Windows 11 China/N/KN editions** which ship without the Media Feature Pack (no
  built-in H.264 decode). Fix: open with VLC, drag into Chrome/Edge, or install the
  Media Feature Pack. A re-encode won't help a missing-codec system (still H.264).
