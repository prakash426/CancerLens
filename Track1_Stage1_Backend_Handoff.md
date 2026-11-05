# Track 1 (Stage 1) Backend Build Plan & Instructions

- **Target:** Track 1 Stage 1 backend build
- **Date Prepared:** October 31, 2026 (`America/Chicago`)
- **Scope:** `backend/` — **Stage 1: Shared Wire Contracts, Local Operational SQLite (`cancerlens_app.db`), Single Live `CancerInfoAPIClient`, Baseten Claim Verification Client (`meta-models/muse-spark-open-1026`), Meta Learn Synthesis Client (`muse-spark-1.3`), and FastAPI Core Orchestrator (`SG-01`–`SG-10`)**
- **Downstream Handoffs Produced by This Stage:**
  - **`HO-1` (Stage 1 $\rightarrow$ Stage 2 guards):** Core backend skeleton, schemas, `CancerInfoAPIClient`, and orchestrator hooks where the Stage 2 build will attach clinical/PII/image/SSRF guards, the Stage-4 Deterministic Provenance & Quote Verifier (`SG-08`), and `$0.00` unit tests.
  - **`HO-2` (Stage 1 $\rightarrow$ Stage 3 frontend):** `backend/app/schemas/` + exported `backend/openapi.json` so the frontend build can generate TypeScript types (`frontend/src/types/api.ts`) immediately.
  - **`HO-3` (backend $\rightarrow$ Stage 3 frontend):** FastAPI REST server on `http://127.0.0.1:8000/api/v1/*`.

---

## 1. Context Files for the Stage 1 Build (In Order of Authority)

Attach or provide the following **7 files** from `/Users/prakash/Meta Hackathon/CancerLens/` when starting the Stage 1 build:

1. **`Track1_Stage1_Backend_Handoff.md` (THIS FILE)** — Exact step-by-step build instructions, file tree, schemas, and acceptance gates for Stage 1.
2. **`CancerLens_Consolidated_Implementation_Plan.md`** — Master approved architecture, 3-layer topology (`Cancer Info API` $\rightarrow$ `Meta Model API` + `Baseten Claim Verification Layer`), `SG-01`–`SG-10` safeguards, and stage boundaries.
3. **`DATABASE.md`** — Authoritative specification of `CancerInfoEvidenceItem` and the local operational SQLite 3.45+ `STRICT` tables in `cancerlens_app.db` (zero medical corpus tables).
4. **`ARCHITECTURE.md`** — End-to-end data flow, 6-stage state machine, and WHO Permission Request `202610792` (granted Oct 23, 2026) technical compliance gates.
5. **`SECURITY.md`** — Security requirements, `certifi` TLS enforcement (`SG-09`), API key validation, review-status gates, and credit budget circuit breakers.
6. **`receipts/2026-10-30-baseten-muse-spark-open-eval.md`** — Empirical findings from the live `T1`–`T5` evaluation of `meta-models/muse-spark-open-1026` on `POST https://inference.baseten.co/v1/chat/completions`.
7. **`receipts/2026-10-29-live-meta-text-call.md`** — Verified request/response JSON structure for `muse-spark-1.3` on `POST https://api.meta.ai/v1/responses`.

---

## 2. Hard Non-Negotiable Rules (Read Before Writing Any Code)

1. **NO `FixtureCancerInfoAPIClient` (Single Source of Truth Only):**
   - Do **not** build a `FixtureCancerInfoAPIClient` or mock medical corpus client class in `backend/app/`.
   - There must be **only ONE** `CancerInfoAPIClient` (`backend/app/clients/cancerinfo_client.py`) that makes live HTTP/HTTPS callouts to `CANCER_INFO_API_BASE_URL` (with a 5-minute in-memory `cachetools.TTLCache`).
2. **NO Custom GPU Containers, NO `Truss`, NO Secondary PyTorch Models (`MedCPT` / `DeBERTa`):**
   - Baseten is used **strictly** via its serverless Model API endpoint: `POST https://inference.baseten.co/v1/chat/completions` with `model="meta-models/muse-spark-open-1026"` (`Authorization: Bearer $BASETEN_API_KEY`) to power the **Claim Verification Layer** (`Evaluate` mode + 1-click consistency double-check).
   - Meta Model API is used **strictly** via its serverless Responses endpoint: `POST https://api.meta.ai/v1/responses` with `model="muse-spark-1.3"` (`Authorization: Bearer $META_API_KEY`) to power **Learn Mode** plain-language synthesis and multimodal extraction. Do not hardcode unverified model slugs (such as `muse-wonder`).
