"""Shared Open Recut project protocol helpers."""

import hashlib
import json
import math
import os
import re
import subprocess
from datetime import datetime
from graphlib import CycleError, TopologicalSorter
from pathlib import Path


STATUSES = {"draft", "approved", "verified", "failed", "stale"}
CONTRIBUTION_KINDS = {
    "timeline-transform",
    "video-filter",
    "audio-filter",
    "overlay",
    "precomputed-asset",
    "output-constraint",
}
POINT_WORD_DURATION_S = 0.001


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quick_fingerprint(path, duration_s):
    stat = Path(path).stat()
    return {
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "duration_s": round(float(duration_s), 6),
    }


def resolve_project_path(project_root, value):
    root = Path(project_root).resolve()
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / "work" / path).resolve()
    if os.path.commonpath((str(root), str(resolved))) != str(root):
        raise ValueError(f"project path escapes root: {value}")
    return resolved


def operation_map(project):
    return {operation.get("id"): operation for operation in project.get("operations", [])}


def _validate_node(node, nodes, errors, *, allow_render=False):
    node_id = node.get("id") or "<missing-id>"
    revision = node.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        errors.append(f"{node_id} revision must be a positive integer")
    if node.get("status") not in STATUSES:
        errors.append(f"{node_id} invalid status: {node.get('status')!r}")

    dependencies = node.get("depends_on", [])
    if not isinstance(dependencies, list):
        errors.append(f"{node_id} depends_on must be a list")
        dependencies = []
    valid_dependencies = []
    for dependency in dependencies:
        if not isinstance(dependency, str) or not dependency.strip():
            errors.append(f"{node_id} dependency id must be a nonblank string")
            continue
        valid_dependencies.append(dependency)
        if dependency not in nodes and not (allow_render and dependency == "render"):
            errors.append(f"{node_id} missing dependency: {dependency}")
    dependencies = valid_dependencies

    based_on = node.get("based_on", {})
    if not isinstance(based_on, dict):
        errors.append(f"{node_id} based_on must be an object")
        return
    expected_dependencies = set(dependencies)
    if allow_render:
        expected_dependencies.discard("render")
    recorded_dependencies = set(based_on)
    for dependency in sorted(expected_dependencies - recorded_dependencies):
        errors.append(f"{node_id} based_on missing revision for dependency: {dependency}")
    for dependency in sorted(recorded_dependencies - expected_dependencies):
        errors.append(f"{node_id} based_on has unexpected dependency: {dependency}")
    for dependency, expected_revision in based_on.items():
        current = nodes.get(dependency, {}).get("revision")
        if current is None:
            errors.append(f"{node_id} based_on missing dependency: {dependency}")
        elif expected_revision != current:
            errors.append(
                f"revision mismatch: {node_id} based_on {dependency}={expected_revision}, current={current}"
            )


def _validate_source(project, project_root, errors, check_media=False):
    source = project.get("source", {})
    value = source.get("path")
    fingerprint = source.get("fingerprint", {})
    if not value:
        errors.append("project source path is required")
        return
    try:
        path = resolve_project_path(project_root, value)
    except ValueError as exc:
        errors.append(str(exc))
        return
    if not path.is_file():
        errors.append(f"project source is missing: {value}")
        return
    stat = path.stat()
    for key, current in (("size", stat.st_size), ("modified_ns", stat.st_mtime_ns)):
        if fingerprint.get(key) != current:
            errors.append(
                f"source fingerprint {key} mismatch: expected {fingerprint.get(key)}, current {current}"
            )
    expected_duration = fingerprint.get("duration_s")
    if not isinstance(expected_duration, (int, float)) or isinstance(expected_duration, bool):
        errors.append("source fingerprint duration_s must be numeric")
    elif check_media:
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            current_duration = float(result.stdout.strip())
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            errors.append(f"source fingerprint duration probe failed: {exc}")
        else:
            if abs(float(expected_duration) - current_duration) > 0.05:
                errors.append(
                    "source fingerprint duration mismatch: "
                    f"expected {expected_duration}, current {current_duration:.6f}"
                )


def _validate_operation_outputs(operation, project_root, errors):
    operation_id = operation.get("id") or "<missing-id>"
    outputs = operation.get("outputs", [])
    if not isinstance(outputs, list):
        errors.append(f"{operation_id} outputs must be a list")
        return

    cache_root = (Path(project_root).resolve() / "work" / "cache").resolve()
    for value in outputs:
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{operation_id} output path must be a non-empty string")
            continue
        try:
            path = resolve_project_path(project_root, value)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if os.path.commonpath((str(cache_root), str(path))) == str(cache_root):
            continue
        if operation.get("status") == "verified" and not path.exists():
            errors.append(f"{operation_id} missing output: {value}")


