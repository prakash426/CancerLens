# CancerLens — Product Requirements (`PRD.md`)

- **Date:** November 2, 2026 (`America/Chicago`)
- **Status:** Authoritative Specification (Aligned with WHO Permission `202610792` Handoff, Organizer Approvals, Live `https://cancerinfo-api.onrender.com/` Architecture, and Baseten Claim Verification Layer; Zero Voice Input)

---

## 1. Purpose, Product Boundary & Relationship to `Cancer Info API`

**CancerLens** helps people understand cancer information and assess cancer-related claims using plain language and traceable sources.
- **Two Permanent Core Modes (Controlled via the Interactive Focal Lens Switcher):**
  1. **Learn Mode (`Explore & Learn`):** Category exploration, subtype browsing, and general educational Q&A.
  2. **Evaluate Mode (`Verify & Evaluate`):** Claim normalization, compound claim decomposition, bounded multi-hop evidence investigation, 5D context-mismatch detection, and non-binary outcomes.
- **Medical Boundary:** General educational descriptions of symptoms, diagnosis, staging, and treatments are in scope. Personal diagnosis, symptom triage, treatment selection, drug dosing, medical advice, recommended clinical paths, and analysis of personal clinical images (skin lesions, scans, pathology slides, lab reports) are strictly out of scope (`OUT_OF_SCOPE_CLINICAL`).
- **Architectural Separation (`Cancer Info API` $\rightarrow$ `CancerLens`):**
  - **`Cancer Info API`** is the independent, pre-existing FastAPI backend (live at `https://cancerinfo-api.onrender.com/`) that discovers, structures, normalizes, and rights-filters cancer information across the **25-cancer target (20 common + 5 rare)**, including licensed WHO material (**Permission Request `202610792`**, granted October 23, 2026), NCI, and other properly reusable sources.
  - **`CancerLens`** is a standalone application built during the hackathon window (`Oct 27 – Nov 4, 2026`) that consumes `Cancer Info API` via live HTTPS callouts, caches only non-restricted responses in short-TTL memory (`5 minutes`), and **never stores a duplicate medical corpus database**.

---

## 2. WHO Licence `202610792` & Source Compliance Requirements

1. **Authorized WHO Content Model (`CONFIRMED`):**
   - Under WHO Non-Exclusive Licence `202610792` (granted Oct 23, 2026), `Cancer Info API` provides selected metadata, structured factual information, concise paraphrased summaries, limited attributed quotations/excerpts, and direct links to original WHO URLs.
   - Complete WHO webpage reproduction, website mirroring, or standalone bulk redistribution is prohibited.
   - During this development phase, raw WHO-derived API responses are not exposed publicly (`PROJECT DECISION`).
2. **Clause 6 AI Controls (`store=false` & Source-Aware Prompting):**
   - External AI requests set non-retention parameters (`store=false`) and only transmit approved structured facts, summaries, or short excerpts where `ai_processing_allowed == True`.
   - AI-generated explanations must **never** be attributed to WHO as though WHO authored them. WHO may be identified as a supporting source with proper bibliographical attribution (Clause 3) and original links.
   - Verbatim quotations must be visually and structurally separated from AI-generated explanations.
3. **Branding, Non-Endorsement & Non-Commercialization (Clauses 3, 7–9):**
   - Display the mandatory independent development disclaimer (*"Independently developed; not published, endorsed, or sponsored by the World Health Organization"*).
   - Never use the WHO emblem or logo. Include zero advertisements, commercial announcements, or paid plans.

---

## 3. Core Functional Requirements (`FR`)

