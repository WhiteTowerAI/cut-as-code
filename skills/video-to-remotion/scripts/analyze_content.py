"""Surface motion-graphic *opportunities* from a video's own content.

Reads a word-level transcript (the work/transcript.json produced by the
video-rough-cut skill's transcribe.py) and, optionally, a list of scene-cut
timestamps, then emits work/content.json: places where an auto-generated
Remotion overlay would earn its keep —

  lower-third  speaker self-introduction        ("it's Thariq from ... team")
  stat         a number/%/$/multiplier worth flagging
  list         an enumeration ("three ways", "first ... second ...")
  keypoint     a question or punchy line worth pinning on screen
  section      a topic boundary (long pause and/or scene cut)

The agent then reads content.json, prunes it editorially, and draft_cues.py
turns the survivors into a FinalEdit cue sheet. Detection is heuristic and
meant to be *reviewed*, not trusted blind.

Usage:
  python analyze_content.py <transcript.json> [out_content.json] \
         [--scenes work/scenes.txt] [--fps 24]

--scenes: optional text file, one cut timestamp (seconds) per line, e.g.:
  ffmpeg -i work/source.mp4 -filter:v "select='gt(scene,0.4)',showinfo" \
    -f null - 2>&1 | grep showinfo \
    | sed -n 's/.*pts_time:\\([0-9.]*\\).*/\\1/p' > work/scenes.txt
"""
import sys, json, re

# ---------------------------------------------------------------- load
def load_transcript(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def flat_words(data):
    out = []
    for s in data["segments"]:
        for w in s.get("words", []):
            out.append(w)
    return out

def build_index(words):
    """full_text rebuilt from the word tokens + char-span per word, so a regex
    match offset can be mapped back to the word (and its timestamp)."""
    parts, spans, pos = [], [], 0
    for w in words:
        tok = w["word"]
        spans.append((pos, pos + len(tok)))
        parts.append(tok)
        pos += len(tok)
    return "".join(parts), spans

def time_at_char(words, spans, ci):
    for i, (a, b) in enumerate(spans):
        if a <= ci < b:
            return words[i]["start"]
    return words[0]["start"] if words else 0.0

# ---------------------------------------------------------------- detectors
INTRO_RE = re.compile(
    r"\b(?:i'?m|i am|this is|it'?s|my name is)\s+"
    r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"          # name (1-2 words)
    r"(?:\s+(?:from|with|at)\s+(?:the\s+)?"
    r"([A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,3}))?")  # opt. org

STAT_RE = re.compile(
    r"\$?\d[\d,]*(?:\.\d+)?\s*"
    r"(?:%|percent|x\b|times|k\b|m\b|bn\b|billion|million|thousand|"
    r"dollars?|fps|frames?|hours?|minutes?|seconds?|days?|weeks?|months?|years?|"
    r"users?|customers?|people)?", re.I)

LIST_RE = re.compile(
    r"\b(two|three|four|five|six|seven|\d+)\s+"
    # NB: "points" deliberately NOT here — it collides with sports/game scores
    # ("19 points") and produced 19-item "lists". Enumeration nouns only.
    r"(ways|things|reasons|steps|tips|rules|principles|lessons|"
    r"parts|stages|phases|takeaways|ideas|questions)\b", re.I)

WORD2NUM = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}

def short_label_after(full, end):
    """Up to two words following a number → its label (e.g. '4,334 frames')."""
    tail = full[end:end + 40].strip()
    m = re.match(r"([A-Za-z%][A-Za-z%\-]*(?:\s+[A-Za-z][A-Za-z\-]*)?)", tail)
    return m.group(1).strip() if m else ""

def is_interesting_number(num_txt):
    if re.search(r"[%$]|percent|x|times|fps|frame|billion|million|thousand|"
                 r"dollar|hour|minute|second|day|week|month|year|user|customer|people",
                 num_txt, re.I):
        return True
    # bare integers: only flag genuinely large ones. Two-digit numbers in speech
    # are mostly ages / school years ("year 13") / jersey numbers / game scores —
    # noise, not stats — and stat COPY is written by hand now (see SKILL.md), so
    # the detector only needs to surface the unmissable ones.
    digits = re.sub(r"[^\d]", "", num_txt.split()[0])
    if not digits:
        return False
    n = int(digits)
    if 1900 <= n <= 2099:          # a year, not a stat
        return False
    return n >= 100

