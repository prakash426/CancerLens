# CancerLens — Local Application State & `Cancer Info API` Data Contract (`DATABASE.md`)

- **Date:** November 2, 2026 (`America/Chicago`)
- **Status:** Authoritative Specification (Zero Duplicate Medical Corpus DB; Live `https://cancerinfo-api.onrender.com/` Integration + Lightweight Local Operational SQLite Store)

---

## 1. Core Architectural Rule: No Duplicate Medical Corpus Database

1. **`Cancer Info API` Owns All Medical Content & Rights Gates:**
   - All cancer taxonomy records (20 common + 5 rare cancers and their subtypes), source registries, **WHO Licence `202610792`** and multi-source document eligibility gates, structured category facts, concise summaries, consensus facts, limited attributed quotations, and epidemiological statistics live inside **`Cancer Info API`** (live at `https://cancerinfo-api.onrender.com/`).
2. **What `CancerLens` Stores Locally (`cancerlens_app.db` + Ephemeral RAM Cache):**
   - **CancerLens never persists a duplicate copy of WHO or `Cancer Info API` medical documents on disk.**
   - CancerLens keeps an **ephemeral in-memory TTL cache (`cachetools.TTLCache`, 5-minute TTL)** for non-restricted `Cancer Info API` responses during active sessions.
   - CancerLens's local SQLite 3.45+ file (`cancerlens_app.db`) stores **only** application-specific operational metadata:
     1. `claim_memory_library` & `claim_memory_fts` (PII-scrubbed canonical claims, verdict codes, nuance warnings, `Cancer Info API` citation IDs, and `review_status` so only reviewed/approved claims are surfaced to users).
     2. `learned_query_mappings` (verified lay-phrase-to-medical-search expansions for Mechanism A, gated by `review_status`).
     3. `saved_results` (private-by-default capability-token snapshots, invalidated if a cited document is revoked in `Cancer Info API`).
     4. `budget_ledger` (dual-pool serverless token telemetry for the `$150` Meta Model API pool and `$100` Baseten Model API pool).
     5. `link_verification_cache` (24h TTL verdicts on upstream `canonical_url` aliveness, so dead outbound links render unlinked instead of 404ing).

---

## 2. `Cancer Info API` Response Contract Consumed by `CancerLens`

`CancerInfoAPIClient` (`backend/app/clients/cancerinfo_client.py`) consumes the protected `Cancer Info API` endpoints and maps each returned evidence item to a strict Pydantic model:

```python
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

class CancerInfoEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str                        # Stable ID from Cancer Info API
    document_id: str                    # Originating source document ID
    source_id: str                      # Delivery source ID (e.g., WHO, NCI)
    origin_source_id: str               # Upstream producer ID (prevents double-counting consensus)
    organization_name: str              # e.g., "World Health Organization (WHO)", "National Cancer Institute (NCI)"
    permission_reference: str | None    # e.g., "WHO Licence 202610792" or "NCI Public Reuse Policy"
    source_title: str
    canonical_url: str                  # Direct original URL (required by WHO Clause 3/6)
    cancer_id: str
    subtype_id: str | None
    category_slug: str
    structured_fact_or_summary: str     # Concise structured factual statement / summary
    limited_verbatim_excerpt: str | None # Short permitted quotation (if authorized for display)
    study_design_scope: str             # guideline | rct_meta | epidemiology | preclinical
    population_scope: str               # human_adult_general | human_high_risk | preclinical_non_human
    jurisdiction_code: str
    observed_source_date: date | None   # Nullable; never fabricated
    retrieved_at_utc: datetime
    reviewed_at_date: date
    attribution_text: str               # Mandatory Clause 3 bibliographical reference & non-endorsement notice
    ai_processing_allowed: bool         # Clause 6 gate verified before external LLM transmission
    link_ok: bool = True                # CancerLens-set; False only when canonical_url is proven dead
```

---

