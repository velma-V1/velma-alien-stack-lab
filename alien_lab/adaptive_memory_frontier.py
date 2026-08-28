from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .experiment import ExperimentConfig, parse_packet_response
from .ollama import ModelResult, OllamaClient
from .records import append_jsonl, stable_hash
from .scoring_repair import StrictFinalAnswerClient


ARM_NONE = "NONE"
ARM_FULL = "FULL"
ARM_RETRIEVED = "RETRIEVED"
MEMORY_ARMS = (ARM_NONE, ARM_FULL, ARM_RETRIEVED)
MODULUS = 97
BOOTSTRAP_RULES = 12
RULES_PER_LEVEL = 12
TASKS_PER_LEVEL = 8
MAX_LEVEL = 30
FRONTIER_PASS_THRESHOLD = 7 / 8
CONSERVATIVE_BYTES_PER_TOKEN = 3


@dataclass(frozen=True)
class MemoryRule:
    rule_id: str
    a: int
    b: int
    modulus: int
    learned_level: int
    evidence_id: str
    fingerprint: str

    def apply(self, value: int) -> int:
        return (self.a * value + self.b) % self.modulus

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryTask:
    task_id: str
    start_value: int
    rule_ids: tuple[str, ...]
    choices: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "start_value": self.start_value,
            "rule_ids": list(self.rule_ids),
            "choices": dict(self.choices),
        }


class MemoryStore:
    def __init__(self) -> None:
        self._rules: dict[str, MemoryRule] = {}
        self._order: list[str] = []

    def append(self, rules: Iterable[MemoryRule]) -> None:
        pending = tuple(rules)
        duplicate = next((rule.rule_id for rule in pending if rule.rule_id in self._rules), None)
        if duplicate is not None:
            raise ValueError(f"memory rule already exists: {duplicate}")
        pending_ids = [rule.rule_id for rule in pending]
        if len(set(pending_ids)) != len(pending_ids):
            raise ValueError("memory append contains duplicate rule ids")
        for rule in pending:
            self._rules[rule.rule_id] = rule
            self._order.append(rule.rule_id)

    def get(self, rule_id: str) -> MemoryRule:
        try:
            return self._rules[rule_id]
        except KeyError as exc:
            raise KeyError(f"unknown memory rule: {rule_id}") from exc

    def all_rules(self) -> tuple[MemoryRule, ...]:
        return tuple(self._rules[rule_id] for rule_id in self._order)

    def snapshot_fingerprint(self) -> str:
        return stable_hash([rule.to_dict() for rule in self.all_rules()])

    def __len__(self) -> int:
        return len(self._order)


def _rule_fingerprint(
    rule_id: str,
    a: int,
    b: int,
    modulus: int,
    learned_level: int,
    evidence_id: str,
) -> str:
    return stable_hash(
        {
            "rule_id": rule_id,
            "a": a,
            "b": b,
            "modulus": modulus,
            "learned_level": learned_level,
            "evidence_id": evidence_id,
        }
    )


def generate_rules(
    seed: int,
    *,
    start_index: int,
    count: int,
    learned_level: int,
) -> tuple[MemoryRule, ...]:
    if start_index < 1 or count < 1 or learned_level < 0:
        raise ValueError("invalid rule generation bounds")
    rng = random.Random(seed + start_index * 1009 + learned_level * 100_003)
    rules: list[MemoryRule] = []
    for index in range(start_index, start_index + count):
        rule_id = f"M{index:04d}"
        a = rng.randint(2, MODULUS - 1)
        b = rng.randint(1, MODULUS - 1)
        evidence_id = f"lesson:{learned_level}:{index}"
        rules.append(
            MemoryRule(
                rule_id=rule_id,
                a=a,
                b=b,
                modulus=MODULUS,
                learned_level=learned_level,
                evidence_id=evidence_id,
                fingerprint=_rule_fingerprint(
                    rule_id,
                    a,
                    b,
                    MODULUS,
                    learned_level,
                    evidence_id,
                ),
            )
        )
    return tuple(rules)


def bootstrap_store(seed: int) -> MemoryStore:
    store = MemoryStore()
    store.append(generate_rules(seed, start_index=1, count=BOOTSTRAP_RULES, learned_level=0))
    return store


