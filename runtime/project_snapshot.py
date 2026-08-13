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
    if isinstance(timeline_value, str) and timeline_value.strip():
        _register_path(
            resources,
            errors,
            root,
            timeline_value,
            "timeline",
            owner=active_sequence,
        )

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
        "active_sequence": project.get("active_sequence"),
        "operation_count": len(operations),
        "review_count": len(reviews),
        "operations": [_node_view(node) for node in operations if isinstance(node, dict)],
        "reviews": [_node_view(node) for node in reviews if isinstance(node, dict)],
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
    return _snapshot(resources, _unique(errors), view)


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
        }
        if "data" in card:
            entry["data"] = card["data"]
        entries.append(entry)
    first = entries[0]
    return {
        "fields": {"copy": first["copy"], "layout": first["visual_treatment"],
                   "placement": first["placement"], "enabled": first["selected"]},
        "review_template": {"schema_version": 1, "cards": entries},
    }