def validate_project(project, project_root, check_files=True, check_media=False):
    errors = []
    if project.get("schema_version") != 1:
        errors.append("project schema_version must be 1")

    operations = project.get("operations", [])
    ids = [operation.get("id") for operation in operations]
    seen = set()
    for operation_id in ids:
        if not operation_id:
            errors.append("operation id is required")
        elif operation_id in seen:
            errors.append(f"duplicate operation id: {operation_id}")
        seen.add(operation_id)
    nodes = operation_map(project)

    effect_flags = (
        "changes_timeline",
        "changes_geometry",
        "changes_video_pixels",
        "changes_audio",
    )
    for operation in operations:
        _validate_node(operation, nodes, errors)
        operation_id = operation.get("id") or "<missing-id>"
        target = operation.get("target")
        if not isinstance(target, dict):
            errors.append(f"{operation_id} target must be an object")
        else:
            if not str(target.get("sequence", "")).strip():
                errors.append(f"{operation_id} target sequence is required")
            if not str(target.get("scope", "")).strip():
                errors.append(f"{operation_id} target scope is required")
        effects = operation.get("effects")
        if not isinstance(effects, dict):
            errors.append(f"{operation_id} effects must be an object")
        else:
            for flag in effect_flags:
                if not isinstance(effects.get(flag), bool):
                    errors.append(f"{operation_id} effects {flag} must be boolean")
            adds_track = effects.get("adds_track")
            if adds_track is not None and (
                not isinstance(adds_track, str) or not adds_track.strip()
            ):
                errors.append(f"{operation_id} effects adds_track must be null or non-empty")
        check = operation.get("check")
        if check is not None:
            if not isinstance(check, dict):
                errors.append(f"{operation_id} check must be an object")
            else:
                if check.get("status") not in ("pending", "pass", "fail"):
                    errors.append(
                        f"{operation_id} check status must be pending, pass, or fail"
                    )
                if not str(check.get("report", "")).strip():
                    errors.append(f"{operation_id} check report is required")

    graph = {
        operation_id: {
            dependency
            for dependency in operation.get("depends_on", [])
            if isinstance(dependency, str) and dependency in nodes
        }
        for operation_id, operation in nodes.items()
        if operation_id
    }
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        cycle = " -> ".join(str(item) for item in exc.args[1])
        errors.append(f"dependency cycle: {cycle}")

    active = project.get("active_sequence")
    sequences = project.get("sequences", {})
    for operation in operations:
        target = operation.get("target")
        if isinstance(target, dict) and target.get("sequence") not in sequences:
            errors.append(
                f"{operation.get('id') or '<missing-id>'} target sequence does not exist: "
                f"{target.get('sequence')!r}"
            )
    if active not in sequences:
        errors.append(f"active_sequence does not exist: {active!r}")
    else:
        for operation_id in sequences[active].get("operations", []):
            if operation_id not in nodes:
                errors.append(f"active sequence references unknown operation: {operation_id}")

    for review in project.get("reviews", []):
        _validate_node(review, nodes, errors, allow_render=True)

    if check_files:
        _validate_source(project, project_root, errors, check_media=check_media)
        for operation in operations:
            _validate_operation_outputs(operation, project_root, errors)
        for node in [*operations, *project.get("reviews", [])]:
            plan = node.get("plan")
            if plan:
                try:
                    path = resolve_project_path(project_root, plan)
                except ValueError as exc:
                    errors.append(str(exc))
                else:
                    if not path.is_file():
                        errors.append(f"{node.get('id')} missing file: {plan}")
            report = node.get("check", {}).get("report")
            if report:
                try:
                    report_path = resolve_project_path(project_root, report)
                except ValueError as exc:
                    errors.append(str(exc))
                else:
                    if not report_path.is_file():
                        errors.append(f"{node.get('id')} missing check report: {report}")

        if active in sequences:
            timeline_value = sequences[active].get("timeline")
            if not timeline_value:
                errors.append(f"active sequence {active} timeline is required")
            else:
                try:
                    timeline_path = resolve_project_path(project_root, timeline_value)
                except ValueError as exc:
                    errors.append(str(exc))
                else:
                    if not timeline_path.is_file():
                        errors.append(f"active sequence missing timeline: {timeline_value}")
                    else:
                        try:
                            timeline = load_json(timeline_path)
                        except (OSError, ValueError, json.JSONDecodeError) as exc:
                            errors.append(f"invalid timeline file: {exc}")
                        else:
                            decision_ids = None
                            cut = nodes.get("cut")
                            if cut and cut.get("plan"):
                                cut_path = resolve_project_path(project_root, cut["plan"])
                                if cut_path.is_file():
                                    cut_plan = load_json(cut_path)
                                    if "decisions" in cut_plan:
                                        decision_ids = {
                                            decision.get("id")
                                            for decision in cut_plan["decisions"]
                                            if decision.get("action") == "keep"
                                        }
                            errors.extend(validate_timeline(timeline, decision_ids=decision_ids))
                            expected_duration = project.get("source", {}).get("fingerprint", {}).get("duration_s")
                            if isinstance(expected_duration, (int, float)):
                                fps = timeline.get("fps", {})
                                tolerance = fps.get("den", 1) / fps.get("num", 1) if fps.get("num") else 0.05
                                if abs(float(timeline.get("source_duration_s", 0)) - float(expected_duration)) > tolerance:
                                    errors.append("timeline source duration does not match source fingerprint")

    return errors


def start_here_text(project, project_root):
    root = Path(project_root)
    sequence = project.get("sequences", {}).get(project.get("active_sequence"), {})
    operations = operation_map(project)
    active_ids = sequence.get("operations", [])
    final_value = project.get("render", {}).get("output", "../final/final-video.mp4")
    final_path = resolve_project_path(root, final_value)
    final_relative = Path(os.path.relpath(final_path, root)).as_posix()
    source_duration = project.get("source", {}).get("fingerprint", {}).get("duration_s")
    program_duration = None
    timeline_value = sequence.get("timeline")
    if timeline_value:
        timeline_path = resolve_project_path(root, timeline_value)
        if timeline_path.is_file():
            program_duration = load_json(timeline_path).get("program_duration_s")

    pending = [
        operation_id.replace("-", " ").title()
        for operation_id, operation in operations.items()
        if operation.get("status") == "draft"
    ]
    if not final_path.is_file():
        pending.append("Final delivery render")

    lines = [
        f"# {project.get('project_id', 'Open Recut Project')}",
        "",
        "## Current status",
        "",
        "Final video is ready." if final_path.is_file() else "Editing is in progress.",
        "",
        "## Pending choices",
        "",
        *([f"- {item}" for item in pending] or ["- None"]),
        "",
        "## Review decisions",
        "",
        "- Understanding: `review/00-video-understanding/video-summary.md`",
    ]
    for operation_id in active_ids:
        operation = operations[operation_id]
        report = operation.get("check", {}).get("report")
        report_text = f" - `{report[3:] if report and report.startswith('../') else report}`" if report else ""
        lines.append(
            f"- {operation_id.replace('-', ' ').title()}: revision {operation['revision']}, "
            f"status {operation['status']}{report_text}"
        )
    for review in project.get("reviews", []):
        output = review.get("output")
        output_text = (
            f" - `{output[3:] if output and output.startswith('../') else output}`"
            if output else ""
        )
        lines.append(
            f"- {review.get('id', 'review')}: revision {review.get('revision', 1)}, "
            f"status {review.get('status', 'draft')}{output_text}"
        )
    lines += [
        "",
        "## Final delivery",
        "",
        f"- Video: `{final_relative}`",
        f"- Source duration: {source_duration if source_duration is not None else 'unknown'} seconds",
        f"- Program duration: {program_duration if program_duration is not None else 'unknown'} seconds",
        f"- Verification: {project.get('render', {}).get('status', 'draft')}",
        "",
        "## Known caveats",
        "",
        *([f"- {item}" for item in project.get("caveats", [])] or ["- None recorded"]),
        "",
    ]
    return "\n".join(lines)


def write_start_here(project, project_root):
    path = Path(project_root) / "START-HERE.md"
    path.write_text(start_here_text(project, project_root), encoding="utf-8")
    return path


def validate_understanding(understanding, transcript):
    """Validate semantic evidence against the canonical transcript."""
    errors = []
    if understanding.get("schema_version") != 1:
        errors.append("understanding schema_version must be 1")

    segments = transcript.get("segments", [])
    evidence_ids = {f"segment:{segment.get('id')}" for segment in segments}
    try:
        duration = float(
            transcript.get("duration", max((segment.get("end", 0) for segment in segments), default=0))
        )
    except (TypeError, ValueError):
        duration = 0.0
        errors.append("transcript duration must be numeric")

    seen_ids = set()
    for collection in ("chapters", "entities", "moments", "transcript_corrections", "uncertainties"):
        items = understanding.get(collection, [])
        if not isinstance(items, list):
            errors.append(f"{collection} must be a list")
            continue
        for index, item in enumerate(items, 1):
            label = f"{collection}[{index}]"
            item_id = item.get("id")
            if not item_id:
                errors.append(f"{label} id is required")
            elif item_id in seen_ids:
                errors.append(f"duplicate semantic id: {item_id}")
            else:
                seen_ids.add(item_id)

            confidence = item.get("confidence")
            if confidence is not None and (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= confidence <= 1
            ):
                errors.append(f"{item_id or label} confidence must be between 0 and 1")

            has_start = "start_s" in item
            has_end = "end_s" in item
            if has_start != has_end:
                errors.append(f"{item_id or label} range requires start_s and end_s")
            elif has_start:
                try:
                    start, end = float(item["start_s"]), float(item["end_s"])
                except (TypeError, ValueError):
                    errors.append(f"{item_id or label} range must be numeric")
                else:
                    if start < 0 or end <= start or end > duration:
                        errors.append(f"{item_id or label} range is outside transcript duration")

            refs = item.get("evidence_refs", [])
            if not isinstance(refs, list):
                errors.append(f"{item_id or label} evidence_refs must be a list")
            else:
                for ref in refs:
                    if ref not in evidence_ids:
                        errors.append(f"{item_id or label} unresolved evidence: {ref}")

    return errors


