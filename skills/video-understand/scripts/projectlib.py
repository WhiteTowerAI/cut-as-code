"""Shared Open Recut project protocol helpers."""

import json
import math
import os
import re
import subprocess
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
    for dependency in dependencies:
        if dependency not in nodes and not (allow_render and dependency == "render"):
            errors.append(f"{node_id} missing dependency: {dependency}")

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
            if dependency in nodes
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
    if not isinstance(evidence, list) or len(evidence) < 4:
        errors.append(f"{operation_id} caption review requires four evidence images")
    else:
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
