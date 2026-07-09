#!/usr/bin/env python3
"""Generate video-to-shorts candidate highlights."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def repo_root_from_package():
    return Path(__file__).resolve().parents[3]


REPO_ROOT = repo_root_from_package()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skills._shared.openai_compatible_llm import (  # noqa: E402
    LLMConfigError,
    LLMRequestError,
    chat_completion,
    resolve_config,
)
from criteria import criteria_for_prompt  # noqa: E402
from preview import write_candidates_preview_html, write_candidates_preview_md  # noqa: E402
from transcript_utils import (  # noqa: E402
    excerpt_for_range,
    fmt_time,
    load_json,
    overlap_ratio,
    transcript_duration,
    transcript_text,
    write_json,
)


def fail(message):
    raise SystemExit(message)


def parse_json_loose(raw):
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def build_prompt(transcript, max_candidates, min_duration, max_duration):
    duration = transcript_duration(transcript)
    text = transcript_text(transcript)
    target = max(8, min(12, max_candidates))
    return f"""You are selecting high-potential YouTube Shorts from a transcript.

{criteria_for_prompt()}

Task:
- Generate {target} candidate shorts if the transcript supports it.
- Target duration: {min_duration:.0f}-{max_duration:.0f} seconds.
- Every candidate must start with a strong hook and feel self-contained.
- Never cut mid-sentence or mid-thought.
- start_time must begin at the first word of a complete sentence or complete thought.
- end_time must land after the final word of a complete sentence or complete thought.
- Do not start with fragment phrases like "Has arrived now" when prior context is needed.
- Do not end with dangling words or incomplete clauses such as "and", "that", "our", "to", "of", or "in fact, that".
- Prefer a slightly longer complete clip over a shorter fragment, as long as it stays within the duration range.
- Avoid overlapping candidates. If two candidates cover the same idea, keep the stronger one.
- Score each candidate 0-100 for short-form potential, not general quality.
- Use transcript timestamps only. Do not invent content.
- transcript_excerpt must be copied or tightly paraphrased from the exact candidate time range.

Return ONLY valid JSON:
{{
  "content_type": "lecture|podcast|interview|tutorial|commentary|other",
  "density": "low|medium|high",
  "candidates": [
    {{
      "title": "string",
      "start_time": 0.0,
      "end_time": 45.0,
      "score": 85,
      "hook_sentence": "string",
      "virality_reason": "string"
    }}
  ]
}}

Transcript duration: {duration:.3f}s

