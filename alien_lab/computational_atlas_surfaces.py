from __future__ import annotations

import base64
import binascii
import hashlib
import json
import struct
import zlib
from dataclasses import asdict, dataclass
from typing import Any

from .computational_atlas_live_types import LiveImage
from .computational_atlas_worlds import World


INTENT_BY_CAPABILITY = {
    "G": "path_query",
    "L": "rule_entailment",
    "C": "budget_selection",
    "P": "state_goal_search",
    "X": "program_transform",
    "M": "numeric_aggregate",
    "D": "record_join_aggregate",
    "R": "evidence_rank",
    "U": "unclassified_problem",
}


@dataclass(frozen=True)
class UnboundOperation:
    operation_id: str
    intent: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UnboundTaskIR:
    task_id: str
    operations: tuple[UnboundOperation, ...]
    verification: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "operations": [operation.to_dict() for operation in self.operations],
            "verification": list(self.verification),
        }


@dataclass(frozen=True)
class LiveSurface:
    world_id: str
    representation: str
    content: Any
    image: LiveImage | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {"world_id": self.world_id, "representation": self.representation, "content": self.content}
        if self.image is not None:
            payload["image"] = self.image.to_dict()
        return payload

    def image_bytes(self) -> bytes:
        if self.image is None:
            return b""
        return base64.b64decode(self.image.base64_data)

    @property
    def sha256(self) -> str:
        return self.image.sha256 if self.image is not None else hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()


def oracle_unbound_ir(world: World) -> UnboundTaskIR:
    return UnboundTaskIR(
        task_id=world.task_ir.task_id,
        operations=tuple(
            UnboundOperation(
                operation_id=operation.operation_id,
                intent=INTENT_BY_CAPABILITY.get(operation.capability, "unclassified_problem"),
                payload=operation.payload,
            )
            for operation in world.task_ir.operations
        ),
        verification=tuple(world.task_ir.verification),
    )


def task_ir_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["task_id", "operations"],
        "properties": {
            "task_id": {"type": "string"},
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["operation_id", "intent", "payload"],
                    "properties": {
                        "operation_id": {"type": "string"},
                        "intent": {"type": "string"},
                        "payload": {"type": "object"},
                    },
                },
            },
            "verification": {"type": "array", "items": {"type": "object"}},
        },
    }


def _describe_payload(intent: str, payload: dict[str, Any]) -> str:
    if intent == "path_query":
        return f"Links are {payload['edges']}. Find a route from {payload['start']} to {payload['goal']}."
    if intent == "rule_entailment":
        return f"Known truth values are {payload['facts']}. Rules are {payload['rules']}. Determine whether {payload['query']} follows."
    if intent == "budget_selection":
        return f"Options are {payload['items']}. Spend no more than {payload['budget']} while maximizing total value."
    if intent == "state_goal_search":
        return f"Allowed state moves are {payload['transitions']}. Start at {payload['start']} and reach {payload['goal']}."
    if intent == "program_transform":
        return f"Apply these ordered transformations {payload['program']} and return {payload['return']}."
    if intent == "numeric_aggregate":
        return f"Combine values {payload['values']} using weights {payload['weights']} and return the weighted average."
    if intent == "record_join_aggregate":
        return f"Match these records by {payload['left_key']} and {payload['right_key']}, then total {payload['sum_field']}: left={payload['left']}, right={payload['right']}."
    if intent == "evidence_rank":
        return f"Given records {payload['records']}, find the best {payload['top_k']} matches for terms {payload['query_terms']} using relevance and authority."
    return f"Resolve this unfamiliar problem from observations: {payload}."


def _structured_operation(operation: UnboundOperation, ordinal: int) -> dict[str, Any]:
    # Deliberately domain-neutral: no solver or engine class labels.
    return {"item": ordinal, "facts": operation.payload, "requested_output": "compute the exact requested outcome from these facts"}


def _text_rows(world: World) -> list[str]:
    unbound = oracle_unbound_ir(world)
    return [_describe_payload(operation.intent, operation.payload) for operation in unbound.operations]


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)


def _render_text_png(text: str, width: int = 960) -> bytes:
    # A deterministic monochrome raster. It is intentionally simple and dependency-free.
    encoded = text.encode("utf-8")
    bits: list[int] = []
    for byte in encoded:
        bits.extend((byte >> shift) & 1 for shift in range(7, -1, -1))
        bits.extend([0, 0])
    columns = max(80, min(width - 20, width))
    rows = max(32, ((len(bits) + columns - 1) // columns) * 3 + 20)
    pixels = bytearray()
    for y in range(rows):
        pixels.append(0)
        for x in range(width):
            bit_index = ((y - 10) // 3) * columns + (x - 10) if y >= 10 and x >= 10 else -1
            on = 0 <= bit_index < len(bits) and bits[bit_index] == 1 and ((y - 10) % 3 == 1)
            pixels.append(0 if on else 255)
    ihdr = struct.pack(">IIBBBBB", width, rows, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9)) + _png_chunk(b"IEND", b"")


def render_live_surface(world: World, representation: str) -> LiveSurface:
    operations = oracle_unbound_ir(world).operations
    if representation == "R1_STRUCTURED":
        content = {"case": world.world_id, "items": [_structured_operation(operation, index + 1) for index, operation in enumerate(operations)], "goal": "return each exact outcome in item order"}
        return LiveSurface(world.world_id, representation, content)
    rows = _text_rows(world)
    if representation == "R2_NATURAL":
        content = {"request": "Solve every part of this job and return the outcomes in the order described. " + " ".join(rows)}
        return LiveSurface(world.world_id, representation, content)
    if representation == "R3_PARAPHRASED":
        reverse_rows = list(reversed(rows))
        content = {"request": "The notes below were shuffled. Reconstruct the intended item order from their numbered positions, ignore irrelevant wording, and return the exact outcomes.", "notes": [{"position": len(rows) - index, "text": row} for index, row in enumerate(reverse_rows)], "distractors": ["Presentation order is not evidence of execution order.", "Do not assume approximate answers are acceptable."]}
        return LiveSurface(world.world_id, representation, content)
    if representation == "R4_IMPLICIT":
        # Values remain available, but requested operations are not named. The model must infer them from structure.
        content = {"request": "Infer what exact operations are necessary from these mixed records, then return one outcome per record group in group order.", "groups": [{"group": index + 1, "records": operation.payload} for index, operation in enumerate(operations)]}
        return LiveSurface(world.world_id, representation, content)
    if representation == "R5_PERCEPTUAL":
        text = "CASE " + world.world_id + "\n" + "\n".join(f"{index + 1}. {row}" for index, row in enumerate(rows))
        raw = _render_text_png(text)
        digest = hashlib.sha256(raw).hexdigest()
        image = LiveImage(media_type="image/png", base64_data=base64.b64encode(raw).decode("ascii"), sha256=digest)
        return LiveSurface(world.world_id, representation, {"instruction": "Read the attached case image and return each exact outcome in item order."}, image=image)
    raise ValueError(f"unsupported live representation: {representation}")
