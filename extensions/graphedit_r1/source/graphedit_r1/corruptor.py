from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Iterable

from .core import GraphMemory, PredicateSchema, RelationMemory


@dataclass
class CorruptionRecord:
    kind: str
    detail: dict


class GraphCorruptor:
    def __init__(self, schema: PredicateSchema, seed: int = 0) -> None:
        self.schema = schema
        self.rng = random.Random(seed)

    def corrupt(self, memory: GraphMemory, *, rate: float, active_track_ids: Iterable[int] | None = None):
        if not 0.0 <= rate <= 1.0:
            raise ValueError("rate must be in [0,1]")
        result = memory.clone()
        active = list(active_track_ids or result.objects.keys())
        records: list[CorruptionRecord] = []
        attempts = max(1, round(rate * max(1, len(result.relations) + 1)))
        operations = [self._drop, self._fake, self._replace, self._swap, self._premature_end, self._duplicate]
        for _ in range(attempts):
            if self.rng.random() > rate:
                continue
            rec = self.rng.choice(operations)(result, active)
            if rec is not None:
                records.append(rec)
        return result, records

    def _pick(self, memory: GraphMemory):
        rels = [r for r in memory.relations.values() if r.state != "terminated"]
        return self.rng.choice(rels) if rels else None

    def _drop(self, memory: GraphMemory, active: list[int]):
        rel = self._pick(memory)
        if rel is None:
            return None
        del memory.relations[rel.relation_id]
        return CorruptionRecord("drop_relation", {"relation_id": rel.relation_id})

    def _fake(self, memory: GraphMemory, active: list[int]):
        ids = [i for i in active if i in memory.objects]
        if len(ids) < 2 or not self.schema.predicates:
            return None
        for _ in range(20):
            sid, oid = self.rng.sample(ids, 2)
            pred = self.rng.choice(sorted(self.schema.predicates))
            if not self.schema.validates(pred, memory.objects[sid].category, memory.objects[oid].category):
                continue
            rid = f"corrupt-{sid}-{pred}-{oid}-{self.rng.randrange(10**8)}"
            memory.relations[rid] = RelationMemory(rid, sid, pred, oid, source="corrupted")
            return CorruptionRecord("add_fake_relation", {"relation_id": rid})
        return None

    def _replace(self, memory: GraphMemory, active: list[int]):
        rel = self._pick(memory)
        options = [] if rel is None else [p for p in self.schema.predicates if p != rel.predicate]
        if rel is None or not options:
            return None
        old = rel.predicate
        rel.predicate = self.rng.choice(sorted(options)); rel.source = "corrupted"
        return CorruptionRecord("replace_predicate", {"relation_id": rel.relation_id, "old": old, "new": rel.predicate})

    def _swap(self, memory: GraphMemory, active: list[int]):
        rel = self._pick(memory)
        if rel is None:
            return None
        rel.subject_id, rel.object_id = rel.object_id, rel.subject_id; rel.source = "corrupted"
        return CorruptionRecord("swap_subject_object", {"relation_id": rel.relation_id})

    def _premature_end(self, memory: GraphMemory, active: list[int]):
        rel = self._pick(memory)
        if rel is None:
            return None
        rel.state = "terminated"; rel.end_frame = rel.start_frame; rel.source = "corrupted"
        return CorruptionRecord("premature_end", {"relation_id": rel.relation_id})

    def _duplicate(self, memory: GraphMemory, active: list[int]):
        rel = self._pick(memory)
        if rel is None:
            return None
        dup = copy.deepcopy(rel); dup.relation_id = f"corrupt-dup-{rel.relation_id}-{self.rng.randrange(10**8)}"; dup.source = "corrupted"
        memory.relations[dup.relation_id] = dup
        return CorruptionRecord("duplicate_relation", {"relation_id": dup.relation_id})
