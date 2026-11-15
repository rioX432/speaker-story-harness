# Slides, script and quality after story approval

The harness is **renderer-agnostic**. Do not copy V14's project-specific Python layouts, Google Slides IDs, fonts, videos, biometric data or product assets into the independent repository.

1. `draft`: creates the approved, beat-anchored slide outline.
2. Slide author AI: build a deck with one clear assertion per slide and the minimal compelling evidence, code, diagram, live demo or image that supports it. A beat may use several slides. The *talk* remains the source, not a bag of slides.
3. Script AI: write only what is natural to speak and explains the evidence at the same moment it is shown. Put presenter cues and provenance separately.
4. Renderer: choose the existing Marp/Slidev/Google Slides/PPTX/HTML workflow for the event. Tool dependencies are optional and not bundled.
5. `deck-audit`: verify the approved storyline order and fingerprint in authored Markdown. For custom renderers preserve equivalent beat IDs and source hashes in a manifest.
6. QA: inspect the actual rendering for cropping, legibility, accurate numerical labels, visual continuity and multimedia fallback. Verify script vs displayed claim, measured vs proposed, time and transitions. Ensure the ending answers the talk's initial problem.
7. Blind audience check: supply only sequential deck frames and spoken notes, not author goals or future slides; ask a fresh reviewer for a 1-sentence takeaway and its evidence. Human rehearsal remains separate.

## Recommended outputs in a talk repository

```text
brief.json
story.json
evidence.json
candidates.json
reviews/ai-candidate-review.json
reviews/ai-story-review.json
reviews/human-feedback.json
approvals/story-approved.json
build/storyboard.html
build/storyboard.md
draft/slides.md
draft/speaker-notes.md
delivery/presentation.pdf
delivery/presentation.pptx
delivery/qa-report.md
```

An optional Marp CLI path (if independently installed): `npx @marp-team/marp-cli draft/slides.md --pdf -o delivery/presentation.pdf`. The generated skeleton is **not** a finished Marp deck: add actual content and speaker notes first. Check the output visually. Some output formats and tool versions need additional local configuration.
