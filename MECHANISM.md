# Dual-LLM Runtime Mechanism

This document explains how this project actually runs at runtime, including trust boundaries, callback flow, A2A interaction, and why some fixes were necessary.

## 1. Security Model (Current Implementation)

### Core roles

- **P-LLM (PrivilegedAgent)**:
  - Receives user instructions
  - Plans tool calls
  - Enforces security callbacks/policies before side-effect actions
- **Q-LLM (QuarantinedAgent)**:
  - Parses untrusted/raw content
  - Returns structured JSON
  - Runs remotely via A2A
- **KeyPlugin + HandleManager**:
  - Replaces raw tool output with `key:<uuid>`
  - Resolves keys only at boundaries where needed

### Trust boundary

- **Trusted**: user input, system policy, explicit tool call policy logic
- **Untrusted**: file contents, email contents, transaction text payloads, remote/raw text that may contain prompt injection

## 2. High-Level Data Flow

1. User sends request to P-LLM.
2. P-LLM calls a local tool (e.g. `read_file`, `get_balance`).
3. `after_tool_callback` sanitizes tool result:
   - Raw value stored in `HandleManager`
   - P-LLM context sees only `key:<uuid>`
4. If extraction/parsing is needed, P-LLM calls `qllm_remote`.
5. `before_tool_callback` resolves keys for Q-LLM-side parsing input.
6. Q-LLM returns JSON.
7. `after_tool_callback` validates schema and sanitizes result back to keys.
8. `after_agent_callback` resolves keys for final human-readable output.

## 3. Where This Is Implemented

- P-LLM setup:
  - `src/adk_dual_llm/core/privileged_agent.py`
- Q-LLM setup:
  - `src/adk_dual_llm/core/quarantined_agent.py`
  - `src/adk_dual_llm/core/server.py`
- Key isolation + schema checks:
  - `src/adk_dual_llm/security/key_plugin.py`
  - `src/adk_dual_llm/security/handle_manager.py`
- Banking policy:
  - `benchmarks/banking/policy.py`

## 4. Why Q-LLM Previously Returned Many `null`

### Root cause

The remote agent path (`AgentTool -> RemoteA2aAgent -> A2A`) behaved most reliably when the extraction payload was passed as a **single JSON string in `request`**.

When `request/source/format` were sent as flat separate fields, the remote side often behaved as if only the textual `request` mattered, producing unstable outputs (`null`, wrong field names, or request/source echo).

### Practical fix applied

In `key_plugin.before_tool_callback`, flat qllm args are packed to:

```json
{
  "request": "<task>",
  "source": "<resolved raw data>",
  "format": { ... }
}
```

Then serialized into `request` so remote Q-LLM receives a single coherent payload.

## 5. Callback Behavior (Important)

### `before_tool_callback`

- Resolves `key:<uuid>` back to raw values for tool execution.
- For `qllm_remote`, packs `request/source/format` into one JSON `request`.

### `after_tool_callback`

- For Q-LLM:
  - Validates against expected schema
  - On malformed response, uses fail-closed fallback (null-filled structured object) instead of crashing the entire session
- For all tools:
  - Sanitizes outputs into key-based references

### `after_agent_callback`

- Replaces key tokens with real values for user-facing answer rendering.

## 6. Policy Layer vs Threat Model

Current banking policy is strict capability control:

- blocks untrusted IBANs
- blocks amounts above threshold

This can block even explicit trusted-user requests. If your threat model is "user is fully trusted; only untrusted data is risky", policy should be adjusted accordingly in `benchmarks/banking/policy.py`.

## 7. Notes on A2A / ADK Defaults

- `AgentTool` default declaration is request-centric (single `request` string unless input schema is defined).
- `RemoteA2aAgent` and converters are experimental and may change behavior across versions.
- For stability, explicit payload contracts (single packed JSON) are recommended for extraction tasks.

## 8. Recommended Validation Checklist

1. `qllm-server` is healthy:
   - `docker compose ps -a`
2. Q-LLM packed payload log appears:
   - `[Packed Q-LLM Payload]`
3. Q-LLM output keys match expected `format` exactly.
4. Final output resolves values (not raw `key:...`).

