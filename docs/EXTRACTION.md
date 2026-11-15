# Extraction and provenance audit

Reviewed source: private `rioX432/kotlinfest-2026`, `main`, on 2026-11-15. Verified top-level `HARNESS_ARCHITECTURE.md`, `HARNESS_AUDIT.md`, `harness/README.md`, `.agents/skills/*/SKILL.md`, `references/presentation-engineering-workflow.md`, `SKILLS.md`, `NARRATIVE_EVALUATION.md`, and repository tree. The original repository has thousands of files and 1GB-scale generated materials; *do not mirror it*.

| Source capability | Independent harness choice |
| --- | --- |
| `deck-narrative`: Big Idea and understanding dependencies | Adapted into `story-architect`, `deck-narrative`, mandatory problem/baseline/alternative chain |
| `deck-audience-review`: separate listener perspective | Adapted into `story-critic` (before slides) and `deck-audience-review` (after slides) |
| `deck-prose` / `deck-figure` / `deck-direction` | Content/visual/rhythm rules retained as lightweight domain-agnostic skills |
| `rio-conference-slides` | Principles of claim-first information design absorbed; individual font/layout/brand presets not brought over |
| `harness/presentation_harness.py`: prepare/check/packet/compare | **Not copied verbatim:** original deck schema and profile differ. `harness/storyflow.py` is new pre-slide human-approval gate. Original CLI can still be run later as an optional second QA layer for compatible slide JSON |
| `harness/schemas`, concept/profile checks, evidence hashes | Conceptual contract retained. JSON content hashes bind review/approval to changed story |
| `delivery-v*/authoring/`, actual slides, evidence videos, image assets | Excluded because tied to a single talk and potentially non-public/licensed |
| `kotlinfest-daily`, Git sync scripts, proprietary devices | Excluded because unrelated to generic talk development and may be destructive when copied |

**Important:** This is a new portable implementation of the reusable workflow, not a 1:1 fork of original Python renderers or exact old unit tests. Run the original `harness/presentation_harness.py` alongside this one when you want its more advanced *post-slide* concept dependency and evidence checks. This standalone package does not claim to have ported all those checks.

## Optional reuse of the original renderer-independent QA

For a local, authorized checkout of the original repo, see `scripts/import-legacy-qa.py`. It selectively copies only the reusable original CLI and schemas into `legacy-qa/`, without any presentation-specific profile, recordings or fonts. Do not invoke this on a source repository you cannot legally reuse. Keep its original provenance notice. The old CLI's input schema is independent of the new `story.json`; a JSON adapter is needed when applying it to new slide formats.

## Security / publishing

The original repo is private. Do not assume files may be published simply because they were available to the authenticated GitHub connector. This repo is published as a **public** MIT-licensed repository; the bundled example is a fictional topic with illustrative numbers and is not a performance report of any product. Before adding material to the repo, review every asset, user name, company detail and source license.
