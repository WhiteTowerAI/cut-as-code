"""Machine-enforced human review gates for video-to-shorts."""

import hashlib
import re
import secrets
from datetime import datetime, timezone
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


def load_candidate_sources(out_dir):
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
        if not preview_path.exists():
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


def open_candidate_review(out_dir, decision_mode="human", delegation_note=None):
    root = Path(out_dir).resolve()
    if decision_mode not in ("human", "agent"):
        fail("decision_mode must be human or agent")
    delegation_note = str(delegation_note or "").strip()
    if decision_mode == "agent" and not delegation_note:
        fail("agent decision mode requires a delegation note")
    paths = candidate_review_paths(root)
    loaded = load_candidate_sources(root)
    transcript_path = root / "transcript.json"
    source_values = {str(entry["data"].get("video", {}).get("source", "")).strip() for entry in loaded.values()}
    if len(source_values) != 1 or not next(iter(source_values)):
        fail("the text_visual candidate file must reference a source video")
    source_video = Path(next(iter(source_values))).resolve()
    review = {
        "schema_version": CANDIDATE_REVIEW_SCHEMA,
        "review_id": secrets.token_hex(16),
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
    for label in (
        "source_video", "transcript", "text_visual_candidates", "text_visual_preview", "fixed_question",
    ):
        verify_artifact(artifacts.get(label), label)


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
    requested_change = change_request(response)
    if requested_change:
        review["status"] = "changes_requested"
        review["answered_at"] = utc_now()
        review["user_response"] = response
        review["change_request"] = requested_change
        write_json(paths["review"], review)
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
    if not isinstance(selected_references, list) or not selected_references:
        fail("agent candidate approval requires explicit candidate references")
    valid = {option["reference"] for option in review["candidate_options"]}
    if any(reference not in valid for reference in selected_references):
        fail("agent candidate approval contains an unknown candidate reference")
    loaded = load_candidate_sources(root)
    approved = approved_candidate_payload(
        loaded, review, "explicit_agent_selection", selected_references, delivery_mode
    )
    write_json(paths["approved"], approved)
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
    write_json(paths["review"], review)
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
    approved = load_json(approved_path).get("candidates") or []
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


def open_vertical_review(out_dir, video, plan_path, summary_path, probe_path=None, preview_path=None, contact_path=None):
    root = Path(out_dir).resolve()
    paths = vertical_review_paths(root)
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
    review = {
        "schema_version": VERTICAL_REVIEW_SCHEMA,
        "review_id": secrets.token_hex(16),
        "workflow_root": str(root),
        "candidate_workflow_root": str(workflow_root),
        "candidate_review_id": candidate_review["review_id"],
        "decision_mode": candidate_review.get("decision_mode", "human"),
        "delegation_note": candidate_review.get("delegation_note"),
        "status": "pending",
        "strategy": plan.get("strategy"),
        "opened_at": utc_now(),
        "artifacts": artifacts,
        "question_path": str(paths["question"]),
    }
    paths["dir"].mkdir(parents=True, exist_ok=True)
    write_json(paths["review"], review)
    paths["question"].write_text(vertical_question(review), encoding="utf-8")
    review["artifacts"]["fixed_question"] = artifact(paths["question"])
    write_json(paths["review"], review)
    return paths["review"], paths["question"]


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
    for label, entry in review.get("artifacts", {}).items():
        verify_artifact(entry, label)
    decision = parse_vertical_decision(response)
    if decision == "approve" and review.get("strategy") == "REVIEW_REQUIRED":
        fail("REVIEW_REQUIRED cannot be approved for final rendering")
    review["status"] = {"approve": "approved", "revise": "changes_requested", "skip": "skipped"}[decision]
    review["answered_at"] = utc_now()
    review["user_response"] = response
    review["decision"] = decision
    requested_change = change_request(response)
    if requested_change:
        review["change_request"] = requested_change
    write_json(paths["review"], review)
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
    for label, entry in review.get("artifacts", {}).items():
        verify_artifact(entry, label)
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
    write_json(paths["review"], review)
    return review


def validate_vertical_review(out_dir, video, plan_path):
    root = Path(out_dir).resolve()
    paths = vertical_review_paths(root)
    if not paths["review"].exists():
        fail("vertical preview review required: render --mode preview, show the fixed question, and record the user's later answer")
    review = load_json(paths["review"])
    ensure_review_root(review, root, VERTICAL_REVIEW_SCHEMA)
    if review.get("status") != "approved":
        fail(f"vertical review is not approved; current status: {review.get('status')}")
    for label, entry in review.get("artifacts", {}).items():
        verify_artifact(entry, label)
    if Path(review["artifacts"]["source_video"]["path"]).resolve() != Path(video).resolve():
        fail("vertical approval belongs to a different source video")
    if Path(review["artifacts"]["vertical_plan"]["path"]).resolve() != Path(plan_path).resolve():
        fail("vertical approval belongs to a different plan")
    required = {"preview_video", "preview_contact_sheet", "preview_summary", "media_probe"}
    if not required.issubset(review.get("artifacts", {})):
        fail("vertical approval is missing required preview artifacts")
    _, candidate_review = validate_vertical_delivery_allowed(video)
    if review.get("candidate_review_id") != candidate_review.get("review_id"):
        fail("vertical approval belongs to an older candidate review")
    return review
