from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

from .core import GraphExecutor, GraphMemory, PredicateSchema, canonical_label, parse_completion


@dataclass(frozen=True)
class RewardWeights:
    format: float = 0.05
    executable: float = 0.10
    node: float = 0.10
    relation: float = 0.25
    lifecycle: float = 0.15
    boundary: float = 0.10
    repair: float = 0.15
    minimal: float = 0.10
    hallucination: float = 0.15


@dataclass
class RewardResult:
    total: float
    format: float
    executable: float
    node: float
    relation: float
    lifecycle: float
    boundary: float
    repair: float
    minimal: float
    hallucination: float
    parsed_operations: int
    valid_operations: int
    details: dict[str, Any]

    def to_dict(self):
        return asdict(self)


def _obj(value: Any):
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        return json.loads(value)
    return value or {}


def _list(value: Any):
    if isinstance(value, str):
        return json.loads(value)
    return list(value or [])


def _f1(pred, target):
    pred, target = set(pred), set(target)
    if not pred and not target:
        return 1.0
    if not pred or not target:
        return 0.0
    tp = len(pred & target)
    p, r = tp / len(pred), tp / len(target)
    return 2 * p * r / max(p + r, 1e-12)


def _nodes(memory: GraphMemory):
    return {(i, canonical_label(o.category)) for i, o in memory.objects.items()}


def _relations(memory: GraphMemory):
    return {(r.subject_id, canonical_label(r.predicate), r.object_id, r.state) for r in memory.relations.values()}


def temporal_iou(a, b):
    s1, e1 = a; s2, e2 = b
    inter = max(0, min(e1, e2) - max(s1, s2) + 1)
    union = max(e1, e2) - min(s1, s2) + 1
    return inter / union if union > 0 else 0.0


def boundary_score(pred: GraphMemory, target: GraphMemory, fallback_end: int):
    p = {r.signature(): r for r in pred.relations.values()}
    g = {r.signature(): r for r in target.relations.values()}
    shared = set(p) & set(g)
    if not shared:
        return 1.0 if not p and not g else 0.0
    scores = []
    for key in shared:
        pr, gt = p[key], g[key]
        scores.append(temporal_iou((pr.start_frame, pr.end_frame or fallback_end), (gt.start_frame, gt.end_frame or fallback_end)))
    return sum(scores) / len(scores)


def graph_distance(pred: GraphMemory, target: GraphMemory, fallback_end: int):
    return 0.35 * (1 - _f1(_nodes(pred), _nodes(target))) + 0.45 * (1 - _f1(_relations(pred), _relations(target))) + 0.20 * (1 - boundary_score(pred, target, fallback_end))


def op_sig(op):
    name = str(op.get("op", "")).upper()
    if op.get("relation_id"):
        return name, str(op["relation_id"])
    return name, int(op.get("subject_id", -1)), canonical_label(op.get("predicate")), int(op.get("object_id", -1))


def compute_reward(completion: Any, *, memory_before, gt_graph_after, active_track_ids, canonical_operations=None, predicate_schema=None, window_start=0, window_end=0, weights: RewardWeights | None = None):
    weights = weights or RewardWeights()
    before = GraphMemory.from_dict(_obj(memory_before)); target = GraphMemory.from_dict(_obj(gt_graph_after))
    active = [int(v) for v in _list(active_track_ids)]; target_ops = [dict(x) for x in _list(canonical_operations)]
    schema = PredicateSchema.from_dict(_obj(predicate_schema) if predicate_schema else {"predicates": []})
    try:
        parsed = parse_completion(completion); ops = [dict(x) for x in parsed["operations"]]; fmt = 1.0
    except Exception as exc:
        return RewardResult(-0.5,0,0,0,0,0,0,0,0,1,0,0,{"parse_error":str(exc)})
    pred, reports = GraphExecutor(schema).execute(before, ops, window_start=int(window_start), window_end=int(window_end), active_track_ids=active)
    executable = sum(int(r.valid) for r in reports) / max(len(reports), 1) if reports else 1.0
    node = _f1(_nodes(pred), _nodes(target)); relation = _f1(_relations(pred), _relations(target))
    lifecycle = _f1({op_sig(x) for x in ops if str(x.get("op","")).upper().endswith("REL")}, {op_sig(x) for x in target_ops if str(x.get("op","")).upper().endswith("REL")})
    boundary = boundary_score(pred, target, int(window_end))
    d0, d1 = graph_distance(before, target, int(window_end)), graph_distance(pred, target, int(window_end))
    repair = (1.0 if d1 <= 1e-12 else 0.0) if d0 <= 1e-12 else max(-1.0, min(1.0, (d0-d1)/d0))
    minimal = math.exp(-abs(len(ops)-len(target_ops))/(len(target_ops)+1.0))
    bad_refs = sum(1 for op in ops for k in ("subject_id","object_id") if k in op and int(op[k]) not in active)
    invalid = sum(int(not r.valid) for r in reports)
    hallucination = min(1.0, (bad_refs + invalid) / max(len(ops), 1))
    positive_weight = weights.format+weights.executable+weights.node+weights.relation+weights.lifecycle+weights.boundary+weights.repair+weights.minimal
    positive = (weights.format*fmt + weights.executable*executable + weights.node*node + weights.relation*relation + weights.lifecycle*lifecycle + weights.boundary*boundary + weights.repair*repair + weights.minimal*minimal) / positive_weight
    total = max(-1.0, min(1.0, positive - weights.hallucination*hallucination))
    return RewardResult(total,fmt,executable,node,relation,lifecycle,boundary,repair,minimal,hallucination,len(ops),sum(int(r.valid) for r in reports),{"before_distance":d0,"after_distance":d1,"invalid_operations":[asdict(r) for r in reports if not r.valid]})
