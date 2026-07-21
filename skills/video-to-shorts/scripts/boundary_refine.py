"""Boundary refinement helpers for Phase 2.5 extraction polish."""

import re
import subprocess

from transcript_utils import transcript_duration


PUNCTUATION_ENDINGS = (".", "?", "!", "。", "！", "？")
UNFINISHED_END_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "because",
    "dollar",
    "for",
    "from",
    "in",
    "into",
    "of",
    "or",
    "our",
    "that",
    "the",
    "to",
    "with",
}
UNFINISHED_TAILS = (
    ("in", "fact", "that"),
    ("and", "so"),
    ("have", "said"),
    ("people", "have", "said"),
)
START_MARKERS = (
    ("and", "now"),
    ("and", "so"),
    ("in", "fact"),
)


def clamp(value, low, high):
    return max(low, min(high, value))


def flatten_words(transcript):
    words = []
    for segment in transcript.get("segments", []):
        for word in segment.get("words") or []:
            text = str(word.get("word", "")).strip()
            if not text:
                continue
            try:
                start = float(word.get("start", 0.0))
                end = float(word.get("end", start))
            except (TypeError, ValueError):
                continue
            if end >= start:
                words.append({"word": text, "start": start, "end": end})
    return words


def should_start_new_phrase(current, next_word, following_word, gap, pause_threshold):
    if not current:
        return False
    if gap >= pause_threshold:
        return True
    nxt = clean_token(next_word["word"])
    following = clean_token(following_word["word"]) if following_word else ""
    if (nxt, following) in START_MARKERS:
        return True
    if is_sentence_end(current[-1]["word"]):
        return True
    return False


def split_words_into_phrases(words, pause_threshold):
    phrases = []
    current = []
    for idx, word in enumerate(words):
        if current:
            gap = word["start"] - current[-1]["end"]
            following_word = words[idx + 1] if idx + 1 < len(words) else None
            if should_start_new_phrase(current, word, following_word, gap, pause_threshold):
                phrases.append(current)
                current = []
        current.append(word)
    if current:
        phrases.append(current)
    return phrases


def segment_word_ranges(transcript, pause_threshold=0.45):
    ranges = []
    for segment in transcript.get("segments", []):
        seg_words = []
        for word in segment.get("words") or []:
            text = str(word.get("word", "")).strip()
            if not text:
                continue
            try:
                start = float(word.get("start", 0.0))
                end = float(word.get("end", start))
            except (TypeError, ValueError):
                continue
            if end >= start:
                seg_words.append({"word": text, "start": start, "end": end})
        for phrase_words in split_words_into_phrases(seg_words, pause_threshold):
            ranges.append({
                "start": phrase_words[0]["start"],
                "end": phrase_words[-1]["end"],
                "words": phrase_words,
                "text": " ".join(w["word"] for w in phrase_words),
            })
    return ranges


def word_overlaps(word, start, end):
    return word["start"] < end and word["end"] > start


def pause_before(words, index):
    if index <= 0:
        return None
    return words[index]["start"] - words[index - 1]["end"]


def pause_after(words, index):
    if index >= len(words) - 1:
        return None
    return words[index + 1]["start"] - words[index]["end"]


def is_sentence_end(token):
    return token.rstrip().endswith(PUNCTUATION_ENDINGS)


def clean_token(token):
    return re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", token).lower()


def looks_unfinished(words):
    if not words:
        return True
    cleaned = [clean_token(w["word"]) for w in words if clean_token(w["word"])]
    if not cleaned:
        return True
    if cleaned[-1] in UNFINISHED_END_WORDS:
        return True
    tail3 = tuple(cleaned[-3:])
    tail2 = tuple(cleaned[-2:])
    if tail3 in UNFINISHED_TAILS or tail2 in UNFINISHED_TAILS:
        return True
    return False


def segment_index_at(segments, time_value):
    for idx, segment in enumerate(segments):
        if segment["start"] <= time_value <= segment["end"]:
            return idx
    for idx, segment in enumerate(segments):
        if segment["end"] >= time_value:
            return idx
    return max(0, len(segments) - 1)


def next_complete_segment(segments, segment_idx, original_start, max_shift=3.0):
    for idx in range(segment_idx + 1, len(segments)):
        segment = segments[idx]
        if segment["start"] < original_start:
            continue
        if segment["start"] - original_start > max_shift:
            break
        if not looks_unfinished(segment["words"]):
            return idx
    return segment_idx


