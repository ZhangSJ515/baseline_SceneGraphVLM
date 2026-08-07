# GraphEdit-R1 source manifest

After running `unpack.sh`, the archive expands to:

```text
source/
├── README.md
├── pyproject.toml
├── configs/
│   └── airgraph.example.json
├── examples/
│   ├── completion.txt
│   ├── frame_records.jsonl
│   └── memory.json
├── graphedit_r1/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── core.py
│   ├── corruptor.py
│   ├── data.py
│   ├── rewards.py
│   └── swift_reward.py
├── prompts/
│   └── system_prompt.txt
├── scripts/
│   ├── run_grpo.sh
│   └── run_sft.sh
└── tests/
    ├── README.md
    ├── test_core.py
    └── test_rewards.py
```

The detailed README covers the research thesis, relationship to SceneGraphVLM/R1-SGG/trajectory methods, annotation conversion, graph-edit semantics, memory corruption, SFT/GRPO implementation, reward definitions, evaluation protocol, baselines, ablations, airport relation mapping, milestones, publication criteria, and known risks.
