# Live smoke: Meta Learn synthesis (Gate 1)

Date: 2026-11-04. Backend 0.1.0-stage2, API 1.0.0-stage2, local server on 127.0.0.1:8000.
Upstream: live https://cancerinfo-api.onrender.com (search + cancers).

## What ran

One call: POST /api/v1/learn with cancer_id ovarian-cancer and user_question immunotherapy.
Live search returned 1 match (ovarian immunotherapy record, NCI source, ai_processing_allowed true),
so the pipeline proceeded to Meta synthesis. No keys, prompts, or raw model content are recorded here.

## Result

PASS. DISPLAYABLE envelope, retrieval WITH_MATCHES, outcome SUPPORTED.
One learn category card citing the live fact id, one complete evidence item
(NCI attribution, canonical cancer.gov URL, jurisdiction US, observed date null preserved).
Stage-4 held: citation intact, compliance banner and AI author label present.
Telemetry: primary provider meta_model_api, model muse-spark-1.3, total latency 6994 ms,
ledger Meta spend $0.000049. Baseten pool untouched by this call.

## Limitations

Single shot, one query. Verifies model id, response structure, usage accounting, and the
gap-free Learn path only. Multi-claim synthesis and truncation behavior need the wider Gate 4 set.
Ledger cost is an estimate, not an invoice.