3. **NO Medical Corpus Tables in `cancerlens_app.db`:**
   - `Cancer Info API` owns all 25 cancer types (20 common + 5 rare), subtypes, WHO Permission `202610792` / multi-source eligibility gates, structured facts, concise summaries, and allowed verbatim quotes.
   - `cancerlens_app.db` may contain **only** the operational tables defined in `DATABASE.md`: `claim_memory_library`, `claim_memory_fts`, `learned_query_mappings`, `budget_ledger`, and `saved_results`.
   - Both `claim_memory_library` and `learned_query_mappings` must enforce `review_status = 'APPROVED'` before surfacing entries in shared user views or automatically expanding user queries (`TESTING.md` Gate 7).
4. **WHO Licence `202610792` (Clauses 3 & 6) Structural Separation:**
   - Every LLM API call (`Meta Model API` and `Baseten Model API`) **must** set non-retention parameters (`"store": false` on Meta API) so WHO-derived records are never retained for third-party model training.
   - Before sending any `CancerInfoEvidenceItem` to an external LLM, verify `item.ai_processing_allowed is True`.
   - In every response schema (`ResultEnvelope`), **AI-generated plain-language explanations** (`ai_plain_language_summary`, explicitly labeled `"Authored by CancerLens AI"`) must be kept in separate fields from **`Cancer Info API` structured facts** (`structured_fact_or_summary`) and **limited verbatim quotations** (`limited_verbatim_excerpt`), and must preserve `attribution_text`, `canonical_url`, and `permission_reference`.
5. **Enforce All Empirical Safeguards (`SG-01` through `SG-10`):**
   - **`SG-01` (6-Stage Pipeline State Machine):** `INPUT_PARSED` $\rightarrow$ `TOOL_REQUESTED` $\rightarrow$ `TOOL_EXECUTED` $\rightarrow$ `EVIDENCE_VALIDATED` $\rightarrow$ `ASSESSMENT_VALIDATED` $\rightarrow$ `DISPLAYABLE`.
   - **`SG-02` (`T4` Fix — Pending-Tool Prose Purge):** Whenever `finish_reason == "tool_calls"` or `message.tool_calls` is non-empty, **immediately purge/discard `message.content` (`content = None`)** so premature model prose is never returned or logged as a final medical verdict.
   - **`SG-03` (4-State Retrieval Enum):** Distinguish `TOOL_NOT_EXECUTED`, `TOOL_FAILED`, `SEARCH_EXECUTED_NO_MATCHES`, and `SEARCH_EXECUTED_WITH_MATCHES`. Zero matches (`SEARCH_EXECUTED_NO_MATCHES`) must map deterministically to `INSUFFICIENT_EVIDENCE` (`CORPUS_COVERAGE_GAP`), **never** `CONTRADICTED`.
   - **`SG-04` (`T1`/`T2` Fix — Reasoning Starvation Guard):** Pass `reasoning={"effort": "low"}` (Meta API) and `reasoning_effort="low"` (Baseten API) with `max_tokens >= 1024` on all structured JSON turns; explicitly catch `finish_reason == "length"` or empty content when `reasoning_tokens > 0`.
   - **`SG-05` (Non-Additive `reasoning_tokens` Accounting):** In `budget_ledger`, `reasoning_tokens_subset` is already included inside `output_tokens` (`completion_tokens`). **Never** add `reasoning_tokens_subset` on top of `output_tokens` when computing total tokens or cost.
   - **`SG-06` (`T3` Fix — User Focal Lens Mode Lock):** Backend locks `resolved_mode` (`LEARN` vs. `EVALUATE`) from the user's Interactive Focal Lens Switch in the request payload; the LLM cannot silently flip an `EVALUATE` request into `LEARN` or vice versa.
   - **`SG-07` (`T5` Fix — Deterministic Markdown Fence Stripper):** Always run `clean_and_validate_json(raw_text, ModelClass)` to strip ` ```json ... ``` ` wrappers before `ModelClass.model_validate_json()`.
   - **`SG-08` (Deterministic Stage-4 Provenance & Quote Verifier Hook):** Every cited `fact_id` / `document_id` and verbatim quote is mechanically checked in Python against the `Cancer Info API` items retrieved in that request before the envelope reaches `DISPLAYABLE`.
   - **`SG-09` (macOS Python TLS & Key Sanity Guard):** All `httpx.AsyncClient` instances must use `verify=ssl.create_default_context(cafile=certifi.where())` (never `verify=False`). Validate API keys (`len >= 20`, no placeholders like `"echo"`, stripped whitespace) before making live calls.
