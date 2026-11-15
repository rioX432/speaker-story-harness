---
name: story-orchestrator
description: 登壇の構成から完成物までを段階的に進める。人間にストーリーを提示して明示的な承認を得るまで、スライドを作らない。
---

# Story-first orchestrator

Read `AGENTS.md` and `docs/WORKFLOW.md` before acting. For every talk, maintain `brief.json`, `story.json` and `evidence.json` as the narrative source. Never import presentation-specific content from the Kotlin Fest example.

## Sequence

1. Ask why this talk is valuable; inspect actual system/user pain, audience and decision at stake. Reuse details already supplied.
2. Call `story-architect`: propose 2–3 materially different story directions when useful; choose one and build a chain of question → answer → next question. State the chosen direction and its rejected alternatives succinctly.
3. Record evidence statuses: `confirmed`, `limited`, `unverified`, `hypothesis`. Do not turn an imagined problem into a measured failure.
4. Run `python3 harness/storyflow.py audit <talk>`, `review-request <talk>` and a separate `story-critic`. Save the review at `<talk>/reviews/ai-story-review.json` with the exact fingerprint.
5. Run `board <talk>`, show the user the generated HTML or Markdown, summarize the 2–3 most important risks and invite targeted edits. Do not create slides here. Do not silently simulate consent.
6. Incorporate user feedback in place. Repeat AI review only as needed for changed material; approval automatically becomes stale on any relevant content change.
7. Only after the user explicitly approves the current narrative, run `approve <talk> --human-confirmed --note '...'`. Then `draft <talk>`.
8. Use `deck-narrative`, `deck-prose`, `deck-figure`, `deck-direction`, `deck-delivery-qa` for the real deck. Validate beat anchors and meaning after production.

Keep loops light. Don't demand a formal review per slide. The narrator and first-time-audience critic must be separate contexts whenever possible. If a separate context is unavailable, mark independence false and report UNVERIFIED.
