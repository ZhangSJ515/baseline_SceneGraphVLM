from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def canonical_label(value: Any) -> str:
    text = str(value or "").strip().lower().replace("_", "-").replace(" ", "-")
    return re.sub(r"-+", "-", text).strip("-")


def _int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def _float(value: Any, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric, got {value!r}") from exc


@dataclass
class ObjectMemory:
    track_id: int
    category: str
    state: str = "visible"
    first_frame: int = 0
    last_frame: int = 0
    bbox: list[float] | None = None
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ObjectMemory":
        bbox = data.get("bbox")
        if bbox is not None:
            if not isinstance(bbox, Sequence) or len(bbox) != 4:
                raise ValueError("bbox must have four coordinates")
            bbox = [float(v) for v in bbox]
        return cls(
            track_id=_int(data.get("track_id", data.get("id")), "track_id"),
            category=canonical_label(data.get("category", data.get("name"))),
            state=str(data.get("state", "visible")),
            first_frame=_int(data.get("first_frame", data.get("frame_id", 0)), "first_frame"),
            last_frame=_int(data.get("last_frame", data.get("frame_id", 0)), "last_frame"),
            bbox=bbox,
            confidence=_float(data.get("confidence", 1.0), "confidence"),
        )


@dataclass
class RelationMemory:
    relation_id: str
    subject_id: int
    predicate: str
    object_id: int
    state: str = "active"
    start_frame: int = 0
    end_frame: int | None = None
    evidence_frames: list[int] = field(default_factory=list)
    confidence: float = 1.0
    source: str = "ground-truth"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RelationMemory":
        end = data.get("end_frame")
        return cls(
            relation_id=str(data.get("relation_id", data.get("id", ""))).strip(),
            subject_id=_int(data.get("subject_id", data.get("subject")), "subject_id"),
            predicate=canonical_label(data.get("predicate")),
            object_id=_int(data.get("object_id", data.get("object")), "object_id"),
            state=str(data.get("state", "active")),
            start_frame=_int(data.get("start_frame", 0), "start_frame"),
            end_frame=None if end is None else _int(end, "end_frame"),
            evidence_frames=sorted({_int(v, "evidence_frame") for v in data.get("evidence_frames", [])}),
            confidence=_float(data.get("confidence", 1.0), "confidence"),
            source=str(data.get("source", "ground-truth")),
        )

    def signature(self) -> tuple[int, str, int]:
        return self.subject_id, self.predicate, self.object_id


@dataclass
class GraphMemory:
    objects: dict[int, ObjectMemory] = field(default_factory=dict)
    relations: dict[str, RelationMemory] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "GraphMemory":
        data = data or {}
        objects: dict[int, ObjectMemory] = {}
        raw_objects = data.get("objects", [])
        if isinstance(raw_objects, Mapping):
            raw_objects = raw_objects.values()
        for item in raw_objects:
            obj = ObjectMemory.from_dict(item)
            objects[obj.track_id] = obj

        relations: dict[str, RelationMemory] = {}
        raw_relations = data.get("relations", [])
        if isinstance(raw_relations, Mapping):
            raw_relations = raw_relations.values()
        for index, item in enumerate(raw_relations):
            rel = RelationMemory.from_dict(item)
            if not rel.relation_id:
                rel.relation_id = f"rel-{rel.subject_id}-{rel.predicate}-{rel.object_id}-{index}"
            relations[rel.relation_id] = rel
        return cls(objects, relations)

    def clone(self) -> "GraphMemory":
        return copy.deepcopy(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objects": [asdict(self.objects[k]) for k in sorted(self.objects)],
            "relations": [asdict(self.relations[k]) for k in sorted(self.relations)],
        }

    def relation_by_signature(self, signature: tuple[int, str, int]) -> RelationMemory | None:
        for rel in self.relations.values():
            if rel.signature() == signature:
                return rel
        return None


@dataclass(frozen=True)
class PredicateSchema:
    predicates: frozenset[str]
    compatibility: dict[str, frozenset[tuple[str, str]]] = field(default_factory=dict)
    allow_self_relations: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PredicateSchema":
        compatibility: dict[str, frozenset[tuple[str, str]]] = {}
        for predicate, pairs in data.get("compatibility", {}).items():
            compatibility[canonical_label(predicate)] = frozenset(
                (canonical_label(a), canonical_label(b)) for a, b in pairs
            )
        return cls(
            frozenset(canonical_label(v) for v in data.get("predicates", [])),
            compatibility,
            bool(data.get("allow_self_relations", False)),
        )

    @classmethod
    def load(cls, path: str | Path) -> "PredicateSchema":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def validates(self, predicate: str, subject_category: str, object_category: str) -> bool:
        predicate = canonical_label(predicate)
        if self.predicates and predicate not in self.predicates:
            return False
        allowed = self.compatibility.get(predicate)
        if not allowed:
            return True
        return (canonical_label(subject_category), canonical_label(object_category)) in allowed


@dataclass
class OperationReport:
    valid: bool
    operation: dict[str, Any]
    error: str | None = None


class GraphExecutor:
    SUPPORTED_OPS = {"ADD_NODE", "UPDATE_NODE", "ADD_REL", "UPDATE_REL", "END_REL", "DELETE_REL"}

    def __init__(self, schema: PredicateSchema | None = None) -> None:
        self.schema = schema or PredicateSchema(frozenset())

    def execute(
        self,
        memory: GraphMemory,
        operations: Sequence[Mapping[str, Any]],
        *,
        window_start: int,
        window_end: int,
        active_track_ids: Iterable[int] | None = None,
        strict: bool = False,
    ) -> tuple[GraphMemory, list[OperationReport]]:
        result = memory.clone()
        active = {int(v) for v in active_track_ids} if active_track_ids is not None else None
        reports: list[OperationReport] = []
        for raw in operations:
            op = dict(raw)
            try:
                self._apply(result, op, window_start, window_end, active)
                reports.append(OperationReport(True, op))
            except (KeyError, TypeError, ValueError) as exc:
                reports.append(OperationReport(False, op, str(exc)))
                if strict:
                    raise
        return result, reports

    def _apply(self, memory: GraphMemory, op: dict[str, Any], start: int, end: int, active: set[int] | None) -> None:
        name = str(op.get("op", "")).upper()
        if name not in self.SUPPORTED_OPS:
            raise ValueError(f"unsupported operation: {name}")
        if name == "ADD_NODE":
            track_id = _int(op.get("track_id", op.get("id")), "track_id")
            if track_id in memory.objects:
                raise ValueError(f"track {track_id} already exists")
            payload = dict(op); payload.setdefault("first_frame", start); payload.setdefault("last_frame", end)
            memory.objects[track_id] = ObjectMemory.from_dict(payload)
            return
        if name == "UPDATE_NODE":
            track_id = _int(op.get("track_id", op.get("id")), "track_id")
            if track_id not in memory.objects:
                raise ValueError(f"unknown track {track_id}")
            obj = memory.objects[track_id]
            for key in ("category", "state", "confidence"):
                if key in op:
                    setattr(obj, key, canonical_label(op[key]) if key == "category" else op[key])
            if "bbox" in op:
                obj.bbox = [float(v) for v in op["bbox"]]
            obj.last_frame = _int(op.get("last_frame", end), "last_frame")
            return

        relation = None
        if name in {"UPDATE_REL", "END_REL", "DELETE_REL"}:
            relation = self._get_relation(memory, op)
        if name == "ADD_REL":
            sid = _int(op.get("subject_id", op.get("subject")), "subject_id")
            oid = _int(op.get("object_id", op.get("object")), "object_id")
            pred = canonical_label(op.get("predicate"))
            if sid == oid and not self.schema.allow_self_relations:
                raise ValueError("self-relations are not allowed")
            for track_id in (sid, oid):
                if track_id not in memory.objects:
                    raise ValueError(f"unknown track {track_id}")
                if active is not None and track_id not in active and memory.objects[track_id].state not in {"occluded", "predicted"}:
                    raise ValueError(f"track {track_id} is not active")
            if not self.schema.validates(pred, memory.objects[sid].category, memory.objects[oid].category):
                raise ValueError("predicate violates compatibility schema")
            existing = memory.relation_by_signature((sid, pred, oid))
            if existing is not None and existing.state != "terminated":
                raise ValueError("duplicate active relation")
            start_frame = _int(op.get("start_frame", start), "start_frame")
            if start_frame < start or start_frame > end:
                raise ValueError("start_frame outside current window")
            evidence = sorted({_int(v, "evidence_frame") for v in op.get("evidence_frames", [])})
            if any(v < start or v > end for v in evidence):
                raise ValueError("evidence frame outside current window")
            rid = str(op.get("relation_id") or f"rel-{sid}-{pred}-{oid}-{start_frame}")
            memory.relations[rid] = RelationMemory(rid, sid, pred, oid, str(op.get("state", "active")), start_frame, None, evidence, _float(op.get("confidence", 1.0), "confidence"), str(op.get("source", "model")))
            return
        if name == "UPDATE_REL":
            assert relation is not None
            if relation.state == "terminated":
                raise ValueError("cannot update terminated relation")
            if "state" in op:
                relation.state = str(op["state"])
            if "confidence" in op:
                relation.confidence = _float(op["confidence"], "confidence")
            if "evidence_frames" in op:
                relation.evidence_frames = sorted(set(relation.evidence_frames) | {_int(v, "evidence_frame") for v in op["evidence_frames"]})
            return
        if name == "END_REL":
            assert relation is not None
            if relation.state == "terminated":
                raise ValueError("relation already terminated")
            end_frame = _int(op.get("end_frame", end), "end_frame")
            if end_frame < relation.start_frame or end_frame > end:
                raise ValueError("invalid end_frame")
            relation.state = "terminated"; relation.end_frame = end_frame
            return
        if name == "DELETE_REL":
            assert relation is not None
            if not str(op.get("reason", "")).strip():
                raise ValueError("DELETE_REL requires reason")
            del memory.relations[relation.relation_id]

    def _get_relation(self, memory: GraphMemory, op: Mapping[str, Any]) -> RelationMemory:
        rid = str(op.get("relation_id", "")).strip()
        if rid:
            if rid not in memory.relations:
                raise ValueError(f"unknown relation {rid}")
            return memory.relations[rid]
        if all(k in op for k in ("subject_id", "predicate", "object_id")):
            rel = memory.relation_by_signature((_int(op["subject_id"], "subject_id"), canonical_label(op["predicate"]), _int(op["object_id"], "object_id")))
            if rel is not None:
                return rel
        raise ValueError("relation_id or full relation signature is required")


class GraphDiffer:
    @staticmethod
    def diff(before: GraphMemory, after: GraphMemory, *, repair_mode: bool = False) -> list[dict[str, Any]]:
        ops: list[dict[str, Any]] = []
        for track_id, current in after.objects.items():
            previous = before.objects.get(track_id)
            if previous is None:
                payload = asdict(current); payload["op"] = "ADD_NODE"; ops.append(payload)
            elif asdict(previous) != asdict(current):
                payload = {"op": "UPDATE_NODE", "track_id": track_id, "state": current.state, "last_frame": current.last_frame, "bbox": current.bbox, "confidence": current.confidence}
                ops.append(payload)
        for rid, current in after.relations.items():
            previous = before.relations.get(rid)
            if previous is None and current.state != "terminated":
                payload = asdict(current); payload["op"] = "ADD_REL"; payload.pop("end_frame", None); ops.append(payload)
            elif previous is not None and previous.state != "terminated" and current.state == "terminated":
                ops.append({"op": "END_REL", "relation_id": rid, "end_frame": current.end_frame})
            elif previous is not None and asdict(previous) != asdict(current):
                ops.append({"op": "UPDATE_REL", "relation_id": rid, "state": current.state, "confidence": current.confidence, "evidence_frames": sorted(set(current.evidence_frames) - set(previous.evidence_frames))})
        for rid in sorted(set(before.relations) - set(after.relations)):
            previous = before.relations[rid]
            if repair_mode or previous.source == "corrupted":
                ops.append({"op": "DELETE_REL", "relation_id": rid, "reason": "unsupported-by-target-memory"})
            elif previous.state != "terminated":
                ops.append({"op": "END_REL", "relation_id": rid, "end_frame": previous.end_frame or previous.start_frame})
        return ops


_ANSWER_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL | re.IGNORECASE)