def choose_start(words, segments, original_start, original_end, max_expand, pause_threshold):
    overlapping = [
        (idx, word) for idx, word in enumerate(words) if word_overlaps(word, original_start, original_end)
    ]
    if not overlapping:
        return original_start, ["NO_WORD_AT_START"]

    first_idx, first_word = overlapping[0]
    reasons = []
    if first_word["start"] < original_start < first_word["end"]:
        reasons.append("START_WAS_INSIDE_WORD")

    if segments:
        segment_idx = segment_index_at(segments, first_word["start"])
        segment = segments[segment_idx]
        if original_start - segment["start"] > 3.0 or looks_unfinished(segment["words"]):
            new_idx = next_complete_segment(segments, segment_idx, original_start)
            if new_idx != segment_idx:
                segment = segments[new_idx]
                reasons.append("START_MOVED_FORWARD_TO_COMPLETE_PHRASE")
        start = segment["start"]
        if start < first_word["start"]:
            reasons.append("START_SNAPPED_TO_SEGMENT_START")
    else:
        start = first_word["start"]
    return start, reasons


def choose_end(words, segments, original_start, original_end, max_expand, pause_threshold, max_duration):
    overlapping = [
        (idx, word) for idx, word in enumerate(words) if word_overlaps(word, original_start, original_end)
    ]
    if not overlapping:
        return original_end, ["NO_WORD_AT_END"]

    last_idx, last_word = overlapping[-1]
    reasons = []
    if last_word["start"] < original_end < last_word["end"]:
        reasons.append("END_WAS_INSIDE_WORD")

    if segments:
        start_segment = segments[segment_index_at(segments, overlapping[0][1]["start"])]
        segment_idx = segment_index_at(segments, last_word["end"])
        selected = segments[segment_idx]
        reasons.append("END_SNAPPED_TO_SEGMENT_END")
        while looks_unfinished(selected["words"]) and segment_idx < len(segments) - 1:
            candidate = segments[segment_idx + 1]
            if candidate["end"] - start_segment["start"] > max_duration:
                reasons.append("END_EXTENSION_HIT_MAX_DURATION")
                break
            selected = candidate
            segment_idx += 1
            reasons.append("END_EXTENDED_FOR_COMPLETE_THOUGHT")
        end = selected["end"]
    else:
        boundary_idx = last_idx
        for idx in range(last_idx, len(words)):
            word = words[idx]
            if word["end"] - original_end > max_expand:
                break
            gap = pause_after(words, idx)
            boundary_idx = idx
            if is_sentence_end(word["word"]) or (gap is not None and gap >= pause_threshold):
                reasons.append("END_SNAPPED_TO_PHRASE_BOUNDARY")
                break
        end = words[boundary_idx]["end"]
        if looks_unfinished(words[: boundary_idx + 1]):
            reasons.append("END_MAY_BE_UNFINISHED")
    return end, reasons


def cap_handle_before(words, content_start, desired_start, previous_release_guard=0.12):
    previous = [w for w in words if w["end"] <= content_start]
    if not previous:
        return desired_start
    prev_end = previous[-1]["end"]
    if desired_start < prev_end + previous_release_guard:
        return min(content_start, prev_end + previous_release_guard)
    return desired_start


def cap_handle_after(
    words,
    content_end,
    desired_end,
    target_tail=0.30,
    min_final_word_tail=0.25,
    max_tail=0.45,
    min_tail_margin=0.25,
):
    following = [
        word
        for word in words
        if word["end"] > content_end + 0.001
    ]
    reasons = []
    desired_tail = max(0.0, desired_end - content_end)
    desired_tail = min(
        max_tail,
        max(target_tail, min_final_word_tail, min(desired_tail, max_tail)),
    )
    desired_end = content_end + desired_tail

    if following and desired_end > following[0]["start"]:
        reasons.append("TAIL_OVERLAP_ALLOWED_FOR_FINAL_WORD_RELEASE")

    if desired_end - content_end < min_tail_margin:
        reasons.append("TIGHT_TAIL_MARGIN")
    return desired_end, reasons