# ---------------------------------------------------------------- main
def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        sys.exit(__doc__)
    transcript = args[0]
    out = "work/content.json"
    scenes_path, fps = None, 24
    rest = args[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--scenes":
            scenes_path = rest[i + 1]; i += 2
        elif rest[i] == "--fps":
            fps = int(rest[i + 1]); i += 2
        else:
            out = rest[i]; i += 1

    data = load_transcript(transcript)
    segs = data["segments"]
    words = flat_words(data)
    full, spans = build_index(words)
    dur = data.get("duration", segs[-1]["end"] if segs else 0)

    opps = []

    # lower-third: speaker self-introduction
    for m in INTRO_RE.finditer(full):
        name, org = m.group(1), m.group(2)
        at = round(time_at_char(words, spans, m.start()), 2)
        opps.append({"type": "lower-third", "at": at, "dur": 4.5,
                     "props": {"name": name, "org": org or ""},
                     "quote": m.group(0).strip()})

    # stat callouts
    for m in STAT_RE.finditer(full):
        txt = m.group(0).strip()
        if not re.match(r"\$?\d", txt) or not is_interesting_number(txt):
            continue
        at = round(time_at_char(words, spans, m.start()), 2)
        value = re.match(r"\$?[\d,.]+", txt).group(0)
        unit = txt[len(value):].strip()            # unit already inside the match
        label = unit or short_label_after(full, m.end())
        opps.append({"type": "stat", "at": at, "dur": 4.0,
                     "props": {"value": value, "label": label},
                     "quote": txt})

    # enumerated lists
    for m in LIST_RE.finditer(full):
        n_raw = m.group(1).lower()
        count = WORD2NUM.get(n_raw, int(n_raw) if n_raw.isdigit() else 3)
        at = round(time_at_char(words, spans, m.start()), 2)
        # clamp: a bad count (e.g. "62 ...") must not yield a 248s overlay
        dur = min(16.0, max(8.0, min(count, 6) * 4.0))
        opps.append({"type": "list", "at": at, "dur": dur,
                     "props": {"count": count, "title": m.group(0).strip(), "items": []},
                     "quote": m.group(0).strip()})

    # keypoints: questions get pinned
    for s in segs:
        t = s["text"].strip()
        if t.endswith("?") and len(t) > 12:
            opps.append({"type": "keypoint", "at": round(s["start"], 2), "dur": 6.0,
                         "props": {"text": t}, "quote": t})

    # sections: a new segment that starts after a long pause (>=1.8s), and/or
    # scene cuts. Title comes from the segment at/after the boundary.
    sec = []  # (time, title)
    prev_end = None
    for s in segs:
        if prev_end is not None and s["start"] - prev_end >= 1.8:
            sec.append((round(s["start"], 2), s["text"].strip()))
        prev_end = s["end"]
    if scenes_path:
        try:
            with open(scenes_path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    c = round(float(line), 2)
                    title = next((s["text"].strip() for s in segs if s["end"] >= c), "")
                    sec.append((c, title))
        except OSError:
            pass
    sec.sort()
    last_t, last_title = -100.0, None
    for c, title in sec:
        if c - last_t < 8.0 or (title and title == last_title):  # sparse + de-dup
            continue
        opps.append({"type": "section", "at": c, "dur": 3.0,
                     "props": {"title": " ".join(title.split()[:6])},
                     "quote": title[:80]})
        last_t, last_title = c, title

    opps.sort(key=lambda o: o["at"])
    content = {"source": transcript, "duration_s": round(dur, 1), "fps": fps,
               "n_opportunities": len(opps), "opportunities": opps}

    with open(out, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=1)

    # readable summary
    by_type = {}
    for o in opps:
        by_type[o["type"]] = by_type.get(o["type"], 0) + 1
    print(f"[content] {len(opps)} opportunities over {dur:.0f}s -> {out}")
    print("[content] by type:", json.dumps(by_type))
    for o in opps:
        p = ", ".join(f"{k}={v}" for k, v in o["props"].items() if v)
        print(f"  {o['at']:7.1f}s  {o['type']:<12} {p[:70]}")

if __name__ == "__main__":
    main()
