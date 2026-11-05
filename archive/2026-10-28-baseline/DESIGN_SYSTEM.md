# CancerLens — Design System & UX Specification (`DESIGN_SYSTEM.md`)

- **Document Status:** `PROPOSED` (Specification Baseline — No UI Code Implemented Yet)
- **Date:** October 27, 2026 (`America/Chicago`)
- **Authoring:** CancerLens team
- **Cross-References:** `PRD.md` (`FR-01`–`FR-16`, `NFR-04`), `ARCHITECTURE.md` (`ResultEnvelope`), `TESTING.md` (`TEST-A11Y-01`–`05`)

---

## 1. Purpose & Design Philosophy

### 1.1 Purpose
`DESIGN_SYSTEM.md` defines the visual language, interaction architecture, accessibility targets, component contracts, microcopy rules, and responsive wireframes for **CancerLens**.

### 1.2 Core Design Principles (`PROPOSED`)
1. **Epistemic Humility Over False Clinical Authority:**
   - Never use hospital-triage red sirens, stethoscope/caduceus medical-authority badges, or "AI Doctor" avatars. CancerLens is an **editorial research & evidence lens**, visually inspired by public reference libraries, scientific journals, and structured fact-checking dossiers.
2. **Traceability as a First-Class Visual Element:**
   - Every paragraph and sub-claim card visibly binds to its underlying source passage (`[D049:P02]`). Users never have to trust an unanchored AI paragraph; one click or hover highlights the exact verbatim quote alongside its observed source date, retrieval date, and license notice.
3. **Never Binary, Never Color-Only:**
   - Cancer claims are rarely "100% True" or "100% False." Verdict badges pair **distinct iconography + explicit multi-word labels + border/pattern treatments + semantic color tokens**, avoiding traffic-light binary framing or invented confidence percentages.
4. **Calm, Low-Cognitive-Load Reading Experience:**
   - Users researching cancer topics are often anxious or fatigued. Typography, line length (`60–72ch`), warm-neutral surfaces, and progressive disclosure prevent information overload while keeping full rigor one click away.
5. **Confirm Before Computing on Ambiguous/Extracted Input:**
   - When extracting text from a social-media screenshot or public URL, or when a user's query sits between a question and a claim, the UI pauses with an inspectable, editable confirmation card before firing multi-model evaluation calls.

---

## 2. Brand Personality & Editorial Tone (`PROPOSED`)

- **Archetype:** The Reference Librarian & Evidence Archivist (clear, empathetic, methodical, transparent about boundaries).
- **Voice Attributes:**
  - **Plain-Language & Precise:** Explains terms like *adjuvant therapy* or *age-standardized rate* inline without talking down to the reader.
  - **Non-Judgmental on Misinformation:** When evaluating viral claims (e.g., alkaline diets or herbal cures), explains *what the evidence shows and why preclinical or anecdotal claims differ from human clinical evidence* without mocking the user who asked.
  - **Boundary-Clear:** States medical advice refusals calmly and immediately provides safe educational category links.

---

## 3. Color Palette & Semantic Design Tokens (`PROPOSED`)

All text-on-background pairings are engineered to meet a minimum **4.5:1 contrast ratio** for normal text and **3:1** for non-text UI boundaries (targeting WCAG 2.2 AA check criteria; see Section 12).

### 3.1 Surface & Neutral Tokens (Light & Dark Mode)
| Token Name | Light Mode Hex | Dark Mode Hex | Usage & Contrast Ratio |
| :--- | :--- | :--- | :--- |
| `--bg-canvas` | `#FAF9F5` (Warm Alabaster) | `#0F1419` (Deep Slate) | Primary page background; reduces harsh white glare. |
| `--bg-surface` | `#FFFFFF` (Pure White) | `#182028` (Elevated Slate) | Primary cards, result containers, input panels. |
| `--bg-subtle` | `#F1EFEA` (Stone Tint) | `#212B36` (Muted Slate) | Verbatim quote blocks, metadata footers, sidebars. |
| `--text-primary` | `#161A1D` (Ink Charcoal) | `#F3F4F6` (Crisp Off-White) | Body copy & headings (`15.2:1` on `--bg-canvas` light). |
| `--text-secondary` | `#4A5560` (Slate Gray) | `#B0BAC5` (Silver Slate) | Secondary labels, dates, locators (`7.1:1` light). |
| `--text-muted` | `#636E7B` (Ash Gray) | `#8B96A5` (Muted Steel) | Captions, non-essential metadata (`4.8:1` light). |
| `--border-default` | `#D8D4CC` (Warm Border) | `#2E3A48` (Slate Border) | Card dividers, table borders. |
| `--border-focus` | `#1D4ED8` (Royal Focus) | `#60A5FA` (Sky Focus) | `2px solid` keyboard focus ring (`outline-offset: 2px`). |

