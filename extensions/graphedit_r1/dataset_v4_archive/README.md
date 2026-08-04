# Current 60-video `final_event_labels.json` data update

This package contains the updated GraphEdit-R1 data adapter for the current Air-SMOAM event labels. The labels are consumed directly instead of reconstructing relationships from legacy action labels.

## Extract

From the repository root:

```bash
bash extensions/graphedit_r1/dataset_v4_archive/unpack.sh
```

The script concatenates the binary archive parts under `archive/`, verifies the reconstructed tarball, and extracts the source to:

```text
extensions/graphedit_r1/dataset_v4/
```

Then read:

```text
extensions/graphedit_r1/dataset_v4/README.md
```

SHA-256 of the reconstructed archive:

```text
b6b2ee990d8a3720cb86b6e2296fa356894a51613a192717d773748d5c05a2e1
```

## Main changes

- recursively discovers exactly 60 `final_event_labels.json` files;
- preserves the established 42/6/12 split through an explicit manifest;
- converts selected candidates, event roles, regions, object behaviours, interactions and spatial relations;
- prefers `spatial_relations_refined` when available and otherwise merges `spatial_relations_by_frame` evidence into persistent relation instances;
- maps region/event references to stable negative integer node IDs for compatibility with the existing GraphEdit-R1 executor;
- retains confidence, source, review status, uncertain items and selection provenance;
- audits missing/empty fields and can filter training by `annotation_status`;
- never fabricates behaviours or interactions when those fields are empty;
- produces GraphEdit-R1-compatible frame records, a generated predicate schema, corpus statistics and issue reports.

## Validation on the supplied `bridge off` label

- 6 adapter tests passed;
- 13 annotation anchors were generated;
- 1,819 spatial observations were preserved;
- those observations were merged into 303 persistent relation instances;
- five functional regions were represented as static graph nodes;
- the spatial-only and `need_human_review` conditions were surfaced explicitly.
