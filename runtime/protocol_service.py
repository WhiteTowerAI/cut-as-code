"""Fixed JSON-line RPC for read-only editor protocol access."""

import json
import sys
import uuid

from project_snapshot import build_snapshot, canonical_project_root, load_resource


class ProtocolService:
    def __init__(self):
        self._projects = {}

    def handle_request(self, request):
        if not isinstance(request, dict):
            return {"ok": False, "error": "request must be an object"}
        verb = request.get("verb")
        if verb == "open_project":
            return self._open_project(request)
        if verb == "get_snapshot":
            return self._get_snapshot(request)
        if verb == "get_resource":
            return self._get_resource(request)
        return {"ok": False, "error": "unknown verb"}

    def _open_project(self, request):
        try:
            root = canonical_project_root(request.get("project_root", ""))
        except (OSError, TypeError, ValueError):
            return {
                "ok": False,
                "error": "project root must contain work/project.json",
            }
        project_id = "project_" + uuid.uuid4().hex
        self._projects[project_id] = root
        return {
            "ok": True,
            "project_id": project_id,
            "snapshot": self._public_snapshot(build_snapshot(root)),
        }

    def _get_snapshot(self, request):
        root = self._projects.get(request.get("project_id"))
        if root is None:
            return {"ok": False, "error": "unknown project_id"}
        return {"ok": True, "snapshot": self._public_snapshot(build_snapshot(root))}

    def _get_resource(self, request):
        root = self._projects.get(request.get("project_id"))
        if root is None:
            return {"ok": False, "error": "unknown project_id"}
        snapshot = build_snapshot(root)
        resource = snapshot["_registry"].get(request.get("resource_id"))
        if resource is None:
            return {"ok": False, "error": "unknown resource_id"}
        try:
            content = load_resource(root, resource)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return {"ok": False, "error": f"invalid resource: {exc}"}
        return {"ok": True, "resource": content}

    @staticmethod
    def _public_snapshot(snapshot):
        return {key: value for key, value in snapshot.items() if not key.startswith("_")}


def main():
    service = ProtocolService()
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"ok": False, "error": f"invalid request JSON: {exc}"}
        else:
            response = service.handle_request(request)
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
