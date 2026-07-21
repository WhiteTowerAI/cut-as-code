#!/usr/bin/env python3
"""Compile a canonical Open Recut timeline from a legacy or canonical edit plan."""

import argparse

import projectlib


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("edit")
    parser.add_argument("output")
    parser.add_argument("--fps-num", type=int, required=True)
    parser.add_argument("--fps-den", type=int, default=1)
    parser.add_argument("--timeline-id", default="main")
    args = parser.parse_args()

    edit = projectlib.load_json(args.edit)
    timeline = projectlib.timeline_from_edit(
        edit,
        fps={"num": args.fps_num, "den": args.fps_den},
        timeline_id=args.timeline_id,
    )
    projectlib.write_json(args.output, timeline)
    print(
        f"[timeline] {len(timeline['clips'])} clips, "
        f"{timeline['program_duration_s']:.3f}s -> {args.output}"
    )


if __name__ == "__main__":
    main()