def _relative_to_render(project_root, render_dir, value):
    resolved = resolve_project_path(project_root, value)
    return Path(os.path.relpath(resolved, render_dir)).as_posix(), resolved


def _validate_grade_choice(plan, contribution, operation_id, errors):
    target = plan.get("target", contribution.get("target"))
    if target not in ("base-video", "composite"):
        errors.append(f"{operation_id} grade target must be base-video or composite")
    if contribution.get("target") and contribution["target"] != target:
        errors.append(f"{operation_id} grade target does not match contribution")
    looks = plan.get("looks", [])
    names = {look.get("name") for look in looks if look.get("name")}
    selected = plan.get("selected_look") or contribution.get("selected_look")
    if not selected:
        errors.append(f"{operation_id} selected_look is required for delivery")
    elif selected not in names:
        errors.append(f"{operation_id} selected look not found: {selected}")
    if plan.get("selection_mode") not in ("human", "agent"):
        errors.append(f"{operation_id} selection_mode must be human or agent")
    if not str(plan.get("selection_rationale", "")).strip():
        errors.append(f"{operation_id} selection_rationale is required")


def _validate_cards_choices(plan, operation_id, errors, project_root=None, expected_fps=None):
    if plan.get("schema_version") != 1 or plan.get("target") != "overlay":
        errors.append(f"{operation_id} cards plan must be schema V1 with overlay target")
        return
    for index, card in enumerate(plan.get("cards", []), 1):
        card_id = card.get("id") or f"card-{index}"
        for field in ("copy", "placement", "visual_treatment"):
            value = card.get(field, {})
            if value.get("status") not in ("approved", "verified"):
                errors.append(f"{card_id} {field} is not approved for delivery")
        copy = card.get("copy", {})
        display = copy.get("display", {})
        if not isinstance(display, dict) or not str(display.get("title", "")).strip():
            errors.append(f"{card_id} approved copy.display.title is required")
        placement = card.get("placement", {})
        if placement.get("face_clearance") != "verified":
            errors.append(f"{card_id} face_clearance is not verified")
        if not placement.get("review_still"):
            errors.append(f"{card_id} composited review_still is required")
        elif project_root is not None:
            try:
                review_still = resolve_project_path(project_root, placement["review_still"])
            except ValueError as exc:
                errors.append(str(exc))
            else:
                if not review_still.is_file():
                    errors.append(f"{card_id} composited review_still is missing")
        renderer = card.get("renderer", {})
        if not renderer.get("composition") or not renderer.get("asset"):
            errors.append(f"{card_id} renderer composition and asset are required")
        fps = renderer.get("fps", {})
        if (
            not isinstance(fps, dict)
            or not isinstance(fps.get("num"), int)
            or isinstance(fps.get("num"), bool)
            or not isinstance(fps.get("den"), int)
            or isinstance(fps.get("den"), bool)
            or fps.get("num", 0) <= 0
            or fps.get("den", 0) <= 0
        ):
            errors.append(f"{card_id} renderer fps num and den must be positive integers")
        elif expected_fps and fps != expected_fps:
            errors.append(f"{card_id} renderer fps does not match timeline fps")