### 3.2 Brand & Mode Accent Tokens
| Token Name | Light Mode Hex | Dark Mode Hex | Usage |
| :--- | :--- | :--- | :--- |
| `--accent-learn` | `#0F52BA` (Sapphire Blue) | `#60A5FA` | **Learn Mode** active tab, category pills, dictionary links. |
| `--accent-learn-bg` | `#EFF6FF` | `#172554` | Subtle background tint for Learn mode header/badges. |
| `--accent-evaluate` | `#5B21B6` (Deep Indigo-Violet) | `#A78BFA` | **Evaluate Mode** active tab, investigator trace accents. |
| `--accent-evaluate-bg`| `#F5F3FF` | `#2E1065` | Subtle background tint for Evaluate mode header/badges. |

### 3.3 Non-Binary Claim Outcome & Coverage Status Tokens
> [!IMPORTANT]
> Every status badge MUST render **Icon + Explicit Label + Border Style** so a user viewing in grayscale or using a screen reader receives identical semantic meaning.

| Outcome / Status Code | Icon Shape | Text Label | Text / Icon Hex (Light) | Surface Fill Hex (Light) | Border Treatment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SUPPORTED` | Check-Shield (`[✓]`) | **Supported by Admitted Evidence** | `#065F46` (Deep Teal-Green) | `#ECFDF5` | `2px solid #059669` |
| `MIXED_OR_CONTEXT_DEPENDENT` | Split-Scale (`[⚖]`) | **Context-Dependent / Mixed Evidence** | `#92400E` (Deep Amber-Ochre) | `#FFFBEB` | `2px dashed #D97706` |
| `CONTRADICTED` | Cross-Octagon (`[✕]`) | **Contradicted by Admitted Evidence** | `#991B1B` (Crimson Brick) | `#FEF2F2` | `2px double #DC2626` |
| `INSUFFICIENT_EVIDENCE` (`SOURCE_STATES_INSUFFICIENT`) | Question-Lens (`[?]`) | **Scientific Evidence Unclear / Insufficient** | `#374151` (Charcoal Slate) | `#F3F4F6` | `2px dotted #6B7280` |
| `INSUFFICIENT_EVIDENCE` (`CORPUS_COVERAGE_GAP`) | Archive-Dash (`[∅]`) | **Not in Admitted CancerLens Collection** | `#1E3A8A` (Navy Slate) | `#EFF6FF` | `2px dashed #3B82F6` |
| `OUT_OF_SCOPE_CLINICAL` | Hand-Stop (`[!]`) | **Personal Medical Advice — Out of Scope** | `#7C2D12` (Burnt Sienna) | `#FFF7ED` | `2px solid #EA580C` |

---

## 4. Typography & Type Scale (`PROPOSED`)

- **UI & Editorial Sans (`--font-sans`):** `'Inter'`, `'Plus Jakarta Sans'`, or system fallback (`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`). Chosen for clean legibility and unambiguous numeral rendering.
- **Editorial Serif for Verbatim Quotes (`--font-serif`):** `'Newsreader'`, `'Source Serif 4'`, or `Georgia, serif`. Used **exclusively** inside verbatim quote blocks so users can visually distinguish exact source quotations from AI-generated plain-language paraphrases at a glance (`FR-07`).
- **Monospace for Provenance & Telemetry (`--font-mono`):** `'JetBrains Mono'` or `ui-monospace, SFMono-Regular, monospace`. Used for passage locators (`[D049:L38]`), SHA-256 hashes, observed/retrieved dates, and Meta model trace metrics.

