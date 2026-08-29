from __future__ import annotations

from typing import Iterable

from .computational_atlas_accumulation import STAGES, build_lineages
from .computational_atlas_frontier import build_phase_i_tasks
from .computational_atlas_horizon import build_horizon_jobs
from .computational_atlas_live_types import LiveCell
from .computational_atlas_types import stable_hash


def _cell(*, order: int, phase: str, seed: int, arm: str, world_index: int | None = None, world_id: str | None = None, representation: str | None = None, condition: str | None = None, lineage_index: int | None = None, stage: str | None = None, metadata: dict | None = None) -> LiveCell:
    raw = [phase, seed, arm, world_index, world_id, representation, condition, lineage_index, stage, metadata or {}]
    return LiveCell(
        cell_id=f"{phase}-{stable_hash(raw)[:20]}",
        order=order,
        phase=phase,
        seed=seed,
        arm=arm,
        world_index=world_index,
        world_id=world_id,
        representation=representation,
        condition=condition,
        lineage_index=lineage_index,
        stage=stage,
        metadata=metadata or {},
    )


def build_phase_c_ledger() -> list[LiveCell]:
    seed = 20260910
    reps = ("R1_STRUCTURED", "R2_NATURAL", "R3_PARAPHRASED", "R4_IMPLICIT", "R5_PERCEPTUAL")
    arms = ("MODEL_DIRECT", "DETERMINISTIC_RECOGNIZER_BASIS", "LOCAL_SEMANTIC_COMPILER_BASIS", "ORACLE_IR_BASIS")
    cells: list[LiveCell] = []
    order = 0
    for world_index in range(192):
        for representation in reps:
            for arm in arms:
                cells.append(_cell(order=order, phase="C", seed=seed, arm=arm, world_index=world_index, representation=representation))
                order += 1
    return cells


def build_phase_d_ledger() -> list[LiveCell]:
    seed = 20260911
    reps = ("R3_PARAPHRASED", "R4_IMPLICIT")
    arms = ("FREE_JSON", "SCHEMA_CONSTRAINED", "SCHEMA_VALIDATE_REPAIR")
    cells: list[LiveCell] = []
    order = 0
    for world_index in range(64, 160):
        for representation in reps:
            for arm in arms:
                cells.append(_cell(order=order, phase="D", seed=seed, arm=arm, world_index=world_index, representation=representation))
                order += 1
    return cells


def build_phase_e_ledger() -> list[LiveCell]:
    seed = 20260912
    routers = ("ORACLE_ROUTER", "RULE_ROUTER", "LOCAL_MODEL_ROUTER")
    catalogs = ("CATALOG_8", "CATALOG_16", "CATALOG_32")
    cells: list[LiveCell] = []
    order = 0
    for world_index in range(96):
        for arm in routers:
            for condition in catalogs:
                cells.append(_cell(order=order, phase="E", seed=seed, arm=arm, world_index=world_index, condition=condition))
                order += 1
    return cells


def build_phase_f_ledger() -> list[LiveCell]:
    seed = 20260913
    arms = (
        "MODEL_DIRECT", "SINGLE_G", "SINGLE_L", "SINGLE_C", "SINGLE_P", "SINGLE_X", "SINGLE_M", "SINGLE_D", "SINGLE_R",
        "ALL_ENGINES_NO_TYPED_HANDOFF", "TYPED_COMPOSITION", "TYPED_COMPOSITION_VERIFIED",
    )
    cells: list[LiveCell] = []
    order = 0
    for world_index in range(96):
        for arm in arms:
            cells.append(_cell(order=order, phase="F", seed=seed, arm=arm, world_index=world_index))
            order += 1
    return cells


def build_phase_g_ledger() -> list[LiveCell]:
    seed = 20260914
    arms = ("NO_RETAINED_CAPABILITY", "TEXT_MEMORY", "VERIFIED_EXECUTABLE_CAPABILITY")
    cells: list[LiveCell] = []
    order = 0
    lineages = build_lineages(seed=seed, count=48)
    for lineage_index, lineage in enumerate(lineages):
        for event in lineage.events:
            for arm in arms:
                cells.append(_cell(order=order, phase="G", seed=seed, arm=arm, lineage_index=lineage_index, world_id=lineage.lineage_id, stage=event.stage, metadata={"event_id": event.event_id, "representation": event.representation}))
                order += 1
    return cells


def build_phase_h_ledger() -> list[LiveCell]:
    seed = 20260915
    arms = ("MODEL_DIRECT_LONG", "VELMA_NO_AUTHORITATIVE_VERIFIER", "VELMA_FULL")
    cells: list[LiveCell] = []
    order = 0
    for world_index, job in enumerate(build_horizon_jobs(seed=seed)):
        for arm in arms:
            cells.append(_cell(order=order, phase="H", seed=seed, arm=arm, world_index=world_index, world_id=job.job_id, metadata={"horizon": job.horizon}))
            order += 1
    return cells


def build_phase_i_ledger() -> list[LiveCell]:
    seed = 20260916
    arms = (
        "LOCAL_GENERIC_AGENT", "VELMA_LOCAL", "FRONTIER_A_GENERIC_AGENT", "VELMA_FRONTIER_A", "FRONTIER_B_GENERIC_AGENT", "VELMA_FRONTIER_B",
    )
    cells: list[LiveCell] = []
    order = 0
    for task in build_phase_i_tasks(seed=seed):
        for arm in arms:
            cells.append(_cell(order=order, phase="I", seed=seed, arm=arm, world_index=task.index, world_id=task.task_id, metadata={"kind": task.kind}))
            order += 1
    return cells


def build_all_live_ledgers() -> list[LiveCell]:
    all_cells: list[LiveCell] = []
    offset = 0
    for builder in (build_phase_c_ledger, build_phase_d_ledger, build_phase_e_ledger, build_phase_f_ledger, build_phase_g_ledger, build_phase_h_ledger, build_phase_i_ledger):
        phase_cells = builder()
        for cell in phase_cells:
            all_cells.append(LiveCell(**{**cell.to_dict(), "order": offset + cell.order}))
        offset += len(phase_cells)
    return all_cells
