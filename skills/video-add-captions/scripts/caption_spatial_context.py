"""Build hash-bound caption placement metadata from approved B-roll composites."""

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path

import build_captions


EPSILON = 1e-6
PANEL_RECT = {"x": 0.04, "y": 0.08, "width": 0.92, "height": 0.40}
LAYOUTS = {"focused-panel", "full-bleed-wash", "corner-pip"}


class NoCompositeContext(ValueError):
    pass


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _words_signature(words):
    payload = [{
        "word": word.get("word"),
        "start": word.get("start"),
        "end": word.get("end"),
        "source_range": word.get("source_range"),
    } for word in words]
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _operation(project, operation_id):
    operations = project.get("operations", [])
    if isinstance(operations, dict):
        return operations.get(operation_id)
    return next((item for item in operations if item.get("id") == operation_id), None)


def _work_root(project_root):
    root = Path(project_root).resolve()
    return root / "work" if (root / "work" / "project.json").is_file() else root


def _resolve_work_path(work, value):
    path = Path(value)
    return path if path.is_absolute() else work / path


def _binding_path_hash(binding):
    if not isinstance(binding, dict):
        return None, None
    return binding.get("path"), binding.get("sha256")


def _speaker_rect(probe, style, anchor):
    if anchor not in {"top-left", "top-right", "upper-center", "lower-center"}:
        return None
    required = {"width_ratio", "aspect_ratio", "margin_ratio", "reserved_bottom_ratio"}
    if not isinstance(style, dict) or not required.issubset(style):
        return None
    frame_width = float(probe.get("width", 0))
    frame_height = float(probe.get("height", 0))
    if frame_width <= 0 or frame_height <= 0:
        return None
    inset_width = frame_width * float(style["width_ratio"])
    inset_height = inset_width / float(style["aspect_ratio"])
    margin = frame_width * float(style["margin_ratio"])
    safe_bottom = frame_height * (1 - float(style["reserved_bottom_ratio"]))
    if anchor != "lower-center" and inset_height > safe_bottom - margin:
        inset_height = safe_bottom - margin
        inset_width = inset_height * float(style["aspect_ratio"])
    if anchor in {"upper-center", "lower-center"}:
        x = (frame_width - inset_width) / 2
    elif anchor == "top-left":
        x = margin
    else:
        x = frame_width - margin - inset_width
    if anchor in {"top-left", "top-right"}:
        y = margin
    elif anchor == "upper-center":
        y = max(margin, (safe_bottom - inset_height) / 4)
    else:
        y = safe_bottom - inset_height
    return {
        "x": round(x / frame_width, 9),
        "y": round(y / frame_height, 9),
        "width": round(inset_width / frame_width, 9),
        "height": round(inset_height / frame_height, 9),
    }


