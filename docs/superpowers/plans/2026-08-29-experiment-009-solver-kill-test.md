# Experiment 009 Solver Kill Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, zero-model-call falsification test that determines whether exact public-surface dependency solving can plausibly support at least 80% verified success on the Experiment 008 workload.

**Architecture:** Reuse Experiment 008 only for deterministic task generation and independent execution/scoring. Add a separate 009 public-surface parser/solver that accepts only `task.public_dict()`, emits a locator plan plus derivation, and is evaluated on 64 unseen solvable cells plus 16 silent-fault controls. Evidence is hash-sealed and the acceptance gate is 64/64 solvable successes with all silent controls correctly refuted.

**Tech Stack:** Python 3 standard library, existing `alien_lab.architecture_discovery` task generator/executor, `unittest`, SHA-256 JSON evidence.

**Spec:** `docs/superpowers/specs/2026-08-29-experiment-009-solver-kill-test-design.md`

## Global Constraints

- Solver model calls MUST equal exactly `0`.
- Solver input MUST be limited to `TaskSpec.public_dict()`; sealed `required_semantics` and `oracle_final` are scorer-only.
- Kill set MUST contain exactly `64` unseen solvable cells.
- Silent controls MUST contain exactly `16` cells and MUST NOT count toward capability success rate.
- PASS requires `64/64` authoritative verified successes and `16/16` expected silent-fault refutations.
- Evidence MUST be deterministic and SHA-256 sealed.
- No new third-party dependency is allowed.

---

### Task 1: Public-surface solver contract

**Files:**
- Create: `tests/test_solver_kill_test.py`
- Create: `alien_lab/solver_kill_test.py`

**Interfaces:**
- Consumes: public task dictionaries shaped like `TaskSpec.public_dict()`.
- Produces: `SolverResult(ok: bool, locators: tuple[str, ...], derivation: tuple[dict, ...], error: str | None)` via `solve_public_task(public_task: dict) -> SolverResult`.

- [ ] **Step 1: Write failing tests for exact solving and oracle-blind input**

```python
from alien_lab.architecture_discovery import build_task
from alien_lab.solver_kill_test import solve_public_task


def test_solver_recovers_unseen_difficulty_32_plan_from_public_surface_only():
    task = build_task(909001, "composition", 32, "NOVEL", "009-red")
    result = solve_public_task(task.public_dict())
    assert result.ok
    assert result.locators


def test_solver_rejects_ambiguous_public_graph():
    public = {
        "task_id": "ambiguous",
        "family": "linear_dependency",
        "difficulty": 2,
        "stage": "NOVEL",
        "lineage": "test",
        "initial": [1, 2, 3],
        "public_flag": 0,
        "surface": [
            {"locator": "x", "label": "action=A00 requires=START condition=any", "slot": 0, "forbidden": False},
            {"locator": "y", "label": "action=A01 requires=START condition=any", "slot": 1, "forbidden": False},
        ],
    }
    result = solve_public_task(public)
    assert not result.ok
    assert result.error == "AMBIGUOUS_SUCCESSOR:START"
```

- [ ] **Step 2: Run test to verify RED**

Run: `python3 -m unittest tests.test_solver_kill_test -v`

Expected: import failure because `alien_lab.solver_kill_test` does not exist.

- [ ] **Step 3: Implement minimal parser/solver**

Implement:

```python
@dataclass(frozen=True)
class SolverResult:
    ok: bool
    locators: tuple[str, ...]
    derivation: tuple[dict[str, Any], ...]
    error: str | None = None


def solve_public_task(public_task: dict[str, Any]) -> SolverResult:
    ...
```

Required behavior:

1. parse `action=<id> requires=<pred> condition=<cond>` with a full-match regex;
2. reject malformed labels, duplicate semantic ids, and duplicate locators;
3. exclude forbidden nodes, `requires=NEVER`, and false flag conditions;
4. require exactly one successor from `START` and then exactly one successor at each visited semantic id;
5. reject cycles and disconnected eligible nodes;
6. return current locators in solved semantic order;
7. record a derivation row for every public surface item with inclusion/exclusion reason.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `python3 -m unittest tests.test_solver_kill_test -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add deterministic public-surface solver`

---

### Task 2: Oracle-blind scientific harness and fixed 64+16 ledger

**Files:**
- Modify: `tests/test_solver_kill_test.py`
- Modify: `alien_lab/solver_kill_test.py`
- Create: `experiments/009-solver-kill-test/config.json`

**Interfaces:**
- Consumes: `build_task(...)`, `solve_public_task(task.public_dict())`, and scorer-only `execute_plan(task, locators)`.
- Produces: `build_kill_ledger(config: dict) -> list[KillCell]`, `run_cell(cell: KillCell) -> KillEvidence`, and `run_experiment(config: dict, output_dir: Path) -> dict`.

- [ ] **Step 1: Add failing tests for ledger size, unseen seeds, stratification, and silent-control isolation**

```python
def test_default_ledger_contains_exactly_64_solvable_and_16_controls():
    config = default_config()
    ledger = build_kill_ledger(config)
    assert sum(c.phase == "SOLVABLE_KILL" for c in ledger) == 64
    assert sum(c.phase == "SILENT_CONTROL" for c in ledger) == 16
    assert all(c.seed not in {20260829, 20260830} for c in ledger)


def test_solver_is_given_public_dict_not_taskspec():
    task = build_task(909002, "multi_record_join", 24, "TRANSFER", "009-public")
    result = solve_public_task(task.public_dict())
    outcome = execute_plan(task, list(result.locators))
    assert result.ok
    assert outcome.verified_success
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests.test_solver_kill_test -v`

