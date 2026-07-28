"""Validate and register source-backed HyperFrames motion overlays."""

import copy
import hashlib
import json
import math
import re
import sys
from datetime import datetime
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image, UnidentifiedImageError


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib


CATALOGS = {"motion-anything", "anime-examples", "uiverse-galaxy", "codrops"}
CATALOG_REPOS = {
    "motion-anything": ("nexu-io", "motion-anything"),
    "anime-examples": ("juliangarnier", "anime"),
    "uiverse-galaxy": ("uiverse-io", "galaxy"),
}
LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0"}
LICENSE_MARKERS = {
    "MIT": (
        "permission is hereby granted, free of charge", 'the software is provided "as is"',
        "without warranty of any kind",
    ),
    "Apache-2.0": (
        "apache license", "version 2.0", "terms and conditions for use, reproduction, and distribution",
    ),
    "BSD-2-Clause": (
        "redistribution and use in source and binary forms", "this list of conditions",
        'this software is provided by the copyright holders and contributors "as is"',
    ),
    "BSD-3-Clause": (
        "redistribution and use in source and binary forms", "this list of conditions", "neither the name",
        'this software is provided by the copyright holders and contributors "as is"',
    ),
    "ISC": (
        "permission to use, copy, modify, and/or distribute", "with or without fee",
        'the software is provided "as is"',
    ),
    "CC0-1.0": ("cc0 1.0 universal", "copyright and related rights", "affirmer"),
}
MOTION_MODELS = {"css", "waapi", "anime", "gsap", "three", "hf-seek"}
CHANGE_CATEGORIES = {"content", "geometry", "transparency", "local-assets", "timing", "seed", "selectors"}
REMOTE_CODE_PATTERN = (
    r"https?://|//[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:[/:]|\b)|\bfetch\s*\(|"
    r"XMLHttpRequest|WebSocket|EventSource|WebTransport|navigator\.sendBeacon\s*\(|"
    r"\bimport\s*\(|(?:window\.)?location(?:\.href)?\s*=|"
    r"(?:window\.)?location\.(?:assign|replace)\s*\(|window\.open\s*\(|<\s*form\b"
)
FORBIDDEN_RUNTIME_CODE = re.compile(
    r"\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|WebTransport|"
    r"navigator\.sendBeacon\s*\(|\bimport\s*\(|(?:window\.)?location(?:\.href)?\s*=|"
    r"(?:window\.)?location\.(?:assign|replace)\s*\(|window\.open\s*\(|<\s*form\b",
    re.IGNORECASE,
)
FORBIDDEN_PORT_CODE = re.compile(
    REMOTE_CODE_PATTERN + r"|requestAnimationFrame\s*\(|performance\.now\s*\(|Date\.now\s*\(|"
    r"setInterval\s*\(|setTimeout\s*\(|Math\.random\s*\(|"
    r"crypto\.(?:getRandomValues|randomUUID)\s*\(|new\s+Date\s*\(|THREE\.Clock\s*\(|"
    r"new\s+(?:Shared)?Worker\s*\(|\bimportScripts\s*\(|\b\w*Worklet\.addModule\s*\(|"
    r"navigator\.(?:credentials|clipboard|serviceWorker)\b|document\.cookie\b|"
    r"\b(?:localStorage|sessionStorage|indexedDB)\b|"
    r":(?:hover|focus(?:-visible|-within)?|active)\b|"
    r"addEventListener\s*\(\s*['\"](?:(?:pointer|mouse|touch)[a-z]*|wheel|scroll|"
    r"click|dblclick|key(?:down|up|press)|input|change|submit)['\"]|"
    r"\bon(?:(?:pointer|mouse|touch)[a-z]*|wheel|scroll|click|dblclick|"
    r"key(?:down|up|press)|input|change|submit)\s*=|"
    r"animation(?:-iteration-count)?\s*:[^;{}]*\binfinite\b",
    re.IGNORECASE,
)
SHA256 = re.compile(r"[0-9a-f]{64}")
REVISION = re.compile(r"[0-9a-f]{7,40}")
LICENSE_NAME = re.compile(r"(?:LICENSE|COPYING|NOTICE)(?:[-._].*)?", re.IGNORECASE)
TEXT_ASSET_SUFFIXES = {".css", ".htm", ".html", ".js", ".json", ".mjs", ".svg"}
REVIEW_IMAGE_KEYS = (
    "source_fidelity", "composite_first", "composite_middle", "composite_last",
)
SNAPSHOT_POSES = ("first-visible", "key-interaction", "final-minus-hold", "final")
RANGE_EPSILON = 1e-6


class _HtmlAssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            name = name.lower()
            if name in {"srcset", "imagesrcset"} and value:
                self.references.extend(
                    candidate.strip().split()[0]
                    for candidate in value.split(",")
                    if candidate.strip()
                )
            elif (
                name in {"src", "href", "poster", "action", "formaction"}
                or (tag.lower() == "object" and name == "data")
            ) and value:
                self.references.append(value)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def active_dependencies(project):
    if not isinstance(project, dict):
        return ["understanding"]
    sequences = project.get("sequences") if isinstance(project.get("sequences"), dict) else {}
    sequence = sequences.get(project.get("active_sequence"), {})
    active = sequence.get("operations", []) if isinstance(sequence, dict) else []
    operations = project.get("operations") if isinstance(project.get("operations"), list) else []
    nodes = {item.get("id"): item for item in operations if isinstance(item, dict)}
    return ["understanding", *[item for item in ("cut", "color-grade", "b-roll") if item in active and item in nodes]]