6. **Spend `$0.00` Credits During Stage 1 Build:**
   - Do not execute unmocked live LLM calls while writing or testing Stage 1 code.

---

## 3. Exact Directory & File Structure for Stage 1

Stay strictly inside `backend/`. Do **not** touch `frontend/`.

```text
backend/
├── pyproject.toml                       # Python 3.12+ dependencies (fastapi, uvicorn, pydantic>=2.9, pydantic-settings, httpx, certifi, cachetools, pytest, pytest-asyncio)
├── .env.example                         # Template for all required env vars
├── openapi.json                         # Generated via scripts/export_openapi.py (Handoff HO-2 to the Stage 3 frontend)
├── scripts/
│   └── export_openapi.py                # Exports FastAPI OpenAPI 3.1 JSON schema without starting server
└── app/
    ├── __init__.py
    ├── main.py                          # FastAPI app factory, CORS for localhost:3000, lifespan SQLite init
    ├── config.py                        # Settings (pydantic-settings), certifi SSL context factory (SG-09), key validator
    ├── schemas/
    │   ├── __init__.py
    │   ├── enums.py                     # PipelineState (SG-01), RetrievalState (SG-03), OutcomeCode, LensMode, InputModality
    │   └── envelope.py                  # CancerInfoEvidenceItem, ContextDimensionComparison, AtomicClaimVerdict, ResultEnvelope, Request models
    ├── db/
    │   ├── __init__.py
    │   └── operational_store.py         # SQLite 3.45+ STRICT init & CRUD for the operational tables + SG-05 budget circuit breaker
    ├── clients/
    │   ├── __init__.py
    │   └── cancerinfo_client.py         # Single live CancerInfoAPIClient (HTTPS + certifi + 5-min TTLCache + SG-03 4-state return)
    ├── providers/
    │   ├── __init__.py
    │   ├── json_utils.py                # SG-07 clean_and_validate_json(), SG-02 purge_pending_tool_prose(), SG-05 token extractor
    │   ├── meta_client.py               # Meta Model API ($150 pool, POST /v1/responses, muse-spark-1.3, store=false)
    │   └── baseten_client.py            # Baseten Claim Verification Layer ($100 pool, POST /v1/chat/completions, meta-models/muse-spark-open-1026)
    ├── investigator/
    │   ├── __init__.py
    │   ├── hooks.py                     # Clean interfaces/default Stage-4 provenance check for the Stage 2 guards & verifiers (HO-1)
    │   ├── learn_pipeline.py            # Deterministic 6-stage Learn Mode pipeline (Meta muse-spark-1.3, SG-01, SG-06, WHO Clause 3/6)
    │   └── evaluate_investigator.py     # Deterministic 6-stage Bounded Claim Verification pipeline (Baseten muse-spark-open-1026, T2-T5 flow)
    └── api/
        ├── __init__.py
        └── routes.py                    # All /api/v1/* endpoints consumed by Frontend (HO-3)
```

---

## 4. Detailed Module-by-Module Implementation Spec

### Module 1: `backend/app/config.py` & `backend/.env.example`
Implement `Settings(BaseSettings)` loading from `.env.local` / `.env`:
- **`Cancer Info API` Connection:**
  - `CANCER_INFO_API_BASE_URL: str = "http://127.0.0.1:8001"` (updated when live URL is provided)
  - `CANCER_INFO_API_KEY: str = ""`
  - `CANCER_INFO_CACHE_TTL_SECONDS: int = 300` (5-minute RAM cache)
- **Meta Model API (`$150` Pool — Verified Oct 29, 2026):**
  - `META_API_BASE_URL: str = "https://api.meta.ai/v1"`
  - `META_API_KEY: str = ""`
  - `META_MODEL_ID: str = "muse-spark-1.3"`
  - `META_BUDGET_CAP_USD: float = 115.00` (leaves `$35.00` reserve for Nov 5–8 judging)
