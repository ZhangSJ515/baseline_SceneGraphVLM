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

## Included implementation

- executable delta-graph protocol with `ADD_NODE`, `UPDATE_NODE`, `ADD_REL`, `UPDATE_REL`, `END_REL`, and `DELETE_REL`;
- persistent object and relation-instance memory;
- deterministic parser, validator, executor, graph differ, and memory retrieval;
- memory-corruption curriculum for active historical-graph repair;
- frame records to windowed MSwift `messages` + `images` JSONL;
- SFT and GRPO launchers that reuse the baseline repository's Qwen3.5/M-Swift pipeline;
- MSwift ORM reward plugin for format, executability, node/relation quality, lifecycle, temporal boundaries, repair improvement, edit minimality, and hallucination penalties;
- CLI tools for building, validating, executing, and evaluating datasets/model outputs;
- AirGraph example schema, sample data, prompts, tests, ablations, metrics, and a complete implementation/research plan.

## Local validation completed before publication

- 6 unit tests passed;
- Python compilation passed;
- example dataset construction produced valid MSwift JSONL;
- JSONL validation passed;
- deterministic edit execution passed;
- the canonical target achieved 1.0 for all reward diagnostics and total reward.

No existing SceneGraphVLM reproduction code is modified by this supplement.