def _source_state(project_root, *, verify_files=True):
    work = _work_root(project_root)
    project_path = work / "project.json"
    if not project_path.is_file():
        raise NoCompositeContext("no composite-aware context required: project.json is missing")
    project = _read_json(project_path)
    operation = _operation(project, "b-roll")
    active = project.get("sequences", {}).get("main", {}).get("operations", [])
    if not operation or "b-roll" not in active:
        raise NoCompositeContext("no composite-aware context required: b-roll is not active")
    if operation.get("status") not in {"approved", "verified"}:
        raise NoCompositeContext("no composite-aware context required: b-roll is not approved")

    plan_binding = operation.get("plan")
    plan_rel = plan_binding.get("path") if isinstance(plan_binding, dict) else plan_binding
    if not isinstance(plan_rel, str) or not plan_rel:
        raise ValueError("active b-roll operation has no plan path")
    plan_path = _resolve_work_path(work, plan_rel)
    if not plan_path.is_file():
        raise ValueError(f"b-roll plan is missing: {plan_path}")
    plan_sha = _sha256(plan_path)
    if isinstance(plan_binding, dict) and plan_binding.get("sha256") not in {None, plan_sha}:
        raise ValueError("b-roll plan SHA-256 does not match project binding")
    broll = _read_json(plan_path)
    if broll.get("review", {}).get("status") != "approved":
        raise ValueError("b-roll plan review.status must be approved")

    bindings = broll.get("speaker_inset") or broll.get("speaker_inset_bindings")
    if not isinstance(bindings, dict):
        raise NoCompositeContext("no composite-aware context required: speaker inset bindings are absent")
    aliases = {
        "analysis": "analysis",
        "agent_input": "agent_input",
        "preview": "preview",
        "clearance": "clearance",
    }
    artifact_state = {}
    for output_name, binding_name in aliases.items():
        binding = bindings.get(binding_name)
        if binding is None and binding_name == "agent_input":
            binding = bindings.get("agent-input")
        rel, expected = _binding_path_hash(binding)
        if not rel or not expected:
            raise ValueError(f"speaker inset {output_name} binding is incomplete")
        path = _resolve_work_path(work, rel)
        if verify_files and (not path.is_file() or _sha256(path) != expected):
            raise ValueError(f"speaker inset {output_name} file/hash is stale")
        artifact_state[output_name] = {"path": rel, "sha256": expected, "absolute_path": path}

    agent_input = _read_json(artifact_state["agent_input"]["absolute_path"])
    agent_shots = {
        item.get("shot_id"): item
        for item in agent_input.get("shots", []) if isinstance(item, dict)
    }
    style = broll.get("speaker_inset_style", {})
    shots = []
    for shot in broll.get("shots", []):
        if shot.get("status") not in {"normalized", "verified"}:
            continue
        normalized = shot.get("normalized") or shot.get("normalized_composite")
        if not isinstance(normalized, dict):
            continue
        composition = normalized.get("composition", {})
        shot_style = shot.get("speaker_inset_style", {})
        layout = composition.get("layout_preset") or shot_style.get("layout")
        if layout not in LAYOUTS:
            continue
        rel = normalized.get("path")
        expected = normalized.get("sha256")
        path = _resolve_work_path(work, rel) if rel else None
        if not rel or not expected:
            raise ValueError(f"B-roll shot {shot.get('id')} normalized composite binding is incomplete")
        if verify_files and (not path.is_file() or _sha256(path) != expected):
            raise ValueError(f"B-roll shot {shot.get('id')} normalized composite file/hash is stale")
        program_range = shot.get("program_range", {})
        start = float(program_range.get("start_s"))
        end = float(program_range.get("end_s"))
        if end <= start:
            raise ValueError(f"B-roll shot {shot.get('id')} has an invalid program range")
        agent_shot = agent_shots.get(shot.get("id"), {})
        enabled_subshots = [
            item for item in agent_shot.get("subshots", [])
            if isinstance(item, dict) and item.get("display_mode") == "enabled"
        ]
        speaker_anchors = {
            item.get("anchor") for item in enabled_subshots
            if isinstance(item.get("anchor"), str) and item.get("anchor")
        }
        if len(speaker_anchors) > 1:
            raise ValueError(f"B-roll shot {shot.get('id')} changes speaker anchor within the shot")
        anchor_name = next(iter(speaker_anchors), None)
        allowed_rect = copy.deepcopy(shot_style.get("broll_rect") or PANEL_RECT) if layout == "focused-panel" else None
        anchor = None
        if allowed_rect:
            anchor = {
                "x": round(float(allowed_rect["x"]) + float(allowed_rect["width"]) / 2, 9),
                "y": round(float(allowed_rect["y"]) + float(allowed_rect["height"]) / 2, 9),
            }
        probe = normalized.get("probe", {})
        shots.append({
            "id": shot.get("id"),
            "start": start,
            "end": end,
            "layout": layout,
            "speaker_anchor": anchor_name,
            "anchor": anchor,
            "allowed_rect": allowed_rect,
            "speaker_rect": _speaker_rect(probe, style or shot_style, anchor_name),
            "background": {
                "kind": "normalized-broll-composite",
                "path": rel,
                "sha256": expected,
                "program_start_s": start,
            },
            "probe": probe,
        })
    shots.sort(key=lambda item: (item["start"], item["end"]))
    if not shots:
        raise NoCompositeContext("no composite-aware context required: no normalized speaker-inset shots")
    for left, right in zip(shots, shots[1:]):
        if right["start"] < left["end"] - EPSILON:
            raise ValueError("speaker-inset B-roll shots overlap")
    return {
        "work": work,
        "project": project,
        "operation": operation,
        "broll": broll,
        "plan_path": plan_path,
        "plan_rel": plan_rel,
        "plan_sha256": plan_sha,
        "artifacts": artifact_state,
        "shots": shots,
    }


