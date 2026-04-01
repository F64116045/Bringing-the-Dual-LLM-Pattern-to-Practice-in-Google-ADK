# Generated Benchmark Artifacts

This directory stores generated experiment artifacts:

- `case_registry.json`: full case registry synced from AgentDojo source tasks.
- `case_pack_v1_50_attacked.json`: curated attacked-only 50-case pack used by default benchmark runs.
- `mapping_v1_50_attacked.csv`: mapping table for the attacked-only curated cases.

Do not edit these files manually.
Regenerate with:

```bash
make cases-sync
make cases-pack
```
