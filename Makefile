SHELL := /bin/bash

MODEL ?= openai/gpt-4.1
CASES ?= benchmarks/generated/case_pack_v1_50_attacked.json
ENV ?= all
LIMIT ?=
ATTACK_SCOPE ?= attacked
RETRY_CRITERIA ?= status_fail
RETRY_FROM_MERGED ?=
RETRY_OUTPUT_TAG ?=

.PHONY: help cases-sync cases-pack qllm-up qllm-down exp-v1 summary-latest table-latest
.PHONY: retry-merge

help:
	@echo "Experiment Lab commands"
	@echo "  make exp-v1 MODEL=openai/gpt-4.1             # run baseline + dual_no_policy + dual"
	@echo "  make exp-v1 MODEL=... ENV=banking LIMIT=5    # quick smoke run"
	@echo "  make summary-latest                           # summarize latest run jsonl"
	@echo "  make table-latest ATTACK_SCOPE=attacked       # render paper-style markdown table"
	@echo "  make retry-merge RUN_ID=<id>                  # rerun failed cases and merge"
	@echo "  make cases-sync && make cases-pack            # rebuild generated case artifacts"
	@echo "  make qllm-up / make qllm-down                 # start/stop qllm-server"

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

table-latest:
	python3 scripts/render_eval_table.py --latest-run --attack-scope "$(ATTACK_SCOPE)"

retry-merge:
	./scripts/retry_failed_and_merge.sh $(if $(RUN_ID),--run-id "$(RUN_ID)",) --model "$(MODEL)" --cases "$(CASES)" --env "$(ENV)" --criteria "$(RETRY_CRITERIA)" $(if $(RETRY_FROM_MERGED),--from-merged,) $(if $(RETRY_OUTPUT_TAG),--output-tag "$(RETRY_OUTPUT_TAG)",)
