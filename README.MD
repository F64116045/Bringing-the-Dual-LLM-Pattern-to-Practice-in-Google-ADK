# Bringing the Dual-LLM Pattern to Practice in Google ADK for Deterministic AI Agent Security against Prompt Injection

<p align="center">
  <img src="https://img.shields.io/badge/Conference-AROB%202026-blue?style=for-the-badge&logo=google-scholar&logoColor=white" alt="AROB 2026">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Framework-Google%20ADK-34A853?style=for-the-badge&logo=google&logoColor=white" alt="Google ADK">
</p>

- **Authors:** Huang Shuo¹ and [Shin-Jie Lee](https://sites.google.com/view/shinjielee/)²
- **Affiliation:** Department of Computer Science and Information Engineering, National Cheng Kung University, Tainan, Taiwan

> This paper has been presented at the [**31st International Symposium on Artificial Life and Robotics (ISAROB 2026)**](https://isarob.org/symposium/).

## Abstract

Large Language Models (LLMs) are increasingly deployed as autonomous agents but remain highly vulnerable to prompt injection attacks that can induce unauthorized actions or data exfiltration. Probabilistic filtering cannot provide deterministic safety, motivating architectural defenses such as the Dual LLM pattern and the CaMeL framework. To make these designs deployable, we implement a Dual LLM–inspired security plugin within Google’s Agent Development Kit (ADK). The plugin (1) isolates a privileged LLM (P-LLM) from a quarantined LLM (Q-LLM), (2) replaces untrusted content with UUID-based symbolic keys, (3) enforces structured, schema-validated exchanges, and (4) applies customizable pre-tool security policies via ADK callbacks. We recreated representative AgentDojo tasks in ADK and simulated 27 security test cases. The undefended baseline passed only 7 cases, with 20 compromised task completions. Dual LLM isolation improved robustness to 19 cases, blocking most injections. Remaining failures stemmed from malicious data extracted by delegated subtasks or reliance on untrusted data—issues mitigable through stricter policies or trusted data sources. These results show that Dual LLM architecture provides a practical and effective foundation for secure LLM-based agents.

## Our Design

This project implements the architectural defense mechanism described in Section 3 of our paper. It enforces strict isolation between trusted and untrusted information flows using the Google ADK framework.

The system consists of the following core components:

1. **Privileged LLM (P-LLM):** Handles high-level planning and tool execution. It is structurally blind to raw data from untrusted sources, reasoning only over symbolic UUID keys.
2. **Quarantined LLM (Q-LLM):** An isolated component responsible for processing untrusted content (e.g., parsing emails, summarizing web pages). It executes subtasks via the Agent2Agent (A2A) protocol and returns structured, schema-validated JSON.
3. **Key–Value Translation Plugin:** A boundary filter that intercepts all outputs from the Q-LLM and tools. It replaces raw values with symbolic keys (e.g., `key:8f92...`) before they reach the P-LLM's context.
4. **Security Policy Callback:** Utilizes ADK’s `before_tool_callback` to enforce deterministic, capability-based access control (e.g., allowlisting IBANs) before any action is executed.

<img src="img/system.png" width="400">

## Repository Structure

The codebase is organized to reflect the modular design of the proposed architecture:

```
.
├── src/
│   └── adk_dual_llm/
│       ├── core/             # Core P-LLM and Q-LLM agent definitions
│       ├── security/         # KeyPlugin (KV Translation) and HandleManager
│       └── server.py         # Q-LLM Remote A2A Server implementation
├── benchmarks/               # AgentDojo environment replications
│   ├── banking/              # E-Banking environment & Allowlist Policy
│   ├── slack/                # Slack environment & Domain Policy
│   ├── travel/               # Travel Agency environment
│   └── workspace/            # Workspace/Productivity environment
├── scripts/                  # Execution and evaluation scripts
├── docker-compose.yml        # Orchestration for P-LLM and Q-LLM containers
├── Dockerfile                # Environment definition (Python 3.12)
└── pyproject.toml            # Dependency management
```

## Installation and Setup

This project utilizes Docker to ensure a reproducible experimental environment, separating the Q-LLM server from the P-LLM client.

### Prerequisites

- Docker and Docker Compose

### Configuration

Create a `.env` file in the root directory to configure the necessary API keys. A template is provided in `.env.example`.

```bash
cp .env.example .env
```

Edit the `.env` file:

```
# Required for ADK Core and Gemini Models
GOOGLE_API_KEY=your_google_api_key

# Optional (if replicating experiments using OpenAI models)
OPENAI_API_KEY=your_openai_api_key
```

## Reproducing Experiments

> ⚠️ Important Note on Benchmark Replication:
Due to the architectural differences between Google ADK and the native AgentDojo runtime, we replicated the core logic, tools, and selected test cases of AgentDojo within the ADK environment. We do not execute the AgentDojo codebase directly.
> 
> 
> This repository focuses on validating the Dual LLM architecture against representative injection scenarios. For the complete, original benchmark suite and the ability to run all 600+ test cases, please refer to the official [AgentDojo Repository](https://github.com/ethz-spylab/agentdojo).
> 

We provide scripts to replicate the evaluation results presented in **Table 1** of the paper. The experiments compare the Dual LLM architecture against the AgentDojo benchmark cases.

To run the full evaluation suite using Docker Compose:

```bash
docker-compose up --build
```

This command will:

1. Start the isolated **Q-LLM Server** (Quarantined Environment).
2. Launch the **Benchmark Runner** container.
3. Execute the 27 security test cases across the four environments.

### Running Individual Environments

To evaluate specific environments individually, use the following commands:

- **E-Banking Environment:** `docker-compose run --rm benchmark-runner python scripts/run_banking.py`
- **Slack Environment:** `docker-compose run --rm benchmark-runner python scripts/run_slack.py`
- **Travel Environment:** `docker-compose run --rm benchmark-runner python scripts/run_travel.py`
- **Workspace Environment:** `docker-compose run --rm benchmark-runner python scripts/run_workspace.py`

## References & Acknowledgements

This work builds upon foundational research in LLM security. We explicitly acknowledge the following works:

### 1. AgentDojo

Our evaluation methodology and test cases are adapted from the **AgentDojo** benchmark.

- **Paper:** [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://openreview.net/forum?id=m1YYAQjO3w) (NeurIPS 2024)
- **Repository:** [ethz-spylab/agentdojo](https://github.com/ethz-spylab/agentdojo)

### 2. CaMeL Framework

Our security policy implementation (`before_tool_callback`) is inspired by the capability-based access control proposed in the **CaMeL** framework.

- **Paper:** [CaMeL: Defeating Prompt Injections by Design](https://arxiv.org/abs/2312.06674) (arXiv 2025)
- **Repository:** [google-research/camel-prompt-injection](https://github.com/google-research/camel-prompt-injection)

### 3. Dual LLM Pattern

The conceptual foundation of separating Privileged and Quarantined LLMs was originally proposed by **Simon Willison**.

- **Article:** [The Dual LLM pattern for building AI assistants that can resist prompt injection](https://simonwillison.net/2023/Apr/25/dual-llm-pattern/) (April 2023)

### 4.Google Agent Development Kit (ADK)

Our system is implemented using the **Google ADK** framework, leveraging its Agent2Agent (A2A) protocol for secure isolation.

- [Google ADK Documentation](https://google.github.io/adk-docs/)