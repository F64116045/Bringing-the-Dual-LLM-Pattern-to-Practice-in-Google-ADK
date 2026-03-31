# Generated Benchmark Artifacts

This directory stores generated experiment artifacts:

- `case_registry.json`: full case registry synced from AgentDojo source tasks.
- `case_pack_v1_50.json`: curated 50-case pack used by default benchmark runs.
- `mapping_v1_50.csv`: mapping table for curated cases.

Do not edit these files manually.
Regenerate with:

```bash
make cases-sync
make cases-pack
```
