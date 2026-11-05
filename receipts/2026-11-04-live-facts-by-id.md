# Live check: Cancer Info API by-ID lookup (`GET /v1/facts?ids=`)

Date: 2026-11-04. Upstream `https://cancerinfo-api.onrender.com/` now serves the
by-ID endpoint from its OpenAPI spec (`FactsResponseOut`, up to 50 comma
separated content record or consensus item IDs). Prior project notes saying
`/v1/facts` is HTTP 404 with no live equivalent are superseded as of this date.

## What ran

1. `GET /v1/search?q=breast+cancer+symptoms` via `CancerInfoAPIClient.search_evidence`
   returned `SEARCH_EXECUTED_WITH_MATCHES` with 2 items; first fact ID
   `8e88ae54-...` (ovarian-cancer / symptoms) used as the by-ID probe.
2. Raw `GET /v1/facts?ids=<real id>` returned HTTP 200
   `{"data": [SearchResultItem], "meta": ...}` with the `content_record` branch
   populated (record id matches the requested id).
3. Raw `GET /v1/facts?ids=does-not-exist-xyz` returned HTTP 200 with
   `{"data": []}`: unknown IDs read as an empty list, not an error.
4. `CancerInfoAPIClient.get_facts_by_ids([<real id>])` returned 1 mapped
   `CancerInfoEvidenceItem` with matching `fact_id`; the unknown ID returned `[]`.
5. Offline suite: 171/171 pass, including the new
   `test_get_facts_by_ids_parses_live_facts_response_shape`, which locks the
   `FactsResponseOut` data-as-list shape plus `meta.generated_at` handling.

## Code impact

- `backend/app/clients/cancerinfo_client.py`: `_extract_evidence_records` handles
  the `FactsResponseOut` data-as-list shape while keeping `meta.generated_at` as
  the `retrieved_at_utc` fallback (previously the fallback path dropped it and
  stamped local now).
- Stale "no by-ID endpoint / 404" notes updated in `config.py`, `routes.py`,
  `backend/README.md`, `backend/.env.example`, and the Stage 2 fallback tests.
  The saved-result unrevalidated-snapshot fallback and the double-check 503 stay
  as transient-outage paths.

## Follow-up validation (same day)

5. Multi-ID batch, owner-validated via raw URL (`ids=<3 breast-cancer IDs>`,
   symptoms + treatment + screening): HTTP 200 with exactly the 3 requested
   items. Re-confirmed through `CancerInfoAPIClient.get_facts_by_ids`: 3/3
   mapped, request order preserved.
6. Mixed valid + invalid IDs, owner-tested (1 valid, 2 invalid): upstream
   returned the valid fact without erroring the batch, matching the client's
   filter-to-requested-IDs design.

## Limitations

Consensus-item IDs could not be probed live: a sweep of 8 cancers x 8
categories plus a 50-hit broad search found zero consensus items upstream
(`consensus_summary` and `items` null everywhere; every search hit is
`content_record`). The client's `_coerce_consensus_item` branch therefore stays
covered by offline fixtures only until upstream seeds consensus data; per owner
decision this gap is accepted and closed as dormant, not live-proven. Batches
larger than 3 IDs (up to the 50 cap) were not probed live either; the client
caps at 50 and filters to requested IDs. Zero LLM cost (read-only Layer 1 calls).
