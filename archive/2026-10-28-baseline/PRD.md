# CancerLens — Product Requirements Document (`PRD.md`)

- **Document Status:** `PROPOSED` (Updated Specification Baseline v2 — Reflects Verified Participant Guide, `$150` Meta Model API Exclusive Pool, Similar Claims Library, and Adaptive Experience Learning)
- **Date:** October 28, 2026 (`America/Chicago`)
- **Authoring:** CancerLens team
- **Target Event:** Meta Global AI Developer Hackathon (Building Period: October 27 – November 4, 2026; Official Deadline: **Wednesday, November 4, 2026 at 9:00 PM EST / 8:00 PM CST**)

---

## 1. Purpose, Evidence Status, and Scope Audit

### 1.1 Purpose
This Product Requirements Document (`PRD.md`) defines the functional, non-functional, evidentiary, legal/rights, and operational requirements for **CancerLens**, a dual-mode cancer information discovery and claim-evaluation web application with **Adaptive Experience Memory** built for the Meta Global AI Developer Hackathon.

### 1.2 Epistemic Labeling Convention
Throughout this specification and its companion documents, material statements carry explicit epistemic labels:
- **`VERIFIED`**: Confirmed directly from inspected source evidence, with source citation, page/cell locator, and date.
- **`PROPOSED`**: Architectural, product, or design decisions recommended for implementation during the hackathon build window.
- **`ASSUMED`**: Reasonable working assumptions used for planning where direct verification is pending.
- **`UNVERIFIED`**: External facts or live API account states that require explicit verification gates before production reliance.

### 1.3 Audit of All Four Supplied Attachments (`VERIFIED`)
1. **`Meta Hackathon Participant Guide.pdf` (`VERIFIED` — 12 pages inspected Oct 28, 2026):**
   - **Problem Statements (Page 1):** Projects must build toward **Build for Your World** (*"Bring Meta's models into your domain. Solve a problem you know firsthand, free up time and mental space, and make something possible that wasn't before"*) or **Push the Frontier**. CancerLens squarely targets **Build for Your World** within the **Indie Developer Track (`$400,000` prize pool, Pages 9–10)**.
   - **Required Meta Models (Page 1):** Incorporates Meta's models through the **Meta Model API**: **Muse Spark series**, **Muse Wonder**, **Muse Image**, **Muse Voice Transcribe**, and **SAM 3.1**, plus coding faster with **Muse Code** coding agent.
   - **Partner Credits Status (`VERIFIED` User Confirmation, Oct 28, 2026):** Baseten, Modal, and Fireworks partner credits (Pages 6–7) are **not used** (application was not selected for partner credits). CancerLens runs **$100\%$ on the `$150` Meta Model API credit pool**.
   - **Schedule & Official Deadlines (Pages 3–4):**
     - Building period: **October 27 – November 4, 2026** (Page 4).
     - Live workshop of note: **Wed, Oct 28 | 12:00–1:00 PM ET (11:00 AM–12:00 PM CT): *Agents 102: Best Practices for Verifiable Agents* (Yash Khare)** (Page 3).
     - Daily Discord office hours in `#office-hours`: **10:00–11:00 AM ET (9:00–10:00 AM CT)** on weekdays (Page 3).
     - Last full day for submission questions/troubleshooting: **Tuesday, Nov 3, 2026** (Page 3).
     - **Final Submission Deadline:** **Wednesday, November 4, 2026 at 9:00 PM EST (8:00 PM CST)** via the Cerebral Valley (CV) platform. Late submissions are not considered (Pages 4, 8).
   - **Hackathon Rules & Anti-Projects (Pages 4–5):**
     - Public repository required; solo participants allowed (max 4 per team) (Page 4).
     - **Demo & New Work Rule (Page 4):** Three-minute demo video must *only* highlight specific features, code, and functionality built during the Hackathon (`Oct 27 – Nov 4`). Failure to clearly identify original event contributions results in immediate disqualification.
     - **Banned / Sample Anti-Projects (Pages 4–5):** Disqualifies projects that use code/data/assets without rights, or generic/policy-violating apps including: *"Any project using AI to generate and give medical advice e.g. AI Mental Health Advisor, skin blemish detector, etc.; Basic RAG Applications; Simple Image Analyzers; simple 'AI for Education' Chatbots"*.
   - **Billing & Credit Activation Rules (Page 5):**
     - Each participant receives `$150` in Meta Model API credits, distributed in batches on the **Billing** page.
     - **Mandatory Payment Card Gate:** *"In order to use your credits & make an API call, a credit card must be applied to your account. Upon providing a valid payment method a temporary pre-authorization charge will show up on your card, this will be released automatically within a few business days."*
     - **Spend Limit Notification Warning:** Page 5 notes you can set a `"Spend Limit" notification` on the Billing page. Because a notification is **not** a hard billing stop, CancerLens enforces a strict **in-code SQLite `budget_ledger` hard circuit breaker** so your card is never charged beyond the free `$150` credit pool.
   - **Judging Rubric & Bonus Prizes (Pages 8–12):**
     - **Stage 1 (Pass/Fail, Page 8):** Fits theme + reasonably uses Meta Model API.
     - **Stage 2 Rubric (`0–10` scale, Page 9):** **Impact (`30%`)**, **Use of Meta AI Tooling (`25%`)**, **Technical Depth & Execution (`20%`)**, **Demo (`25%`)**.
     - **Targeted Bonus Prizes (Pages 10–12):** **Best Agentic Use-Case (`$5,000`, Page 11)**, **Best Creative Build (`$5,000`, Pages 11–12 — rewards projects built using `Muse Wonder` or `Muse Image`)**, **Community Vote (`$10,000`, Page 11)**, and **Most Viral Project (`$20,000`, Page 10)**.
