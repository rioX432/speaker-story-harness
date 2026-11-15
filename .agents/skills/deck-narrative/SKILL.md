---
name: deck-narrative
description: 承認後のスライド順序がストーリーの問い・理解依存・根拠と整合しているかを保つ。
---

# Preserve the approved argument

This is an adaptation of the narrative principles in `kotlinfest-2026/.agents/skills/deck-narrative`. Read `story.json` and its human approval first. Do **not** devise a second story inside the slide generator.

Before each section ask which audience question it answers and what knowledge must already have been introduced. Maintain concept prerequisites, evidence scope and section transitions. One claim per slide is the focal point, not a one-sentence limit on all explanatory labels. Use multiple slides for genuinely necessary explanations without adding unrelated beats.

Keep `<!-- story-beat:B1 -->` metadata in Markdown decks. Run `deck-audit` and investigate every missing beat, reordered explanation, stale approval fingerprint, and unsupported conclusion. If the agreed story changes materially, go back to the human story preview rather than silently reshaping the talk.
