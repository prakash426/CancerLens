# Baseten Reference & CancerLens Claim Verification Layer Guide (`Baseten_Guide.md`)

- **Document Role:** Authoritative Technical Reference for Baseten (`$100` Hackathon Credits) & CancerLens Claim Verification Layer
- **Last Updated:** October 31, 2026 (`America/Chicago`)
- **Locked Project Decision:**
  - CancerLens uses **Baseten's Serverless Model API (`POST https://inference.baseten.co/v1/chat/completions`)** with the official hackathon model **`meta-models/muse-spark-open-1026`** (Meta Hackathon Participant Guide, p. 7) to power the **Claim Verification Layer (Evaluate Mode)**.
  - CancerLens does **not** deploy custom GPU containers (`Truss`, `BEI`, or `Chains`), does **not** rent per-minute GPUs (`L4`/`T4`), and does **not** run secondary PyTorch cross-encoders or NLI models. All inference is serverless and billed strictly per token.

---

## 1. Verified Baseten Endpoint & Authentication (`T1`–`T5` Live Evaluation)

### 1.1 Endpoint & Model Slug
- **Endpoint:** `POST https://inference.baseten.co/v1/chat/completions`
- **Model ID:** `meta-models/muse-spark-open-1026`
- **Authorization Header:** `Authorization: Bearer $BASETEN_API_KEY`
- **Content-Type:** `application/json`
- **Idle Cost:** **`$0.00`** (serverless token-based billing against the `$100.00` Baseten credit pool).

### 1.2 Mandatory macOS Python TLS & Key Validation Rules (`SG-09`)
1. **macOS Python SSL Verification (`certifi`):**
   - Standard Python `urllib` / unconfigured `httpx` on macOS can fail with `ssl.SSLCertVerificationError: unable to get local issuer certificate`.
   - Always pass `verify=ssl.create_default_context(cafile=certifi.where())` to `httpx.AsyncClient`. **Never** set `verify=False`.
2. **Environment Variable Sanity Check:**
   - During early testing, a local shell issue accidentally set `BASETEN_API_KEY="echo"` (4 chars), causing `HTTP 401 {"error":"Authentication required."}`.
   - Backend startup/request validation must strip whitespace, verify `len(key) >= 20`, and reject placeholder values.

---

## 2. Empirical Findings from Live Tests (`T1`–`T5`, Oct 30, 2026) & Mandatory Fixes

| Test ID | What Was Tested | Parameters | Observed Behavior | Mandatory Backend Rule (`SG-01`–`SG-10`) |
| :--- | :--- | :--- | :--- | :--- |
| **`T1`** | Single-claim normalization (*"eating sugar directly causes breast cancer"*) | Default `reasoning_effort`, `max_tokens=512` | `HTTP 200` (`2.92s`), `finish_reason="length"`, `message.content=null`. `509/512` completion tokens were consumed by `reasoning_tokens`. | **`SG-04`:** Always pass `reasoning_effort="low"` and `max_tokens >= 1024`. Treat `finish_reason == "length"` or `content is None` as an incomplete generation error—never treat `HTTP 200` alone as success. |
| **`T2`** | Same single-claim normalization | `reasoning_effort="low"`, `max_tokens=1024` | `finish_reason="stop"`, valid JSON (`intent="claim_verification"`, `cancer_topic="breast cancer"`). `199` prompt + `256` completion (`221` reasoning) = `455` total tokens. | **`SG-05`:** `completion_tokens_details.reasoning_tokens` is a **subset** of `completion_tokens`. Never add `reasoning_tokens` on top of `completion_tokens` in `budget_ledger`. |
| **`T3`** | Compound claim splitting (*"sugar causes breast cancer and vitamin C cures breast cancer"*) | `reasoning_effort="low"`, `max_tokens=1024`, `response_format={"type": "json_schema", ...}` | Extracted both atomic claims accurately into JSON array, but returned `intent="cancer_information"`. | **`SG-06`:** Backend code locks `resolved_mode` (`LEARN` vs. `EVALUATE`) from the user's explicit UI selection. Model-inferred `intent` is advisory only. |
| **`T4`** | Tool call generation (`search_admitted_evidence`) | `reasoning_effort="low"`, `max_tokens=2048`, `tools=[...]`, `tool_choice="required"` | `finish_reason="tool_calls"`; valid tool call arguments, **but simultaneously populated `message.content` with ungrounded medical verdict prose claiming no passages were found before any search ran.** | **`SG-02` (CRITICAL):** Whenever `finish_reason == "tool_calls"` or `message.tool_calls` is non-empty, backend code **must immediately discard/purge `message.content`** and execute the real `Cancer Info API` search first. |
| **`T5`** | Grounded verification turn after tool result (`TOOL_NOT_EXECUTED`) | `reasoning_effort="low"`, `max_tokens=1024`, `role="tool"` | `finish_reason="stop"`; correctly returned `evidence_status="UNAVAILABLE"`, `verdict="NOT_ASSESSED"`, `citations=[]`, but wrapped JSON inside ```` ```json ... ``` ```` fences. | **`SG-07`:** Always strip Markdown code fences (` ```json ... ``` `) before calling `Pydantic.model_validate_json()`. |

