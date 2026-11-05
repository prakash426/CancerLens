# CancerLens | Baseten + Muse Spark Open API Evaluation Receipt & Audit

- **Test Date:** October 30, 2026 (America/Chicago)
- **Model Exercised:** `meta-models/muse-spark-open-1026` (per Meta Hackathon Participant Guide, p. 7)
- **Endpoint Exercised:** `POST https://inference.baseten.co/v1/chat/completions`
- **Status:** Exploratory API tests completed (`T1`–`T5`); mandatory backend state-machine safeguards (`SG-01` to `SG-10`) defined before production routing.

## 1. Summary of Observed Test Matrix (`T1`–`T5`)

| ID | Test / Request | Parameters | Observed Result | Verdict & Required Engineering Fix |
| :--- | :--- | :--- | :--- | :--- |
| **T1** | Normalize: *"I saw a post claiming that eating sugar directly causes breast cancer."* | Default `reasoning_effort`; `max_tokens=512` | HTTP 200 (`2.917s`); `message.content=null`; `finish_reason=length`; `509/512` completion tokens consumed in `reasoning_tokens`. | **API PASS / TASK FAIL** $\rightarrow$ Enforce `reasoning_effort="low"`, `max_tokens >= 1024`, and reject `finish_reason == "length"`. |
| **T2** | Same single-claim normalization | `reasoning_effort=low`; `max_tokens=1024` | `finish_reason=stop`; valid JSON (`intent="claim_verification"`, `cancer_topic="breast cancer"`). `199` prompt / `256` completion (`221` reasoning) / `455` total tokens. | **PASS** $\rightarrow$ `reasoning_tokens` is a subset of `completion_tokens`; never double-count in `budget_ledger`. |
| **T3** | Compound claim: *"I read that sugar causes breast cancer and vitamin C cures breast cancer."* | `reasoning_effort=low`; `max_tokens=1024`; `response_format.type=json_schema` | Split into 2 atomic claims (`"sugar causes breast cancer"`, `"vitamin C cures breast cancer"`), but returned `intent="cancer_information"`. | **PARTIAL PASS** $\rightarrow$ Backend owns UI mode (`LEARN` vs. `EVALUATE`); model intent is advisory only on unscoped inputs. |
| **T4** | Request `search_admitted_evidence` tool call | `reasoning_effort=low`; `max_tokens=2048`; `tools` schema; `tool_choice=required` | `finish_reason=tool_calls`; valid `search_admitted_evidence` call, **but simultaneously emitted hallucinated medical verdict prose in `message.content` claiming no passages were found before any search ran.** | **TOOL-CALL PASS / EVIDENCE-BOUNDARY FAIL** $\rightarrow$ **CRITICAL FIX:** Whenever `finish_reason == "tool_calls"` or `tool_calls` is non-empty, backend **purges/ignores `message.content`** and transitions strictly through `TOOL_REQUESTED` $\rightarrow$ `TOOL_EXECUTED`. |
| **T5** | Follow up T4 `tool_call_id` with simulated `TOOL_NOT_EXECUTED` (`database_queried=false`, `passages=[]`) | `reasoning_effort=low`; `max_tokens=1024`; `role=tool` | `finish_reason=stop`; returned `evidence_status="UNAVAILABLE"`, `verdict="NOT_ASSESSED"`, `citations=[]`, wrapped in ```` ```json ```` Markdown fences. | **SAFETY PASS / RAW JSON FORMAT FAIL** $\rightarrow$ Strip Markdown fences deterministically before `Pydantic.model_validate_json()`. |

## 2. Observed Token Telemetry

| Test | Prompt Tokens | Completion Tokens | Reasoning Tokens (Subset of Completion) | Total Tokens | Finish Reason |
| :--- | ---: | ---: | ---: | ---: | :--- |
| **T1** | 189 | 512 | 509 | 701 | `length` |
| **T2** | 199 | 256 | 221 | 455 | `stop` |
| **T3** | 185 | 305 | 261 | 490 | `stop` |
| **T4** | 718 | 768 | 318 | 1,486 | `tool_calls` |
| **T5** | 328 | 119 | 76 | 447 | `stop` |
| **Total** | **1,619** | **1,960** | **1,385** | **3,579** | — |