Transcript:
{text}
"""


def normalize_candidate(item, idx, duration, min_duration, max_duration, transcript):
    start = float(item.get("start_time", -1))
    end = float(item.get("end_time", -1))
    if start < 0 or end <= start:
        return None
    start = max(0.0, min(duration, start))
    end = max(0.0, min(duration, end))
    if end <= start:
        return None
    cand_duration = round(end - start, 3)
    warnings = []
    if cand_duration < min_duration:
        warnings.append("SHORT_DURATION")
    if cand_duration > max_duration:
        warnings.append("LONG_DURATION")
    excerpt = excerpt_for_range(transcript, start, end)
    if not excerpt:
        return None
    score = int(float(item.get("score", 0)))
    score = max(0, min(100, score))
    return {
        "candidate_id": f"cand-{idx:03d}",
        "title": str(item.get("title") or f"Candidate {idx}").strip(),
        "start_time": round(start, 3),
        "end_time": round(end, 3),
        "duration": cand_duration,
        "score": score,
        "hook_sentence": str(item.get("hook_sentence") or "").strip(),
        "virality_reason": str(item.get("virality_reason") or "").strip(),
        "transcript_excerpt": excerpt,
        "warnings": warnings,
        "review_status": "candidate",
        "metadata": {},
    }


def dedupe_candidates(candidates):
    ordered = sorted(candidates, key=lambda c: c["score"], reverse=True)
    kept = []
    for cand in ordered:
        too_close = False
        for existing in kept:
            if overlap_ratio(cand, existing) > 0.5:
                too_close = True
                break
        if not too_close:
            kept.append(cand)
    for idx, cand in enumerate(kept, start=1):
        cand["candidate_id"] = f"cand-{idx:03d}"
    return kept


def validate_and_build(parsed, transcript, video_path, transcript_path, args, config):
    duration = transcript_duration(transcript)
    raw_candidates = parsed.get("candidates")
    if not isinstance(raw_candidates, list):
        raw_candidates = parsed.get("highlights")
    if not isinstance(raw_candidates, list):
        raise ValueError("LLM JSON must contain a candidates array.")

    normalized = []
    for idx, item in enumerate(raw_candidates, start=1):
        if not isinstance(item, dict):
            continue
        cand = normalize_candidate(
            item,
            idx,
            duration,
            args.min_duration,
            args.max_duration,
            transcript,
        )
        if cand:
            normalized.append(cand)

    if not normalized:
        raise ValueError("No valid candidates after validation.")

    normalized = dedupe_candidates(normalized)[: args.max_candidates]
    return {
        "schema_version": "shorts-candidates.v1",
        "video": {
            "source": str(video_path),
            "duration_s": round(duration, 3),
        },
        "transcript": {
            "path": str(transcript_path),
            "timebase": "input_video_relative",
            "source": "provided",
        },
        "producer": {
            "skill": "video-to-shorts",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "llm_provider": config["provider"],
            "llm_model": config["model"],
        },
        "selection": {
            "target_count": args.max_candidates,
            "target_aspect_ratio": "9:16",
            "duration_range_s": {
                "min": args.min_duration,
                "max": args.max_duration,
            },
            "content_type": str(parsed.get("content_type") or "other"),
            "density": str(parsed.get("density") or "medium"),
        },
        "candidates": normalized,
        "metadata": {
            "notes": "Generated by Phase 1 highlight selection. Review before creating shorts_plan.json.",
        },
    }


def write_error_files(out_dir, message, raw_response=""):
    write_json(out_dir / "llm_error.json", {"error": message})
    (out_dir / "llm_raw_response.txt").write_text(raw_response or "", encoding="utf-8")


def call_and_parse(prompt, args, out_dir):
    raw = ""
    try:
        config = resolve_config(base_url=args.base_url, model=args.model)
        raw = chat_completion(prompt, base_url=args.base_url, model=args.model, temperature=0.2)
        try:
            return parse_json_loose(raw), raw, config
        except Exception:
            repair_prompt = (
                "Repair this response into valid JSON only. Preserve all candidate fields.\n\n"
                + raw
            )
            repaired = chat_completion(repair_prompt, base_url=args.base_url, model=args.model, temperature=0.0)
            raw = repaired
            return parse_json_loose(repaired), raw, config
    except (LLMConfigError, LLMRequestError, Exception) as e:
        write_error_files(out_dir, str(e), raw)
        raise


def run_candidates(args):
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        fail(f"video not found: {video_path}")
    transcript_path = out_dir / "transcript.json"
    if not transcript_path.exists():
        fail(f"transcript not found: {transcript_path}. Run prepare_transcript.py first.")

    transcript = load_json(transcript_path)
    prompt = build_prompt(transcript, args.max_candidates, args.min_duration, args.max_duration)
    try:
        parsed, raw, config = call_and_parse(prompt, args, out_dir)
        result = validate_and_build(parsed, transcript, video_path, transcript_path, args, config)
    except Exception as e:
        print(f"[video-to-shorts] LLM candidate generation failed: {e}", file=sys.stderr)
        print(f"[video-to-shorts] wrote: {out_dir / 'llm_error.json'}", file=sys.stderr)
        print(f"[video-to-shorts] wrote: {out_dir / 'llm_raw_response.txt'}", file=sys.stderr)
        raise SystemExit(1)

    candidates_path = out_dir / "shorts_candidates.json"
    preview_md = out_dir / "shorts_candidates_preview.md"
    preview_html = out_dir / "shorts_candidates_preview.html"
    write_json(candidates_path, result)
    write_candidates_preview_md(preview_md, result)
    write_candidates_preview_html(preview_html, result)
    print(f"[video-to-shorts] candidates: {candidates_path}")
    print(f"[video-to-shorts] preview md: {preview_md}")
    print(f"[video-to-shorts] preview html: {preview_html}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate reviewable short-form candidates from work/shorts/transcript.json."
    )
    parser.add_argument("--video", required=True, help="Input video path.")
    parser.add_argument("--out", required=True, help="Output work/shorts directory.")
    parser.add_argument("--model", help="LLM model. Overrides LLM_MODEL.")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL. Overrides LLM_BASE_URL.")
    parser.add_argument("--max-candidates", type=int, default=12, help="Maximum candidates to keep.")
    parser.add_argument("--min-duration", type=float, default=20.0, help="Minimum candidate duration in seconds.")
    parser.add_argument("--max-duration", type=float, default=90.0, help="Maximum candidate duration in seconds.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    run_candidates(args)


if __name__ == "__main__":
    main()