- **Baseten Claim Verification Layer (`$100` Pool — Verified Oct 30, 2026 in `T1`–`T5`):**
  - `BASETEN_API_BASE_URL: str = "https://inference.baseten.co/v1"`
  - `BASETEN_API_KEY: str = ""`
  - `BASETEN_MODEL_ID: str = "meta-models/muse-spark-open-1026"`
  - `BASETEN_BUDGET_CAP_USD: float = 65.00` (leaves `$35.00` reserve for Nov 5–8 judging)
- **Local Operational SQLite:**
  - `OPERATIONAL_DB_PATH: str = "./cancerlens_app.db"`
- **Helper Functions in `config.py` (`SG-09`):**
  - `create_verified_ssl_context() -> ssl.SSLContext`: returns `ssl.create_default_context(cafile=certifi.where())`.
  - `validate_api_key(raw_key: str, provider_name: str) -> str`: strips whitespace/newlines, checks `len >= 20`, rejects placeholder strings (`"echo"`, `"your_key_here"`, `"xxx"`, `"todo"`), or raises a typed `ConfigurationError`.

---

### Module 2: `backend/app/schemas/enums.py` & `backend/app/schemas/envelope.py` (`HO-1` & `HO-2` Priority #1)
**Build this module first and run `scripts/export_openapi.py` immediately so the Track 2 frontend build (`frontend/`) can start.**

1. **`enums.py`:**
   - `LensMode(str, Enum)`: `"LEARN"`, `"EVALUATE"` (`SG-06`)
   - `InputModality(str, Enum)`: `"TEXT"`, `"IMAGE_OCR"`, `"URL_EXTRACT"` (voice input is out of scope per `D11`)
   - `PipelineState(str, Enum)` (`SG-01`):
     - `"INPUT_PARSED"`
     - `"TOOL_REQUESTED"`
     - `"TOOL_EXECUTED"`
     - `"EVIDENCE_VALIDATED"`
     - `"ASSESSMENT_VALIDATED"`
     - `"DISPLAYABLE"`
   - `RetrievalState(str, Enum)` (`SG-03`):
     - `"TOOL_NOT_EXECUTED"`
     - `"TOOL_FAILED"`
     - `"SEARCH_EXECUTED_NO_MATCHES"`
     - `"SEARCH_EXECUTED_WITH_MATCHES"`
   - `OutcomeCode(str, Enum)`:
     - `"SUPPORTED"`
     - `"MIXED_OR_CONTEXT_DEPENDENT"`
     - `"CONTRADICTED"`
     - `"INSUFFICIENT_EVIDENCE"`
     - `"OUT_OF_SCOPE_CLINICAL"`