2. **`CancerLens_Launch_Coverage_and_Permissions_2026-10-16.xlsx` (`VERIFIED`):**
   - Inspected directly (review dates: October 15–16, 2026). Contains **12 worksheets**, **102 source entries** (`Source register!A9:Z110`: `29 Keep`, `16 Secondary`, `17 Replace`, `2 Quarantine`, `38 Permission-dependent`; `13 P1`), **26 candidate cancer types** (`Cancer readiness!A6:G31`), and **338 coverage decisions** (`Section coverage!A6:M343`: **119 `Source verified`**, **168 `Partial`**, **51 `Gap`**; all 338 marked `"Not accepted for publication by this audit"` in `L6:L343`). `Document evidence!A6:J175` lists 170 documents (`D001`–`D170`) where `I6:I175` confirms hashes are `"Research-tool transcript hash; not original HTML/PDF hash"`.
3. **`Idea Approval.png` (`VERIFIED` via two Discord screenshots):**
   - Shows organizer **`Adam Blumenfeld` (`adamblumenfeld`, Cerebral Valley)** confirming on October 26, 2026 at 8:02 PM in `#questions > Clarification about project`: *"Thanks for the guidance around questions. This idea is permitted though, the anti projects are meant to encourage people to go beyond what we've seen a lot of projects around before."*
4. **`PROJECT_MEMORY.md` (`VERIFIED`, dated October 27, 2026):**
   - Locks both **Learn (category browse & Q&A)** and **Evaluate (claim assessment)** as non-negotiable core modes.

---

## 2. Vision, Mission, and Anti-Project Differentiation

### 2.1 Vision & Mission (`PROPOSED`)
- **Vision:** Empower everyday people facing overwhelming cancer terminology or viral misinformation to explore trusted public medical knowledge and verify specific cancer claims with transparent, passage-level provenance and collective experience memory.
- **Mission:** Build a zero-hallucination-tolerance informational lens powered by **Meta's `Muse` model family (`Muse Spark`, `Muse Wonder`, `Muse Voice Transcribe`, `SAM 3.1`)** where every assertion is bound to a rights-cleared source passage, every context mismatch is surfaced, similar community-searched claims are cross-checked safely, and the retrieval investigator learns stronger lay-to-medical search paths over time without ever drifting from verified clinical sources.

### 2.2 How CancerLens Defeats the "Basic RAG" and "Medical Advice" Anti-Project Concerns (`PROPOSED`)
| Hackathon Anti-Project Concern (Guide Page 5) | Why Naive Apps Fail | How CancerLens Engineers Beyond It (Rubric Alignment: Page 9) |
| :--- | :--- | :--- |
| **Basic RAG Application** | Splits unvetted PDFs into fixed chunks, embeds in a vector DB, runs top-$k$ cosine similarity, and stuffs chunks into one prompt—producing conflated cancer subtypes, hallucinated citations, and zero memory. | **1. Structured PICO & Subtype Evidence Graph:** Passages retain explicit cancer subtype (`NSCLC` vs. `SCLC`), clinical section, jurisdiction, study design (`human_rct`, `guideline`, `preclinical`), and upstream lineage (`origin_source_id`).<br>**2. Bounded Investigator (`Muse Wonder` / `Muse Spark`):** Decomposes compound claims into atomic sub-claims, executes up to 3 hops of FTS5 + metadata search with tool feedback, and maps each sub-claim to a deterministic 4-state rubric.<br>**3. Adaptive Experience Learning (Mechanisms A & B):** Remembers successful lay-to-medical search reformulations (`learned_query_mappings`) so future queries find deeper evidence on Hop 1, and cross-enriches both Learn and Evaluate answers with verified **Similar Claims & Common Misconceptions** from `claim_memory_library`.<br>**4. Deterministic Substring Quote Verifier:** Verifies every `[doc_id:passage_id]` and checks that every verbatim quote is an exact character substring of the admitted passage. |
| **Medical Advice / Skin Blemish Detector** | Accepts photos of skin lesions or scans, suggests diagnoses, or recommends personal chemotherapy dosing. | **1. Strict Input Boundary Guard:** Rejects skin lesions, X-rays, pathology slides, lab reports, and personal symptom triage at the first classification gate.<br>**2. Informational Screenshot OCR Only:** Vision models (`Muse Spark` / `Muse Wonder` + optional `SAM 3.1` text-box isolation) extract *only* text/claims from screenshots of articles or social posts, requiring user confirmation before assessment. |

---

## 3. Target Audience & Personas (`ASSUMED` Hypotheses)

