from __future__ import annotations

import json
import random
from pathlib import Path

from .types import Edge, SealedAnswers, SourceRecord, Task, TaskSet


def _source(record_id: str, key: str, value: str, authority: int, revision: int, scope: str, kind: str = "state") -> SourceRecord:
    raw = f"{record_id} [{scope}] authority={authority} revision={revision}: {key}={value}"
    return SourceRecord(record_id, key, value, authority, revision, scope, kind, raw)


def _edge(edge_id: str, source: str, target: str, active: bool, scope: str) -> Edge:
    status = "active" if active else "inactive"
    return Edge(edge_id, source, target, active, scope, f"{edge_id}: {source}->{target} is {status} [{scope}]")


def _task(
    rng: random.Random,
    *,
    task_id: str,
    family: str,
    target_scope: str,
    target_key: str,
    entry: str,
    sources: list[SourceRecord],
    edges: list[Edge],
    procedure_rules: list[str],
    question: str,
    correct: str,
    distractors: list[str],
    deterministic_unique: bool = False,
) -> tuple[Task, dict]:
    options = [correct, *distractors]
    rng.shuffle(options)
    letters = "ABCD"
    choices = {letters[i]: options[i] for i in range(4)}
    correct_letter = next(k for k, v in choices.items() if v == correct)
    source_order = list(sources)
    edge_order = list(edges)
    rng.shuffle(source_order)
    rng.shuffle(edge_order)
    task = Task(
        task_id=task_id,
        family=family,
        target_scope=target_scope,
        target_key=target_key,
        entry=entry,
        sources=tuple(source_order),
        edges=tuple(edge_order),
        procedure_rules=tuple(procedure_rules),
        question=question,
        choices=choices,
    )
    sealed = {
        "answer": correct_letter,
        "deterministic_unique": deterministic_unique,
        "correct_action": correct,
    }
    return task, sealed


