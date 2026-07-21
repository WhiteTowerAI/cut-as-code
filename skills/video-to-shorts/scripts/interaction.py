#!/usr/bin/env python3
"""Open and answer the fixed human-review interviews for video-to-shorts."""

import argparse
from pathlib import Path

from review_gate import (
    answer_candidate_review,
    answer_candidate_review_agent,
    answer_vertical_review,
    answer_vertical_review_agent,
    open_candidate_review,
)
from transcript_utils import load_json


def response_text(args):
    if args.response is not None:
        return args.response
    return Path(args.response_file).read_text(encoding="utf-8-sig")


def run_candidate_open(args):
    review_path, question_path = open_candidate_review(
        args.out, decision_mode=args.decision_mode, delegation_note=args.delegation_note,
        review_out=args.review_out,
    )
    print(f"[video-to-shorts] candidate review: {review_path}")
    if args.review_out:
        print(f"[video-to-shorts] authoritative page: {load_json(review_path)['artifacts']['candidate_review_page']['path']}")
    print(f"[video-to-shorts] fixed question: {question_path}")
    print("[video-to-shorts] STOP: show the question to the user and end the current turn")


def run_candidate_answer(args):
    review = answer_candidate_review(args.out, response_text(args))
    print(f"[video-to-shorts] candidate review status: {review['status']}")
    if review["status"] == "approved":
        print(f"[video-to-shorts] selection mode: {review['decision']['selection_mode']}")
        print(f"[video-to-shorts] delivery mode: {review['decision']['delivery_mode']}")
    else:
        print("[video-to-shorts] STOP: candidate changes were requested; do not generate a plan")


def run_vertical_answer(args):
    review = answer_vertical_review(args.out, response_text(args))
    print(f"[video-to-shorts] vertical review status: {review['status']}")
    if review["status"] != "approved":
        print("[video-to-shorts] STOP: final vertical rendering is not approved")


def run_candidate_agent_approve(args):
    selected = [value.strip() for value in args.candidates.split(",") if value.strip()]
    review = answer_candidate_review_agent(
        args.out, selected, args.delivery, args.rationale
    )
    print(f"[video-to-shorts] candidate review status: {review['status']}")
    print(f"[video-to-shorts] delivery mode: {review['decision']['delivery_mode']}")


def run_vertical_agent_approve(args):
    review = answer_vertical_review_agent(args.out, args.rationale)
    print(f"[video-to-shorts] vertical review status: {review['status']}")


def add_response_arguments(parser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--response", help="Verbatim later user response.")
    group.add_argument("--response-file", help="UTF-8 file containing the verbatim later user response.")


def build_parser():
    parser = argparse.ArgumentParser(description="Manage mandatory video-to-shorts user interviews.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    candidate_open = subparsers.add_parser("candidate-open", help="Open the candidate interview and emit its fixed question.")
    candidate_open.add_argument("--out", required=True)
    candidate_open.add_argument("--decision-mode", choices=("human", "agent"), default="human")
    candidate_open.add_argument("--delegation-note")
    candidate_open.add_argument("--review-out", help="Build and bind an immutable visual candidate review page.")
    candidate_open.set_defaults(func=run_candidate_open)

    candidate_answer = subparsers.add_parser("candidate-answer", help="Record and validate the later candidate-review user response.")
    candidate_answer.add_argument("--out", required=True)
    add_response_arguments(candidate_answer)
    candidate_answer.set_defaults(func=run_candidate_answer)

    vertical_answer = subparsers.add_parser("vertical-answer", help="Record and validate the later vertical-preview user response.")
    vertical_answer.add_argument("--out", required=True)
    add_response_arguments(vertical_answer)
    vertical_answer.set_defaults(func=run_vertical_answer)

    candidate_agent = subparsers.add_parser(
        "candidate-agent-approve", help="Record an explicitly delegated candidate decision."
    )
    candidate_agent.add_argument("--out", required=True)
    candidate_agent.add_argument("--candidates", required=True)
    candidate_agent.add_argument(
        "--delivery", required=True,
        choices=("horizontal_only", "horizontal_and_vertical"),
    )
    candidate_agent.add_argument("--rationale", required=True)
    candidate_agent.set_defaults(func=run_candidate_agent_approve)

    vertical_agent = subparsers.add_parser(
        "vertical-agent-approve", help="Record an explicitly delegated vertical-preview decision."
    )
    vertical_agent.add_argument("--out", required=True)
    vertical_agent.add_argument("--rationale", required=True)
    vertical_agent.set_defaults(func=run_vertical_agent_approve)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
