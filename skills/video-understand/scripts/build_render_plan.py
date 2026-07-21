"""Compile work/project.json into the configured work/render/render-plan.json."""

import argparse
from pathlib import Path

import projectlib


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root")
    parser.add_argument("--project", default="work/project.json")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    project_path = Path(args.project)
    if not project_path.is_absolute():
        project_path = root / project_path
    project = projectlib.load_json(project_path)
    plan = projectlib.build_render_plan(project, root)
    output = (
        Path(args.output).resolve()
        if args.output
        else projectlib.resolve_project_path(root, project["render"]["plan"])
    )
    projectlib.write_json(output, plan)
    print(f"[render-plan] {len(plan['contributions'])} contributions -> {output}")


if __name__ == "__main__":
    main()
