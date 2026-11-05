# CancerLens backend: Track 1, Stage 2

Status, 4 Nov 2026: Stage 2 built. **174/174 offline tests pass at $0.00 LLM spend**
(62 Stage 1 + 112 Stage 2). Live Cancer Info API adapter verified read-only against
`https://cancerinfo-api.onrender.com` (search + cancers + by-ID facts); no live Meta/Baseten call made.

## Stage 2 deliverables

- **D1 live adapter:** default base URL is the live service, timeout 45s (Render cold
  starts), CORS covers local static servers (`:3000`/`:5500`/`:8080`). Live search is
  `GET /v1/search` (Stage 1 assumed `/v1/evidence/search`, which is HTTP 404 live);
  `_coerce_record_to_evidence_item` maps nested `SearchResultItem` / `ContentRecordOut` /
  `ConsensusItemOut` shapes to `CancerInfoEvidenceItem`, flat Stage 1 dicts untouched.
  `GET /v1/facts?ids=a,b` (up to 50 IDs, live-verified 4 Nov 2026) returns
  `FactsResponseOut` (`{"data": [SearchResultItem...]}`), so saved-result reads
  revalidate live and double-checks run; on a by-ID outage they still degrade to a
  labeled unrevalidated snapshot (`200`, `revalidated=false`, nothing invalidated)
  and a labeled `CANCER_INFO_API_UNAVAILABLE` 503 respectively.
- **D2 guards (`app/guards/`):** clinical boundary (SEC-03), PII sanitizer (SG-10),
  pure-Python image guard (magic bytes, 5 MB, 4096px, in-memory EXIF strip, zero disk
  writes), SSRF guard (https:443 only, DNS + private/loopback/link-local/CGNAT/IPv6
  block, injectable resolver). `hooks.py` delegates with unchanged signatures.
- **D3 routes:** `POST /extract/url` is fully wired (guard + 3-hop redirect re-guard +
  HTML extract + PII scrub) behind `URL_EXTRACTION_ENABLED=false` default so the
  offline suite stays hermetic; `POST /extract/image` enforces the guard (422 on bad
  uploads) then transcribes via Meta image understanding (`input_image` block,
  PII scrub, 3000 chars, user confirmation required).
- **D4 verifier:** `run_stage4_verifier` factored verbatim into
  `app/verifiers/stage4_verifier.py`, re-exported from `hooks.py`.
- **D5 tests:** `tests/test_stage2_guards_and_verifier.py` (108 tests, mocked
  DNS/HTTP only). One Stage 1 assertion updated: garbage image bytes now expect
  422 per D3 instead of Stage 1's blanket 501.

## Stage 1 notes (kept)

Status, 1 Nov 2026: Stage 1 built and verified offline only. **$0.00 spent. No live Meta, Baseten
or Cancer Info API call has been made by this code.** Nothing here is evidence of live behavior.

## Run

```bash
cd backend
uv venv -p 3.12 .venv && source .venv/bin/activate
uv pip install -r pyproject.toml --extra test
pytest                                    # offline suite (mocked transports, real sockets blocked)
python scripts/export_openapi.py          # or, from repo root: python -m backend.scripts.export_openapi
cp .env.example .env.local                # fill in keys; keep LIVE_LLM_CALLS_ENABLED=false until the smoke gate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Handoffs

- **HO-2 (frontend contract):** `backend/openapi.json` (OpenAPI 3.1, 9 paths). Generate `frontend/src/types/api.ts` from it.
- **HO-3 (frontend API):** `http://127.0.0.1:8000/api/v1/*`, CORS for `http://localhost:3000` and `http://127.0.0.1:3000`.
- **HO-1 (Stage 2 guards):** replace the baselines in `app/investigator/hooks.py` (signatures are stable):
  `check_clinical_boundary` (returns `(is_out_of_scope, reason)`), `sanitize_pii`, `guard_image_upload`,
  `guard_public_url`, `run_stage4_verifier`. Stage 1 tests live in `tests/test_stage1_*.py`.

