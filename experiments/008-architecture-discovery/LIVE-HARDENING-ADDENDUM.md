# Experiment 008 — Live Hardening Addendum

Date: 2026-08-29
Status: preregistered before the repaired Experiment 007 overnight result exists.

## Why this addendum exists

The first real-Ollama 008 preflight exposed two distinct issues that synthetic/fake clients could not reveal:

1. Several otherwise-correct local models returned the required JSON object wrapped in one standard Markdown code fence.
2. Some models produced objectively wrong plans on the easy 008 capability task even though they were valid candidates for Experiment 007.

Neither issue may be hidden by scoring or post-hoc model choice.

## Transport normalization rule

At the model-output boundary, 008 may losslessly remove exactly one outer Markdown code fence when:

- the opener is exactly ``` or ```json (case-insensitive for `json`);
- the closer is exactly ```;
- there is no nested code fence inside; and
- the remaining payload parses as one JSON object.

008 must NOT extract a JSON object from surrounding prose, repair keys/values, infer missing steps, reorder actions, or otherwise change model semantics.

The original raw response remains in evidence. Thus Markdown-fence noncompliance remains observable even though it is not confused with reasoning capability.

## Cross-experiment model-selection rule

Experiment 007 remains authoritative for ranking models by its preregistered memory criteria:

1. higher `paired_retrieved_minus_none_mean`;
2. tie-break by higher RETRIEVED `last_passing_level`;
3. tie-break by original 007 suite order.

Experiment 008 then applies an independent capability eligibility gate to that fixed ranking.

The 008 primary model is:

> the highest-ranked scientifically valid 007 model, in the order above, that is present in the 008 live config and passes the 008 real-Ollama planner/auditor capability preflight.

A higher-ranked 007 model that fails the 008 gate is not silently reclassified or scored as weaker in 007; it is retained in the selection evidence as `LIVE_PREFLIGHT_FAILED`, and 008 proceeds to the next ranked candidate.

If no ranked valid 007 model passes the 008 live gate, Experiment 008 does not start.

The complete sequence of attempted candidates and their preflight reports is written to `model-selection-gate.json`.

## What remains a real capability failure

A syntactically recoverable transport wrapper does not excuse an objectively wrong plan. Plans that omit required actions, include distractor/forbidden actions, execute in the wrong order, or fail the authoritative final-state/effect check remain capability failures.

## Reason for preregistration timing

This rule is recorded before the repaired 007 overnight experiment is launched and therefore before its gain/frontier ranking is known. The fallback rule cannot be tuned to favor the eventual 007 winner.