2. **`envelope.py` (All Models use `ConfigDict(extra="forbid")` and `snake_case` field names):**
   - `CancerInfoEvidenceItem`: Exact fields from Section 2 of `DATABASE.md` (`fact_id`, `document_id`, `source_id`, `origin_source_id`, `organization_name`, `permission_reference`, `source_title`, `canonical_url`, `cancer_id`, `subtype_id`, `category_slug`, `structured_fact_or_summary`, `limited_verbatim_excerpt`, `study_design_scope`, `population_scope`, `jurisdiction_code`, `observed_source_date`, `retrieved_at_utc`, `reviewed_at_date`, `attribution_text`, `ai_processing_allowed`).
   - `ContextDimensionComparison`:
     - `dimension_name: Literal["cancer_and_subtype", "population_and_stage", "study_design", "endpoint_measured", "caveat_or_dose"]`
     - `claim_assumes: str`
     - `evidence_actually_shows: str`
     - `is_mismatch: bool`
   - `AtomicClaimVerdict`:
     - `subclaim_id: str`
     - `atomic_claim_text: str`
     - `outcome_code: OutcomeCode`
     - `outcome_label: str`
     - `ai_plain_language_explanation: str` (WHO Clause 6: AI-authored explanation, distinct from source facts)
     - `context_comparisons_5d: list[ContextDimensionComparison]` (the 5D Context-Mismatch Matrix)
     - `cited_fact_ids: list[str]`
     - `cited_document_ids: list[str]`
     - `verbatim_quote_verified: bool = False`
     - `stage4_downgraded: bool = False`
     - `stage4_downgrade_reason: str | None = None`
     - `pivot_to_learn_cancer_id: str | None = None` (enables the Frontend "Pivot-in-Place" bridge back to Learn Lens)
     - `pivot_to_learn_category_slug: str | None = None`
   - `LearnCategoryCard`:
     - `category_slug: str`
     - `category_title: str`
     - `coverage_status: Literal["COVERED", "PARTIAL", "COVERAGE_GAP"]`
     - `ai_plain_language_explanation: str`
     - `cited_fact_ids: list[str]`
     - `common_public_claims: list[str] = []` (Mechanism B chips that pivot into Evaluate Lens when clicked)
   - `RelatedReviewedClaimItem`:
     - `claim_memory_id: str`
     - `canonical_claim_text: str`
     - `primary_outcome_code: OutcomeCode`
     - `outcome_label: str`
     - `nuance_warning_note: str`
     - `how_this_differs_note: str`
   - `ComplianceAndAttributionBanner`:
     - `ai_author_label: str = "AI-Generated Plain-Language Summary — Authored by CancerLens AI"`
     - `medical_boundary_disclaimer: str = "CancerLens provides general educational information and evidence analysis, not personal medical diagnosis or treatment advice."`
     - `who_non_endorsement_notice: str = "Source materials used under permission (including WHO Licence 202610792 where applicable). Independently developed; not published, endorsed, or sponsored by the World Health Organization."`
   - `TelemetrySnapshot`:
     - `request_id: str`
     - `pipeline_state: PipelineState`
     - `retrieval_state: RetrievalState`
     - `primary_provider: str`
     - `primary_model: str`
     - `total_latency_ms: int`
     - `hops_executed: int`
     - `learned_query_mapping_applied: str | None = None`
     - `meta_pool_spent_usd: float`
     - `meta_pool_remaining_usd: float`
     - `baseten_pool_spent_usd: float`
     - `baseten_pool_remaining_usd: float`
   - `ResultEnvelope`:
     - `request_id: str`
     - `resolved_mode: LensMode` (`SG-06`)
     - `pipeline_state: PipelineState` (`SG-01`)
     - `retrieval_state: RetrievalState` (`SG-03`)
     - `interpreted_query_or_claim: str`
     - `cancer_id: str | None = None`
     - `cancer_name: str | None = None`
     - `subtype_id: str | None = None`
     - `category_slug: str | None = None`
     - `overall_outcome_code: OutcomeCode`
     - `overall_outcome_label: str`
     - `ai_plain_language_summary: str` (strictly separated from `evidence_items` per WHO Clause 6)
     - `learn_category_cards: list[LearnCategoryCard] = []` (populated when `resolved_mode == "LEARN"`)
     - `atomic_claim_verdicts: list[AtomicClaimVerdict] = []` (populated when `resolved_mode == "EVALUATE"`)
     - `evidence_items: list[CancerInfoEvidenceItem] = []` (populated from `Cancer Info API` for the right-hand Sticky Provenance Inspector)
     - `related_reviewed_claims: list[RelatedReviewedClaimItem] = []`
     - `limitations_and_gaps_note: str`
     - `compliance_banner: ComplianceAndAttributionBanner`
     - `telemetry: TelemetrySnapshot`
   - **Request Models (`LearnRequest`, `EvaluateRequest`, `ConsistencyDoubleCheckRequest`, `ExtractionResponse`):**
     - `LearnRequest`: `cancer_id: str`, `subtype_id: str | None = None`, `category_slug: str | None = None`, `user_question: str | None = None`, `resolved_mode: Literal[LensMode.LEARN] = LensMode.LEARN`
     - `EvaluateRequest`: `claim_text: str`, `source_modality: InputModality = InputModality.TEXT`, `user_confirmed_extraction: bool = True`, `cancer_id_hint: str | None = None`, `subtype_id_hint: str | None = None`, `resolved_mode: Literal[LensMode.EVALUATE] = LensMode.EVALUATE`
     - `ConsistencyDoubleCheckRequest`: `request_id: str`, `claim_text: str`, `cited_fact_ids: list[str]`, `primary_outcome_code: OutcomeCode`

---

### Module 3: `backend/app/db/operational_store.py` (Local Operational SQLite)
- Initialize `cancerlens_app.db` using the exact SQLite 3.45+ `STRICT` DDL from Section 3 of `DATABASE.md`:
  1. `claim_memory_library` + `claim_memory_fts` (including `review_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW'`)
  2. `learned_query_mappings` (including `review_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW'`)
  3. `budget_ledger` (enforcing `SG-05` non-additive `reasoning_tokens_subset`, `provider_name IN ('meta_model_api', 'baseten_model_api')`)
  4. `saved_results` (private-by-default capability-token snapshots)
