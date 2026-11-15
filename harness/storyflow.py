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
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_BEAT_FIELDS = ("id", "role", "question", "claim", "why_here", "next_question", "evidence", "minutes")
DECISION_ROLES = ("context", "problem", "baseline", "alternative", "hypothesis", "experiment", "results", "decision")


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


def filled(value):
    return isinstance(value, str) and bool(value.strip())


def normalized(value):
    return re.sub(r"\s+", "", str(value)).strip("。？！?!：:")


def story_items(project: Path):
    return load(project / "brief.json"), load(project / "story.json"), load(project / "evidence.json")


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
        if ev.get("status") not in ("confirmed", "limited", "unverified", "hypothesis"):
            errors.append(f"evidence {ev['id']}: status must be confirmed/limited/unverified/hypothesis")
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
    human_path = project / "reviews" / "human-feedback.json"
    human = load(human_path, default={})
    if human and human.get("fingerprint") == sha and not human.get("incorporated", False):
        warnings.append("unincorporated human feedback for current storyboard")
    review = load(project / "reviews" / "ai-story-review.json", default={})
    review_state = "missing"
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
            "total_minutes": round(total, 2), "beat_count": len(beats)}


def review_findings(project: Path, sha: str):
    review = load(project / "reviews" / "ai-story-review.json", default={})
    if review.get("fingerprint") != sha:
        return [], False
    return review.get("findings", []), review.get("reviewer_independent") is True


