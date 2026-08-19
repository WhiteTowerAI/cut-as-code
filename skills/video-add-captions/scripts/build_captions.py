"""Build readable caption cues or a canonical caption plan from word timing.

Reads a word-level transcript (the work/transcript.json produced by the
video-cut skill's transcribe.py) and groups words into caption cues —
broken on sentence punctuation, a max line budget, a max duration, and speech
gaps — while keeping per-word timings so any renderer can highlight the current
word (karaoke).

Outputs:
  captions.json   list of { index, start, end, text, lines[], words[] }
  captions.srt    standard SubRip subtitles (portable + a quick sanity read)

Usage:
  python build_captions.py <transcript.json> [captions.json] [captions.srt] \
         [--max-chars 42] [--max-lines 2] [--max-dur 6] [--gap 0.6]
"""
import argparse
import json
import re
import sys
from pathlib import Path


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402

ENDERS = (".", "?", "!", "…", "。", "！", "？")
MIN_CUE_DUR = 0.6   # cues shorter than this (or 1 token) are merged into a neighbor
PRESENTATION_MODES = {"standard", "expressive"}
LAYOUT_VARIANTS = {"bottom-standard", "center-emphasis"}
SEMANTIC_ROLES = {"normal", "keyword", "number", "contrast"}
HERO_LINE_LEVELS = {"strong", "hero"}

def _cjk(ch):
    return ("一" <= ch <= "鿿" or "぀" <= ch <= "ヿ"
            or "가" <= ch <= "힣" or "㐀" <= ch <= "䶿")

def needs_space(a, b):
    # a space between Latin tokens, never around CJK characters
    return (
        bool(a) and bool(b) and not b.startswith("-")
        and not _cjk(a[-1]) and not _cjk(b[0])
    )

def join_tokens(tokens):
    s = ""
    for t in tokens:
        s += (" " if s and needs_space(s, t) else "") + t
    return s