## 3. Local Operational Tables in `cancerlens_app.db` (SQLite 3.45+ `STRICT`)

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. Sanitized Canonical Claim Memory Library (FR-07 / FR-14 Related Reviewed Claims)
-- Only rows with review_status = 'APPROVED' are served in shared Related Reviewed Claims views.
CREATE TABLE claim_memory_library (
    claim_memory_id TEXT PRIMARY KEY,
    canonical_claim_hash TEXT NOT NULL UNIQUE,
    canonical_claim_text TEXT NOT NULL CHECK (length(canonical_claim_text) BETWEEN 15 AND 600),
    cancer_id TEXT NOT NULL,
    subtype_id TEXT,
    category_slug TEXT NOT NULL,
    primary_outcome_code TEXT NOT NULL CHECK (
        primary_outcome_code IN ('SUPPORTED', 'MIXED_OR_CONTEXT_DEPENDENT', 'CONTRADICTED', 'INSUFFICIENT_EVIDENCE')
    ),
    outcome_label TEXT NOT NULL,
    nuance_warning_note TEXT NOT NULL,
    cited_document_ids_json TEXT NOT NULL DEFAULT '[]',
    cited_fact_ids_json TEXT NOT NULL DEFAULT '[]',
    cancer_info_api_version_hash TEXT NOT NULL,
    pii_sanitized_verified INTEGER NOT NULL DEFAULT 1 CHECK (pii_sanitized_verified = 1),
    review_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW' CHECK (
        review_status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')
    ),
    search_hit_count INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_searched_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;

CREATE VIRTUAL TABLE claim_memory_fts USING fts5(
    claim_memory_id UNINDEXED,
    cancer_id UNINDEXED,
    category_slug UNINDEXED,
    canonical_claim_text,
    nuance_warning_note,
    tokenize = 'porter unicode61'
);

-- 2. Adaptive Experience Learning: Mechanism A (Lay-to-Medical Search Bridges - FR-08 / FR-19)
-- Only rows with review_status = 'APPROVED' are automatically applied to expand user queries.
CREATE TABLE learned_query_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_lay_phrase TEXT NOT NULL UNIQUE,
    learned_medical_query TEXT NOT NULL,
    cancer_id TEXT NOT NULL,
    category_slug TEXT,
    verified_fact_ids_json TEXT NOT NULL CHECK (length(verified_fact_ids_json) > 4),
    review_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW' CHECK (
        review_status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')
    ),
    times_applied INTEGER NOT NULL DEFAULT 0,
    hops_saved_per_run INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;

-- 3. Dual-Pool Runtime Credit & Telemetry Ledger ($150 Meta Model API Pool + $100 Baseten Model API Pool)
-- Enforces SG-05: reasoning_tokens_subset is logged separately and NEVER added on top of output_tokens.
CREATE TABLE budget_ledger (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    pipeline_stage TEXT NOT NULL,
    provider_name TEXT NOT NULL CHECK (provider_name IN ('meta_model_api', 'baseten_model_api')),
    model_id TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens_subset INTEGER NOT NULL DEFAULT 0,
    finish_reason TEXT NOT NULL,
    estimated_cost_usd REAL NOT NULL,
    latency_ms INTEGER NOT NULL,
    is_live_call INTEGER NOT NULL DEFAULT 1 CHECK (is_live_call IN (0, 1)),
    created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;

-- 4. Private User Saved Results (Private-by-Default Capability Token Snapshots)
CREATE TABLE saved_results (
    saved_result_id TEXT PRIMARY KEY,
    capability_token_hash TEXT NOT NULL UNIQUE,
    resolved_mode TEXT NOT NULL CHECK (resolved_mode IN ('LEARN', 'EVALUATE')),
    cancer_id TEXT,
    subtype_id TEXT,
    category_slug TEXT,
    query_or_claim_summary TEXT NOT NULL,
    result_envelope_json TEXT NOT NULL,
    cited_document_ids_json TEXT NOT NULL DEFAULT '[]',
    is_public INTEGER NOT NULL DEFAULT 0 CHECK (is_public = 0),
    created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    expires_at_utc TEXT NOT NULL
) STRICT;

-- 5. Source-Link Verification Cache (dead outbound citations render unlinked, never dropped)
CREATE TABLE link_verification_cache (
    url TEXT PRIMARY KEY,
    is_alive INTEGER NOT NULL CHECK (is_alive IN (0, 1)),
    checked_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;
```