### 4.1 Type Scale (`rem` based on `16px` root)
| Token | Size (`rem` / `px`) | Line Height | Weight | Usage |
| :--- | :--- | :--- | :--- | :--- |
| `--text-display` | `2.0rem` (`32px`) | `1.25` | `700` | Workspace header / cancer profile title |
| `--text-h1` | `1.5rem` (`24px`) | `1.3` | `700` | Result section headers, mode headers |
| `--text-h2` | `1.25rem` (`20px`) | `1.35` | `600` | Sub-claim title, category card title |
| `--text-h3` | `1.0625rem` (`17px`)| `1.4` | `600` | Source card title, mismatch alert header |
| `--text-body-lg`| `1.0625rem` (`17px`)| `1.65` | `400` | Plain-language synthesis (optimal reading comfort) |
| `--text-body` | `0.9375rem` (`15px`)| `1.6` | `400` | Standard UI copy, rationale descriptions |
| `--text-quote` | `0.9375rem` (`15px`)| `1.65` | `400` (`--font-serif`) | Verbatim source quote blocks |
| `--text-meta` | `0.8125rem` (`13px`)| `1.45` | `500` (`--font-mono`) | Citation badges, dates, license attribution, trace |

---

## 5. Spacing, Grid & Responsive Layout System (`PROPOSED`)

- **Base Spacing Unit:** `4px` (`0.25rem` scale: `4, 8, 12, 16, 24, 32, 48, 64px`).
- **Max Content Width:** `1280px` centered with `24px` horizontal padding on desktop (`16px` on mobile).
- **Reading Measure:** All plain-language explanation and claim rationale columns are constrained to `65ch` max width.
- **Desktop Layout (`\ge 1024px`):**
  - **2-Column Split Workspace (`7:5` ratio):**
    - **Left Column (`7 cols`):** Mode Switcher (`Learn` vs. `Evaluate`), Unified Input / Category Selector, Confirmation Banner, Plain-Language Synthesis, and Sub-Claim Verdict Cards.
    - **Right Column (`5 cols`, Sticky Inspector):** Source Provenance Cards, Verbatim vs. Paraphrase Viewer, Country Statistics Card, Related Claim Variants, and Meta Model Execution Trace.
- **Tablet & Mobile Layout (`< 1024px`):**
  - Single-column vertical flow. Clicking any inline citation badge (`[D049:P02]`) opens a slide-up **Bottom Sheet Provenance Drawer** so mobile users can verify quotes without losing their reading position.

---

## 6. Navigation & Mode Switching Architecture (`PROPOSED`)

Top navigation remains uncluttered with 4 persistent elements:
1. **Brand Mark & Scope Pill:** `CancerLens` + subtle pill `Informational Evidence Lens • Non-Diagnostic`.
2. **Primary Mode Segmented Control (`role="tablist"`):**
   - Tab 1: **Learn: Browse & Ask** (Category Directory + Guided Q&A)
   - Tab 2: **Evaluate: Assess a Claim** (Text, Screenshot OCR, or Public URL)
3. **Corpus & Rights Status Indicator:** Displays `Admitted Corpus: v2026.10 • P1 Cleared Sources Only` (opens modal listing admitted NCI, CDC, AIHW, StatCan sources and quarantined exclusions).
4. **Budget & Meta Trace Pill:** Live indicator showing `Meta API: Active ($XX.XX remaining)` for hackathon transparency.

---

## 7. Input Interactions, Multimodal Confirmation & Disambiguation (`PROPOSED`)

### 7.1 Learn Mode Input Panel
- **Step 1 — Cancer Entity & Subtype Picker:** Searchable combobox of all 26 audited cancers (`Cancer readiness!A6:A31`), showing a badge next to each (`Full P1 Profile` vs. `Subtype-Split` vs. `Partial / External Link`). Selecting an umbrella cancer (e.g., *Lung Cancer*) reveals a mandatory **Subtype Pill Bar** (`All Lung Overview` | `Non-Small Cell (NSCLC)` | `Small Cell (SCLC)`).
- **Step 2 — Category Grid:** 11 tactile category cards (`Overview`, `Symptoms`, `Risk Factors`, `Prevention`, `Screening`, `Diagnosis`, `Staging`, `Treatment`, `Supportive Care`, `Side Effects`, `Prognosis & Survival`, plus `Terminology Lookup`). Each card displays an instant coverage indicator (`Admitted` vs. `Shared Support` vs. `Coverage Gap`).
- **Step 3 — Natural-Language Question Box:** Optional free-text question input scoped to the selected cancer/category or across all admitted sources.