def _inside(value, start, end):
    return start + EPSILON < value < end - EPSILON


def _rebuild_cue(original, words, cue_id, original_id):
    cue = copy.deepcopy(original)
    cue["id"] = cue_id
    cue["original_cue_id"] = original_id
    cue["words"] = copy.deepcopy(words)
    cue["start"] = round(float(words[0]["start"]), 9)
    cue["end"] = round(float(words[-1]["end"]), 9)
    cue["program_range"] = {"start_s": cue["start"], "end_s": cue["end"]}
    cue["text"] = build_captions.join_tokens([word["word"] for word in words])
    max_chars = max(1, max((len(line) for line in original.get("lines", [])), default=len(cue["text"])))
    cue["lines"] = build_captions.wrap_tokens([word["word"] for word in words], max_chars)
    source_words = [word for word in words if isinstance(word.get("source_range"), dict)]
    cue["source_ranges"] = ([{
        "start_s": source_words[0]["source_range"]["start_s"],
        "end_s": source_words[-1]["source_range"]["end_s"],
    }] if source_words else [])
    cue.pop("hero_line", None)
    return cue


def _alignment_for_cue(cue, boundaries):
    words = cue.get("words", [])
    if not words:
        raise ValueError(f"cue {cue.get('id') or cue.get('index')} has no words")
    split_points = {}
    markers = []
    for boundary in boundaries:
        if not _inside(boundary, float(cue["start"]), float(cue["end"])):
            continue
        containing = next((i for i, word in enumerate(words)
                           if float(word["start"]) < boundary < float(word["end"])), None)
        if containing is None:
            gaps = [
                i
                for i in range(1, len(words))
                if float(words[i - 1]["end"]) <= boundary <= float(words[i]["start"])
            ]
            if gaps:
                split_points[gaps[0]] = {"boundary_s": boundary, "policy": "containing-word-gap"}
                continue
            word_index, midpoint = min(
                ((i, (float(word["start"]) + float(word["end"])) / 2)
                 for i, word in enumerate(words)),
                key=lambda item: abs(item[1] - boundary),
            )
            markers.append({"boundary_s": boundary, "word_index": word_index + 1,
                            "word_midpoint_s": midpoint,
                            "midpoint_side": "before" if midpoint < boundary else "after",
                            "requires_review": True})
            continue
        word = words[containing]
        midpoint = (float(word["start"]) + float(word["end"])) / 2
        split_after = containing if midpoint >= boundary else containing + 1
        marker = {
            "boundary_s": boundary,
            "word_index": containing + 1,
            "word_midpoint_s": midpoint,
            "midpoint_side": "before" if midpoint < boundary else "after",
            "requires_review": True,
        }
        if split_after in {0, len(words)}:
            markers.append(marker)
        else:
            split_points[split_after] = {
                "boundary_s": boundary,
                "policy": "word-midpoint",
                "marker": marker,
            }
    return split_points, markers


