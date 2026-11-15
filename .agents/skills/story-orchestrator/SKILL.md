---
name: story-orchestrator
description: 登壇の構成から完成物までを段階的に進める。人間にストーリーを提示して明示的な承認を得るまで、スライドを作らない。
---

# Story-first orchestrator

Read `AGENTS.md` and `docs/WORKFLOW.md` before acting. For every talk, maintain `brief.json`, `story.json` and `evidence.json` as the narrative source. Never import presentation-specific content from the Kotlin Fest example.

## Sequence

1. Ask why this talk is valuable; inspect actual system/user pain, audience and decision at stake. Reuse details already supplied.
2. Call `story-architect`: write 2–3 materially different story directions into `candidates.json` with a recommendation and reason; expand the recommended one into `story.json` (`candidate_id`) as a chain of question → answer → next question, with `from_previous` and the author's `risks` per beat.
3. Record evidence statuses (`confirmed`, `limited`, `unverified`, `hypothesis`) and kinds (`fact`, `experiment`, `inference`, `plan`). Do not turn an imagined problem into a measured failure.
4. Run `python3 harness/storyflow.py audit <talk>`, `review-request <talk>` and a separate `story-critic`. Save the review at `<talk>/reviews/ai-story-review.json` with the exact fingerprint, including the whole-story `checks`. When `candidates.json` exists, also have a separate critic answer `build/ai-candidate-review-request.md` into `reviews/ai-candidate-review.json`.
5. Run `board <talk>`, show the user the generated HTML or Markdown, summarize the 2–3 most important risks and invite targeted edits and a candidate choice (one candidate or a mix). Do not create slides here. Do not silently simulate consent.
6. Incorporate user feedback in place. Repeat AI review only as needed for changed material; approval automatically becomes stale on any relevant content change.
7. Only after the user explicitly approves the current narrative, run `approve <talk> --human-confirmed --note '...'`. Then `draft <talk>`.
8. Use `deck-narrative`, `deck-prose`, `deck-figure`, `deck-direction`, `deck-delivery-qa` for the real deck. Validate beat anchors and meaning after production.

Keep loops light. Don't demand a formal review per slide. The narrator and first-time-audience critic must be separate contexts whenever possible. If a separate context is unavailable, mark independence false and report UNVERIFIED.
