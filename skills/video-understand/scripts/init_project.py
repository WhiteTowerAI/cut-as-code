"""Initialize the minimal user-facing and machine-facing Open Recut project."""

import argparse
import shutil
from pathlib import Path

import probe
import projectlib


def _video_summary(media):
    fps = media["fps"]
    audio = next((stream for stream in media["streams"] if stream.get("codec_type") == "audio"), None)
    return "\n".join(
        [
            "# Video understanding",
            "",
            "## Media facts",
            "",
            f"- Duration: {media['duration_s']:.3f} seconds",
            f"- Frame size: {media['width']} x {media['height']}",
            f"- Frame rate: {fps['num']}/{fps['den']}",
            f"- Video codec: {next(stream for stream in media['streams'] if stream.get('codec_type') == 'video').get('codec_name', 'unknown')}",
            f"- Audio: {audio.get('codec_name', 'unknown') if audio else 'none'}",
            "",
            "Transcript, semantic summary, and contact sheet are pending.",
            "",
        ]
    )


def initialize(source, project_root, project_id=None):
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    root = Path(project_root).resolve()
    project_file = root / "work/project.json"
    if project_file.exists():
        raise ValueError(f"project already exists: {project_file}")

    destination = root / "input" / f"original-video{source.suffix.lower()}"
    for directory in (
        destination.parent,
        root / "review/00-video-understanding",
        root / "final",
        root / "work/understand",
        root / "work/cache",
        root / "work/render",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    if source != destination:
        shutil.copy2(source, destination)

    media = probe.probe(destination)
    timeline = projectlib.source_timeline(media["duration_s"], media["fps"])
    project = {
        "schema_version": 1,
        "project_id": project_id or source.stem,
        "source": {
            "path": f"../input/{destination.name}",
            "fingerprint": media["fingerprint"],
        },
        "active_sequence": "main",
        "sequences": {"main": {"operations": [], "timeline": "timeline.json"}},
        "operations": [
            {
                "id": "understanding",
                "skill": "video-understand",
                "revision": 1,
                "depends_on": [],
                "based_on": {},
                "status": "draft",
                "plan": None,
                "outputs": [
                    "understand/media.json",
                    "understand/transcript.json",
                    "understand/analysis.json",
                    "understand/understanding.json",
                ],
                "target": {"sequence": "main", "scope": "evidence"},
                "effects": {
                    "changes_timeline": False,
                    "changes_geometry": False,
                    "changes_video_pixels": False,
                    "changes_audio": False,
                    "adds_track": None,
                },
                "check": {
                    "status": "pending",
                    "report": "../review/00-video-understanding/video-summary.md",
                },
            }
        ],
        "render": {
            "plan": "render/render-plan.json",
            "output": "../final/final-video.mp4",
            "status": "draft",
        },
        "reviews": [],
    }
    projectlib.write_json(root / "work/understand/media.json", media)
    projectlib.write_json(root / "work/timeline.json", timeline)
    projectlib.write_json(project_file, project)
    (root / "review/00-video-understanding/video-summary.md").write_text(
        _video_summary(media), encoding="utf-8"
    )
    projectlib.write_start_here(project, root)
    return project


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("project_root")
    parser.add_argument("--project-id")
    args = parser.parse_args(argv)
    initialize(args.source, args.project_root, project_id=args.project_id)
    print(f"[project] initialized {Path(args.project_root).resolve()}")


if __name__ == "__main__":
    main()