- Provide clean helper methods:
  - `record_budget_entry(...)` & `get_pool_totals() -> dict` (checks `$115.00` Meta / `$65.00` Baseten circuit breakers before any live LLM call)
  - `lookup_approved_query_mapping(lay_phrase: str)` (queries only `WHERE review_status = 'APPROVED'`) & `record_candidate_query_mapping(...)`
  - `search_approved_similar_claims_fts(query_text: str, cancer_id: str | None, limit: int = 3)` (queries only `WHERE review_status = 'APPROVED'`) & `record_candidate_claim_memory(...)`
  - `create_saved_result(...)`, `get_saved_result_by_token(...)`, `delete_saved_result(...)`

---

### Module 4: `backend/app/clients/cancerinfo_client.py` (Single Live `CancerInfoAPIClient`)
- **Zero Fake/Fixture Client Classes.** Build a single `CancerInfoAPIClient` class.
- Uses `httpx.AsyncClient(base_url=settings.CANCER_INFO_API_BASE_URL, verify=create_verified_ssl_context(), timeout=15.0)`.
- Sends `Authorization: Bearer <CANCER_INFO_API_KEY>` (and `X-API-Key` header if configured).
- Uses an in-memory `cachetools.TTLCache(maxsize=256, ttl=settings.CANCER_INFO_CACHE_TTL_SECONDS)` keyed by `(endpoint, normalized_params)` for non-restricted read calls.
- Exposes async methods:
  1. `list_cancers() -> list[dict]`: fetches the 25-cancer taxonomy (20 common + 5 rare, subtypes, and 11 category coverage statuses) from `Cancer Info API`.
  2. `search_evidence(query: str, cancer_id: str | None = None, subtype_id: str | None = None, category_slug: str | None = None, limit: int = 12) -> tuple[RetrievalState, list[CancerInfoEvidenceItem]]`:
     - Maps HTTP/connection errors to `(RetrievalState.TOOL_FAILED, [])` (`SG-03`).
     - Maps empty `200 OK` results to `(RetrievalState.SEARCH_EXECUTED_NO_MATCHES, [])` (`SG-03`).
     - Maps non-empty `200 OK` results to `(RetrievalState.SEARCH_EXECUTED_WITH_MATCHES, items)` (`SG-03`).
  3. `get_facts_by_ids(fact_ids: list[str]) -> list[CancerInfoEvidenceItem]`: fetches specific facts by ID for Stage-4 provenance verification and consistency double-checks.

---

### Module 5: `backend/app/providers/` (`json_utils.py`, `meta_client.py`, `baseten_client.py`)
1. **`json_utils.py` (`SG-02`, `SG-05` & `SG-07`):**
   - `purge_pending_tool_prose(finish_reason: str | None, tool_calls: list | None, content: str | None) -> str | None`:
     - **Enforces `SG-02` (`T4` Critical Fix):** If `finish_reason == "tool_calls"` or `bool(tool_calls)` is True, immediately return `None` (discarding any premature prose in `content`).
   - `clean_and_validate_json(raw_text: str | None, schema_cls: type[T]) -> T`:
     - **Enforces `SG-04` & `SG-07` (`T1`/`T5` Fix):** Rejects `None`/empty strings and strips leading/trailing whitespace and Markdown code fences (` ```json ... ``` ` or ` ``` ... ``` `) before calling `schema_cls.model_validate_json(cleaned)`.
   - `extract_non_additive_usage(usage_dict: dict | None) -> tuple[int, int, int]`:
     - **Enforces `SG-05`:** Extracts `(input_tokens, output_tokens, reasoning_tokens_subset)` from either Meta API (`input_tokens`, `output_tokens`, `output_tokens_details.reasoning_tokens`) or Baseten API (`prompt_tokens`, `completion_tokens`, `completion_tokens_details.reasoning_tokens`) without ever adding `reasoning_tokens` on top of `output_tokens`.
2. **`meta_client.py` (`MetaMuseClient` — `$150` Pool, Verified in `receipts/2026-10-29-live-meta-text-call.md`):**
   - Calls `POST {META_API_BASE_URL}/responses` with `model=settings.META_MODEL_ID` (`"muse-spark-1.3"`).
   - Always includes `"store": False` (WHO Clause 6) and `"reasoning": {"effort": "low"}` (`SG-04`).
   - Parses the verified `/v1/responses` response format: iterates `body["output"]` for items with `type == "message"` and extracts text from `content[]` where `type == "output_text"`.
   - Checks `operational_store.get_pool_totals()` before calling (`$115.00` circuit breaker) and logs every call to `budget_ledger` (`provider_name="meta_model_api"`).