### 7.2 Evaluate Mode Multimodal Input & Mandatory Confirmation Step
- **Input Method Sub-Tabs:** `Paste Claim Text` | `Upload Screenshot (PNG/JPG/WEBP ≤ 5MB)` | `Public Article URL`.
- **Screenshot Upload Guard & Preview:**
  - Displays explicit microcopy before upload: *"Upload screenshots of articles, headlines, or social posts only. Do not upload photos of skin lesions, scans, lab reports, or personal medical records."*
  - After upload, `/api/v1/extract/image` runs the Meta Vision model and renders the **Extracted Claim Confirmation Card**:
    - Shows thumbnail preview (in browser memory only), OCR confidence indicator, and an **editable `<textarea>`** containing the extracted claim wording.
    - User can fix any OCR typo and click **`Confirm & Evaluate Claim`** (or cancel).
- **Public URL Preview:**
  - After submitting an `https://` URL, `/api/v1/extract/url` displays the fetched page title, domain, and extracted claim sentences inside the same editable confirmation card before evaluation begins.
- **Ambiguous Input Disambiguation Banner:**
  - If a user enters `"HPV vaccine and cervical cancer"` without clear question or claim framing, a non-blocking banner appears:
    - *"Would you like to browse general educational guidance on **Cervical Cancer Prevention & HPV Vaccines (Learn)**, or evaluate a specific claim about the vaccine (**Evaluate**)?"* with two 1-click action buttons.

---

## 8. Results, Evidence Visualization & Verbatim Quote Distinction (`PROPOSED`)

### 8.1 Plain-Language Summary with Inline Citation Chips
- Every substantive sentence ends with a keyboard-focusable citation chip, e.g., `[NCI D049 • §Screening]`.
- Activating a citation chip scrolls/highlights the corresponding **Source Provenance Card** in the right-hand inspector.

### 8.2 Verbatim Quote vs. Paraphrase Card (`SourcePassageCard`)
To satisfy the result contract (` quotes must be permitted and distinguishable from paraphrases; observed source dates separated from retrieval and review dates`):
- **Header:** Source Organization Badge (`NCI Cancer.gov — US01`), Document Title, and Canonical URL link (`target="_blank" rel="noopener noreferrer"`).
- **Body View Toggle:**
  - **Plain-Language Paraphrase (Default):** Rendered in `--font-sans` with label `AI Plain-Language Summary of Passage`.
  - **Exact Verbatim Quote:** Rendered inside a `--bg-subtle` inset box with a `4px solid var(--accent-learn)` left border, `--font-serif` typography, quotation marks, and a verified badge: `✓ Exact Substring Verified against Admitted Snapshot`.
- **Three-Date Provenance Footer (`--font-mono`):**
  - `Observed Source Date: Dec 2, 2025` *(or explicitly `Not stated on source page` if `NULL` — never fabricated)*
  - `Retrieved Snapshot: Oct 28, 2026`
  - `Rights & Review Audit: Oct 16, 2026 (NCI Public Text Policy — Adapted by CancerLens; graphics excluded)`

### 8.3 Context Mismatch Alert Component (`ContextMismatchCallout`)
When evaluating claims in **Evaluate** mode, any detected context mismatch renders as a prominent structured table inside the sub-claim card:

| Dimension | What the Claim Assumes | What the Admitted Evidence Actually Covers | Why This Matters |
| :--- | :--- | :--- | :--- |
| **Study Population / Design** | Human patients with pancreatic cancer | Laboratory cell lines / animal models (*preclinical*) | Compounds that kill cancer cells in a petri dish frequently fail or cause toxicity in human trials. |
| **Screening Target Group** | Average-risk adults over age 40 | High-risk individuals with inherited genetic syndromes (`D080`) | Routine screening in average-risk adults has not been shown to reduce pancreatic cancer mortality and carries false-positive risks. |

---

## 9. Similar Claims Library, Adaptive Experience Learning & Snapshot UI (`PROPOSED`)