def composition_depth(level: int) -> int:
    if level < 1:
        raise ValueError("level must be >= 1")
    return level + 2


def _apply_sequence(store: MemoryStore, start: int, rule_ids: Iterable[str]) -> int:
    value = start
    for rule_id in rule_ids:
        value = store.get(rule_id).apply(value)
    return value


def _select_rule_ids(rng: random.Random, level: int, store: MemoryStore) -> tuple[str, ...]:
    rules = list(store.all_rules())
    depth = composition_depth(level)
    if len(rules) < depth:
        raise ValueError(f"level {level} needs {depth} learned rules but store has {len(rules)}")
    if any(rule.learned_level >= level for rule in rules):
        raise ValueError("challenge memory contains a rule not acquired before this level")

    selected: list[MemoryRule] = []
    learned_levels = sorted({rule.learned_level for rule in rules})
    if len(learned_levels) > 1 and depth >= 2:
        oldest = [rule for rule in rules if rule.learned_level == learned_levels[0]]
        newest = [rule for rule in rules if rule.learned_level == learned_levels[-1]]
        selected.extend([rng.choice(oldest), rng.choice(newest)])

    remaining = [rule for rule in rules if rule.rule_id not in {item.rule_id for item in selected}]
    rng.shuffle(remaining)
    selected.extend(remaining[: depth - len(selected)])
    rng.shuffle(selected)
    return tuple(rule.rule_id for rule in selected)


def _distractors(store: MemoryStore, start: int, rule_ids: tuple[str, ...], correct: int) -> list[int]:
    candidates: list[int] = []
    if len(rule_ids) > 1:
        candidates.append(_apply_sequence(store, start, rule_ids[:-1]))
        candidates.append(_apply_sequence(store, start, tuple(reversed(rule_ids))))
    candidates.extend([(correct + 1) % MODULUS, (correct - 1) % MODULUS, start])
    unique: list[int] = []
    for value in candidates:
        if value != correct and value not in unique:
            unique.append(value)
    probe = 2
    while len(unique) < 3:
        value = (correct + probe * 7) % MODULUS
        if value != correct and value not in unique:
            unique.append(value)
        probe += 1
    return unique[:3]


def build_level_packet(
    seed: int,
    level: int,
    store: MemoryStore,
    *,
    variant: int = 0,
    task_count: int = TASKS_PER_LEVEL,
) -> tuple[tuple[MemoryTask, ...], dict[str, dict[str, Any]]]:
    if level < 1 or variant < 0 or task_count < 1:
        raise ValueError("invalid packet bounds")
    rng = random.Random(seed + level * 10_007 + variant * 1_000_003)
    tasks: list[MemoryTask] = []
    sealed: dict[str, dict[str, Any]] = {}
    for position in range(1, task_count + 1):
        rule_ids = _select_rule_ids(rng, level, store)
        start = rng.randrange(MODULUS)
        correct_value = _apply_sequence(store, start, rule_ids)
        values = [correct_value, *_distractors(store, start, rule_ids, correct_value)]
        rng.shuffle(values)
        letters = "ABCD"
        choices = {letter: value for letter, value in zip(letters, values)}
        answer = next(letter for letter, value in choices.items() if value == correct_value)
        task_id = f"memory-L{level}-V{variant}-T{position}"
        task = MemoryTask(task_id=task_id, start_value=start, rule_ids=rule_ids, choices=choices)
        tasks.append(task)
        sealed[task_id] = {
            "answer": answer,
            "final_value": correct_value,
            "deterministic_unique": True,
        }
    return tuple(tasks), sealed