def fmt_ts(t):
    ms = int(round(float(t) * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def flat_words(data):
    out = []
    for seg in data["segments"]:
        for w in seg.get("words", []):
            tok = w["word"].strip()
            if tok:
                out.append({**w, "word": tok, "start": w["start"], "end": w["end"]})
    return out

def wrap_tokens(tokens, max_chars):
    # space-aware for Latin, character-packing for CJK (no spaces)
    lines, cur = [], []
    for t in tokens:
        if cur and len(join_tokens(cur + [t])) > max_chars:
            lines.append(join_tokens(cur)); cur = [t]
        else:
            cur.append(t)
    if cur:
        lines.append(join_tokens(cur))
    return lines

def build(words, max_chars, max_lines, max_dur, gap):
    budget = max_chars * max_lines
    cues, cur = [], []

    def text_of(ws):
        return join_tokens([w["word"] for w in ws])

    def flush():
        if cur:
            cues.append({"start": round(cur[0]["start"], 3),
                         "end": round(cur[-1]["end"], 3),
                         "text": text_of(cur),
                         "clip_id": cur[0].get("clip_id"),
                         "words": [dict(w) for w in cur]})

    for i, w in enumerate(words):
        if cur and cur[0].get("clip_id") != w.get("clip_id"):
            flush(); cur = []
        # would adding this word blow the char or duration budget? close first.
        if cur:
            cand_len = len(text_of(cur + [w]))
            cand_dur = w["end"] - cur[0]["start"]
            if cand_len > budget or cand_dur > max_dur:
                flush(); cur = []
        cur.append(w)
        # hard break right after sentence-ending punctuation
        if w["word"].endswith(ENDERS):
            flush(); cur = []
            continue
        # break on a real pause before the next word
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt and (nxt["start"] - w["end"] >= gap):
            flush(); cur = []
    flush()

    # merge orphan cues (1 token or < MIN_CUE_DUR) into a neighbor so a stray
    # "So" (0.44s) doesn't flash on its own. Prefer the previous cue; a leading
    # orphan folds into the next.
    def is_orphan(c):
        return len(c["words"]) <= 1 or (c["end"] - c["start"]) < MIN_CUE_DUR
    def fits(left, right):
        words = left["words"] + right["words"]
        return (
            words[-1]["end"] - words[0]["start"] <= max_dur
            and len(text_of(words)) <= budget
        )
    merged = []
    for c in cues:
        if (
            merged
            and is_orphan(c)
            and merged[-1].get("clip_id") == c.get("clip_id")
            and fits(merged[-1], c)
        ):
            p = merged[-1]
            p["words"] = p["words"] + c["words"]
            p["end"] = c["end"]
            p["text"] = text_of(p["words"])
        else:
            merged.append(c)
    if (
        len(merged) >= 2
        and is_orphan(merged[0])
        and merged[0].get("clip_id") == merged[1].get("clip_id")
        and fits(merged[0], merged[1])
    ):
        nxt = merged[1]
        nxt["words"] = merged[0]["words"] + nxt["words"]
        nxt["start"] = merged[0]["start"]
        nxt["text"] = text_of(nxt["words"])
        merged = merged[1:]
    cues = merged

    for current, following in zip(cues, cues[1:]):
        if current["end"] > following["start"]:
            if following["start"] <= current["start"]:
                raise ValueError("caption cue timing collapsed after millisecond rounding")
            current["end"] = following["start"]

    for idx, c in enumerate(cues, 1):
        c["index"] = idx
        c["lines"] = wrap_tokens([w["word"] for w in c["words"]], max_chars)
        c["program_range"] = {"start_s": c["start"], "end_s": c["end"]}
        source_words = [word for word in c["words"] if "source_range" in word]
        c["source_ranges"] = (
            [{
                "start_s": source_words[0]["source_range"]["start_s"],
                "end_s": source_words[-1]["source_range"]["end_s"],
            }]
            if source_words else []
        )
    return cues


def add_expressive_planning_shell(plan):
    for cue in plan["cues"]:
        cue["id"] = f"cue-{cue['index']:03d}"
        for word in cue["words"]:
            word.setdefault("semantic_role", "normal")
    plan["presentation"] = {
        "schema_version": 1,
        "mode": "expressive",
        "planning_status": "draft",
        "planner": {
            "actor": "agent",
            "scope": "full-program",
            "rationale": "",
        },
        "layout_beats": [],
    }
    return plan


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _same_time(left, right):
    return _is_number(left) and _is_number(right) and abs(float(left) - float(right)) <= 1e-6


def _reject_non_expressive_hero_lines(cues, mode):
    for position, cue in enumerate(cues, 1):
        if not isinstance(cue, dict):
            continue
        if "hero_lines" in cue:
            raise ValueError(f"cue at position {position} uses unsupported hero_lines; use one hero_line")
        if "hero_line" in cue:
            raise ValueError(f"{mode} cue at position {position} must not contain hero_line")


def _validate_hero_line(cue, cue_index):
    if "hero_lines" in cue:
        raise ValueError(f"cue index {cue_index} uses unsupported hero_lines; use one hero_line")
    hero_line = cue.get("hero_line")
    if hero_line is None:
        return False
    if not isinstance(hero_line, dict):
        raise ValueError(f"cue index {cue_index} hero_line must be an object")
    if hero_line.get("level") not in HERO_LINE_LEVELS:
        raise ValueError(f"cue index {cue_index} hero_line level must be strong or hero")
    word_indexes = hero_line.get("word_indexes")
    if not isinstance(word_indexes, list) or not word_indexes:
        raise ValueError(f"cue index {cue_index} hero_line word_indexes must be a non-empty array")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in word_indexes):
        raise ValueError(f"cue index {cue_index} hero_line word_indexes must contain integers")
    if word_indexes != list(range(word_indexes[0], word_indexes[-1] + 1)):
        raise ValueError(f"cue index {cue_index} hero_line word_indexes must be unique, ordered, and contiguous")
    words = cue.get("words", [])
    if word_indexes[0] < 1 or word_indexes[-1] > len(words):
        raise ValueError(f"cue index {cue_index} hero_line word_indexes are outside the cue words")
    rationale = hero_line.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip() or "\n" in rationale or "\r" in rationale:
        raise ValueError(f"cue index {cue_index} hero_line rationale must be non-empty single-line text")
    return True


def _validate_spatial_binding(plan):
    binding = plan.get("spatial_context")
    if binding is None:
        return
    if not isinstance(binding, dict):
        raise ValueError("spatial_context must be an object")
    required = {"policy", "path", "sha256", "source_operation", "source_revision"}
    if set(binding) != required:
        raise ValueError("spatial_context binding fields are invalid")
    if binding.get("policy") != "composite-aware" or binding.get("source_operation") != "b-roll":
        raise ValueError("spatial_context policy/source operation is invalid")
    if not isinstance(binding.get("path"), str) or not binding["path"].strip():
        raise ValueError("spatial_context path must be non-empty")
    if not isinstance(binding.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", binding["sha256"]):
        raise ValueError("spatial_context sha256 must be 64 lowercase hex characters")
    revision = binding.get("source_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision <= 0:
        raise ValueError("spatial_context source_revision must be a positive integer")


def validate_caption_plan(plan, *, require_complete=False):
    if isinstance(plan, list):
        if not plan:
            raise ValueError("legacy top-level cue array must not be empty")
        _reject_non_expressive_hero_lines(plan, "legacy")
        return {"mode": "standard", "cue_count": len(plan), "layout_beat_count": 0}
    if not isinstance(plan, dict):
        raise ValueError("caption plan must be an object or a legacy top-level cue array")

    cues = plan.get("cues")
    if not isinstance(cues, list) or not cues:
        raise ValueError("canonical caption plan must contain a non-empty cues array")
    _validate_spatial_binding(plan)
    presentation = plan.get("presentation")
    if presentation is None:
        _reject_non_expressive_hero_lines(cues, "standard")
        return {"mode": "standard", "cue_count": len(cues), "layout_beat_count": 0}
    if not isinstance(presentation, dict):
        raise ValueError("presentation must be an object")

    mode = presentation.get("mode")
    if mode not in PRESENTATION_MODES:
        raise ValueError("presentation mode must be standard or expressive")
    if mode == "standard":
        _reject_non_expressive_hero_lines(cues, "standard")
        return {"mode": "standard", "cue_count": len(cues), "layout_beat_count": 0}
    if presentation.get("schema_version") != 1:
        raise ValueError("expressive presentation schema_version must be 1")

    cue_by_id = {}
    cue_positions = {}
    cue_indices = set()
    previous_index = 0
    hero_line_count = 0
    for position, cue in enumerate(cues):
        if not isinstance(cue, dict):
            raise ValueError(f"cue at position {position + 1} must be an object")
        cue_index = cue.get("index")
        if not isinstance(cue_index, int) or isinstance(cue_index, bool) or cue_index <= 0:
            raise ValueError(f"expressive cue at position {position + 1} must have a positive integer index")
        if cue_index in cue_indices:
            raise ValueError(f"duplicate cue index: {cue_index}")
        if cue_index <= previous_index:
            raise ValueError("expressive cues must remain in ascending cue index order")
        previous_index = cue_index
        cue_indices.add(cue_index)

        cue_id = cue.get("id")
        if not isinstance(cue_id, str) or not cue_id.strip():
            raise ValueError(f"expressive cue index {cue_index} must have a non-empty id")
        if cue_id in cue_by_id:
            raise ValueError(f"duplicate cue id: {cue_id}")
        if not _is_number(cue.get("start")) or not _is_number(cue.get("end")) or cue["end"] <= cue["start"]:
            raise ValueError(f"expressive cue index {cue_index} must have a positive time range")
        cue_by_id[cue_id] = cue
        cue_positions[cue_id] = position

        words = cue.get("words")
        if not isinstance(words, list) or not words:
            raise ValueError(f"expressive cue index {cue_index} must contain words")
        for word_index, word in enumerate(words, 1):
            if not isinstance(word, dict):
                raise ValueError(f"cue index {cue_index} word {word_index} must be an object")
            semantic_role = word.get("semantic_role", "normal")
            if semantic_role not in SEMANTIC_ROLES:
                raise ValueError(
                    f"cue index {cue_index} word {word_index} has invalid semantic_role: {semantic_role}"
                )
        hero_line_count += int(_validate_hero_line(cue, cue_index))

    planning_status = presentation.get("planning_status")
    if planning_status not in {"draft", "complete"}:
        raise ValueError("expressive planning_status must be draft or complete")
    if require_complete and planning_status != "complete":
        raise ValueError("expressive plan must be complete before preview generation")

    planner = presentation.get("planner")
    if not isinstance(planner, dict):
        raise ValueError("expressive planner must be an object")
    if planner.get("actor") != "agent" or planner.get("scope") != "full-program":
        raise ValueError("expressive planner must use actor agent and scope full-program")
    if planning_status == "complete" and not str(planner.get("rationale", "")).strip():
        raise ValueError("completed expressive plan requires a whole-program planning rationale")

    layout_beats = presentation.get("layout_beats")
    if not isinstance(layout_beats, list):
        raise ValueError("expressive layout_beats must be an array")
    if planning_status == "complete" and not layout_beats:
        raise ValueError("completed expressive plan requires layout beats")

    beat_ids = set()
    covered_cue_ids = set()
    previous_start = None
    previous_end = None
    previous_last_position = -1
    for beat_position, beat in enumerate(layout_beats, 1):
        if not isinstance(beat, dict):
            raise ValueError(f"layout beat {beat_position} must be an object")
        beat_id = beat.get("id")
        if not isinstance(beat_id, str) or not beat_id.strip():
            raise ValueError(f"layout beat {beat_position} must have a non-empty id")
        if beat_id in beat_ids:
            raise ValueError(f"duplicate layout beat id: {beat_id}")
        beat_ids.add(beat_id)

        variant = beat.get("variant")
        if variant == "top-statement":
            raise ValueError(
                f"layout beat {beat_id} uses removed variant top-statement; "
                "the plan must be replanned as bottom-standard or center-emphasis"
            )
        if variant not in LAYOUT_VARIANTS:
            raise ValueError(f"layout beat {beat_id} has invalid variant: {variant}")
        cue_ids = beat.get("cue_ids")
        if not isinstance(cue_ids, list) or not cue_ids:
            raise ValueError(f"layout beat {beat_id} must reference one or more cue_ids")

        positions = []
        for cue_id in cue_ids:
            if cue_id not in cue_by_id:
                raise ValueError(f"layout beat {beat_id} references unknown cue id/index: {cue_id}")
            if cue_id in covered_cue_ids:
                raise ValueError(f"cue {cue_id} is referenced by more than one layout beat")
            positions.append(cue_positions[cue_id])
        if positions != list(range(positions[0], positions[-1] + 1)):
            raise ValueError(f"layout beat {beat_id} cue_ids must be contiguous and ordered")

        program_range = beat.get("program_range")
        if not isinstance(program_range, dict):
            raise ValueError(f"layout beat {beat_id} must have a program_range")
        start_s = program_range.get("start_s")
        end_s = program_range.get("end_s")
        if not _is_number(start_s) or not _is_number(end_s) or end_s <= start_s:
            raise ValueError(f"layout beat {beat_id} must have a positive program_range")
        first_cue = cue_by_id[cue_ids[0]]
        last_cue = cue_by_id[cue_ids[-1]]
        if not _same_time(start_s, first_cue["start"]) or not _same_time(end_s, last_cue["end"]):
            raise ValueError(f"layout beat {beat_id} starts or ends inside a cue")
        if previous_start is not None and start_s < previous_start:
            raise ValueError("layout beats must be sorted by time")
        if previous_end is not None and start_s < previous_end:
            raise ValueError(f"layout beat {beat_id} overlaps the previous layout beat")
        if positions[0] <= previous_last_position:
            raise ValueError("layout beats must follow cue order")
        if planning_status == "complete" and not str(beat.get("rationale", "")).strip():
            raise ValueError(f"completed layout beat {beat_id} requires a rationale")

        covered_cue_ids.update(cue_ids)
        previous_start = start_s
        previous_end = end_s
        previous_last_position = positions[-1]

    if planning_status == "complete" and covered_cue_ids != set(cue_by_id):
        missing = [cue_id for cue_id in cue_by_id if cue_id not in covered_cue_ids]
        raise ValueError("completed expressive plan does not cover every cue: " + ", ".join(missing))

    return {
        "mode": "expressive",
        "planning_status": planning_status,
        "cue_count": len(cues),
        "layout_beat_count": len(layout_beats),
        "hero_line_count": hero_line_count,
    }


def build_plan(
    transcript, timeline, *, source_transcript, max_chars=42, max_lines=2,
    max_dur=6.0, gap=0.6, presentation_mode="standard",
):
    if presentation_mode not in PRESENTATION_MODES:
        raise ValueError("presentation mode must be standard or expressive")
    mapped = projectlib.map_transcript_to_timeline(transcript, timeline)
    words = flat_words(mapped)
    if not words:
        raise ValueError("no retained word-level timestamps in transcript")
    cues = build(words, max_chars, max_lines, max_dur, gap)
    plan = {
        "schema_version": 1,
        "target": "overlay",
        "timeline_id": timeline["timeline_id"],
        "timebase": "program",
        "source_transcript": source_transcript,
        "program_duration_s": timeline["program_duration_s"],
        "cue_settings": {
            "max_chars": max_chars,
            "max_lines": max_lines,
            "max_duration_s": max_dur,
            "gap_s": gap,
        },
        "style": {
            "status": "draft",
            "selection_mode": None,
            "selection_rationale": "",
        },
        "review": {"status": "pending", "evidence": []},
        "cues": cues,
        "renderer_recipe": {
            "engine": "hyperframes",
            "composition": "cache/captions/index.html",
            "asset": "cache/captions/overlay-frames",
            "asset_type": "image-sequence",
            "pattern": "frame_%06d.png",
            "start_number": 1,
            "fps": dict(timeline["fps"]),
            "runtime_assets": [],
        },
    }
    if presentation_mode == "expressive":
        add_expressive_planning_shell(plan)
    return plan


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", nargs="?")
    parser.add_argument("out_json", nargs="?", default="captions.json")
    parser.add_argument("out_srt", nargs="?", default="captions.srt")
    parser.add_argument("--timeline")
    parser.add_argument("--source-transcript")
    parser.add_argument("--presentation-mode", choices=sorted(PRESENTATION_MODES), default="standard")
    parser.add_argument("--validate-plan")
    parser.add_argument("--max-chars", type=int, default=42)
    parser.add_argument("--max-lines", type=int, default=2)
    parser.add_argument("--max-dur", type=float, default=6.0)
    parser.add_argument("--gap", type=float, default=0.6)
    args = parser.parse_args(argv)
    if args.max_chars < 1 or args.max_lines < 1 or args.max_dur <= 0 or args.gap < 0:
        parser.error("caption grouping limits must be positive (gap may be zero)")
    if not args.validate_plan and not args.transcript:
        parser.error("transcript is required unless --validate-plan is used")
    if args.presentation_mode == "expressive" and not args.timeline and not args.validate_plan:
        parser.error("--presentation-mode expressive requires --timeline and a canonical caption plan")
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.validate_plan:
        with open(args.validate_plan, encoding="utf-8-sig") as handle:
            plan = json.load(handle)
        try:
            summary = validate_caption_plan(plan, require_complete=True)
        except ValueError as error:
            raise SystemExit(f"[captions] invalid plan: {error}") from error
        print(
            f"[captions] plan validation passed: mode={summary['mode']} "
            f"cues={summary['cue_count']} layout_beats={summary['layout_beat_count']}"
        )
        return

    with open(args.transcript, encoding="utf-8") as handle:
        transcript = json.load(handle)
    if args.timeline:
        with open(args.timeline, encoding="utf-8") as handle:
            timeline = json.load(handle)
        output = build_plan(
            transcript,
            timeline,
            source_transcript=args.source_transcript or args.transcript,
            max_chars=args.max_chars,
            max_lines=args.max_lines,
            max_dur=args.max_dur,
            gap=args.gap,
            presentation_mode=args.presentation_mode,
        )
        cues = output["cues"]
    else:
        words = flat_words(transcript)
        if not words:
            raise SystemExit("[captions] no word-level timestamps in transcript")
        cues = build(words, args.max_chars, args.max_lines, args.max_dur, args.gap)
        output = cues

    out_json = Path(args.out_json)
    out_srt = Path(args.out_srt)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=1)
    srt = []
    for c in cues:
        srt.append(f"{c['index']}\n{fmt_ts(c['start'])} --> {fmt_ts(c['end'])}\n"
                   + "\n".join(c["lines"]) + "\n")
    with open(out_srt, "w", encoding="utf-8") as handle:
        handle.write("\n".join(srt))

    durs = [c["end"] - c["start"] for c in cues]
    chars = [len(c["text"]) for c in cues]
    word_count = sum(len(cue["words"]) for cue in cues)
    print(f"[captions] {len(cues)} cues from {word_count} words "
          f"-> {out_json} + {out_srt}")
    print(f"[captions] dur avg={sum(durs)/len(durs):.1f}s max={max(durs):.1f}s | "
          f"chars avg={sum(chars)//len(chars)} max={max(chars)} "
          f"(budget {args.max_chars*args.max_lines})")
    for c in cues[:6]:
        print(f"  {c['start']:6.1f}-{c['end']:6.1f}  {c['text'][:60]}")

if __name__ == "__main__":
    main()
