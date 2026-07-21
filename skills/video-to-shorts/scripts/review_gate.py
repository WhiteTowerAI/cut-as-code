"""Machine-enforced human review gates for video-to-shorts."""

import base64
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from transcript_utils import load_json, write_json


CANDIDATE_REVIEW_SCHEMA = "video-to-shorts.candidate-review.v1"
VERTICAL_REVIEW_SCHEMA = "video-to-shorts.vertical-review.v1"
DELIVERY_MODES = {"horizontal_only", "horizontal_and_vertical"}
DEFAULT_SELECTION_WORDS = {
    "default", "skip", "none", "no selection", "默认", "跳过", "不选择", "无选择", "没有选择",
}


def fail(message):
    raise SystemExit(message)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path):
    path = Path(path).resolve()
    if not path.exists():
        fail(f"required review artifact not found: {path}")
    return {"path": str(path), "sha256": sha256_file(path)}


def atomic_write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_copy_alias(source, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{secrets.token_hex(8)}.tmp")
    try:
        shutil.copyfile(source, temporary)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_json_artifact(entry, label, schema=None):
    if not isinstance(entry, dict):
        fail(f"{label} artifact record is invalid")
    path = Path(entry.get("path", "")).resolve()
    try:
        raw = path.read_bytes()
    except OSError as error:
        fail(f"{label} artifact cannot be read: {path}: {error}")
    if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
        fail(f"{label} artifact changed after review opened: {path}")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as error:
        fail(f"{label} artifact is invalid JSON: {path}: {error}")
    if not isinstance(data, dict):
        fail(f"{label} artifact must contain a JSON object: {path}")
    if schema is not None and data.get("schema_version") != schema:
        fail(f"{label} artifact must use {schema}: {path}")
    return path, data


def load_bound_candidate_sources(review):
    path, data = load_json_artifact(
        review.get("artifacts", {}).get("text_visual_candidates"),
        "text_visual candidates", "shorts-candidates.v2",
    )
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or any(
        not isinstance(candidate, dict) or candidate.get("evidence_mode") != "text_visual"
        for candidate in candidates
    ):
        fail(f"text_visual candidates are invalid: {path}")
    return {"text_visual": {"path": path, "preview_path": path.parent / "shorts_candidates_preview.html", "data": data}}


def verify_artifact(entry, label):
    if not isinstance(entry, dict):
        fail(f"{label} artifact record is invalid")
    path = Path(entry.get("path", "")).resolve()
    if not path.exists():
        fail(f"{label} artifact no longer exists: {path}")
    actual = sha256_file(path)
    if actual != entry.get("sha256"):
        fail(f"{label} artifact changed after review opened: {path}")
    return path


def candidate_review_paths(out_dir):
    review_dir = Path(out_dir).resolve() / "review"
    return {
        "dir": review_dir,
        "review": review_dir / "candidate_review.json",
        "question": review_dir / "candidate_review_question.md",
        "approved": review_dir / "approved_candidates.json",
    }


def candidate_sources(out_dir):
    root = Path(out_dir).resolve()
    return {
        "text_visual": root / "preview" / "text_visual" / "shorts_candidates.json",
    }


def load_candidate_sources(out_dir, require_preview=True):
    loaded = {}
    for mode, path in candidate_sources(out_dir).items():
        if not path.exists():
            fail(f"{mode} candidates are required before opening review: {path}")
        data = load_json(path)
        if data.get("schema_version") != "shorts-candidates.v2":
            fail(f"{mode} candidates must use shorts-candidates.v2: {path}")
        candidates = data.get("candidates")
        if not isinstance(candidates, list):
            fail(f"{mode} candidates must contain a candidates array: {path}")
        if any(candidate.get("evidence_mode") != mode for candidate in candidates):
            fail(f"every candidate in {path} must use evidence_mode={mode}")
        preview_path = path.parent / "shorts_candidates_preview.html"
        if require_preview and not preview_path.exists():
            fail(f"{mode} HTML preview is required before opening review: {preview_path}")
        loaded[mode] = {"path": path.resolve(), "preview_path": preview_path.resolve(), "data": data}
    return loaded


def candidate_options(loaded):
    options = []
    for mode in ("text_visual",):
        for candidate in loaded[mode]["data"]["candidates"]:
            candidate_id = str(candidate.get("candidate_id", "")).strip()
            if not candidate_id:
                fail(f"candidate without candidate_id in {loaded[mode]['path']}")
            options.append({
                "reference": f"{mode}/{candidate_id}",
                "evidence_mode": mode,
                "candidate_id": candidate_id,
                "title": str(candidate.get("title", "")).strip(),
                "score": candidate.get("score"),
                "duration": candidate.get("duration"),
            })
    return options


def candidate_question(review):
    if review.get("bound_visual_review"):
        page = review["artifacts"]["candidate_review_page"]["path"]
        lines = [
            "# Shorts Candidate Review Required", "",
            f"Open the bound visual review page: `{page}`", "",
            "The workflow is stopped. Inspect all candidate rows and real start/middle/end frames.", "",
            "For approval, paste the page's exact `Shorts candidate review` summary.",
            "For revision, paste its `Decision: revise` summary with non-empty `Changes`.", "",
        ]
        if review.get("decision_mode") == "agent":
            lines.extend([
                "Delegated Agent approval must use explicit candidate references (1-5), an explicit delivery mode, and a non-empty rationale.", "",
            ])
        lines.extend([
            f"Review ID: `{review['review_id']}`", "",
            "Do not continue until this exact review has been answered.",
        ])
        return "\n".join(lines) + "\n"
    if review.get("decision_mode") == "agent":
        lines = [
            "# Delegated Candidate Review", "",
            "Inspect the candidate JSON and HTML preview, then record explicit candidates, delivery mode, and rationale.",
            "", "| Reference | Score | Duration | Title |", "|---|---:|---:|---|",
        ]
        for option in review["candidate_options"]:
            lines.append(
                f"| `{option['reference']}` | {option['score']} | "
                f"{float(option['duration']):.3f}s | {option['title'].replace('|', '/')} |"
            )
        lines.extend(["", f"Review ID: `{review['review_id']}`", ""])
        return "\n".join(lines)
    lines = [
        "# Candidate Review Required / 候选审核",
        "",
        "The workflow is stopped. The Agent must show this question and end the current turn.",
        "流程已停止。Agent 必须展示本问题并结束当前轮次，不能继续生成计划或提取视频。",
        "",
        "## Required Reply / 必填回复",
        "",
        "Reply with one delivery line and optionally one candidate line:",
        "请回复一行交付模式，并可选择回复一行候选：",
        "",
        "```text",
        "候选: text_visual/cand-001, text_visual/cand-002",
        "交付: horizontal_only",
        "```",
        "",
        "Candidate rules / 候选规则:",
        "",
        "- Omit `候选:` or use `候选: 默认` / `候选: 跳过` to use the five highest-scoring `text_visual` candidates.",
        "- 不写 `候选:`，或回复 `候选: 默认` / `候选: 跳过`，将使用 `text_visual` 得分最高的 5 个候选。",
        "- To request changes without approval, reply `修改: <your request>`.",
        "- 如需修改候选且不批准，回复 `修改: <要求>`。",
        "",
        "Delivery choices / 交付模式:",
        "",
        "- `交付: horizontal_only`",
        "- `交付: horizontal_and_vertical`",
        "",
        "## Candidate References / 候选编号",
        "",
        "| Reference | Score | Duration | Title |",
        "|---|---:|---:|---|",
    ]
    for option in review["candidate_options"]:
        score = "" if option["score"] is None else str(option["score"])
        duration = "" if option["duration"] is None else f"{float(option['duration']):.3f}s"
        title = option["title"].replace("|", "\\|")
        lines.append(f"| `{option['reference']}` | {score} | {duration} | {title} |")
    lines.extend([
        "",
        f"Review ID / 审核 ID: `{review['review_id']}`",
        "",
        "Do not continue until a later user message has been recorded by `interaction.py candidate-answer`.",
    ])
    return "\n".join(lines) + "\n"


def open_candidate_review(out_dir, decision_mode="human", delegation_note=None, review_out=None):
    root = Path(out_dir).resolve()
    if decision_mode not in ("human", "agent"):
        fail("decision_mode must be human or agent")
    delegation_note = str(delegation_note or "").strip()
    if decision_mode == "agent" and not delegation_note:
        fail("agent decision mode requires a delegation note")
    paths = candidate_review_paths(root)
    loaded = load_candidate_sources(root, require_preview=review_out is None)
    transcript_path = root / "transcript.json"
    source_values = {str(entry["data"].get("video", {}).get("source", "")).strip() for entry in loaded.values()}
    if len(source_values) != 1 or not next(iter(source_values)):
        fail("the text_visual candidate file must reference a source video")
    source_video = Path(next(iter(source_values))).resolve()
    if not source_video.is_file():
        fail(f"candidate source video not found: {source_video}")
    if not transcript_path.is_file():
        fail(f"candidate transcript not found: {transcript_path}")
    review_id = secrets.token_hex(16)
    if review_out is not None:
        from build_candidate_review import build_candidate_review

        built = None
        question_path = Path(review_out).resolve() / f"candidates-{review_id}-question.md"
        initial_artifacts = {
            "source_video": artifact(source_video),
            "transcript": artifact(transcript_path),
            "text_visual_candidates": artifact(loaded["text_visual"]["path"]),
        }
        loaded = load_bound_candidate_sources({"artifacts": initial_artifacts})
        try:
            built = build_candidate_review(
                source_video, loaded["text_visual"]["path"], review_out, review_id
            )
            review = {
                "schema_version": CANDIDATE_REVIEW_SCHEMA,
                "review_id": review_id,
                "workflow_root": str(root),
                "decision_mode": decision_mode,
                "delegation_note": delegation_note or None,
                "bound_visual_review": True,
                "status": "pending",
                "opened_at": utc_now(),
                "artifacts": {
                    **initial_artifacts,
                    "candidate_review_page": artifact(built["page"]),
                    "candidate_review_frames": [artifact(frame) for frame in built["frames"]],
                },
                "candidate_options": candidate_options(loaded),
                "question_path": str(question_path),
                "approved_candidates_path": str(paths["approved"]),
            }
            for label, entry in initial_artifacts.items():
                verify_artifact(entry, label)
            question_path.write_text(candidate_question(review), encoding="utf-8")
            review["artifacts"]["fixed_question"] = artifact(question_path)
            atomic_write_json(paths["review"], review)
        except BaseException:
            if question_path.exists():
                question_path.unlink()
            if built:
                if built["page"].exists():
                    built["page"].unlink()
                if built["frames"]:
                    shutil.rmtree(built["frames"][0].parent, ignore_errors=True)
            raise
        try:
            paths["approved"].unlink(missing_ok=True)
        except OSError:
            pass
        try:
            atomic_copy_alias(built["page"], Path(review_out).resolve() / "candidates.html")
        except OSError as error:
            print(
                f"[video-to-shorts] warning: latest alias update failed ({error}); "
                f"authoritative page remains {built['page']}", file=sys.stderr,
            )
        return paths["review"], question_path
    review = {
        "schema_version": CANDIDATE_REVIEW_SCHEMA,
        "review_id": review_id,
        "workflow_root": str(root),
        "decision_mode": decision_mode,
        "delegation_note": delegation_note or None,
        "status": "pending",
        "opened_at": utc_now(),
        "artifacts": {
            "source_video": artifact(source_video),
            "transcript": artifact(transcript_path),
            **{f"{mode}_candidates": artifact(entry["path"]) for mode, entry in loaded.items()},
            **{f"{mode}_preview": artifact(entry["preview_path"]) for mode, entry in loaded.items()},
        },
        "candidate_options": candidate_options(loaded),
        "question_path": str(paths["question"]),
        "approved_candidates_path": str(paths["approved"]),
    }
    paths["dir"].mkdir(parents=True, exist_ok=True)
    write_json(paths["review"], review)
    paths["question"].write_text(candidate_question(review), encoding="utf-8")
    review["artifacts"]["fixed_question"] = artifact(paths["question"])
    write_json(paths["review"], review)
    if paths["approved"].exists():
        paths["approved"].unlink()
    return paths["review"], paths["question"]


def ensure_review_root(review, out_dir, schema):
    if review.get("schema_version") != schema:
        fail(f"review must use {schema}")
    expected = Path(out_dir).resolve()
    actual = Path(review.get("workflow_root", "")).resolve()
    if actual != expected:
        fail(f"review workflow_root does not match --out: {actual} != {expected}")


def require_decision_mode(review, expected):
    actual = review.get("decision_mode", "human")
    if actual != expected:
        command = "agent approval" if actual == "agent" else "human answer"
        fail(f"{actual} decision mode requires {command}")


def verify_candidate_artifacts(review):
    artifacts = review.get("artifacts")
    if not isinstance(artifacts, dict):
        fail("candidate review artifacts are missing")
    labels = ["source_video", "transcript", "text_visual_candidates", "fixed_question"]
    labels.append("candidate_review_page" if review.get("bound_visual_review") else "text_visual_preview")
    for label in labels:
        verify_artifact(artifacts.get(label), label)
    if review.get("bound_visual_review"):
        frames = artifacts.get("candidate_review_frames")
        if not isinstance(frames, list) or not frames:
            fail("candidate review frame artifacts are missing")
        for index, entry in enumerate(frames, 1):
            verify_artifact(entry, f"candidate review frame {index}")


def parse_bound_candidate_response(response, review_id, options):
    lines = [line.strip() for line in str(response).splitlines() if line.strip()]
    if not lines or lines[0].casefold() != "shorts candidate review":
        fail("bound candidate response must begin with `Shorts candidate review`")
    fields = {}
    for line in lines[1:]:
        if ":" not in line:
            fail(f"bound candidate response contains an invalid line: {line}")
        name, value = line.split(":", 1)
        name = name.strip().casefold()
        if name not in {"review", "candidates", "delivery", "decision", "changes"}:
            fail(f"bound candidate response contains an unknown field: {name}")
        if name in fields:
            fail(f"bound candidate response contains a duplicate field: {name}")
        fields[name] = value.strip()
    if fields.get("review") != review_id:
        fail("bound candidate response review ID does not match the pending review")
    if fields.get("decision", "").casefold() == "revise":
        if set(fields) != {"review", "decision", "changes"} or not fields.get("changes"):
            fail("revision requires exactly Review, Decision: revise, and non-empty Changes")
        return {"decision": "revise", "changes": fields["changes"]}
    if set(fields) != {"review", "candidates", "delivery"}:
        fail("approval requires exactly Review, Candidates, and Delivery")
    if fields["delivery"] not in DELIVERY_MODES:
        fail("bound candidate response contains an invalid delivery mode")
    tokens = [token.strip() for token in fields["candidates"].split(",") if token.strip()]
    if not 1 <= len(tokens) <= 5:
        fail("bound candidate approval requires 1-5 candidates")
    if len({token.casefold() for token in tokens}) != len(tokens):
        fail("bound candidate references must be unique")
    known = {option["reference"].casefold(): option["reference"] for option in options}
    unknown = [token for token in tokens if token.casefold() not in known]
    if unknown:
        fail(f"unknown candidate reference: {unknown[0]}")
    return {
        "decision": "approve",
        "selected_references": [known[token.casefold()] for token in tokens],
        "delivery_mode": fields["delivery"],
    }


def parse_delivery_mode(response):
    match = re.search(
        r"(?im)^\s*(?:交付|delivery)\s*[:：]\s*(horizontal_only|horizontal_and_vertical|仅横屏|横屏和竖屏|横屏与竖屏)\s*$",
        response,
    )
    if not match:
        fail("candidate review remains pending: reply with `交付: horizontal_only` or `交付: horizontal_and_vertical`")
    value = match.group(1)
    aliases = {"仅横屏": "horizontal_only", "横屏和竖屏": "horizontal_and_vertical", "横屏与竖屏": "horizontal_and_vertical"}
    return aliases.get(value, value)


def change_request(response):
    match = re.search(r"(?im)^\s*(?:修改|changes?)\s*[:：]\s*(.+?)\s*$", response)
    return match.group(1).strip() if match else None


def parse_candidate_references(response, options):
    match = re.search(r"(?im)^\s*(?:候选|candidates?)\s*[:：]\s*(.*?)\s*$", response)
    if not match or match.group(1).strip().lower() in DEFAULT_SELECTION_WORDS:
        return "default_text_visual_top_five", []
    raw_tokens = [token.strip() for token in re.split(r"[,，;；\s]+", match.group(1)) if token.strip()]
    if not raw_tokens:
        return "default_text_visual_top_five", []
    by_reference = {option["reference"].lower(): option["reference"] for option in options}
    by_id = {}
    for option in options:
        by_id.setdefault(option["candidate_id"].lower(), []).append(option["reference"])
    selected = []
    for token in raw_tokens:
        lowered = token.lower()
        if lowered in by_reference:
            reference = by_reference[lowered]
        elif lowered in by_id and len(by_id[lowered]) == 1:
            reference = by_id[lowered][0]
        elif lowered in by_id:
            fail(f"ambiguous candidate ID `{token}`; use a qualified reference such as text_visual/{token}")
        else:
            fail(f"unknown candidate reference: {token}")
        if reference not in selected:
            selected.append(reference)
    return "explicit_user_selection", selected


def approved_candidate_payload(loaded, review, selection_mode, selected_references, delivery_mode):
    candidate_map = {}
    for mode, entry in loaded.items():
        for candidate in entry["data"]["candidates"]:
            candidate_map[f"{mode}/{candidate['candidate_id']}"] = candidate
    if selection_mode == "default_text_visual_top_five":
        selected_references = [
            option["reference"]
            for option in sorted(
                (item for item in review["candidate_options"] if item["evidence_mode"] == "text_visual"),
                key=lambda item: float(item["score"] or 0),
                reverse=True,
            )[:5]
        ]
    if not selected_references:
        fail("candidate review produced no selectable candidates")
    candidates = [candidate_map[reference] for reference in selected_references]
    source = loaded["text_visual"]["data"]
    return {
        "schema_version": "shorts-candidates.v2",
        "video": source.get("video", {}),
        "transcript": source.get("transcript", {}),
        "producer": {
            "skill": "video-to-shorts",
            "mode": f"{review.get('decision_mode', 'human')}_review_gate",
            "review_id": review["review_id"],
            "created_at": utc_now(),
        },
        "selection": {
            "target_count": len(candidates),
            "evidence_mode": "human_reviewed",
            "selection_mode": selection_mode,
            "delivery_mode": delivery_mode,
            "references": selected_references,
        },
        "candidates": candidates,
    }


def answer_candidate_review(out_dir, response):
    root = Path(out_dir).resolve()
    paths = candidate_review_paths(root)
    if not paths["review"].exists():
        fail(f"candidate review is not open; run interaction.py candidate-open first: {paths['review']}")
    review = load_json(paths["review"])
    ensure_review_root(review, root, CANDIDATE_REVIEW_SCHEMA)
    require_decision_mode(review, "human")
    if review.get("status") != "pending":
        fail(f"candidate review is not pending: {review.get('status')}")
    verify_candidate_artifacts(review)
    if review.get("bound_visual_review"):
        parsed = parse_bound_candidate_response(response, review["review_id"], review["candidate_options"])
        if parsed["decision"] == "revise":
            review["status"] = "changes_requested"
            review["answered_at"] = utc_now()
            review["user_response"] = response
            review["change_request"] = parsed["changes"]
            atomic_write_json(paths["review"], review)
            return review
        loaded = load_bound_candidate_sources(review)
        approved = approved_candidate_payload(
            loaded, review, "explicit_user_selection", parsed["selected_references"], parsed["delivery_mode"]
        )
        atomic_write_json(paths["approved"], approved)
        review["status"] = "approved"
        review["answered_at"] = utc_now()
        review["user_response"] = response
        review["decision"] = {
            "selection_mode": "explicit_user_selection",
            "delivery_mode": parsed["delivery_mode"],
            "selected_references": parsed["selected_references"],
        }
        review["approved_candidates"] = artifact(paths["approved"])
        atomic_write_json(paths["review"], review)
        return review
    requested_change = change_request(response)
    if requested_change:
        review["status"] = "changes_requested"
        review["answered_at"] = utc_now()
        review["user_response"] = response
        review["change_request"] = requested_change
        atomic_write_json(paths["review"], review)
        return review
    delivery_mode = parse_delivery_mode(response)
    selection_mode, selected_references = parse_candidate_references(response, review["candidate_options"])
    loaded = load_candidate_sources(root)
    approved = approved_candidate_payload(loaded, review, selection_mode, selected_references, delivery_mode)
    write_json(paths["approved"], approved)
    review["status"] = "approved"
    review["answered_at"] = utc_now()
    review["user_response"] = response
    review["decision"] = {
        "selection_mode": selection_mode,
        "delivery_mode": delivery_mode,
        "selected_references": approved["selection"]["references"],
    }
    review["approved_candidates"] = artifact(paths["approved"])
    write_json(paths["review"], review)
    return review


def answer_candidate_review_agent(out_dir, selected_references, delivery_mode, rationale):
    root = Path(out_dir).resolve()
    paths = candidate_review_paths(root)
    if not paths["review"].exists():
        fail("candidate review is not open")
    review = load_json(paths["review"])
    ensure_review_root(review, root, CANDIDATE_REVIEW_SCHEMA)
    require_decision_mode(review, "agent")
    if review.get("status") != "pending":
        fail(f"candidate review is not pending: {review.get('status')}")
    verify_candidate_artifacts(review)
    rationale = str(rationale or "").strip()
    if not rationale:
        fail("agent candidate approval requires a rationale")
    if delivery_mode not in DELIVERY_MODES:
        fail("agent candidate approval requires an explicit delivery mode")
    if not isinstance(selected_references, list) or not 1 <= len(selected_references) <= 5:
        fail("agent candidate approval requires 1-5 explicit candidate references")
    if len(set(selected_references)) != len(selected_references):
        fail("agent candidate approval requires unique candidate references")
    valid = {option["reference"] for option in review["candidate_options"]}
    if any(reference not in valid for reference in selected_references):
        fail("agent candidate approval contains an unknown candidate reference")
    loaded = load_bound_candidate_sources(review) if review.get("bound_visual_review") else load_candidate_sources(root)
    approved = approved_candidate_payload(
        loaded, review, "explicit_agent_selection", selected_references, delivery_mode
    )
    atomic_write_json(paths["approved"], approved)
    review["status"] = "approved"
    review["answered_at"] = utc_now()
    review["decision"] = {
        "actor": "agent",
        "selection_mode": "explicit_agent_selection",
        "selection_rationale": rationale,
        "delivery_mode": delivery_mode,
        "selected_references": selected_references,
    }
    review["approved_candidates"] = artifact(paths["approved"])
    atomic_write_json(paths["review"], review)
    return review


def validate_candidate_review(out_dir):
    root = Path(out_dir).resolve()
    paths = candidate_review_paths(root)
    if not paths["review"].exists():
        fail(
            "candidate review required: run interaction.py candidate-open, show the generated question to the user, "
            "end the turn, then record the later user response with interaction.py candidate-answer"
        )
    review = load_json(paths["review"])
    ensure_review_root(review, root, CANDIDATE_REVIEW_SCHEMA)
    if review.get("status") != "approved":
        fail(f"candidate review is not approved; current status: {review.get('status')}")
    verify_candidate_artifacts(review)
    approved_path = verify_artifact(review.get("approved_candidates"), "approved candidates")
    decision = review.get("decision")
    if not isinstance(decision, dict) or decision.get("delivery_mode") not in DELIVERY_MODES:
        fail("candidate review does not contain a valid user-selected delivery mode")
    return review, approved_path


def validate_plan_review(out_dir, plan, video_path=None):
    review, approved_path = validate_candidate_review(out_dir)
    metadata = plan.get("metadata") if isinstance(plan.get("metadata"), dict) else {}
    review_path = candidate_review_paths(out_dir)["review"]
    if plan.get("schema_version") == 1:
        review_id = plan.get("selection", {}).get("review_id")
        review_sha256 = metadata.get("candidate_review_sha256")
        approved_value = metadata.get("approved_candidates_path")
    else:
        gate = metadata.get("human_review") if isinstance(metadata.get("human_review"), dict) else {}
        review_id = gate.get("candidate_review_id")
        review_sha256 = gate.get("candidate_review_sha256")
        approved_value = plan.get("source_candidates", {}).get("path")
    if review_id != review.get("review_id"):
        fail("shorts_plan.json is not bound to the current candidate review")
    if review_sha256 != sha256_file(review_path):
        fail("candidate review changed after shorts_plan.json was generated")
    if Path(approved_value or "").resolve() != approved_path:
        fail("shorts_plan.json does not use the approved candidate file")
    if video_path is not None:
        approved_video = Path(review["artifacts"]["source_video"]["path"]).resolve()
        if Path(video_path).resolve() != approved_video:
            fail("extraction video does not match the user-reviewed source video")
    approved = load_json_artifact(
        review["approved_candidates"], "approved candidates", "shorts-candidates.v2"
    )[1].get("candidates") or []
    approved_keys = {
        (item.get("evidence_mode"), item.get("candidate_id"), item.get("start_time"), item.get("end_time"))
        for item in approved
    }
    for short in plan.get("shorts") or []:
        key = (short.get("evidence_mode"), short.get("candidate_id"), short.get("start_time"), short.get("end_time"))
        if key not in approved_keys:
            fail(f"shorts_plan.json contains an unapproved candidate: {short.get('candidate_id')}")
    return review


def candidate_workflow_root_for_short(video):
    video = Path(video).resolve()
    if video.name.lower() == "source.mp4" and video.parent.name.startswith("short_"):
        return video.parent.parent
    if (
        re.fullmatch(r"short-[0-9]+-horizontal\.mp4", video.name.lower())
        and video.parent.name == "shorts"
        and video.parent.parent.name == "final"
    ):
        return video.parent.parent.parent / "work" / "shorts"
    fail("vertical delivery requires a legacy short source or project final/shorts horizontal output")


def validate_vertical_delivery_allowed(video):
    root = candidate_workflow_root_for_short(video)
    review, _ = validate_candidate_review(root)
    if review["decision"]["delivery_mode"] != "horizontal_and_vertical":
        fail("vertical delivery was not selected by the user during candidate review")
    return root, review


def vertical_review_paths(out_dir):
    review_dir = Path(out_dir).resolve() / "review"
    return {
        "dir": review_dir,
        "review": review_dir / "vertical_review.json",
        "question": review_dir / "vertical_review_question.md",
    }


def vertical_question(review):
    if review.get("decision_mode") == "agent":
        lines = [
            "# Delegated Vertical Preview Review", "",
            "Inspect every preview artifact and validator warning, then record approval with a rationale.",
            "",
        ]
        lines.extend(
            f"- {label}: `{entry['path']}`" for label, entry in review["artifacts"].items()
        )
        lines.extend(["", f"Review ID: `{review['review_id']}`", ""])
        return "\n".join(lines)
    renderable = review["strategy"] != "REVIEW_REQUIRED"
    choices = [
        "- `决定: revise` and optionally `修改: <request>` — request a new plan or preview.",
        "- `决定: skip` — keep the horizontal short and do not render a final vertical video.",
    ]
    if renderable:
        choices.insert(0, "- `决定: approve` — approve this exact preview and plan for final rendering.")
    lines = [
        "# Vertical Preview Review Required / 竖屏预览审核",
        "",
        "The workflow is stopped. The Agent must show this question and end the current turn.",
        "流程已停止。Agent 必须展示本问题并结束当前轮次，不能直接正式渲染。",
        "",
        "Inspect these artifacts / 请检查：",
        "",
    ]
    for label, entry in review["artifacts"].items():
        lines.append(f"- {label}: `{entry['path']}`")
    lines.extend(["", "Reply with exactly one decision / 请明确回复一种决定：", "", *choices, ""])
    if not renderable:
        lines.extend([
            "`REVIEW_REQUIRED` cannot be approved for final rendering. Choose `revise` or `skip`.",
            "`REVIEW_REQUIRED` 不能批准正式渲染，只能选择修改或跳过。",
            "",
        ])
    lines.extend([
        f"Review ID / 审核 ID: `{review['review_id']}`",
        "",
        "Do not continue until a later user message has been recorded by `interaction.py vertical-answer`.",
    ])
    return "\n".join(lines) + "\n"


def _load_current_json(path, label):
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"{label} is invalid JSON: {path}: {error}")
    if not isinstance(data, dict):
        fail(f"{label} must contain a JSON object: {path}")
    return path, data


