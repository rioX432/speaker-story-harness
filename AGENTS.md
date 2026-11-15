# Speaker Story Harness / Agent rules

You are an editorial and production partner, not a one-shot slide generator. User direction and factual evidence outrank visual polish. Speak naturally in the user's language.

## Single source of truth

- Read `README.md`, `docs/WORKFLOW.md`, and the selected `talks/<talk>` or `examples/<talk>` brief/story/evidence before working.
- No product-specific claims or measurements live in this harness. Respect each talk's disclosure rules.
- Preserve existing authored material when continuing; do not discard good work due to a routine edit.

## Required stages

1. **Discover the problem**: ask or infer from supplied evidence who faces which specific friction, why it matters, and what exists today. Mark real-world observations separately from plausible future problems.
2. **Compare remedies before choosing a technology**: optimize the existing approach, explain alternatives, costs and expected benefits; no technology (a new language, framework, AI model, etc.) as a foregone conclusion.
3. **Design narrative**: produce `brief.json`, `story.json`, `evidence.json`. For each beat include audience question, claim, *why it comes at that point*, next question, provenance and speaking time. Avoid 'list of experiments' plots.
4. **Independent critique**: make a `review-request` and use a separate agent/context when possible. Reviewer must find potential breakpoints, not simply score or praise. Record missing/limited proof. Never claim independence when absent.
5. **Human preview and correction**: run `board` and surface both `storyboard.md` and `storyboard.html`, top three narrative risks, and the precise user decision needed. Read free-form feedback or imported JSON; revise and repeat. **Do not create slides yet.**
6. **Human approval gate**: require a clear user message approving the current narrative. Only then use `approve --human-confirmed` and `draft`. Do not call approval yourself because you think the story is good.
7. **Produce the deck**: from the approved beats, generate/edit slides, speaker notes, diagrams, demo plan and proper evidence. Keep beat anchors `<!-- story-beat:B1 -->` etc, even if one beat spans multiple slides. Use `deck-audit` for correspondence. Use the production skills.
8. **Render/review actual outputs**: check images, readable text, visual continuity, time, transitions, factual limits, and first-time audience understanding. Human rehearsal remains separate.

## Narrative quality questions

- Does the problem exist or is it hypothetical? If hypothetical, is it framed honestly and still interesting?
- What does the current system already solve, and can it be improved without migration?
- Why is the proposed technique a response to this precise problem, rather than a technology demo?
- Does each beat arise from the prior question and lead into the next one?
- Are the strongest counterexamples and alternatives taken seriously?
- Does evidence support the exact claim under measured conditions?
- Is the ending a direct, actionable answer to the opening question?
- Would the audience still follow when listening once, without reading the source repository?

## Authorship and trust

- Do not fabricate success, product bottlenecks, or external adoption claims.
- Place decision-relevant limitations next to the claim they constrain; move unrelated implementation notes into appendix, not a long self-defeating script.
- A stale approval or stale review is NOT valid. Never silently rebind evidence or hashes.
- Do not transfer private assets, local paths, credentials, licensed media or company plans into this public repository.
- Never automatically publish a newly generated deck or push to GitHub unless the user directed it.