def _understanding_evidence_valid(media, transcript, analysis):
    duration = _number(media.get("duration_s"))
    fps = media.get("fps") if isinstance(media.get("fps"), dict) else {}
    if (
        media.get("schema_version") != 1
        or duration is None or duration <= 0
        or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (media.get("width"), media.get("height"), fps.get("num"), fps.get("den")))
    ):
        return False
    transcript_duration = _number(transcript.get("duration"))
    segments = transcript.get("segments")
    if transcript_duration is None or transcript_duration < 0 or not isinstance(segments, list):
        return False
    for segment in segments:
        start = _number(segment.get("start")) if isinstance(segment, dict) else None
        end = _number(segment.get("end")) if isinstance(segment, dict) else None
        words = segment.get("words") if isinstance(segment, dict) else None
        if start is None or end is None or start < 0 or end < start or end > transcript_duration or not isinstance(words, list):
            return False
        for word in words:
            word_start = _number(word.get("start")) if isinstance(word, dict) else None
            word_end = _number(word.get("end")) if isinstance(word, dict) else None
            if word_start is None or word_end is None or not _nonblank(word.get("word")) or word_start < start or word_end < word_start or word_end > end:
                return False
    speech = analysis.get("speech")
    moments = analysis.get("moments")
    return (
        analysis.get("schema_version") == 1
        and analysis.get("timeline_id") == "source"
        and isinstance(speech, dict)
        and _number(speech.get("duration_s")) is not None
        and isinstance(moments, list)
        and all(isinstance(item, dict) for item in moments)
    )


def _understanding_operation_valid(operation):
    return (
        isinstance(operation, dict)
        and operation.get("skill") == "video-understand"
        and operation.get("status") == "verified"
        and isinstance(operation.get("check"), dict)
        and operation["check"].get("status") == "pass"
    )


