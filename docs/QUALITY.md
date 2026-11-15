# Story quality criteria

Do not reduce a speech to a numeric score. Ask whether each of these statements is supportable from the actual storyline and its evidence:

- The listener knows *why the problem matters* before hearing the proposed solution.
- The talk distinguishes a real bottleneck, a likely future bottleneck and a thought experiment.
- The existing solution gets a serious, fair baseline and feasible optimization path.
- A new technology enters as a hypothesis for solving a residual problem, not a predetermined winner.
- Every section answers a question the prior section naturally created.
- Contradictory results are explained in terms of the decision, not presented as unrelated loose ends.
- Demonstration conditions, device differences and measurement endpoints do not silently turn into generic claims.
- The ending responds to the opening question with actionable selection conditions.
- The user can read the storyboard in a few minutes and give targeted edits.
- A separate first-time listener can explain what changed in their understanding without receiving the author's answer key.

## AI reviewer output

At minimum: concrete beat identifier; verbatim claim or question; risk and why it matters; severity `critical/major/minor`; specific revision suggestion; status `open/resolved/accepted_risk`.

The story review also answers every whole-story check from `brief.review_checks` (or the generic defaults) as `checks:[{check, verdict, reason, fix}]`, copying the check text verbatim. `verdict` is `pass/partial/fail/unknown`; `partial` and `fail` need a structural `fix`, and `audit` warns about them until they are resolved. Answering the same check twice is an error; once a review has `checks`, `audit` also warns about any check it left unanswered (older reviews without `checks` are unaffected).

A candidate comparison review (`reviews/ai-candidate-review.json`) judges each candidate for accuracy, inevitability, causality, first-time comprehension and interest: `candidates:[{candidate_id, verdict, strengths, breakpoints, criteria:[{criterion, assessment}]}]`, plus `summary` and an optional `recommended`. `audit` warns about any candidate the review does not cover. More technical detail is not a reason to prefer a candidate. Any reviewer who has read the author's private plan or model answer is **not** an independent initial-audience reviewer.

## The difference between caution and self-sabotage

Keep all material limitations that affect the truth of the assertion. Do not force the speaker to recite every unimplemented idea or unsuccessful experiment. For example, 'the demonstration's **internal Core** was faster under these conditions' is more precise and persuasive than a vague 'Rust is always faster'; however 'we were not able to test dozens of unrelated caveats' should not consume a slide unless it changes the recommendation.
