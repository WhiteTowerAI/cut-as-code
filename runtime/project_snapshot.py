"""Read-only, project-root-confined Protocol V1 snapshots."""

import hashlib
import json
import os
import sys
from pathlib import Path


PROJECTLIB_DIR = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "video-understand"
    / "scripts"
)
sys.path.insert(0, str(PROJECTLIB_DIR))

import projectlib  # noqa: E402


_UNPARSED = object()


def file_etag(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resource_id(kind, owner=""):
    key = f"{kind}:{owner}".encode("utf-8")
    return "res_" + hashlib.sha256(key).hexdigest()[:24]


def canonical_project_root(value):
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError("project root must contain work/project.json")
    root = Path(value).resolve(strict=False)
    _manifest_path(root)
    return root


def _manifest_path(root):
    manifest = (root / "work" / "project.json").resolve(strict=False)
    try:
        contained = os.path.commonpath((str(root), str(manifest))) == str(root)
    except ValueError:
        contained = False
    if not contained or not manifest.is_file():
        raise ValueError("project root must contain work/project.json")
    return manifest


def build_snapshot(project_root):
    root = canonical_project_root(project_root)
    project_path = _manifest_path(root)
    resources = [_resource("project", project_path)]
    errors = []
    project = _UNPARSED

    try:
        project = json.loads(project_path.read_bytes().decode("utf-8"))
    except UnicodeDecodeError as exc:
        errors.append(f"invalid project JSON: {exc}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid project JSON: {exc}")

    if not isinstance(project, dict):
        if project is not _UNPARSED:
            errors.append("invalid project JSON: root must be an object")
        return _snapshot(resources, errors, {})

    try:
        errors.extend(
            projectlib.validate_project(
                project,
                root,
                check_files=True,
                dependency_mode="allow_stale",
            )
        )
    except (AttributeError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        errors.append(f"project validation failed: {exc}")

    sequences = project.get("sequences")
    if not isinstance(sequences, dict):
        sequences = {}
    active_sequence = project.get("active_sequence")
    sequence = (
        sequences.get(active_sequence, {}) if isinstance(active_sequence, str) else {}
    )
    timeline_value = sequence.get("timeline") if isinstance(sequence, dict) else None
    timeline = None
    if isinstance(timeline_value, str) and timeline_value.strip():
        _register_path(
            resources,
            errors,
            root,
            timeline_value,
            "timeline",
            owner=active_sequence,
        )
        try:
            timeline = json.loads(_contained_path(root, timeline_value).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            timeline = None

    operations = project.get("operations")
    if not isinstance(operations, list):
        operations = []
    reviews = project.get("reviews")
    if not isinstance(reviews, list):
        reviews = []
    nodes = [*operations, *reviews]
    for node in nodes:
        if not isinstance(node, dict):
            continue
        plan = node.get("plan")
        if plan is None:
            continue
        if not isinstance(plan, str) or not plan.strip():
            node_id = node.get("id") or "<missing-id>"
            errors.append(f"{node_id} plan must be a nonblank string")
            continue
        _register_path(
            resources,
            errors,
            root,
            plan,
            "plan",
            owner=str(node.get("id", "")),
            operation_id=str(node.get("id", "")),
        )

    view = {
        "schema_version": project.get("schema_version"),
        "project_id": project.get("project_id"),
        "project_revision": project.get("revision", 1),
        "active_sequence": project.get("active_sequence"),
        "operation_count": len(operations),
        "review_count": len(reviews),
        "operations": [_node_view(node) for node in operations if isinstance(node, dict)],
        "reviews": [_node_view(node) for node in reviews if isinstance(node, dict)],
    }
    source_media_id = _source_media_id(root, project_path, project)
    if source_media_id:
        view["source_media_id"] = source_media_id
    source_media = _source_media_view(root, project)
    if source_media:
        view["source_media"] = source_media
        view["sequence_geometry"] = {
            "width": source_media["width"],
            "height": source_media["height"],
        }
    if isinstance(timeline, dict):
        clips = timeline.get("clips") if isinstance(timeline.get("clips"), list) else []
        fps = timeline.get("fps") if isinstance(timeline.get("fps"), dict) else {}
        view["timeline"] = {
            "duration_s": timeline.get("program_duration_s", 0),
            "fps": {"num": fps.get("num", 30), "den": fps.get("den", 1)},
            "clips": [
                {
                    "id": clip.get("id"),
                    "source_range": clip.get("source_range"),
                    "program_range": clip.get("program_range"),
                    "speed": clip.get("speed"),
                }
                for clip in clips if isinstance(clip, dict)
            ],
        }
    cards = next((node for node in operations if isinstance(node, dict) and node.get("id") == "content-cards"), None)
    if cards and isinstance(cards.get("plan"), str):
        try:
            cards_plan = json.loads(_contained_path(root, cards["plan"]).read_text(encoding="utf-8"))
            edit_model = _content_cards_edit_model(cards_plan)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            edit_model = None
        if edit_model:
            view["content_cards_edit"] = edit_model
    captions = next((node for node in operations if isinstance(node, dict) and node.get("id") == "captions"), None)
    if captions and isinstance(captions.get("plan"), str):
        try:
            captions_plan = json.loads(_contained_path(root, captions["plan"]).read_text(encoding="utf-8"))
            edit_model = _captions_edit_model(captions_plan)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            edit_model = None
        if edit_model:
            view["captions_edit"] = edit_model
    graphic_motion = next((node for node in operations if isinstance(node, dict) and node.get("id") == "graphic-motion"), None)
    if graphic_motion and isinstance(graphic_motion.get("plan"), str):
        try:
            motion_plan = json.loads(_contained_path(root, graphic_motion["plan"]).read_text(encoding="utf-8"))
            edit_model = _graphic_motion_edit_model(motion_plan)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            edit_model = None
        if edit_model:
            view["graphic_motion_edit"] = edit_model
    snapshot = _snapshot(resources, _unique(errors), view)
    snapshot["snapshot_etag"] = _snapshot_binding(project, snapshot["resources"])
    return snapshot


def load_resource(project_root, resource):
    root = canonical_project_root(project_root)
    path = _contained_path(root, resource["value"])
    data = path.read_bytes()
    return {
        "id": resource["id"],
        "kind": resource["kind"],
        "etag": hashlib.sha256(data).hexdigest(),
        "content": json.loads(data.decode("utf-8")),
    }


def _register_path(resources, errors, root, value, kind, owner="", **metadata):
    try:
        path = _contained_path(root, value)
    except (OSError, TypeError, ValueError) as exc:
        errors.append(str(exc))
        return
    if not path.is_file():
        return
    resources.append(_resource(kind, path, owner=owner, value=value, **metadata))


def _contained_path(root, value):
    return projectlib.resolve_project_path(root, value)


def _resource(kind, path, owner="", value=None, **metadata):
    item = {
        "id": resource_id(kind, owner),
        "kind": kind,
        "etag": file_etag(path),
        "size": path.stat().st_size,
        "_value": value if value is not None else str(path),
    }
    item.update(metadata)
    return item


def _snapshot(resources, errors, view):
    public_resources = []
    registry = {}
    for resource in resources:
        public = {key: value for key, value in resource.items() if not key.startswith("_")}
        public_resources.append(public)
        registry[resource["id"]] = {
            "id": resource["id"],
            "kind": resource["kind"],
            "value": resource["_value"],
        }
    return {
        "read_only": bool(errors),
        "errors": errors,
        "view": view,
        "resources": public_resources,
        "_registry": registry,
    }


def _source_media_id(root, project_path, project):
    source = project.get("source")
    value = source.get("path") if isinstance(source, dict) else None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        path = (project_path.parent / value).resolve(strict=True)
        if os.path.commonpath((str(root), str(path))) != str(root) or not path.is_file():
            return None
        relative = path.relative_to(root).as_posix()
    except (OSError, ValueError):
        return None
    return "asset_" + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:24]


def _source_media_view(root, project):
    operations = project.get("operations")
    if not isinstance(operations, list):
        return None
    understanding = next((
        item for item in operations
        if isinstance(item, dict)
        and (item.get("id") == "understanding" or item.get("skill") == "video-understand")
        and item.get("status") == "verified"
    ), None)
    outputs = understanding.get("outputs") if isinstance(understanding, dict) else None
    media_value = next((
        value for value in outputs or []
        if isinstance(value, str) and value.replace("\\", "/").endswith("/media.json")
    ), None)
    if not media_value:
        return None
    try:
        media = json.loads(_contained_path(root, media_value).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(media, dict):
        return None
    width = media.get("width")
    height = media.get("height")
    duration = media.get("duration_s")
    if (not isinstance(width, int) or isinstance(width, bool) or width <= 0
            or not isinstance(height, int) or isinstance(height, bool) or height <= 0
            or not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration < 0):
        return None
    source = project.get("source")
    source_value = source.get("path") if isinstance(source, dict) else None
    name = Path(source_value).name if isinstance(source_value, str) and source_value.strip() else "Unknown media"
    streams = media.get("streams") if isinstance(media.get("streams"), list) else []
    return {
        "name": name,
        "duration_s": duration,
        "width": width,
        "height": height,
        "has_video": any(isinstance(stream, dict) and stream.get("codec_type") == "video" for stream in streams),
        "has_audio": any(isinstance(stream, dict) and stream.get("codec_type") == "audio" for stream in streams),
    }


def _unique(values):
    return list(dict.fromkeys(values))


def _node_view(node):
    item = {
        "id": node.get("id"),
        "revision": node.get("revision"),
        "status": node.get("status"),
        "etag": hashlib.sha256(
            json.dumps(node, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    if "target" in node:
        item["target"] = node.get("target")
    if isinstance(node.get("plan"), str) and node["plan"].strip():
        item["plan_resource_id"] = resource_id("plan", str(node.get("id", "")))
    for field in ("based_on", "snapshot_etag", "evidence_hashes", "decision_mode", "rationale"):
        if field in node:
            item[field] = node[field]
    return item


def _snapshot_binding(project, resources):
    stable_project = dict(project)
    stable_project["reviews"] = []
    value = json.dumps(
        {
            "project": stable_project,
            "resources": [item["etag"] for item in resources if item.get("kind") != "project"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _content_cards_edit_model(plan):
    cards = plan.get("cards")
    if not isinstance(cards, list) or not cards:
        return None
    entries = []
    for card in cards:
        if not isinstance(card, dict) or not isinstance(card.get("id"), str):
            return None
        copy = card.get("copy") if isinstance(card.get("copy"), dict) else {}
        placement = card.get("placement") if isinstance(card.get("placement"), dict) else {}
        treatment = card.get("visual_treatment") if isinstance(card.get("visual_treatment"), dict) else {}
        entry = {
            "id": card["id"], "selected": True,
            "copy": copy.get("text") or copy.get("suggested_text") or "",
            "placement": placement.get("region") or "bottom",
            "visual_treatment": treatment.get("layout") or "default",
            "card_type": card.get("card_type"),
            "enabled": True,
            "program_range": {
                "start_s": card.get("program_start_s", 0),
                "end_s": card.get("program_start_s", 0) + card.get("duration_s", 0),
            },
        }
        if "data" in card:
            entry["data"] = card["data"]
        entries.append(entry)
    first = entries[0]
    return {
        "fields": {"copy": first["copy"], "layout": first["visual_treatment"],
                   "placement": first["placement"], "enabled": first["selected"]},
        "review_template": {"schema_version": 1, "cards": entries},
        "cues": [
            {
                "id": entry["id"],
                "card_type": entry["card_type"],
                "copy": entry["copy"],
                "layout": entry["visual_treatment"],
                "placement": entry["placement"],
                "enabled": entry["enabled"],
                "program_range": entry["program_range"],
                **({"data": entry["data"]} if "data" in entry else {}),
            }
            for entry in entries
        ],
    }


def _captions_edit_model(plan):
    if not isinstance(plan, dict):
        return None
    cues = plan.get("cues")
    if not isinstance(cues, list):
        return None
    entries = []
    for position, cue in enumerate(cues, 1):
        if not isinstance(cue, dict):
            return None
        cue_id = cue.get("id") or f"cue-{position:03d}"
        program_range = cue.get("program_range") if isinstance(cue.get("program_range"), dict) else {
            "start_s": cue.get("start"), "end_s": cue.get("end"),
        }
        if not isinstance(cue_id, str) or not isinstance(cue.get("text", ""), str):
            return None
        entries.append({
            "id": cue_id,
            "index": cue.get("index", position),
            "text": cue.get("text", ""),
            "program_range": program_range,
            "source_ranges": cue.get("source_ranges", []),
        })
    return {"style": copy_json(plan.get("style", {})), "cues": entries}


def _graphic_motion_edit_model(plan):
    if not isinstance(plan, dict):
        return None
    cues = plan.get("cues")
    if not isinstance(cues, list):
        return None
    entries = []
    for cue in cues:
        if not isinstance(cue, dict) or not isinstance(cue.get("id"), str):
            return None
        intent = cue.get("intent") if isinstance(cue.get("intent"), dict) else {}
        selection = cue.get("selection") if isinstance(cue.get("selection"), dict) else {}
        recipe = cue.get("recipe") if isinstance(cue.get("recipe"), dict) else {}
        review = cue.get("review") if isinstance(cue.get("review"), dict) else {}
        entries.append({
            "id": cue["id"],
            "status": cue.get("status"),
            "enabled": cue.get("status") == "verified",
            "program_range": cue.get("program_range"),
            "content": intent.get("content", ""),
            "recipe_id": recipe.get("id") or selection.get("chosen_recipe_id"),
            "review_status": review.get("status"),
            "review_mode": review.get("mode"),
            "source_status": "bound" if recipe.get("manifest") and recipe.get("files") else "missing",
            "license_status": "unknown" if recipe.get("manifest") and recipe.get("files") else "missing",
        })
    return {"cues": entries}


def copy_json(value):
    return json.loads(json.dumps(value))