def generate_taskset(seed: int = 20260828) -> tuple[TaskSet, SealedAnswers]:
    rng = random.Random(seed)
    sealed: dict[str, dict] = {}

    discovery: list[Task] = []
    transfer: list[Task] = []
    challenge: list[Task] = []

    t, a = _task(
        rng,
        task_id="disc-migration-01",
        family="compound_migration",
        target_scope="payments",
        target_key="request_field",
        entry="gateway",
        sources=[
            _source("contract-r6", "request_field", "deadline_ms", 3, 6, "payments"),
            _source("contract-r5", "request_field", "timeout", 3, 5, "payments"),
            _source("readme-r20", "request_field", "timeout", 1, 20, "payments"),
            _source("ops-r8", "retry_limit", "5", 2, 8, "payments"),
            _source("catalog-note", "request_field", "ttl", 1, 40, "catalog"),
            _source("handler-note", "handler_mode", "strict", 2, 3, "charge_handler", "semantic"),
        ],
        edges=[
            _edge("e1", "gateway", "legacy_handler", False, "payments"),
            _edge("e2", "gateway", "charge_handler", True, "payments"),
        ],
        procedure_rules=[
            "Higher authority outranks lower authority; within equal authority, higher revision supersedes lower revision.",
            "Patch only the active production path.",
            "When a current contract value supersedes a historical value, migrate the active implementation to the current value.",
            "If the highest-authority current state is unresolved, make no production change and escalate.",
        ],
        question="Which production action is justified by the project evidence?",
        correct="Patch charge_handler to use deadline_ms.",
        distractors=[
            "Patch legacy_handler to use deadline_ms.",
            "Keep charge_handler on timeout because the README is newer.",
            "Change charge_handler to use ttl.",
        ],
    )
    discovery.append(t); sealed[t.task_id] = a

    t, a = _task(
        rng,
        task_id="disc-conflict-02",
        family="compound_conflict",
        target_scope="scheduler",
        target_key="retry_mode",
        entry="worker",
        sources=[
            _source("policy-a", "retry_mode", "bounded", 3, 7, "scheduler"),
            _source("policy-b", "retry_mode", "adaptive", 3, 7, "scheduler"),
            _source("readme-r22", "retry_mode", "legacy", 1, 22, "scheduler"),
            _source("ops-r31", "retry_limit", "5", 1, 31, "scheduler"),
            _source("ui-r3", "retry_mode", "instant", 1, 3, "ui"),
        ],
        edges=[
            _edge("e3", "worker", "scheduler_v2", True, "scheduler"),
            _edge("e4", "worker", "legacy_scheduler", False, "scheduler"),
        ],
        procedure_rules=[
            "Equal highest-authority records at the same revision that disagree are unresolved.",
            "Never choose arbitrarily between unresolved authoritative values.",
            "Only the active path may be changed.",
        ],
        question="What production action is justified before changing retry behavior?",
        correct="Make no retry-mode change and escalate the equal-authority conflict.",
        distractors=[
            "Set scheduler_v2 to bounded.",
            "Set scheduler_v2 to adaptive.",
            "Set legacy_scheduler to legacy.",
        ],
    )
    discovery.append(t); sealed[t.task_id] = a

    extra_discovery_specs = [
        dict(
            task_id="disc-authority-03", family="authority_temporal", target_scope="identity", target_key="required_role", entry="router",
            sources=[_source("auth-r9","required_role","maintainer",4,9,"identity"), _source("auth-r8","required_role","editor",4,8,"identity"), _source("wiki-r41","required_role","viewer",1,41,"identity"), _source("noise","required_role","guest",1,90,"marketing")],
            edges=[_edge("da1","router","control_handler",True,"identity"), _edge("da2","router","legacy_handler",False,"identity")],
            procedure_rules=["Higher authority outranks lower authority; higher revision breaks ties.", "Apply policy only to the active path."],
            question="Which production policy change is justified?", correct="Require maintainer in control_handler.",
            distractors=["Require viewer in control_handler.","Require maintainer in legacy_handler.","Require editor in control_handler."]
        ),
        dict(
            task_id="disc-semantic-04", family="semantic_repair", target_scope="fulfillment", target_key="delivery_semantics", entry="orders",
            sources=[_source("delivery-r3","delivery_semantics","at_least_once",3,3,"fulfillment"), _source("delivery-r2","delivery_semantics","best_effort",3,2,"fulfillment"), _source("guide-r30","delivery_semantics","best_effort",1,30,"fulfillment"), _source("effect-r1","operation_effect","creates_shipment",3,1,"fulfillment","semantic")],
            edges=[_edge("ds1","orders","shipment_creator",True,"fulfillment"), _edge("ds2","orders","preview_builder",False,"fulfillment")],
            procedure_rules=["Use the current authoritative delivery semantics.","At-least-once delivery plus an external create side effect requires deduplication on the active consumer."],
            question="Which repair satisfies the current semantics without duplicating the side effect?", correct="Add a deduplication key to shipment_creator.",
            distractors=["Add deduplication only to preview_builder.","Leave shipment_creator unchanged because the guide is newer.","Run shipment_creator twice for verification."]
        ),
        dict(
            task_id="disc-safety-05", family="side_effect_safety", target_scope="infra", target_key="approval_mode", entry="deploy",
            sources=[_source("safety-r12","approval_mode","three_person",5,12,"infra"), _source("safety-r11","approval_mode","two_person",5,11,"infra"), _source("readme-r60","approval_mode","automatic",1,60,"infra"), _source("effect-r2","effect","drops_primary_table",5,2,"infra","semantic")],
            edges=[_edge("df1","deploy","schema_drop",True,"infra"), _edge("df2","deploy","dry_run",False,"infra")],
            procedure_rules=["Destructive effects must obey the current approval policy.","Only the active production path is relevant."],
            question="Which change preserves the governing safety property?", correct="Require three-person approval for schema_drop.",
            distractors=["Allow automatic approval for schema_drop.","Require three-person approval only for dry_run.","Use two-person approval because it was previously current."]
        ),
        dict(
            task_id="disc-path-06", family="active_path", target_scope="telemetry", target_key="span_field", entry="collector",
            sources=[_source("telemetry-r5","span_field","span_id",3,5,"telemetry"), _source("telemetry-r4","span_field","trace_key",3,4,"telemetry"), _source("doc-r70","span_field","correlation",1,70,"telemetry"), _source("other-r1","span_field","session",1,1,"search")],
            edges=[_edge("dp1","collector","audit_sink",True,"telemetry"), _edge("dp2","collector","legacy_sink",False,"telemetry")],
            procedure_rules=["Use the current authoritative schema field.","Change only the active sink."],
            question="Which active-path schema repair is justified?", correct="Change audit_sink to span_id.",
            distractors=["Change legacy_sink to span_id.","Change audit_sink to correlation.","Change audit_sink to trace_key."]
        ),
    ]
    for spec in extra_discovery_specs:
        t, a = _task(rng, **spec)
        discovery.append(t); sealed[t.task_id] = a

    transfer_specs = [
        dict(
            task_id="xfer-authority-01", family="authority_temporal", target_scope="identity", target_key="required_role", entry="router",
            sources=[_source("security-r5","required_role","operator",3,5,"identity"), _source("security-r4","required_role","viewer",3,4,"identity"), _source("wiki-r30","required_role","editor",1,30,"identity")],
            edges=[_edge("a1","router","admin_handler",True,"identity"), _edge("a2","router","old_handler",False,"identity")],
            procedure_rules=["Higher authority outranks lower authority; higher revision breaks ties.", "Apply policy to the active path only."],
            question="Which change aligns production with governing policy?", correct="Require operator in admin_handler.",
            distractors=["Require editor in admin_handler.","Require operator in old_handler.","Require viewer in admin_handler."]
        ),
        dict(
            task_id="xfer-path-02", family="active_path", target_scope="billing", target_key="trace_field", entry="dispatcher",
            sources=[_source("event-r8","trace_field","trace_id",3,8,"billing"), _source("event-r7","trace_field","request_id",3,7,"billing"), _source("obs-r20","trace_field","correlation_id",1,20,"billing")],
            edges=[_edge("p1","dispatcher","metrics_consumer",False,"billing"), _edge("p2","dispatcher","audit_consumer",True,"billing")],
            procedure_rules=["Use the highest-authority current schema.","Modify only the active consumer."],
            question="Which consumer change is justified?", correct="Change audit_consumer to trace_id.",
            distractors=["Change metrics_consumer to trace_id.","Change audit_consumer to request_id.","Change audit_consumer to correlation_id."]
        ),
        dict(
            task_id="xfer-conflict-03", family="unresolved_conflict", target_scope="storage", target_key="write_mode", entry="api",
            sources=[_source("policy-x","write_mode","sync",4,9,"storage"), _source("policy-y","write_mode","async",4,9,"storage"), _source("guide","write_mode","buffered",1,33,"storage")],
            edges=[_edge("c1","api","writer",True,"storage"), _edge("c2","api","legacy_writer",False,"storage")],
            procedure_rules=["Equal top-ranked conflicting state is unresolved.","Do not mutate production from unresolved state."],
            question="What should happen before changing the active writer?", correct="Escalate the unresolved write_mode conflict and make no change.",
            distractors=["Set writer to sync.","Set writer to async.","Set writer to buffered."]
        ),
        dict(
            task_id="xfer-semantic-04", family="semantic_repair", target_scope="orders", target_key="idempotency", entry="checkout",
            sources=[_source("contract-r4","idempotency","required",3,4,"orders"), _source("old-contract","idempotency","optional",3,3,"orders"), _source("note","idempotency","optional",1,20,"orders"), _source("sidefx","operation_effect","charges_card",3,2,"orders","semantic")],
            edges=[_edge("s1","checkout","charge_once",True,"orders"), _edge("s2","checkout","preview",False,"orders")],
            procedure_rules=["Current contract requirements govern.","A retryable operation with external side effects must satisfy required idempotency before retry is enabled."],
            question="Which repair best satisfies the current contract and side-effect constraint?", correct="Add an idempotency key to charge_once before enabling retries.",
            distractors=["Enable retries on charge_once without an idempotency key.","Add an idempotency key only to preview.","Disable all checkout requests permanently."]
        ),
        dict(
            task_id="xfer-migration-05", family="migration_direction", target_scope="customer", target_key="customer_column", entry="worker",
            sources=[_source("migration-r6","customer_column","customer_id",3,6,"customer"), _source("migration-r5","customer_column","account_id",3,5,"customer"), _source("guide-r14","customer_column","user_id",1,14,"customer")],
            edges=[_edge("m1","worker","invoice_writer",True,"customer"), _edge("m2","worker","invoice_reader",False,"customer")],
            procedure_rules=["Migrate active writers from superseded schema values to current authoritative values."],
            question="Which migration direction is supported?", correct="Change invoice_writer from account_id to customer_id.",
            distractors=["Change invoice_writer from customer_id to account_id.","Change invoice_reader to user_id.","Change invoice_writer to user_id."]
        ),
        dict(
            task_id="xfer-safety-06", family="side_effect_safety", target_scope="deployment", target_key="approval_mode", entry="release",
            sources=[_source("policy-r11","approval_mode","two_person",4,11,"deployment"), _source("policy-r10","approval_mode","single",4,10,"deployment"), _source("readme","approval_mode","automatic",1,50,"deployment"), _source("effect","effect","production_delete",4,1,"deployment","semantic")],
            edges=[_edge("z1","release","destructive_migration",True,"deployment"), _edge("z2","release","dry_run",False,"deployment")],
            procedure_rules=["Destructive production effects must satisfy the current approval policy.","Modify only the active path."],
            question="Which action preserves the current safety property?", correct="Require two-person approval for destructive_migration.",
            distractors=["Allow automatic approval for destructive_migration.","Require two-person approval only for dry_run.","Use single-person approval because it was previously authoritative."]
        ),
    ]

    for spec in transfer_specs:
        t, a = _task(rng, **spec)
        transfer.append(t); sealed[t.task_id] = a

    challenge.extend([transfer[3], transfer[5]])

    return TaskSet(tuple(discovery), tuple(transfer), tuple(challenge)), SealedAnswers(sealed)


def write_sealed_taskset(public: TaskSet, sealed: SealedAnswers, public_path: Path, sealed_path: Path) -> None:
    public_path.parent.mkdir(parents=True, exist_ok=True)
    sealed_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(public.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sealed_path.write_text(json.dumps(sealed.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