def extend_for_tail_margin(segments, current_content_start, current_content_end, desired_tail, max_duration):
    selected_idx = None
    for idx, segment in enumerate(segments):
        if segment["start"] <= current_content_end <= segment["end"] + 0.001:
            selected_idx = idx
            break
    if selected_idx is None:
        return current_content_end, []

    reasons = []
    while selected_idx < len(segments) - 1:
        next_segment = segments[selected_idx + 1]
        gap = next_segment["start"] - current_content_end
        if gap >= desired_tail:
            break
        if next_segment["end"] - current_content_start > max_duration:
            reasons.append("TAIL_MARGIN_HIT_MAX_DURATION")
            break
        current_content_end = next_segment["end"]
        selected_idx += 1
        reasons.append("END_EXTENDED_FOR_TAIL_MARGIN")
        if not looks_unfinished(next_segment["words"]):
            continue
    return current_content_end, reasons


def first_last_text_for_range(words, start, end, count=10):
    inside = [
        w["word"]
        for w in words
        if w["start"] >= start - 0.001 and w["end"] <= end + 0.001
    ]
    return {
        "first_words": " ".join(inside[:count]),
        "last_words": " ".join(inside[-count:]),
        "word_count": len(inside),
    }


def completeness_for_range(words, start, end):
    inside = [
        w
        for w in words
        if w["start"] >= start - 0.001 and w["end"] <= end + 0.001
    ]
    if not inside:
        return {
            "first_sentence_complete": False,
            "last_sentence_complete": False,
            "ends_with_unfinished_word": True,
        }
    return {
        "first_sentence_complete": True,
        "last_sentence_complete": not looks_unfinished(inside),
        "ends_with_unfinished_word": looks_unfinished(inside),
    }


def detect_scene_cuts(ffmpeg, video_path, start, end, threshold=0.35):
    duration = end - start
    if duration <= 0:
        return []
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(video_path),
        "-t",
        f"{duration:.3f}",
        "-vf",
        f"select='gt(scene,{threshold})',showinfo",
        "-an",
        "-f",
        "null",
        "NUL",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        return [{"warning": "SCENE_DETECTION_FAILED", "message": p.stderr.strip()[-500:]}]
    cuts = []
    for match in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", p.stderr):
        rel = float(match.group(1))
        cuts.append({
            "time": round(start + rel, 3),
            "relative_time": round(rel, 3),
        })
    deduped = []
    for cut in cuts:
        if not deduped or abs(cut["relative_time"] - deduped[-1]["relative_time"]) > 0.2:
            deduped.append(cut)
    return deduped