1. **Persona A — The Newly Navigating Family Member ("Maya", 34):** Needs plain-language explanations of *Breast Cancer* staging, screening, and terminology, enriched with common misconceptions already checked on the platform. (**Learn Mode**).
2. **Persona B — The Skeptical Family Fact-Checker ("Raj", 42):** Receives forwarded screenshots or blog links claiming *"soursop or baking soda cures colon cancer"* or *"annual full-body CT scans save everyone over 30"*. Needs a non-binary verdict, context mismatch breakdown, and a **Similar Claims** panel showing related variations already investigated. (**Evaluate Mode**).
3. **Persona C — The Hackathon Judge ("Alex", 29):** Evaluates CancerLens against the Stage 2 Rubric (`Impact 30%`, `Use of Meta AI Tooling 25%`, `Technical Depth 20%`, `Demo 25%`, Guide Page 9).

---

## 4. Core User Journeys (`PROPOSED`)

### Journey 1: Learn Mode — Category Browse, Subtype Precision & Adaptive Misconception Enrichment
1. User selects **Learn: Browse & Ask**, picks a cancer entity (e.g., **Breast Cancer** or **Lung Cancer** with mandatory `NSCLC` vs. `SCLC` subtype selector), and clicks a category (e.g., **Screening**) or types a question.
2. **Adaptive Synonym Lookup (Mechanism A):** If the user typed lay phrasing (e.g., *"chemo brain"* or *"water pill side effects"*), the system checks `learned_query_mappings` to immediately expand the query to the proven NCI terminology learned from prior multi-hop investigations.
3. **Rights-Gated Synthesis & Cross-Mode Enrichment (Mechanism B):**
   - Synthesizes a plain-language answer using `Muse Spark` / `Muse Wonder` with inline `[doc_id:passage_id]` locators, Verbatim Quote toggle, and separated Observed / Retrieved / Reviewed dates.
   - Automatically queries `claim_memory_library` for verified claims linked to that `(cancer_id, category_slug)` and appends a **"Common Claims & Misconceptions Checked in This Category"** card so the learner gets an enhanced, proactive answer.

### Journey 2: Evaluate Mode — Claim Assessment with Exact-Match Cache, Consistency Check & Similar Claims
1. User submits a claim (e.g., *"High-dose IV Vitamin C cures pancreatic cancer in humans and replaces chemotherapy"*).
2. **PII Sanitization & Canonical Claim Check:**
   - `Muse Spark` + deterministic PII scrubber strips any personal names/identifiers and normalizes the assertion into an anonymous `canonical_claim_text`.
   - **Exact-Match Fast Path & Consistency Double-Check:** If `canonical_claim_hash` already exists in `claim_memory_library` **and** its `corpus_snapshot_hash` matches the current admitted database, CancerLens can immediately serve the verified assessment (`$0.00` credit cost, `< 50ms`) with a badge **`[Verified in Claim Memory • 0 Credits Used — Click to Re-Run Live]`**, OR use the stored outcome as a **Consistency Double-Check** if re-run live.
3. **Bounded Investigator Execution (Cache Miss or Live Re-Run):**
   - Decomposes compound claims into atomic sub-claims, executes up to 3 search hops against `v_admitted_passages`, evaluates the 4-state verdict rubric, and detects 5-dimension Context Mismatches.
4. **Experience Consolidation (Learning Step):**
   - If the Investigator needed 2–3 hops to bridge a lay term to an NCI medical term, it saves that mapping into `learned_query_mappings` (so the *next* user gets a 1-hop enhanced search).
   - Stores the sanitized, anonymous canonical claim and its verified `ResultEnvelope` in `claim_memory_library`.
5. **Similar Claims Section:**
   - Below the main verdict, displays the **"Similar Claims Searched in CancerLens"** section (`top 3–5` FTS5/topic matches from `claim_memory_library`), showing each similar claim's non-binary verdict badge and a mandatory nuance banner explaining why wording differences (e.g., *average-risk adults* vs. *BRCA2 carriers*) produce different outcomes.

### Journey 3: Multimodal Screenshot & Public URL Claim Extraction with User Confirmation
1. User uploads a social-media screenshot (`PNG`/`JPEG`/`WEBP` $\le 5\text{ MB}$) or pastes a public `https://` URL, or optionally speaks a query via `Muse Voice Transcribe`.
2. **Vision / Fetch Gate:** Rejects clinical skin lesions/scans (`Out of Scope`). Extracts visible text/claims and displays the **Editable Confirmation Box** before running Journey 2.

---

## 5. Functional & Non-Functional Requirements

