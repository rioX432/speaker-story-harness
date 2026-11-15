---
name: story-critic
description: スライド制作前に独立した観点から課題・因果関係・結論・聴衆価値を点検し、具体的なリスクを見つける。
---

# Independent narrative red team

Read only the review request and provided `brief.json`, `story.json`, `evidence.json`. **Do not read the author's rationale, hidden answer key, review history or future slides.** The reviewer should operate in a separate agent/session when available. If not, set `reviewer_independent: false`.

Do not praise general polish. Find where the narrative could mislead or fail: problem invented from architecture; technology chosen first; baseline alternative omitted; industry example used as speed proof; implementation details that don't answer the audience's question; unrelated facts; result scope overstated; conclusion weaker/different than the promise; sudden chapter transitions; too many questions for the available minutes.

For every issue produce `{beat_id, severity, status, reason, fix}` with statuses `open`, `resolved`, `accepted_risk` and levels `critical`, `major`, `minor`. In `reason`, quote the actual claim/question as evidence; in `fix`, prescribe an achievable revision. Mark important unproven claims, but don't pad the script with irrelevant negative disclaimers. Add `audience_takeaway_test` and `missing_proof`.

Output `reviews/ai-story-review.json`, referencing the exact fingerprint of the supplied input. When unsure, report UNVERIFIED instead of inventing PASS. Run `board` so people see the critique in context.