def parse_completion(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping) and "content" in value:
        value = value["content"]
    text = str(value).strip()
    match = _ANSWER_RE.search(text)
    if match:
        text = match.group(1).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    if not isinstance(parsed, Mapping) or not isinstance(parsed.get("operations"), list):
        raise ValueError("completion must be a JSON object containing operations[]")
    return dict(parsed)


def retrieve_memory(memory: GraphMemory, active_track_ids: Iterable[int], *, top_k_relations: int = 32) -> GraphMemory:
    active = {int(v) for v in active_track_ids}
    objects = {k: copy.deepcopy(v) for k, v in memory.objects.items() if k in active or v.state in {"occluded", "predicted"}}
    scored = []
    for rel in memory.relations.values():
        overlap = int(rel.subject_id in active) + int(rel.object_id in active)
        recency = max(rel.evidence_frames or [rel.start_frame])
        score = 1000 * overlap + recency + rel.confidence
        scored.append((score, rel))
    relations = {r.relation_id: copy.deepcopy(r) for _, r in sorted(scored, key=lambda x: x[0], reverse=True)[:top_k_relations]}
    for rel in relations.values():
        for tid in (rel.subject_id, rel.object_id):
            if tid in memory.objects:
                objects.setdefault(tid, copy.deepcopy(memory.objects[tid]))
    return GraphMemory(objects, relations)
