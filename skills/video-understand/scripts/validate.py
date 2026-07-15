"""Validate canonical project, timeline, and understanding JSON files."""

import argparse
import sys

from projectlib import load_json, validate_project, validate_timeline, validate_understanding


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="kind", required=True)

    project = subparsers.add_parser("project")
    project.add_argument("file")
    project.add_argument("project_root")

    timeline = subparsers.add_parser("timeline")
    timeline.add_argument("file")

    understanding = subparsers.add_parser("understanding")
    understanding.add_argument("file")
    understanding.add_argument("transcript")

    args = parser.parse_args(argv)
    if args.kind == "project":
        errors = validate_project(
            load_json(args.file), args.project_root, check_files=True, check_media=True
        )
    elif args.kind == "timeline":
        errors = validate_timeline(load_json(args.file))
    else:
        errors = validate_understanding(load_json(args.file), load_json(args.transcript))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
