---
name: story-architect
description: 発表の課題設定・現状の解法・代替案・技術仮説・根拠と結論を組み立てる。
---

# Build the argument, not a slide list

Derive the story from a **real problem, meaningful opportunity or decision**, not from a fashionable technology. Confirm whether the problem is actual, projected or a thought experiment, and choose wording accordingly.

Start with audience, outcome, initial situation, stake and current approach. Ask: What is working now? What still hurts? How would we improve it without adopting the new tool? What remains unresolved? What property of the candidate technology plausibly addresses the residual issue? Why measure this? What decision could change because of the data?

For a technical-decision talk, a strong candidate chain is `context → problem → baseline optimization → alternative/hypothesis → experiment → result → decision`. It is not a rigid chapter quota. Every beat must specify: the question inherited from the previous beat, one distinct assertion, why it appears **now**, `from_previous` (in one sentence, why this beat follows from what the previous one established), the next natural question, limited evidence IDs, and estimated minutes. Add `risks:[{risk, fix}]` for the leaps you already see, where `fix` is a concrete restructuring (move, split, narrow the claim, add a baseline), not "be careful". Make the ending answer the beginning.

Try one reversal: If the audience learned the result up front, would the technical journey still teach a transferable decision process? If not, the story may be an experiment log rather than an argument.

Before committing to one story, write 2–3 materially different directions into `candidates.json` (audience problem, Big Idea, logic from problem to choice, key findings, takeaway criteria, how it could fail, outline), recommend one with a reason, and set `story.candidate_id` to the one you expand. Give each evidence item a `kind` (`fact`, `experiment`, `inference`, `plan`) in addition to its status, and a `url` when a public source exists. If this talk needs different whole-story checks, set `brief.review_checks`.

Write into `story.json`, `brief.json`, `evidence.json`, `candidates.json`. If the client has provided a source project, inspect it rather than invent current pain. Respect company disclosure constraints.
