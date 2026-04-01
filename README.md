# ADK Dual-LLM Security Lab

Deterministic prompt-injection defense experiments for tool-using agents, implemented with Google ADK.

This repository evaluates a fixed 50-case attacked benchmark pack across:

1. `baseline` (single LLM)
2. `dual_no_policy` (Dual-LLM isolation only)
3. `dual` (Dual-LLM isolation + policy callback)

## Project Status

This is a research-oriented benchmark lab focused on reproducibility and traceability, not a production SaaS package.

## Why This Repo Exists

LLM agents can be manipulated by hostile instructions hidden inside data (emails, files, web content, reviews).  
This lab ports AgentDojo-style tasks to ADK and tests whether Dual-LLM isolation plus policy hooks reduce attack success.

## Core Design

1. **P-LLM (Privileged Planner)** plans and calls tools.
2. **Q-LLM (Quarantined Extractor)** handles untrusted text via A2A.
3. **Key Isolation Plugin** replaces raw tool outputs with symbolic `key:<uuid>` handles.
4. **Policy Callback** blocks sensitive actions before tool execution.

Key implementation files:

- `src/adk_dual_llm/core/privileged_agent.py`
- `src/adk_dual_llm/core/quarantined_agent.py`
- `src/adk_dual_llm/security/key_plugin.py`
- `src/adk_dual_llm/core/server.py`

## Repository Map

High-value entry points:

- `docs/LAB_OVERVIEW.md` (end-to-end lab architecture and pipeline)
- `scripts/README.md` (script index)

## Requirements

1. Docker + Docker Compose
2. Python 3.12 (for local helper scripts)
3. At least one provider key in `.env`:
   - `OPENAI_API_KEY` and/or `GOOGLE_API_KEY`

## Quick Start

1. Copy env template:

```bash
cp .env.example .env
```

2. Set model(s) in `.env` or pass via `MODEL=...`:

```env
PLLM_MODEL=openai/gpt-4.1
QLLM_MODEL=openai/gpt-4.1
QLLM_URL=http://qllm-server:8001
```

3. Run full 3-mode benchmark:

```bash
make exp-v1 MODEL=openai/gpt-4.1
```

4. Summarize latest run:

```bash
make summary-latest
make table-latest ATTACK_SCOPE=attacked
```

## What Gets Produced

Each run writes to:

`results/runs/<RUN_ID>/`

Including:

- `baseline.jsonl`
- `dual_no_policy.jsonl`
- `dual.jsonl`
- `traces_baseline/*`
- `traces_dual_no_policy/*`
- `traces_dual/*`
- `summary.json`

## Case Packs

Generated artifacts are in `benchmarks/generated/`:

- `case_registry.json` (full synced registry)
- `case_pack_v1_50_attacked.json` (fixed attacked-only 50 pack)
- `mapping_v1_50_attacked.csv` (source mapping)

Regenerate:

```bash
make cases-sync
make cases-pack
```

## Retry Failed Cases (Token Saving)

Rerun only failed rows and merge back:

```bash
make retry-merge RUN_ID=<run-id> RETRY_CRITERIA=status_fail
```

## Limitations

1. API quota/rate limits can interrupt long runs.
2. ADK/A2A experimental warnings are expected in current dependency versions.
3. Results are model-sensitive; compare modes using the same model and same case pack.

## Acknowledgements

This benchmark methodology and task design are adapted from:

- AgentDojo (NeurIPS 2024): https://github.com/ethz-spylab/agentdojo
- CaMeL prompt-injection defense design ideas: https://github.com/google-research/camel-prompt-injection
- Dual-LLM pattern framing by Simon Willison: https://simonwillison.net/2023/Apr/25/dual-llm-pattern/
