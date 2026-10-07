"""Reconcile legacy editor-made timeline changes without reviving stale state."""

import argparse
import json
import sys
from pathlib import Path

from protocol_service import ProtocolService


def timeline_read_set(snapshot):
    resources = snapshot["resources"]
    project = next(item for item in resources if item["kind"] == "project")
    timeline = next(item for item in resources if item["kind"] == "timeline")
    cut = next(item for item in snapshot["view"]["operations"] if item["id"] == "cut")
    plans = {
        item["operation_id"]: item["etag"]
        for item in resources
        if item["kind"] == "plan" and item.get("operation_id")
    }
    return {
        "project": project["etag"],
        "operation": cut["etag"],
        "timeline": timeline["etag"],
        "plans": plans,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate or apply deterministic reconciliation for legacy manual timeline edits."
    )
    parser.add_argument("project_root", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the reconciled project and render plan after strict validation.",
    )
    args = parser.parse_args(argv)

    service = ProtocolService()
    opened = service.handle_request({
        "verb": "open_project",
        "project_root": str(args.project_root.resolve()),
    })
    if not opened.get("ok"):
        print(json.dumps(opened, ensure_ascii=False, indent=2))
        return 1
    snapshot = opened["snapshot"]
    stale = [
        item["id"] for item in [
            *snapshot.get("view", {}).get("operations", []),
            *snapshot.get("view", {}).get("reviews", []),
        ]
        if item.get("status") == "stale"
    ]
    if not args.apply:
        print(json.dumps({
            "ok": not snapshot.get("read_only"),
            "mode": "check",
            "read_only": snapshot.get("read_only"),
            "errors": snapshot.get("errors", []),
            "stale_nodes": stale,
            "would_reconcile": bool(stale),
        }, ensure_ascii=False, indent=2))
        return 0 if not snapshot.get("read_only") else 1

    result = service.handle_request({
        "verb": "timeline.reconcile-manual",
        "project_id": opened["project_id"],
        "read_set": timeline_read_set(snapshot),
        "acknowledge_manual_edits": True,
    })
    result_snapshot = result.get("snapshot") or snapshot
    print(json.dumps({
        "ok": result.get("ok", False),
        "result": result.get("result"),
        "error": result.get("error"),
        "remaining_errors": result_snapshot.get("errors", []),
        "remaining_stale_nodes": [
            item["id"] for item in [
                *result_snapshot.get("view", {}).get("operations", []),
                *result_snapshot.get("view", {}).get("reviews", []),
            ]
            if item.get("status") == "stale"
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
