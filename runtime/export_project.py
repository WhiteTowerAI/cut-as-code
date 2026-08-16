"""Compile and render one Project Protocol V1 delivery from a fixed project root."""

import json
import os
import sys
import traceback
import uuid
from pathlib import Path


def _dependencies():
    scripts = Path(__file__).resolve().parents[1] / "skills" / "video-understand" / "scripts"
    sys.path.insert(0, str(scripts))
    import projectlib
    import render_project
    return projectlib, render_project


def run_export(project_root, *, projectlib=None, renderer=None):
    root = Path(project_root).resolve()
    if projectlib is None or renderer is None:
        projectlib, renderer = _dependencies()
    project_path = root / "work" / "project.json"
    project = projectlib.load_json(project_path)
    render_config = project.get("render")
    if not isinstance(render_config, dict) or not render_config.get("plan"):
        raise ValueError("project render plan is not configured")

    plan = projectlib.build_render_plan(project, root)
    plan_path = projectlib.resolve_project_path(root, render_config["plan"])
    projectlib.write_json(plan_path, plan)
    output = projectlib.resolve_project_path(root, render_config["output"])
    staging = output.with_name(f".{output.stem}.export-{uuid.uuid4().hex}{output.suffix}")
    render_plan = {
        **plan,
        "output": Path(os.path.relpath(staging, plan_path.parent)).as_posix(),
    }
    try:
        rendered = Path(renderer.render(render_plan, root, plan_path.parent)).resolve()
        if rendered != staging.resolve():
            raise ValueError("renderer returned an unexpected export path")
        staging.replace(output)
    finally:
        staging.unlink(missing_ok=True)
    if hasattr(renderer, "_write_delivery_report"):
        renderer._write_delivery_report(output, root)

    current = projectlib.load_json(project_path)
    current.setdefault("render", {})["status"] = "verified"
    projectlib.write_json(project_path, current)
    if hasattr(projectlib, "write_start_here"):
        projectlib.write_start_here(current, root)

    return {
        "ok": True,
        "output": output.relative_to(root).as_posix(),
        "size": output.stat().st_size,
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: export_project.py PROJECT_ROOT")
    try:
        result = run_export(args[0])
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
        return 1
    print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