Expected: failures for missing ledger/harness APIs.

- [ ] **Step 3: Implement deterministic ledger construction**

Use fixed defaults:

```python
SOLVABLE_FAMILIES = (
    "linear_dependency", "conditional_branch", "multi_record_join",
    "loop_worklist", "policy_guard", "composition", "drift_resolution",
)
SOLVABLE_STAGES = ("NOVEL", "PARAMETER_VARIATION", "DRIFT", "COMPOSITION", "TRANSFER")
DIFFICULTIES = (12, 16, 20, 24, 28, 32)
UNSEEN_SEEDS = tuple(range(20260901, 20260917))
```

Generate cells in deterministic round-robin order until exactly 64 solvable cells exist. Generate 16 controls by alternating `family="silent_effect_fault", stage="NOVEL"` and a normal family with `stage="SILENT_EFFECT_FAULT"`.

- [ ] **Step 4: Implement scorer separation**

The solver receives only `public = task.public_dict()`. Only after it returns does the harness call:

```python
outcome = execute_plan(task, list(result.locators))
```

For `SOLVABLE_KILL`, classify verified outcomes as `SOLVER_SUCCESS`; any solver/verification miss as `SOLVER_FAILURE`.

For `SILENT_CONTROL`, require `screen_success is True`, `authoritative_success is False`, and `verified_success is False`; classify that as `EXPECTED_REFUTATION`.

- [ ] **Step 5: Run tests to verify GREEN**

Run: `python3 -m unittest tests.test_solver_kill_test -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `feat: add 009 kill-test ledger and scorer`

---

### Task 3: Evidence sealing, Wilson gate, replay fingerprint, CLI

**Files:**
- Modify: `tests/test_solver_kill_test.py`
- Modify: `alien_lab/solver_kill_test.py`

**Interfaces:**
- Consumes: complete kill ledger and per-cell results.
- Produces: `ledger.json`, `cells/<cell_id>.json`, `summary.json`, deterministic replay fingerprint, and CLI exit status.

- [ ] **Step 1: Add failing tests for evidence integrity and exact PASS rule**

```python
def test_summary_requires_perfect_kill_set_and_controls(tmp_path):
    summary = run_experiment(default_config(), tmp_path)
    assert summary["solvable_total"] == 64
    assert summary["silent_control_total"] == 16
    assert summary["model_calls"] == 0
    assert summary["solver_kill_test_passed"] is True
    assert summary["solvable_successes"] == 64
    assert summary["silent_controls_correctly_refuted"] == 16
    assert summary["wilson95_lower"] > 0.9345
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests.test_solver_kill_test -v`

Expected: failures for missing persistence/summary APIs.

- [ ] **Step 3: Implement evidence envelope**

Store each evidence payload as:

```python
{"evidence": payload, "sha256": stable_hash(payload)}
```

Reject stale output directories if a preexisting `ledger-manifest.json` has a different ledger hash.

- [ ] **Step 4: Implement Wilson interval and PASS rule**

Compute Wilson 95% interval over only the 64 solvable cells.

`solver_kill_test_passed` is true only when:

```python
solvable_total == 64
and solvable_successes == 64
and silent_control_total == 16
and silent_controls_correctly_refuted == 16
and invalid_cells == 0
and model_calls == 0
and wilson95_lower > 0.9345
```

- [ ] **Step 5: Implement CLI**

Support:

```bash
python3 -m alien_lab.solver_kill_test \
  --config experiments/009-solver-kill-test/config.json \
  --output-dir results/009-solver-kill-test
```

Exit `0` on PASS, `4` on a valid scientific KILL, and `2` on invalid configuration/harness failure.

- [ ] **Step 6: Run tests to verify GREEN**

Run: `python3 -m unittest tests.test_solver_kill_test -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Commit message: `feat: seal and score experiment 009 evidence`

---

### Task 4: Experiment documentation and CI smoke gate

**Files:**
- Create: `experiments/009-solver-kill-test/README.md`
- Create: `.github/workflows/009-smoke.yml`

**Interfaces:**
- Consumes: completed solver/harness CLI.
- Produces: reproducible run instructions and automated test gate.

- [ ] **Step 1: Write README**

Document the hypothesis, exact 64/64 kill rule, 16 silent controls, oracle-blind contract, zero-model-call requirement, run command, outputs, and interpretation boundary.

- [ ] **Step 2: Add CI workflow**

Run:

```bash
python -m unittest tests.test_solver_kill_test -v
python -m alien_lab.solver_kill_test --config experiments/009-solver-kill-test/config.json --output-dir /tmp/009-smoke
```

- [ ] **Step 3: Run complete verification**

Run:

```bash
python3 -m unittest tests.test_solver_kill_test -v
python3 -m unittest tests.test_architecture_discovery -v
python3 -m compileall alien_lab tests
python3 -m alien_lab.solver_kill_test --config experiments/009-solver-kill-test/config.json --output-dir /tmp/009-final
```

Expected: all tests PASS and 009 summary reports `solver_kill_test_passed=true`, 64 solvable successes, 16 correct refutations, and 0 model calls.

- [ ] **Step 4: Commit**

Commit message: `docs: make experiment 009 reproducible`
