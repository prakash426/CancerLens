# CancerLens — Engineering Conventions & Code Style Specification (`CODE_STYLE.md`)

- **Document Status:** `PROPOSED` (Specification Baseline — No Application Code Implemented Yet)
- **Date:** October 27, 2026 (`America/Chicago`)
- **Authoring:** CancerLens team
- **Cross-References:** `ARCHITECTURE.md`, `DATABASE.md`, `SECURITY.md`, `TESTING.md`

---

## 1. Purpose & Guiding Principles

### 1.1 Purpose
`CODE_STYLE.md` establishes practical, high-leverage engineering conventions for a solo developer building **CancerLens** across an 8-day hackathon window with AI coding collaborators.

### 1.2 Core Engineering Tenets (`PROPOSED`)
1. **Enforce Domain Invariants in Types and SQL, Never in Prompt Prose Alone:**
   - Rights gates (`admission_status == 'ADMITTED'`), nullable observed dates (`observed_source_date: date | None`), non-binary verdict enums (`OutcomeCode`), and `$150` budget caps are enforced by Pydantic `extra="forbid"` schemas and SQLite `STRICT` constraints.
2. **One Provider Abstraction for All Meta Inference:**
   - Application services never call `httpx.post` or provider SDKs directly. All model calls route through a single budget-aware, timeout-bounded `MetaModelClient` interface.
3. **Zero Silent Fallbacks or Faked Live Calls:**
   - If a live Meta API call fails, raise a typed `ProviderUnavailableError` or explicitly mark the response `is_recorded_fallback = True` in the UI banner—never silently substitute a non-Meta model or fabricate citations.

---

## 2. Languages & Runtime Versions (`PROPOSED`)

- **Backend & Ingestion:** **Python `3.12+`** (using `uv` or `pip-tools` for deterministic lockfiles).
- **Database:** **SQLite `3.45+`** (`STRICT` tables + `FTS5` virtual tables + `WAL` mode).
- **Frontend:** **TypeScript `5.6+`** with **Next.js `15`** (App Router) and **Tailwind CSS `3.4+`** *(or HTMX + Jinja2 if the `DEC-02` single-process fallback is triggered)*.

---

## 3. Repository Folder Layout (`PROPOSED`)