def write_storyboard(project: Path):
    brief, story, evidence = story_items(project)
    report = audit(project)
    findings, is_independent = review_findings(project, report["fingerprint"])
    by_beat = {}
    for x in findings:
        if isinstance(x, dict):
            by_beat.setdefault(x.get("beat_id", "overall"), []).append(x)
    lines = [f"# {brief['title']} | Storyboard", "", f"**Audience:** {brief['audience']}",
             f"**Big Idea:** {story['big_idea']}", f"**Opening Question:** {story['opening_question']}",
             f"**Final Answer:** {story['final_answer']}", f"**Fingerprint:** `{report['fingerprint']}`",
             f"**AI Review:** {report['semantic_review']} (independent: {is_independent})",
             f"**Human Approval:** {report['approval']}", "", "## Story flow", ""]
    for idx, b in enumerate(story["beats"], 1):
        lines += [f"### {idx}. [{b['role']}] {b['claim']} ({b['minutes']} min)",
                  f"- Audience asks: {b['question']}", f"- Why now: {b['why_here']}",
                  f"- Evidence: {', '.join(b['evidence']) or 'none'}",
                  f"- Leads to: {b['next_question'] or 'closing'}"]
        for f in by_beat.get(b["id"], []):
            lines += [f"- ⚠ {f.get('severity')}/{f.get('status')}: {f.get('reason')} → {f.get('fix')}"]
        lines += [""]
    lines += ["## Machine-audit observations", ""] + [f"- {x}" for x in report['errors'] + report['warnings']]
    lines += ["", "## Human revision requests", "", "Use the HTML board to export per-beat feedback, or tell your AI agent the changes conversationally."]
    out = project / "build"
    out.mkdir(parents=True, exist_ok=True)
    (out / "storyboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    issues_html = "".join("<li>"+html.escape(x)+"</li>" for x in report['errors'] + report['warnings']) or "<li>None recorded</li>"
    all_cards = []
    for i, b in enumerate(story["beats"], 1):
        frows = by_beat.get(b['id'], [])
        flags = "".join(f"<div class='finding {html.escape(f.get('severity','minor'))}'><strong>{html.escape(f.get('severity',''))} · {html.escape(f.get('status',''))}</strong> {html.escape(f.get('reason',''))}<div>Suggested: {html.escape(f.get('fix',''))}</div></div>" for f in frows)
        all_cards.append(f"""<article class='beat'><div class='meta'><span class='step'>{i:02}</span><span class='role'>{html.escape(b['role'])}</span><span>{b['minutes']} min</span></div><h3>{html.escape(b['claim'])}</h3><p><b>Audience question</b><br>{html.escape(b['question'])}</p><p><b>Why here?</b><br>{html.escape(b['why_here'])}</p><p class='evidence'><b>Evidence:</b> {html.escape(', '.join(b['evidence']) or 'Not linked')}</p>{flags}<div class='next'><span>↓ Next question</span><p>{html.escape(b['next_question'] or 'Final answer')}</p></div><label for='f{i}'>Your direction / what feels wrong</label><textarea id='f{i}' data-beat='{html.escape(b['id'])}' placeholder='例：課題を先に示したい / この結果は別の位置へ / 主張が言い過ぎ'></textarea></article>""")
    html_doc = """<!doctype html><html lang='ja'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Story Review</title><style>
:root{color-scheme:light dark;--bg:#f5f6fb;--fg:#182433;--card:#fff;--sub:#53647b;--edge:#d8e0ea;--accent:#475eea}*{box-sizing:border-box}body{margin:0;font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--fg)}header{background:#152641;color:#fff;padding:40px max(22px,calc((100% - 850px)/2))}header p{color:#c9d7e9}main{max-width:900px;margin:auto;padding:24px}.deck{display:flex;flex-direction:column;gap:16px}.beat, .summary{background:var(--card);border:1px solid var(--edge);border-radius:16px;padding:24px;box-shadow:0 2px 10px #192b4009}.meta{display:flex;align-items:center;gap:13px;color:var(--sub);font-size:13px}.step{background:#e6eaff;color:#2441af;border-radius:50px;padding:4px 10px;font-weight:800}.role{text-transform:uppercase;letter-spacing:.12em}h1{font-size:29px;line-height:1.3}h2{font-size:22px}h3{font-size:21px;line-height:1.4;margin:12px 0 18px}p{margin:12px 0}.evidence{color:var(--sub);font-size:14px}.next{background:#f2f6ff;border-left:3px solid var(--accent);padding:9px 16px;border-radius:6px}.next span{color:var(--sub);font-size:12px}.next p{margin:0}textarea{display:block;width:100%;min-height:78px;margin-top:7px;padding:11px;font:inherit;border:1px solid #b9c6d9;border-radius:9px;resize:vertical;background:#fff;color:#182433}.finding{padding:11px 14px;margin:10px 0;background:#fff4e5;border-left:4px solid #d18a19;border-radius:6px;font-size:14px}.finding.critical{background:#fff0f0;border-color:#d43a42}.finding.minor{background:#eff7ff;border-color:#558aba}label{display:block;font-weight:650;margin-top:16px}.actionbar{position:sticky;bottom:0;display:flex;gap:10px;align-items:center;background:#fff;border:1px solid #dbe4f0;border-radius:12px;padding:10px;margin:15px 0;box-shadow:0 3px 18px #0002}button{background:#314edc;color:white;border:none;border-radius:8px;font:inherit;font-weight:650;padding:9px 18px;cursor:pointer}.hint{font-size:12px;color:#64758c}.summary code{font-size:11px;overflow-wrap:anywhere}@media(prefers-color-scheme:dark){:root{--bg:#121b2a;--fg:#e9eef7;--card:#1c2c42;--sub:#aebcd2;--edge:#364763}.next{background:#243953}.actionbar{background:#1c2c42}.finding{background:#4b3923}.finding.critical{background:#4a2730}.finding.minor{background:#283e58}textarea{background:#18283e;color:#e9eef7;border-color:#60728b}}</style></head><body>
<header><div style='max-width:850px;margin:auto'><p>STORY-FIRST · REVIEW BEFORE SLIDES</p><h1>__TITLE__</h1><p>__BIG__</p><p>__AUDIENCE__</p></div></header><main><section class='summary'><h2>Will this story make sense?</h2><p><b>Opening:</b> __OPENING__</p><p><b>Answer:</b> __ANSWER__</p><p><b>Machine audit:</b> __AUDIT__ · <b>AI semantic review:</b> __REVIEW__ · <b>Human approval:</b> __APPROVAL__</p><p class='hint'>Fingerprint: <code>__SHA__</code></p><details><summary>Structural warnings (not a substitute for AI semantic review)</summary><ul>__WARNINGS__</ul></details></section><section class='actionbar'><button id='export'>Export feedback (.json)</button><span class='hint'>AIにこのファイルを渡すと、各章への指示を反映できます。ここでの入力は自動送信されません。</span></section><div class='deck'>__CARDS__</div><section class='summary'><h2>Overall feedback</h2><textarea id='overall' placeholder='全体のストーリー構成、話すべきでないこと、ここに追加したい論点'></textarea></section></main><script>document.getElementById('export').addEventListener('click',()=>{const comments=[...document.querySelectorAll('[data-beat]')].map(t=>({beat_id:t.dataset.beat,comment:t.value.trim()})).filter(x=>x.comment);const data={fingerprint:'__SHA__',overall:document.getElementById('overall').value.trim(),comments,incorporated:false};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='human-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)});</script></body></html>"""
    replacements={"__TITLE__":html.escape(brief['title']),"__BIG__":html.escape(story['big_idea']),"__AUDIENCE__":html.escape(brief['audience']),"__OPENING__":html.escape(story['opening_question']),"__ANSWER__":html.escape(story['final_answer']),"__AUDIT__":report['status'],"__REVIEW__":report['semantic_review'] + (" (not independent)" if report['semantic_review']=="current" and not is_independent else ""),"__APPROVAL__":report['approval'],"__SHA__":report['fingerprint'],"__WARNINGS__":issues_html,"__CARDS__":"".join(all_cards)}
    for k,v in replacements.items():
        html_doc=html_doc.replace(k,v)
    (out / "storyboard.html").write_text(html_doc,encoding="utf-8")
    save(out / "audit.json",report)
    return [out / "storyboard.html",out / "storyboard.md"]


def review_request(project: Path):
    report = audit(project)
    if report['errors']:
        raise ValueError('Fix structural audit errors before independent review: '+', '.join(report['errors']))
    brief, story, evidence = story_items(project)
    content = f"""# Independent story review request

Snapshot fingerprint: `{report['fingerprint']}`

Review only the supplied brief/story/evidence. Work in a **separate context** from the author. Do not create slides, scripts or images.

Assess: audience value, depth of problem definition, why existing approach is not sufficient, fair baseline and alternatives, rationale for trying the proposed technology, causal progression between every beat, evidence scope, conclusion/decision fit, disclosure risk, and time. Do not award a pass just because the order feels logical. Question assumptions and the possibility of an invented problem.

For each issue, cite an exact beat id, its actual claim/question, why the flaw matters, and a concrete revision. Never invent empirical results. Report CRITICAL/MAJOR/MINOR issues with status open/resolved/accepted_risk. Output `reviews/ai-story-review.json` with: `fingerprint`, `reviewer_independent: true` only when genuinely in a separate context, `summary`, `findings:[{{beat_id,severity,status,reason,fix}}]`, `audience_takeaway_test`, `missing_proof`. Existing constraints on sharing/private assets always apply.

## Brief\n```json\n{json.dumps(brief,ensure_ascii=False,indent=2)}\n```\n
## Story\n```json\n{json.dumps(story,ensure_ascii=False,indent=2)}\n```\n
## Evidence\n```json\n{json.dumps(evidence,ensure_ascii=False,indent=2)}\n```\n"""
    p=project / "build" / "ai-review-request.md"
    p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(content,encoding="utf-8")
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


def init_project(project: Path, title: str, duration: float):
    if project.exists() and any(project.iterdir()):
        raise ValueError('Target directory is non-empty. Refusing to overwrite.')
    project.mkdir(parents=True,exist_ok=True)
    save(project/'brief.json',{"title":title,"audience":"対象聴衆を明示","audience_takeaway":"聴講者が終わった後にできる判断","duration_minutes":duration,"talk_type":"technical_decision","disclosure_rules":[]})
    save(project/'story.json',{"big_idea":"この発表で変えたい認識を1文で","opening_question":"なぜこの課題に取り組むのか？","final_answer":"どう判断するか？","beats":[
       {"id":"B1","role":"problem","question":"なぜこの課題に取り組むのか？","claim":"具体的な課題を1つ示す","why_here":"聴講者に解決の必要性を理解してもらう","next_question":"既存の手段で解決できないか？","evidence":[],"minutes":duration/2},
       {"id":"B2","role":"decision","question":"既存の手段で解決できないか？","claim":"検証から妥当な判断を導く","why_here":"冒頭の問題に答える","next_question":"","evidence":[],"minutes":duration/2}]})
    save(project/'evidence.json',{"items":[]})
    (project/'reviews').mkdir(exist_ok=True)


def import_feedback(project: Path, file: Path):
    feedback=load(file)
    if not isinstance(feedback,dict) or not isinstance(feedback.get('comments',[]),list):
        raise ValueError('Invalid feedback JSON')
    if feedback.get('fingerprint') != fingerprint(project):
        raise ValueError('Feedback is based on a different story version; review the changed story first')
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