def align_plan_to_context_boundaries(project_root: Path, caption_plan: dict) -> tuple[dict, list[dict]]:
    state = _source_state(project_root)
    plan = copy.deepcopy(caption_plan)
    presentation = plan.get("presentation")
    if presentation is not None:
        if presentation.get("mode") != "expressive" or presentation.get("planning_status") != "draft":
            raise ValueError("cue alignment requires a draft Expressive plan before layout planning")
        if presentation.get("layout_beats"):
            raise ValueError("cue alignment must run before Expressive layout beats")
    if any(cue.get("hero_line") or cue.get("hero_lines") for cue in plan.get("cues", [])):
        raise ValueError("cue alignment must run before hero_line planning")
    if any(key in plan for key in ("interaction", "interaction_receipt", "approval", "spatial_context")):
        raise ValueError("cue alignment cannot rewrite a plan after interaction or approval")

    boundaries = sorted({shot[key] for shot in state["shots"] for key in ("start", "end")})
    aligned = []
    records = []
    for position, original in enumerate(plan.get("cues", []), 1):
        original_id = original.get("id") or f"cue-{position:03d}"
        original_words_sha256 = _words_signature(original["words"])
        split_points, markers = _alignment_for_cue(original, boundaries)
        cuts = [0, *sorted(split_points), len(original["words"])]
        if len(cuts) == 2:
            cue = _rebuild_cue(original, original["words"], original_id, original_id)
            if markers:
                cue["unsplittable_word_boundary"] = markers[0]
                record = {
                    "original_cue_id": original_id,
                    "derived_cue_ids": [original_id],
                    "boundary_s": markers[0]["boundary_s"],
                    "split_after_word_index": None,
                    "policy": "unsplittable-word-boundary",
                    "original_words_sha256": original_words_sha256,
                    "derived_words_sha256": original_words_sha256,
                }
                records.append(record)
                cue["cue_alignment"] = [copy.deepcopy(record)]
            aligned.append(cue)
            continue
        derived = []
        suffixes = "abcdefghijklmnopqrstuvwxyz"
        for part, (start, end) in enumerate(zip(cuts, cuts[1:])):
            if part >= len(suffixes):
                raise ValueError(f"cue {original_id} crosses too many visual boundaries")
            cue = _rebuild_cue(original, original["words"][start:end], original_id + suffixes[part], original_id)
            for split_after, detail in split_points.items():
                marker = detail.get("marker")
                if marker and start <= marker["word_index"] - 1 < end:
                    cue["unsplittable_word_boundary"] = marker
            derived.append(cue)
        aligned.extend(derived)
        for split_after, detail in sorted(split_points.items()):
            records.append({
                "original_cue_id": original_id,
                "derived_cue_ids": [cue["id"] for cue in derived],
                "boundary_s": detail["boundary_s"],
                "split_after_word_index": split_after,
                "policy": detail["policy"],
                "original_words_sha256": original_words_sha256,
                "derived_words_sha256": _words_signature([
                    word for cue in derived for word in cue["words"]
                ]),
            })

        cue_records = [record for record in records if record["original_cue_id"] == original_id]
        for cue in derived:
            cue["cue_alignment"] = copy.deepcopy(cue_records)

    for index, cue in enumerate(aligned, 1):
        cue["index"] = index
    plan["cues"] = aligned
    return plan, records


def _requested_variants(plan):
    presentation = plan.get("presentation")
    if not presentation or presentation.get("mode") == "standard":
        return {cue["id"]: "standard" for cue in plan["cues"]}
    variants = {}
    for beat in presentation.get("layout_beats", []):
        for cue_id in beat.get("cue_ids", []):
            variants[cue_id] = beat.get("variant")
    missing = [cue["id"] for cue in plan["cues"] if cue["id"] not in variants]
    if missing:
        raise ValueError("Expressive layout beats do not cover aligned cues: " + ", ".join(missing))
    return variants


def _shot_for_cue(cue, shots):
    marker = cue.get("unsplittable_word_boundary")
    if marker:
        time_s = float(marker["word_midpoint_s"])
        return next((shot for shot in shots if shot["start"] <= time_s < shot["end"]), None)
    overlaps = [shot for shot in shots
                if max(float(cue["start"]), shot["start"]) < min(float(cue["end"]), shot["end"]) - EPSILON]
    if len(overlaps) > 1:
        raise ValueError(f"aligned cue {cue['id']} still crosses multiple visual contexts")
    if overlaps:
        shot = overlaps[0]
        if float(cue["start"]) < shot["start"] - EPSILON or float(cue["end"]) > shot["end"] + EPSILON:
            raise ValueError(f"aligned cue {cue['id']} still crosses a visual boundary")
        return shot
    return None


