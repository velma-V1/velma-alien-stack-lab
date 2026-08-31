from __future__ import annotations

from dataclasses import dataclass

from .computational_atlas_types import stable_hash


STAGES = (
    "NOVEL",
    "REPEAT",
    "PARAMETER_VARIATION",
    "REPRESENTATION_SHIFT",
    "ENVIRONMENT_DRIFT",
    "COMPOSITION_TRANSFER",
)


@dataclass(frozen=True)
class LineageEvent:
    event_id: str
    stage: str
    representation: str
    parameter_delta: int
    environment_tag: str


@dataclass(frozen=True)
class CapabilityLineage:
    lineage_id: str
    events: tuple[LineageEvent, ...]
    seed: int


def build_lineages(seed: int = 20260914, count: int = 48) -> list[CapabilityLineage]:
    """Build the frozen Phase G exam definition only.

    Runtime capability-package creation/reuse is intentionally absent until the
    explicit post-evidence G gate. This function freezes lineage membership and
    task shape without pre-building the system mechanism being tested.
    """
    if count != 48:
        raise ValueError("frozen Phase G requires exactly 48 lineages")
    reps = {
        "NOVEL": "R2_NATURAL",
        "REPEAT": "R2_NATURAL",
        "PARAMETER_VARIATION": "R2_NATURAL",
        "REPRESENTATION_SHIFT": "R3_PARAPHRASED",
        "ENVIRONMENT_DRIFT": "R2_NATURAL",
        "COMPOSITION_TRANSFER": "R4_IMPLICIT",
    }
    lineages: list[CapabilityLineage] = []
    for index in range(count):
        lineage_id = f"LG-{seed}-{index:03d}-{stable_hash([seed, index])[:8]}"
        events = tuple(
            LineageEvent(
                event_id=f"{lineage_id}-{position:02d}",
                stage=stage,
                representation=reps[stage],
                parameter_delta=0 if stage in {"NOVEL", "REPEAT", "REPRESENTATION_SHIFT"} else position + 1,
                environment_tag="base" if stage not in {"ENVIRONMENT_DRIFT", "COMPOSITION_TRANSFER"} else f"drift-{index % 5}-{position}",
            )
            for position, stage in enumerate(STAGES)
        )
        lineages.append(CapabilityLineage(lineage_id=lineage_id, events=events, seed=seed))
    return lineages