def refine_short_boundary(
    short_item,
    transcript,
    ffmpeg=None,
    video_path=None,
    pre_roll=0.25,
    post_roll=0.30,
    max_expand=1.5,
    pause_threshold=0.45,
    scene_threshold=0.35,
    max_duration=90.0,
    tail_padding=0.30,
    target_tail=0.30,
    min_final_word_tail=0.25,
    max_tail=0.45,
    hard_next_word_overlap_limit=0.20,
    min_tail_margin=0.25,
    media_duration=None,
    snap_to_phrases=True,
):
    original_start = float(short_item["start_time"])
    original_end = float(short_item["end_time"])
    video_duration = (
        float(media_duration)
        if isinstance(media_duration, (int, float))
        else transcript_duration(transcript)
    )
    warnings = []
    reasons = []

    words = flatten_words(transcript)
    segments = segment_word_ranges(transcript, pause_threshold=pause_threshold)
    if snap_to_phrases:
        content_start, start_reasons = choose_start(
            words,
            segments,
            original_start,
            original_end,
            max_expand,
            pause_threshold,
        )
        content_end, end_reasons = choose_end(
            words,
            segments,
            original_start,
            original_end,
            max_expand,
            pause_threshold,
            max_duration,
        )
    else:
        overlapping = [
            word for word in words if word_overlaps(word, original_start, original_end)
        ]
        content_start = original_start
        content_end = overlapping[-1]["end"] if overlapping else original_end
        start_reasons = ["SEMANTIC_BOUNDARY_REFINEMENT_DISABLED"]
        end_reasons = ["RAW_END_PROTECTED_BY_RELEASE_HANDLE"]
    reasons.extend(start_reasons)
    reasons.extend(end_reasons)
    start = (
        cap_handle_before(
            words,
            content_start,
            clamp(content_start - pre_roll, 0.0, video_duration),
        )
        if snap_to_phrases
        else clamp(original_start, 0.0, video_duration)
    )
    end = max(original_end, content_end + max(post_roll, tail_padding))
    end, tail_cap_reasons = cap_handle_after(
        words,
        content_end,
        end,
        target_tail=target_tail,
        min_final_word_tail=min_final_word_tail,
        max_tail=max_tail,
        min_tail_margin=min_tail_margin,
    )
    end = clamp(end, 0.0, video_duration)
    reasons.extend(tail_cap_reasons)
    if "TAIL_OVERLAP_ALLOWED_FOR_FINAL_WORD_RELEASE" in tail_cap_reasons:
        warnings.append("TAIL_OVERLAP_ALLOWED_FOR_FINAL_WORD_RELEASE")
    if "TIGHT_TAIL_MARGIN" in tail_cap_reasons:
        warnings.append("TIGHT_TAIL_MARGIN")
    if end <= start:
        start, end = original_start, original_end
        content_start, content_end = original_start, original_end
        warnings.append("REFINEMENT_INVALID_USED_ORIGINAL")

    scene_cuts = []
    if ffmpeg and video_path:
        scene_result = detect_scene_cuts(ffmpeg, video_path, start, end, threshold=scene_threshold)
        if scene_result and "warning" in scene_result[0]:
            warnings.append(scene_result[0]["warning"])
        else:
            scene_cuts = scene_result

    for cut in scene_cuts:
        near_start = cut["time"] - start <= 1.0
        near_end = end - cut["time"] <= 1.0
        if near_start:
            warnings.append("SCENE_CUT_NEAR_START")
        elif near_end:
            warnings.append("SCENE_CUT_NEAR_END")
        else:
            warnings.append("POSSIBLE_JUMP_CUT")

    if abs(start - original_start) > 0.001:
        warnings.append("START_ADJUSTED")
    if abs(end - original_end) > 0.001:
        warnings.append("END_ADJUSTED")
    following_words = [
        word
        for word in words
        if word["start"] >= content_end - 0.001 and word["end"] > content_end + 0.001
    ]
    next_word = following_words[0] if following_words else None
    next_word_overlap_s = (
        max(0.0, end - next_word["start"]) if next_word else 0.0
    )
    if next_word and next_word_overlap_s > hard_next_word_overlap_limit + 0.001:
        warnings.append("TAIL_OVERLAPS_FOLLOWING_SPEECH")
    elif next_word and next_word_overlap_s > 0.08:
        warnings.append("TAIL_OVERLAP_NOTICEABLE_RISK")
    completeness = completeness_for_range(words, content_start, content_end)
    if not completeness["last_sentence_complete"]:
        warnings.append("POSSIBLE_INCOMPLETE_ENDING")

    warnings = list(dict.fromkeys(warnings))
    text_edges = first_last_text_for_range(words, content_start, content_end)
    content_words = [
        word
        for word in words
        if word["start"] >= content_start - 0.001 and word["end"] <= content_end + 0.001
    ]
    last_word = content_words[-1] if content_words else None
    return {
        "short_id": short_item.get("id") or short_item.get("short_id"),
        "original_start_time": round(original_start, 3),
        "original_end_time": round(original_end, 3),
        "original_duration": round(original_end - original_start, 3),
        "refined_start_time": round(start, 3),
        "refined_end_time": round(end, 3),
        "refined_duration": round(end - start, 3),
        "content_start_time": round(content_start, 3),
        "content_end_time": round(content_end, 3),
        "content_duration": round(content_end - content_start, 3),
        "boundary_adjustment_s": {
            "start": round(start - original_start, 3),
            "end": round(end - original_end, 3),
        },
        "content_boundary_adjustment_s": {
            "start": round(content_start - original_start, 3),
            "end": round(content_end - original_end, 3),
        },
        "first_transcript_words": text_edges["first_words"],
        "last_transcript_words": text_edges["last_words"],
        "last_word": last_word["word"] if last_word else "",
        "last_word_end": round(last_word["end"], 3) if last_word else None,
        "next_word": next_word["word"] if next_word else "",
        "next_word_start": round(next_word["start"], 3) if next_word else None,
        "media_tail_after_content_end_s": round(end - content_end, 3),
        "next_word_overlap_s": round(next_word_overlap_s, 3),
        "word_count": text_edges["word_count"],
        "completeness": completeness,
        "reasons": reasons,
        "warnings": warnings,
        "scene_cuts": scene_cuts,
    }