def _validate_caption_plan(plan, contribution, operation_id, errors, project_root, timeline):
    if (
        plan.get("schema_version") != 1
        or plan.get("target") != "overlay"
        or plan.get("timebase") != "program"
    ):
        errors.append(f"{operation_id} caption plan must be schema V1 program-time overlay")
        return
    if plan.get("timeline_id") != timeline.get("timeline_id"):
        errors.append(f"{operation_id} caption plan timeline_id does not match timeline")
    if not str(plan.get("source_transcript", "")).strip():
        errors.append(f"{operation_id} caption plan source_transcript is required")
    tolerance = timeline["fps"]["den"] / timeline["fps"]["num"]
    try:
        duration = float(plan["program_duration_s"])
    except (KeyError, TypeError, ValueError):
        errors.append(f"{operation_id} caption plan program_duration_s is required")
        duration = 0.0
    if not math.isfinite(duration) or duration <= 0:
        errors.append(f"{operation_id} caption plan duration must be positive and finite")
    elif abs(duration - float(timeline["program_duration_s"])) > tolerance:
        errors.append(f"{operation_id} caption plan duration does not match timeline")

    style = plan.get("style", {})
    if style.get("status") != "approved":
        errors.append(f"{operation_id} caption style is not approved")
    if style.get("selection_mode") not in ("human", "agent"):
        errors.append(f"{operation_id} caption selection_mode must be human or agent")
    for field in ("selection_rationale", "choice_id", "preset"):
        if not str(style.get(field, "")).strip():
            errors.append(f"{operation_id} caption style {field} is required")
    if not isinstance(style.get("resolved"), dict) or not style["resolved"]:
        errors.append(f"{operation_id} caption resolved style is required")

    review = plan.get("review", {})
    if review.get("status") != "approved":
        errors.append(f"{operation_id} caption review is not approved")
    evidence = review.get("evidence")
    presentation = plan.get("presentation", {})
    expressive = presentation.get("mode") == "expressive"
    if not isinstance(evidence, list):
        errors.append(f"{operation_id} caption review evidence must be a list")
    elif expressive:
        layout_beats = presentation.get("layout_beats")
        if not isinstance(layout_beats, list) or not layout_beats:
            errors.append(f"{operation_id} expressive caption review requires layout beats")
        else:
            expected_evidence = len(layout_beats) + 1
            if len(evidence) != expected_evidence:
                errors.append(
                    f"{operation_id} expressive caption review requires one image per "
                    f"layout beat plus no-caption ({expected_evidence} total)"
                )
    elif len(evidence) < 4:
        errors.append(f"{operation_id} caption review requires four evidence images")
    if isinstance(evidence, list):
        for value in evidence:
            try:
                path = resolve_project_path(project_root, value)
            except (TypeError, ValueError) as exc:
                errors.append(str(exc))
            else:
                if not path.is_file():
                    errors.append(f"{operation_id} caption review evidence is missing: {value}")

    cues = plan.get("cues")
    if not isinstance(cues, list) or not cues:
        errors.append(f"{operation_id} caption cues must be a non-empty list")
    else:
        previous_end = 0.0
        for index, cue in enumerate(cues, 1):
            label = f"{operation_id} cue {index}"
            try:
                start, end = float(cue["start"]), float(cue["end"])
                program_range = cue["program_range"]
                program_start = float(program_range["start_s"])
                program_end = float(program_range["end_s"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{label} timing is invalid")
                continue
            if (
                not math.isfinite(start) or not math.isfinite(end)
                or start < previous_end - tolerance or end <= start or end > duration + tolerance
            ):
                errors.append(f"{label} is outside ordered program time")
            if abs(start - program_start) > tolerance or abs(end - program_end) > tolerance:
                errors.append(f"{label} program_range does not match compatibility timing")
            words = cue.get("words")
            if not isinstance(words, list) or not words:
                errors.append(f"{label} words must resolve to one timeline clip")
            else:
                clip_ids = {
                    word.get("clip_id") if isinstance(word, dict) else None
                    for word in words
                }
                if None in clip_ids or len(clip_ids) != 1:
                    errors.append(f"{label} words must resolve to one timeline clip")
                elif any(
                    not isinstance(word.get("source_range"), dict)
                    or not isinstance(word.get("program_range"), dict)
                    for word in words
                ):
                    errors.append(f"{label} words require source and program ranges")
            previous_end = end

    renderer = plan.get("renderer_recipe", {})
    if renderer.get("engine") != "hyperframes" or renderer.get("asset_type") != "image-sequence":
        errors.append(f"{operation_id} caption renderer must be a HyperFrames image sequence")
    if renderer.get("fps") != timeline.get("fps"):
        errors.append(f"{operation_id} caption renderer fps does not match timeline fps")
    if renderer.get("asset") != contribution.get("asset"):
        errors.append(f"{operation_id} caption plan asset does not match render contribution")
    runtime_assets = renderer.get("runtime_assets")
    if not isinstance(runtime_assets, list) or not runtime_assets:
        errors.append(f"{operation_id} caption runtime_assets are required")
    elif any(
        not isinstance(asset, dict)
        or not str(asset.get("path", "")).strip()
        or not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256", "")))
        for asset in runtime_assets
    ):
        errors.append(f"{operation_id} caption runtime asset hashes are invalid")


def _validate_broll_plan(plan, operation, contributions, timeline, errors, project_root=None):
    operation_id = operation.get("id") if isinstance(operation, dict) else "b-roll"
    prefix = f"{operation_id or 'b-roll'} B-roll plan mismatch: "

    def number(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        try:
            value = float(value)
        except (OverflowError, TypeError, ValueError):
            return None
        return value if math.isfinite(value) else None

    def valid_dependencies(value):
        if (
            not isinstance(value, list) or not value
            or any(not isinstance(item, str) or not item.strip() for item in value)
        ):
            return False
        order = ("understanding", "cut", "color-grade")
        return len(value) == len(set(value)) and value == [item for item in order if item in value]

    def valid_based_on(value, dependencies):
        return (
            isinstance(value, dict)
            and isinstance(dependencies, list)
            and set(value) == set(dependencies)
            and all(
                isinstance(revision, int) and not isinstance(revision, bool) and revision > 0
                for revision in value.values()
            )
        )

    def valid_timestamp(value):
        if not isinstance(value, str):
            return False
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed.tzinfo is not None and parsed.utcoffset() is not None

    def bound_file(binding, label, expected_path=None):
        path_value = binding.get("path") if isinstance(binding, dict) else None
        valid = (
            isinstance(binding, dict) and set(binding) == {"path", "sha256"}
            and isinstance(path_value, str) and bool(path_value.strip())
            and re.fullmatch(r"[0-9a-fA-F]{64}", str(binding.get("sha256", "")))
            and (expected_path is None or path_value == expected_path)
        )
        if not valid:
            errors.append(prefix + f"{label} binding is invalid")
            return None
        if project_root is None:
            return None
        try:
            root, raw = Path(project_root).resolve(), Path(path_value)
            path = (root / raw).resolve()
        except (OSError, ValueError, TypeError, RuntimeError):
            errors.append(prefix + f"{label} path is invalid")
            return None
        try:
            path.relative_to(root)
        except ValueError:
            errors.append(prefix + f"{label} path escapes project root")
            return None
        try:
            if not path.is_file():
                errors.append(prefix + f"{label} file is missing")
                return None
            digest = _sha256_file(path)
        except (OSError, ValueError, TypeError, RuntimeError):
            errors.append(prefix + f"{label} file could not be validated")
            return None
        if digest != binding["sha256"]:
            errors.append(prefix + f"{label} SHA-256 is stale")
            return None
        return path

    if not isinstance(plan, dict):
        errors.append(prefix + "plan must be an object")
        return
    if not isinstance(operation, dict):
        errors.append(prefix + "operation must be an object")
        return
    if not isinstance(timeline, dict):
        errors.append(prefix + "timeline must be an object")
        return
    schema_version = plan.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        errors.append(prefix + "plan schema_version must be integer 1")
    elif schema_version != 1:
        errors.append(prefix + "plan schema_version must be 1")
    if plan.get("review_status") != "approved":
        errors.append(prefix + "review_status must be approved")
    review = plan.get("review")
    if not isinstance(review, dict) or review.get("status") != "approved":
        errors.append(prefix + "review receipt must be approved")
    visual_review = plan.get("visual_review")
    receipt = None
    required_checks = {
        "semantic_fit", "unwanted_logos_or_text", "jump_cuts",
        "entry_exit_boundaries", "grade_match",
    }
    if operation.get("status") == "approved":
        if visual_review is not None:
            errors.append(prefix + "approved operation must not carry completed visual review")
        check = operation.get("check")
        expected_report = "../review/03-b-roll/b-roll-summary.md"
        if not isinstance(check, dict) or check.get("status") != "pending" or check.get("report") != expected_report:
            errors.append(prefix + "approved operation check must reference pending machine summary")
    elif not isinstance(visual_review, dict) or visual_review.get("status") != "completed":
        errors.append(prefix + "visual review must be completed")
    else:
        active_review_id = review.get("review_id") if isinstance(review, dict) else None
        if visual_review.get("review_id") != active_review_id:
            errors.append(prefix + "visual review UUID does not match active review")
        subject = {key: value for key, value in plan.items() if key != "visual_review"}
        payload = json.dumps(subject, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        expected_plan_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if visual_review.get("plan_sha256") != expected_plan_hash:
            errors.append(prefix + "visual review plan SHA-256 does not match")
        mode = visual_review.get("mode")
        if mode not in ("human", "agent"):
            errors.append(prefix + "visual review mode must be human or agent")
        if not isinstance(visual_review.get("actor"), str) or not visual_review["actor"].strip():
            errors.append(prefix + "visual review actor is required")
        if not isinstance(visual_review.get("rationale"), str) or not visual_review["rationale"].strip():
            errors.append(prefix + "visual review rationale is required")
        if not valid_timestamp(visual_review.get("timestamp")):
            errors.append(prefix + "visual review timestamp is invalid")
        if mode == "human" and visual_review.get("explicit_user_action") is not True:
            errors.append(prefix + "human visual review requires explicit_user_action true")
        checks = visual_review.get("checks")
        if (not isinstance(checks, dict) or set(checks) != required_checks
                or any(value is not True for value in checks.values())):
            errors.append(prefix + "all visual checks must be true booleans")
        receipt_path = bound_file(
            visual_review.get("receipt"), "visual review receipt",
            "work/b-roll/b-roll-visual-review.json",
        )
        bound_file(
            visual_review.get("report"), "visual review report",
            "review/03-b-roll/b-roll-visual-review.md",
        )
        if receipt_path is not None:
            try:
                receipt = load_json(receipt_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(prefix + f"visual review receipt is invalid JSON: {exc}")
            else:
                if not isinstance(receipt, dict):
                    errors.append(prefix + "visual review receipt must be an object")
                    receipt = None
                elif receipt.get("schema_version") != 1:
                    errors.append(prefix + "visual review receipt schema_version must be 1")
                authority = (
                    "status", "review_id", "plan_sha256", "mode", "actor",
                    "rationale", "timestamp", "checks",
                )
                if (isinstance(receipt, dict)
                        and (any(receipt.get(key) != visual_review.get(key) for key in authority)
                             or receipt.get("explicit_user_action") != visual_review.get("explicit_user_action"))):
                    errors.append(prefix + "visual review receipt authority does not match plan")
        check = operation.get("check")
        expected_report = "../review/03-b-roll/b-roll-visual-review.md"
        if not isinstance(check, dict) or check.get("status") != "pass" or check.get("report") != expected_report:
            errors.append(prefix + "operation check must reference completed visual review")
    plan_timeline_id = plan.get("timeline_id")
    timeline_id = timeline.get("timeline_id")
    if not isinstance(plan_timeline_id, str) or not plan_timeline_id.strip():
        errors.append(prefix + "plan timeline_id must be nonblank")
    if not isinstance(timeline_id, str) or not timeline_id.strip():
        errors.append(prefix + "timeline timeline_id must be nonblank")
    if (
        isinstance(plan_timeline_id, str) and plan_timeline_id.strip()
        and isinstance(timeline_id, str) and timeline_id.strip()
        and plan_timeline_id != timeline_id
    ):
        errors.append(prefix + "timeline_id does not match timeline")

    duration = number(plan.get("program_duration_s"))
    timeline_duration = number(timeline.get("program_duration_s"))
    if duration is None:
        errors.append(prefix + "program_duration_s must be finite")
    elif timeline_duration is None:
        errors.append(prefix + "timeline program_duration_s must be finite")
    elif duration != timeline_duration:
        errors.append(prefix + "program_duration_s does not match timeline")

    target = operation.get("target")
    if not isinstance(target, dict):
        errors.append(prefix + "operation target must be an object")
    elif target.get("scope") != "b-roll":
        errors.append(prefix + "operation target scope must be b-roll")
    revision = operation.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision <= 0:
        errors.append(prefix + "operation revision must be a positive integer")

    operation_dependencies = operation.get("depends_on")
    plan_dependencies = plan.get("dependencies")
    operation_dependencies_valid = valid_dependencies(operation_dependencies)
    plan_dependencies_valid = valid_dependencies(plan_dependencies)
    if not operation_dependencies_valid:
        errors.append(prefix + "operation dependencies must be unique and canonically ordered")
    if not plan_dependencies_valid:
        errors.append(prefix + "plan dependencies must be unique and canonically ordered")
    if operation_dependencies != plan_dependencies:
        errors.append(prefix + "operation dependencies do not match plan")
        errors.append(prefix + "plan dependencies do not match operation")

    operation_based_on = operation.get("based_on")
    plan_based_on = plan.get("based_on")
    if not isinstance(operation_based_on, dict) or not operation_dependencies_valid or set(operation_based_on) != set(operation_dependencies):
        errors.append(prefix + "operation based_on keys must exactly match dependencies")
    elif not valid_based_on(operation_based_on, operation_dependencies):
        errors.append(prefix + "operation based_on revisions must be positive integers")
    if not isinstance(plan_based_on, dict) or not plan_dependencies_valid or set(plan_based_on) != set(plan_dependencies):
        errors.append(prefix + "plan based_on keys must exactly match dependencies")
    elif not valid_based_on(plan_based_on, plan_dependencies):
        errors.append(prefix + "plan based_on revisions must be positive integers")
    if operation_based_on != plan_based_on:
        errors.append(prefix + "operation based_on does not match plan")

    shots = plan.get("shots")
    if not isinstance(shots, list):
        errors.append(prefix + "shots must be a list")
        return
    selected = []
    ranges = []
    shot_ids = set()
    for index, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            errors.append(prefix + f"shot {index} must be an object")
            continue
        shot_id = shot.get("id")
        label = shot_id if isinstance(shot_id, str) and shot_id.strip() else str(index)
        if isinstance(shot_id, str):
            if shot_id in shot_ids:
                errors.append(prefix + f"duplicate shot id: {shot_id}")
            else:
                shot_ids.add(shot_id)
        status = shot.get("status")
        if status == "skipped":
            if shot.get("selected") is not None or "normalized" in shot or "verification" in shot:
                errors.append(prefix + f"shot {label} skipped lifecycle is invalid")
            continue
        selected.append(shot)
        if status != "verified":
            errors.append(prefix + f"shot {label} must be verified or skipped")
        if not isinstance(shot.get("selected"), dict):
            errors.append(prefix + f"shot {label} selection must be an object")
        verification = shot.get("verification")
        if not isinstance(verification, dict) or verification.get("status") != "pass":
            errors.append(prefix + f"shot {label} verification must pass")
            verification_digest = None
        elif "normalized_sha256" not in verification:
            errors.append(prefix + f"shot {label} verification normalized_sha256 is required")
            verification_digest = None
        elif not re.fullmatch(r"[0-9a-fA-F]{64}", str(verification.get("normalized_sha256", ""))):
            errors.append(prefix + f"shot {label} verification normalized_sha256 is invalid")
            verification_digest = None
        else:
            verification_digest = verification["normalized_sha256"]

        program_range = shot.get("program_range")
        start = number(program_range.get("start_s")) if isinstance(program_range, dict) else None
        end = number(program_range.get("end_s")) if isinstance(program_range, dict) else None
        if (
            start is None or end is None or timeline_duration is None
            or start < 0 or end <= start or end > timeline_duration
        ):
            errors.append(prefix + f"shot {label} program_range is invalid")
        else:
            ranges.append((start, end, label))

        normalized = shot.get("normalized")
        if not isinstance(normalized, dict):
            errors.append(prefix + f"shot {label} normalized record is required")
            continue
        value = normalized.get("path")
        if not isinstance(value, str) or not value.strip():
            safe_path = False
        else:
            path = Path(value)
            safe_path = (
                not path.is_absolute() and not path.drive and ".." not in path.parts
                and path.as_posix() == value
            )
        if not safe_path:
            errors.append(prefix + f"shot {label} normalized path must be safe and project-relative")
        normalized_digest = normalized.get("sha256")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(normalized_digest or "")):
            errors.append(prefix + f"shot {label} normalized SHA-256 is invalid")
        elif verification_digest is not None and verification_digest != normalized_digest:
            errors.append(
                prefix + f"shot {label} verification normalized_sha256 "
                "does not match normalized SHA-256"
            )

    if [item[0] for item in ranges] != sorted(item[0] for item in ranges):
        errors.append(prefix + "selected shots must be chronological")
    ordered_ranges = sorted(ranges)
    if any(current[0] < previous[1] for previous, current in zip(ordered_ranges, ordered_ranges[1:])):
        errors.append(prefix + "selected shot ranges overlap")

    if receipt is not None:
        artifacts = receipt.get("artifacts")
        artifact_keys = {
            "stills", "contact_sheet", "boundary_reel", "machine_summary",
            "final_video",
        }
        if not isinstance(artifacts, dict) or set(artifacts) != artifact_keys:
            errors.append(prefix + "visual review receipt artifacts are invalid")
        else:
            expected_stills, shared = [], {}
            for shot in selected:
                shot_id, verification = shot.get("id"), shot.get("verification")
                shot_stills = verification.get("stills") if isinstance(verification, dict) else None
                if not isinstance(shot_stills, dict) or set(shot_stills) != {"first", "middle", "last"}:
                    errors.append(prefix + f"shot {shot_id} verification stills are invalid")
                    continue
                for position in ("first", "middle", "last"):
                    item = shot_stills[position]
                    path = item.get("path") if isinstance(item, dict) else None
                    if not isinstance(path, str) or not path.startswith("review/03-b-roll/stills/"):
                        errors.append(prefix + f"shot {shot_id} {position} still path is invalid")
                    bound_file(item, f"shot {shot_id} {position} still")
                    if isinstance(item, dict):
                        expected_stills.append({"shot_id": shot_id, "position": position, **item})
                for key, expected_path in (
                    ("contact_sheet", "review/03-b-roll/contact-sheet.jpg"),
                    ("boundary_reel", "review/03-b-roll/boundary-reel.mp4"),
                    ("report", "review/03-b-roll/b-roll-summary.md"),
                ):
                    item = verification.get(key) if isinstance(verification, dict) else None
                    bound_file(item, f"shot {shot_id} {key.replace('_', ' ')}", expected_path)
                    if key in shared and shared[key] != item:
                        errors.append(prefix + f"verified shots disagree on {key.replace('_', ' ')}")
                    else:
                        shared[key] = item
            expected = {
                "stills": expected_stills,
                "contact_sheet": shared.get("contact_sheet"),
                "boundary_reel": shared.get("boundary_reel"),
                "machine_summary": shared.get("report"),
            }
            if any(artifacts.get(key) != value for key, value in expected.items()):
                errors.append(prefix + "visual review receipt artifact bindings do not match plan")
            bound_file(
                artifacts.get("final_video"), "final video", "final/final-video.mp4"
            )

    if not isinstance(contributions, list):
        errors.append(prefix + "render contributions must be a list")
        return
    if len(contributions) != len(selected):
        errors.append(
            prefix + f"overlay contribution count {len(contributions)} does not match "
            f"verified selected shot count {len(selected)}"
        )
    for index, (shot, contribution) in enumerate(zip(selected, contributions), 1):
        label = shot.get("id") or index
        if not isinstance(contribution, dict):
            errors.append(prefix + f"contribution {index} must be an object")
            continue
        if set(contribution) != {"kind", "asset", "start_s", "duration_s"}:
            errors.append(
                prefix + f"contribution {index} fields must be exactly "
                "asset, duration_s, kind, start_s"
            )
        if contribution.get("kind") != "overlay":
            errors.append(prefix + f"contribution {index} kind must be overlay")
        normalized = shot.get("normalized")
        expected_asset = normalized.get("path") if isinstance(normalized, dict) else None
        if contribution.get("asset") != expected_asset:
            errors.append(prefix + f"contribution {index} asset does not match shot {label} normalized path")
        program_range = shot.get("program_range")
        start = number(program_range.get("start_s")) if isinstance(program_range, dict) else None
        end = number(program_range.get("end_s")) if isinstance(program_range, dict) else None
        contribution_start = number(contribution.get("start_s"))
        contribution_duration = number(contribution.get("duration_s"))
        if contribution_start is None or start is None or contribution_start != start:
            errors.append(prefix + f"contribution {index} start_s does not match shot {label}")
        if contribution_duration is None or start is None or end is None or contribution_duration != end - start:
            errors.append(prefix + f"contribution {index} duration_s does not match shot {label}")


def _validate_image_sequence(contribution, asset_path, expected_fps, operation_id, errors):
    pattern = contribution.get("pattern")
    start_number = contribution.get("start_number", 1)
    fps = contribution.get("fps")
    if not asset_path.is_dir():
        errors.append(f"{operation_id} image-sequence asset must be a directory")
        return
    if (
        not isinstance(pattern, str)
        or Path(pattern).name != pattern
        or not re.fullmatch(r"[A-Za-z0-9._-]*%0?[1-9][0-9]*d[A-Za-z0-9._-]*", pattern)
    ):
        errors.append(f"{operation_id} image-sequence pattern is invalid")
        return
    if not isinstance(start_number, int) or isinstance(start_number, bool) or start_number < 0:
        errors.append(f"{operation_id} image-sequence start_number must be a non-negative integer")
        return
    if (
        not isinstance(fps, dict)
        or not isinstance(fps.get("num"), int)
        or isinstance(fps.get("num"), bool)
        or not isinstance(fps.get("den"), int)
        or isinstance(fps.get("den"), bool)
        or fps.get("num", 0) <= 0
        or fps.get("den", 0) <= 0
    ):
        errors.append(f"{operation_id} image-sequence fps must use positive integer num and den")
        return
    if expected_fps and fps != expected_fps:
        errors.append(f"{operation_id} image-sequence fps does not match timeline fps")
    try:
        first_frame = asset_path / (pattern % start_number)
    except (TypeError, ValueError):
        errors.append(f"{operation_id} image-sequence pattern is invalid")
    else:
        if not first_frame.is_file():
            errors.append(f"{operation_id} image-sequence first frame is missing")


def build_render_plan(project, project_root):
    """Compile approved active operations into a render-relative delivery plan."""
    errors = validate_project(project, project_root, check_files=True)
    if errors:
        raise ValueError("invalid project: " + "; ".join(errors))

    sequence_name = project["active_sequence"]
    sequence = project["sequences"][sequence_name]
    operations = operation_map(project)
    render_path = resolve_project_path(project_root, project["render"]["plan"])
    render_dir = render_path.parent

    source_value = project.get("source", {}).get("path")
    if not source_value:
        errors.append("project source path is required")
        source_relative = None
    else:
        source_relative, source_path = _relative_to_render(
            project_root, render_dir, source_value
        )
        if not source_path.is_file():
            errors.append(f"project source is missing: {source_value}")

    timeline_value = sequence.get("timeline")
    timeline = None
    if not timeline_value:
        errors.append(f"sequence {sequence_name} has no timeline")
        timeline_relative = None
    else:
        timeline_relative, timeline_path = _relative_to_render(
            project_root, render_dir, timeline_value
        )
        if not timeline_path.is_file():
            errors.append(f"sequence {sequence_name} missing timeline: {timeline_value}")
        else:
            timeline = load_json(timeline_path)

    compiled = []
    for operation_id in sequence.get("operations", []):
        operation = operations[operation_id]
        if operation.get("status") not in ("approved", "verified"):
            errors.append(f"{operation_id} is not approved for delivery")
            continue
        if operation.get("skill") == "video-add-content-cards" and operation.get("plan"):
            cards_path = resolve_project_path(project_root, operation["plan"])
            if cards_path.is_file():
                try:
                    _validate_cards_choices(
                        load_json(cards_path), operation_id, errors,
                        project_root=project_root,
                        expected_fps=timeline.get("fps") if timeline else None,
                    )
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"{operation_id} invalid cards plan: {exc}")
        declared = operation.get("render")
        if not declared:
            errors.append(f"{operation_id} has no render contribution")
            continue
        contributions = declared if isinstance(declared, list) else [declared]
        if operation.get("skill") == "video-add-b-roll":
            before = len(errors)
            target = operation.get("target")
            if not isinstance(target, dict) or target.get("sequence") != sequence_name:
                errors.append(
                    f"{operation_id} B-roll plan mismatch: "
                    "operation target sequence does not match active_sequence"
                )
            required_dependencies = [
                "understanding",
                *[
                    dependency for dependency in ("cut", "color-grade")
                    if dependency in sequence.get("operations", []) and dependency in operations
                ],
            ]
            if operation.get("depends_on") != required_dependencies:
                errors.append(
                    f"{operation_id} B-roll plan mismatch: operation dependencies "
                    "do not match active upstream operations"
                )
            plan_value = operation.get("plan")
            if not plan_value:
                errors.append(f"{operation_id} B-roll plan mismatch: plan is required")
            elif timeline:
                try:
                    broll_path = resolve_project_path(project_root, plan_value)
                    broll_plan = load_json(broll_path)
                except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"{operation_id} B-roll plan mismatch: invalid plan: {exc}")
                else:
                    _validate_broll_plan(
                        broll_plan, operation, contributions, timeline, errors,
                        project_root=project_root,
                    )
            if len(errors) != before:
                continue
        for contribution in contributions:
            if not isinstance(contribution, dict):
                errors.append(f"{operation_id} render contribution must be an object")
                continue
            kind = contribution.get("kind")
            if kind not in CONTRIBUTION_KINDS:
                errors.append(f"{operation_id} unsupported contribution: {kind!r}")
                continue
            if (
                kind == "overlay"
                and timeline
                and operation.get("skill") == "video-add-captions"
                and operation.get("plan")
            ):
                captions_path = resolve_project_path(project_root, operation["plan"])
                if captions_path.is_file():
                    try:
                        _validate_caption_plan(
                            load_json(captions_path), contribution, operation_id,
                            errors, project_root, timeline,
                        )
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        errors.append(f"{operation_id} invalid caption plan: {exc}")
            item = {"operation": operation_id, **contribution}

            required_path = {
                "timeline-transform": "input",
                "video-filter": "plan",
                "overlay": "asset",
                "precomputed-asset": "asset",
            }.get(kind)
            resolved_paths = {}
            for key in ("input", "plan", "asset"):
                if key not in item:
                    continue
                try:
                    item[key], resolved_paths[key] = _relative_to_render(
                        project_root, render_dir, item[key]
                    )
                except ValueError as exc:
                    errors.append(str(exc))
            if required_path and required_path not in item:
                errors.append(f"{operation_id} {kind} requires {required_path}")
            elif required_path:
                required = resolved_paths[required_path]
                if kind == "overlay" and contribution.get("asset_type") == "image-sequence":
                    _validate_image_sequence(
                        contribution,
                        required,
                        timeline.get("fps") if timeline else None,
                        operation_id,
                        errors,
                    )
                elif not required.is_file():
                    errors.append(
                        f"{operation_id} missing {required_path}: {contribution[required_path]}"
                    )

            if kind == "video-filter":
                if contribution.get("target") not in ("base-video", "composite"):
                    errors.append(f"{operation_id} video-filter target is unsupported")
                plan_path = resolved_paths.get("plan")
                if plan_path and plan_path.is_file() and operation.get("skill") == "video-color-grade":
                    try:
                        grade_plan = load_json(plan_path)
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        errors.append(f"{operation_id} invalid grade plan: {exc}")
                    else:
                        _validate_grade_choice(grade_plan, contribution, operation_id, errors)
            compiled.append(item)

    output = project.get("render", {}).get("output")
    if not output:
        errors.append("render output is required")
        output_relative = None
    else:
        output_relative, _ = _relative_to_render(project_root, render_dir, output)

    if errors:
        raise ValueError("invalid render plan: " + "; ".join(errors))
    return {
        "schema_version": 1,
        "sequence": sequence_name,
        "source": source_relative,
        "source_fingerprint": dict(project["source"]["fingerprint"]),
        "timeline": timeline_relative,
        "contributions": compiled,
        "output": output_relative,
    }


def _rounded_time(value):
    return round(float(value), 6)


def timeline_from_segments(
    segments, source_duration_s, fps, timeline_id="main", source_asset_id="source"
):
    clips = []
    program_start = 0.0
    for index, segment in enumerate(segments, 1):
        source_start = float(segment.get("start_s", segment.get("in")))
        source_end = float(segment.get("end_s", segment.get("out")))
        speed = float(segment.get("speed", 1.0))
        if speed <= 0:
            raise ValueError(f"segment {index} speed must be positive")
        program_end = program_start + (source_end - source_start) / speed
        decision_id = segment.get("id") or segment.get("decision_ref") or f"edit-{index:03d}"
        clip = {
            "id": f"clip-{index:03d}",
            "source_range": {
                "start_s": _rounded_time(source_start),
                "end_s": _rounded_time(source_end),
            },
            "program_range": {
                "start_s": _rounded_time(program_start),
                "end_s": _rounded_time(program_end),
            },
            "speed": speed,
            "decision_ref": decision_id,
        }
        if segment.get("reason"):
            clip["reason"] = segment["reason"]
        clips.append(clip)
        program_start = program_end

    timeline = {
        "schema_version": 1,
        "timeline_id": timeline_id,
        "source_asset_id": source_asset_id,
        "fps": {"num": int(fps["num"]), "den": int(fps["den"])},
        "source_duration_s": _rounded_time(source_duration_s),
        "program_duration_s": _rounded_time(program_start),
        "clips": clips,
    }
    errors = validate_timeline(timeline)
    if errors:
        raise ValueError("invalid timeline: " + "; ".join(errors))
    return timeline


def source_timeline(source_duration_s, fps, source_asset_id="source"):
    return timeline_from_segments(
        [
            {
                "id": "source",
                "start_s": 0.0,
                "end_s": float(source_duration_s),
                "speed": 1.0,
            }
        ],
        source_duration_s=source_duration_s,
        fps=fps,
        timeline_id="source",
        source_asset_id=source_asset_id,
    )


def timeline_from_edit(edit, fps, timeline_id="main", source_asset_id="source"):
    if "decisions" in edit:
        segments = []
        for decision in edit["decisions"]:
            if decision.get("action") != "keep":
                continue
            segments.append(
                {
                    "id": decision.get("id"),
                    "start_s": decision["start_s"],
                    "end_s": decision["end_s"],
                    "speed": decision.get("speed", 1.0),
                    "reason": decision.get("reason", ""),
                }
            )
    else:
        segments = [
            {
                "id": segment.get("decision_ref") or segment.get("id") or f"edit-{index:03d}",
                "in": segment["in"],
                "out": segment["out"],
                "speed": segment.get("speed", 1.0),
                "reason": segment.get("reason", ""),
            }
            for index, segment in enumerate(edit.get("keep", []), 1)
        ]
    source_duration = edit.get("source_duration_s")
    if source_duration is None:
        raise ValueError("edit source_duration_s is required")
    return timeline_from_segments(
        segments,
        source_duration_s=source_duration,
        fps=fps,
        timeline_id=timeline_id,
        source_asset_id=source_asset_id,
    )


def validate_timeline(timeline, decision_ids=None):
    errors = []
    if timeline.get("schema_version") != 1:
        errors.append("timeline schema_version must be 1")

    fps = timeline.get("fps", {})
    num, den = fps.get("num"), fps.get("den")
    if (
        not isinstance(num, int)
        or isinstance(num, bool)
        or not isinstance(den, int)
        or isinstance(den, bool)
        or num <= 0
        or den <= 0
    ):
        errors.append("fps num and den must be positive integers")
        frame_tolerance = 1e-6
    else:
        frame_tolerance = den / num

    try:
        source_duration = float(timeline["source_duration_s"])
        program_duration = float(timeline["program_duration_s"])
    except (KeyError, TypeError, ValueError):
        errors.append("source_duration_s and program_duration_s must be numbers")
        return errors
    if source_duration <= 0:
        errors.append("source_duration_s must be positive")
    if program_duration < 0:
        errors.append("program_duration_s must not be negative")

    clips = timeline.get("clips")
    if not isinstance(clips, list) or not clips:
        errors.append("timeline clips must be a non-empty list")
        return errors

    seen = set()
    previous_source_start = -1.0
    previous_source_end = 0.0
    expected_program_start = 0.0
    for index, clip in enumerate(clips, 1):
        clip_id = clip.get("id") or f"clip-{index}"
        if clip_id in seen:
            errors.append(f"duplicate clip id: {clip_id}")
        seen.add(clip_id)

        try:
            source_start = float(clip["source_range"]["start_s"])
            source_end = float(clip["source_range"]["end_s"])
            program_start = float(clip["program_range"]["start_s"])
            program_end = float(clip["program_range"]["end_s"])
            speed = float(clip["speed"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{clip_id} ranges and speed must be numeric")
            continue

        if source_start < previous_source_start - frame_tolerance:
            errors.append(f"{clip_id} source clips must stay chronological")
        if source_start < previous_source_end - frame_tolerance:
            errors.append(f"{clip_id} source ranges overlap")
        if source_start < 0 or source_end <= source_start:
            errors.append(f"{clip_id} source range is invalid")
        if source_end > source_duration + frame_tolerance:
            errors.append(f"{clip_id} source range exceeds source duration")
        if abs(program_start - expected_program_start) > frame_tolerance:
            errors.append(f"{clip_id} program ranges must be contiguous")
        if program_end <= program_start:
            errors.append(f"{clip_id} program range is invalid")
        if speed <= 0:
            errors.append(f"{clip_id} speed must be positive")
        else:
            expected_duration = (source_end - source_start) / speed
            if abs((program_end - program_start) - expected_duration) > frame_tolerance:
                errors.append(f"{clip_id} program duration does not match speed")

        decision_ref = clip.get("decision_ref")
        if decision_ids is not None and decision_ref not in decision_ids:
            errors.append(f"{clip_id} decision_ref does not resolve: {decision_ref}")

        previous_source_start = source_start
        previous_source_end = source_end
        expected_program_start = program_end

    if abs(expected_program_start - program_duration) > frame_tolerance:
        errors.append("program_duration_s does not match final program range")
    return errors


def source_to_program(timeline, source_s):
    source_s = float(source_s)
    for clip in timeline["clips"]:
        source_range = clip["source_range"]
        if source_range["start_s"] <= source_s < source_range["end_s"]:
            return _rounded_time(
                clip["program_range"]["start_s"]
                + (source_s - source_range["start_s"]) / clip["speed"]
            )
    return None


def program_to_source(timeline, program_s):
    program_s = float(program_s)
    for clip in timeline["clips"]:
        program_range = clip["program_range"]
        if program_range["start_s"] <= program_s < program_range["end_s"]:
            return _rounded_time(
                clip["source_range"]["start_s"]
                + (program_s - program_range["start_s"]) * clip["speed"]
            )
    return None


def map_transcript_to_timeline(transcript, timeline):
    """Map canonical source-time words onto a validated program timeline."""
    errors = validate_timeline(timeline)
    if errors:
        raise ValueError("invalid timeline: " + "; ".join(errors))
    segments = transcript.get("segments")
    if not isinstance(segments, list):
        raise ValueError("transcript segments must be a list")

    mapped_segments = []
    previous_source_start = -1.0
    for segment_index, segment in enumerate(segments):
        words = segment.get("words", [])
        if not isinstance(words, list):
            raise ValueError(f"segment {segment_index} words must be a list")
        groups = []
        for word_index, word in enumerate(words):
            try:
                source_start = float(word["start"])
                source_end = float(word["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"segment {segment_index} word {word_index} has invalid timing"
                ) from exc
            if (
                not math.isfinite(source_start)
                or not math.isfinite(source_end)
                or source_start < 0
                or source_end < source_start
            ):
                raise ValueError(
                    f"segment {segment_index} word {word_index} has invalid timing"
                )
            if source_end == source_start:
                # faster-whisper can emit point-timed words; preserve the word and
                # its clip assignment while giving downstream cues a positive range.
                source_end = source_start + POINT_WORD_DURATION_S
            if source_start < previous_source_start - 1e-6:
                raise ValueError("transcript words must stay chronological")
            previous_source_start = source_start

            midpoint = (source_start + source_end) / 2
            clip = next(
                (
                    item
                    for item in timeline["clips"]
                    if item["source_range"]["start_s"]
                    <= midpoint
                    < item["source_range"]["end_s"]
                ),
                None,
            )
            if clip is None:
                continue

            source_range = clip["source_range"]
            clipped_start = max(source_start, float(source_range["start_s"]))
            clipped_end = min(source_end, float(source_range["end_s"]))
            if clipped_end <= clipped_start:
                continue
            program_start = (
                float(clip["program_range"]["start_s"])
                + (clipped_start - float(source_range["start_s"])) / float(clip["speed"])
            )
            program_end = (
                float(clip["program_range"]["start_s"])
                + (clipped_end - float(source_range["start_s"])) / float(clip["speed"])
            )
            mapped_word = {
                **word,
                "start": _rounded_time(program_start),
                "end": _rounded_time(program_end),
                "source_range": {
                    "start_s": _rounded_time(clipped_start),
                    "end_s": _rounded_time(clipped_end),
                },
                "program_range": {
                    "start_s": _rounded_time(program_start),
                    "end_s": _rounded_time(program_end),
                },
                "clip_id": clip["id"],
            }
            if not groups or groups[-1]["clip_id"] != clip["id"]:
                groups.append({"clip_id": clip["id"], "words": []})
            groups[-1]["words"].append(mapped_word)

        source_segment_id = segment.get("id", segment_index)
        for group_index, group in enumerate(groups, 1):
            group_words = group["words"]
            raw_words = [str(word.get("word", "")) for word in group_words]
            text = "".join(raw_words).strip()
            if len(raw_words) > 1 and not any(
                value[:1].isspace() for value in raw_words[1:]
            ) and any(character.isascii() and character.isalnum() for character in text):
                text = " ".join(value.strip() for value in raw_words).strip()
            mapped_segments.append(
                {
                    "id": f"{source_segment_id}.{group['clip_id']}.{group_index}",
                    "source_segment_id": source_segment_id,
                    "clip_id": group["clip_id"],
                    "start": group_words[0]["start"],
                    "end": group_words[-1]["end"],
                    "text": text,
                    "source_range": {
                        "start_s": group_words[0]["source_range"]["start_s"],
                        "end_s": group_words[-1]["source_range"]["end_s"],
                    },
                    "program_range": {
                        "start_s": group_words[0]["program_range"]["start_s"],
                        "end_s": group_words[-1]["program_range"]["end_s"],
                    },
                    "words": group_words,
                }
            )

    return {
        **transcript,
        "duration": _rounded_time(timeline["program_duration_s"]),
        "timebase": "program",
        "timeline_id": timeline["timeline_id"],
        "source_duration": transcript.get("duration", timeline["source_duration_s"]),
        "segments": mapped_segments,
    }