### 9.1 "Similar Claims Searched in CancerLens" Panel (`SimilarClaimsPanel` — `FR-14`)
Displayed after every claim evaluation (irrespective of whether the user submitted Text, Screenshot OCR, Voice, or a Public URL):
- **Source of Claims:** Queries `claim_memory_library` (containing pre-seeded reviewed claims + PII-scrubbed, generalized anonymous canonical claims from prior evaluations).
- **Card Content:** Shows up to 4 similar claims with:
  1. Generalized canonical claim text (e.g., *"Pancreatic surveillance imaging for individuals with inherited BRCA2 / familial risk"*).
  2. Non-binary verdict badge (`[⚖ Context-Dependent]`, `[✕ Contradicted]`, `[✓ Supported]`, `[? Insufficient Evidence]`).
  3. Search frequency / memory indicator (`Checked 4 times • Grounded in NCI D080`).
  4. `View Full Evidence Breakdown` 1-click button (loads the cached result at `$0.00` credit cost).
- **Mandatory Anti-Conflation Banner:**
  > **Similar wording does not mean identical evidence.** Small changes in cancer subtype, stage, or target population can completely change the scientific conclusion. Compare each claim independently.
- **Privacy & Anonymization Notice:** `"All claims in this library are automatically stripped of personal details and generalized into anonymous medical assertions before indexing."`

### 9.2 Exact-Match Claim Memory Cache & Consistency Double-Check Banner (`ClaimCacheBanner` — `FR-14`)
When a user searches a claim whose generalized `canonical_claim_hash` already exists in `claim_memory_library` with a matching `corpus_snapshot_hash`:
- **Instant Cache Hit Banner:**
  - `[⚡ Verified Claim Memory Match • 0 API Credits Used • Corpus Hash #a94f26 Verified Current]`
  - Includes a secondary action button: **`Re-Run Live with Meta Muse Wonder (~$0.015 est.)`** which executes a fresh live investigation and displays a **`[✓ Consistency Double-Check Passed: Live Run Matches Stored Verdict]`** badge.

### 9.3 Adaptive Experience Learning UI (`ExperienceLearningCallout` — `FR-19` Mechanisms A & B)
1. **Mechanism A Badge (`Search & Synonym Learning`):**
   - When a query benefits from a previously learned lay-to-medical search bridge in `learned_query_mappings` (e.g., mapping *"chemo brain"* $\rightarrow$ *"cancer-related cognitive impairment [D139]"* on Hop 1), the Execution Trace displays:
     `[🧠 Experience Memory Applied: Used learned NCI search mapping ('chemo brain' → 'cognitive problems') — Resolved in 1 Hop]`.
2. **Mechanism B Card (`Cross-Mode Misconception Enrichment`):**
   - In both **Learn** and **Evaluate** modes, if `claim_memory_library` contains verified claims for the active `(cancer_id, category_slug)`, a collapsible card appears below the main summary:
     - **Header:** `Common Claims & Clarifications Checked in This Topic (From CancerLens Memory)`
     - **Body:** Lists 2–3 frequently checked claims in that category alongside their verified NCI-grounded outcomes.

### 9.4 Versioned Saved Results Banner (`SavedSnapshotBanner` — `FR-13`)
- When viewing a saved evaluation URL (`/saved/{result_id}?v=1`), a top banner states:
  - `Viewing Historical Snapshot v1 • Generated Oct 30, 2026 against Corpus Hash #a94f26 • 0 API Credits Used on Reload`.
  - If the underlying corpus has been updated or revoked since `v1`, a warning badge states `Corpus Updated Since Snapshot`.
  - An explicit button **`Re-evaluate Against Current Corpus (~$0.015 est.)`** allows the user to create `v2` and view a side-by-side diff of any changed evidence or outcomes.

---

## 10. Loading, Empty, Coverage Gap & Error States (`PROPOSED`)

1. **Progressive Investigator Loading State (`aria-live="polite"`):**
   - Instead of a generic spinner, displays the real-time bounded steps (without exposing raw chain-of-thought):
     - `[1/5] Checking input safety & Claim Memory Library...`
     - `[2/5] Applying learned NCI synonym mappings & decomposing claim...`
     - `[3/5] Searching admitted NCI, CDC, AIHW & StatCan passages...`
     - `[4/5] Verifying exact quotes and checking context mismatches...`
     - `[5/5] Updating Experience Memory & matching Similar Claims...`
2. **Honest Coverage Gap State (`CORPUS_COVERAGE_GAP`):**
   - Displays `[∅] Not in Admitted CancerLens Collection`.
   - Microcopy: *"CancerLens currently does not have an admitted, rights-cleared passage for **[Cancer / Section]**. Important: Missing coverage in this curated collection does not mean medical evidence does not exist. You can consult the official National Cancer Institute page directly at [Canonical URL]."*
