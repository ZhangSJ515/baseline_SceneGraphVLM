# GraphEdit-R1 supplement

This directory delivers a complete, self-contained research supplement for extending SceneGraphVLM from previous-frame full-graph prompting to **track-grounded, persistent, executable video scene-graph editing**.

The full source tree is stored as a checksum-protected split archive under `archive/` because the publishing runtime did not provide GitHub CLI access. Extraction produces `source/`, containing all code, documentation, launch scripts, examples, configurations, and tests.

## Extract and verify

From the repository root:

```bash
bash extensions/graphedit_r1/unpack.sh
```

The script:

1. concatenates the numbered Base64 parts;
2. decodes `graphedit_r1_source.tar.gz`;
3. verifies SHA-256;
4. extracts the complete package to `extensions/graphedit_r1/source/`.

Then read:

```text
extensions/graphedit_r1/source/README.md
```

## Current 60-video final-event-label adapter

The latest Air-SMOAM labels already contain selected event participants,
functional regions, object behaviours, semantic interactions, sparse spatial
relations, confidence/provenance and annotation-review status. Use the direct
adapter under:

```text
extensions/graphedit_r1/dataset_v4/
```

First extract it:

```bash
bash extensions/graphedit_r1/dataset_v4_archive/unpack.sh
```

Then run:

```bash
bash extensions/graphedit_r1/dataset_v4/run_60video_pipeline.sh
```

It replaces the earlier action-to-relation heuristic and emits frame records
compatible with the unpacked GraphEdit-R1 builder. The adapter preserves the
existing 42/6/12 video split through an explicit split manifest; it never
generates a new random split.

## Included implementation

- executable delta-graph protocol with `ADD_NODE`, `UPDATE_NODE`, `ADD_REL`, `UPDATE_REL`, `END_REL`, and `DELETE_REL`;
- persistent object and relation-instance memory;
- deterministic parser, validator, executor, graph differ, and memory retrieval;
- memory-corruption curriculum for active historical-graph repair;
- frame records to windowed MSwift `messages` + `images` JSONL;
- SFT and GRPO launchers that reuse the baseline repository's Qwen3.5/M-Swift pipeline;
- MSwift ORM reward plugin for format, executability, node/relation quality, lifecycle, temporal boundaries, repair improvement, edit minimality, and hallucination penalties;
- CLI tools for building, validating, executing, and evaluating datasets/model outputs;
- AirGraph example schema, sample data, prompts, tests, ablations, metrics, and a complete implementation/research plan;
- direct ingestion and auditing of the current 60-video `final_event_labels.json` corpus.

## Local validation completed before publication

Core supplement:

- 6 unit tests passed;
- Python compilation passed;
- example dataset construction produced valid MSwift JSONL;
- JSONL validation passed;
- deterministic edit execution passed;
- the canonical target achieved 1.0 for all reward diagnostics and total reward.

Current v4 data adapter:

- 6 adapter tests passed;
- the supplied `bridge off` label produced 13 annotated snapshots;
- 1,819 spatial observations were preserved and merged into 303 persistent relation instances;
- regions, selected participants, spatial-only events and review-status warnings were validated.

No existing SceneGraphVLM reproduction code is modified by this supplement.