```text
CancerLens/
├── README.md                          # Project overview, setup, and live verification guide
├── DISCLOSURE.md                      # Explicit separation of Oct 15-16 research audit vs. Oct 27-Nov 4 code
├── PRD.md                             # Product Requirements Document & Roadmap
├── DESIGN_SYSTEM.md                   # UX, Accessibility & Visual Token Specification
├── ARCHITECTURE.md                    # System, Multi-Model & $150 Budget Specification
├── DATABASE.md                        # SQLite + FTS5 Schema & Rights Provenance Specification
├── SECURITY.md                        # Threat Model, SSRF, Upload & Boundary Specification
├── CODE_STYLE.md                      # Engineering Conventions & Review Rules (this file)
├── TESTING.md                         # Test Matrix, Gold Fixtures & Baseline Comparison Plan
├── .env.example                       # Committed template with dummy placeholders (NO SECRETS)
├── .gitignore                         # Ignores .env*, *.db-wal, __pycache__, node_modules/
├── backend/
│   ├── pyproject.toml                 # Pinned dependencies, ruff, mypy, pytest config
│   ├── uv.lock                        # Deterministic lockfile
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory, CORS, rate-limit & budget middleware
│   │   ├── config.py                  # pydantic-settings Settings & MODEL_REGISTRY
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── routes_learn.py    # GET /cancers, POST /learn, GET /statistics/{cancer_id}
│   │   │       ├── routes_evaluate.py # POST /evaluate, POST /extract/image, POST /extract/url
│   │   │       └── routes_saved.py    # GET /saved/{id}, POST /saved/{id}/refresh, GET /health/budget
│   │   ├── schemas/
│   │   │   ├── envelope.py            # ResultEnvelope, ClaimAssessment, EvidencePassage, ModelTrace
│   │   │   └── enums.py               # OutcomeCode, CoverageStatus, ResolvedMode, AdmissionStatus
│   │   ├── providers/
│   │   │   ├── base.py                # MetaModelClient Protocol & BudgetLedgerRecorder
│   │   │   └── meta_api.py            # Official Meta Model API adapter (Muse Spark / Wonder / Voice / SAM 3.1)
│   │   ├── guards/
│   │   │   ├── clinical_boundary.py   # Personal medical advice & clinical lesion refusal guard
│   │   │   ├── pii_sanitizer.py       # Strips PII & generalizes canonical claims before library indexing
│   │   │   ├── ssrf_url_guard.py      # DNS pinning, private IP block, redirect & byte cap
│   │   │   └── image_upload_guard.py  # Magic-byte check, 5MB limit, 4096x4096 bomb guard, EXIF strip
│   │   ├── memory/
│   │   │   ├── claim_memory_repo.py   # FR-14 Similar Claims FTS5 search, Exact Cache & Consistency Check
│   │   │   └── experience_learner.py  # FR-19 Mechanism A (Search/Synonym Learning) & Mechanism B Enrichment
│   │   ├── retrieval/
│   │   │   ├── repository.py          # Read-only queries strictly via v_admitted_passages
│   │   │   └── hybrid_reranker.py     # Optional local NumPy cosine reranker (if enabled by M4)
│   │   ├── investigator/
│   │   │   ├── learn_pipeline.py      # 1-hop deterministic category & Q&A synthesizer + Mechanism B
│   │   │   └── claim_investigator.py  # Bounded <= 3-hop claim decomposer & mismatch evaluator
│   │   └── verifiers/
│   │       └── citation_verifier.py   # Deterministic passage_id existence & substring quote check
│   └── scripts/
│       ├── verify_meta_models.py      # M2 live authenticated smoke test & receipt generator
│       ├── ingest_admitted_corpus.py  # M3 deterministic NCI/CDC/AIHW/StatCan fetcher & SHA-256 hasher
│       └── run_benchmark.py           # M6 Baseline RAG vs. Adaptive Investigator comparison script
├── data/
│   ├── migrations/
│   │   └── 001_initial_schema.sql     # Exact DDL from DATABASE.md
│   └── seeds/
│       ├── source_registry.json       # Admitted P1 vs Quarantined source rows
│       ├── cancer_taxonomy.json       # 26 cancers + subtype trees + 338 section coverage statuses
│       └── initial_claim_memory.json  # 20 reviewed initial claims seeded into claim_memory_library
├── frontend/
│   ├── package.json
│   ├── tsconfig.json                  # strict: true, noImplicitAny: true
│   └── src/
│       ├── app/                       # Next.js App Router pages
│       ├── components/                # ModeTabs, SplitWorkspace, VerdictCard, QuoteInspector
│       └── lib/                       # Typed API client matching ResultEnvelope
└── tests/
    ├── conftest.py                    # In-memory SQLite fixtures & deterministic FakeMetaClient
    ├── fixtures/
    │   └── gold_cases.json            # Permitted NCI/CDC passage fixtures & expected outcomes
    ├── unit/                          # Verifier, SSRF, upload guard, date & rights unit tests
    ├── integration/                   # Learn, Evaluate, Snapshot & Budget ledger API tests
    └── live_smoke/                    # @pytest.mark.live_smoke real Meta API connectivity tests
```

---

## 4. Naming, Type Safety & Schema Conventions (`PROPOSED`)

### 4.1 Naming Conventions
- **Python:** `snake_case` for functions, variables, modules, and database columns; `PascalCase` for Pydantic models, classes, and enums; `UPPER_SNAKE_CASE` for module constants.
- **TypeScript / React:** `PascalCase` for React components (`VerdictBadge.tsx`, `SourcePassageCard.tsx`) and types/interfaces; `camelCase` for functions and local variables; JSON wire payloads keep `snake_case` to match `ResultEnvelope` without error-prone key-remapping middleware.
- **Requirement & Test Traceability Tags:** Include the requirement or test ID in module docstrings (e.g., `"""Enforces FR-07 and SEC-04 deterministic substring verification."""`).

### 4.2 Strict Type Safety Rules
- **Python (`mypy --strict` & Pydantic v2):**
  - Every function signature must have explicit parameter and return type annotations.
  - All Pydantic request/response models must inherit from a base class setting `model_config = ConfigDict(extra="forbid", frozen=True, strict=True)`.
  - Never pass untyped `dict[str, Any]` across module boundaries.
- **Date & Provenance Types:**
  - `observed_source_date: datetime.date | None` (explicitly `None` when not present on the source page; never defaulted to `datetime.date.today()`).
  - `retrieved_at_utc: datetime.datetime` (always timezone-aware `datetime.UTC`).

---

## 5. Provider-Client Abstraction & Budget Middleware (`PROPOSED`)

To prevent vendor lock-in or scattered API logic, all Meta Model API and Baseten calls implement a single typed protocol in `backend/app/providers/base.py`:

```python
from dataclasses import dataclass
from typing import Protocol, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

@dataclass(frozen=True)
class ModelCallTelemetry:
    provider_name: str          # "meta_model_api" | "baseten"
    model_id: str               # Resolved from MODEL_REGISTRY
    stage_name: str             # e.g., "DECOMPOSE_AND_INVESTIGATE"
    latency_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    provider_request_id: str    # Redacted/safe request identifier

class MetaModelClient(Protocol):
    async def generate_structured(
        self,
        *,
        stage_name: str,
        role_key: str,
        system_prompt: str,
        user_content: str,
        response_model: type[T],
        timeout_sec: float = 8.0,
    ) -> tuple[T, ModelCallTelemetry]:
        """Executes a budget-checked, timeout-bounded call and records to budget_ledger."""
        ...
```

### 5.1 Mandatory Provider Call Rules
1. **Pre-Call Budget Gate:** Before opening an HTTP connection, `MetaModelClient` checks `budget_ledger.get_total_spend_usd()`. If spend exceeds the configured threshold (`$115.00` pre-submission hard cap), it raises `BudgetExhaustedError` immediately.
2. **Bounded Retries & Timeouts:** Every call enforces an explicit `httpx.Timeout(connect=2.0, read=timeout_sec)` and retries **at most once** (`max_retries = 1`) only on transient `429`/`502`/`503` errors.
3. **Post-Call Ledger Write:** Every completed call writes a row to `budget_ledger` in the same request lifecycle and appends `ModelCallTelemetry` to `ResultEnvelope.model_trace`.

---

## 6. Error Handling, Logging & Redaction (`PROPOSED`)

1. **Structured Domain Exceptions:**
   - Raise specific domain exceptions (`SSRFBlockedError`, `UnsupportedMediaError`, `ClinicalBoundaryRefusalError`, `BudgetExhaustedError`, `CitationVerificationError`) mapped to clean RFC 7807 / structured JSON error responses in `main.py`.
2. **PII & Secret Redaction in Logs:**
   - Use structured JSON logging (`structlog` or standard `logging` with a JSON formatter).
   - Never log raw uploaded image base64 strings, `Authorization` headers, or unredacted user query strings containing email/phone/MRN patterns (`SEC-05`).

---

## 7. Formatting, Linting & Dependency Pinning (`PROPOSED`)

- **Python Linting & Formatting:**
  - `ruff check .` (rules: `E`, `F`, `I`, `B`, `UP`, `S` bandit security subset, `ASYNC`) + `ruff format --check .` + `mypy app tests`.
- **Frontend Linting & Typecheck:**
  - `npm run lint` (`eslint`) + `npx tsc --noEmit`.
- **Dependency Pinning:**
  - Pin exact versions in `backend/pyproject.toml` + `uv.lock` (or `requirements.txt` with hashes) and `frontend/package-lock.json` so builds on Nov 3–4 cannot break due to upstream package releases.

---

## 8. Git Workflow, Baseline Tagging & AI-Generated Code Review (`PROPOSED`)

### 8.1 Git & Event Disclosure Workflow
1. **Baseline Commit Tag:** Tag the initial specification commit on October 27, 2026 as `v0.1.0-planning-baseline`.
2. **Atomic Milestone Branches / Commits:** Use clear prefixes matching the roadmap (`feat(M2): verify live Meta API client and budget ledger`, `feat(M3): ingest admitted NCI P1 passages with SHA256 hashes`, `security(M8): add DNS-pinning SSRF guard`).
3. **Pre-Push Gate:** Run `pytest -m "not live_smoke"` and secret check before every `git push origin main`.

### 8.2 Mandatory Review Checklist for AI-Generated Code
Every file generated or modified with AI assistance must pass these 6 human/architect checks before merge:
1. **No Bypassed Rights Gate:** Does any SQL query read from `evidence_passages` or `source_documents` directly instead of `v_admitted_passages`? *(If yes -> reject).*
2. **No Fabricated Dates:** Does any adapter or model fallback set `observed_source_date = datetime.now()` when a date is missing? *(If yes -> reject; must remain `None`).*
3. **No Unbounded Loops or Retries:** Does any `while` loop or retry decorator lack a hard integer ceiling (`max_hops <= 3`, `max_retries <= 1`)? *(If yes -> reject).*
4. **No Binary Verdict Drift:** Did the AI assistant introduce a `boolean` `is_true` field or a `confidence_percent` float in `ClaimAssessment`? *(If yes -> reject; use `OutcomeCode` enum only).*
5. **No Silent Non-Meta Runtime Model:** Did any code path import `google.generativeai`, `openai` (pointing to GPT), or `anthropic` for runtime inference? *(If yes -> reject; runtime inference must use `MetaModelClient` pointing to Meta Model API / Baseten).*
6. **Documentation Integrity:** Preserve all existing comments, docstrings, and legal attribution notices unless intentionally updating them for accuracy.