3. **Medical Boundary Refusal State (`OUT_OF_SCOPE_CLINICAL`):**
   - Displays `[!] Personal Medical Advice — Out of Scope`.
   - Microcopy: *"CancerLens is an informational evidence tool and cannot evaluate personal symptoms, interpret medical scans or skin lesions, or recommend individual treatments or dosages. Please consult a qualified healthcare professional. If you want general educational information, explore these admitted topics:"* followed by safe category links.

---

## 11. Text Wireframes (`PROPOSED`)

### 11.1 Desktop Split-Screen Wireframe — Evaluate Mode (Compound Claim + Similar Claims + Experience Memory)
```text
+--------------------------------------------------------------------------------------------------+
| [CancerLens] Informational Evidence Lens       ( Learn: Browse & Ask | *Evaluate: Assess Claim* ) |
| Admitted Corpus: v2026.10 (P1 Cleared)                          Meta API Trace: Active ($142.10) |
+--------------------------------------------------------------------------------------------------+
| LEFT WORKSPACE (7 COLS)                         | RIGHT EVIDENCE INSPECTOR (5 COLS - STICKY)     |
|                                                 |                                                |
| [Text Claim] [Screenshot OCR] [Public URL] [Mic]| SOURCE PROVENANCE & VERBATIM QUOTES            |
| +---------------------------------------------+ | +--------------------------------------------+ |
| | "Annual pancreatic CT scans save everyone   | | | [D080:P01] NCI — Pancreatic Cancer         | |
| |  over 40, and high-dose Vitamin C cures     | | | Screening (US01 • Admitted)                | |
| |  pancreatic cancer without chemo."          | | | [Paraphrase] [*Exact Verbatim Quote*]      | |
| +---------------------------------------------+ | | "Screening tests for pancreatic cancer     | |
| [Decompose & Evaluate Claim]                    | |  have not been shown to reduce the risk    | |
|                                                 | |  of dying from the disease in the general  | |
| INTERPRETED INPUT: 2 Atomic Sub-Claims Found    | |  population..."                            | |
|                                                 | | ✓ Substring verified against snapshot      | |
| +---------------------------------------------+ | |--------------------------------------------| |
| | SUB-CLAIM 1                                 | | | Observed Source Date : Aug 3, 2026         | |
| | "Routine annual CT screening reduces        | | | Retrieved Snapshot   : Oct 28, 2026        | |
| |  pancreatic cancer mortality in average-    | | | Rights Audit Date    : Oct 16, 2026        | |
| |  risk adults over 40."                      | | | Attribution: Adapted from NCI (Public)     | |
| |                                             | | +--------------------------------------------+ |
| | [✕ CONTRADICTED BY ADMITTED EVIDENCE]       | |                                                |
| |                                             | | SIMILAR CLAIMS SEARCHED IN CANCERLENS          |
| | Plain-Language Explanation:                 | | ! Note: Similar wording can have different     |
| | Admitted NCI screening evidence states that | |   meaning, evidence, and clinical outcomes.    |
| | general-population pancreatic screening has | | • "Pancreatic surveillance for individuals     |
| | not been shown to reduce mortality [D080].  | |    with inherited BRCA2 / familial risk"       |
| |                                             | |   -> [⚖ Context-Dependent] (View Breakdown)    |
| | ! CONTEXT MISMATCH DETECTED:                | | • "CA 19-9 blood test screens healthy adults   |
| | • Claim Target : General population > 40    | |    for early pancreatic cancer"                |
| | • Evidence Scope: Surveillance studied only | |   -> [✕ Contradicted by D080] (View Breakdown) |
| |   in high-risk genetic/familial cohorts.    | |                                                |
| +---------------------------------------------+ | META MODEL API & LEARNING TRACE (REDACTED)     |
|                                                 | • Router/Sanitizer: Muse Spark (310ms)         |
|                                                 | • Investigator    : Muse Wonder (1,480ms)      |
|                                                 | • Memory Learned  : +1 Synonym Bridge, +1 Claim|
|                                                 | • Session Cost    : $0.0138 USD ($150 Meta API)|
+--------------------------------------------------------------------------------------------------+
```