---

## 3. How Baseten Powers the CancerLens Claim Verification Layer

In CancerLens, **Baseten (`meta-models/muse-spark-open-1026`)** is dedicated to the **Claim Verification Layer** in `backend/app/providers/baseten_client.py` and `backend/app/investigator/evaluate_investigator.py`:

1. **Step 1 — Claim Normalization & Atomic Claim Decomposition (`T2`/`T3` Pattern):**
   - Receives the user's confirmed claim text.
   - Calls `POST https://inference.baseten.co/v1/chat/completions` with `model="meta-models/muse-spark-open-1026"`, `reasoning_effort="low"`, `max_tokens=1024`, and `response_format={"type": "json_schema", ...}`.
   - Strips any Markdown fences (`SG-07`) and validates into `1–5` atomic claims + target `cancer_topic`.
2. **Step 2 — Controlled Evidence Search Planning (`T4` Pattern + `SG-02` Purge):**
   - Requests `search_admitted_evidence` tool calls (up to $\le 3$ bounded hops).
   - Backend immediately purges `message.content` (`SG-02`) on any `tool_calls` turn and executes the real HTTPS callout to **`Cancer Info API`** (`CancerInfoAPIClient.search_evidence()`).
   - Backend records the explicit 4-state `RetrievalState` (`SG-03`: `TOOL_NOT_EXECUTED`, `TOOL_FAILED`, `SEARCH_EXECUTED_NO_MATCHES`, `SEARCH_EXECUTED_WITH_MATCHES`).
3. **Step 3 — Grounded Claim Verification & 5D Context-Mismatch Assessment (`T5` Pattern):**
   - Only when `RetrievalState == SEARCH_EXECUTED_WITH_MATCHES` (and only for records where `ai_processing_allowed == True` under WHO Licence `202610792` Clause 6), the backend feeds the admitted `Cancer Info API` structured facts and permitted excerpts into `meta-models/muse-spark-open-1026`.
   - Produces the structured `AtomicClaimVerdict` (`SUPPORTED`, `MIXED_OR_CONTEXT_DEPENDENT`, `CONTRADICTED`, or `INSUFFICIENT_EVIDENCE`) and the **5D Context-Mismatch comparison** (`cancer_and_subtype`, `population_and_stage`, `study_design`, `endpoint_measured`, `caveat_or_dose`).
   - Backend Stage-4 Verifier (`SG-08`) deterministically checks that every cited `fact_id` / `document_id` and verbatim quote exists in the `Cancer Info API` response for that session before marking the envelope `DISPLAYABLE`.

---

## 4. Reference Python Client Implementation (`backend/app/providers/baseten_client.py`)

```python
import re
import ssl
import certifi
import httpx
from typing import Any, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
FENCE_REGEX = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)

def create_verified_ssl_context() -> ssl.SSLContext:
    """SG-09: Mandatory certifi SSL context for macOS Python."""
    return ssl.create_default_context(cafile=certifi.where())

def purge_pending_tool_prose(
    finish_reason: str | None,
    tool_calls: list[Any] | None,
    content: str | None,
) -> str | None:
    """SG-02 (T4 Fix): Never expose or retain assistant prose when tool_calls are pending."""
    if finish_reason == "tool_calls" or (tool_calls and len(tool_calls) > 0):
        return None
    return content

def clean_and_validate_json(raw_content: str | None, schema_cls: type[T]) -> T:
    """SG-04 & SG-07 (T1/T5 Fix): Reject null content and strip Markdown code fences."""
    if not raw_content or not raw_content.strip():
        raise ValueError("Empty message.content returned by Baseten model (SG-04).")
    cleaned = FENCE_REGEX.sub("", raw_content.strip()).strip()
    return schema_cls.model_validate_json(cleaned)
```
