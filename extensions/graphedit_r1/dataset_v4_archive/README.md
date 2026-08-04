# Current 60-video `final_event_labels.json` data adapter

This package updates GraphEdit-R1 for the current Air-SMOAM event-label schema. It reads each video directory's `final_event_labels.json` directly instead of reconstructing relationships from legacy action labels.

## Extract

From the repository root:

```bash
bash extensions/graphedit_r1/dataset_v4_archive/unpack.sh
```

The script Base64-decodes the source archive, verifies its SHA-256, and extracts the directly usable source to:

```text
extensions/graphedit_r1/dataset_v4/
```

Then read:

```text
extensions/graphedit_r1/dataset_v4/README.md
```

Archive SHA-256:

```text
ba6e869ade73b253cbdecaed37c19641852a249ffc8ede0e70e9bd020646889b
```

## Actual label structure handled

```text
annotation_version
selection_policy
regions[]
events[]
  candidate_objects[]
  main_objects[]
  object_behaviors[]
  interactions[]
  spatial_relations_by_frame[]
  spatial_relations_refined[]
  event_description_cn
  uncertain_items[]
  annotation_status
```

The file is event-level with sparse spatial anchor frames. Candidate objects contain event-range track summaries, not dense per-frame boxes. Image paths are therefore resolved from a separate frame root and template; the adapter never fabricates missing boxes or dense intermediate labels.

## Default compact-semantic profile

The default converter keeps only information useful for the persistent video scene graph:

- selected candidate objects, with roles and selection provenance;
- functional regions as stable graph nodes;
- one event node per event;
- high-confidence semantic interactions;
- high-confidence object behaviours represented as object-to-event state relations;
- high-confidence `spatial_relations_refined`;
- sparse per-anchor `inside_region` relations.

It intentionally excludes the large set of low-value pairwise `left/right/above/below/far` observations from the main SFT/GRPO data. A separate `spatial_ablation.json` profile enables directional relations for controlled ablations.

## Main implementation details

- recursively discovers exactly 60 `final_event_labels.json` files by default;
- preserves the established 42/6/12 split only through an explicit split manifest and never guesses membership;
- maps physical tracks to their numeric IDs and maps region/event nodes to stable negative integer IDs;
- produces one update target for every annotated spatial anchor plus an event-closure target;
- maintains persistent interaction, behaviour and refined-spatial relation instances across anchors;
- treats per-anchor region relations as sparse evidence and terminates them when they disappear at the next annotated anchor;
- carries confidence, source, evidence frames, annotation version, selection policy, uncertainty and review status;
- exposes `top_k_memory_relations` and uses it to bound prompt memory;
- produces GraphEdit-R1-compatible MSwift JSONL, generated predicate schemas, corpus statistics and issue reports;
- never invents interactions or behaviours when their source arrays are empty.

## Validation on the supplied bridge-off label

The current full label was used as an integration test without copying it into the repository. Results under the default compact profile:

- 13 GraphEdit update samples: 12 sparse spatial anchors and one event-closure sample;
- 11 selected physical objects retained and background objects excluded;
- five functional regions represented as graph nodes;
- three interactions retained;
- six object behaviours retained;
- four refined spatial relations retained;
- 64 high-confidence `inside_region` observations retained from the sparse anchors;
- all 1,819 raw spatial observations were inspected, but generic directional/far relations were excluded from the default training target;
- `llm_prelabel_need_human_review` is propagated as `requires_human_review=true`.

Validation performed:

- four repository-contained adapter unit tests passed;
- Python compilation passed;
- shell launcher syntax passed;
- the supplied complete label converted successfully to `unsplit.jsonl` with 13 rows;
- final event closure emitted 19 `END_REL` operations for active semantic and spatial relations.

## Build all 60 videos

After extraction:

```bash
LABELS_ROOT=/path/to/60_video_label_root \
MEDIA_ROOT=/path/to/extracted_frames \
SPLIT_MANIFEST=/path/to/air_smoam_42_6_12_split.json \
OUTPUT_ROOT=/workspace/datasets/data_playground/GraphEditR1_v4 \
bash extensions/graphedit_r1/dataset_v4/scripts/build_60_videos.sh
```

The label directories are expected to follow:

```text
LABELS_ROOT/
  <video-name>/
    final_event_labels.json
```

The video directory name is used as `video_id`.
