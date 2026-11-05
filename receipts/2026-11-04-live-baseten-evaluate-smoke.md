# Live smoke: Baseten Evaluate normalization (Gate 1)

Date: 2026-11-04. Backend 0.1.0-stage2, API 1.0.0-stage2, local server on 127.0.0.1:8000.

## What ran

One call: POST /api/v1/evaluate with claim_text "sugar causes breast cancer".
Baseten normalization ran live and returned the interpreted claim plus an intent
of personal_clinical_question. Per SG-06 the pipeline honored the cautious intent
and abstained before retrieval. No keys, prompts, or raw reasoning are recorded here.

## Result

PASS for provider liveness. Telemetry: primary provider baseten_model_api,
model meta-models/muse-spark-open-1026, total latency 4221 ms,
ledger Baseten spend $0.000286. Pool balance observed to move one cent,
consistent with whole-cent billing granularity against a fractional estimate.

Note: the OUT_OF_SCOPE verdict came from the model intent label, not from the
local clinical boundary guard, which correctly allowed the claim (guard runs
before any model call). Demo claims should use neutral third-person phrasing
until the normalizer prompt is tuned.

## Limitations

Single shot. Proves authentication, model id, response structure, usage, and
ledger behavior only. The full retrieval plus verdict path was not exercised on
this call because abstention preceded search; a live SUPPORTED or CONTRADICTED
run is still needed for full Gate 4 confidence.
