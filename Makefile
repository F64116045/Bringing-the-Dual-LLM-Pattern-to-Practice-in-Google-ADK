SHELL := /bin/bash

MODEL ?= openai/gpt-4o-mini
CASES ?= benchmarks/case_pack_v1_50.json
ENV ?= all
LIMIT ?=

.PHONY: cases-sync cases-pack qllm-up qllm-down exp-v1 summary-latest

cases-sync:
	python3 scripts/sync_agentdojo_cases.py

cases-pack:
	python3 scripts/build_case_pack_v1_50.py

qllm-up:
	docker compose up -d qllm-server

qllm-down:
	docker compose stop qllm-server

exp-v1:
	./scripts/run_experiment_v1_50.sh --model "$(MODEL)" --cases "$(CASES)" --env "$(ENV)" $(if $(LIMIT),--limit "$(LIMIT)",)

summary-latest:
	python3 scripts/summarize_case_results.py --latest-run
