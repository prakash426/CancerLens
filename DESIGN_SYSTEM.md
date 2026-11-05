# CancerLens — Design System & Creative UX Specification (`DESIGN_SYSTEM.md`)

**Status:** APPROVED ARCHITECTURE & INTERACTIVE LENS DESIGN (November 2, 2026)  
**Implemented Stack (Option 2):** Zero-Dependency Modern HTML5 / CSS3 / Vanilla JS (`frontend/index.html`, `frontend/css/styles.css`, `frontend/js/data.js`, `frontend/js/app.js`) + View Transitions API

---

## 1. Purpose & Core Aesthetic Philosophy
Build a calm, high-precision clinical & research discovery workspace inspired by the `CancerInfo API` / `Cancer Compass` interface that lets users explore oncology topics and inspect health claims without anxiety or false clinical authority.
- **No Traditional Static Tab Wall:** Instead of isolating `Learn` and `Evaluate` into disconnected page tabs, CancerLens centers around a tactile **Two-Card Mode Selector & Interactive Focal Lens Switcher** (`Mode A: Explore & Learn` $\leftrightarrow$ `Mode B: Verify & Evaluate`) paired with a unified search/claim input bar and `Easy to Understand` / `Research & Provenance View` density toggle.
- **WHO Permission `202610792` (Clauses 3 & 6) Visual Integrity:** Every response structurally and typographically separates **AI-Generated Plain-Language Explanations** (explicitly badged as authored by CancerLens AI) from **Attributed `Cancer Info API` Facts & Limited Verbatim Quotations** (rendered in editorial serif callouts with publisher attribution, original source URL, and non-endorsement notice). Never display the WHO emblem/logo.

---

## 2. Color Tokens & Typography (Midnight-Navy Default + Warm Alabaster Light Theme)
- **Primary Dark Canvas (`CancerInfo API` / `Cancer Compass` Aesthetic — Default):**
  - Deep Midnight-Navy Canvas: `#060b14`
  - Surface Cards & Panels: `#0b1220` / `#10192b` with subtle slate borders `#1e2d45`
  - Elevated Glass Header: `rgba(6, 11, 20, 0.88)` with `backdrop-filter: blur(12px)`
- **Secondary Light Theme (`#FAF9F5` Editorial Toggle):**
  - Warm Alabaster Canvas: `#FAF9F5`, Pure Surface Cards `#FFFFFF`, Deep Slate Ink `#17212B`
- **Typography:**
  - **Sans-Serif (`Inter` / `Plus Jakarta Sans`):** Used for UI controls, navigation, and **AI-Generated Plain-Language Explanations**.
  - **Editorial Serif (`Newsreader`):** Reserved exclusively for **Verbatim Source Excerpts** from `Cancer Info API`.
  - **Monospace (`JetBrains Mono`):** Used for `fact_id` / `document_id` badges, Stage-4 provenance verification status, and Dual-Pool Credit Telemetry (`$150` Meta Model API + `$100` Baseten Model API).
- **Semantic Outcome Tokens (Always Paired with Icon + Text Label — Never Color Alone):**
  - **Mode A (`Explore & Learn`) Focal Accent:** Clinical Emerald-Teal `#10b981` (light mode `#12675F`)
  - **Mode B (`Verify & Evaluate`) Focal Accent:** Provenance Sky-Blue `#38bdf8` (light mode `#2B4C7E`)
  - **`SUPPORTED`:** Emerald `#10b981` / `#15803D`
  - **`MIXED_OR_CONTEXT_DEPENDENT`:** Warm Amber `#f59e0b` / `#B45309`
  - **`CONTRADICTED`:** Crimson-Coral `#ef4444` / `#B91C1C`
  - **`INSUFFICIENT_EVIDENCE` (`CORPUS_COVERAGE_GAP`):** Neutral Slate `#94a3b8` / `#475569`
  - **`OUT_OF_SCOPE_CLINICAL`:** Protective Violet `#a855f7` / `#6D28D9`

---

## 3. Signature UX Pattern: The Interactive Focal Lens Switcher

Instead of separate pages or dead tabs, the top of the workspace features the **Unified Discovery & Verification Command Card**:

1. **Two-Card Mode Selector (`Mode A: Explore & Learn` vs. `Mode B: Verify & Evaluate`):**
   - Driven by View Transitions API morphing and keyboard hotkey (`Cmd/Ctrl + L`).
   - Switching the lens deterministically locks `resolved_mode` (`LEARN` vs. `EVALUATE`, `SG-06`) in the payload sent to the backend and smoothly morphs the command canvas underneath:
     - **In `Explore & Learn` Focus (`Mode A`):** Reveals the **25-Cancer Searchable Selector** (20 common + 5 rare, with Subtype pills when relevant), the **12-Category Clinical Bento Strip** (showing `Covered`, `Partial`, or `Coverage Gap` badges), and a natural-language search bar.
     - **In `Verify & Evaluate` Focus (`Mode B`):** Morphs into the **Multimodal Claim Inspection Canvas** supporting **Direct Text (`TEXT`)**, **Screenshot OCR (`IMAGE_OCR`)**, and **SSRF-Guarded Public URL (`URL_EXTRACT`)** (voice input is out of scope per `D11`), paired with an **Inline Confirmation Drawer** where the user reviews/edits extracted text before clicking **"Confirm & Evaluate"** (`SG-01`).
2. **"Pivot-in-Place" Cross-Mode Bridges:**
   - **From `Learn` $\rightarrow$ `Evaluate`:** Clicking any **Common Public Claim** (Mechanism B) inside a `Learn` category card smoothly flips the Focal Lens Switch to `Verify & Evaluate` and loads that claim's full **5D Context-Mismatch Dossier** and Stage-4 provenance verification badge without losing scroll context.
   - **From `Evaluate` $\rightarrow$ `Learn`:** Every `Evaluate` verdict card includes an **"Explore Underlying Biology in Learn Lens $\rightarrow$"** chip that flips the Focal Lens Switch back to `Explore & Learn` anchored to that exact cancer type, subtype, and category.

---

## 4. Two-Column Desktop Split & Evidence Inspector (`Clause 3 & Clause 6`)

- **Left Column (60% width on Desktop) — Primary Workspace & Dossier:**
  - Displays the active Focal Lens canvas, 6-stage deterministic progress stepper (`INPUT_PARSED` $\rightarrow$ `DISPLAYABLE`), AI-generated plain-language synthesis (explicitly badged `"AI-Generated Plain-Language Summary — Authored by CancerLens AI"`), **11-Category Bento Cards** (in `Learn`), or **Atomic Claim Verdict Cards + 5D Context-Mismatch Matrix** (`cancer_and_subtype`, `population_and_stage`, `study_design`, `endpoint_measured`, `caveat_or_dose` in `Evaluate`).
- **Right Column (40% width on Desktop, Accessible Slide-Over Sheet on Mobile) — Sticky Provenance & Rights Inspector:**
  - Synchronizes with hovered or clicked inline citation pills (`[WHO-BC-01]`, `[NCI-LC-04]`).
  - Displays:
    1. **Structured Consensus Facts** from `Cancer Info API`.
    2. **Limited Verbatim Excerpt** in editorial serif (`Newsreader`) with an `"Exact Verified Excerpt"` badge (verified by Stage-4 Python substring check).
    3. **3 Separated Dates:** `observed_source_date` (`null` $\rightarrow$ *"Not stated on source page"*), `retrieved_at_utc`, and `reviewed_at_date`.
    4. **Claim Verification Telemetry:** Provider/model badge (`meta-models/muse-spark-open-1026` on Baseten / `muse-spark-1.3` on Meta) + optional **1-Click "Run Live Consistency Double-Check"** button (`FR-07`).
    5. **Mandatory WHO Clause 3 Attribution & Original Source Link** + non-endorsement notice.

---

## 5. Accessibility (`WCAG 2.2 AA` Targets)
- Every outcome badge pairs **Icon + Text Label + Border Pattern** (never color alone).
- Full keyboard navigation (`Tab`, `ArrowLeft`/`ArrowRight` on the Focal Lens Switcher, `Escape` on drawers/modals, `Cmd/Ctrl + L` shortcut).
- Minimum `4.5:1` contrast ratio on all body text and `16px` (`1rem`) base reading size with `65ch` measure.