3. **`baseten_client.py` (`BasetenClaimVerifierClient` — `$100` Pool, Verified in `receipts/2026-10-30-baseten-muse-spark-open-eval.md`):**
   - Calls `POST {BASETEN_API_BASE_URL}/chat/completions` (`https://inference.baseten.co/v1/chat/completions`) with `Authorization: Bearer {settings.BASETEN_API_KEY}` and `model=settings.BASETEN_MODEL_ID` (`"meta-models/muse-spark-open-1026"`).
   - Always passes `"reasoning_effort": "low"` and `"max_tokens": 1024` (`2048` for multi-claim verification) (`SG-04`).
   - Rejects any response where `choice["finish_reason"] == "length"` (`SG-04` `T1` fix).
   - Immediately calls `purge_pending_tool_prose(...)` (`SG-02` `T4` fix) on every response so `message.content` is wiped to `None` whenever `finish_reason == "tool_calls"` or `tool_calls` is non-empty.
   - Provides three clean methods for the Claim Verification Layer:
     1. `normalize_and_split_claims(user_claim_text: str) -> NormalizedClaimsOutput` (`T2`/`T3` pattern using `response_format={"type": "json_schema", ...}` + `clean_and_validate_json`).
     2. `plan_evidence_search_tool_call(claims: list[str], cancer_topic: str, hop_index: int)` (`T4` pattern using `tools=[search_admitted_evidence_schema]` + `SG-02` prose purge).
     3. `verify_claims_against_evidence(claims: list[str], retrieval_state: RetrievalState, admitted_items: list[CancerInfoEvidenceItem])` (`T5` pattern producing grounded `AtomicClaimVerdict` items and 5D context comparisons + `clean_and_validate_json`).

---

### Module 6: `backend/app/investigator/` (`hooks.py`, `learn_pipeline.py`, `evaluate_investigator.py`)
1. **`hooks.py` (`HO-1` Interface for Stage 2 guards):**
   - Define clean hooks for Stage 2 to expand (`backend/app/guards/` and `backend/app/verifiers/stage4_verifier.py`), including a working default Stage-4 provenance/quote verifier (`SG-08`):
     - `check_clinical_boundary(text: str) -> tuple[bool, str | None]`
     - `sanitize_pii(text: str) -> str`
     - `run_stage4_verifier(envelope: ResultEnvelope, retrieved_items: list[CancerInfoEvidenceItem]) -> ResultEnvelope`: verifies every `cited_fact_id` and `cited_document_id` against `retrieved_items` and checks any verbatim quote against `limited_verbatim_excerpt`.
2. **`learn_pipeline.py` (`run_learn_pipeline`):**
   - Locks `resolved_mode = LensMode.LEARN` (`SG-06`).
   - Advances through `PipelineState` (`INPUT_PARSED` $\rightarrow$ `TOOL_REQUESTED` $\rightarrow$ `TOOL_EXECUTED` $\rightarrow$ `EVIDENCE_VALIDATED` $\rightarrow$ `ASSESSMENT_VALIDATED` $\rightarrow$ `DISPLAYABLE`) (`SG-01`).
   - Checks `lookup_approved_query_mapping` (Mechanism A) before calling `CancerInfoAPIClient.search_evidence()`.
   - Handles `RetrievalState.SEARCH_EXECUTED_NO_MATCHES` (`SG-03`) by returning a deterministic `INSUFFICIENT_EVIDENCE` (`CORPUS_COVERAGE_GAP`) envelope without calling an LLM to guess medical facts.
   - Uses `MetaMuseClient` (`muse-spark-1.3`, `store=False`) on items where `ai_processing_allowed == True` to synthesize `LearnCategoryCard` items and `ai_plain_language_summary` strictly separated from `evidence_items` (WHO Clause 6).