| ID | Priority | Requirement |
| :--- | :--- | :--- |
| **`FR-01`** | **P0** | **Learn Mode (Category Browse & Q&A):** Browse across the 25-cancer target (20 common + 5 rare), subtypes (`NSCLC` vs. `SCLC`), and clinical categories (`overview`, `symptoms`, `risk_factors`, `prevention`, `screening`, `diagnosis`, `staging`, `treatment`, `supportive_care`, `side_effects`, `prognosis/survival`, `terminology`) fetched live from `Cancer Info API`, with plain-language synthesis powered by **Meta Model API (`muse-spark-1.3`)**. Keep all categories visible and display honest coverage gaps with official links when uncovered. |
| **`FR-02`** | **P0** | **Evaluate Mode — Baseten Claim Verification Layer:** Normalize claims, decompose compound claims into `1–5` atomic assertions, request bounded evidence searches ($\le 3$ hops against `Cancer Info API`), detect 5-dimension context mismatches (`cancer_and_subtype`, `population_and_stage`, `study_design`, `endpoint_measured`, `caveat_or_dose`), and assign a 4-state non-binary outcome (`SUPPORTED`, `MIXED_OR_CONTEXT_DEPENDENT`, `CONTRADICTED`, or `INSUFFICIENT_EVIDENCE`) using **Baseten's Serverless Model API (`POST https://inference.baseten.co/v1/chat/completions`, `meta-models/muse-spark-open-1026`)**. Never invent confidence percentages. |
| **`FR-03`** | **P0** | **Backend State Machine & Pending-Tool Prose Purge (`SG-01`–`SG-07`):** Enforce `INPUT_PARSED` $\rightarrow$ `TOOL_REQUESTED` $\rightarrow$ `TOOL_EXECUTED` $\rightarrow$ `EVIDENCE_VALIDATED` $\rightarrow$ `ASSESSMENT_VALIDATED` $\rightarrow$ `DISPLAYABLE`. Immediately discard any assistant `message.content` emitted during `finish_reason="tool_calls"` (`SG-02`). Lock user UI mode (`LEARN` vs. `EVALUATE`) in backend code (`SG-06`). |
| **`FR-04`** | **P0** | **Deterministic Stage-4 Provenance & Quote Verification (`SG-08`):** Mechanically verify every cited `fact_id` / `document_id` and verbatim excerpt against `Cancer Info API`'s actual response for that request before displaying any verdict. Downgrade or abstain on any ungrounded assertion. |
| **`FR-05`** | **P0** | **Truthful Dates & Clause 6 Attribution Separation:** Display `observed_source_date` (`null` $\rightarrow$ *"Not stated on source page"*), `retrieved_at_utc`, and `reviewed_at_date` separately. Clearly distinguish AI-generated plain-language explanations from `Cancer Info API` structured facts and verbatim quotes. |
| **`FR-06`** | **P0** | **Clinical Boundary & Safe Refusal:** Refuse personal diagnosis, treatment selection, drug dosing, and clinical lesion/scan images (`OUT_OF_SCOPE_CLINICAL`) while providing safe educational category links. |
| **`FR-07`** | **P0** | **Reviewed Similar Claims Library & Cross-Provider Verification (`FR-14`):** PII-scrub and generalize evaluated claims into anonymous canonical statements in `claim_memory_library` (serving only reviewed/approved entries to users). Offer a 1-click **Live Consistency Double-Check** and display Related Reviewed Claims with mandatory nuance warnings. |
| **`FR-08`** | **P0** | **Adaptive Experience Learning (`FR-19` Mechanisms A & B):** Persist verified multi-hop lay-to-medical search bridges in `learned_query_mappings` (Mechanism A, gated by verification/review status) so future queries resolve on Hop 1, and enrich Learn & Evaluate views with reviewed Common Claims & Clarifications (Mechanism B). |
| **`FR-09`** | **P0** | **Dual-Pool Budget Circuit Breaker:** Track every Meta Model API (`$150` pool) and Baseten Model API (`$100` pool) call in `budget_ledger` with pre-submission hard stops (`$115` Meta / `$65` Baseten) preserving `$35` in each pool for judging. |
| **`FR-10`** | **P1** | **Multimodal Input with Mandatory Editable Confirmation:** Extract claim text from informational screenshots (`IMAGE_OCR`) or SSRF-guarded public URLs (`URL_EXTRACT`) into an editable confirmation box requiring explicit user confirmation before evaluation begins (voice input is out of scope per `D11`). |
| **`FR-11`** | **P1** | **Versioned Private Saved Snapshots:** Allow saving a private result snapshot (`is_public = 0`), reloading at `$0.00` cost, and explicitly refreshing if `Cancer Info API` updates or revokes a cited document. |
| **`FR-12`** | **P1** | **Check-Time PubMed Discovery Tier (`D4`):** Query PubMed at check time for short excerpts and links (zero stored abstract library), strictly gated on per-use NLM/article rights clearance and deterministic provenance checks. |
