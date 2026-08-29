from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True)
class CapabilityPackage:
    package_id: str
    source_event_id: str
    verified_source: bool
    structural_signature: str
    applicability_signature: str
    provenance_hash: str

    def can_apply(self, *, structural_signature: str, applicability_signature: str) -> bool:
        return bool(self.verified_source and self.structural_signature == structural_signature and self.applicability_signature == applicability_signature)


def build_lineages(seed: int = 20260914, count: int = 48) -> list[CapabilityLineage]:
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


def create_capability_package(*, event: LineageEvent, verified: bool, structural_signature: str, applicability_signature: str, provenance: Any) -> CapabilityPackage | None:
    if not verified:
        return None
    return CapabilityPackage(
        package_id=f"PKG-{stable_hash([event.event_id, structural_signature, applicability_signature])[:16]}",
        source_event_id=event.event_id,
        verified_source=True,
        structural_signature=structural_signature,
        applicability_signature=applicability_signature,
        provenance_hash=stable_hash(provenance),
    )