3. **`evaluate_investigator.py` (`run_evaluate_investigator`):**
   - Locks `resolved_mode = LensMode.EVALUATE` (`SG-06`).
   - Requires `user_confirmed_extraction == True` when `source_modality != InputModality.TEXT` (`SG-01`).
   - **Step 1 (`INPUT_PARSED`):** Calls `BasetenClaimVerifierClient.normalize_and_split_claims()` (`meta-models/muse-spark-open-1026`, `T2`/`T3`) to decompose the input into `1–5` atomic sub-claims.
   - **Step 2 (`TOOL_REQUESTED` $\rightarrow$ `TOOL_EXECUTED`):** Executes bounded evidence retrieval (`max 3 hops` against `CancerInfoAPIClient.search_evidence()`, enforcing `SG-02` pending-tool prose purge on any `tool_calls` turn).
   - **Step 3 (`EVIDENCE_VALIDATED`):** Calls `BasetenClaimVerifierClient.verify_claims_against_evidence()` (`meta-models/muse-spark-open-1026`, `T5`) over items with `ai_processing_allowed == True` to generate `AtomicClaimVerdict` with the **5D Context-Mismatch Matrix** (`cancer_and_subtype`, `population_and_stage`, `study_design`, `endpoint_measured`, `caveat_or_dose`).
   - **Step 4 (`ASSESSMENT_VALIDATED` $\rightarrow$ `DISPLAYABLE`):** Runs `run_stage4_verifier` (`SG-08`) to verify every cited `fact_id` / `document_id` and verbatim quote before returning the `ResultEnvelope`.

---

### Module 7: `backend/app/api/routes.py` & `backend/app/main.py` (`HO-3`)
Expose the following FastAPI endpoints under `/api/v1` with CORS enabled for `http://localhost:3000`:
1. `GET /api/v1/cancers` $\rightarrow$ Proxies live 25-cancer & subtype catalog from `CancerInfoAPIClient.list_cancers()`.
2. `POST /api/v1/learn` (`LearnRequest` $\rightarrow$ `ResultEnvelope`)
3. `POST /api/v1/evaluate` (`EvaluateRequest` $\rightarrow$ `ResultEnvelope`)
4. `POST /api/v1/evaluate/double-check` (`ConsistencyDoubleCheckRequest` $\rightarrow$ runs 1-click consistency verification check)
5. `POST /api/v1/extract/image`, `POST /api/v1/extract/url` $\rightarrow$ Returns `ExtractionResponse` (`extracted_text`, `requires_user_confirmation=True`, `modality`, `warnings`) so the Frontend Inline Confirmation Drawer can display editable text before evaluation (voice input is out of scope per `D11`).
6. `POST /api/v1/saved-results`, `GET /api/v1/saved-results/{saved_result_id}`, `DELETE /api/v1/saved-results/{saved_result_id}`
7. `GET /api/v1/health/budget` $\rightarrow$ Returns live Dual-Pool credit telemetry (`$150` Meta pool + `$100` Baseten pool) and circuit-breaker status from `budget_ledger`.

---

## 5. Stage 1 Completion & Verification Checklist (`$0.00` Credit Spend)

Before handing off `HO-1` to Stage 2 and `HO-2` to the frontend build, verify:
1. `python -m backend.scripts.export_openapi` generates `backend/openapi.json` cleanly with zero Pydantic schema errors.
2. `cancerlens_app.db` initializes cleanly on startup with **only** the operational tables (`claim_memory_library`, `claim_memory_fts`, `learned_query_mappings`, `budget_ledger`, `saved_results`) and **zero** medical corpus tables.
3. There is **no** `FixtureCancerInfoAPIClient` and **no** custom GPU / Truss / `MedCPT` / `DeBERTa` code anywhere in `backend/`.
4. Offline unit smoke check (mocked HTTP transport, `$0.00` spend) confirms:
   - `SG-02`: `purge_pending_tool_prose("tool_calls", [{"id": "1"}], "Premature verdict")` returns `None`.
   - `SG-03`: Empty `Cancer Info API` search returns `RetrievalState.SEARCH_EXECUTED_NO_MATCHES` and `OutcomeCode.INSUFFICIENT_EVIDENCE` (never `CONTRADICTED`).
   - `SG-04`: `finish_reason == "length"` or null `content` raises `IncompleteGenerationError`.
   - `SG-05`: `budget_ledger` does not add `reasoning_tokens_subset` on top of `output_tokens`.
   - `SG-06`: `LearnRequest` always produces `resolved_mode == "LEARN"` and `EvaluateRequest` always produces `resolved_mode == "EVALUATE"`.
   - `SG-07`: `clean_and_validate_json` parses ` ```json\n{...}\n``` ` into Pydantic models without raising `ValidationError`.
   - `SG-08`: Stage-4 verifier downgrades any verdict citing an unknown `fact_id` to `OutcomeCode.INSUFFICIENT_EVIDENCE`.
