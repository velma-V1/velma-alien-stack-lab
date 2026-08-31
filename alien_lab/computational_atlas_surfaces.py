from __future__ import annotations

import base64
import hashlib
import io
import json
import textwrap
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
LEGAL_INTENTS = tuple(INTENT_BY_CAPABILITY.values())


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


class LiveSurface(dict):
    """JSON-native surface with deterministic image helpers."""

    def __init__(self, world_id: str, representation: str, content: Any, image: LiveImage | None = None):
        payload: dict[str, Any] = {"world_id": world_id, "representation": representation, "content": content}
        if image is not None:
            payload["image"] = image.to_dict()
        super().__init__(payload)
        self._image = image

    def to_dict(self) -> dict[str, Any]:
        return dict(self)

    def image_bytes(self) -> bytes:
        if self._image is None:
            return b""
        return base64.b64decode(self._image.base64_data)

    @property
    def sha256(self) -> str:
        if self._image is not None:
            return self._image.sha256
        return hashlib.sha256(json.dumps(self, sort_keys=True).encode()).hexdigest()


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
                        "intent": {"type": "string", "enum": list(LEGAL_INTENTS)},
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
    return {"item": ordinal, "facts": operation.payload, "requested_output": "compute the exact requested outcome from these facts"}


def _text_rows(world: World) -> list[str]:
    unbound = oracle_unbound_ir(world)
    return [_describe_payload(operation.intent, operation.payload) for operation in unbound.operations]


def _r5_document_text(world: World) -> str:
    return "CASE " + world.world_id + "\n" + "\n".join(
        f"{index + 1}. {row}" for index, row in enumerate(_text_rows(world))
    )


def _render_text_png(text: str, width: int = 960) -> bytes:
    """Render deterministic readable glyphs into a real PNG document artifact."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - CI installs the pinned dependency.
        raise RuntimeError("R5_RENDERER_DEPENDENCY_MISSING:Pillow") from exc

    font = ImageFont.load_default(size=18)
    wrapped_lines: list[str] = []
    for source_line in text.splitlines() or [""]:
        parts = textwrap.wrap(
            source_line,
            width=92,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False,
        )
        wrapped_lines.extend(parts or [""])
    rendered = "\n".join(wrapped_lines)

    probe = Image.new("L", (width, 32), 255)
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.multiline_textbbox((0, 0), rendered, font=font, spacing=6)
    text_height = max(1, int(bbox[3] - bbox[1]))
    height = max(64, text_height + 40)

    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)
    draw.multiline_text((20, 20), rendered, font=font, fill=0, spacing=6)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()


def render_live_surface(world: World, representation: str) -> LiveSurface:
    operations = oracle_unbound_ir(world).operations
    if representation == "R1_STRUCTURED":
        content = {
            "case": world.world_id,
            "items": [_structured_operation(operation, index + 1) for index, operation in enumerate(operations)],
            "goal": "return each exact outcome in item order",
        }
        return LiveSurface(world.world_id, representation, content)
    rows = _text_rows(world)
    if representation == "R2_NATURAL":
        content = {"request": "Solve every part of this job and return the outcomes in the order described. " + " ".join(rows)}
        return LiveSurface(world.world_id, representation, content)
    if representation == "R3_PARAPHRASED":
        reverse_rows = list(reversed(rows))
        content = {
            "request": "The notes below were shuffled. Reconstruct the intended item order from their numbered positions, ignore irrelevant wording, and return the exact outcomes.",
            "notes": [{"position": len(rows) - index, "text": row} for index, row in enumerate(reverse_rows)],
            "distractors": ["Presentation order is not evidence of execution order.", "Do not assume approximate answers are acceptable."],
        }
        return LiveSurface(world.world_id, representation, content)
    if representation == "R4_IMPLICIT":
        content = {
            "request": "Infer what exact operations are necessary from these mixed records, then return one outcome per record group in group order.",
            "groups": [{"group": index + 1, "records": operation.payload} for index, operation in enumerate(operations)],
        }
        return LiveSurface(world.world_id, representation, content)
    if representation == "R5_PERCEPTUAL":
        raw = _render_text_png(_r5_document_text(world))
        digest = hashlib.sha256(raw).hexdigest()
        image = LiveImage(media_type="image/png", base64_data=base64.b64encode(raw).decode("ascii"), sha256=digest)
        return LiveSurface(
            world.world_id,
            representation,
            {"instruction": "Read the attached case image and return each exact outcome in item order."},
            image=image,
        )
    raise ValueError(f"unsupported live representation: {representation}")
