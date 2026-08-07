from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import GraphExecutor, GraphMemory, PredicateSchema, parse_completion
from .rewards import compute_reward


def _jsonl(path):
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def cmd_execute(args):
    schema = PredicateSchema.load(args.schema)
    memory = GraphMemory.from_dict(json.loads(Path(args.memory).read_text(encoding="utf-8")))
    parsed = parse_completion(Path(args.completion).read_text(encoding="utf-8"))
    updated, reports = GraphExecutor(schema).execute(memory, parsed["operations"], window_start=args.window_start, window_end=args.window_end, active_track_ids=args.active_track_ids)
    print(json.dumps(updated.to_dict(), ensure_ascii=False, indent=2))
    invalid = [r.__dict__ for r in reports if not r.valid]
    if invalid:
        print(json.dumps(invalid, ensure_ascii=False, indent=2))
        return 1
    return 0


def cmd_validate(args):
    invalid = 0; total = 0
    for total, record in enumerate(_jsonl(args.input), start=1):
        try:
            if "messages" in record:
                parse_completion(record["messages"][-1]["content"])
            if "memory_before" in record:
                GraphMemory.from_dict(json.loads(record["memory_before"]) if isinstance(record["memory_before"], str) else record["memory_before"])
        except Exception as exc:
            invalid += 1; print(f"record {total}: {exc}")
    print(f"validated={total} invalid={invalid}")
    return 1 if invalid else 0


def cmd_evaluate(args):
    rows = list(_jsonl(args.input)); sums = {}
    for record in rows:
        completion = record.get("completion") or record.get("response") or record.get("messages", [{}])[-1].get("content", "")
        result = compute_reward(completion, memory_before=record["memory_before"], gt_graph_after=record["gt_graph_after"], active_track_ids=record["active_track_ids"], canonical_operations=record.get("canonical_operations"), predicate_schema=record.get("predicate_schema"), window_start=record.get("window_start",0), window_end=record.get("window_end",0))
        for k,v in result.to_dict().items():
            if isinstance(v,(int,float)):
                sums[k] = sums.get(k,0.0)+float(v)
    print(json.dumps({k:v/max(len(rows),1) for k,v in sums.items()}, ensure_ascii=False, indent=2))
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="GraphEdit-R1 utilities")
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("validate"); q.add_argument("--input", required=True); q.set_defaults(func=cmd_validate)
    q = sub.add_parser("evaluate"); q.add_argument("--input", required=True); q.set_defaults(func=cmd_evaluate)
    q = sub.add_parser("execute"); q.add_argument("--memory", required=True); q.add_argument("--completion", required=True); q.add_argument("--schema", required=True); q.add_argument("--window-start", type=int, required=True); q.add_argument("--window-end", type=int, required=True); q.add_argument("--active-track-ids", type=int, nargs="+", required=True); q.set_defaults(func=cmd_execute)
    return p


def main():
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