def _referenced_rule_ids(tasks: Iterable[MemoryTask]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for task in tasks:
        for rule_id in task.rule_ids:
            if rule_id not in seen:
                seen.add(rule_id)
                ordered.append(rule_id)
    return tuple(ordered)


def _memory_rules_for_arm(
    tasks: tuple[MemoryTask, ...], store: MemoryStore, arm: str
) -> tuple[MemoryRule, ...]:
    if arm == ARM_NONE:
        return ()
    if arm == ARM_FULL:
        return store.all_rules()
    if arm == ARM_RETRIEVED:
        referenced = set(_referenced_rule_ids(tasks))
        return tuple(rule for rule in store.all_rules() if rule.rule_id in referenced)
    raise ValueError(f"unknown memory arm: {arm}")


def _render_rule(rule: MemoryRule) -> str:
    return (
        f"{rule.rule_id} next=({rule.a}*current+{rule.b}) mod {rule.modulus} "
        f"learned_level={rule.learned_level} evidence={rule.evidence_id} fp={rule.fingerprint}"
    )


def render_memory_packet(
    tasks: tuple[MemoryTask, ...], store: MemoryStore, arm: str
) -> tuple[str, tuple[str, ...]]:
    rules = _memory_rules_for_arm(tasks, store, arm)
    parts = [
        "EXTERNAL MEMORY FRONTIER",
        "Every task is independent except that all may consult the validated external memory below.",
        "Apply referenced memory transformations exactly in the listed order.",
        f"MEMORY ARM: {arm}",
        "VALIDATED EXTERNAL MEMORY",
    ]
    if rules:
        parts.extend(_render_rule(rule) for rule in rules)
    else:
        parts.append("NO MEMORY RECORDS AVAILABLE")

    for index, task in enumerate(tasks, 1):
        parts.extend(
            [
                f"TASK {index}",
                f"START REGISTER: {task.start_value}",
                "APPLY RULE IDS IN ORDER: " + " -> ".join(task.rule_ids),
                "CHOICES",
                *(f"{letter}: {value}" for letter, value in task.choices.items()),
            ]
        )
    pattern = " ".join(f"{i}:<LETTER>" for i in range(1, len(tasks) + 1))
    parts.extend(
        [
            "PACKET OUTPUT CONTRACT",
            f"Return exactly one letter per task in this format: {pattern}",
            "No explanation in the final response.",
        ]
    )
    return "\n\n".join(parts), tuple(rule.rule_id for rule in rules)


def _preflight_memory() -> tuple[MemoryStore, tuple[MemoryTask, ...], dict[str, dict[str, Any]]]:
    store = MemoryStore()
    rules = (
        MemoryRule("P0001", 1, 1, MODULUS, 0, "preflight:1", _rule_fingerprint("P0001", 1, 1, MODULUS, 0, "preflight:1")),
        MemoryRule("P0002", 1, 2, MODULUS, 0, "preflight:2", _rule_fingerprint("P0002", 1, 2, MODULUS, 0, "preflight:2")),
    )
    store.append(rules)
    tasks = (
        MemoryTask("preflight-1", 1, ("P0001",), {"A": 2, "B": 3, "C": 4, "D": 5}),
        MemoryTask("preflight-2", 3, ("P0002",), {"A": 5, "B": 4, "C": 6, "D": 7}),
    )
    sealed = {
        "preflight-1": {"answer": "A", "final_value": 2, "deterministic_unique": True},
        "preflight-2": {"answer": "A", "final_value": 5, "deterministic_unique": True},
    }
    return store, tasks, sealed


def deterministic_preflight(seed: int) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    a = bootstrap_store(seed)
    b = bootstrap_store(seed)
    checks.append({"name": "stable_bootstrap", "passed": a.snapshot_fingerprint() == b.snapshot_fingerprint()})

    packet_a, sealed_a = build_level_packet(seed, 1, a)
    packet_b, sealed_b = build_level_packet(seed, 1, b)
    checks.append(
        {
            "name": "stable_packet",
            "passed": [task.to_dict() for task in packet_a] == [task.to_dict() for task in packet_b] and sealed_a == sealed_b,
        }
    )

    unique_answers = all(
        len(set(task.choices.values())) == 4 and sealed_a[task.task_id]["answer"] in task.choices
        for task in packet_a
    )
    checks.append({"name": "unique_sealed_answers", "passed": unique_answers})

    none_prompt, none_ids = render_memory_packet(packet_a, a, ARM_NONE)
    full_prompt, full_ids = render_memory_packet(packet_a, a, ARM_FULL)
    retrieved_prompt, retrieved_ids = render_memory_packet(packet_a, a, ARM_RETRIEVED)
    referenced = set(_referenced_rule_ids(packet_a))
    checks.append({"name": "none_is_empty", "passed": none_ids == () and "next=(" not in none_prompt})
    checks.append({"name": "full_is_complete", "passed": set(full_ids) == {rule.rule_id for rule in a.all_rules()}})
    checks.append({"name": "retrieval_is_exact", "passed": set(retrieved_ids) == referenced})

    memory_prefixes = [full_prompt.split("TASK 1", 1)[0], retrieved_prompt.split("TASK 1", 1)[0]]
    checks.append(
        {
            "name": "memory_has_no_answer_key",
            "passed": all("CHOICES" not in prefix and "answer=" not in prefix and "expected=" not in prefix for prefix in memory_prefixes),
        }
    )

    store = bootstrap_store(seed)
    metrics: list[tuple[int, int]] = []
    prior_rule_ok = True
    for level in range(1, 7):
        tasks, _ = build_level_packet(seed, level, store)
        metrics.append((len(store), composition_depth(level)))
        prior_rule_ok = prior_rule_ok and all(
            store.get(rule_id).learned_level < level for task in tasks for rule_id in task.rule_ids
        )
        store.append(
            generate_rules(
                seed,
                start_index=len(store) + 1,
                count=RULES_PER_LEVEL,
                learned_level=level,
            )
        )
    checks.append(
        {
            "name": "difficulty_monotonic",
            "passed": all(a_count < b_count and a_depth < b_depth for (a_count, a_depth), (b_count, b_depth) in zip(metrics, metrics[1:])),
        }
    )
    checks.append({"name": "only_prior_rules_used", "passed": prior_rule_ok})

    parsed = parse_packet_response("1:A 2:B 3:C 4:D", ["a", "b", "c", "d"])
    checks.append({"name": "strict_packet_parser", "passed": parsed == {"a": "A", "b": "B", "c": "C", "d": "D"}})
    checks.append(
        {
            "name": "two_failure_confirmation_rule",
            "passed": not confirmed_failure_values(0.75, 1.0) and confirmed_failure_values(0.75, 0.75),
        }
    )

    return {"seed": seed, "checks": checks, "passed": all(check["passed"] for check in checks)}


def confirmed_failure_values(primary_accuracy: float | None, confirmation_accuracy: float | None) -> bool:
    if primary_accuracy is None or confirmation_accuracy is None:
        return False
    return primary_accuracy < FRONTIER_PASS_THRESHOLD and confirmation_accuracy < FRONTIER_PASS_THRESHOLD


class AdaptiveMemoryRunner:
    def __init__(
        self,
        config: ExperimentConfig,
        *,
        client: Any,
        output_dir: Path | None = None,
        clock=time.monotonic,
    ) -> None:
        self.config = config
        self.client = client
        self.output_dir = output_dir or Path("results") / config.experiment_id
        self.clock = clock
        self._started = 0.0
        self._deadline = 0.0
        self._run_seq = 0
        self.call_durations_seconds: list[float] = []
        self.levels: list[dict[str, Any]] = []
        self.summary: dict[str, Any] = {}

    def confirmed_failure(self, *, primary_accuracy: float | None, confirmation_accuracy: float | None) -> bool:
        return confirmed_failure_values(primary_accuracy, confirmation_accuracy)

    def _remaining(self) -> float:
        if self._deadline <= 0:
            return self.config.ceiling_minutes * 60.0
        return max(0.0, self._deadline - self.clock())

    def _p95_duration(self) -> float:
        values = sorted(value for value in self.call_durations_seconds if value > 0)
        if not values:
            return 30.0
        index = max(0, math.ceil(0.95 * len(values)) - 1)
        return values[index]

    def _can_start_level(self) -> bool:
        estimated = max(180.0, self._p95_duration() * 3.0 * 1.5)
        return self._remaining() > estimated + self.config.safety_margin_seconds

    def _next_run_id(self, phase: str, level: int, arm: str) -> str:
        self._run_seq += 1
        return f"{self.config.experiment_id}:{phase}:L{level}:{arm}:{self._run_seq:04d}"

    def _write_environment(self) -> None:
        metadata = None
        if hasattr(self.client, "model_metadata"):
            metadata = self.client.model_metadata(self.config.model, timeout_seconds=5.0)
        payload = {
            "experiment": "007-adaptive-memory-frontier",
            "config": asdict(self.config),
            "model_metadata": metadata,
            "controls": {
                "thinking_enabled": False,
                "bootstrap_rules": BOOTSTRAP_RULES,
                "rules_per_level": RULES_PER_LEVEL,
                "tasks_per_level": TASKS_PER_LEVEL,
                "max_level": MAX_LEVEL,
                "frontier_pass_threshold": FRONTIER_PASS_THRESHOLD,
                "bytes_per_token_guard": CONSERVATIVE_BYTES_PER_TOKEN,
            },
        }
        (self.output_dir / "environment.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def live_preflight(self) -> dict[str, Any]:
        store, tasks, sealed = _preflight_memory()
        checks: list[dict[str, Any]] = []
        model_seed = self.config.seed + 77_000
        for arm in (ARM_FULL, ARM_RETRIEVED):
            prompt, memory_ids = render_memory_packet(tasks, store, arm)
            result: ModelResult = self.client.generate(
                model=self.config.model,
                prompt=prompt,
                num_ctx=self.config.context_limit,
                num_predict=self.config.discovery_budget,
                temperature=self.config.temperature,
                seed=model_seed,
                timeout_seconds=min(180.0, max(1.0, self._remaining())),
            )
            self.call_durations_seconds.append(result.wall_ms / 1000.0)
            task_ids = [task.task_id for task in tasks]
            parsed = parse_packet_response(result.response, task_ids) if result.status == "OK" else {task_id: None for task_id in task_ids}
            complete = all(parsed[task_id] is not None for task_id in task_ids)
            accurate = complete and all(parsed[task_id] == sealed[task_id]["answer"] for task_id in task_ids)
            passed = result.status == "OK" and not result.hit_ceiling and complete and accurate
            checks.append(
                {
                    "arm": arm,
                    "status": result.status,
                    "hit_ceiling": result.hit_ceiling,
                    "prompt_tokens": result.prompt_tokens,
                    "eval_tokens": result.eval_tokens,
                    "memory_records": len(memory_ids),
                    "response": result.response,
                    "passed": passed,
                }
            )
        return {"checks": checks, "passed": all(row["passed"] for row in checks)}

    def _context_cap_record(
        self,
        *,
        level: int,
        arm: str,
        phase: str,
        model_seed: int,
        prompt_bytes: int,
        estimated_tokens: int,
        memory_ids: tuple[str, ...],
        store: MemoryStore,
        tasks: tuple[MemoryTask, ...],
    ) -> dict[str, Any]:
        record = {
            "run_id": self._next_run_id(phase, level, arm),
            "level": level,
            "phase": phase,
            "arm": arm,
            "model": self.config.model,
            "model_seed": model_seed,
            "status": "CONTEXT_CAP_REACHED",
            "accuracy": None,
            "prompt_bytes": prompt_bytes,
            "estimated_prompt_tokens": estimated_tokens,
            "prompt_tokens": 0,
            "eval_tokens": 0,
            "wall_ms": 0.0,
            "hit_ceiling": False,
            "memory_rule_count": len(store),
            "supplied_memory_count": len(memory_ids),
            "memory_snapshot_fingerprint": store.snapshot_fingerprint(),
            "composition_depth": len(tasks[0].rule_ids) if tasks else 0,
        }
        append_jsonl(self.output_dir / "runs.jsonl", record)
        return record

    def _run_arm(
        self,
        level: int,
        tasks: tuple[MemoryTask, ...],
        sealed: dict[str, dict[str, Any]],
        store: MemoryStore,
        arm: str,
        *,
        model_seed: int,
        phase: str,
    ) -> dict[str, Any]:
        prompt, memory_ids = render_memory_packet(tasks, store, arm)
        prompt_bytes = len(prompt.encode("utf-8"))
        estimated_tokens = math.ceil(prompt_bytes / CONSERVATIVE_BYTES_PER_TOKEN)
        if estimated_tokens > self.config.context_limit:
            return self._context_cap_record(
                level=level,
                arm=arm,
                phase=phase,
                model_seed=model_seed,
                prompt_bytes=prompt_bytes,
                estimated_tokens=estimated_tokens,
                memory_ids=memory_ids,
                store=store,
                tasks=tasks,
            )

        remaining = max(1.0, self._remaining() - self.config.safety_margin_seconds)
        result: ModelResult = self.client.generate(
            model=self.config.model,
            prompt=prompt,
            num_ctx=self.config.context_limit,
            num_predict=self.config.discovery_budget,
            temperature=self.config.temperature,
            seed=model_seed,
            timeout_seconds=min(600.0, remaining),
        )
        self.call_durations_seconds.append(result.wall_ms / 1000.0)
        task_ids = [task.task_id for task in tasks]
        predictions = parse_packet_response(result.response, task_ids) if result.status == "OK" else {task_id: None for task_id in task_ids}
        complete = all(predictions[task_id] is not None for task_id in task_ids)
        status = result.status
        if status == "OK" and (result.hit_ceiling or not complete):
            status = "UNSCORABLE"
        scored = status == "OK"
        per_task: list[dict[str, Any]] = []
        for task in tasks:
            prediction = predictions[task.task_id]
            success = prediction == sealed[task.task_id]["answer"] if scored else None
            row = {
                "level": level,
                "phase": phase,
                "arm": arm,
                "task_id": task.task_id,
                "prediction": prediction,
                "expected": sealed[task.task_id]["answer"],
                "verified_success": success,
                "start_value": task.start_value,
                "rule_ids": list(task.rule_ids),
                "composition_depth": len(task.rule_ids),
                "memory_snapshot_fingerprint": store.snapshot_fingerprint(),
            }
            append_jsonl(self.output_dir / "observations.jsonl", row)
            per_task.append(row)
        successes = [row["verified_success"] for row in per_task if row["verified_success"] is not None]
        accuracy = sum(bool(value) for value in successes) / len(successes) if successes else None
        learned_levels = [store.get(rule_id).learned_level for rule_id in _referenced_rule_ids(tasks)]
        record = {
            "run_id": self._next_run_id(phase, level, arm),
            "level": level,
            "phase": phase,
            "arm": arm,
            "model": self.config.model,
            "model_seed": model_seed,
            "status": status,
            "accuracy": accuracy,
            "prompt_bytes": prompt_bytes,
            "estimated_prompt_tokens": estimated_tokens,
            "prompt_tokens": result.prompt_tokens,
            "eval_tokens": result.eval_tokens,
            "wall_ms": result.wall_ms,
            "done_reason": result.done_reason,
            "hit_ceiling": result.hit_ceiling,
            "memory_rule_count": len(store),
            "supplied_memory_count": len(memory_ids),
            "referenced_memory_count": len(_referenced_rule_ids(tasks)),
            "oldest_referenced_level": min(learned_levels) if learned_levels else None,
            "newest_referenced_level": max(learned_levels) if learned_levels else None,
            "memory_snapshot_fingerprint": store.snapshot_fingerprint(),
            "composition_depth": len(tasks[0].rule_ids) if tasks else 0,
            "response": result.response,
        }
        append_jsonl(self.output_dir / "runs.jsonl", record)
        return record

    def _append_learned_rules(self, store: MemoryStore, learned_level: int) -> None:
        new_rules = generate_rules(
            self.config.seed,
            start_index=len(store) + 1,
            count=RULES_PER_LEVEL,
            learned_level=learned_level,
        )
        store.append(new_rules)
        for rule in new_rules:
            append_jsonl(
                self.output_dir / "memory.jsonl",
                {
                    "event": "memory_acquired",
                    "learned_level": learned_level,
                    "rule": rule.to_dict(),
                    "snapshot_fingerprint": store.snapshot_fingerprint(),
                },
            )

    def _write_bootstrap_memory(self, store: MemoryStore) -> None:
        for rule in store.all_rules():
            append_jsonl(
                self.output_dir / "memory.jsonl",
                {
                    "event": "memory_acquired",
                    "learned_level": 0,
                    "rule": rule.to_dict(),
                    "snapshot_fingerprint": store.snapshot_fingerprint(),
                },
            )

    def _aggregate_accuracy(self, arm: str) -> float | None:
        rows = [
            level["arms"][arm]["accuracy"]
            for level in self.levels
            if level["arms"].get(arm, {}).get("status") == "OK"
            and level["arms"][arm]["accuracy"] is not None
        ]
        return sum(rows) / len(rows) if rows else None

    def _write_report(self) -> None:
        lines = [
            "# Experiment 007 — Adaptive External Memory Frontier",
            "",
            f"- Interpretation: {self.summary.get('interpretation')}",
            f"- Capability valid: {self.summary.get('capability_valid')}",
            f"- Model: {self.config.model}",
            f"- Retrieved last passing level: {self.summary.get('retrieved_last_passing_level')}",
            f"- Retrieved first confirmed failure: {self.summary.get('retrieved_first_confirmed_failure_level')}",
            f"- Rules at confirmed frontier: {self.summary.get('memory_rules_at_frontier')}",
            f"- Full-memory first failure: {self.summary.get('full_memory_first_failure_level')}",
            f"- Full-memory context cap: {self.summary.get('full_memory_context_cap_level')}",
            "",
            "## Levels",
            "",
        ]
        for row in self.levels:
            arms = row["arms"]
            lines.append(
                f"- L{row['level']} depth={row['composition_depth']} rules={row['memory_rule_count']}: "
                f"none={arms.get(ARM_NONE, {}).get('accuracy')} "
                f"full={arms.get(ARM_FULL, {}).get('accuracy')} "
                f"retrieved={arms.get(ARM_RETRIEVED, {}).get('accuracy')}"
            )
        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        raw_paths = [
            self.output_dir / "runs.jsonl",
            self.output_dir / "observations.jsonl",
            self.output_dir / "memory.jsonl",
        ]
        if any(path.exists() for path in raw_paths):
            raise RuntimeError(
                f"output directory already contains raw Experiment 007 evidence: {self.output_dir}"
            )
        self._started = self.clock()
        self._deadline = self._started + self.config.ceiling_minutes * 60.0
        self._write_environment()

        deterministic = deterministic_preflight(self.config.seed)
        live = self.live_preflight()
        preflight = {"deterministic": deterministic, "live": live, "passed": deterministic["passed"] and live["passed"]}
        (self.output_dir / "preflight.json").write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not preflight["passed"]:
            self.summary = {
                "interpretation": "PREFLIGHT_FAILED",
                "capability_valid": False,
                "preflight_passed": False,
                "levels_completed": 0,
            }
            (self.output_dir / "summary.json").write_text(json.dumps(self.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self._write_report()
            return self.summary

        store = bootstrap_store(self.config.seed)
        self._write_bootstrap_memory(store)
        interpretation = "FRONTIER_NOT_REACHED_MAX_LEVEL"
        capability_valid = True
        last_passing: int | None = None
        confirmed_failure_level: int | None = None
        frontier_rules: int | None = None
        full_first_failure: int | None = None
        full_context_cap: int | None = None
        unstable_levels: list[int] = []

        for level in range(1, MAX_LEVEL + 1):
            if not self._can_start_level():
                interpretation = "FRONTIER_NOT_REACHED_TIME_LIMIT"
                break

            tasks, sealed = build_level_packet(self.config.seed, level, store)
            model_seed = self.config.seed + 500_000 + level
            arms: dict[str, dict[str, Any]] = {}
            for arm in MEMORY_ARMS:
                arms[arm] = self._run_arm(
                    level,
                    tasks,
                    sealed,
                    store,
                    arm,
                    model_seed=model_seed,
                    phase="frontier",
                )

            if arms[ARM_FULL]["status"] == "CONTEXT_CAP_REACHED" and full_context_cap is None:
                full_context_cap = level
            if (
                arms[ARM_FULL]["status"] == "OK"
                and arms[ARM_FULL]["accuracy"] is not None
                and arms[ARM_FULL]["accuracy"] < FRONTIER_PASS_THRESHOLD
                and full_first_failure is None
            ):
                full_first_failure = level

            level_row: dict[str, Any] = {
                "level": level,
                "memory_rule_count": len(store),
                "memory_snapshot_fingerprint": store.snapshot_fingerprint(),
                "composition_depth": composition_depth(level),
                "arms": arms,
                "confirmation": None,
            }
            self.levels.append(level_row)

            primary = arms[ARM_RETRIEVED]
            if primary["status"] != "OK":
                capability_valid = False
                interpretation = "INVALID_PRIMARY_PACKET"
                break
            if arms[ARM_NONE]["status"] != "OK":
                capability_valid = False
                interpretation = "INVALID_CONTROL_PACKET"
                break
            if arms[ARM_FULL]["status"] not in {"OK", "CONTEXT_CAP_REACHED"}:
                capability_valid = False
                interpretation = "INVALID_FULL_MEMORY_PACKET"
                break

            primary_accuracy = primary["accuracy"]
            if primary_accuracy is not None and primary_accuracy >= FRONTIER_PASS_THRESHOLD:
                last_passing = level
                self._append_learned_rules(store, level)
                continue

            # One miss is not a frontier. Confirm at the same difficulty with fresh tasks and seed.
            confirmation_tasks, confirmation_sealed = build_level_packet(
                self.config.seed,
                level,
                store,
                variant=1,
            )
            confirmation = self._run_arm(
                level,
                confirmation_tasks,
                confirmation_sealed,
                store,
                ARM_RETRIEVED,
                model_seed=self.config.seed + 900_000 + level,
                phase="confirmation",
            )
            level_row["confirmation"] = confirmation
            if confirmation["status"] != "OK":
                capability_valid = False
                interpretation = "INVALID_CONFIRMATION_PACKET"
                break
            if self.confirmed_failure(
                primary_accuracy=primary_accuracy,
                confirmation_accuracy=confirmation["accuracy"],
            ):
                confirmed_failure_level = level
                frontier_rules = len(store)
                interpretation = "RETRIEVED_MEMORY_FRONTIER_FOUND"
                break

            unstable_levels.append(level)
            self._append_learned_rules(store, level)

        self.summary = {
            "interpretation": interpretation,
            "capability_valid": capability_valid,
            "preflight_passed": True,
            "model": self.config.model,
            "levels_completed": len(self.levels),
            "retrieved_last_passing_level": last_passing,
            "retrieved_first_confirmed_failure_level": confirmed_failure_level,
            "memory_rules_at_frontier": frontier_rules,
            "composition_depth_at_frontier": composition_depth(confirmed_failure_level) if confirmed_failure_level is not None else None,
            "full_memory_first_failure_level": full_first_failure,
            "full_memory_context_cap_level": full_context_cap,
            "no_memory_aggregate_accuracy": self._aggregate_accuracy(ARM_NONE),
            "full_memory_aggregate_accuracy": self._aggregate_accuracy(ARM_FULL),
            "retrieved_memory_aggregate_accuracy": self._aggregate_accuracy(ARM_RETRIEVED),
            "unstable_levels": unstable_levels,
            "max_rules_learned": len(store),
            "final_memory_snapshot_fingerprint": store.snapshot_fingerprint(),
            "level_results": self.levels,
        }
        (self.output_dir / "summary.json").write_text(json.dumps(self.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._write_report()
        return self.summary


def _load_config(path: str) -> ExperimentConfig:
    return ExperimentConfig.from_json(Path(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Experiment 007 adaptive external-memory frontier")
    parser.add_argument("--config", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)

    config = _load_config(args.config)
    output = Path(args.output_dir) if args.output_dir else Path("results") / config.experiment_id
    client = StrictFinalAnswerClient(OllamaClient(config.ollama_url))
    runner = AdaptiveMemoryRunner(config, client=client, output_dir=output)
    runner._started = runner.clock()
    runner._deadline = runner._started + config.ceiling_minutes * 60.0

    if args.preflight_only:
        deterministic = deterministic_preflight(config.seed)
        live = runner.live_preflight()
        report = {"deterministic": deterministic, "live": live, "passed": deterministic["passed"] and live["passed"]}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2

    summary = runner.run()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("capability_valid") else 2


if __name__ == "__main__":
    raise SystemExit(main())
