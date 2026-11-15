# Human-in-the-loop storytelling

## The key design change

The legacy pipeline correctly tracked `Big Idea → concept graph → independent audience review → render`, but it could still run all the way to a polished deck before the presenter had challenged the *premise*. The new gate sits **before slide generation**, and its output is a digestible story map rather than a giant deck.

### States

`DISCOVER` → `STORY_DRAFT` → `AI_CRITIQUE` → `HUMAN_STORY_REVIEW` ↺ → `STORY_APPROVED` → `SLIDE_DRAFT` → `DECK_QA` → `REHEARSAL`

AI may propose several distinct narratives early. Put them side by side in the optional `candidates.json` (usually 2–3, with a recommendation and its reason) and have them reviewed independently, but only one coherent proposal should appear in `story.json` at a time; record which one in `story.candidate_id`. Keep candidates short: they are decision material, not parallel stories to maintain. Never invent a mandatory number of revisions or agents.

### Who can do what

- **Author AI:** research, analyse code if available, extract actual problem, design alternatives, draft story, respond to reviewer and human direction.
- **Independent story critic:** read only brief/story/evidence and review request. Find false premises, irrelevant evidence, unjustified technology jumps, weak cause-and-effect and nonresponsive conclusions.
- **Presenter:** review the 1-page overview and eight or so narrative beats; approve, redirect or replace the central claim. No need to micromanage every slide.
- **Production AI:** only after approval, turn claims into visuals, scripts and deliverables. For large structural changes, return to the story gate.
- **Fresh audience AI:** only finished slides and spoken script in chronological portions, not author intentions or future slides.

### Revision UX

`python3 harness/storyflow.py board <project>` produces `build/storyboard.html` and `.md`. Each beat shows eight numbered items: the audience question, the claim, why it is here, the supporting evidence (summary, kind, status, scope, source), how it follows from the previous beat, the question handed to the next beat, risks (the author's own risks with structural fixes, then independent AI findings), and minutes. Above the beats the board shows the candidate comparison when `candidates.json` exists, and the whole-story checks with verdict, reason and fix. Missing optional fields render as 「未記入」 instead of being hidden, so gaps stay visible.

A textarea at each beat, an overall one and the candidate choice (one candidate, a mix, or none, with an instruction) export `human-feedback.json` without network calls. `storyflow.py feedback` rejects a candidate choice made against a different `candidates.json`, an unknown candidate id, and a `selected` or `instruction` that is not a string.

Alternatively, the presenter can simply tell the AI what feels wrong in chat. The author must update the story file, regenerate the board, and describe the causal difference in the new version. Approval does not carry over when any `brief.json`, `story.json` or `evidence.json` content changes. `candidates.json` is hashed separately (`candidates_fingerprint`) and binds only the candidate review and the candidate choice, so refining rejected candidates does not invalidate an approved story.

### Optional fields

All of these are optional; older projects without them keep working and the board shows 「未記入」.

```jsonc
// brief.json — whole-story checks for this talk; defaults are used when absent
"review_checks": ["Does the talk explain why the proposed change needs to be considered?", "..."]

// story.json — the candidate this story expands, and per-beat fields
"candidate_id": "C1",
"beats": [{
  "id": "B2", "...": "...",
  "from_previous": "B1 established that the current setup is fine at small scale, so we ask what breaks as data grows",
  "risks": [{"risk": "The breakdown is a hypothesis and may read as an observed failure",
             "fix": "Open the beat by framing it as a growth scenario; replace the evidence once measured"}]
}]

// evidence.json — kind is fact / experiment / inference / plan; url is optional and becomes a link only for http(s)
{"id": "E3", "status": "limited", "kind": "experiment", "summary": "...", "scope": "...", "source": "...", "url": "https://..."}

// candidates.json
{"recommended": "C1", "recommendation_reason": "...",
 "candidates": [{"id": "C1", "title": "...", "approach": "problem-first",
   "audience_problem": "...", "big_idea": "...", "logic": ["..."], "key_findings": ["..."],
   "takeaway_criteria": ["..."], "failure_risks": ["..."], "outline": ["..."]}]}
```

`logic`, `key_findings`, `takeaway_criteria` and `failure_risks` accept a string or a list of strings. `audit` rejects malformed values, duplicate candidate ids, a `recommended` or `candidate_id` that names no candidate, and a risk without a fix. A `null` `from_previous` or `risks` counts as not written.

### Semantic review questions (beyond lint)

1. **Problem fidelity:** actual user/system pain vs speculative opportunity? Evidence of magnitude? If absent, narrow the framing.
2. **Existing solution:** what value does it already deliver? Is the simple improvement fairly explored?
3. **Choice rationale:** why is option B plausible for the residual problem and not because it is fashionable?
4. **Causality:** can each beat be prefaced with 'therefore' instead of merely 'next'?
5. **Evidence fit:** does measured scope support the wording and audience takeaway?
6. **Counterarguments:** conditions where the preferred answer becomes wrong? Does the conclusion teach selection criteria?
7. **Listener value:** will a first-time listener remember one idea and apply it?
8. **Time/disclosure:** can this be understood in the allotted minutes without exposing unapproved details?

Do not mistake syntactic `next_question` equality for a real narrative link. It is only a mechanical tripwire.

### Approval discipline

`approve` does not pretend to authenticate the person who invoked it. It records human-confirmed direction *when the actual user has approved*. No independent review, unresolved major/critical findings, or unincorporated feedback stops approval unless the presenter explicitly supplies a reasoned override. This prevents an agent quietly paving over real uncertainty with a green checkmark.

### After approval

`draft` produces a beat-anchored Markdown skeleton. The production AI can split a beat into multiple slides, but must preserve their chronological order and beat anchors. `deck-audit` then detects storyline drift, missing approved claims, and stale storyboard hash. Renderers and output formats are downstream. Check what the audience actually sees, not just markdown and code.