## Frontend notes

- Errors use `ErrorResponse {error_code, message}`: 422 `EXTRACTION_NOT_CONFIRMED` / `INVALID_REQUEST`,
  429 `BUDGET_CIRCUIT_OPEN`, 501 `CAPABILITY_NOT_AVAILABLE`, 502 `PROVIDER_UNAVAILABLE` /
  `MODEL_OUTPUT_INCOMPLETE` / `MODEL_OUTPUT_REJECTED`, 503 `LIVE_LLM_CALLS_DISABLED` /
  `PROVIDER_NOT_CONFIGURED` / `CANCER_INFO_API_UNAVAILABLE`, 404, 410 `SAVED_RESULT_INVALIDATED`.
- In LEARN mode `overall_outcome_code` is `SUPPORTED` when sources were found and `INSUFFICIENT_EVIDENCE`
  on a gap. It is not a claim verdict; do not render it as a verdict badge.
- Use `retrieval_state` to tell a coverage gap (`SEARCH_EXECUTED_NO_MATCHES`) from a service failure (`TOOL_FAILED`).
- Saved results: `POST` returns a one-time `capability_token`; send it as `X-Capability-Token` on GET/DELETE.
- `/extract/*` return 501 in Stage 1 (guards and verified extraction not built yet).

## Assumptions and open items (need owner confirmation)

1. **Cancer Info API endpoints are live-verified** (`GET /v1/cancers`, `GET /v1/search`,
   `GET /v1/facts?ids=a,b` against `https://cancerinfo-api.onrender.com/`; facts verified
   4 Nov 2026). Paths are configurable in `.env.local`; query parameter names are in
   `cancerinfo_client.py`. Records must match `CancerInfoEvidenceItem` exactly (unknown
   extra fields are ignored; malformed records rejected).
2. **Meta pricing is unverified**, so live Meta calls are refused until `META_PRICE_*` are set.
   Baseten: $1.25 input / $0.15 cached input / $4.25 output per 1M tokens (Baseten pricing page 29 Oct; owner
   confirmed 1 Nov that `-1026` uses the same rates). Budget reservations assume no cache hits (worst case);
   the ledger bills cached tokens at the cached rate. Ledger costs are estimates, not invoices.
3. **Meta request fields are docs-verified (2 Nov 2026), not yet live-verified.** Learn mode calls the Responses
   endpoint `/v1/responses`. Meta's Responses docs confirm `store` (default `true`; `false` = server keeps no copy),
   `reasoning.effort` (`low` used), `instructions`, and `max_output_tokens` (>= 16). One live smoke call is still
   needed. The parser drops `phase: "commentary"` message items and treats `failed`/`cancelled` as errors.
4. **Voice input is out of scope** (owner decision, 1 Nov 2026, consistent with D11). There is no voice route and no
   `VOICE_TRANSCRIPT` modality.
5. `CLAIM_MEMORY_CAPTURE_ENABLED=false` by default until the Stage 2 PII sanitizer replaces the regex baseline.

## Deviations from the handoff file tree (small, intentional)

- `app/investigator/common.py`: shared service container, SG-01 tracker and deterministic envelopes.
- `app/providers/governance.py`: shared live switch, key check, pricing check and budget reservation for both providers.
- Extra response models to type the routes: `ConsistencyDoubleCheckResult`, `CancerCatalogResponse`,
  `SavedResultCreateRequest`, `SavedResultCreatedResponse`, `SavedResultView`, `BudgetHealthResponse`,
  `ProviderPoolStatus`, `UrlExtractionRequest`, `ErrorResponse`.
- `LIVE_LLM_CALLS_ENABLED` master switch (default false) to enforce the $0.00 rule in code.
- Saved results store the envelope **without** `evidence_items` and re-fetch cited facts live on read, re-running
  Stage-4; a withdrawn fact invalidates the snapshot (410). This keeps medical text off disk.
- DDL uses `IF NOT EXISTS` so startup is idempotent; otherwise identical to DATABASE.md.