### 11.2 Mobile Single-Column Wireframe — Screenshot Confirmation & Bottom-Sheet Quote
```text
+-----------------------------------------------+
| [CancerLens]             [Learn] [*Evaluate*] |
+-----------------------------------------------+
| UPLOAD INFORMATIONAL SCREENSHOT               |
| [x] social_post_claim.png (412 KB)            |
| ! Do not upload skin lesions or medical scans |
|                                               |
| REVIEW & EDIT EXTRACTED TEXT BEFORE ASSESSING |
| (OCR Confidence: High — 1 uncertain word)     |
| +-------------------------------------------+ |
| | "Baking soda stops breast cancer tumors   | |
| |  from growing in patients."               | |
| +-------------------------------------------+ |
| [Cancel]         [*Confirm & Evaluate Claim*] |
+-----------------------------------------------+
| SUB-CLAIM 1 RESULT                            |
| [? INSUFFICIENT EVIDENCE IN COLLECTION]       |
| Reason: Admitted NCI breast cancer treatment  |
| passages [D037] do not support sodium         |
| bicarbonate as a human cancer treatment.      |
|                                               |
| Tap citation to inspect source: [NCI D037:P4] |
+-----------------------------------------------+
| === SLIDE-UP PROVENANCE DRAWER (ACTIVE) ===   |
| Source: Treatment for Breast Cancer - NCI     |
| URL   : https://www.cancer.gov/types/breast/..|
| Observed Date : Not stated on source page     |
| Retrieved Date: Oct 28, 2026                  |
| [Close Drawer]                                |
+-----------------------------------------------+
```

---

## 12. Accessibility Target & Testable Verification Checks (`NFR-04`)

> [!NOTE]
> CancerLens targets **WCAG 2.2 Level AA** design and engineering criteria as a proposed quality target (`PROPOSED`). We do not claim formal third-party accessibility certification.

| Check ID | Accessibility Requirement | Testable Engineering Rule |
| :--- | :--- | :--- |
| `A11Y-01` | **Non-Color-Only Outcomes** | Every verdict badge (`SUPPORTED`, `CONTRADICTED`, `MIXED_OR_CONTEXT_DEPENDENT`, `INSUFFICIENT_EVIDENCE`, `OUT_OF_SCOPE_CLINICAL`) renders an SVG icon with `aria-hidden="true"` plus a visible text label and distinct border style. |
| `A11Y-02` | **Keyboard Navigation & Focus Order** | All mode tabs (`role="tablist"`), category pills, citation chips (`<button>`), and drawer controls are reachable via `Tab`/`Shift+Tab` and `Enter`/`Space`, with `2px solid var(--border-focus)` visible outline. Modal/drawer traps focus and closes on `Escape`. |
| `A11Y-03` | **Screen Reader Status Announcements** | Investigator step progression, OCR completion, and validation errors use `aria-live="polite"` (or `role="alert"` for boundary refusals) so screen-reader users hear state transitions without focus hijacking. |
| `A11Y-04` | **Contrast & Zoom Resilience** | Automated axe-core / Playwright check verifies $\ge 4.5:1$ text contrast across light/dark themes and zero horizontal scroll clipping at `200%` browser zoom (`320px` CSS viewport width). |
| `A11Y-05` | **Form & Confirmation Labeling** | Every input, file dropzone, and editable OCR confirmation `<textarea>` has an explicit programmatic `<label>` and `aria-describedby` pointing to boundary/privacy microcopy. |

---

## 13. Decisions, Open Questions & References

- **Key Decisions Captured:**
  - Use warm editorial surfaces (`#FAF9F5`) and serif blockquotes (`--font-serif`) to visually separate verbatim source evidence from AI plain-language explanations.
  - Require an explicit user confirmation step on all OCR/URL extractions before running multi-model evaluation.
  - Enforce a 5-state non-binary outcome badge system with zero percentage confidence bars.
- **Open Questions:** Whether to include an optional dyslexia-friendly font toggle in the header (deferred to `P2` polish).
- **References:**
  - W3C WCAG 2.2 Quick Reference: `https://www.w3.org/WAI/WCAG22/quickref/`
  - NCI Reuse & Attribution Guidelines (`US01`/`US02`): `https://www.cancer.gov/policies/copyright-reuse`