def _intersected_visual_contexts(cue, shots):
    start = float(cue["start"])
    end = float(cue["end"])
    cuts = {start, end}
    for shot in shots:
        if start < shot["start"] < end:
            cuts.add(shot["start"])
        if start < shot["end"] < end:
            cuts.add(shot["end"])
    ordered = sorted(cuts)
    contexts = []
    for segment_start, segment_end in zip(ordered, ordered[1:]):
        if segment_end <= segment_start + EPSILON:
            continue
        midpoint = (segment_start + segment_end) / 2
        shot = next((item for item in shots if item["start"] <= midpoint < item["end"]), None)
        context = {
            "visual_context": shot["layout"] if shot else "a-roll",
            "program_range": {
                "start_s": round(segment_start, 9),
                "end_s": round(segment_end, 9),
            },
        }
        if shot:
            context["source_shot_id"] = shot["id"]
            context["background"] = copy.deepcopy(shot["background"])
            if shot.get("speaker_anchor"):
                context["speaker_anchor"] = shot["speaker_anchor"]
            if shot.get("speaker_rect"):
                context["speaker_rect"] = copy.deepcopy(shot["speaker_rect"])
            if shot.get("allowed_rect"):
                context["allowed_rect"] = copy.deepcopy(shot["allowed_rect"])
        contexts.append(context)
    return contexts


def _panel_bottom_geometry(cue, shots):
    marker = cue.get("unsplittable_word_boundary")
    if not marker:
        return None
    boundary = float(marker["boundary_s"])
    focused = next((shot for shot in shots
                    if shot["layout"] == "focused-panel"
                    and shot.get("speaker_anchor") == "lower-center"
                    and shot.get("speaker_rect")
                    and (abs(boundary - shot["start"]) <= EPSILON
                         or abs(boundary - shot["end"]) <= EPSILON)
                    and max(float(cue["start"]), shot["start"])
                    < min(float(cue["end"]), shot["end"]) - EPSILON), None)
    if not focused:
        return None
    speaker = focused["speaker_rect"]
    safe_margin = float(PANEL_RECT["x"])
    top = round(float(speaker["y"]) + float(speaker["height"]), 9)
    bottom = round(1 - safe_margin, 9)
    if bottom <= top + EPSILON:
        raise ValueError(f"focused-panel leaves no reserved bottom band for cue {cue['id']}")
    allowed_rect = {
        "x": safe_margin,
        "y": top,
        "width": round(1 - 2 * safe_margin, 9),
        "height": round(bottom - top, 9),
    }
    return {
        "allowed_rect": allowed_rect,
        "anchor": {
            "x": round(allowed_rect["x"] + allowed_rect["width"] / 2, 9),
            "y": round(allowed_rect["y"] + allowed_rect["height"] / 2, 9),
        },
    }


def _cue_alignment_from_plan(plan):
    records = {}
    for cue in plan.get("cues", []):
        for record in cue.get("cue_alignment", []):
            key = (record.get("original_cue_id"), record.get("boundary_s"))
            records[key] = copy.deepcopy(record)
    return list(records.values())


