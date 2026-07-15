import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(relative_path, module_name=None):
    path = ROOT / relative_path
    name = module_name or path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def timeline_fixture():
    return {
        "schema_version": 1,
        "timeline_id": "main",
        "source_asset_id": "source",
        "fps": {"num": 30, "den": 1},
        "source_duration_s": 6.0,
        "program_duration_s": 3.0,
        "clips": [
            {
                "id": "clip-001",
                "source_range": {"start_s": 0.0, "end_s": 2.0},
                "program_range": {"start_s": 0.0, "end_s": 2.0},
                "speed": 1.0,
                "decision_ref": "edit-001",
            },
            {
                "id": "clip-002",
                "source_range": {"start_s": 4.0, "end_s": 6.0},
                "program_range": {"start_s": 2.0, "end_s": 3.0},
                "speed": 2.0,
                "decision_ref": "edit-002",
            },
        ],
    }


def project_fixture(root):
    return {
        "schema_version": 1,
        "project_id": "fixture",
        "source": {
            "path": "../input/source.mp4",
            "fingerprint": {
                "size": 1,
                "modified_ns": 1,
                "duration_s": 6.0,
            },
        },
        "active_sequence": "main",
        "sequences": {
            "main": {
                "operations": ["rough-cut", "content-cards"],
                "timeline": "timeline.json",
            }
        },
        "operations": [
            {
                "id": "understanding",
                "skill": "video-understand",
                "revision": 1,
                "depends_on": [],
                "based_on": {},
                "status": "verified",
                "plan": None,
                "outputs": [],
            },
            {
                "id": "rough-cut",
                "skill": "video-rough-cut",
                "revision": 2,
                "depends_on": ["understanding"],
                "based_on": {"understanding": 1},
                "status": "verified",
                "plan": "rough-cut/edit-plan.json",
                "outputs": ["timeline.json"],
                "render": {
                    "kind": "timeline-transform",
                    "input": "../input/source.mp4",
                },
            },
            {
                "id": "content-cards",
                "skill": "video-add-content-cards",
                "revision": 1,
                "depends_on": ["rough-cut"],
                "based_on": {"rough-cut": 2},
                "status": "approved",
                "plan": "content-cards/cards-plan.json",
                "outputs": ["cache/content-cards-overlay.mov"],
                "render": {
                    "kind": "overlay",
                    "asset": "cache/content-cards-overlay.mov",
                },
            },
        ],
        "render": {
            "plan": "render/render-plan.json",
            "output": "../final/final.mp4",
            "status": "draft",
        },
        "reviews": [],
    }


def ffprobe_json(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,width,height,duration:format=duration", "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)