def snapshot_json_artifact(path, label, schema=None):
    path = Path(path).resolve()
    try:
        raw = path.read_bytes()
    except OSError as error:
        fail(f"{label} cannot be read: {path}: {error}")
    entry = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as error:
        fail(f"{label} is invalid JSON: {path}: {error}")
    if not isinstance(data, dict):
        fail(f"{label} must contain a JSON object: {path}")
    if schema is not None and data.get("schema_version") != schema:
        fail(f"{label} must use {schema}: {path}")
    return path, entry, data, raw


def snapshot_file_artifact(path, label):
    path = Path(path).resolve()
    try:
        raw = path.read_bytes()
    except OSError as error:
        fail(f"{label} cannot be read: {path}: {error}")
    return path, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}, raw


def artifact_from_bytes(path, raw):
    return {"path": str(Path(path).resolve()), "sha256": hashlib.sha256(raw).hexdigest()}


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(f"{label} must be a finite number")
    return float(value)


def _normalize_probe_media(media, label):
    if not isinstance(media, dict):
        fail(f"media probe {label} must be an object")
    streams = media.get("streams")
    if not isinstance(streams, list) or any(not isinstance(stream, dict) for stream in streams):
        fail(f"media probe {label}.streams must be an array of objects")
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video:
        fail(f"media probe {label} has no video stream")
    width, height = video.get("width"), video.get("height")
    if (
        not isinstance(width, int) or isinstance(width, bool) or width <= 0
        or not isinstance(height, int) or isinstance(height, bool) or height <= 0
    ):
        fail(f"media probe {label} has invalid video dimensions")
    fps_value = str(video.get("avg_frame_rate", ""))
    try:
        fps = Fraction(fps_value)
    except (ValueError, ZeroDivisionError):
        fail(f"media probe {label} has invalid FPS")
    if fps <= 0:
        fail(f"media probe {label} has invalid FPS")
    try:
        duration = float(media.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        fail(f"media probe {label} has invalid duration")
    if not math.isfinite(duration) or duration <= 0:
        fail(f"media probe {label} has invalid duration")
    return {
        "width": width,
        "height": height,
        "fps": f"{fps.numerator}/{fps.denominator}",
        "durationS": duration,
        "audio": any(stream.get("codec_type") == "audio" for stream in streams),
    }


def probe_review_media(path, ffprobe=None):
    path = Path(path).resolve()
    tool = ffprobe or shutil.which("ffprobe")
    if not tool:
        fail("ffprobe is required to validate vertical preview media")
    process = subprocess.run([
        tool, "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height,avg_frame_rate,sample_rate,channels",
        "-of", "json", str(path),
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
    if process.returncode != 0:
        fail(f"vertical preview is not decodable by ffprobe: {path}: {process.stderr.strip()}")
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        fail(f"ffprobe returned invalid JSON for vertical preview: {path}: {error}")
    return _normalize_probe_media(payload, "preview video")


def validate_contact_sheet(path):
    from PIL import Image

    path = Path(path).resolve()
    try:
        with Image.open(path) as image:
            width, height = image.size
            image.verify()
    except (OSError, ValueError) as error:
        fail(f"preview contact sheet is not a decodable image: {path}: {error}")
    if width <= 0 or height <= 0:
        fail(f"preview contact sheet has invalid dimensions: {path}")


def validate_preview_media(preview_path, contact_path, bound_output):
    actual = probe_review_media(preview_path)
    if actual["width"] != bound_output["width"] or actual["height"] != bound_output["height"]:
        fail("vertical preview dimensions do not match the bound media probe")
    if Fraction(actual["fps"]) != Fraction(bound_output["fps"]):
        fail("vertical preview FPS does not match the bound media probe")
    if actual["audio"] is not bound_output["audio"]:
        fail("vertical preview audio presence does not match the bound media probe")
    tolerance = max(0.1, 2 / float(Fraction(bound_output["fps"])))
    if abs(actual["durationS"] - bound_output["durationS"]) > tolerance:
        fail("vertical preview duration does not match the bound media probe")
    validate_contact_sheet(contact_path)


def _path_is_within(path, directory):
    try:
        Path(path).resolve().relative_to(Path(directory).resolve())
        return True
    except ValueError:
        return False


def _vertical_page_payload(
    short_id, review_id, plan, probe, preview_path, contact_path, page_dir, allowed_media_dirs,
):
    if plan.get("schema_version") != "video-to-shorts.vertical-plan.v1":
        fail("vertical plan must use video-to-shorts.vertical-plan.v1")
    strategy = plan.get("strategy")
    renderable = plan.get("render_allowed") is True and strategy != "REVIEW_REQUIRED"
    segments = plan.get("segments")
    if not isinstance(segments, list) or not segments:
        fail("vertical plan segments must be a non-empty array")
    normalized_segments = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            fail(f"vertical plan segments[{index}] must be an object")
        start = _finite_number(segment.get("start_time"), f"vertical plan segments[{index}].start_time")
        end = _finite_number(segment.get("end_time"), f"vertical plan segments[{index}].end_time")
        if start < 0 or end <= start:
            fail(f"vertical plan segments[{index}] has an invalid range")
        values = {
            "strategy": segment.get("strategy"),
            "content_type": segment.get("content_type"),
            "reason": segment.get("reason"),
        }
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            fail(f"vertical plan segments[{index}] display fields must be non-empty strings")
        crop_fields = ("crop_x", "crop_y", "crop_width", "crop_height")
        supplied_crop_fields = [name for name in crop_fields if name in segment]
        crop_object = None
        if supplied_crop_fields:
            if len(supplied_crop_fields) != len(crop_fields):
                fail(f"vertical plan segments[{index}] crop requires x, y, width, and height")
            crop_values = {
                "x": _finite_number(segment["crop_x"], f"vertical plan segments[{index}].crop.x"),
                "y": _finite_number(segment["crop_y"], f"vertical plan segments[{index}].crop.y"),
                "width": _finite_number(segment["crop_width"], f"vertical plan segments[{index}].crop.width"),
                "height": _finite_number(segment["crop_height"], f"vertical plan segments[{index}].crop.height"),
            }
            if crop_values["x"] < 0 or crop_values["y"] < 0:
                fail(f"vertical plan segments[{index}] crop x and y must be non-negative")
            if crop_values["width"] <= 0 or crop_values["height"] <= 0:
                fail(f"vertical plan segments[{index}] crop width and height must be positive")
            source_width, source_height = plan.get("source_width"), plan.get("source_height")
            if (
                isinstance(source_width, (int, float)) and not isinstance(source_width, bool)
                and math.isfinite(source_width) and source_width > 0
                and crop_values["x"] + crop_values["width"] > source_width
            ):
                fail(f"vertical plan segments[{index}] crop exceeds source width")
            if (
                isinstance(source_height, (int, float)) and not isinstance(source_height, bool)
                and math.isfinite(source_height) and source_height > 0
                and crop_values["y"] + crop_values["height"] > source_height
            ):
                fail(f"vertical plan segments[{index}] crop exceeds source height")
            crop_object = crop_values
            crop = (
                f"({crop_values['x']:g}, {crop_values['y']:g}) "
                f"{crop_values['width']:g}x{crop_values['height']:g}"
            )
        elif segment["strategy"] == "LETTERBOX":
            crop = "LETTERBOX"
        elif segment["strategy"] == "REVIEW_REQUIRED":
            crop = "REVIEW_REQUIRED"
        else:
            fail(f"vertical plan segments[{index}] is missing crop geometry")
        normalized_segments.append({
            "start": start,
            "end": end,
            "contentType": segment["content_type"],
            "strategy": segment["strategy"],
            "crop": crop_object,
            "cropOrFit": crop,
            "rationale": segment["reason"],
        })
    warnings = plan.get("warnings", []) + plan.get("validator_warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(value, str) for value in warnings):
        fail("vertical plan warnings must be arrays of strings")
    source_probe = _normalize_probe_media(probe.get("source"), "source")
    output_value = probe.get("output")
    output_probe = _normalize_probe_media(output_value, "output") if output_value is not None else None
    if renderable and output_probe is None:
        fail("renderable vertical review requires an output media probe")

    def relative_media(path, label):
        if path is None:
            return None
        path = Path(path).resolve()
        if not path.is_file():
            fail(f"{label} not found: {path}")
        allowed = False
        for directory in allowed_media_dirs:
            try:
                path.relative_to(directory)
                allowed = True
                break
            except ValueError:
                pass
        if not allowed:
            fail(f"{label} must be inside an allowed vertical review directory")
        return os.path.relpath(path, page_dir).replace("\\", "/")

    preview_relative = relative_media(preview_path, "preview video")
    contact_relative = relative_media(contact_path, "preview contact sheet")
    if renderable and (preview_relative is None or contact_relative is None):
        fail("renderable vertical review requires preview and contact-sheet media")
    if not renderable and (preview_relative is not None or contact_relative is not None):
        fail("REVIEW_REQUIRED vertical review must not publish preview media")
    approval_reason = (
        "Approval is unavailable because REVIEW_REQUIRED has no safe deterministic vertical render."
        if not renderable else ""
    )
    return {
        "shortId": short_id,
        "reviewId": review_id,
        "strategy": strategy,
        "renderable": renderable,
        "approvalReason": approval_reason,
        "previewPath": preview_relative,
        "contactPath": contact_relative,
        "segments": normalized_segments,
        "probe": {"source": source_probe, "output": output_probe},
        "warnings": warnings,
    }


def _publish_text_once(path, text_value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        temporary.write_text(text_value, encoding="utf-8")
        try:
            os.link(temporary, path)
        except FileExistsError:
            fail(f"authoritative vertical review page already exists: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def _bound_vertical_question(review):
    page = review["artifacts"]["vertical_review_page"]["path"]
    lines = [
        "# Shorts Vertical Review Required", "",
        f"Open the bound vertical review page: `{page}`", "",
        "The workflow is stopped. Inspect the complete preview, contact sheet, segment decisions, media probe, and every warning.", "",
        "Paste the page's exact `Shorts vertical review` summary to approve, request revision, or skip vertical delivery.", "",
    ]
    if review.get("decision_mode") == "agent":
        lines.extend([
            "Delegated Agent approval must inspect this same page and record a non-empty rationale.", "",
        ])
    lines.extend([
        f"Short ID: `{review['short_id']}`",
        f"Review ID: `{review['review_id']}`", "",
        "Do not continue until this exact review has been answered.",
    ])
    return "\n".join(lines) + "\n"


def open_vertical_review(
    out_dir, video, plan_path, summary_path, probe_path=None, preview_path=None,
    contact_path=None, review_out=None, short_id=None,
):
    root = Path(out_dir).resolve()
    paths = vertical_review_paths(root)
    if review_out is not None or short_id is not None:
        if review_out is None:
            fail("bound vertical review requires review_out")
        short_id = str(short_id or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", short_id):
            fail("bound vertical review requires a path-safe short_id")
        page_dir = Path(review_out).resolve()
        page_dir.mkdir(parents=True, exist_ok=True)
        plan_path, plan_artifact, plan, _plan_raw = snapshot_json_artifact(
            plan_path, "vertical plan", "video-to-shorts.vertical-plan.v1"
        )
        probe_path, _probe_artifact, probe, probe_raw = snapshot_json_artifact(
            probe_path, "vertical preview probe"
        )
        summary_path, _summary_artifact, summary, summary_raw = snapshot_json_artifact(
            summary_path, "vertical preview summary",
            "video-to-shorts.vertical-preview-summary.v1",
        )
        if summary.get("mode") != "preview" or summary.get("strategy") != plan.get("strategy"):
            fail("vertical preview summary does not match the current plan")
        expected_renderable = plan.get("render_allowed") is True and plan.get("strategy") != "REVIEW_REQUIRED"
        if summary.get("renderable") is not expected_renderable:
            fail("vertical preview summary renderable state does not match the current plan")
        source_media = _normalize_probe_media(probe.get("source"), "source")
        source_rate = Fraction(source_media["fps"])
        from vertical_plan import validate_vertical_plan_data
        validate_vertical_plan_data(plan, video, {
            "width": source_media["width"],
            "height": source_media["height"],
            "duration_s": source_media["durationS"],
            "fps": {"num": source_rate.numerator, "den": source_rate.denominator},
        })
        workflow_root, candidate_review = validate_vertical_delivery_allowed(video)
        review_id = secrets.token_hex(16)
        page_path = page_dir / f"{short_id}-vertical-review-{review_id}.html"
        question_path = page_dir / f"{short_id}-vertical-review-{review_id}-question.md"
        evidence_dir = page_dir / f"{short_id}-vertical-review-assets" / review_id
        allowed_flat_dirs = (page_dir, root / "preview")
        preview_raw = contact_raw = None
        if preview_path is not None:
            preview_path = Path(preview_path).resolve()
            if not any(_path_is_within(preview_path, directory) for directory in allowed_flat_dirs):
                fail("preview video must be inside an allowed vertical review directory")
            _preview_path, _preview_artifact, preview_raw = snapshot_file_artifact(
                preview_path, "preview video"
            )
        if contact_path is not None:
            contact_path = Path(contact_path).resolve()
            if not any(_path_is_within(contact_path, directory) for directory in allowed_flat_dirs):
                fail("preview contact sheet must be inside an allowed vertical review directory")
            _contact_path, _contact_artifact, contact_raw = snapshot_file_artifact(
                contact_path, "preview contact sheet"
            )
        try:
            evidence_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            fail(f"vertical review evidence directory already exists: {evidence_dir}")
        owned = []
        try:
            immutable_summary = evidence_dir / "preview-summary.json"
            immutable_probe = evidence_dir / "media-probe.json"
            immutable_summary.write_bytes(summary_raw)
            immutable_probe.write_bytes(probe_raw)
            immutable_preview = immutable_contact = None
            if preview_raw is not None:
                immutable_preview = evidence_dir / "preview.mp4"
                immutable_preview.write_bytes(preview_raw)
            if contact_raw is not None:
                immutable_contact = evidence_dir / "contact-sheet.jpg"
                immutable_contact.write_bytes(contact_raw)
            initial_artifacts = {
                "source_video": artifact(video),
                "vertical_plan": plan_artifact,
                "preview_summary": artifact_from_bytes(immutable_summary, summary_raw),
                "media_probe": artifact_from_bytes(immutable_probe, probe_raw),
            }
            if immutable_preview is not None:
                initial_artifacts["preview_video"] = artifact_from_bytes(immutable_preview, preview_raw)
            if immutable_contact is not None:
                initial_artifacts["preview_contact_sheet"] = artifact_from_bytes(immutable_contact, contact_raw)
            payload = _vertical_page_payload(
                short_id, review_id, plan, probe, immutable_preview, immutable_contact, page_dir,
                (page_dir,),
            )
            if expected_renderable:
                validate_preview_media(
                    immutable_preview, immutable_contact,
                    _normalize_probe_media(probe.get("output"), "output"),
                )
            template = Path(__file__).resolve().parent.parent / "assets" / "shorts-vertical-review.html"
            try:
                html = template.read_text(encoding="utf-8")
            except OSError as error:
                fail(f"vertical review template cannot be read: {template}: {error}")
            marker = "__SHORTS_VERTICAL_REVIEW_DATA__"
            if html.count(marker) != 1:
                fail(f"vertical review template must contain exactly one {marker} marker")
            encoded = base64.b64encode(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
            _publish_text_once(page_path, html.replace(marker, encoded))
            owned.append(page_path)
            review = {
                "schema_version": VERTICAL_REVIEW_SCHEMA,
                "review_id": review_id,
                "short_id": short_id,
                "workflow_root": str(root),
                "candidate_workflow_root": str(workflow_root),
                "candidate_review_id": candidate_review["review_id"],
                "decision_mode": candidate_review.get("decision_mode", "human"),
                "delegation_note": candidate_review.get("delegation_note"),
                "bound_visual_review": True,
                "status": "pending",
                "strategy": plan.get("strategy"),
                "renderable": payload["renderable"],
                "opened_at": utc_now(),
                "artifacts": {
                    **initial_artifacts,
                    "vertical_review_page": artifact(page_path),
                },
                "question_path": str(question_path),
            }
            _publish_text_once(question_path, _bound_vertical_question(review))
            owned.append(question_path)
            review["artifacts"]["fixed_question"] = artifact(question_path)
            for label, entry in initial_artifacts.items():
                verify_artifact(entry, label)
            atomic_write_json(paths["review"], review)
        except BaseException:
            for path in reversed(owned):
                path.unlink(missing_ok=True)
            shutil.rmtree(evidence_dir, ignore_errors=True)
            raise
        try:
            atomic_copy_alias(page_path, page_dir / f"{short_id}-vertical-review.html")
        except OSError as error:
            print(
                f"[video-to-shorts] warning: latest alias update failed ({error}); "
                f"authoritative page remains {page_path}", file=sys.stderr,
            )
        return paths["review"], question_path, page_path

    plan = load_json(plan_path)
    artifacts = {
        "source_video": artifact(video),
        "vertical_plan": artifact(plan_path),
        "preview_summary": artifact(summary_path),
    }
    if probe_path and Path(probe_path).exists():
        artifacts["media_probe"] = artifact(probe_path)
    if preview_path and Path(preview_path).exists():
        artifacts["preview_video"] = artifact(preview_path)
    if contact_path and Path(contact_path).exists():
        artifacts["preview_contact_sheet"] = artifact(contact_path)
    workflow_root, candidate_review = validate_vertical_delivery_allowed(video)
    review_id = secrets.token_hex(16)
    question_path = paths["dir"] / f"vertical-review-{review_id}-question.md"
    review = {
        "schema_version": VERTICAL_REVIEW_SCHEMA,
        "review_id": review_id,
        "workflow_root": str(root),
        "candidate_workflow_root": str(workflow_root),
        "candidate_review_id": candidate_review["review_id"],
        "decision_mode": candidate_review.get("decision_mode", "human"),
        "delegation_note": candidate_review.get("delegation_note"),
        "status": "pending",
        "strategy": plan.get("strategy"),
        "opened_at": utc_now(),
        "artifacts": artifacts,
        "question_path": str(question_path),
    }
    try:
        _publish_text_once(question_path, vertical_question(review))
        review["artifacts"]["fixed_question"] = artifact(question_path)
        atomic_write_json(paths["review"], review)
    except BaseException:
        question_path.unlink(missing_ok=True)
        raise
    return paths["review"], question_path


def parse_vertical_decision(response):
    match = re.search(r"(?im)^\s*(?:决定|decision)\s*[:：]\s*(approve|revise|skip|批准|修改|跳过)\s*$", response)
    if match:
        aliases = {"批准": "approve", "修改": "revise", "跳过": "skip"}
        return aliases.get(match.group(1), match.group(1))
    stripped = response.strip().lower()
    aliases = {"1": "approve", "2": "revise", "3": "skip", "批准": "approve", "修改": "revise", "跳过": "skip"}
    if stripped in aliases:
        return aliases[stripped]
    if change_request(response):
        return "revise"
    fail("vertical review remains pending: reply with `决定: approve`, `决定: revise`, or `决定: skip`")


def parse_bound_vertical_response(response, short_id, review_id):
    lines = [line.strip() for line in str(response).splitlines() if line.strip()]
    if not lines or lines[0].casefold() != "shorts vertical review":
        fail("bound vertical response must begin with `Shorts vertical review`")
    fields = {}
    for line in lines[1:]:
        if ":" not in line:
            fail(f"bound vertical response contains an invalid line: {line}")
        name, value = line.split(":", 1)
        name = name.strip().casefold()
        if name not in {"short", "review", "decision", "changes"}:
            fail(f"bound vertical response contains an unknown field: {name}")
        if name in fields:
            fail(f"bound vertical response contains a duplicate field: {name}")
        fields[name] = value.strip()
    if fields.get("short") != short_id:
        fail("bound vertical response short ID does not match the pending review")
    if fields.get("review") != review_id:
        fail("bound vertical response review ID does not match the pending review")
    decision = fields.get("decision", "").casefold()
    if decision not in {"approve", "revise", "skip"}:
        fail("bound vertical response decision must be approve, revise, or skip")
    expected = {"short", "review", "decision", "changes"} if decision == "revise" else {
        "short", "review", "decision"
    }
    if set(fields) != expected:
        fail("bound vertical response fields do not match the selected decision")
    if decision == "revise" and not fields["changes"]:
        fail("bound vertical revision requires non-empty Changes")
    parsed = {"decision": decision}
    if decision == "revise":
        parsed["changes"] = fields["changes"]
    return parsed


def verify_vertical_artifacts(review):
    artifacts = review.get("artifacts")
    if not isinstance(artifacts, dict):
        fail("vertical review artifacts are missing")
    required = {"source_video", "vertical_plan", "preview_summary", "fixed_question"}
    if review.get("bound_visual_review"):
        required.update({"media_probe", "vertical_review_page"})
        if review.get("renderable"):
            required.update({"preview_video", "preview_contact_sheet"})
    missing = required - set(artifacts)
    if missing:
        fail(f"vertical review is missing required artifacts: {', '.join(sorted(missing))}")
    for label, entry in artifacts.items():
        verify_artifact(entry, label)


def answer_vertical_review(out_dir, response):
    root = Path(out_dir).resolve()
    paths = vertical_review_paths(root)
    if not paths["review"].exists():
        fail("vertical review is not open; render preview mode first")
    review = load_json(paths["review"])
    ensure_review_root(review, root, VERTICAL_REVIEW_SCHEMA)
    require_decision_mode(review, "human")
    if review.get("status") != "pending":
        fail(f"vertical review is not pending: {review.get('status')}")
    verify_vertical_artifacts(review)
    if review.get("bound_visual_review"):
        parsed = parse_bound_vertical_response(response, review.get("short_id"), review.get("review_id"))
        decision = parsed["decision"]
    else:
        parsed = None
        decision = parse_vertical_decision(response)
    if decision == "approve" and review.get("strategy") == "REVIEW_REQUIRED":
        fail("REVIEW_REQUIRED cannot be approved for final rendering")
    verify_vertical_artifacts(review)
    review["status"] = {"approve": "approved", "revise": "changes_requested", "skip": "skipped"}[decision]
    review["answered_at"] = utc_now()
    review["user_response"] = response
    review["decision"] = decision
    requested_change = parsed.get("changes") if parsed else change_request(response)
    if requested_change:
        review["change_request"] = requested_change
    atomic_write_json(paths["review"], review)
    return review


def answer_vertical_review_agent(out_dir, rationale):
    root = Path(out_dir).resolve()
    paths = vertical_review_paths(root)
    if not paths["review"].exists():
        fail("vertical review is not open; render preview mode first")
    review = load_json(paths["review"])
    ensure_review_root(review, root, VERTICAL_REVIEW_SCHEMA)
    require_decision_mode(review, "agent")
    if review.get("status") != "pending":
        fail(f"vertical review is not pending: {review.get('status')}")
    verify_vertical_artifacts(review)
    if review.get("strategy") == "REVIEW_REQUIRED":
        fail("REVIEW_REQUIRED cannot be approved for final rendering")
    rationale = str(rationale or "").strip()
    if not rationale:
        fail("agent vertical approval requires a rationale")
    review["status"] = "approved"
    review["answered_at"] = utc_now()
    review["decision"] = "approve"
    review["decision_actor"] = "agent"
    review["decision_rationale"] = rationale
    verify_vertical_artifacts(review)
    atomic_write_json(paths["review"], review)
    return review


def load_validated_vertical_review(out_dir, video, plan_path):
    root = Path(out_dir).resolve()
    paths = vertical_review_paths(root)
    if not paths["review"].exists():
        fail("vertical preview review required: render --mode preview, show the fixed question, and record the user's later answer")
    review = load_json(paths["review"])
    ensure_review_root(review, root, VERTICAL_REVIEW_SCHEMA)
    if review.get("status") != "approved":
        fail(f"vertical review is not approved; current status: {review.get('status')}")
    artifacts = review.get("artifacts", {})
    plan_artifact_path, plan = load_json_artifact(
        artifacts.get("vertical_plan"), "vertical plan",
        "video-to-shorts.vertical-plan.v1" if review.get("bound_visual_review") else None,
    )
    for label, entry in artifacts.items():
        if label != "vertical_plan":
            verify_artifact(entry, label)
    if Path(review["artifacts"]["source_video"]["path"]).resolve() != Path(video).resolve():
        fail("vertical approval belongs to a different source video")
    if plan_artifact_path != Path(plan_path).resolve():
        fail("vertical approval belongs to a different plan")
    required = {"preview_video", "preview_contact_sheet", "preview_summary", "media_probe"}
    if not required.issubset(review.get("artifacts", {})):
        fail("vertical approval is missing required preview artifacts")
    _, candidate_review = validate_vertical_delivery_allowed(video)
    if review.get("candidate_review_id") != candidate_review.get("review_id"):
        fail("vertical approval belongs to an older candidate review")
    return review, plan


def validate_vertical_review(out_dir, video, plan_path):
    return load_validated_vertical_review(out_dir, video, plan_path)[0]