def build_context(project_root: Path, caption_plan: dict, *, cue_alignment=None) -> dict:
    state = _source_state(project_root)
    variants = _requested_variants(caption_plan)
    visual_intervals = []
    for index, shot in enumerate(state["shots"], 1):
        interval = {
            "id": f"visual-{index:03d}",
            "source_shot_id": shot["id"],
            "program_range": {"start_s": shot["start"], "end_s": shot["end"]},
            "visual_context": shot["layout"],
            "background": copy.deepcopy(shot["background"]),
        }
        if shot.get("speaker_anchor"):
            interval["speaker_anchor"] = shot["speaker_anchor"]
        if shot.get("speaker_rect"):
            interval["speaker_rect"] = copy.deepcopy(shot["speaker_rect"])
        if shot.get("allowed_rect"):
            interval["allowed_rect"] = copy.deepcopy(shot["allowed_rect"])
        visual_intervals.append(interval)
    beats = []
    for cue in caption_plan.get("cues", []):
        shot = _shot_for_cue(cue, state["shots"])
        intersected_contexts = (
            _intersected_visual_contexts(cue, state["shots"])
            if cue.get("unsplittable_word_boundary") else []
        )
        panel_bottom = _panel_bottom_geometry(cue, state["shots"])
        visual = shot["layout"] if shot else "a-roll"
        requested = variants[cue["id"]]
        if panel_bottom:
            placement = "panel-bottom"
        elif visual == "focused-panel":
            placement = "panel-center"
        elif caption_plan.get("presentation", {}).get("mode") == "expressive" and requested == "center-emphasis":
            placement = "frame-center"
        else:
            placement = "preset-bottom"
        item = {
            "id": f"spatial-{len(beats) + 1:03d}",
            "cue_ids": [cue["id"]],
            "cue_indexes": [cue["index"]],
            "program_range": {"start_s": cue["start"], "end_s": cue["end"]},
            "visual_context": visual,
            "requested_variant": requested,
            "resolved_placement": placement,
            "rationale": (
                "A focused-panel boundary inside a word resolves to the reserved panel-bottom band."
                if placement == "panel-bottom" else
                "focused-panel deterministically resolves to panel-center."
                if visual == "focused-panel" else
                "Expressive center-emphasis resolves to frame-center."
                if placement == "frame-center" else
                "The maintained preset bottom position remains active."
            ),
        }
        if shot:
            item["background"] = copy.deepcopy(shot["background"])
            if shot.get("speaker_anchor"):
                item["speaker_anchor"] = shot["speaker_anchor"]
            if shot.get("speaker_rect"):
                item["speaker_rect"] = copy.deepcopy(shot["speaker_rect"])
        if intersected_contexts:
            item["intersected_visual_contexts"] = intersected_contexts
        if placement in {"panel-center", "panel-bottom"}:
            geometry = panel_bottom or shot
            item["anchor"] = copy.deepcopy(geometry["anchor"])
            item["allowed_rect"] = copy.deepcopy(geometry["allowed_rect"])
        identity = (
            visual, requested, placement,
            item.get("background", {}).get("sha256"),
            json.dumps(item.get("allowed_rect"), sort_keys=True),
            json.dumps(item.get("intersected_visual_contexts"), sort_keys=True),
        )
        if beats:
            previous = beats[-1]
            previous_identity = previous.pop("_identity")
            previous["_identity"] = previous_identity
            if (identity == previous_identity
                    and abs(float(previous["program_range"]["end_s"]) - float(cue["start"])) <= EPSILON):
                previous["cue_ids"].append(cue["id"])
                previous["cue_indexes"].append(cue["index"])
                previous["program_range"]["end_s"] = cue["end"]
                continue
        item["_identity"] = identity
        beats.append(item)
    for index, beat in enumerate(beats, 1):
        beat.pop("_identity", None)
        beat["id"] = f"spatial-{index:03d}"

    artifacts = state["artifacts"]
    return {
        "schema_version": 1,
        "timeline_id": caption_plan.get("timeline_id"),
        "policy": "composite-aware",
        "source": {
            "operation_id": "b-roll",
            "operation_revision": state["operation"].get("revision"),
            "operation_status": state["operation"].get("status"),
            "check_status": state["operation"].get("check", {}).get("status"),
            "plan_path": state["plan_rel"],
            "plan_sha256": state["plan_sha256"],
            "analysis_sha256": artifacts["analysis"]["sha256"],
            "agent_input_sha256": artifacts["agent_input"]["sha256"],
            "preview_sha256": artifacts["preview"]["sha256"],
            "clearance_sha256": artifacts["clearance"]["sha256"],
        },
        "cue_alignment": copy.deepcopy(cue_alignment if cue_alignment is not None else _cue_alignment_from_plan(caption_plan)),
        "visual_intervals": visual_intervals,
        "placement_beats": beats,
    }


