# Experiment 003 — Scoring Repair Validation

Experiments 001 and 002 are preserved as compute/provenance evidence, but their capability scores are invalid because every generation exhausted the output budget in Ollama's `thinking` channel and left the scored `response` blank.

Experiment 003 repairs that failure before any new hour-scale run.

## Protocol

1. Hold `qwen3.5:9b-q8_0` and context 25,600 fixed.
2. Force `think=false` for the primary capability-validation path.
3. Run three live six-task preflight packets: RAW, STRUCTURED, FULL.
4. Require all six final answers to be parseable in every preflight packet.
5. Require nonblank final responses and no generation-ceiling hit.
6. If any preflight check fails, abort before the causal cube starts.
7. If preflight passes, run exactly one required 64-subset Boolean cube plus RAW.
8. Disable all optional experiment phases for this validation run.
9. Any blank, malformed, incomplete, or ceiling-hit completion is `UNSCORABLE`, never `WRONG`.
10. Capability analysis is valid only if all 65 discovery generations are scorable.

This experiment is intentionally short. Its purpose is evaluator integrity, not maximum statistical power.

## Step 1 — preflight only

```bash
python3 -m alien_lab.scoring_repair \
  --config experiments/003-scoring-repair/config.json \
  --preflight-only
```

Do not start the cube unless the printed report says:

```text
"passed": true
```

and all three conditions report 6/6 parseable answers with `hit_ceiling: false`.

## Step 2 — one validation cube

After a passing preflight:

```bash
python3 -m alien_lab.scoring_repair \
  --config experiments/003-scoring-repair/config.json
```

Results are written to:

`results/003-scoring-repair-validation/`

The full-hour replication experiment should only be designed after Experiment 003 proves capability scoring is valid.