### 5.1 Functional Requirements (`FR`)
| ID | Priority | Requirement Description | Verification Method |
| :--- | :--- | :--- | :--- |
| `FR-01` | `P0` | **Category Browse & Search (Learn Mode):** Browse by cancer type, subtype, and 11 clinical categories (`overview`, `symptoms`, `risk_factors`, `prevention`, `screening`, `diagnosis`, `staging`, `treatment`, `supportive_care`, `side_effects`, `prognosis/survival`, `terminology`) + natural-language Q&A. | `TEST-LEARN-01..05` |
| `FR-02` | `P0` | **Subtype & Coverage Honesty:** Umbrella cancers (`Lung`, `Colorectal`, `Pancreatic`, `Leukemia`) enforce subtype selection; unseeded sections return honest `CORPUS_GAP` notices with official NCI links. | `TEST-GAP-01..04` |
| `FR-03` | `P0` | **Compound Claim Decomposition (Evaluate Mode):** Splits 1–4 assertion claims into atomic sub-claims and evaluates each independently. | `TEST-EVAL-01..06` |
| `FR-04` | `P0` | **Context Mismatch Detection:** Flags mismatches across: (1) Human vs. Preclinical/Lab, (2) Subtype/Stage, (3) General vs. High-Risk Population, (4) Jurisdiction, and (5) Observed vs. Projected Statistics. | `TEST-MISMATCH-01..05` |
| `FR-05` | `P0` | **4-State Non-Binary Verdict Rubric:** Assigns `SUPPORTED`, `MIXED_OR_CONTEXT_DEPENDENT`, `CONTRADICTED`, or `INSUFFICIENT_EVIDENCE` (`SOURCE_STATES_INSUFFICIENT` vs. `CORPUS_COVERAGE_GAP`); zero binary True/False or invented percentages. | `TEST-SCHEMA-01` |
| `FR-06` | `P0` | **Rights-Cleared Retrieval Gate:** SQL view `v_admitted_passages` enforces `admission_status = 'ADMITTED'` outside the model. Quarantined (`WHO GL01`, `Cancer Australia AU01`) and unpermitted sources cannot leak. | `TEST-DB-01..02` |
| `FR-07` | `P0` | **Citation & Verbatim Quote Verifier:** Validates every `[doc_id:passage_id]` and verifies verbatim quotes via exact normalized substring match against `clean_text`. | `TEST-UNIT-01`, `TEST-CITE-01` |
| `FR-08` | `P0` | **Truthful Date Separation:** Displays `observed_source_date` (`NULL` -> `"Not stated on source page"`), `retrieved_at_utc`, and `reviewed_at_date` separately. | `TEST-UNIT-02` |
| `FR-09` | `P0` | **Medical Boundary & Safe Refusal:** Blocks personal diagnosis, treatment selection, drug dosing, and clinical lesion/scan images (`OUT_OF_SCOPE_CLINICAL`) while offering general educational links. | `TEST-SAFE-01`, `TEST-IMG-02` |
| `FR-10` | `P1` | **Screenshot Claim Extraction & User Confirmation:** Extracts text from informational screenshots (`\le 5\text{MB}`) via Meta Model API Vision (`Muse Spark` / `Muse Wonder`), presenting an editable confirmation box before evaluation. | `TEST-IMG-01` |
| `FR-11` | `P1` | **Public URL Extraction with SSRF Defense:** Validates DNS/IP against private ranges, enforces redirect/byte caps, extracts claim text, and requires user confirmation. | `TEST-URL-01` |
| `FR-12` | `P1` | **Ambiguous Input Mode Selector:** Prompts user to choose **Learn** or **Evaluate** when input intent sits between a question and a claim. | `TEST-AMB-01` |
| `FR-13` | `P1` | **Versioned Saved Results & Explicit Refresh:** Reopening a saved link loads the immutable snapshot at `$0.00` credit cost; clicking **Re-Run Live** checks `corpus_snapshot_hash` and diffs changes. | `TEST-PRIV-01` |
| `FR-14` | `P0` | **Similar Claims Library & Exact-Match Cache / Double-Check (Updated per Owner Request #3):** Every valid informational claim evaluated is PII-scrubbed, generalized into an anonymous `canonical_claim_text`, and stored in `claim_memory_library` (seeded with 20 baseline claims + grown dynamically from sanitized searches). Used to: (a) serve instant `$0`-cost cached results or consistency double-checks when the exact same claim is searched against the same `corpus_snapshot_hash`, and (b) display a **"Similar Claims Searched in CancerLens"** section after every evaluation. | `TEST-MEM-01..03` |
| `FR-15` | `P1` | **Country Burden Statistics Card:** Displays curated epidemiological data (`US05` USCS, `CA01` StatCan, `AU02` AIHW) with explicit observation years and rate-vs-count labels. | `TEST-LEARN-01` |
| `FR-16` | `P0` | **Runtime Budget & Meta Model API Telemetry (`$150` Exclusive Pool):** Logs every Meta Model API call (`Muse Spark`, `Muse Wonder`, `Muse Voice Transcribe`, `SAM 3.1`) to `budget_ledger`, enforcing a hard pre-submission circuit breaker at `$115.00` so the user's credit card is never billed beyond the `$150` free credits. | `TEST-PERF-01` |
| `FR-17` | `P1` | **Spoken Query Input via `Muse Voice Transcribe`:** Allows users to speak a question or claim (`\le 30\text{s}` audio) via the Meta Model API (`Muse Voice Transcribe`), populating the editable confirmation box. | `TEST-VOICE-01` |
| `FR-18` | `P3` | **Optional WhatsApp Cloud API Webhook:** Deferred to `M11` (`SC-01` first scope cut) so it never blocks the Web MVP. | `TEST-WA-01` |
| `FR-19` | `P0` | **Adaptive Experience Learning (Mechanisms A & B — Added per Owner Request #4):**<br>• **Mechanism A (`Search & Synonym Learning`):** When a multi-hop investigation (`Hop 2`/`Hop 3`) bridges a lay phrase to an admitted NCI medical term/document, the system persists the mapping in `learned_query_mappings` (verified by citation support) so future queries retrieve the optimal passages on `Hop 1`.<br>• **Mechanism B (`Cross-Mode Misconception Enrichment`):** Both `Learn` and `Evaluate` modes query `claim_memory_library` to enrich answers with a **"Common Claims & Clarifications Learned"** callout grounded strictly in admitted passages. | `TEST-LEARN-MEM-01..02` |

### 5.2 Non-Functional Requirements (`NFR`)
- **`NFR-01` (Latency):** Exact-match Claim Library hit $\le 100\text{ms}$; Learn mode p95 $\le 3.5\text{s}$; Evaluate mode p95 $\le 7.5\text{s}$ (dropping to $\le 3.8\text{s}$ on subsequent similar queries via Mechanism A learned search mappings).
- **`NFR-02` (Zero Over-Budget Card Charge):** $100\%$ of runtime inference uses the `$150` Meta Model API pool; hard code-enforced stop at `$115.00` pre-submission (`$35.00` reserved for Nov 5–8 judging).
- **`NFR-03` (Zero Unlearned Medical Hallucination):** Experience learning (`FR-19`) may **only** index terms/claims that resolve to `ADMITTED` passage citations (`v_admitted_passages`). Unverified user text is never treated as a medical source.
- **`NFR-04` (Accessibility Target):** Target WCAG 2.2 Level AA check criteria (non-color-only verdict badges, `4.5:1` contrast, keyboard navigation, `aria-live` step updates).
- **`NFR-05` (Privacy & Anonymization before Claim Library Indexing):** Raw user inputs are scrubbed of PII (names, emails, phones, MRNs, first-person narrative identifiers) and converted to generalized canonical statements before entering `claim_memory_library`. Personal medical advice refusals (`OUT_OF_SCOPE_CLINICAL`) are **never** stored in the Claim Library.

---

## Appendix A: Updated Execution Roadmap (Oct 28 – Nov 4, 2026)

- **Current Date:** **Wednesday, October 28, 2026** (`America/Chicago`).
- **Official Submission Deadline:** **Wednesday, November 4, 2026 at 9:00 PM EST (`America/New_York`) / 8:00 PM CST (`America/Chicago`)** (Participant Guide Page 4 & Page 8).
- **Judging Period:** **Thursday, Nov 5 – Sunday, Nov 8, 2026**; Closing Ceremony: **Monday, Nov 9 at 12:00 PM ET (11:00 AM CT)** (Page 4).

### A.1 Reordered 12-Milestone Dependency Table
| Milestone ID | Dependency-Ordered Milestone | Target Window (`America/Chicago`) | Effort Range | Dependencies | Core Deliverables | Definition of Done (DoD) | Verification Gate | Principal Risk | Fallback |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `M0` | **History & Prep Baseline** (Oct 26–27) | Oct 26–27 (Completed) | Historical | None | Idea approval on Discord (Oct 26, 8:02 PM); Oct 15–16 source audit workbook; initial Oct 27 repo commit `0d6dff1e` + v1 specs. | Documented in `DISCLOSURE.md` as pre-build research & planning. | `VG-M0`: Confirmed. | None. | N/A |
| `M1` | **Spec v2 Lock & Meta Billing Activation** | Day 2: Wed Oct 28 (11:30 AM – 2:30 PM CT) | `2–3 hrs` | `M0` | Updated 7 Markdown specs (v2); Owner completes Meta Billing page setup (apply card for pre-auth, set Spend Limit alert, generate API key per Guide p. 5). | Credits active on Meta Billing page; `.env.local` created locally with `META_API_KEY`. | `VG-M1`: All 7 v2 specs written; API key ready locally. | Pre-auth card check delayed. | Use `#office-hours` Discord channel (9–10 AM CT) if billing issue arises. |
| `M2` | **Meta Model API Live Connectivity & Budget Ledger** | Day 2 PM: Wed Oct 28 (3:00 PM – 7:30 PM CT) | `4 hrs` | `M1` | `MetaModelClient` adapter, SQLite `budget_ledger` table (`$115` hard pre-submission cap), live smoke test of `Muse Spark`, `Muse Wonder`, `Muse Voice Transcribe`, and `SAM 3.1`. | `pytest -m live_smoke` returns HTTP 200 from Meta Model API and logs real token/cost telemetry. | `VG-M2`: Redacted `live_smoke_receipt.json` saved. | Specific model slug naming difference. | Query `/v1/models` (Guide p. 6 `Model list`) and map exact IDs in `config.py`. |
| `M3` | **Permitted Evidence Ingestion & Rights Gate** | Day 3 AM: Thu Oct 29 (9:00 AM – 2:00 PM CT) | `5 hrs` | `M1` | SQLite `3.45+` schema migration (`DATABASE.md`), deterministic NCI/CDC/AIHW/StatCan fetcher, SHA-256 raw & cleaned text hashing, `v_admitted_passages` view. | 7 P1 cancers deeply populated + all 26 cancers in taxonomy + 20 initial claims seeded in `claim_memory_library`. | `VG-M3`: Negative SQL test proves `GL01`/`AU01` cannot be retrieved. | NCI HTML layout differences. | Curated static snapshot manifest with verified SHA-256 hashes. |
| `M4` | **FTS5 Retrieval + Mechanism A (`Search & Synonym Learning`)** | Day 3 PM: Thu Oct 29 (2:30 PM – 8:00 PM CT) | `5 hrs` | `M3` | `passages_fts` BM25 search, subtype filter (`NSCLC` vs. `SCLC`), and `learned_query_mappings` table that records successful multi-hop lay-to-medical term bridges. | Hop 1 retrieval automatically uses learned query mappings; Run #2 of a multi-hop query resolves in 1 hop. | `VG-M4`: Recall@5 $\ge 90\%$ + Mechanism A latency reduction test passes. | Over-broad learned synonym. | Only persist mappings that yielded verified cited passages. |
| `M5` | **Learn Mode End-to-End + Mechanism B (`Misconception Enrichment`)** | Day 4: Fri Oct 30 (9:00 AM – 7:00 PM CT) | `7–8 hrs` | `M2`, `M4` | `/api/v1/learn` endpoint, Next.js Category Browser, Verbatim Quote toggle, Country Burden Card, and **"Common Claims & Clarifications"** enrichment from `claim_memory_library`. | Browsing a category shows plain-language NCI synthesis + verbatim quotes + relevant community claims checked in that category. | `VG-M5`: E2E Learn test passes (`ADMITTED`, `GAP`, and `ENRICHED`). | UI clutter from enrichment card. | Collapsible accordion for Common Claims in Learn view. |
| `M6` | **Evaluate Mode + Similar Claims Library & Cache/Double-Check** | Day 5: Sat Oct 31 (9:00 AM – 8:00 PM CT) | `8–9 hrs` | `M2`, `M4`, `M5` | `/api/v1/evaluate` (`Muse Wonder` / `Muse Spark` Bounded Investigator), PII-sanitized canonical claim indexer, Exact-Match Cache / Double-Check, and **"Similar Claims Searched"** UI panel. | Submitting a claim shows non-binary verdicts + Context Mismatches + Similar Claims; searching the exact same claim again hits the verified cache (`$0` cost) or double-checks consistency. | `VG-M6`: 15-case claim benchmark + Similar Claims & Cache tests pass. | Raw PII in user claim. | Mandatory PII regex + `Muse Spark` generalization before indexing; `OUT_OF_SCOPE_CLINICAL` never indexed. |
| `M7` | **Screenshot OCR (`Muse Spark`/`Wonder` + `SAM 3.1` Check) & Voice Input** | Day 6 AM: Sun Nov 1 (9:00 AM – 2:30 PM CT) | `4–5 hrs` | `M2`, `M6` | `/api/v1/extract/image` (clinical lesion refusal + OCR), optional `/api/v1/extract/voice` (`Muse Voice Transcribe`), Editable Confirmation UI, and Similar Claims match across all input modalities. | Screenshot and voice inputs populate the confirmation box, run Evaluate, and display Similar Claims seamlessly. | `VG-M7`: Image OCR, clinical refusal, and voice smoke tests pass. | Cluttered screenshot layout. | Optional `SAM 3.1` text-card isolation or client crop tool. |
| `M8` | **Public URL Extraction & SSRF Defenses** | Day 6 PM: Sun Nov 1 (3:00 PM – 8:00 PM CT) | `4–5 hrs` | `M6` | `/api/v1/extract/url`, DNS/IP private-network guard, redirect/byte cap, readable claim extractor, confirmation UI. | Public URL extracts claim safely and connects to Evaluate + Similar Claims; private IPs blocked $100\%$. | `VG-M8`: SSRF test suite passes $100\%$. | Target site blocks bot fetch. | Graceful fallback prompting user to paste snippet or upload screenshot. |
| `M9` | **Citation, Safety & Experience-Learning Hardening** | Day 7 AM: Mon Nov 2 (9:00 AM – 2:00 PM CT) | `4–5 hrs` | `M5`–`M8` | Substring quote verifier, prompt-injection delimiter tests, Consistency Double-Check audit, and **Baseline RAG vs. Adaptive Investigator Benchmark** (`scripts/run_benchmark.py`). | Benchmark proves measurable gain from Run #1 to Run #2 (Mechanism A & B) and $0\%$ fake citations. | `VG-M9`: Full safety, citation & learning benchmark green. | Poisoned user query entering `learned_query_mappings`. | Gate learning strictly on `len(verified_passage_ids) > 0`. |
| `M10` | **Versioned Saved Snapshots & UI Polish** | Day 7 PM: Mon Nov 2 (2:30 PM – 7:30 PM CT) | `4–5 hrs` | `M6`, `M9` | `/api/v1/saved/{id}`, explicit Refresh diff viewer, dark/light accessibility check, Meta Telemetry & Learning Inspector drawer. | Judges can inspect exact Meta models used, token costs, and what the system learned from the session. | `VG-M10`: Snapshot & `axe-core` accessibility checks pass. | Contrast or mobile drawer bug. | Fix via design tokens in `DESIGN_SYSTEM.md`. |
| `M11` | **Stretch Gate & Final Troubleshooting Day** | Day 8 AM: Tue Nov 3 (9:00 AM – 12:00 PM CT) | `2–3 hrs` | `M1`–`M10` | Per Guide Page 3, **Nov 3 is the last full day for submission questions and technical troubleshooting**. Lock scope cuts (`SC-01` WhatsApp cut unless trivial). | Feature freeze declared by Nov 3, 12:00 PM CT. | `VG-M11`: Full regression suite green. | Late feature creep. | Strict feature freeze at noon Nov 3. |
| `M12` | **Deployment, 3-Min Demo Video & CV Platform Submission** | Day 8 PM – Day 9: Nov 3 (1:00 PM CT) – Nov 4 (6:00 PM CT) | `10–12 hrs` | `M1`–`M11` | Deploy public web app, verify public GitHub repo + `DISCLOSURE.md`, record 3-minute demo video (Guide p. 8), submit on CV platform by **Nov 4, 6:00 PM CT** (2 hrs before 8:00 PM CST / 9:00 PM EST deadline). | Submission confirmed on CV platform; repo & video publicly accessible; `$35` credit reserve intact for Nov 5–8 judging. | `VG-M12`: Submission receipt saved. | Last-minute upload lag on CV platform. | Submit by 6:00 PM CT (2-hour safety margin). |

---

## Appendix B: Ordered Scope Cuts (`PROPOSED`)
1. **`SC-01` (Cut First):** WhatsApp Cloud API integration (`FR-18`). Keep web app $100\%$ focused.
2. **`SC-02` (Cut Second):** `SAM 3.1` screenshot pre-segmentation (keep direct `Muse Spark`/`Wonder` Vision OCR).
3. **`SC-03` (Cut Third):** Live URL fetching (`FR-11`) if external sites block automated requests (fallback to paste snippet / screenshot while keeping SSRF unit tests).
4. **`SC-04` (Cut Fourth):** Reduce deeply populated P1 cancers from 7 to 4 (`Breast`, `Lung [NSCLC/SCLC]`, `Colorectal [Colon/Rectal]`, `Pancreatic`) while retaining all 26 cancers in taxonomy + Similar Claims + Adaptive Learning (`FR-14`, `FR-19`). **Never** cut Learn mode, Evaluate mode, Similar Claims, or Adaptive Experience Learning.


---

## Appendix C: Comprehensive Risk Register

| Risk ID | Category | Description | Likelihood | Impact | Mitigation & Technical Control |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RSK-01` | **Hackathon Eligibility** | Judges mistake CancerLens for a "Basic RAG" or "Medical Advice" anti-project (Guide Pages 4–5). | Medium | Critical | Highlight organizer approval (`Idea Approval.png`), lead the 3-minute demo with Bounded Investigator + Context Mismatch detection + Adaptive Experience Learning (`FR-19`) + Clinical Refusal Guardrail, and publish the Baseline RAG vs. CancerLens benchmark (`TESTING.md`). |
| `RSK-02` | **Meta Billing Activation Gate** | API calls fail even after claiming `$150` credits because a payment card for temporary pre-authorization was not added on the Billing page (Guide Page 5). | High | Critical | Complete the 4-step **Meta Billing & API Activation Checklist** on Day 2 (`M1`) before running `M2` live smoke tests. |
| `RSK-03` | **Credit Over-Spend Beyond `$150`** | Meta's Billing page "Spend Limit" is only a notification, not a hard lock (Guide Page 5). Unbounded calls could charge the attached credit card. | Medium | Critical | Enforce a **hard in-code SQLite `budget_ledger` circuit breaker** at `$115.00` pre-submission spend (`$35.00` reserved for Nov 5–8 judging; hard ceiling at `$145.00` total so `$150` is never exceeded). |
| `RSK-04` | **Privacy / Poisoning in Similar Claims & Learning** | A user submits personal medical details or false rumors into the Claim Library (`FR-14`) or Experience Learning (`FR-19`). | Medium | High | Strip PII and generalize into anonymous canonical claims before storing; reject `OUT_OF_SCOPE_CLINICAL` queries from memory; only store `learned_query_mappings` that successfully resolved to `ADMITTED` NCI/CDC/AIHW/StatCan passages. |
| `RSK-05` | **Rights & Licensing Leak** | Restricted content from `WHO` (`GL01`), `Cancer Australia` (`AU01`), or hospital websites leaks into public repo or API responses (Guide Page 4 bans unlicensed data). | Low | Critical | Ingest *only* `ADMITTED` `P1` sources (`US01`, `US02`, `US05`, `US06`, `AU02`, `CA01`); enforce SQL view `v_admitted_passages` and CI negative tests. |

---

## Appendix D: Three-Minute Demonstration Script & Verification Plan (Guide Page 8 & Page 9 Rubric)

- **Judging Rubric Alignment (Guide Page 9):**
  - **Impact (`30%`):** Solves real-world cancer information overload and viral misinformation without crossing clinical advice boundaries.
  - **Use of Meta AI Tooling (`25%`):** Showcases coordinated use of `Muse Spark`, `Muse Wonder` (Bounded Investigator) and `Muse Voice Transcribe` on the `$150` Meta Model API pool.
  - **Technical Depth & Execution (`20%`):** Demonstrates SQL rights gates, PICO context-mismatch tables, Exact-Match Claim Cache / Consistency Double-Check, and Adaptive Experience Learning (Mechanisms A & B).
  - **Demo (`25%`):** Live, fast split-screen workspace showing only new work built Oct 27 – Nov 4 (Guide Page 4).

### D.1 Scene-by-Scene Breakdown (`3:00` Total)
- **`0:00 – 0:25` (25s) — Hook, Problem & Organizer Boundary:**
  - Contrast dense oncology portals with viral WhatsApp/social "miracle cure" claims. Introduce CancerLens: built 100% during Oct 27–Nov 4 on the Meta Model API (`Muse Spark`, `Muse Wonder`, `Muse Voice Transcribe`), strictly informational, rights-cleared, and self-improving through safe Experience Memory.
- **`0:25 – 1:05` (40s) — Scene 1: Learn Mode + Mechanism B (`Misconception Enrichment`):**
  - Browse **Breast Cancer -> Screening** (`D049`) and **Lung Cancer (`NSCLC` vs. `SCLC`)**. Show verbatim NCI quotes, separated `Observed Source Date` vs. `Retrieved Date`, the **Country Burden Card** (`US05`, `CA01`, `AU02`), and the **"Common Claims & Clarifications Checked"** card automatically pulled from `claim_memory_library`. Click **Gallbladder -> Screening** to show an honest **Coverage Gap** notice.
- **`1:05 – 2:05` (60s) — Scene 2: Evaluate Mode (Screenshot OCR + `Muse Wonder` Investigator + Similar Claims):**
  - Upload a social-media screenshot claiming: *"Baking soda and high-dose IV Vitamin C cure pancreatic cancer in humans, and annual pancreatic CT scans save everyone over 40."*
  - Confirm extracted text -> Watch `Muse Wonder` decompose into 3 sub-claims, detect the **Preclinical vs. Human** and **High-Risk vs. General Population** context mismatches (`D080`), and render non-binary verdict badges.
  - Scroll to **"Similar Claims Searched in CancerLens"**: show how previously searched claims in the library are surfaced with nuance warnings, and re-submit an exact claim to show the **Instant Verified Claim Cache / Consistency Double-Check (`0 credits used`)**.
- **`2:05 – 2:35` (30s) — Scene 3: Mechanism A (`Search & Synonym Learning`) + Clinical Boundary Refusal:**
  - Show the **Experience Learning Inspector**: demonstrate how a lay phrase (*"chemo brain"* or *"sugar feeds tumors"*) that took 2 hops on Run #1 learned its NCI term mapping (`learned_query_mappings`) and now resolves in **1 hop (`50%` faster)** with deeper passage coverage.
  - Type a personal dosing request (*"Should I stop my gemcitabine dose today?"*) -> show instant `OUT_OF_SCOPE_CLINICAL` refusal.
- **`2:35 – 3:00` (25s) — Scene 4: Live Meta API Telemetry & `$150` Budget Protection:**
  - Open the **Meta Model API Telemetry Drawer** showing real `Muse Spark` / `Muse Wonder` model IDs, token counts, latency, and the SQLite `budget_ledger` hard circuit breaker protecting the Judge Reserve for Nov 5–8 judging.

---

## Appendix E: Development-Readiness Checklist (`READY` / `NOT READY` / `UNVERIFIED`)

| Readiness Item | Current Status (Oct 28, 2026) | Evidence / Blocker | Required Action to Reach `READY` |
| :--- | :--- | :--- | :--- |
| **1. Participant Guide & Rules Audit** | `READY` (`VERIFIED`) | `Meta Hackathon Participant Guide.pdf` (12 pages inspected Oct 28, 2026). | Follow Page 4–5 rules & Page 8–9 judging rubric. |
| **2. Partner Credits Exclusion** | `READY` (`VERIFIED`) | Owner confirmed Baseten, Modal, and Fireworks credits were not granted. | Use `$150` Meta Model API credit pool exclusively. |
| **3. Meta Model API Billing & Card Pre-Auth (Page 5)** | `NOT READY` (Action Needed) | Owner claimed `$150` credits via form, but has not yet added the required payment card for pre-auth or generated an API key on the Billing page. | Follow the step-by-step **First-Time API Builder Setup Guide** in chat (`M1`). |
| **4. Source Rights & Coverage Audit Register** | `READY` (`VERIFIED`) | `CancerLens_Launch_Coverage_and_Permissions_2026-10-16.xlsx` (12 sheets). | Ingest `P1` `Keep` sources (`US01`, `US02`, `US05`, `US06`, `AU02`, `CA01`) in `M3`. |
| **5. Updated 7 Markdown Specifications (v2)** | `READY` (`PROPOSED`) | All 7 files updated on Oct 28, 2026 with Similar Claims (`FR-14`) and Adaptive Learning (`FR-19`). | Proceed to `M2` once Meta API key is generated. |