def validate_prerequisite(project_root):
    """Return one actionable error unless video-understand is complete and valid."""
    root = Path(project_root)
    required = [
        "work/project.json",
        "work/understand/media.json",
        "work/understand/transcript.json",
        "work/understand/analysis.json",
        "work/understand/understanding.json",
        "work/timeline.json",
        "review/00-video-understanding/contact-sheet.jpg",
        "review/00-video-understanding/transcript.srt",
        "review/00-video-understanding/video-summary.md",
    ]
    if any(not (root / value).is_file() for value in required):
        return ["finish video-understand first"]
    try:
        project = projectlib.load_json(root / "work/project.json")
        media = projectlib.load_json(root / "work/understand/media.json")
        transcript = projectlib.load_json(root / "work/understand/transcript.json")
        analysis = projectlib.load_json(root / "work/understand/analysis.json")
        understanding = projectlib.load_json(root / "work/understand/understanding.json")
        timeline = projectlib.load_json(root / "work/timeline.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return ["finish video-understand first"]
    if not all(isinstance(value, dict) for value in (project, media, transcript, analysis, understanding, timeline)):
        return ["finish video-understand first"]
    operations = project.get("operations")
    if not isinstance(operations, list) or any(not isinstance(item, dict) for item in operations):
        return ["finish video-understand first"]
    operation = next((item for item in operations if item.get("id") == "understanding"), {})
    try:
        valid = (
            _understanding_operation_valid(operation)
            and not projectlib.validate_project(project, root, check_files=False)
            and not projectlib.validate_understanding(understanding, transcript)
            and not projectlib.validate_timeline(timeline)
            and _understanding_evidence_valid(media, transcript, analysis)
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        valid = False
    return [] if valid else ["finish video-understand first"]


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        value = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _range(value):
    if not isinstance(value, dict):
        return None
    start, end = _number(value.get("start_s")), _number(value.get("end_s"))
    return (start, end) if start is not None and end is not None else None


def _source_ranges_match(declared, program, timeline):
    expected = []
    clips = timeline.get("clips")
    if not isinstance(clips, list):
        return False
    for clip in clips:
        source = _range(clip.get("source_range")) if isinstance(clip, dict) else None
        clip_program = _range(clip.get("program_range")) if isinstance(clip, dict) else None
        speed = _number(clip.get("speed")) if isinstance(clip, dict) else None
        if not source or not clip_program or speed is None or speed <= 0 or not _nonblank(clip.get("id")):
            return False
        start, end = max(program[0], clip_program[0]), min(program[1], clip_program[1])
        if start < end:
            expected.append({
                "clip_id": clip["id"],
                "start_s": source[0] + (start - clip_program[0]) * speed,
                "end_s": source[0] + (end - clip_program[0]) * speed,
            })
    if not isinstance(declared, list) or len(declared) != len(expected):
        return False
    for actual, required in zip(declared, expected):
        value = _range(actual) if isinstance(actual, dict) else None
        if (
            not value
            or actual.get("clip_id") != required["clip_id"]
            or abs(value[0] - required["start_s"]) > RANGE_EPSILON
            or abs(value[1] - required["end_s"]) > RANGE_EPSILON
        ):
            return False
    return True


def _nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def _one_of(value, choices):
    return isinstance(value, str) and value in choices


def _https(value):
    try:
        parsed = urlsplit(value)
    except (TypeError, ValueError):
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)


def _url_path_parts(value):
    try:
        return [unquote(part) for part in urlsplit(value).path.split("/") if part]
    except (TypeError, ValueError):
        return []


def _html_url(value):
    parts = _url_path_parts(value)
    return bool(parts) and Path(parts[-1]).suffix.lower() in {".html", ".htm"}


def _catalog_revision(catalog_id, value):
    """Return the immutable GitHub revision when a URL belongs to its catalog."""
    if not isinstance(catalog_id, str) or not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
    except (TypeError, ValueError):
        return None
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.hostname != "github.com" or len(parts) < 5:
        return None
    if catalog_id == "codrops":
        valid_repo = parts[0].lower() == "codrops"
    else:
        repo = CATALOG_REPOS.get(catalog_id)
        valid_repo = repo is not None and tuple(part.lower() for part in parts[:2]) == repo
    revision = parts[3] if valid_repo and parts[2] == "blob" else None
    return revision if REVISION.fullmatch(str(revision or "")) else None


def _same_catalog_revision(catalog_id, source_url, license_url, revision):
    source_revision = _catalog_revision(catalog_id, source_url)
    license_revision = _catalog_revision(catalog_id, license_url)
    if source_revision is None or source_revision != revision or license_revision != revision:
        return False
    source_parts = _url_path_parts(source_url)
    license_parts = _url_path_parts(license_url)
    return source_parts[:2] == license_parts[:2]


def _motion_anything_license_is_recipe_specific(catalog_id, source_url, license_url):
    if catalog_id != "motion-anything":
        return True
    source_parts = _url_path_parts(source_url)
    license_parts = _url_path_parts(license_url)
    return len(source_parts) > 5 and source_parts[4:-1] == license_parts[4:-1]


def _bound_path(binding, project_root):
    if not isinstance(binding, dict) or not _nonblank(binding.get("path")):
        return None
    root = Path(project_root).resolve()
    try:
        value = Path(binding["path"])
        if value.is_absolute():
            return None
        path = (root / value).resolve()
        path.relative_to(root)
    except (OSError, ValueError, TypeError, RuntimeError):
        return None
    return path


def _asset_references(path, text):
    references = []
    if path.suffix.lower() in {".html", ".htm", ".svg"}:
        parser = _HtmlAssetParser()
        try:
            parser.feed(text)
        except Exception:
            return ["<invalid-markup>"]
        references.extend(parser.references)
    if path.suffix.lower() in {".css", ".html", ".htm", ".svg"}:
        references.extend(re.findall(r"url\([\s\"']*([^\s\"')]+)", text, re.IGNORECASE))
        references.extend(re.findall(
            r"@import\s+(?!url\()[\s\"']*([^\s\"';)]+)", text, re.IGNORECASE,
        ))
    if path.suffix.lower() in {".js", ".mjs", ".html", ".htm"}:
        references.extend(re.findall(
            r"(?:\bimport\s+(?:[^;]*?\s+from\s+)?|\brequire\s*\()[\s\"']*([^\s\"')]+)",
            text,
        ))
        references.extend(re.findall(
            r"(?:\.src|\.href|new\s+URL\s*\()[\s=,\"']+([^\s\"')]+)",
            text,
        ))
        references.extend(re.findall(
            r"(?:new\s+(?:Shared)?Worker|importScripts|"
            r"(?:[A-Za-z_$][\w$]*\.)*[A-Za-z_$][\w$]*Worklet\.addModule)"
            r"\s*\([\s\"']*([^\s\"')]+)",
            text,
        ))
    return references


def _license_matches(path, spdx):
    if not isinstance(spdx, str):
        return False
    try:
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
    except (OSError, UnicodeDecodeError):
        return False
    markers = LICENSE_MARKERS.get(spdx)
    if not markers or not all(marker in text for marker in markers):
        return False
    return spdx != "BSD-2-Clause" or "neither the name" not in text


def _valid_image(path, *, size=None, rgba=False):
    try:
        with Image.open(path) as image:
            image.load()
            if image.format not in {"JPEG", "PNG"}:
                return False, None
            if size is not None and image.size != size:
                return False, None
            if rgba and (image.format != "PNG" or image.mode != "RGBA"):
                return False, None
            alpha = image.getchannel("A").getextrema() if rgba else None
            return True, alpha
    except (OSError, UnidentifiedImageError, ValueError):
        return False, None


def _timestamp(value):
    return _parsed_timestamp(value) is not None


def _parsed_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _binding_errors(binding, label, project_root=None, verify=False, scan_port=False):
    errors = []
    if (
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256"}
        or not _nonblank(binding.get("path"))
        or not SHA256.fullmatch(str(binding.get("sha256", "")))
    ):
        return [f"{label} binding is invalid"]
    if Path(binding["path"]).is_absolute():
        return [f"{label} path must be project-relative"]
    if not verify or project_root is None:
        return errors
    root = Path(project_root).resolve()
    try:
        path = (root / binding["path"]).resolve()
        path.relative_to(root)
    except (OSError, ValueError, TypeError, RuntimeError):
        return [f"{label} path escapes project root"]
    if not path.is_file():
        return [f"{label} file is missing"]
    if sha256_file(path) != binding["sha256"]:
        errors.append(f"{label} SHA-256 is stale")
    if scan_port and path.suffix.lower() in TEXT_ASSET_SUFFIXES:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            errors.append(label.rsplit(" ", 1)[0] + " text asset is not valid UTF-8")
        else:
            if FORBIDDEN_PORT_CODE.search(text):
                errors.append(label.rsplit(" ", 1)[0] + " contains nondeterministic or remote runtime code")
    return errors


def _cue_bindings(cue):
    if not isinstance(cue, dict) or cue.get("status") != "verified":
        return []
    source, port, render, review = (
        cue.get(key) if isinstance(cue.get(key), dict) else {}
        for key in ("source", "port", "render", "review")
    )
    source_files = source.get("files") if isinstance(source.get("files"), list) else []
    port_files = port.get("files") if isinstance(port.get("files"), list) else []
    runtime_assets = port.get("runtime_assets") if isinstance(port.get("runtime_assets"), list) else []
    frames = render.get("frames") if isinstance(render.get("frames"), list) else []
    review_evidence = review.get("evidence") if isinstance(review.get("evidence"), dict) else {}
    snapshots = review_evidence.get("hyperframes_snapshots")
    snapshots = snapshots if isinstance(snapshots, list) else []
    snapshot_files = [
        snapshot.get("file") if isinstance(snapshot, dict) and "file" in snapshot else snapshot
        for snapshot in snapshots
    ]
    return [
        *source_files,
        *port_files,
        port.get("adaptation_patch"),
        *runtime_assets,
        *frames,
        *[review_evidence.get(key) for key in REVIEW_IMAGE_KEYS],
        review_evidence.get("hyperframes_check"),
        *snapshot_files,
        review.get("receipt"),
    ]


def _input_hashes(plan):
    hashes = plan.get("input_hashes") if isinstance(plan, dict) else None
    return hashes if isinstance(hashes, dict) else {}


def _input_bindings(plan):
    hashes = _input_hashes(plan)
    return [
        {"path": "work/timeline.json", "sha256": hashes.get("timeline_sha256")},
        {"path": "work/understand/transcript.json", "sha256": hashes.get("transcript_sha256")},
        {"path": "work/understand/understanding.json", "sha256": hashes.get("understanding_sha256")},
        {"path": "work/understand/media.json", "sha256": hashes.get("media_sha256")},
        {"path": "review/00-video-understanding/contact-sheet.jpg", "sha256": hashes.get("contact_sheet_sha256")},
    ]


def _evidence_errors(cue_id, cue, program, timeline, contact_sheet_sha256, transcript=None):
    evidence = cue.get("evidence")
    if not isinstance(evidence, dict):
        return [f"{cue_id} video evidence is incomplete"]
    words = evidence.get("transcript_words")
    visual_refs = evidence.get("visual_refs")
    errors = []
    if not isinstance(words, list) or not words or not isinstance(visual_refs, list) or not visual_refs:
        return [f"{cue_id} video evidence is incomplete"]
    mapped_words = None
    if transcript is not None:
        try:
            mapped = projectlib.map_transcript_to_timeline(transcript, timeline)
            mapped_words = [
                word
                for segment in mapped.get("segments", [])
                if isinstance(segment, dict)
                for word in segment.get("words", [])
                if isinstance(word, dict)
            ]
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
            mapped_words = []
    for word in words:
        word_range = _range(word.get("program_range")) if isinstance(word, dict) else None
        if (
            not isinstance(word, dict)
            or not word_range
            or (mapped_words is not None and word not in mapped_words)
            or (program and (word_range[0] < program[0] - RANGE_EPSILON or word_range[1] > program[1] + RANGE_EPSILON))
        ):
            errors.append(f"{cue_id} transcript evidence is not mapped from the canonical transcript")
    for ref in visual_refs:
        if (
            not isinstance(ref, dict)
            or ref.get("path") != "review/00-video-understanding/contact-sheet.jpg"
            or ref.get("sha256") != contact_sheet_sha256
            or not _nonblank(ref.get("note"))
        ):
            errors.append(f"{cue_id} visual evidence is not bound to the understanding contact sheet")
    return errors


def _search_errors(cue_id, cue):
    intent = cue.get("intent") if isinstance(cue.get("intent"), dict) else {}
    search = cue.get("search")
    authored_at = _parsed_timestamp(intent.get("authored_at"))
    searched_at = _parsed_timestamp(search.get("searched_at")) if isinstance(search, dict) else None
    errors = []
    if authored_at is None or searched_at is None or searched_at < authored_at:
        errors.append(f"{cue_id} search must happen after motion intent")
    if not isinstance(search, dict):
        return errors + [f"{cue_id} search receipt is incomplete"]
    candidates = search.get("candidates")
    queries = search.get("queries")
    if (
        queries != intent.get("search_queries")
        or not isinstance(candidates, list)
        or not 2 <= len(candidates) <= 3
        or not _nonblank(search.get("selected_candidate_id"))
        or not _nonblank(search.get("selection_rationale"))
    ):
        return errors + [f"{cue_id} search receipt is incomplete"]
    ids = []
    selected = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            errors.append(f"{cue_id} search receipt is incomplete")
            continue
        candidate_id = candidate.get("id")
        if _nonblank(candidate_id):
            ids.append(candidate_id)
        if (
            not _nonblank(candidate_id)
            or not _one_of(candidate.get("catalog_id"), CATALOGS)
            or not _https(candidate.get("url"))
            or _catalog_revision(candidate.get("catalog_id"), candidate.get("url")) is None
            or not _html_url(candidate.get("url"))
            or not _nonblank(candidate.get("license"))
            or not _nonblank(candidate.get("popularity_evidence"))
            or not _one_of(candidate.get("decision"), {"selected", "rejected"})
            or not _nonblank(candidate.get("reason"))
        ):
            errors.append(f"{cue_id} search receipt is incomplete")
        if candidate.get("decision") == "selected":
            selected.append(candidate)
    if (
        len(ids) != len(candidates)
        or len(ids) != len(set(ids))
        or len(selected) != 1
        or selected[0].get("id") != search.get("selected_candidate_id")
    ):
        errors.append(f"{cue_id} search receipt is incomplete")
        return errors
    source = cue.get("source") if isinstance(cue.get("source"), dict) else {}
    chosen = selected[0]
    if any(
        source.get(key) != chosen.get(candidate_key)
        for key, candidate_key in (
            ("candidate_id", "id"),
            ("catalog_id", "catalog_id"),
            ("url", "url"),
            ("license", "license"),
        )
    ):
        errors.append(f"{cue_id} selected source does not match search receipt")
    return errors


def validate_port(cue, project_root):
    """Preflight one frozen port before any browser executes it."""
    if not isinstance(cue, dict) or not _nonblank(cue.get("id")):
        return ["port cue is invalid"]
    cue_id = cue["id"]
    port = cue.get("port")
    if not isinstance(port, dict):
        return [f"{cue_id} port is required"]
    files = port.get("files") if isinstance(port.get("files"), list) else []
    assets = port.get("runtime_assets") if isinstance(port.get("runtime_assets"), list) else []
    bindings = [*files, port.get("adaptation_patch"), *assets]
    errors = []
    for binding in files:
        errors.extend(_binding_errors(binding, f"{cue_id} port file", project_root, True, scan_port=True))
    errors.extend(_binding_errors(port.get("adaptation_patch"), f"{cue_id} adaptation patch", project_root, True))
    for binding in assets:
        errors.extend(_binding_errors(binding, f"{cue_id} runtime asset", project_root, True))

    root = Path(project_root).resolve()
    port_root = (root / f"work/cache/graphic-motion/hyperframes/{cue_id}").resolve()
    declared = set()
    for binding in bindings:
        path = _bound_path(binding, root)
        if path is None:
            continue
        try:
            path.relative_to(port_root)
        except ValueError:
            errors.append(f"{cue_id} port file is outside its cue directory")
            continue
        declared.add(path)
    actual = {path.resolve() for path in port_root.rglob("*") if path.is_file()} if port_root.is_dir() else set()
    if actual != declared:
        errors.append(f"{cue_id} port contains undeclared files")

    for binding, scanner in [
        *((binding, FORBIDDEN_PORT_CODE) for binding in files),
        *((binding, FORBIDDEN_RUNTIME_CODE) for binding in assets),
    ]:
        path = _bound_path(binding, root)
        if path is None or path.suffix.lower() not in TEXT_ASSET_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            errors.append(f"{cue_id} port text asset is not valid UTF-8")
            continue
        if scanner.search(text):
            message = f"{cue_id} port contains nondeterministic or remote runtime code"
            if message not in errors:
                errors.append(message)
        for reference in _asset_references(path, text):
            parsed = urlsplit(reference)
            if reference == "<invalid-markup>" or parsed.scheme or parsed.netloc or reference.startswith("//"):
                errors.append(f"{cue_id} port contains nondeterministic or remote runtime code")
                continue
            if not reference or reference.startswith(("#", "data:", "blob:", "about:")):
                continue
            referenced = (path.parent / unquote(parsed.path)).resolve()
            try:
                referenced.relative_to(port_root)
            except ValueError:
                errors.append(f"{cue_id} port references undeclared assets")
                continue
            if referenced not in declared:
                errors.append(f"{cue_id} port references undeclared assets")
    return list(dict.fromkeys(errors))


def _frame_errors(cue_id, cue, render, program, timeline, project_root, verify_files, media_size):
    if not isinstance(render, dict) or not program:
        return []
    fps = timeline.get("fps") if isinstance(timeline.get("fps"), dict) else {}
    num, den = fps.get("num"), fps.get("den")
    if not isinstance(num, int) or not isinstance(den, int) or num <= 0 or den <= 0:
        return [f"{cue_id} render frames do not match exact frame sequence"]
    duration = Fraction(str(program[1])) - Fraction(str(program[0]))
    expected_count = math.ceil(duration * num / den)
    frames = render.get("frames")
    pattern, start_number = render.get("pattern"), render.get("start_number")
    pattern_valid = isinstance(pattern, str) and re.fullmatch(
        r"[A-Za-z0-9._-]*%0?[1-9][0-9]*d[A-Za-z0-9._-]*", pattern,
    )
    expected_paths = [
        f"work/{render.get('asset')}/{pattern % (start_number + offset)}"
        for offset in range(expected_count)
    ] if pattern_valid and isinstance(start_number, int) and not isinstance(start_number, bool) else []
    actual_paths = [item.get("path") for item in frames if isinstance(item, dict)] if isinstance(frames, list) else []
    errors = []
    if actual_paths != expected_paths:
        errors.append(f"{cue_id} render frames do not match exact frame sequence")
        frames = frames if isinstance(frames, list) else []
    if (
        verify_files
        and project_root is not None
        and pattern_valid
        and render.get("asset") == f"cache/graphic-motion/rendered/{cue_id}"
    ):
        match = re.fullmatch(r"(.*)%0?([1-9][0-9]*)d(.*)", pattern)
        asset_dir = (Path(project_root).resolve() / "work" / str(render.get("asset", ""))).resolve()
        expected_files = {(Path(project_root).resolve() / path).resolve() for path in expected_paths}
        if match and asset_dir.is_dir():
            frame_name = re.compile(
                re.escape(match.group(1)) + rf"\d{{{int(match.group(2))}}}" + re.escape(match.group(3))
            )
            actual_files = {path.resolve() for path in asset_dir.iterdir() if path.is_file() and frame_name.fullmatch(path.name)}
            if actual_files != expected_files:
                errors.append(f"{cue_id} render frames do not match exact frame sequence")
    alpha_min, alpha_max = 255, 0
    for binding in frames:
        errors.extend(_binding_errors(binding, f"{cue_id} render frame", project_root, verify_files))
        if not verify_files or project_root is None:
            continue
        path = _bound_path(binding, project_root)
        valid, alpha = _valid_image(path, size=media_size, rgba=True) if path else (False, None)
        if not valid:
            errors.append(f"{cue_id} render frame is not an RGBA PNG at timeline dimensions")
        elif alpha:
            alpha_min, alpha_max = min(alpha_min, alpha[0]), max(alpha_max, alpha[1])
    intent = cue.get("intent") if isinstance(cue.get("intent"), dict) else {}
    if (
        verify_files
        and intent.get("compositing_mode") == "transparent-overlay"
        and frames
        and not (alpha_min < 255 and alpha_max > 0)
    ):
        errors.append(f"{cue_id} render sequence has no usable alpha")
    return list(dict.fromkeys(errors))


def _review_evidence_errors(
    cue_id, evidence, project_root, verify_files, media_size, duration_s=None,
):
    if not isinstance(evidence, dict) or set(evidence) != {
        *REVIEW_IMAGE_KEYS, "hyperframes_check", "hyperframes_snapshots",
    }:
        return [f"{cue_id} review evidence contract is invalid"]
    snapshots = evidence.get("hyperframes_snapshots")
    if (
        not isinstance(snapshots, list)
        or len(snapshots) != 4
        or any(not isinstance(item, dict) or set(item) != {"pose", "at_s", "file"} for item in snapshots)
    ):
        return [f"{cue_id} review evidence contract is invalid"]
    errors = []
    times = [_number(snapshot.get("at_s")) for snapshot in snapshots]
    if (
        tuple(snapshot.get("pose") for snapshot in snapshots) != SNAPSHOT_POSES
        or duration_s is None
        or any(value is None or value < 0 or value >= duration_s for value in times)
        or any(left >= right for left, right in zip(times, times[1:]))
    ):
        errors.append(f"{cue_id} HyperFrames snapshot poses or times are invalid")
    snapshot_bindings = [snapshot.get("file") for snapshot in snapshots]
    image_bindings = [*[evidence.get(key) for key in REVIEW_IMAGE_KEYS], *snapshot_bindings]
    paths = [binding.get("path") for binding in image_bindings if isinstance(binding, dict)]
    hashes = [binding.get("sha256") for binding in image_bindings if isinstance(binding, dict)]
    if (
        len(paths) != len(image_bindings)
        or any(not _nonblank(value) for value in paths)
        or any(not isinstance(value, str) or not SHA256.fullmatch(value) for value in hashes)
        or len(paths) != len(set(paths))
        or len(hashes) != len(set(hashes))
    ):
        errors.append(f"{cue_id} review visual evidence must use distinct images")
    for index, binding in enumerate(image_bindings):
        errors.extend(_binding_errors(binding, f"{cue_id} review image", project_root, verify_files))
        if verify_files and project_root is not None:
            path = _bound_path(binding, project_root)
            expected_size = media_size if 1 <= index <= 3 else None
            valid, _ = _valid_image(path, size=expected_size) if path else (False, None)
            if not valid:
                errors.append(f"{cue_id} review image is invalid")
    check = evidence.get("hyperframes_check")
    errors.extend(_binding_errors(check, f"{cue_id} HyperFrames check", project_root, verify_files))
    if verify_files and project_root is not None:
        path = _bound_path(check, project_root)
        try:
            report = projectlib.load_json(path) if path else None
        except (OSError, ValueError, json.JSONDecodeError):
            report = None
        if (
            not isinstance(report, dict)
            or report.get("status") != "pass"
            or report.get("composition_id") != cue_id
        ):
            errors.append(f"{cue_id} HyperFrames check receipt is invalid")
    return list(dict.fromkeys(errors))


def validate_plan(plan, timeline, project=None, project_root=None, verify_files=False):
    """Return deterministic plan, provenance, timing, and file-binding errors."""
    errors = []
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    if not isinstance(timeline, dict):
        return ["timeline must be an object"]
    if plan.get("schema_version") != 1:
        errors.append("plan schema_version must be 1")
    if plan.get("timebase") != "program":
        errors.append("plan timebase must be program")
    if plan.get("timeline_id") != timeline.get("timeline_id"):
        errors.append("plan timeline_id does not match timeline")
    if plan.get("program_duration_s") != timeline.get("program_duration_s"):
        errors.append("plan program_duration_s does not match timeline")
    if plan.get("fps") != timeline.get("fps"):
        errors.append("plan fps does not match timeline")

    if project is not None:
        dependencies = active_dependencies(project)
        operations = project.get("operations") if isinstance(project, dict) and isinstance(project.get("operations"), list) else []
        nodes = {item.get("id"): item for item in operations if isinstance(item, dict)}
        expected = {item: nodes.get(item, {}).get("revision") for item in dependencies}
        if not _understanding_operation_valid(nodes.get("understanding")):
            errors.append("finish video-understand first")
        if any(
            isinstance(revision, bool) or not isinstance(revision, int) or revision <= 0
            for revision in expected.values()
        ):
            errors.append("dependency revisions must be positive integers")
        if plan.get("dependencies") != dependencies:
            errors.append("plan dependencies do not match current dependencies")
        if plan.get("based_on") != expected:
            errors.append("plan based_on does not match current revisions")
    decision = plan.get("decision")
    if (
        not isinstance(decision, dict)
        or not _one_of(decision.get("mode"), {"human", "agent"})
        or not _nonblank(decision.get("actor"))
        or not _nonblank(decision.get("rationale"))
        or (decision.get("mode") == "human" and decision.get("explicit_user_action") is not True)
    ):
        errors.append("decision receipt is invalid")

    transcript = None
    media_size = None
    if verify_files and project_root is not None:
        expected_inputs = {
            "timeline_sha256": Path(project_root) / "work/timeline.json",
            "transcript_sha256": Path(project_root) / "work/understand/transcript.json",
            "understanding_sha256": Path(project_root) / "work/understand/understanding.json",
            "media_sha256": Path(project_root) / "work/understand/media.json",
            "contact_sheet_sha256": Path(project_root) / "review/00-video-understanding/contact-sheet.jpg",
        }
        hashes = _input_hashes(plan)
        for key, path in expected_inputs.items():
            if not path.is_file() or hashes.get(key) != sha256_file(path):
                errors.append(f"{key} is stale")
        try:
            transcript = projectlib.load_json(expected_inputs["transcript_sha256"])
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append("canonical transcript is invalid")
        try:
            media = projectlib.load_json(expected_inputs["media_sha256"])
            width, height = media.get("width"), media.get("height")
            if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (width, height)):
                raise ValueError("invalid dimensions")
            media_size = (width, height)
        except (AttributeError, OSError, ValueError, json.JSONDecodeError):
            errors.append("canonical media probe is invalid")
    input_bindings = _input_bindings(plan)
    hashes = _input_hashes(plan)
    for binding in input_bindings:
        errors.extend(_binding_errors(binding, "input evidence", project_root, verify_files))

    cues = plan.get("cues")
    if not isinstance(cues, list):
        return errors + ["cues must be a list"]
    duration = _number(timeline.get("program_duration_s")) or 0
    previous = None
    seen = set()
    collected = []
    for cue in cues:
        if not isinstance(cue, dict):
            errors.append("cue must be an object")
            continue
        cue_id = cue.get("id") if _nonblank(cue.get("id")) else "<missing>"
        if cue_id == "<missing>":
            errors.append("cue id is required")
        elif cue_id in seen:
            errors.append(f"duplicate cue id: {cue_id}")
        seen.add(cue_id)
        program = _range(cue.get("program_range"))
        if not program or program[0] < 0 or program[1] <= program[0] or program[1] > duration:
            errors.append(f"{cue_id} program range is outside timeline")
        elif previous and program[0] < previous[1] - RANGE_EPSILON:
            errors.append(f"{cue_id} program range overlaps {previous[2]}")
        if program:
            previous = (program[0], program[1], cue_id)

        status = cue.get("status")
        if status == "skipped":
            if not _nonblank(cue.get("skip_reason")):
                errors.append(f"{cue_id} skip_reason is required")
            continue
        if status != "verified":
            errors.append(f"{cue_id} status must be skipped or verified")
            continue
        if not program or not _source_ranges_match(cue.get("source_ranges"), program, timeline):
            errors.append(f"{cue_id} source_ranges do not match timeline")
        intent = cue.get("intent")
        if (
            not isinstance(intent, dict)
            or any(not _nonblank(intent.get(key)) for key in (
                "content", "purpose", "motion_family", "interaction_model", "timing_rationale",
            ))
            or not _one_of(intent.get("compositing_mode"), {"transparent-overlay", "opaque-full-frame"})
            or not isinstance(intent.get("search_queries"), list)
            or not intent.get("search_queries")
            or any(not _nonblank(item) for item in intent.get("search_queries", []))
        ):
            errors.append(f"{cue_id} motion intent is incomplete")
        errors.extend(_evidence_errors(
            cue_id,
            cue,
            program,
            timeline,
            hashes.get("contact_sheet_sha256"),
            transcript,
        ))
        errors.extend(_search_errors(cue_id, cue))

        source = cue.get("source")
        if not isinstance(source, dict):
            errors.append(f"{cue_id} source is required")
            source = {}
        if not _one_of(source.get("catalog_id"), CATALOGS):
            errors.append(f"{cue_id} source catalog is not permitted")
        if not _one_of(source.get("license"), LICENSES):
            errors.append(f"{cue_id} source license is not permitted")
        if not _https(source.get("url")) or not _https(source.get("license_url")):
            errors.append(f"{cue_id} source URLs must use HTTPS")
        if not _html_url(source.get("url")):
            errors.append(f"{cue_id} selected source URL must name HTML")
        retrieved_at = _parsed_timestamp(source.get("retrieved_at"))
        revision = source.get("revision")
        if not _nonblank(revision) or not REVISION.fullmatch(revision) or retrieved_at is None:
            errors.append(f"{cue_id} source revision and retrieval time are required")
        if not _same_catalog_revision(
            source.get("catalog_id"), source.get("url"), source.get("license_url"), revision,
        ):
            errors.append(f"{cue_id} source URL does not match its catalog and revision")
        if not _motion_anything_license_is_recipe_specific(
            source.get("catalog_id"), source.get("url"), source.get("license_url"),
        ):
            errors.append(f"{cue_id} motion-anything license must be recipe-specific")
        if not _nonblank(source.get("attribution")):
            errors.append(f"{cue_id} source attribution is required")
        search = cue.get("search") if isinstance(cue.get("search"), dict) else {}
        searched_at = _parsed_timestamp(search.get("searched_at"))
        if retrieved_at is not None and searched_at is not None and retrieved_at < searched_at:
            errors.append(f"{cue_id} source retrieval must happen after search")
        source_files = source.get("files", [])
        if not isinstance(source_files, list) or not source_files:
            errors.append(f"{cue_id} source files are required")
            source_files = []
        elif not any(
            isinstance(binding, dict)
            and Path(str(binding.get("path", ""))).suffix.lower() in {".html", ".htm"}
            for binding in source_files
        ):
            errors.append(f"{cue_id} source requires an HTML entry point")
        for binding in source_files:
            errors.extend(_binding_errors(binding, f"{cue_id} source file", project_root, verify_files))
        if verify_files and project_root is not None:
            root = Path(project_root).resolve()
            source_root = (root / f"work/cache/graphic-motion/source/{cue_id}").resolve()
            declared_source = {_bound_path(binding, root) for binding in source_files}
            declared_source.discard(None)
            if any(
                not path.is_relative_to(source_root)
                for path in declared_source
            ):
                errors.append(f"{cue_id} source file is outside its cue directory")
            actual_source = {
                path.resolve() for path in source_root.rglob("*") if path.is_file()
            } if source_root.is_dir() else set()
            if actual_source != declared_source:
                errors.append(f"{cue_id} source contains undeclared files")
        license_file = source.get("license_file")
        if (
            not isinstance(license_file, dict)
            or license_file not in source_files
            or not LICENSE_NAME.fullmatch(Path(str(license_file.get("path", ""))).name)
        ):
            errors.append(f"{cue_id} frozen license file is required")
        elif verify_files and project_root is not None:
            license_path = _bound_path(license_file, project_root)
            if license_path is None or not _license_matches(license_path, source.get("license")):
                errors.append(f"{cue_id} frozen license does not match declared SPDX license")

        port = cue.get("port")
        if not isinstance(port, dict):
            errors.append(f"{cue_id} port is required")
            port = {}
        if port.get("composition_id") != cue_id or not _one_of(port.get("motion_model"), MOTION_MODELS):
            errors.append(f"{cue_id} port composition or motion model is invalid")
        files = port.get("files", [])
        if not isinstance(files, list) or not files:
            errors.append(f"{cue_id} port files are required")
            files = []
        for binding in files:
            errors.extend(_binding_errors(binding, f"{cue_id} port file"))
        errors.extend(_binding_errors(port.get("adaptation_patch"), f"{cue_id} adaptation patch"))
        categories = port.get("change_categories")
        if not isinstance(categories, list) or not categories or any(not _one_of(item, CHANGE_CATEGORIES) for item in categories):
            errors.append(f"{cue_id} change categories are invalid")
        assets = port.get("runtime_assets", [])
        if not isinstance(assets, list):
            errors.append(f"{cue_id} runtime_assets must be a list")
            assets = []
        for binding in assets:
            errors.extend(_binding_errors(binding, f"{cue_id} runtime asset"))
        if verify_files and project_root is not None:
            errors.extend(validate_port(cue, project_root))

        render = cue.get("render")
        expected_duration = program[1] - program[0] if program else None
        if (
            not isinstance(render, dict)
            or render.get("kind") != "overlay"
            or render.get("asset_type") != "image-sequence"
            or render.get("asset") != f"cache/graphic-motion/rendered/{cue_id}"
            or render.get("fps") != timeline.get("fps")
            or not program
            or render.get("start_s") != program[0]
            or render.get("duration_s") != expected_duration
            or not re.fullmatch(r"[A-Za-z0-9._-]*%0?[1-9][0-9]*d[A-Za-z0-9._-]*", str(render.get("pattern", "")))
            or Path(str(render.get("pattern", ""))).name != render.get("pattern")
            or Path(str(render.get("pattern", ""))).suffix.lower() != ".png"
            or not isinstance(render.get("start_number"), int)
            or isinstance(render.get("start_number"), bool)
            or render.get("start_number", -1) < 0
        ):
            errors.append(f"{cue_id} render contribution is invalid")
        errors.extend(_frame_errors(
            cue_id, cue, render, program, timeline, project_root, verify_files, media_size,
        ))

        review = cue.get("review")
        if (
            not isinstance(review, dict)
            or review.get("status") != "approved"
            or not _one_of(review.get("mode"), {"human", "agent"})
            or not _nonblank(review.get("actor"))
            or not _nonblank(review.get("rationale"))
            or (review.get("mode") == "human" and review.get("explicit_user_action") is not True)
        ):
            errors.append(f"{cue_id} review receipt is invalid")
            review = {}
        evidence = review.get("evidence")
        errors.extend(_review_evidence_errors(
            cue_id, evidence, project_root, verify_files, media_size, expected_duration,
        ))
        receipt_binding = review.get("receipt")
        errors.extend(_binding_errors(receipt_binding, f"{cue_id} review receipt", project_root, verify_files))
        if verify_files and project_root is not None and isinstance(receipt_binding, dict):
            try:
                receipt_path = _bound_path(receipt_binding, project_root)
                receipt = projectlib.load_json(receipt_path) if receipt_path else None
            except (KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
                receipt = None
            authority = ("status", "mode", "actor", "rationale", "explicit_user_action", "evidence")
            if not isinstance(receipt, dict) or any(receipt.get(key) != review.get(key) for key in authority):
                errors.append(f"{cue_id} review receipt authority does not match plan")
        collected.extend(_cue_bindings(cue))

    declared = plan.get("delivery_bindings")
    expected_bindings = [*input_bindings, *collected]
    if not isinstance(declared, list) or declared != expected_bindings:
        errors.append("delivery_bindings do not match verified cues")
    return errors


def _verified_overlays(plan):
    cues = plan.get("cues", []) if isinstance(plan, dict) else []
    overlays = [copy.deepcopy(cue.get("render")) for cue in cues if isinstance(cue, dict) and cue.get("status") == "verified"]
    if any(not isinstance(item, dict) for item in overlays):
        raise ValueError("verified cues require render contributions")
    return overlays


def register_operation(project, plan, timeline, project_root, *, plan_path="graphic-motion/graphic-motion-plan.json"):
    """Register verified cues, or remove the operation for an all-skipped plan."""
    errors = validate_plan(
        plan, timeline, project=project, project_root=project_root, verify_files=True,
    )
    if errors:
        raise ValueError("; ".join(errors))
    result = copy.deepcopy(project)
    if not isinstance(result, dict) or not isinstance(result.get("operations"), list):
        raise ValueError("project operations must be a list")
    dependencies = active_dependencies(result)
    nodes = {item.get("id"): item for item in result["operations"] if isinstance(item, dict)}
    based_on = {item: nodes.get(item, {}).get("revision") for item in dependencies}
    if plan.get("dependencies") != dependencies:
        raise ValueError("plan dependencies do not match current dependencies")
    if plan.get("based_on") != based_on:
        raise ValueError("plan based_on does not match current revisions")
    overlays = _verified_overlays(plan)
    old = [item for item in result["operations"] if isinstance(item, dict) and item.get("id") == "graphic-motion"]
    sequence = result.get("sequences", {}).get(result.get("active_sequence"), {})
    if not isinstance(sequence, dict) or not isinstance(sequence.get("operations"), list):
        raise ValueError("active sequence operations must be a list")
    if not overlays:
        if old:
            result["operations"] = [item for item in result["operations"] if item.get("id") != "graphic-motion"]
            sequence["operations"] = [item for item in sequence["operations"] if item != "graphic-motion"]
            result.setdefault("render", {})["status"] = "draft"
        return result
    common = {
        "id": "graphic-motion",
        "skill": "video-add-graphic-motion",
        "status": "verified",
        "depends_on": dependencies,
        "based_on": based_on,
        "plan": plan_path,
        "plan_sha256": canonical_sha256(plan),
        "delivery_bindings": copy.deepcopy(plan.get("delivery_bindings")),
        "outputs": [item["asset"] for item in overlays],
        "target": {"sequence": result["active_sequence"], "scope": "graphic-motion"},
        "effects": {
            "changes_timeline": False,
            "changes_geometry": False,
            "changes_video_pixels": True,
            "changes_audio": False,
            "adds_track": "graphic-motion",
        },
        "render": overlays,
        "check": {"status": "pass", "report": "../review/04-graphic-motion/graphic-motion-summary.md"},
    }
    expected = {**common, "revision": old[0].get("revision") if len(old) == 1 else None}
    if len(old) == 1 and old[0] == expected and sequence["operations"].count("graphic-motion") == 1:
        return result
    revision = max((item.get("revision", 0) for item in old), default=0) + 1
    result["operations"] = [item for item in result["operations"] if item.get("id") != "graphic-motion"]
    result["operations"].append({**common, "revision": revision})
    ids = [item for item in sequence["operations"] if item != "graphic-motion"]
    anchors = [index for index, item in enumerate(ids) if item in {"cut", "color-grade", "b-roll"}]
    index = anchors[-1] + 1 if anchors else next((i for i, item in enumerate(ids) if item in {"content-cards", "captions"}), len(ids))
    ids.insert(index, "graphic-motion")
    sequence["operations"] = ids
    result.setdefault("render", {})["status"] = "draft"
    return result
