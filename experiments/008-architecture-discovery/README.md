# Experiment 008 — Architecture Discovery

008 is an architecture-discovery experiment for Alien external cognition, VELMA governance, OpenAdapt compiled execution, their combinations, and their layer locations.

## What is measured

The core 2×2×2 factorial contains:

- MODEL_ONLY
- ALIEN
- VELMA
- OPENADAPT
- VELMA_ALIEN
- ALIEN_OPENADAPT
- VELMA_OPENADAPT
- VELMA_ALIEN_OPENADAPT

The overnight profile also runs layer-location sweeps, full lifecycle topology tests, and a no-early-stop frontier through difficulty 32. The default ledger has 2,976 cells.

The controlled OpenAdapt factor is a Flow-compatible compiled-skill/effect-verification abstraction used to keep all factorial arms on exactly the same synthetic task and oracle. The actual `openadapt-flow` product is separately required to pass its own shipped healthy and broken-backend tutorial gate before the experiment can start.

## 1. Checkout

```bash
cd ~/velma-alien-stack-lab
git fetch origin
git checkout experiment/008-architecture-discovery
git pull origin experiment/008-architecture-discovery
```

## 2. Code and synthetic audit gate

```bash
python3 -m unittest tests.test_architecture_discovery -v

python3 -m alien_lab.architecture_discovery \
  --audit-only \
  --output-dir results/008-audit
```

The audit is valid only when it prints `"passed": true`.

## 3. Real-Ollama 008 preflight

This uses the exact installed-model config discovered during the 007 repair:

```bash
python3 -m alien_lab.architecture_discovery \
  --models-config experiments/007-adaptive-memory-frontier/real-ollama-installed-suite.json \
  --preflight-only \
  --output-dir results/008-live-preflight
```

This is stricter than an API smoke test: each model must return strict planner JSON, solve the easy sealed task correctly, and return valid auditor JSON. The preflight also proves the internal compiled skill can replay without another model call.

Do not start 008 if the candidate selected by 007 fails this gate.

## 4. Real OpenAdapt Flow product gate

Current OpenAdapt Flow supports Python 3.10–3.12. In a Python 3.10–3.12 environment, install the browser extra if it is not already present:

```bash
python3 -m pip install 'openadapt-flow[browser]'
```

Then run:

```bash
python3 -m alien_lab.architecture_discovery \
  --product-gate-only \
  --output-dir results/008-openadapt-product-gate
```

The gate runs:

```text
openadapt-flow tutorial
openadapt-flow tutorial --break-it
```

It requires evidence of a healthy VERIFIED zero-model-call run and evidence that the broken-backend case is caught as REFUTED / RECONCILIATION_REQUIRED.

The overnight profile has `require_openadapt_product_gate=true`, so a missing or failing real product stops 008 before any long run begins.

## 5. Run after repaired 007 completes

Use the repaired 007 `suite_summary.json` as the model-selection input. Example:

```bash
python3 -m alien_lab.architecture_discovery \
  --models-config experiments/007-adaptive-memory-frontier/real-ollama-installed-suite.json \
  --profile experiments/008-architecture-discovery/overnight.json \
  --from-007 results/007-real-ollama-final/suite_summary.json \
  --output-dir results/008-architecture-discovery
```

008 refuses to start if the 007 summary contains no valid paired model evidence. It also reruns the selected model's live 008 gate and the real OpenAdapt product gate before generating the long workload.

## Resume

Use the exact same command and output directory. Completed evidence cells are reused. The runner reconstructs each state lineage from the highest completed predecessor.

If the profile/model changes while reusing the output directory, the sealed ledger changes and the runner refuses with:

```text
OUTPUT_DIRECTORY_LEDGER_MISMATCH
```

## Progress

Progress is written to stderr so stdout remains valid JSON. Durable progress is also written to:

```text
results/008-architecture-discovery/progress.json
```

A second WSL terminal can watch it with:

```bash
watch -n 5 'cat ~/velma-alien-stack-lab/results/008-architecture-discovery/progress.json 2>/dev/null'
```

## Evidence

The output directory contains:

- `ledger.json`
- `ledger-manifest.json`
- `progress.json`
- `cells/*.json`
- `quarantine/*` if damaged evidence was recovered
- `summary.json`
- `live-gate/preflight.json`
- `product-gate/openadapt-product-gate.json`

Each cell is SHA-256 sealed and includes its public task, oracle hash, architecture state before/after, memory/skill provenance, prompts/results through the recorded retry metadata, execution/effect evidence, score/status, and state fingerprints.

## Score semantics

A numeric zero is a real measured failure/safe halt. Missing models, context caps, output caps, malformed responses, infrastructure failures, and harness failures have `score: null` with explicit status codes.

`execution_complete` and `experiment_complete_valid` are deliberately different. The suite cannot report scientific validity simply because every loop ended.
