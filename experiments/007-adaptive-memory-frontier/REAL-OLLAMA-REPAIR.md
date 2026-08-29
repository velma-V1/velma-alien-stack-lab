# Experiment 007 — Real Ollama Repair Run

This repair exists because the first final-suite execution completed its loops with zero scorable paired packets. It is not a capability result.

## Root causes fixed

1. The original shared Ollama client defaulted `think=True` when the runner omitted the argument.
2. Non-thinking models could reject that request with HTTP 400.
3. Thinking models could consume the 96-token output budget in hidden reasoning and return `done_reason=length` before a scorable final response.
4. Missing exact model tags were allowed to consume the full ladder as HTTP 404 failures.
5. `completed=true` meant loop completion even when `paired_packet_count=0`.

`alien_lab.repaired_memory_frontier` fixes these without rewriting the frozen failed-run evidence:

- `/api/tags` is authoritative for exact local availability and capabilities;
- installed thinking-capable models receive `think=false`;
- installed non-thinking models receive no `think` field;
- every enabled model must pass a live three-arm format preflight before level 1;
- unavailable or preflight-failed models never enter the 48-level ladder;
- zero paired packets can never be reported as a scientifically completed model;
- suite validity is separate from execution progress.

## Exact installed suite

The repair config reflects the Windows Ollama `/api/tags` response supplied on 2026-08-28:

- `qwen3.5:9b` — Q4_K_M
- `qwen3.5:9b-q8_0` — Q8_0 quantization control
- `qwen3:8b` — Q4_K_M
- `gemma3:12b` — Q4_K_M
- `qwen3:14b` — Q4_K_M
- `qwen2.5-coder:14b` — Q4_K_M
- `devstral-small-2:24b` — Q4_K_M
- `huihui_ai/mistral-small-abliterated:24b` — Q4_K_M, labeled only as an abliterated-model comparator

The originally requested `qwen3.8:27b` and exact AliBilge abliterated Devstral tag are recorded in config as unavailable. They are not silently substituted.

## Mandatory gate

From WSL at the repository root:

```bash
python3 -m unittest tests.test_final_memory_frontier tests.test_repaired_memory_frontier -v
python3 -m alien_lab.repaired_memory_frontier \
  --config experiments/007-adaptive-memory-frontier/real-ollama-installed-suite.json \
  --output-dir results/007-real-ollama-preflight \
  --preflight-only
```

Do not start the long run unless both commands succeed.

## Full run

Use a fresh output directory. Never reuse the failed final-suite directory.

```bash
python3 -m alien_lab.repaired_memory_frontier \
  --config experiments/007-adaptive-memory-frontier/real-ollama-installed-suite.json \
  --output-dir results/007-real-ollama-repair
```

The process remains resumable through the inherited per-variant checkpoints. A preflight failure is terminalized before the expensive ladder and cannot masquerade as a zero capability score.