def validate_context(context: dict, caption_plan: dict, project_root: Path,
                     *, verify_files: bool = True) -> list[str]:
    errors = []
    try:
        state = _source_state(project_root, verify_files=verify_files)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        return [str(error)]
    if context.get("schema_version") != 1 or context.get("policy") != "composite-aware":
        errors.append("caption spatial context schema/policy is invalid")
    if context.get("timeline_id") != caption_plan.get("timeline_id"):
        errors.append("caption spatial context timeline is stale")
    source = context.get("source", {})
    expected_source = {
        "operation_status": state["operation"].get("status"),
        "check_status": state["operation"].get("check", {}).get("status"),
        "operation_revision": state["operation"].get("revision"),
        "plan_path": state["plan_rel"],
        "plan_sha256": state["plan_sha256"],
        "analysis_sha256": state["artifacts"]["analysis"]["sha256"],
        "agent_input_sha256": state["artifacts"]["agent_input"]["sha256"],
        "preview_sha256": state["artifacts"]["preview"]["sha256"],
        "clearance_sha256": state["artifacts"]["clearance"]["sha256"],
    }
    for field, expected in expected_source.items():
        if source.get(field) != expected:
            label = "b-roll plan" if field == "plan_sha256" else field.replace("_", " ")
            errors.append(f"caption spatial context {label} binding is stale")

    cues = caption_plan.get("cues", [])
    cue_by_id = {cue.get("id"): cue for cue in cues}
    cue_order = {cue.get("id"): position for position, cue in enumerate(cues)}
    alignment = context.get("cue_alignment")
    if not isinstance(alignment, list):
        errors.append("caption spatial cue_alignment must be an array")
        alignment = []
    seen_alignment = set()
    covered_derived = set()
    for record in alignment:
        if not isinstance(record, dict):
            errors.append("caption spatial cue_alignment record is invalid")
            continue
        original_id = record.get("original_cue_id")
        boundary = record.get("boundary_s")
        key = (original_id, boundary)
        if key in seen_alignment:
            errors.append("caption spatial cue_alignment has duplicate boundary records")
            continue
        seen_alignment.add(key)
        derived_ids = record.get("derived_cue_ids")
        if not isinstance(derived_ids, list) or not derived_ids or len(derived_ids) != len(set(derived_ids)):
            errors.append("caption spatial cue_alignment derived cue ids are invalid")
            continue
        if any(cue_id not in cue_by_id for cue_id in derived_ids):
            errors.append("caption spatial cue_alignment references an unknown derived cue")
            continue
        if derived_ids != sorted(derived_ids, key=cue_order.get):
            errors.append("caption spatial cue_alignment derived cues are out of order")
        derived_cues = [cue_by_id[cue_id] for cue_id in derived_ids]
        if any(cue.get("original_cue_id") != original_id for cue in derived_cues):
            errors.append("caption spatial cue_alignment original cue provenance is stale")
        signature = _words_signature([word for cue in derived_cues for word in cue.get("words", [])])
        if (record.get("original_words_sha256") != signature
                or record.get("derived_words_sha256") != signature):
            errors.append("caption spatial cue_alignment word preservation signature is stale")
        covered_derived.update(
            cue_id for cue_id in derived_ids
            if cue_by_id[cue_id].get("original_cue_id") != cue_id
        )
    expected_derived = {
        cue.get("id") for cue in cues
        if cue.get("original_cue_id") and cue.get("original_cue_id") != cue.get("id")
    }
    if covered_derived != expected_derived:
        errors.append("caption spatial cue_alignment does not cover every derived cue")
    flattened = []
    previous_end = None
    for beat in context.get("placement_beats", []):
        cue_ids = beat.get("cue_ids", [])
        flattened.extend(cue_ids)
        if not cue_ids or any(cue_id not in cue_by_id for cue_id in cue_ids):
            errors.append("caption spatial placement beat references an unknown cue")
            continue
        start = cue_by_id[cue_ids[0]]["start"]
        end = cue_by_id[cue_ids[-1]]["end"]
        if beat.get("program_range") != {"start_s": start, "end_s": end}:
            errors.append("caption spatial placement coverage is stale")
        if previous_end is not None and start < previous_end - EPSILON:
            errors.append("caption spatial placement beats overlap or are out of order")
        previous_end = end
        if beat.get("resolved_placement") in {"panel-center", "panel-bottom"}:
            placement = beat["resolved_placement"]
            rect = beat.get("allowed_rect", {})
            anchor = beat.get("anchor", {})
            try:
                expected_anchor = {
                    "x": round(float(rect["x"]) + float(rect["width"]) / 2, 9),
                    "y": round(float(rect["y"]) + float(rect["height"]) / 2, 9),
                }
            except (KeyError, TypeError, ValueError):
                errors.append(f"{placement} allowed rect is invalid")
            else:
                if anchor != expected_anchor:
                    errors.append(f"{placement} anchor does not match allowed rect center")
        background = beat.get("background")
        if background and verify_files:
            path = _resolve_work_path(state["work"], background.get("path", ""))
            if not path.is_file() or _sha256(path) != background.get("sha256"):
                errors.append("caption spatial normalized composite binding is stale")
    expected_ids = [cue.get("id") for cue in cues]
    if flattened != expected_ids:
        errors.append("caption spatial placement beats must cover every cue exactly once in order")
    if len(expected_ids) != len(set(expected_ids)):
        errors.append("caption plan has duplicate cue ids")
    try:
        expected_context = build_context(
            project_root, caption_plan, cue_alignment=context.get("cue_alignment", []),
        )
    except (ValueError, OSError, json.JSONDecodeError) as error:
        errors.append(f"caption spatial placement could not be recomputed: {error}")
    else:
        if context.get("visual_intervals") != expected_context.get("visual_intervals"):
            errors.append("caption spatial visual intervals differ from frozen B-roll composites")
        if context.get("placement_beats") != expected_context.get("placement_beats"):
            errors.append("caption spatial placement beats differ from deterministic resolution")
    return errors


