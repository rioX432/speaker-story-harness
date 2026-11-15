# Human-in-the-loop storytelling

## The key design change

The legacy pipeline correctly tracked `Big Idea → concept graph → independent audience review → render`, but it could still run all the way to a polished deck before the presenter had challenged the *premise*. The new gate sits **before slide generation**, and its output is a digestible story map rather than a giant deck.

### States

`DISCOVER` → `STORY_DRAFT` → `AI_CRITIQUE` → `HUMAN_STORY_REVIEW` ↺ → `STORY_APPROVED` → `SLIDE_DRAFT` → `DECK_QA` → `REHEARSAL`

AI may propose several distinct narratives early, but only one coherent proposal should appear in `story.json` at a time. Keep rejected candidates as short decision notes, not as a large maintenance burden. Never invent a mandatory number of revisions or agents.

### Who can do what

- **Author AI:** research, analyse code if available, extract actual problem, design alternatives, draft story, respond to reviewer and human direction.
- **Independent story critic:** read only brief/story/evidence and review request. Find false premises, irrelevant evidence, unjustified technology jumps, weak cause-and-effect and nonresponsive conclusions.
- **Presenter:** review the 1-page overview and eight or so narrative beats; approve, redirect or replace the central claim. No need to micromanage every slide.
- **Production AI:** only after approval, turn claims into visuals, scripts and deliverables. For large structural changes, return to the story gate.
- **Fresh audience AI:** only finished slides and spoken script in chronological portions, not author intentions or future slides.

### Revision UX

`python3 harness/storyflow.py board <project>` produces `build/storyboard.html` and `.md`. HTML displays each beat's question, claim, reason for position, next question, available evidence and independent AI findings. A textarea at each beat plus an overall one exports `human-feedback.json` without network calls.

Alternatively, the presenter can simply tell the AI what feels wrong in chat. The author must update the story file, regenerate the board, and describe the causal difference in the new version. Approval does not carry over when any `brief.json`, `story.json` or `evidence.json` content changes.

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
