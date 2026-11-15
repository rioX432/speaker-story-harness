#!/usr/bin/env python3
"""Story-first talk authoring gates. Stdlib-only; meaning is reviewed by an independent AI/human."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_BEAT_FIELDS = ("id", "role", "question", "claim", "why_here", "next_question", "evidence", "minutes")
DECISION_ROLES = ("context", "problem", "baseline", "alternative", "hypothesis", "experiment", "results", "decision")
EVIDENCE_STATUSES = ("confirmed", "limited", "unverified", "hypothesis")
EVIDENCE_KINDS = ("fact", "experiment", "inference", "plan")
CHECK_VERDICTS = ("pass", "partial", "fail", "unknown")
CANDIDATE_ASPECTS = (
    ("audience_problem", "聴講者の問題意識"),
    ("big_idea", "中心的な主張（Big Idea）"),
    ("logic", "課題から技術選択に至る論理"),
    ("key_findings", "重要な発見"),
    ("takeaway_criteria", "聴講者が持ち帰る判断基準"),
    ("failure_risks", "この構成が破綻する可能性"),
)
# Generic wording on purpose: a talk overrides these with brief.review_checks.
DEFAULT_REVIEW_CHECKS = (
    "なぜ提案する技術や変更を検討する必要があるのか説明できているか",
    "既存の手段を改善する選択肢を十分に検討したか",
    "既存の課題と実験・根拠が対応しているか",
    "実験の結果から技術選択の結論が導けるか",
    "冒頭の問いに最後までに答えているか",
    "各章の順番を入れ替えると論証が崩れるか（順番に必然性があるか）",
    "聴講者が翌日から使える知見があるか",
)
DEFAULT_CANDIDATE_CRITERIA = ("内容の正確さ", "話の必然性", "因果関係", "初見での理解", "面白さ")
ROLE_LABELS = {"context": "前提", "problem": "課題", "baseline": "既存手段の改善", "alternative": "代替案",
               "hypothesis": "仮説", "experiment": "検証", "results": "結果", "decision": "判断"}
STATUS_LABELS = {"confirmed": "確認済み", "limited": "条件付き", "unverified": "未検証", "hypothesis": "仮説"}
KIND_LABELS = {"fact": "事実", "experiment": "実験・PoC", "inference": "推測", "plan": "構想"}
VERDICT_LABELS = {"pass": "満たす", "partial": "一部満たす", "fail": "満たさない", "unknown": "判断できない"}
SEVERITY_LABELS = {"critical": "重大", "major": "大", "minor": "小"}
FINDING_STATUS_LABELS = {"open": "未対応", "resolved": "対応済み", "accepted_risk": "リスク受容"}
UNFILLED = "未記入"


def load(path: Path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(project: Path) -> str:
    """Stable identity of what the presenter is approving, independent of formatting."""
    bundle = {p: load(project / p) for p in ("brief.json", "story.json", "evidence.json")}
    return hashlib.sha256(canonical(bundle)).hexdigest()


def candidates_fingerprint(project: Path) -> str | None:
    """Identity of the candidate comparison. Kept apart from fingerprint() so that editing
    rejected candidates neither invalidates an approved story nor changes existing hashes."""
    if not (project / "candidates.json").exists():
        return None
    bundle = {p: load(project / p) for p in ("brief.json", "evidence.json", "candidates.json")}
    return hashlib.sha256(canonical(bundle)).hexdigest()


def filled(value):
    return isinstance(value, str) and bool(value.strip())


def obj(value) -> dict:
    return value if isinstance(value, dict) else {}


def label_of(table: dict, value, fallback: str) -> str:
    # Values come from hand-edited JSON and may be lists or numbers; never use them as dict keys unchecked.
    return table.get(value, value) if isinstance(value, str) and value else fallback


def safe_url(value) -> str | None:
    """Only http(s) evidence URLs become links; anything else (javascript:, data:) stays plain text."""
    if not filled(value):
        return None
    url = value.strip()
    try:
        return url if urlsplit(url).scheme.lower() in ("http", "https") else None
    except ValueError:
        return None


def normalized(value):
    return re.sub(r"\s+", "", str(value)).strip("。？！?!：:")


def text_items(value) -> list[str]:
    """Candidate aspects may be a sentence or a list of sentences."""
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [x for x in value if filled(x)]
    return []


def is_text_or_list(value) -> bool:
    return isinstance(value, str) or (isinstance(value, list) and all(isinstance(x, str) for x in value))


def story_items(project: Path):
    return load(project / "brief.json"), load(project / "story.json"), load(project / "evidence.json")


def review_checks(brief: dict) -> tuple[list[str], bool]:
    checks = brief.get("review_checks")
    if isinstance(checks, list) and checks and all(filled(x) for x in checks):
        return list(checks), True
    return list(DEFAULT_REVIEW_CHECKS), False


def audit_candidates(project: Path, story: dict, errors: list, warnings: list):
    """Returns (candidate list, review state). Absent candidates.json is valid."""
    path = project / "candidates.json"
    if not path.exists():
        if filled(story.get("candidate_id")):
            warnings.append("story.candidate_id is set but candidates.json is absent")
        return [], "none"
    try:
        doc = load(path)
    except (ValueError, json.JSONDecodeError) as e:
        errors.append(f"candidates.json: {e}")
        return [], "none"
    cands = doc.get("candidates") if isinstance(doc, dict) else None
    if not isinstance(cands, list):
        errors.append("candidates.json: candidates must be a list")
        return [], "none"
    ids = []
    for i, c in enumerate(cands):
        if not isinstance(c, dict) or not filled(c.get("id")):
            errors.append(f"candidate {i+1}: needs a nonempty id")
            continue
        if c["id"] in ids:
            errors.append(f"duplicate candidate id: {c['id']}")
        ids.append(c["id"])
        if not filled(c.get("title")):
            warnings.append(f"candidate {c['id']}: missing title")
        for key, _ in CANDIDATE_ASPECTS:
            if key in c and not is_text_or_list(c[key]):
                errors.append(f"candidate {c['id']}: {key} must be text or a list of text")
            elif not text_items(c.get(key)):
                warnings.append(f"candidate {c['id']}: {key} is empty")
    if len(ids) < 2:
        warnings.append("candidates.json has fewer than two candidates to compare")
    rec = doc.get("recommended")
    if filled(rec):
        if rec not in ids:
            errors.append(f"candidates.json: recommended '{rec}' is not a candidate id")
        elif not filled(doc.get("recommendation_reason")):
            warnings.append("candidates.json: recommendation has no reason")
    else:
        warnings.append("candidates.json: no recommended candidate")
    cid = story.get("candidate_id")
    if filled(cid) and cid not in ids:
        errors.append(f"story.candidate_id '{cid}' is not in candidates.json")
    review = load(project / "reviews" / "ai-candidate-review.json", default={})
    if not isinstance(review, dict):
        errors.append("reviews/ai-candidate-review.json must be a JSON object")
        return cands, "missing"
    if not review:
        warnings.append("candidate comparison has no AI review")
        return cands, "missing"
    if review.get("fingerprint") != candidates_fingerprint(project):
        warnings.append("AI candidate review is stale; rerun independent review")
        return cands, "STALE"
    if review.get("reviewer_independent") is not True:
        warnings.append("AI candidate review has no independent-context attestation")
    entries = review.get("candidates", [])
    if not isinstance(entries, list):
        errors.append("AI candidate review candidates must be list")
        return cands, "current"
    reviewed = set()
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("candidate_id"), str) or e["candidate_id"] not in ids:
            errors.append("AI candidate review refers to an unknown candidate")
            continue
        reviewed.add(e["candidate_id"])
        crit = e.get("criteria")
        if crit is not None and (not isinstance(crit, list) or not all(isinstance(x, dict) for x in crit)):
            errors.append(f"AI candidate review {e['candidate_id']}: criteria must be a list of objects")
    for cid in ids:
        if cid not in reviewed:
            warnings.append(f"AI candidate review does not cover candidate {cid}")
    return cands, "current"


def audit_checks(review: dict, expected: list, errors: list, warnings: list):
    checks = review.get("checks")
    # Reviews written before whole-story checks existed have no key; only a review that answers checks must answer all.
    if checks is None:
        return
    if not isinstance(checks, list):
        errors.append("AI review checks must be list")
        return
    seen = set()
    for c in checks:
        if not isinstance(c, dict) or not filled(c.get("check")) or c.get("verdict") not in CHECK_VERDICTS:
            errors.append("AI review check needs check text and verdict pass/partial/fail/unknown")
            continue
        key = normalized(c["check"])
        if key in seen:
            errors.append(f"AI review check answered twice: {c['check']}")
        seen.add(key)
        if not filled(c.get("reason")):
            errors.append(f"AI review check '{c['check']}' needs a reason")
        if c["verdict"] in ("partial", "fail"):
            if not filled(c.get("fix")):
                errors.append(f"AI review check '{c['check']}' needs a concrete fix")
            warnings.append(f"story check not met ({c['verdict']}): {c['check']}")
    for text in expected:
        if normalized(text) not in seen:
            warnings.append(f"story check not answered by AI review: {text}")


def audit(project: Path):
    errors, warnings = [], []
    try:
        brief, story, evidence = story_items(project)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        return {"status": "FAIL", "fingerprint": None, "errors": [str(e)], "warnings": [], "approval": "missing", "semantic_review": "missing"}
    if not isinstance(brief, dict) or not isinstance(story, dict) or not isinstance(evidence, dict):
        errors.append("brief/story/evidence must be JSON objects")
        return {"status": "FAIL", "fingerprint": None, "errors": errors, "warnings": warnings, "approval": "missing", "semantic_review": "missing"}
    sha = fingerprint(project)
    for key in ("title", "audience", "audience_takeaway"):
        if not filled(brief.get(key)):
            errors.append(f"brief.{key} must be provided")
    if not isinstance(brief.get("duration_minutes"), (int, float)) or brief["duration_minutes"] <= 0:
        errors.append("brief.duration_minutes must be positive")
    if "review_checks" in brief and not (isinstance(brief["review_checks"], list) and all(filled(x) for x in brief["review_checks"])):
        errors.append("brief.review_checks must be a list of nonempty strings")
    for key in ("big_idea", "opening_question", "final_answer"):
        if not filled(story.get(key)):
            errors.append(f"story.{key} must be provided")
    beats = story.get("beats", [])
    if not isinstance(beats, list) or len(beats) < 2:
        errors.append("story.beats must contain at least two beats")
        beats = []
    evs = evidence.get("items", [])
    if not isinstance(evs, list):
        errors.append("evidence.items must be a list")
        evs = []
    ev_ids = set()
    for ev in evs:
        if not isinstance(ev, dict) or not filled(ev.get("id")):
            errors.append("every evidence item needs a nonempty id")
            continue
        if ev["id"] in ev_ids:
            errors.append(f"duplicate evidence id: {ev['id']}")
        ev_ids.add(ev["id"])
        if ev.get("status") not in EVIDENCE_STATUSES:
            errors.append(f"evidence {ev['id']}: status must be confirmed/limited/unverified/hypothesis")
        if "kind" in ev and ev["kind"] not in EVIDENCE_KINDS:
            errors.append(f"evidence {ev['id']}: kind must be fact/experiment/inference/plan")
        if "url" in ev and not isinstance(ev["url"], str):
            errors.append(f"evidence {ev['id']}: url must be a string")
        elif filled(ev.get("url")) and safe_url(ev["url"]) is None:
            warnings.append(f"evidence {ev['id']}: url is not http(s); shown as text, not a link")
        if not filled(ev.get("scope")):
            warnings.append(f"evidence {ev['id']}: missing observation scope")
    total, ids, roles = 0.0, set(), []
    for i, b in enumerate(beats):
        if not isinstance(b, dict):
            errors.append(f"beat {i+1}: must be object")
            continue
        for field in REQUIRED_BEAT_FIELDS:
            if field not in b:
                errors.append(f"beat {i+1}: missing {field}")
        bid = b.get("id", f"#{i+1}")
        if not filled(bid):
            errors.append(f"beat {i+1}: empty id")
            continue
        if bid in ids:
            errors.append(f"beat {bid}: duplicate id")
        ids.add(bid)
        roles.append(b.get("role", ""))
        for field in ("question", "claim", "why_here"):
            if not filled(b.get(field)):
                errors.append(f"beat {bid}: empty {field}")
        if i < len(beats) - 1 and not filled(b.get("next_question")):
            errors.append(f"beat {bid}: next question is empty")
        if i > 0 and normalized(b.get("question")) != normalized(beats[i-1].get("next_question")):
            warnings.append(f"flow {beats[i-1].get('id','?')} -> {bid}: next_question and question differ; human must check causality")
        if b.get("from_previous") is not None and not isinstance(b["from_previous"], str):
            errors.append(f"beat {bid}: from_previous must be a string")
        risks = b.get("risks") or []
        if not isinstance(risks, list):
            errors.append(f"beat {bid}: risks must be a list")
        else:
            for r in risks:
                if not isinstance(r, dict) or not filled(r.get("risk")) or not filled(r.get("fix")):
                    errors.append(f"beat {bid}: each risk needs risk and a concrete fix")
        minutes = b.get("minutes")
        if type(minutes) not in (int, float) or minutes <= 0:
            errors.append(f"beat {bid}: invalid minutes")
        else:
            total += minutes
        refs = b.get("evidence", [])
        if not isinstance(refs, list):
            errors.append(f"beat {bid}: evidence must be list")
        else:
            for r in refs:
                if r not in ev_ids:
                    errors.append(f"beat {bid}: unknown evidence id {r}")
        if b.get("role") in ("results", "decision") and not refs:
            warnings.append(f"beat {bid}: result/decision has no evidence reference")
    if type(brief.get("duration_minutes")) in (int, float) and abs(total - brief["duration_minutes"]) > .25:
        warnings.append(f"story duration {total:g} min differs from target {brief['duration_minutes']:g} min")
    if brief.get("talk_type") == "technical_decision":
        for role in ("problem", "baseline", "alternative", "experiment", "decision"):
            if role not in roles:
                warnings.append(f"technical decision story omits '{role}' section: explain why")
        if "experiment" in roles and "problem" in roles and roles.index("experiment") < roles.index("problem"):
            warnings.append("experiment precedes problem definition: solution-first risk")
        if "alternative" in roles and "baseline" in roles and roles.index("alternative") < roles.index("baseline"):
            warnings.append("new technology comes before improvement of existing approach")
    candidates, candidate_review = audit_candidates(project, story, errors, warnings)
    human_path = project / "reviews" / "human-feedback.json"
    human = load(human_path, default={})
    if human and human.get("fingerprint") == sha and not human.get("incorporated", False):
        warnings.append("unincorporated human feedback for current storyboard")
    review = load(project / "reviews" / "ai-story-review.json", default={})
    review_state = "missing"
    if not isinstance(review, dict):
        errors.append("reviews/ai-story-review.json must be a JSON object")
        review = {}
    if review:
        if review.get("fingerprint") != sha:
            review_state = "STALE"
            warnings.append("AI story review is stale; rerun independent review")
        else:
            review_state = "current"
            if review.get("reviewer_independent") is not True:
                warnings.append("AI story review has no independent-context attestation")
            findings = review.get("findings", [])
            if not isinstance(findings, list):
                errors.append("AI review findings must be list")
            else:
                for issue in findings:
                    if not isinstance(issue, dict):
                        errors.append("malformed AI review finding")
                        continue
                    if issue.get("severity") not in ("critical", "major", "minor") or issue.get("status") not in ("open", "resolved", "accepted_risk"):
                        errors.append("AI review issue has invalid severity/status")
                    if not filled(issue.get("reason")) or not filled(issue.get("fix")):
                        errors.append("AI review finding needs reason and actionable fix")
            audit_checks(review, review_checks(brief)[0], errors, warnings)
    else:
        warnings.append("AI semantic review not supplied; textual continuity not verified")
    approval = load(project / "approvals" / "story-approved.json", default={})
    if not approval:
        approval_state = "missing"
    elif approval.get("fingerprint") != sha:
        approval_state = "STALE"
        warnings.append("story approval invalidated by content change")
    else:
        approval_state = "current"
    status = "FAIL" if errors else "UNVERIFIED" if warnings else "PASS"
    return {"status": status, "fingerprint": sha, "errors": errors, "warnings": warnings,
            "approval": approval_state, "semantic_review": review_state,
            "total_minutes": round(total, 2), "beat_count": len(beats),
            "candidates": len(candidates), "candidate_review": candidate_review}


def current_review(project: Path, sha: str) -> dict:
    review = obj(load(project / "reviews" / "ai-story-review.json", default={}))
    return review if review.get("fingerprint") == sha else {}


def review_findings(project: Path, sha: str):
    review = current_review(project, sha)
    if not review:
        return [], False
    return review.get("findings", []), review.get("reviewer_independent") is True


# ---------- storyboard rendering ----------

def esc(value) -> str:
    return html.escape(str(value))


def unfilled_html(what: str = "") -> str:
    return f"<p class='unfilled'>{UNFILLED}{('（' + esc(what) + '）') if what else ''}</p>"


def text_block(value, empty_hint: str = "") -> str:
    items = text_items(value)
    if not items:
        return unfilled_html(empty_hint)
    if isinstance(value, list):
        return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>"
    return f"<p>{esc(items[0])}</p>"


def minutes_label(m) -> str:
    return f"{m:g} 分" if isinstance(m, (int, float)) else UNFILLED


def role_label(role) -> str:
    return label_of(ROLE_LABELS, role, UNFILLED)


def evidence_html(refs, ev_by_id: dict) -> str:
    if not isinstance(refs, list) or not refs:
        return unfilled_html("根拠IDの紐付けなし")
    rows = []
    for r in refs:
        ev = ev_by_id.get(r) if isinstance(r, str) else None
        if ev is None:
            rows.append(f"<li class='ev'><div class='evhead'><code>{esc(r)}</code><span class='tag bad'>台帳に無いID</span></div></li>")
            continue
        kind = ev.get("kind")
        kind_tag = (f"<span class='tag'>{esc(label_of(KIND_LABELS, kind, ''))}</span>" if filled(kind)
                    else "<span class='tag unfilled-tag'>種別: 未記入</span>")
        status = ev.get("status")
        status_tag = f"<span class='tag st-{esc(status)}'>{esc(label_of(STATUS_LABELS, status, '確度: ' + UNFILLED))}</span>"
        source = esc(ev.get("source") or UNFILLED)
        url = safe_url(ev.get("url"))
        if url:
            source += f" <a href='{esc(url)}' rel='noopener noreferrer'>{esc(url)}</a>"
        elif filled(ev.get("url")):
            source += f" <code>{esc(ev['url'])}</code>"
        rows.append(
            f"<li class='ev'><div class='evhead'><code>{esc(r)}</code>{kind_tag}{status_tag}</div>"
            f"<p>{esc(ev.get('summary') or UNFILLED)}</p>"
            f"<p class='evmeta'><b>適用範囲:</b> {esc(ev.get('scope') or UNFILLED)}</p>"
            f"<p class='evmeta'><b>出所:</b> {source}</p></li>")
    return "<ul class='evlist'>" + "".join(rows) + "</ul>"


def finding_html(f: dict) -> str:
    sev = f.get("severity", "minor")
    return (f"<div class='finding {esc(sev)}'><b>AIレビュー・{esc(label_of(SEVERITY_LABELS, sev, ''))}・"
            f"{esc(label_of(FINDING_STATUS_LABELS, f.get('status'), ''))}</b> {esc(f.get('reason', ''))}"
            f"<div class='fix'><b>修正案:</b> {esc(f.get('fix', ''))}</div></div>")


def risks_html(beat: dict, findings: list, review_state: str) -> str:
    out = ["<p class='subhead'>作成者が認識しているリスク</p>"]
    risks = beat.get("risks")
    if isinstance(risks, list) and risks:
        for r in risks:
            if isinstance(r, dict):
                out.append(f"<div class='risk'>{esc(r.get('risk', ''))}<div class='fix'><b>構成修正案:</b> {esc(r.get('fix', ''))}</div></div>")
    else:
        out.append(unfilled_html())
    out.append("<p class='subhead'>AIレビューの指摘</p>")
    if findings:
        out += [finding_html(f) for f in findings]
    elif review_state == "current":
        out.append("<p class='muted'>この章への指摘なし</p>")
    else:
        out.append(f"<p class='muted'>AIレビュー: {esc(review_state_label(review_state))}</p>")
    return "".join(out)


def review_state_label(state: str) -> str:
    return {"current": "最新", "STALE": "古い（本文が変わったため再レビューが必要）", "missing": "未実施", "none": "対象なし"}.get(state, state)


def item(n: int, label: str, body: str, cls: str = "") -> str:
    return f"<div class='item {cls}'><dt><span class='n'>{n}</span>{esc(label)}</dt><dd>{body}</dd></div>"


def beat_card(i: int, b: dict, last: bool, ev_by_id: dict, findings: list, review_state: str) -> str:
    bid = b.get("id", f"#{i}")
    nq = b.get("next_question")
    if filled(nq):
        next_html = f"<p>{esc(nq)}</p>"
    elif last:
        next_html = "<p class='muted'>最終章（冒頭の問いへの答えで締める）</p>"
    else:
        next_html = unfilled_html()
    from_prev = b.get("from_previous")
    from_html = f"<p>{esc(from_prev)}</p>" if filled(from_prev) else unfilled_html()
    items = "".join([
        item(1, "聴講者に考えてもらう問い", text_block(b.get("question"))),
        item(2, "この章の主張", text_block(b.get("claim")), "claim"),
        item(3, "なぜこの章が必要か", text_block(b.get("why_here"))),
        item(4, "主張を支える根拠", evidence_html(b.get("evidence"), ev_by_id)),
        item(5, "前章からのつながり", from_html),
        item(6, "次章へ渡す問い", next_html),
        item(7, "論理の飛躍・主張のリスク", risks_html(b, findings, review_state), "risks"),
        item(8, "想定時間", f"<p>{esc(minutes_label(b.get('minutes')))}</p>"),
    ])
    return (f"<article class='beat' id='beat-{esc(bid)}'><div class='meta'><span class='step'>{i:02}</span>"
            f"<span class='role'>{esc(role_label(b.get('role')))}</span><code>{esc(bid)}</code>"
            f"<span class='time'>{esc(minutes_label(b.get('minutes')))}</span></div>"
            f"<dl class='items'>{items}</dl>"
            f"<label for='f{i}'>この章への修正指示</label><textarea id='f{i}' data-beat='{esc(bid)}' "
            f"placeholder='例：課題を先に示したい / この結果は別の位置へ / 主張が言い過ぎ'></textarea></article>")


def candidates_section(project: Path, story: dict, state: str) -> tuple[str, list[str]]:
    path = project / "candidates.json"
    if not path.exists():
        return ("<section class='panel' id='candidates'><h2>ストーリー候補の比較</h2>"
                + unfilled_html("candidates.json がありません。方向の違う候補を比べるときに作成します") + "</section>",
                ["## ストーリー候補の比較", "", f"- {UNFILLED}（candidates.json なし）", ""])
    doc = obj(load(path))
    cands = [c for c in doc.get("candidates") or [] if isinstance(c, dict) and isinstance(c.get("id"), str) and filled(c["id"])]
    by_id = {c["id"]: c for c in cands}
    rec = doc.get("recommended")
    name = lambda cid: f"{cid}「{by_id[cid].get('title') or UNFILLED}」" if isinstance(cid, str) and cid in by_id else str(cid)
    review = obj(load(project / "reviews" / "ai-candidate-review.json", default={})) if state == "current" else {}
    entries = review.get("candidates") if isinstance(review.get("candidates"), list) else []
    rev_by_id = {e["candidate_id"]: e for e in entries if isinstance(e, dict) and isinstance(e.get("candidate_id"), str)}
    md = ["## ストーリー候補の比較", ""]
    parts = ["<section class='panel' id='candidates'><h2>ストーリー候補の比較</h2>"]
    if isinstance(rec, str) and rec in by_id:
        reason = doc.get("recommendation_reason")
        parts.append(f"<div class='recommend'><b>推奨:</b> {esc(name(rec))}<p>{esc(reason) if filled(reason) else UNFILLED}</p></div>")
        md.append(f"- **推奨:** {name(rec)} — {reason if filled(reason) else UNFILLED}")
    else:
        parts.append(f"<div class='recommend'><b>推奨:</b> <span class='unfilled'>{UNFILLED}</span></div>")
        md.append(f"- **推奨:** {UNFILLED}")
    cid = story.get("candidate_id")
    based = name(cid) if filled(cid) else UNFILLED
    parts.append(f"<p class='muted'>下の章立て（story.json）が展開している候補: {esc(based)}</p>")
    md.append(f"- **章立てが展開している候補:** {based}")
    parts.append("<div class='cgrid head'>")
    for c in cands:
        badge = "<span class='badge'>推奨</span>" if c["id"] == rec else ""
        outline = text_items(c.get("outline"))
        outline_html = ("<ol class='outline'>" + "".join(f"<li>{esc(x)}</li>" for x in outline) + "</ol>") if outline else ""
        parts.append(f"<div class='cell chead'><div class='ctag'>{esc(c['id'])}{badge}</div><h3>{esc(c.get('title') or UNFILLED)}</h3>"
                     f"<p class='muted'>{esc(c.get('approach') or '')}</p>{outline_html}</div>")
        md.append(f"- **{name(c['id'])}**{'（推奨）' if c['id'] == rec else ''} 切り口: {c.get('approach') or UNFILLED} / "
                  f"章立て: {' → '.join(outline) or UNFILLED}")
    parts.append("</div>")
    for key, label in CANDIDATE_ASPECTS:
        parts.append(f"<h3 class='aspect'>{esc(label)}</h3><div class='cgrid'>")
        md += ["", f"### {label}"]
        for c in cands:
            parts.append(f"<div class='cell'><div class='ctag'>{esc(c['id'])} {esc(c.get('title') or '')}</div>{text_block(c.get(key))}</div>")
            md.append(f"- {c['id']}: {' / '.join(text_items(c.get(key))) or UNFILLED}")
        parts.append("</div>")
    parts.append(f"<h3 class='aspect'>独立AIレビューの要点</h3><p class='muted'>候補レビュー: {esc(review_state_label(state))}"
                 + (f" · 独立したコンテキスト: {'はい' if review.get('reviewer_independent') is True else 'いいえ'}" if review else "") + "</p>")
    md += ["", "### 独立AIレビューの要点", f"- 状態: {review_state_label(state)}"
           + (f" / 独立したコンテキスト: {'はい' if review.get('reviewer_independent') is True else 'いいえ'}" if review else "")]
    if filled(review.get("summary")):
        parts.append(f"<p>{esc(review['summary'])}</p>")
        md.append(f"- {review['summary']}")
    if filled(review.get("recommended")):
        parts.append(f"<p><b>レビュー側の推奨:</b> {esc(name(review['recommended']))}</p>")
        md.append(f"- レビュー側の推奨: {name(review['recommended'])}")
    parts.append("<div class='cgrid'>")
    for c in cands:
        e = rev_by_id.get(c["id"])
        if not e:
            parts.append(f"<div class='cell'><div class='ctag'>{esc(c['id'])}</div>{unfilled_html()}</div>")
            md.append(f"- {c['id']}: {UNFILLED}")
            continue
        criteria = [x for x in (e.get("criteria") if isinstance(e.get("criteria"), list) else []) if isinstance(x, dict)]
        crit = "".join(f"<li><b>{esc(x.get('criterion', ''))}:</b> {esc(x.get('assessment', ''))}</li>" for x in criteria)
        parts.append(f"<div class='cell'><div class='ctag'>{esc(c['id'])}</div>"
                     + (f"<p><b>{esc(e['verdict'])}</b></p>" if filled(e.get("verdict")) else "")
                     + "<p class='subhead'>強み</p>" + text_block(e.get("strengths"))
                     + "<p class='subhead'>破綻しうる点</p>" + text_block(e.get("breakpoints"))
                     + (f"<p class='subhead'>観点別</p><ul>{crit}</ul>" if crit else "") + "</div>")
        md.append(f"- {c['id']}: {e.get('verdict') or UNFILLED} / 強み: {' / '.join(text_items(e.get('strengths'))) or UNFILLED}"
                  f" / 破綻しうる点: {' / '.join(text_items(e.get('breakpoints'))) or UNFILLED}")
        md += [f"  - {x.get('criterion', '')}: {x.get('assessment', '')}" for x in criteria]
    parts.append("</div>")
    radios = "".join(f"<label class='choice'><input type='radio' name='candidate' value='{esc(c['id'])}'> {esc(name(c['id']))}</label>" for c in cands)
    radios += ("<label class='choice'><input type='radio' name='candidate' value='mix'> 複数の案を混ぜる</label>"
               "<label class='choice'><input type='radio' name='candidate' value='other'> どれでもない</label>")
    parts.append(f"<fieldset class='pick'><legend>どの案で進めるか</legend>{radios}"
                 "<label for='candidate-instruction'>選んだ理由・混ぜ方・追加の指示</label>"
                 "<textarea id='candidate-instruction' placeholder='例：案Bの構成で、案Aの冒頭の問いを使う'></textarea></fieldset></section>")
    return "".join(parts), md + [""]


def checks_section(brief: dict, review: dict) -> tuple[str, list[str]]:
    checks, custom = review_checks(brief)
    results = review.get("checks") if isinstance(review.get("checks"), list) else []
    by_text = {normalized(r.get("check")): r for r in results if isinstance(r, dict)}
    used = set()
    source = "brief.review_checks" if custom else "既定の観点（brief.review_checks で登壇ごとに変更できます）"
    parts = [f"<section class='panel' id='checks'><h2>構成全体の確認</h2><p class='muted'>観点: {esc(source)}</p><ol class='checks'>"]
    md = ["## 構成全体の確認", "", f"観点: {source}", ""]

    def row(text, r):
        if not r:
            return (f"<li><div class='check-q'>{esc(text)}</div><span class='verdict unfilled-tag'>{UNFILLED}</span></li>",
                    f"- {text} — {UNFILLED}")
        v = r.get("verdict")
        fix = f"<p><b>修正案:</b> {esc(r['fix'])}</p>" if filled(r.get("fix")) else ""
        return (f"<li><div class='check-q'>{esc(text)}</div><span class='verdict v-{esc(v)}'>{esc(label_of(VERDICT_LABELS, v, UNFILLED))}</span>"
                f"<p><b>理由:</b> {esc(r.get('reason') or UNFILLED)}</p>{fix}</li>",
                f"- {text} — {label_of(VERDICT_LABELS, v, UNFILLED)}: {r.get('reason') or UNFILLED}" + (f" → {r['fix']}" if filled(r.get('fix')) else ""))
    for text in checks:
        key = normalized(text)
        r = by_text.get(key)
        if r:
            used.add(key)
        h, m = row(text, r)
        parts.append(h)
        md.append(m)
    for r in results:
        if isinstance(r, dict) and normalized(r.get("check")) not in used:
            h, m = row(r.get("check", ""), r)
            parts.append(h)
            md.append(m + "（レビュー側で追加された観点）")
    parts.append("</ol></section>")
    return "".join(parts), md + [""]


BOARD_CSS = """
:root{color-scheme:light dark;--bg:#f5f6fb;--fg:#182433;--card:#fff;--sub:#4a5a70;--edge:#d8e0ea;--accent:#3549c9;--soft:#eef2ff;
--warn-bg:#fff4e5;--warn-edge:#c17a0f;--crit-bg:#fff0f0;--crit-edge:#c9323a;--minor-bg:#eef6ff;--minor-edge:#4f84b4;
--ok-bg:#e6f5ec;--ok-fg:#17663a;--bad-bg:#fde8e8;--bad-fg:#a12a31;--mid-bg:#fff2d9;--mid-fg:#875000;
--un-fg:#8d4f00;--un-edge:#d9a55a;--input-bg:#fff;--input-edge:#b9c6d9;--bar:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#111a28;--fg:#e9eef7;--card:#1b2a3f;--sub:#b3c1d6;--edge:#34465f;--accent:#9aabff;--soft:#22385a;
--warn-bg:#4a3820;--warn-edge:#e0a040;--crit-bg:#4b2630;--crit-edge:#ff7b84;--minor-bg:#23405e;--minor-edge:#86b6e6;
--ok-bg:#1d4630;--ok-fg:#a6e3bd;--bad-bg:#5a2329;--bad-fg:#ffc0c4;--mid-bg:#4d3a14;--mid-fg:#ffd98a;
--un-fg:#f3bd6b;--un-edge:#a07020;--input-bg:#142235;--input-edge:#5d708b;--bar:#1b2a3f}}
*{box-sizing:border-box}body{margin:0;font:16px/1.65 -apple-system,BlinkMacSystemFont,'Hiragino Sans','Segoe UI',sans-serif;background:var(--bg);color:var(--fg);overflow-wrap:anywhere}
header{background:#152641;color:#fff;padding:36px 16px}header .wrap{max-width:1080px;margin:auto}header p{color:#d3def0;margin:8px 0}header .kicker{font-size:12px;letter-spacing:.12em;color:#9fb4d6}
main{max-width:1080px;margin:auto;padding:20px 16px}.deck{display:flex;flex-direction:column;gap:16px}
.panel,.beat{background:var(--card);border:1px solid var(--edge);border-radius:14px;padding:22px;margin:0 0 16px}
h1{font-size:28px;line-height:1.35;margin:6px 0}h2{font-size:22px;margin:0 0 12px}h3{font-size:18px;line-height:1.45;margin:8px 0}
p{margin:8px 0}ul,ol{margin:6px 0;padding-left:1.4em}code{font-size:13px}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:10px;color:var(--sub);font-size:14px}.step{background:var(--soft);color:var(--accent);border-radius:50px;padding:2px 10px;font-weight:800}.role{font-weight:700;color:var(--fg)}.time{margin-left:auto}
dl.items{margin:12px 0 0}.item{display:grid;grid-template-columns:minmax(0,200px) minmax(0,1fr);gap:4px 16px;padding:10px 0;border-top:1px solid var(--edge)}
dt{font-weight:700;font-size:14px;color:var(--sub)}dd{margin:0;min-width:0}dd>p:first-child{margin-top:0}.n{display:inline-block;min-width:1.6em;color:var(--accent)}
.item.claim dd{font-size:18px;font-weight:700}
@media (max-width:640px){.item{grid-template-columns:minmax(0,1fr)}.time{margin-left:0}}
.evlist{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px}.ev{border:1px solid var(--edge);border-radius:8px;padding:8px 12px}.ev p{margin:4px 0}
.evhead{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.evmeta{font-size:14px;color:var(--sub)}
.tag{font-size:12px;border-radius:50px;padding:1px 9px;background:var(--soft);color:var(--fg)}.tag.bad{background:var(--bad-bg);color:var(--bad-fg)}
.st-confirmed{background:var(--ok-bg);color:var(--ok-fg)}.st-limited{background:var(--mid-bg);color:var(--mid-fg)}.st-unverified,.st-hypothesis{background:var(--bad-bg);color:var(--bad-fg)}
.unfilled{color:var(--un-fg);font-weight:600;border:1px dashed var(--un-edge);border-radius:6px;padding:2px 8px;display:inline-block;margin:2px 0}
.unfilled-tag{color:var(--un-fg);border:1px dashed var(--un-edge);background:transparent}
.muted{color:var(--sub);font-size:14px}.subhead{font-size:13px;font-weight:700;color:var(--sub);margin:10px 0 4px}.subhead:first-child{margin-top:0}
.risk{padding:9px 12px;margin:6px 0;background:var(--warn-bg);border-left:4px solid var(--warn-edge);border-radius:6px;font-size:15px}
.finding{padding:9px 12px;margin:6px 0;background:var(--warn-bg);border-left:4px solid var(--warn-edge);border-radius:6px;font-size:15px}
.finding.critical{background:var(--crit-bg);border-color:var(--crit-edge)}.finding.minor{background:var(--minor-bg);border-color:var(--minor-edge)}.fix{margin-top:4px}
.cgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:10px}.cell{border:1px solid var(--edge);border-radius:10px;padding:10px 12px;min-width:0}
.chead{background:var(--soft)}.ctag{font-size:12px;font-weight:700;color:var(--sub)}.badge{margin-left:8px;background:var(--accent);color:var(--card);border-radius:50px;padding:1px 8px}
.aspect{margin-top:18px;font-size:16px;border-bottom:2px solid var(--edge);padding-bottom:4px}.recommend{background:var(--soft);border-left:4px solid var(--accent);border-radius:6px;padding:10px 14px;margin:0 0 10px}
.outline{font-size:14px}.pick{border:1px solid var(--edge);border-radius:10px;margin:18px 0 0;padding:12px 14px}.pick legend{font-weight:700;padding:0 6px}.choice{display:block;font-weight:500;margin:4px 0}
.checks{padding-left:1.4em}.checks li{padding:8px 0;border-top:1px solid var(--edge)}.check-q{font-weight:700}
.verdict{display:inline-block;font-size:13px;font-weight:700;border-radius:50px;padding:1px 10px;margin:4px 0}.v-pass{background:var(--ok-bg);color:var(--ok-fg)}.v-partial{background:var(--mid-bg);color:var(--mid-fg)}.v-fail{background:var(--bad-bg);color:var(--bad-fg)}.v-unknown{background:var(--soft);color:var(--fg)}
label{display:block;font-weight:650;margin-top:14px}textarea{display:block;width:100%;min-height:78px;margin-top:6px;padding:10px;font:inherit;border:1px solid var(--input-edge);border-radius:9px;resize:vertical;background:var(--input-bg);color:var(--fg)}
.actionbar{position:sticky;bottom:0;display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:var(--bar);border:1px solid var(--edge);border-radius:12px;padding:10px;margin:16px 0;box-shadow:0 3px 18px #0003}
button{background:#314edc;color:#fff;border:none;border-radius:8px;font:inherit;font-weight:650;padding:9px 18px;cursor:pointer}.hint{font-size:13px;color:var(--sub)}
a{color:var(--accent)}details summary{cursor:pointer;color:var(--sub)}
"""

BOARD_JS = """
function collectFeedback(){
  const meta=JSON.parse(document.getElementById('board-meta').textContent);
  const comments=[...document.querySelectorAll('textarea[data-beat]')].map(t=>({beat_id:t.dataset.beat,comment:t.value.trim()})).filter(x=>x.comment);
  const data={fingerprint:meta.fingerprint,overall:document.getElementById('overall').value.trim(),comments,incorporated:false};
  if(meta.candidates_fingerprint){
    const sel=document.querySelector('input[name=candidate]:checked');
    const ins=document.getElementById('candidate-instruction');
    const choice={selected:sel?sel.value:'',instruction:ins?ins.value.trim():''};
    if(choice.selected||choice.instruction){data.candidates_fingerprint=meta.candidates_fingerprint;data.candidate_choice=choice;}
  }
  return data;
}
document.getElementById('export').addEventListener('click',()=>{
  const blob=new Blob([JSON.stringify(collectFeedback(),null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='human-feedback.json';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),1000);
});
"""


def write_storyboard(project: Path):
    brief, story, evidence = story_items(project)
    if not all(isinstance(x, dict) for x in (brief, story, evidence)):
        raise ValueError("brief/story/evidence must be JSON objects")
    report = audit(project)
    sha = report["fingerprint"]
    review = current_review(project, sha)
    findings = review.get("findings", []) if isinstance(review.get("findings"), list) else []
    is_independent = review.get("reviewer_independent") is True
    # Malformed beats are reported by audit; the board still renders the rest so the author can see them.
    beats = [b for b in story.get("beats") or [] if isinstance(b, dict)] if isinstance(story.get("beats"), list) else []
    beat_ids = {b.get("id") for b in beats if isinstance(b, dict)}
    by_beat, overall_findings = {}, []
    for x in findings:
        if not isinstance(x, dict):
            continue
        if x.get("beat_id") in beat_ids:
            by_beat.setdefault(x["beat_id"], []).append(x)
        else:
            overall_findings.append(x)
    items = evidence.get("items") if isinstance(evidence.get("items"), list) else []
    ev_by_id = {e["id"]: e for e in items if isinstance(e, dict) and isinstance(e.get("id"), str) and filled(e["id"])}
    cfp = candidates_fingerprint(project)
    cand_html, cand_md = candidates_section(project, story, report.get("candidate_review", "none"))
    checks_html, checks_md = checks_section(brief, review)
    review_label = review_state_label(report["semantic_review"]) + (
        "（独立したコンテキストではない）" if report["semantic_review"] == "current" and not is_independent else "")

    text = lambda v: v if filled(v) else UNFILLED
    lines = [f"# {text(brief.get('title'))} | ストーリーボード", "", f"**聴講者:** {text(brief.get('audience'))}",
             f"**持ち帰り:** {text(brief.get('audience_takeaway'))}",
             f"**Big Idea:** {text(story.get('big_idea'))}", f"**冒頭の問い:** {text(story.get('opening_question'))}",
             f"**最終的な答え:** {text(story.get('final_answer'))}",
             f"**時間:** 合計 {report['total_minutes']:g} 分 / 目標 {brief.get('duration_minutes', UNFILLED)} 分",
             f"**Fingerprint:** `{sha}`", f"**AIレビュー:** {review_label}",
             f"**人間の承認:** {review_state_label(report['approval']) if report['approval'] != 'current' else '最新の構成を承認済み'}", ""]
    if review:
        if filled(review.get("summary")):
            lines += [f"**AIレビューの要約:** {review['summary']}", ""]
        if filled(review.get("audience_takeaway_test")):
            lines += [f"**持ち帰りの確認:** {review['audience_takeaway_test']}", ""]
        missing = text_items(review.get("missing_proof"))
        if missing:
            lines += ["**不足している証明:**"] + [f"- {m}" for m in missing] + [""]
        for f in overall_findings:
            lines.append(f"- ⚠ 全体 {f.get('severity')}/{f.get('status')}: {f.get('reason')} → {f.get('fix')}")
        lines.append("")
    lines += cand_md + checks_md + ["## 章ごとのストーリー", ""]
    for idx, b in enumerate(beats, 1):
        evs = []
        for r in b.get("evidence") if isinstance(b.get("evidence"), list) else []:
            ev = ev_by_id.get(r) if isinstance(r, str) else None
            if ev is None:
                evs.append(f"{r}（台帳に無いID）")
                continue
            url = safe_url(ev.get("url"))
            evs.append(f"{r} [{label_of(KIND_LABELS, ev.get('kind'), '種別' + UNFILLED)}/{label_of(STATUS_LABELS, ev.get('status'), '確度' + UNFILLED)}] "
                       f"{text(ev.get('summary'))}（適用範囲: {text(ev.get('scope'))} / 出所: {text(ev.get('source'))}"
                       + (f" {url}" if url else "") + "）")
        risks = [f"{r.get('risk')} → 修正案: {r.get('fix')}" for r in (b.get("risks") if isinstance(b.get("risks"), list) else [])
                 if isinstance(r, dict)]
        nq = b.get("next_question")
        next_text = nq if filled(nq) else ("最終章（冒頭の問いへの答えで締める）" if idx == len(beats) else UNFILLED)
        lines += [f"### {idx}. [{role_label(b.get('role'))}] {text(b.get('claim'))} ({minutes_label(b.get('minutes'))})",
                  f"1. 聴講者に考えてもらう問い: {text(b.get('question'))}",
                  f"2. この章の主張: {text(b.get('claim'))}",
                  f"3. なぜこの章が必要か: {text(b.get('why_here'))}",
                  f"4. 主張を支える根拠: {'; '.join(evs) or UNFILLED}",
                  f"5. 前章からのつながり: {text(b.get('from_previous'))}",
                  f"6. 次章へ渡す問い: {next_text}",
                  f"7. 論理の飛躍・主張のリスク: {'; '.join(risks) or UNFILLED}"]
        for f in by_beat.get(b.get("id"), []):
            lines.append(f"   - ⚠ AIレビュー {f.get('severity')}/{f.get('status')}: {f.get('reason')} → {f.get('fix')}")
        lines += [f"8. 想定時間: {minutes_label(b.get('minutes'))}", ""]
    lines += ["## 機械チェックの所見", ""] + [f"- {x}" for x in report["errors"] + report["warnings"]]
    lines += ["", "## 人間からの修正指示", "", "HTML のストーリーボードで章ごとの指示を書き出すか、AIエージェントに会話で伝えてください。"]
    out = project / "build"
    out.mkdir(parents=True, exist_ok=True)
    (out / "storyboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    issues_html = "".join("<li>" + esc(x) + "</li>" for x in report["errors"] + report["warnings"]) or "<li>なし</li>"
    review_extra = ""
    if review:
        if filled(review.get("summary")):
            review_extra += f"<p><b>AIレビューの要約:</b> {esc(review['summary'])}</p>"
        if filled(review.get("audience_takeaway_test")):
            review_extra += f"<p><b>持ち帰りの確認:</b> {esc(review['audience_takeaway_test'])}</p>"
        missing = text_items(review.get("missing_proof"))
        if missing:
            review_extra += "<p class='subhead'>不足している証明</p><ul>" + "".join(f"<li>{esc(m)}</li>" for m in missing) + "</ul>"
        if overall_findings:
            review_extra += "<p class='subhead'>全体への指摘</p>" + "".join(finding_html(f) for f in overall_findings)
    cards = "".join(beat_card(i, b, i == len(beats), ev_by_id, by_beat.get(b.get("id"), []), report["semantic_review"])
                    for i, b in enumerate(beats, 1))
    approval_label = "最新の構成を承認済み" if report["approval"] == "current" else review_state_label(report["approval"])
    meta = json.dumps({"fingerprint": sha, "candidates_fingerprint": cfp}).replace("</", "<\\/")
    html_doc = (
        "<!doctype html><html lang='ja'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Story Review</title><style>{BOARD_CSS}</style></head><body>"
        f"<header><div class='wrap'><p class='kicker'>STORY-FIRST · スライドの前に構成を確認</p><h1>{esc(text(brief.get('title')))}</h1>"
        f"<p><b>Big Idea:</b> {esc(text(story.get('big_idea')))}</p><p><b>聴講者:</b> {esc(text(brief.get('audience')))}</p>"
        f"<p><b>持ち帰り:</b> {esc(text(brief.get('audience_takeaway')))}</p></div></header><main>"
        "<section class='panel'><h2>このストーリーで伝わるか</h2>"
        f"<p><b>冒頭の問い:</b> {esc(text(story.get('opening_question')))}</p><p><b>最終的な答え:</b> {esc(text(story.get('final_answer')))}</p>"
        f"<p><b>時間:</b> 合計 {report['total_minutes']:g} 分 / 目標 {esc(brief.get('duration_minutes', UNFILLED))} 分</p>"
        f"<p><b>機械チェック:</b> {esc(report['status'])} · <b>AIレビュー:</b> {esc(review_label)} · <b>人間の承認:</b> {esc(approval_label)}</p>"
        f"{review_extra}<p class='hint'>Fingerprint: <code>{esc(sha)}</code></p>"
        f"<details><summary>機械チェックの所見（意味のレビューの代わりではありません）</summary><ul>{issues_html}</ul></details></section>"
        f"{cand_html}{checks_html}<h2>章ごとのストーリー</h2><div class='deck'>{cards}</div>"
        "<section class='panel'><h2>全体への修正指示</h2><textarea id='overall' placeholder='全体のストーリー構成、話すべきでないこと、追加したい論点'></textarea></section>"
        "<section class='actionbar'><button id='export'>修正指示を書き出す（.json）</button>"
        "<span class='hint'>human-feedback.json を AI に渡すか <code>storyflow.py feedback</code> で取り込みます。入力は自動送信されません。</span></section>"
        f"</main><script type='application/json' id='board-meta'>{meta}</script><script>{BOARD_JS}</script></body></html>")
    (out / "storyboard.html").write_text(html_doc, encoding="utf-8")
    save(out / "audit.json", report)
    return [out / "storyboard.html", out / "storyboard.md"]


def review_request(project: Path):
    report = audit(project)
    if report['errors']:
        raise ValueError('Fix structural audit errors before independent review: '+', '.join(report['errors']))
    brief, story, evidence = story_items(project)
    checks, _ = review_checks(brief)
    check_lines = "\n".join(f"- {c}" for c in checks)
    content = f"""# Independent story review request

Snapshot fingerprint: `{report['fingerprint']}`

Review only the supplied brief/story/evidence. Work in a **separate context** from the author. Do not create slides, scripts or images.

Assess: audience value, depth of problem definition, why existing approach is not sufficient, fair baseline and alternatives, rationale for trying the proposed technology, causal progression between every beat (including each beat's `from_previous`), evidence scope and kind (fact / experiment / inference / plan), conclusion/decision fit, disclosure risk, and time. Check whether the author's own `risks` per beat are real and whether their fixes would work; add the risks the author missed. Do not award a pass just because the order feels logical. Question assumptions and the possibility of an invented problem.

For each issue, cite an exact beat id (or `overall`), its actual claim/question, why the flaw matters, and a concrete revision. Never invent empirical results. Report CRITICAL/MAJOR/MINOR issues with status open/resolved/accepted_risk.

Answer every whole-story check below with a verdict `pass` / `partial` / `fail` / `unknown`, a reason, and for `partial`/`fail` a concrete structural fix:

{check_lines}

Output `reviews/ai-story-review.json` with: `fingerprint`, `reviewer_independent: true` only when genuinely in a separate context, `summary`, `findings:[{{beat_id,severity,status,reason,fix}}]`, `checks:[{{check,verdict,reason,fix}}]` (copy each check text verbatim), `audience_takeaway_test`, `missing_proof`. Existing constraints on sharing/private assets always apply.

## Brief\n```json\n{json.dumps(brief,ensure_ascii=False,indent=2)}\n```\n
## Story\n```json\n{json.dumps(story,ensure_ascii=False,indent=2)}\n```\n
## Evidence\n```json\n{json.dumps(evidence,ensure_ascii=False,indent=2)}\n```\n"""
    p=project / "build" / "ai-review-request.md"
    p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(content,encoding="utf-8")
    return p


def candidate_review_request(project: Path):
    cfp = candidates_fingerprint(project)
    if cfp is None:
        return None
    report = audit(project)
    if report['errors']:
        raise ValueError('Fix structural audit errors before independent review: '+', '.join(report['errors']))
    brief, _, evidence = story_items(project)
    candidates = load(project / "candidates.json")
    criteria = "、".join(DEFAULT_CANDIDATE_CRITERIA)
    content = f"""# Independent candidate comparison request

Candidates fingerprint: `{cfp}`

Compare the materially different story directions below. Work in a **separate context** from the author, and do not read the author's elaborated `story.json` first. Do not create slides.

For each candidate judge {criteria}. A candidate is not better because it carries more technical information. Name where each would break in front of a first-time audience, and which evidence it leans on beyond its stated scope.

Output `reviews/ai-candidate-review.json` with: `fingerprint` (the value above), `reviewer_independent: true` only when genuinely in a separate context, `summary`, optional `recommended` (candidate id), `candidates:[{{candidate_id, verdict, strengths:[...], breakpoints:[...], criteria:[{{criterion, assessment}}]}}]`.

## Brief\n```json\n{json.dumps(brief,ensure_ascii=False,indent=2)}\n```\n
## Candidates\n```json\n{json.dumps(candidates,ensure_ascii=False,indent=2)}\n```\n
## Evidence\n```json\n{json.dumps(evidence,ensure_ascii=False,indent=2)}\n```\n"""
    p = project / "build" / "ai-candidate-review-request.md"
    p.parent.mkdir(exist_ok=True, parents=True)
    p.write_text(content, encoding="utf-8")
    return p


def approve(project: Path, note: str, human_confirmed: bool, override_reason: str=""):
    if not human_confirmed or not filled(note):
        raise ValueError('Human confirmation and nonempty approval note required.')
    report=audit(project)
    if report['errors']:
        raise ValueError('Cannot approve invalid story: '+', '.join(report['errors']))
    findings, independent=review_findings(project,report['fingerprint'])
    open_high=[x for x in findings if isinstance(x,dict) and x.get('status')=='open' and x.get('severity') in ('critical','major')]
    if not independent and not filled(override_reason):
        raise ValueError('Independent AI story review required, or explicit override with reason.')
    if open_high and not filled(override_reason):
        raise ValueError(f'{len(open_high)} critical/major story findings remain; address them or document override reason.')
    human=load(project/'reviews'/'human-feedback.json',default={})
    if human and human.get('fingerprint')==report['fingerprint'] and not human.get('incorporated',False) and not filled(override_reason):
        raise ValueError('Human feedback not yet incorporated.')
    record={"fingerprint":report['fingerprint'],"approved_at_utc":datetime.now(timezone.utc).isoformat(),
            "human_confirmed":True,"approval_note":note,"override_reason":override_reason or None}
    save(project/'approvals'/'story-approved.json',record)
    return record


def draft(project: Path):
    report=audit(project)
    if report['errors'] or report['approval']!='current':
        raise ValueError('Story is not valid and approved at the current fingerprint; drafting is blocked.')
    brief,story,evidence=story_items(project)
    chunks=[f"<!-- DRAFT ONLY: {brief['title']} | approved story sha256 {report['fingerprint']} -->", ""]
    for b in story['beats']:
        chunks.extend([f"<!-- story-beat:{b['id']} -->",f"# {b['claim']}","",f"<!-- role: {b['role']} | time: {b['minutes']} min | evidence: {', '.join(b['evidence'])} -->", f"<!-- question: {b['question']} -->", f"<!-- transition: {b['next_question']} -->", "", "---", ""])
    p=project/'draft'/'slides.md'
    p.parent.mkdir(exist_ok=True)
    p.write_text("\n".join(chunks),encoding='utf-8')
    return p



def deck_audit(project: Path):
    report=audit(project)
    errors=[]
    if report['approval']!='current':
        errors.append('No current human-approved story')
    deck=project/'draft'/'slides.md'
    if not deck.exists():
        errors.append('draft/slides.md is absent')
        return {"status":"FAIL","errors":errors,"warnings":[]}
    source=deck.read_text(encoding='utf-8')
    if report['fingerprint'] not in source.splitlines()[0]:
        errors.append('Slide source is not bound to current approved storyboard fingerprint')
    sequence=re.findall(r'<!--\s*story-beat:([A-Za-z0-9_-]+)\s*-->',source)
    _,story,_=story_items(project)
    expected=[b['id'] for b in story['beats']]
    collapsed=[]
    for item in sequence:
        if not collapsed or collapsed[-1]!=item:collapsed.append(item)
    if collapsed!=expected:
        errors.append('Story beat sequence changed, missing or reordered: expected '+str(expected)+'; found '+str(collapsed))
    if not sequence:
        errors.append('No story-beat anchors; could not trace deck to approved narrative')
    for b in story['beats']:
        if b['claim'] not in source:
            errors.append('Approved claim absent from slide content: '+b['id'])
    return {"status":"FAIL" if errors else "PASS","errors":errors,"warnings":[],"beat_sequence":collapsed}


def candidate_template(cid: str, approach: str) -> dict:
    return {"id": cid, "title": "", "approach": approach, "audience_problem": "", "big_idea": "",
            "logic": [], "key_findings": [], "takeaway_criteria": [], "failure_risks": [], "outline": []}


def init_project(project: Path, title: str, duration: float):
    if project.exists() and any(project.iterdir()):
        raise ValueError('Target directory is non-empty. Refusing to overwrite.')
    project.mkdir(parents=True,exist_ok=True)
    save(project/'brief.json',{"title":title,"audience":"対象聴衆を明示","audience_takeaway":"聴講者が終わった後にできる判断","duration_minutes":duration,"talk_type":"technical_decision","disclosure_rules":[],
         "review_checks":list(DEFAULT_REVIEW_CHECKS)})
    save(project/'story.json',{"big_idea":"この発表で変えたい認識を1文で","opening_question":"なぜこの課題に取り組むのか？","final_answer":"どう判断するか？","beats":[
       {"id":"B1","role":"problem","question":"なぜこの課題に取り組むのか？","claim":"具体的な課題を1つ示す","why_here":"聴講者に解決の必要性を理解してもらう","from_previous":"冒頭の問いを受けて、課題の実例から入る","next_question":"既存の手段で解決できないか？","evidence":[],"risks":[],"minutes":duration/2},
       {"id":"B2","role":"decision","question":"既存の手段で解決できないか？","claim":"検証から妥当な判断を導く","why_here":"冒頭の問題に答える","from_previous":"前章の課題に対して、選択肢を比べた結果を示す","next_question":"","evidence":[],"risks":[],"minutes":duration/2}]})
    save(project/'evidence.json',{"items":[]})
    save(project/'candidates.json',{"recommended":"","recommendation_reason":"","candidates":[
        candidate_template("C1","課題起点"),candidate_template("C2","技術選択起点"),candidate_template("C3","仮説検証起点")]})
    (project/'reviews').mkdir(exist_ok=True)


def import_feedback(project: Path, file: Path):
    feedback=load(file)
    if not isinstance(feedback,dict) or not isinstance(feedback.get('comments',[]),list):
        raise ValueError('Invalid feedback JSON')
    if feedback.get('fingerprint') != fingerprint(project):
        raise ValueError('Feedback is based on a different story version; review the changed story first')
    choice=feedback.get('candidate_choice')
    if choice is not None:
        if not isinstance(choice,dict):
            raise ValueError('Invalid feedback JSON: candidate_choice must be an object')
        cfp=candidates_fingerprint(project)
        if cfp is None:
            raise ValueError('Feedback chooses a candidate but candidates.json is absent')
        if feedback.get('candidates_fingerprint') != cfp:
            raise ValueError('Candidate choice is based on a different candidates.json version; review the changed candidates first')
        cands=obj(load(project/'candidates.json')).get('candidates')
        ids={c['id'] for c in (cands if isinstance(cands,list) else []) if isinstance(c,dict) and isinstance(c.get('id'),str)}
        selected=choice.get('selected','')
        if not isinstance(selected,str) or not isinstance(choice.get('instruction',''),str):
            raise ValueError('Invalid feedback JSON: candidate_choice.selected and instruction must be strings')
        if selected and selected not in ids and selected not in ('mix','other'):
            raise ValueError(f'Unknown candidate in feedback: {selected}')
    else:
        # A fingerprint without a choice would look like a stale binding in later audits.
        feedback.pop('candidates_fingerprint',None)
    save(project/'reviews'/'human-feedback.json',feedback)


def run(argv=None):
    p=argparse.ArgumentParser(description="Story-first presentation harness")
    sub=p.add_subparsers(dest='command',required=True)
    for action in ('audit','board','review-request','approve','draft','deck-audit','status'):
        a=sub.add_parser(action)
        a.add_argument('project',type=Path)
        if action=='approve':
            a.add_argument('--note',required=True)
            a.add_argument('--human-confirmed',action='store_true')
            a.add_argument('--override-reason',default='')
    i=sub.add_parser('init');i.add_argument('project',type=Path);i.add_argument('--title',required=True);i.add_argument('--minutes',type=float,required=True)
    f=sub.add_parser('feedback');f.add_argument('project',type=Path);f.add_argument('--file',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='init':
            init_project(args.project,args.title,args.minutes)
            print('Created',args.project)
        elif args.command=='feedback':
            import_feedback(args.project,args.file)
            print('Feedback imported; ask the author agent to revise the story, then re-review.')
        elif args.command=='board':
            for path in write_storyboard(args.project):print(path)
        elif args.command=='review-request':
            print(review_request(args.project))
            extra=candidate_review_request(args.project)
            if extra:print(extra)
        elif args.command=='approve':
            print(json.dumps(approve(args.project,args.note,args.human_confirmed,args.override_reason),ensure_ascii=False,indent=2))
        elif args.command=='draft':
            print(draft(args.project))
        elif args.command=='deck-audit':
            result=deck_audit(args.project)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            if result['status']=='FAIL':return 1
        else:
            report=audit(args.project)
            print(json.dumps(report,ensure_ascii=False,indent=2))
            if args.command=='audit' and report['errors']:
                return 1
    except (ValueError,FileNotFoundError,KeyError,TypeError) as e:
        print('ERROR:',str(e),file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    sys.exit(run())
