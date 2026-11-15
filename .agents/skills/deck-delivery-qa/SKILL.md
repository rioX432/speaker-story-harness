---
name: deck-delivery-qa
description: 承認後のスライド、台本、実描画、計測根拠、時間と本番配信媒体を最終監査する。
---

# Delivery QA

Run `python3 harness/storyflow.py deck-audit <talk>` first. Check any additional source-specific graph/evidence QA available from the renderer. Then inspect actual PDF/PPTX/HTML/Google Slides output rather than claiming QA based on source files only.

Validate: main-slide count and sequence; readable typography at distance; charts with unit, numerator/denominator and measured endpoint; no visual crop; speaker notes not overloaded with production metadata; demo working plus still fallback; claims supported by the exact bounded evidence; speaker-friendly Japanese; time from an actual read-through; beginning and end connected.

Distinguish machine PASS, AI semantic judgment, speaker rehearsal, human audience feedback, venue/projector checks. Do not upgrade unverified items to PASS because other checks succeeded. Revise local failures without forcing every unrelated step to restart, unless the story changes.