def attach_context(plan_path: Path, context_path: Path, project_root: Path) -> dict:
    plan_path = Path(plan_path)
    context_path = Path(context_path)
    plan = _read_json(plan_path)
    context = _read_json(context_path)
    errors = validate_context(context, plan, project_root)
    if errors:
        raise ValueError("; ".join(errors))
    state = _source_state(project_root)
    try:
        relative = context_path.resolve().relative_to(state["work"].resolve()).as_posix()
    except ValueError:
        relative = str(context_path.resolve())
    plan["spatial_context"] = {
        "policy": "composite-aware",
        "path": relative,
        "sha256": _sha256(context_path),
        "source_operation": "b-roll",
        "source_revision": state["operation"].get("revision"),
    }
    _atomic_json(plan_path, plan)
    return plan


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("align", "build", "validate", "attach"):
        command = subparsers.add_parser(name)
        command.add_argument("--project-root", required=True)
        command.add_argument("--plan", required=True)
        if name == "align":
            command.add_argument("--out-plan", required=True)
        elif name in {"validate", "attach"}:
            command.add_argument("--context", required=True)
        else:
            command.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    plan = _read_json(args.plan)
    try:
        if args.command == "align":
            aligned, _ = align_plan_to_context_boundaries(Path(args.project_root), plan)
            _atomic_json(args.out_plan, aligned)
            print(f"[caption-spatial-context] aligned {len(aligned['cues'])} cues -> {args.out_plan}")
        elif args.command == "build":
            context = build_context(Path(args.project_root), plan)
            _atomic_json(args.out, context)
            print(f"[caption-spatial-context] built {len(context['placement_beats'])} placement beats -> {args.out}")
        elif args.command == "validate":
            context = _read_json(args.context)
            errors = validate_context(context, plan, Path(args.project_root))
            if errors:
                raise SystemExit("[caption-spatial-context] invalid: " + "; ".join(errors))
            print("[caption-spatial-context] validation passed")
        else:
            attach_context(Path(args.plan), Path(args.context), Path(args.project_root))
            print(f"[caption-spatial-context] attached {args.context} -> {args.plan}")
    except NoCompositeContext as error:
        print(f"[caption-spatial-context] {error}")


if __name__ == "__main__":
    main()
