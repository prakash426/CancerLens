# CancerLens Verification and Evaluation Plan (`TESTING.md`)

Status: AUTHORITATIVE SPECIFICATION (Updated November 2, 2026). All 37 offline Stage 1 backend unit and pipeline tests (`backend/tests/test_stage1_units.py` and `backend/tests/test_stage1_pipelines.py`) pass at `$0.00` credit cost. Single-shot live smoke verification (`LIVE_LLM_CALLS_ENABLED=true`) is gated until final `https://cancerinfo-api.onrender.com/` endpoint alignment.

## Status and evidence
Mocks establish control-flow and state-machine behavior (`SG-01`–`SG-10`) only. Every live test records test version, data, environment, result and limitations. A valid source ID or exact quote does not establish that an assertion is supported. Human review of claim-to-passage support is needed for the evaluation set; independent clinical review is desirable and must not be invented if unavailable.

## Gates and cases
Gate 1, provider: authenticated minimal text call using the configured Meta model (`muse-spark-1.3` on `/v1/responses`) and Baseten Claim Verification model (`meta-models/muse-spark-open-1026` on `/v1/chat/completions`); verify model identifier, response structure, usage and error behavior. Test screenshot (`IMAGE_OCR`) or public URL (`URL_EXTRACT`) extraction only if those P1 capabilities are enabled (voice input is out of scope per `D11`). Record a redacted receipt and confirm pricing separately.

Gate 2, rights and ingestion: inspect exact source and intended uses, attribution and snapshot version. Reject unresolved, revoked and quarantined content from every retrieval, model input, cache and export path. Verify source, retrieval and review dates independently; unknown dates stay null. Test withdrawal from indexes and saved outputs.

Gate 3, retrieval: curated test set covers aliases, category browse, coverage gaps, ambiguous subtype, NSCLC versus SCLC, population, human versus lab evidence and an irrelevant but authoritative passage. Record denominator, corpus version and expected passage rationale. Test that an unknown subtype does not fabricate a match.

Gate 4, Learn and Evaluate: positive, negative, ambiguous, compound and out-of-collection cases. Examine every substantive answer assertion against the cited passage, context and limitations. Score support, mismatch detection and appropriate abstention using a human-reviewed answer key. 'Not shown to reduce deaths' does not alone establish the opposite; validate the exact current passage before choosing an expected verdict. D080 examples in the old baseline are not approved gold fixtures.

Gate 5, citation: nonexistent ID, wrong admitted passage, changed quote, altered punctuation, and paraphrase incorrectly labeled verbatim. Verify exact source text independently of normalized search text. A model repeating the same answer or a cache hit is not verification. Any ungrounded substantive assertion must trigger correction, omission or abstention.

Gate 6, safety and security: personal treatment selection and symptom triage refusal alongside valid general education; upload type, size and image limits; URL SSRF including redirects, IPv6 and rebinding; prompt injection; secret and log redaction; saved-result authorization, deletion and expiry; concurrent budget reservations and provider failures. A passing finite suite does not prove complete protection.

Gate 7, privacy and learning: verify no user input reaches the shared claim library or learned mapping index by default. Test owner isolation, access tokens, retention and deletion. If a reviewed mapping is enabled, test false synonyms, population mismatch, rollback, poisoning and held-out retrieval quality. Related claims must not inherit outcomes by textual similarity.

Gate 8, experience and deployment: keyboard, focus, labels, zoom and a screen reader spot check plus automated accessibility scan; desktop and mobile user journeys; deployment restart and persistent storage; real provider outage and labeled fallback; public repository secret scan, public video access and contribution disclosure.

## Fair comparison protocol
Before tuning, define and separate a reviewed development set from a held-out evaluation set. Run fixed retrieval and the bounded investigator against identical admitted corpus snapshots and the same test cases, with comparable model and budget conditions. Log searches, relevance, claim-level support, context mistakes, abstentions, time and cost. Show sample counts and failures; do not invent baseline results or guarantee the investigator wins. Compare learning using held-out phrases and a reviewed mapping, with cold and warm runs; fewer hops do not prove proportional latency savings. If no measurable benefit or review capacity exists, disable automatic promotion and report the result honestly.

## Demo exit gate
Both modes work on the deployed environment; a live Meta call is evidenced; source links and exact passages are checked; a gap and advice refusal behave safely; selected example claims and expected results have human-reviewed rationale; no unpermitted content or secrets appear in the repository; selected browser and accessibility checks pass; recordings reflect actual event work; a clearly labeled fallback exists; submission is confirmed. If a gate fails, describe the limitation and fix or remove the affected feature rather than reporting a pass.

## References
PRD.md, ARCHITECTURE.md, DATABASE.md, SECURITY.md, and the consolidated master plan. Original baseline examples and latency numbers are hypotheses until validated.
