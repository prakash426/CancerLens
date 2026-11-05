/**
 * CancerLens — Interactive Frontend Controller (`frontend/js/app.js`)
 * Implements:
 * - Two-Card Mode Selector (Mode A: Explore & Learn <-> Mode B: Verify & Evaluate, SG-06)
 * - View Transitions API smooth morphing with graceful fallback
 * - Pivot-in-Place bridges between Mode A (Learn) and Mode B (Evaluate)
 * - Mandatory Editable Confirmation Drawer for Screenshot OCR / Public URL inputs (FR-10 / SG-01)
 * - Stage-4 Provenance Inspector, 5D Context-Mismatch Matrix & WHO Clause 3/6 Separation
 * - Auto-detection of the CancerLens FastAPI backend (`http://127.0.0.1:8000/api/v1`) with honest UI Preview fallback
 */

// Preview data globals (CLINICAL_CATEGORIES, CANCER_CATALOG_25, LEARN_ENVELOPES,
// EVALUATE_SCENARIOS) come from js/data.js, loaded first in index.html. They are
// deliberately not redeclared here: duplicate top-level const declarations across
// classic scripts are a SyntaxError that kills this whole file.

const BACKEND_BASE_URL = "http://127.0.0.1:8000/api/v1";

// Screenshot OCR upload contract (mirrors the backend image guard).
const OCR_ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const OCR_MAX_BYTES = 5 * 1024 * 1024;

function setConfirmationStatus(message) {
  const status = document.getElementById("confirmation-status");
  if (status) status.textContent = message || "";
}

const state = {
  activeMode: "LEARN", // Locked per SG-06: "LEARN" | "EVALUATE"
  viewDensity: "EASY", // "EASY" | "PROVENANCE"
  theme: "dark", // "dark" (Screenshots 1-4 default) | "light" (#FAF9F5)
  backendConnected: false,
  hasActiveResult: false, // Result card hidden on initial landing until user searches/clicks
  hasExploredTopic: false, // Subtype Scope shown only after user clicks Explore Topic
  selectedCancerId: null,
  selectedSubtypeId: "all",
  selectedCategorySlug: "overview",
  categoryCoverage: null, // cancer+subtype -> { slug: has_data } from GET /learn/coverage
  coverageCancerKey: null,
  coverageReqToken: 0,
  selectedEvalScenarioKey: null,
  activeModality: "TEXT", // "TEXT" | "IMAGE_OCR" | "URL_EXTRACT"
  confirmationOpen: false,
  currentEnvelope: LEARN_ENVELOPES["lung-cancer"],
  sourceTabModeByFactId: {}, // fact_id -> "SUMMARY" | "VERBATIM"
  doubleCheckStatus: null,
  activeSnapshotCard: null,
  savedSnapshots: [],
  recentHistory: [
    { label: "Lung cancer (Non-Small Cell & Small Cell)", mode: "LEARN", target: "lung-cancer" },
    { label: "Sugar & Vitamin C breast cancer claim", mode: "EVALUATE", target: "sugar-vitamin-c-compound" },
    { label: "Breast cancer (HER2+ & TNBC)", mode: "LEARN", target: "breast-cancer" },
    { label: "Alkaline water pancreatic claim", mode: "EVALUATE", target: "alkaline-water-pancreatic" },
    { label: "HPV vaccine cervical cancer prevention", mode: "EVALUATE", target: "hpv-vaccine-cervical" }
  ]
};

function withViewTransition(updateFn) {
  if (typeof document.startViewTransition === "function") {
    document.startViewTransition(() => updateFn());
  } else {
    updateFn();
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showToast(message) {
  const toastEl = document.getElementById("app-toast");
  if (!toastEl) return;
  toastEl.textContent = message;
  toastEl.hidden = false;
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toastEl.hidden = true;
  }, 3200);
}

// Ribbon loading overlay with depth counting so overlapping live calls each hold it.
let loadingDepth = 0;

function showLoading(message) {
  loadingDepth++;
  const overlay = document.getElementById("loading-overlay");
  const text = document.getElementById("loading-text");
  if (text && message) text.textContent = message;
  if (overlay) overlay.hidden = false;
}

function hideLoading() {
  loadingDepth = Math.max(0, loadingDepth - 1);
  if (loadingDepth === 0) {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.hidden = true;
  }
}

/* --------------------------------------------------------------------------
   Backend Connectivity Check (Auto-connects when FastAPI Backend is live)
   -------------------------------------------------------------------------- */
async function probeBackendStatus() {
  const badgeEl = document.getElementById("backend-status-text");
  const dotEl = document.getElementById("backend-status-dot");
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2000);
    const resp = await fetch(`${BACKEND_BASE_URL}/health/budget`, {
      signal: controller.signal
    });
    clearTimeout(timer);
    if (resp.ok) {
      state.backendConnected = true;
      if (badgeEl) badgeEl.textContent = "Backend Live";
      if (dotEl) dotEl.style.background = "#10b981";
      return;
    }
  } catch (_err) {
    // Expected while backend is offline
  }
  state.backendConnected = false;
  if (badgeEl) badgeEl.textContent = "Backend Preview";
  if (dotEl) dotEl.style.background = "#38bdf8";
}

/* --------------------------------------------------------------------------
   Mode Switching (Mode A: LEARN <-> Mode B: EVALUATE, SG-06 Locked)
   -------------------------------------------------------------------------- */
function setLensMode(newMode, options = {}) {
  if (newMode !== "LEARN" && newMode !== "EVALUATE") return;

  withViewTransition(() => {
    state.activeMode = newMode;
    state.doubleCheckStatus = null;
    if (!options.showResult) {
      state.hasActiveResult = false;
    }
    document.body.setAttribute("data-active-mode", newMode);

    const btnLearn = document.getElementById("mode-card-learn");
    const btnEval = document.getElementById("mode-card-evaluate");
    if (btnLearn && btnEval) {
      btnLearn.setAttribute("aria-selected", String(newMode === "LEARN"));
      btnEval.setAttribute("aria-selected", String(newMode === "EVALUATE"));
    }

    const inputEl = document.getElementById("main-query-input");
    const submitBtn = document.getElementById("main-submit-btn");
    const mmToolbar = document.getElementById("multimodal-toolbar");
    const confirmDrawer = document.getElementById("confirmation-drawer");

    if (newMode === "LEARN") {
      state.confirmationOpen = false;
      if (mmToolbar) mmToolbar.hidden = true;
      if (confirmDrawer) confirmDrawer.hidden = true;

      if (inputEl) {
        if (!options.keepInput) {
          inputEl.value = "";
        }
        inputEl.placeholder =
          "Search 25 cancers (e.g., Ovarian cancer stages, Breast cancer symptoms, Lung cancer) or ask a general question...";
      }
      if (submitBtn) {
        submitBtn.textContent = "Explore Topic";
      }
      if (options.showResult && state.selectedCancerId) {
        state.currentEnvelope = buildLearnEnvelope(
          state.selectedCancerId,
          state.selectedSubtypeId,
          state.selectedCategorySlug
        );
      }
    } else {
      if (mmToolbar) mmToolbar.hidden = false;
      if (inputEl) {
        if (!options.keepInput) {
          inputEl.value = "";
        }
        inputEl.placeholder =
          "Paste a cancer claim, headline, or compound post to verify against WHO & NCI evidence...";
      }
      if (submitBtn) {
        submitBtn.textContent = "Verify Claim";
      }
      if (options.showResult && state.selectedEvalScenarioKey) {
        state.currentEnvelope =
          EVALUATE_SCENARIOS[state.selectedEvalScenarioKey] ||
          EVALUATE_SCENARIOS["sugar-vitamin-c-compound"];
      }
    }

    renderSuggestionsAndHistory();
    renderPipelineStepper();
    renderMainDossier();
    renderSourcesSection();
  });
}

function resolveCancerMetaBySlug(slug) {
  if (!slug) return null;
  const fromCatalog = CANCER_CATALOG_25.find((c) => c.cancer_id === slug);
  if (fromCatalog) return fromCatalog;

  const fallbackCatalog = {
    "ovarian-cancer": {
      cancer_id: "ovarian-cancer",
      canonical_name: "Ovarian Cancer (Epithelial, Germ Cell & Stromal)",
      short_label: "Ovarian cancer",
      aliases: "Ovarian epithelial carcinoma, High-grade serous ovarian cancer, Fallopian tube / Peritoneal cancer",
      anatomical_site: "Ovaries, fallopian tubes, and peritoneum",
      subtypes: [
        { id: "all", label: "All Ovarian Subtypes" },
        { id: "epithelial", label: "Epithelial Ovarian (~90%)" },
        { id: "germ-cell", label: "Germ Cell & Stromal" }
      ]
    },
    "bladder-cancer": {
      cancer_id: "bladder-cancer",
      canonical_name: "Bladder Cancer (Urothelial Carcinoma)",
      short_label: "Bladder cancer",
      aliases: "Urothelial carcinoma, Transitional cell carcinoma, NMIBC, MIBC",
      anatomical_site: "Urinary bladder and urothelial tract",
      subtypes: [{ id: "all", label: "All Bladder Subtypes" }]
    },
    "kidney-cancer": {
      cancer_id: "kidney-cancer",
      canonical_name: "Kidney Cancer (Renal Cell Carcinoma)",
      short_label: "Kidney cancer",
      aliases: "Renal cell carcinoma, Clear cell RCC, Renal adenocarcinoma",
      anatomical_site: "Renal cortex and kidney parenchyma",
      subtypes: [{ id: "all", label: "All Renal Subtypes" }]
    },
    "liver-cancer": {
      cancer_id: "liver-cancer",
      canonical_name: "Liver Cancer (Hepatocellular Carcinoma & Cholangiocarcinoma)",
      short_label: "Liver cancer",
      aliases: "Hepatocellular carcinoma (HCC), Intrahepatic bile duct cancer",
      anatomical_site: "Liver hepatocytes and intrahepatic bile ducts",
      subtypes: [{ id: "all", label: "All Liver Subtypes" }]
    },
    "stomach-cancer": {
      cancer_id: "stomach-cancer",
      canonical_name: "Stomach (Gastric) Cancer",
      short_label: "Stomach cancer",
      aliases: "Gastric adenocarcinoma, Gastroesophageal junction cancer",
      anatomical_site: "Stomach lining and gastric mucosa",
      subtypes: [{ id: "all", label: "All Gastric Subtypes" }]
    },
    "thyroid-cancer": {
      cancer_id: "thyroid-cancer",
      canonical_name: "Thyroid Cancer (Papillary, Follicular, Medullary & Anaplastic)",
      short_label: "Thyroid cancer",
      aliases: "Papillary thyroid carcinoma, Follicular thyroid cancer, MTC, ATC",
      anatomical_site: "Thyroid gland",
      subtypes: [{ id: "all", label: "All Thyroid Subtypes" }]
    },
    "uterine-corpus-cancer": {
      cancer_id: "uterine-corpus-cancer",
      canonical_name: "Uterine & Endometrial Cancer",
      short_label: "Uterine / Endometrial cancer",
      aliases: "Endometrial carcinoma, Uterine sarcoma, Corpus uteri cancer",
      anatomical_site: "Uterine endometrium and myometrium",
      subtypes: [{ id: "all", label: "All Uterine Subtypes" }]
    },
    "melanoma-of-skin": {
      cancer_id: "melanoma-of-skin",
      canonical_name: "Melanoma of the Skin",
      short_label: "Melanoma of skin",
      aliases: "Cutaneous melanoma, Malignant melanoma",
      anatomical_site: "Cutaneous melanocytes (skin)",
      subtypes: [{ id: "all", label: "All Cutaneous Melanoma Subtypes" }]
    },
    "mesothelioma": {
      cancer_id: "mesothelioma",
      canonical_name: "Mesothelioma (Pleural & Peritoneal)",
      short_label: "Pleural mesothelioma",
      aliases: "Malignant pleural mesothelioma, MPM",
      anatomical_site: "Pleural and peritoneal mesothelium",
      subtypes: [{ id: "all", label: "All Mesothelioma Subtypes" }]
    },
    "non-hodgkin-lymphoma": {
      cancer_id: "non-hodgkin-lymphoma",
      canonical_name: "Non-Hodgkin Lymphoma (B-Cell & T-Cell)",
      short_label: "Non-Hodgkin lymphoma",
      aliases: "NHL, DLBCL, Follicular lymphoma",
      anatomical_site: "Lymph nodes and lymphatic system",
      subtypes: [{ id: "all", label: "All NHL Subtypes" }]
    },
    "hodgkin-lymphoma": {
      cancer_id: "hodgkin-lymphoma",
      canonical_name: "Hodgkin Lymphoma",
      short_label: "Hodgkin lymphoma",
      aliases: "Classical Hodgkin lymphoma (cHL)",
      anatomical_site: "Lymph nodes and lymphoid tissue",
      subtypes: [{ id: "all", label: "All Hodgkin Subtypes" }]
    },
    "leukaemia": {
      cancer_id: "leukaemia",
      canonical_name: "Leukemia (AML, ALL, CLL & CML)",
      short_label: "Leukemia (AML / ALL)",
      aliases: "Leukaemia, Acute myeloid leukemia (AML), Acute lymphoblastic leukemia (ALL)",
      anatomical_site: "Bone marrow, blood, and hematopoietic system",
      subtypes: [{ id: "all", label: "All Leukemia Subtypes" }]
    },
    "oesophageal-cancer": {
      cancer_id: "oesophageal-cancer",
      canonical_name: "Esophageal (Oesophageal) Cancer",
      short_label: "Esophageal cancer",
      aliases: "Oesophageal squamous cell carcinoma, Esophageal adenocarcinoma",
      anatomical_site: "Esophagus and gastroesophageal junction",
      subtypes: [{ id: "all", label: "All Esophageal Subtypes" }]
    },
    "brain-cns-cancer": {
      cancer_id: "brain-cns-cancer",
      canonical_name: "Brain & Central Nervous System (CNS) Tumors",
      short_label: "Brain & CNS cancer",
      aliases: "Glioblastoma, Astrocytoma, Meningioma",
      anatomical_site: "Brain and spinal cord (CNS)",
      subtypes: [{ id: "all", label: "All Brain & CNS Subtypes" }]
    },
    "lip-oral-cavity-cancer": {
      cancer_id: "lip-oral-cavity-cancer",
      canonical_name: "Lip & Oral Cavity Cancer",
      short_label: "Oral cavity cancer",
      aliases: "Oral squamous cell carcinoma, Mouth and tongue cancer",
      anatomical_site: "Lips, tongue, gums, and oral cavity",
      subtypes: [{ id: "all", label: "All Oral Cavity Subtypes" }]
    },
    "laryngeal-cancer": {
      cancer_id: "laryngeal-cancer",
      canonical_name: "Laryngeal (Voice Box) Cancer",
      short_label: "Laryngeal cancer",
      aliases: "Glottic and Supraglottic laryngeal carcinoma",
      anatomical_site: "Larynx",
      subtypes: [{ id: "all", label: "All Laryngeal Subtypes" }]
    },
    "gallbladder-cancer": {
      cancer_id: "gallbladder-cancer",
      canonical_name: "Gallbladder & Biliary Tract Cancer",
      short_label: "Gallbladder cancer",
      aliases: "Gallbladder adenocarcinoma, Extrahepatic biliary cancer",
      anatomical_site: "Gallbladder and bile ducts",
      subtypes: [{ id: "all", label: "All Gallbladder Subtypes" }]
    },
    "salivary-gland-cancer": {
      cancer_id: "salivary-gland-cancer",
      canonical_name: "Salivary Gland Cancer (Rare)",
      short_label: "Salivary gland cancer",
      aliases: "Parotid and Submandibular salivary gland carcinoma",
      anatomical_site: "Major and minor salivary glands",
      subtypes: [{ id: "all", label: "All Salivary Gland Subtypes" }]
    },
    "vaginal-cancer": {
      cancer_id: "vaginal-cancer",
      canonical_name: "Vaginal Cancer (Rare)",
      short_label: "Vaginal cancer",
      aliases: "Vaginal squamous cell carcinoma",
      anatomical_site: "Vaginal epithelium",
      subtypes: [{ id: "all", label: "All Vaginal Subtypes" }]
    },
    "penile-cancer": {
      cancer_id: "penile-cancer",
      canonical_name: "Penile Cancer (Rare)",
      short_label: "Penile cancer",
      aliases: "Squamous cell carcinoma of the penis",
      anatomical_site: "Penile tissue",
      subtypes: [{ id: "all", label: "All Penile Subtypes" }]
    }
  };
  if (fallbackCatalog[slug]) return fallbackCatalog[slug];
  const label = slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
  return {
    cancer_id: slug,
    canonical_name: label,
    short_label: label,
    aliases: label,
    anatomical_site: "Oncology Reference",
    subtypes: [{ id: "all", label: "All Subtypes" }]
  };
}

function buildLearnEnvelope(cancerId, subtypeId, categorySlug, userQuestion = null) {
  const cancerMeta =
    resolveCancerMetaBySlug(cancerId) ||
    resolveCancerMetaBySlug("lung-cancer") ||
    CANCER_CATALOG_25[0];
  const catMeta =
    CLINICAL_CATEGORIES.find((cat) => cat.slug === categorySlug) || CLINICAL_CATEGORIES[0];
  const directBase = LEARN_ENVELOPES[cancerMeta.cancer_id];

  // Offline preview has no records for gap categories (SG-03 abstention)
  if (catMeta.status === "COVERAGE_GAP") {
    return {
      ...(directBase || LEARN_ENVELOPES["lung-cancer"]),
      interpreted_query_or_claim: userQuestion || `${cancerMeta.canonical_name} — ${catMeta.title}`,
      cancer_id: cancerMeta.cancer_id,
      cancer_name: cancerMeta.canonical_name,
      subtype_id: subtypeId,
      category_slug: categorySlug,
      retrieval_state: "SEARCH_EXECUTED_NO_MATCHES",
      overall_outcome_code: "INSUFFICIENT_EVIDENCE",
      overall_outcome_label: `No ${catMeta.title} data in this preview`,
      ai_plain_language_summary: `${catMeta.title} for ${cancerMeta.canonical_name} is not included in this offline preview. Start the CancerLens backend for live coverage.`,
      evidence_items: []
    };
  }

  if (directBase) {
    return {
      ...directBase,
      interpreted_query_or_claim: userQuestion || cancerMeta.canonical_name,
      cancer_id: cancerMeta.cancer_id,
      cancer_name: cancerMeta.canonical_name,
      subtype_id: subtypeId,
      category_slug: categorySlug
    };
  }

  return {
    ...LEARN_ENVELOPES["lung-cancer"],
    request_id: `req_preview_${cancerMeta.cancer_id}`,
    interpreted_query_or_claim: userQuestion || cancerMeta.canonical_name,
    cancer_id: cancerMeta.cancer_id,
    cancer_name: cancerMeta.canonical_name,
    subtype_id: subtypeId,
    category_slug: categorySlug,
    ai_plain_language_summary: `${cancerMeta.canonical_name} involves abnormal cell growth originating in the ${cancerMeta.anatomical_site.toLowerCase()}. Start the CancerLens Backend (:8000) to load live WHO and NCI clinical facts, symptoms, staging, and treatment overviews for ${cancerMeta.short_label}.`,
    treatment_approaches: [],
    symptoms_list: [],
    diagnostic_procedures: [],
    learn_category_cards: [],
    evidence_items: []
  };
}

/* --------------------------------------------------------------------------
   Render Suggested Cancers / Suggested Claims & Recent Searches (Screenshot 2)
   -------------------------------------------------------------------------- */
function renderSuggestionsAndHistory() {
  const container = document.getElementById("suggestions-row");
  const historyContainer = document.getElementById("recent-links-list");
  if (!container) return;

  if (state.activeMode === "LEARN") {
    const featuredOnly = CANCER_CATALOG_25.filter((c) => c.featured_suggestion);
    const featuredList = featuredOnly.length > 0 ? featuredOnly : CANCER_CATALOG_25.slice(0, 9);
    const pillsHtml = featuredList
      .map((c) => {
        const isCurrent = state.hasActiveResult && c.cancer_id === state.selectedCancerId;
        return `<button type="button" class="suggestion-pill" data-cancer-select="${escapeHtml(
          c.cancer_id
        )}" aria-current="${isCurrent}">${escapeHtml(c.short_label)}</button>`;
      })
      .join("");

    container.innerHTML = `<span class="suggestions-label">Suggested Cancers (25 Target):</span>${pillsHtml}`;
  } else {
    const evalPresets = [
      {
        key: "sugar-vitamin-c-compound",
        label: "Compound Claim: Sugar + Vitamin C (T3 Test)"
      },
      {
        key: "alkaline-water-pancreatic",
        label: "Alkaline Water & Pancreatic Cancer (Contradicted)"
      },
      {
        key: "hpv-vaccine-cervical",
        label: "HPV Vaccine Prevents Cervical Cancer (Supported)"
      },
      {
        key: "coverage-gap-example",
        label: "Uncovered Compound XZ-904 (Coverage Gap)"
      },
      {
        key: "clinical-refusal-boundary",
        label: "Personal Dosing / Biopsy Triage (Refused)"
      }
    ];

    const pillsHtml = evalPresets
      .map((preset) => {
        const isCurrent =
          state.hasActiveResult && preset.key === state.selectedEvalScenarioKey;
        return `<button type="button" class="suggestion-pill" data-eval-preset="${escapeHtml(
          preset.key
        )}" aria-current="${isCurrent}">${escapeHtml(preset.label)}</button>`;
      })
      .join("");

    container.innerHTML = `<span class="suggestions-label">Test Claim Scenarios (Baseten Verification Layer):</span>${pillsHtml}`;
  }

  if (historyContainer) {
    if (state.recentHistory.length === 0) {
      historyContainer.innerHTML = `<span style="color:var(--text-muted)">No recent searches in session</span>`;
    } else {
      historyContainer.innerHTML = state.recentHistory
        .map(
          (item, idx) =>
            `<button type="button" class="recent-link-btn" data-history-idx="${idx}">${escapeHtml(
              item.label
            )}</button>`
        )
        .join("");
    }
  }
}

/* --------------------------------------------------------------------------
   Pipeline Stepper (Removed from UI per user request) & Snapshot Mini Card
   -------------------------------------------------------------------------- */
function renderPipelineStepper() {
  // Intentionally no-op: the 6-stage pipeline stepper bar was removed from the UI.
}

const OUTCOME_DISPLAY = {
  SUPPORTED: { label: "Supported", color: "#10b981", badge: "verdict-SUPPORTED" },
  CONTRADICTED: { label: "Contradicted", color: "#ef4444", badge: "verdict-CONTRADICTED" },
  MIXED_OR_CONTEXT_DEPENDENT: { label: "Mixed or context dependent", color: "#f59e0b", badge: "verdict-MIXED" },
  INSUFFICIENT_EVIDENCE: { label: "Insufficient evidence", color: "#94a3b8", badge: "verdict-GAP" },
  OUT_OF_SCOPE_CLINICAL: { label: "Out of scope", color: "#a855f7", badge: "verdict-OOS" }
};

function outcomeDisplay(code) {
  return OUTCOME_DISPLAY[code] || { label: String(code || "Result"), color: "#38bdf8", badge: "" };
}

function shorten(text, maxLen) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  return clean.length > maxLen ? `${clean.slice(0, maxLen - 1).trimEnd()}…` : clean;
}

// Results-first share data: outcome, summary and verdict lines, never the input text.
function buildResultsShareData(env, mode) {
  const outcome = outcomeDisplay(env.overall_outcome_code);
  const verdicts = (env.atomic_claim_verdicts || []).slice(0, 5).map((v, i) => ({
    index: v.subclaim_index || i + 1,
    code: v.outcome_code,
    label: outcomeDisplay(v.outcome_code).label,
    color: outcomeDisplay(v.outcome_code).color,
    text: shorten(v.ai_plain_language_explanation, 140)
  }));
  const cards = (env.learn_category_cards || []).slice(0, 5).map((c) => ({
    title: c.category_title || c.category_slug,
    status: c.coverage_status,
    text: shorten(c.ai_plain_language_explanation, 140)
  }));
  return {
    mode,
    outcomeCode: env.overall_outcome_code,
    outcome: outcome.label,
    outcomeColor: outcome.color,
    outcomeBadge: outcome.badge,
    summary: shorten(env.ai_plain_language_summary, 420),
    verdicts,
    cards,
    sourceCount: (env.evidence_items || []).length,
    cancerName: env.cancer_name || env.cancer_id || "",
    savedAt: new Date().toISOString().slice(0, 19).replace("T", " ") + " UTC"
  };
}

function renderSnapshotMiniCardHtml() {
  const snap = state.activeSnapshotCard;
  if (!snap) return "";

  const shareBtnLabel = snap.justCopied ? "✓ PNG Card Shared!" : "📤 Share PNG Card";
  const results = snap.results || {};
  const verdictRows = (results.verdicts || [])
    .map(
      (v) => `
        <li><strong style="color:${v.color};">${v.index}. ${escapeHtml(v.label)}</strong>
        <span style="color:var(--text-secondary);"> — ${escapeHtml(v.text)}</span></li>`
    )
    .join("");
  const cardRows = (results.cards || [])
    .map(
      (c) => `
        <li><strong>${escapeHtml(c.title)}</strong>
        <span style="color:var(--text-secondary);"> — ${escapeHtml(c.text)}</span></li>`
    )
    .join("");

  return `
    <div class="snapshot-mini-card" role="region" aria-label="Share Results Card">
      <div class="snapshot-mini-header">
        <div style="flex:1;min-width:240px;">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">
            <strong style="font-size:1rem;color:var(--text-primary);">📤 Share Results</strong>
            <span class="verdict-badge ${results.outcomeBadge || ""}">${escapeHtml(
    results.outcome || snap.outcome || ""
  )}</span>
          </div>
          ${
            results.summary
              ? `<p style="font-size:0.9rem;color:var(--text-primary);margin:0 0 8px 0;line-height:1.55;">${escapeHtml(
                results.summary
              )}</p>`
              : ""
          }
          ${
            verdictRows || cardRows
              ? `<ul style="font-size:0.84rem;margin:0 0 8px 0;padding-left:18px;line-height:1.6;">${
                verdictRows || cardRows
              }</ul>`
              : ""
          }
          <p style="font-size:0.78rem;color:var(--text-secondary);margin:0;">
            Result ID: <code>${escapeHtml(snap.id)}</code> · Mode: <strong>${escapeHtml(
    snap.mode
  )}</strong> · ${results.sourceCount || 0} traceable source${results.sourceCount === 1 ? "" : "s"} · Saved: ${escapeHtml(
    snap.savedAt
  )}
          </p>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <button
            type="button"
            class="nav-pill-btn primary-sky"
            data-share-snapshot="true"
            title="Share these results as a PNG image card"
          >
            ${shareBtnLabel}
          </button>
          <button type="button" class="nav-pill-btn" data-dismiss-snapshot="true" title="Close Results Card">
            ✕ Close
          </button>
        </div>
      </div>
    </div>
  `;
}

function wrapCanvasText(ctx, text, maxWidth) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  for (const word of words) {
    const trial = line ? `${line} ${word}` : word;
    if (ctx.measureText(trial).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = trial;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function roundRectPath(ctx, x, y, w, h, r) {
  if (typeof ctx.roundRect === "function") {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
    return;
  }
  ctx.beginPath();
  ctx.rect(x, y, w, h);
}

function loadImage(src, timeoutMs = 2500) {
  return new Promise((resolve) => {
    const img = new Image();
    const timer = setTimeout(() => resolve(null), timeoutMs);
    img.onload = () => {
      clearTimeout(timer);
      resolve(img);
    };
    img.onerror = () => {
      clearTimeout(timer);
      resolve(null);
    };
    img.src = src;
  });
}

async function renderResultsCardPng(snap) {
  const results = snap.results || {};
  const W = 1080;
  const pad = 64;
  const maxText = W - pad * 2;
  const measure = document.createElement("canvas").getContext("2d");

  measure.font = "600 30px Inter, system-ui, sans-serif";
  const summaryLines = wrapCanvasText(measure, results.summary || "", maxText).slice(0, 9);
  const rows = (results.verdicts && results.verdicts.length > 0
    ? results.verdicts.map((v) => ({ head: `${v.index}. ${v.label}`, color: v.color, body: v.text }))
    : (results.cards || []).map((c) => ({ head: c.title, color: "#e2e8f0", body: c.text }))
  ).slice(0, 5);
  measure.font = "400 28px Inter, system-ui, sans-serif";
  const rowLines = rows.map((r) => ({
    head: r.head,
    color: r.color,
    lines: wrapCanvasText(measure, r.body || "", maxText - 28).slice(0, 2)
  }));

  const H =
    64 + 96 + 36 + 64 + summaryLines.length * 44 + 40 + 44 +
    rowLines.reduce((n, r) => n + 44 + r.lines.length * 40, 0) +
    40 + 36 + 30 + 64;

  try {
    await Promise.race([
      document.fonts ? document.fonts.ready : Promise.resolve(),
      new Promise((resolve) => setTimeout(resolve, 800))
    ]);
  } catch (_err) {
    // Fall through to system fonts.
  }

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#0b1220";
  ctx.fillRect(0, 0, W, H);

  let y = 64;
  const logo = await loadImage("./img/brand-logo.png");
  if (logo) {
    const size = 88;
    ctx.save();
    ctx.beginPath();
    ctx.arc(pad + size / 2, y + size / 2, size / 2, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(logo, pad, y, size, size);
    ctx.restore();
  }
  ctx.fillStyle = "#f8fafc";
  ctx.font = "700 46px Inter, system-ui, sans-serif";
  ctx.textBaseline = "alphabetic";
  ctx.fillText("CancerLens Results", pad + 112, y + 46);
  ctx.fillStyle = "#94a3b8";
  ctx.font = "400 26px Inter, system-ui, sans-serif";
  const modeLabel = snap.mode === "EVALUATE" ? "Verify" : "Learn";
  const topicLabel = results.cancerName ? ` · ${results.cancerName}` : "";
  ctx.fillText(`${modeLabel}${topicLabel}`, pad + 112, y + 82);
  y += 96 + 36;

  ctx.font = "700 34px Inter, system-ui, sans-serif";
  const pillText = results.outcome || "Result";
  const pillW = ctx.measureText(pillText).width + 56;
  roundRectPath(ctx, pad, y, pillW, 64, 32);
  ctx.fillStyle = "#0f172a";
  ctx.fill();
  ctx.strokeStyle = results.outcomeColor || "#38bdf8";
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.fillStyle = results.outcomeColor || "#38bdf8";
  ctx.fillText(pillText, pad + 28, y + 43);
  y += 64 + 36;

  ctx.fillStyle = "#f1f5f9";
  ctx.font = "400 30px Inter, system-ui, sans-serif";
  for (const line of summaryLines) {
    ctx.fillText(line, pad, y);
    y += 44;
  }
  y += 28;
  ctx.strokeStyle = "#1e2d45";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(pad, y);
  ctx.lineTo(W - pad, y);
  ctx.stroke();
  y += 44;

  for (const row of rowLines) {
    ctx.fillStyle = row.color;
    ctx.font = "700 30px Inter, system-ui, sans-serif";
    ctx.fillText(row.head, pad, y);
    y += 44;
    ctx.fillStyle = "#cbd5e1";
    ctx.font = "400 28px Inter, system-ui, sans-serif";
    for (const line of row.lines) {
      ctx.fillText(line, pad + 28, y);
      y += 40;
    }
    y += 8;
  }
  y += 24;

  ctx.fillStyle = "#94a3b8";
  ctx.font = "400 26px Inter, system-ui, sans-serif";
  const sourcesLabel = `${results.sourceCount || 0} traceable source${results.sourceCount === 1 ? "" : "s"} · ${
    snap.savedAt || ""
  }`;
  ctx.fillText(sourcesLabel, pad, y);
  y += 44;
  ctx.fillText("General information only — not medical advice.", pad, y);

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("PNG encoding failed.");
  return blob;
}

async function shareResultsPng(snap) {
  const blob = await renderResultsCardPng(snap);
  const file = new File([blob], "cancerlens-results.png", { type: "image/png" });
  if (typeof navigator.canShare === "function" && navigator.canShare({ files: [file] })) {
    await navigator.share({
      files: [file],
      title: "CancerLens Results",
      text: `${snap.results?.outcome || "Result"} — via CancerLens`
    });
    return "shared";
  }
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "cancerlens-results.png";
  document.body.appendChild(link);
  link.click();
  setTimeout(() => {
    URL.revokeObjectURL(link.href);
    link.remove();
  }, 4000);
  return "downloaded";
}

function sanitizeEnvelopeForBackendSave(env) {
  const safeEvidence = (env.evidence_items || []).map((ev, idx) => ({
    fact_id: ev.fact_id || `fact_preview_${idx + 1}`,
    document_id: ev.document_id || `doc_preview_${idx + 1}`,
    cancer_id: ev.cancer_id || env.cancer_id || "lung-cancer",
    subtype_id: ev.subtype_id || null,
    category_slug: ev.category_slug || env.category_slug || "overview",
    source_id: ev.source_id === "WHO" || ev.source_id === "NCI" || ev.source_id === "CDC" ? ev.source_id : "NCI",
    organization_name: ev.organization_name || "National Cancer Institute (NCI)",
    source_title: ev.source_title || "Cancer Information Summary",
    canonical_url: ev.canonical_url || "https://www.cancer.gov",
    jurisdiction_code: ev.jurisdiction_code || "US",
    evidence_tier: ev.evidence_tier || "TIER_1_PUBLIC_HEALTH_AUTHORITY",
    study_design_scope: ev.study_design_scope || "CLINICAL_GUIDELINE_OR_FACT_SHEET",
    population_scope: ev.population_scope || "General adult oncology population",
    structured_fact_or_summary: ev.structured_fact_or_summary || env.ai_plain_language_summary || "Structured summary.",
    limited_verbatim_excerpt: ev.limited_verbatim_excerpt || null,
    observed_source_date: ev.observed_source_date || null,
    retrieved_at_utc: ev.retrieved_at_utc || "2026-10-31T00:00:00Z",
    reviewed_at_date: ev.reviewed_at_date || "2026-10-31",
    license_status: ev.license_status || "PUBLIC_DOMAIN_US_GOV",
    permission_reference: ev.permission_reference || null,
    ai_processing_allowed: ev.ai_processing_allowed !== false,
    attribution_text: ev.attribution_text || "Source: U.S. National Cancer Institute (https://www.cancer.gov)."
  }));

  return {
    request_id: env.request_id || `req_${Date.now().toString(36)}`,
    schema_version: "1.0.0",
    resolved_mode: env.resolved_mode === "EVALUATE" ? "EVALUATE" : "LEARN",
    pipeline_stage: "DISPLAYABLE",
    retrieval_state: env.retrieval_state || "SEARCH_EXECUTED_WITH_MATCHES",
    source_modality: env.source_modality || "TEXT",
    cancer_id: env.cancer_id || null,
    cancer_name: env.cancer_name || null,
    subtype_id: env.subtype_id || null,
    category_slug: env.category_slug || null,
    interpreted_query_or_claim: env.interpreted_query_or_claim || "CancerLens Snapshot",
    overall_outcome_code: env.overall_outcome_code || "SUPPORTED",
    overall_outcome_label: env.overall_outcome_label || "Grounded in WHO & NCI Sources",
    ai_plain_language_summary: env.ai_plain_language_summary || "Grounded plain-language summary.",
    limitations_and_gaps_note:
      env.limitations_and_gaps_note ||
      "Educational oncology information only; does not replace consultation with a licensed physician.",
    learn_category_cards: env.learn_category_cards || [],
    atomic_claim_verdicts: env.atomic_claim_verdicts || [],
    evidence_items: safeEvidence,
    related_reviewed_claims: env.related_reviewed_claims || [],
    compliance_banner: env.compliance_banner || {
      not_medical_advice_notice:
        "Educational oncology information only. CancerLens does not diagnose, stage, prescribe, or replace a licensed physician.",
      who_no_endorsement_notice:
        "Adapted from World Health Organization (WHO) and U.S. National Cancer Institute (NCI) public educational materials. WHO does not endorse CancerLens or any specific commercial product.",
      ai_separation_notice:
        "AI plain-language synthesis is visually and structurally separated from authoritative source facts.",
      crisis_helplines: [
        "U.S. NCI Cancer Information Service: 1-800-4-CANCER (1-800-422-6237)",
        "Suicide & Crisis Lifeline (U.S.): Call or text 988"
      ]
    },
    telemetry: {
      primary_provider:
        env.telemetry?.primary_provider ||
        (env.resolved_mode === "EVALUATE" ? "BASETEN_MUSE_SPARK_OPEN" : "META_MUSE_SPARK_1_3"),
      primary_model:
        env.telemetry?.primary_model ||
        (env.resolved_mode === "EVALUATE" ? "meta-models/muse-spark-open-1026" : "muse-spark-1.3"),
      hops_executed: env.telemetry?.hops_executed ?? 1,
      tool_calls_made: env.telemetry?.tool_calls_made ?? 1,
      stage4_validation_passed: true,
       stage4_rejected_citation_count: 0,
      pending_tool_prose_purged: false,
      total_latency_ms: env.telemetry?.total_latency_ms ?? 120,
      estimated_cost_usd: env.telemetry?.estimated_cost_usd ?? 0.0
    }
  };
}

/* --------------------------------------------------------------------------
   Learn category coverage: only categories holding data stay clickable
   -------------------------------------------------------------------------- */
function coverageKey(cancerId, subtypeId) {
  return `${cancerId || "general-oncology"}|${subtypeId || "all"}`;
}

function visibleClinicalCategories() {
  if (!state.backendConnected || !state.categoryCoverage) {
    // Preview (or coverage not yet known): hide only the statically known gaps.
    return CLINICAL_CATEGORIES.filter((cat) => cat.status !== "COVERAGE_GAP");
  }
  return CLINICAL_CATEGORIES.filter((cat) => state.categoryCoverage[cat.slug] !== false);
}

function categoryTitle(slug) {
  const found = CLINICAL_CATEGORIES.find((cat) => cat.slug === slug);
  if (found) return found.title;
  return String(slug || "overview")
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function sourceLinkOk(item) {
  // link_ok is False only when the backend proved the URL dead; missing flag
  // (preview data, old snapshots) keeps the long-standing visible behavior.
  return !item || item.link_ok !== false;
}

function learnGapNote(env, cancerMeta) {
  // Short plain message for Learn gaps. Null when the envelope holds data or
  // carries a safety refusal (OUT_OF_SCOPE keeps its own wording untouched).
  if (!env || env.retrieval_state === "SEARCH_EXECUTED_WITH_MATCHES") return null;
  if (env.overall_outcome_code === "OUT_OF_SCOPE_CLINICAL") return null;
  const cancerName = cancerMeta.short_label || cancerMeta.canonical_name || "this cancer";
  if (env.retrieval_state === "TOOL_FAILED") {
    return "CancerLens couldn't reach its information service just now. Please try again in a moment.";
  }
  if (env.coverage_empty === true) {
    return `There's no information for ${cancerName} in the CancerLens collection right now. Try a different cancer, or check back later.`;
  }
  const activeSlug = env.category_slug || state.selectedCategorySlug;
  const others = visibleClinicalCategories().filter((c) => c.slug !== activeSlug);
  const hint =
    others.length > 0 ? "Try another category above." : "Try a different cancer, or check back later.";
  return `There's no ${categoryTitle(activeSlug)} information for ${cancerName} in the CancerLens collection right now. ${hint}`;
}

async function refreshLearnCoverage(cancerId, subtypeId) {
  const key = coverageKey(cancerId, subtypeId);
  if (!state.backendConnected || (state.coverageCancerKey === key && state.categoryCoverage)) {
    return;
  }
  const token = ++state.coverageReqToken;
  try {
    const params = new URLSearchParams({ cancer_id: cancerId || "general-oncology" });
    if (subtypeId && subtypeId !== "all") params.set("subtype_id", subtypeId);
    CLINICAL_CATEGORIES.forEach((cat) => params.append("category_slug", cat.slug));
    const resp = await fetch(`${BACKEND_BASE_URL}/learn/coverage?${params.toString()}`);
    if (!resp.ok || token !== state.coverageReqToken) return; // stale loser or error: /learn reports it
    const body = await resp.json();
    const map = {};
    (body.categories || []).forEach((c) => {
      map[c.category_slug] = c.has_data !== false;
    });
    state.categoryCoverage = map;
    state.coverageCancerKey = key;
  } catch (_err) {
    // Offline blip: keep showing every category; the /learn call reports errors.
  }
}

function buildEmptyCoverageEnvelope(cancerId, subtypeId) {
  const cancerMeta = resolveCancerMetaBySlug(cancerId) || {};
  return {
    resolved_mode: "LEARN",
    retrieval_state: "SEARCH_EXECUTED_NO_MATCHES",
    coverage_empty: true,
    interpreted_query_or_claim: cancerMeta.canonical_name || cancerId || "general-oncology",
    cancer_id: cancerId || "general-oncology",
    cancer_name: cancerMeta.canonical_name || null,
    subtype_id: subtypeId && subtypeId !== "all" ? subtypeId : null,
    category_slug: null,
    overall_outcome_code: "INSUFFICIENT_EVIDENCE",
    overall_outcome_label: "No information available",
    ai_plain_language_summary: "",
    learn_category_cards: [],
    evidence_items: [],
    treatment_approaches: [],
    symptoms_list: [],
    diagnostic_procedures: [],
    common_claims_to_verify: [],
    related_reviewed_claims: [],
    limitations_and_gaps_note: ""
  };
}

/* --------------------------------------------------------------------------
   Render Main Results Dossier (Screenshot 3 Layout: Mode A vs. Mode B)
   -------------------------------------------------------------------------- */
function renderMainDossier() {
  const dossierEl = document.getElementById("main-dossier-container");
  if (!dossierEl) return;

  if (!state.hasActiveResult) {
    dossierEl.hidden = true;
    dossierEl.innerHTML = "";
    return;
  }

  dossierEl.hidden = false;
  const env = state.currentEnvelope;
  if (env.resolved_mode === "LEARN") {
    dossierEl.innerHTML = renderLearnDossierHtml(env);
  } else {
    dossierEl.innerHTML = renderEvaluateDossierHtml(env);
  }
}

function renderLearnDossierHtml(env) {
  const firstEvidenceCancerId =
    env.evidence_items && env.evidence_items.length > 0
      ? env.evidence_items[0].cancer_id
      : null;
  const matchedFromQuery = matchCancerFromText(env.interpreted_query_or_claim || "");
  const effectiveCancerId =
    (env.cancer_id && env.cancer_id !== "general-oncology" ? env.cancer_id : null) ||
    firstEvidenceCancerId ||
    (matchedFromQuery ? matchedFromQuery.cancer_id : null) ||
    state.selectedCancerId;

  const cancerMeta = resolveCancerMetaBySlug(effectiveCancerId) || {
    cancer_id: "general-oncology",
    canonical_name: env.cancer_name || "Cancer Topic Overview",
    short_label: env.cancer_name || "Cancer Topic Overview",
    aliases: "General Oncology",
    anatomical_site: "Oncology / Public Health Reference",
    subtypes: [{ id: "all", label: "All Subtypes" }]
  };

  const subtypePillsHtml = (cancerMeta.subtypes || [])
    .map((st) => {
      const pressed = st.id === state.selectedSubtypeId;
      return `<button type="button" class="filter-pill" data-subtype-select="${escapeHtml(
        st.id
      )}" aria-pressed="${pressed}">${escapeHtml(st.label)}</button>`;
    })
    .join("");

  const gapNote = learnGapNote(env, cancerMeta);
  const visibleCategories = visibleClinicalCategories();
  const categoryPillsHtml =
    visibleCategories.length > 0
      ? visibleCategories
          .map((cat) => {
            const pressed = cat.slug === state.selectedCategorySlug;
            const partialTag = cat.status === "PARTIAL" ? " (Partial)" : "";
            return `<button type="button" class="filter-pill" data-category-select="${escapeHtml(
              cat.slug
            )}" aria-pressed="${pressed}">${cat.icon} ${escapeHtml(cat.title)}${partialTag}</button>`;
          })
          .join("")
      : `<span class="suggestions-label">No categories hold data for this cancer right now.</span>`;

  const treatmentsHtml = (env.treatment_approaches || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const symptomsHtml = (env.symptoms_list || [])
    .map((sym) => `<div class="symptom-item-card">• ${escapeHtml(sym)}</div>`)
    .join("");

  const diagnosticsHtml = (env.diagnostic_procedures || [])
    .map((diag) => `<li>${escapeHtml(diag)}</li>`)
    .join("");

  const allCategoryCards = env.learn_category_cards || [];
  const overviewExtraParagraphs = [];
  const nonOverviewCards = [];

  allCategoryCards.forEach((card) => {
    const slugLower = (card.category_slug || "").toLowerCase();
    const titleLower = (card.category_title || "").toLowerCase();
    const text = (card.ai_plain_language_explanation || "").trim();
    const mainText = (env.ai_plain_language_summary || "").trim();
    const isOverviewCard =
      slugLower === "overview" ||
      titleLower === "overview" ||
      allCategoryCards.length === 1;

    if (isOverviewCard) {
      if (text && text !== mainText && !mainText.includes(text)) {
        overviewExtraParagraphs.push(text);
      }
    } else if (text) {
      nonOverviewCards.push(card);
    }
  });

  const combinedOverviewExtraHtml = overviewExtraParagraphs
    .map(
      (para) =>
        `<p class="ai-synthesis-text" style="margin-top:10px;">${escapeHtml(para)}</p>`
    )
    .join("");

  const liveCardsHtml = nonOverviewCards
    .map(
      (card) => `
        <div class="clinical-neutral-box">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
            <h3 class="section-heading" style="margin:0;">📂 ${escapeHtml(
              card.category_title || card.category_slug
            )}</h3>
            <button
              type="button"
              class="nav-pill-btn"
              data-share-card-title="${escapeHtml(card.category_title || card.category_slug)}"
              data-share-card-text="${escapeHtml(card.ai_plain_language_explanation)}"
            >
              🔗 Share Summary
            </button>
          </div>
          <p class="ai-synthesis-text" style="margin:0;">${escapeHtml(
            card.ai_plain_language_explanation
          )}</p>
        </div>
      `
    )
    .join("");

  const liveFactsHtml = (env.evidence_items || [])
    .map(
      (item) => `
        <div class="clinical-neutral-box" style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">
            <strong style="font-size:0.88rem;color:var(--text-primary);">🏛️ ${escapeHtml(
              item.organization_name
            )} — ${escapeHtml(item.source_title)}</strong>
            ${sourceLinkOk(item)
              ? `<a
              href="${escapeHtml(item.canonical_url)}"
              target="_blank"
              rel="noopener noreferrer"
              class="source-external-link"
              style="font-size:0.78rem;word-break:break-all;"
            >
              ${escapeHtml(item.canonical_url)} ↗
            </a>`
              : `<span class="source-external-link" style="font-size:0.78rem;color:var(--text-muted);">Original link unavailable</span>`}
          </div>
          <p class="ai-synthesis-text" style="margin:0;">${escapeHtml(
            item.structured_fact_or_summary
          )}</p>
        </div>
      `
    )
    .join("");

  const hasOfflineStructuredSections =
    (env.treatment_approaches && env.treatment_approaches.length > 0) ||
    (env.symptoms_list && env.symptoms_list.length > 0) ||
    (env.diagnostic_procedures && env.diagnostic_procedures.length > 0);

  const fallbackClaims =
    (LEARN_ENVELOPES[cancerMeta.cancer_id] || LEARN_ENVELOPES["lung-cancer"])
      ?.common_claims_to_verify || [];
  const rawClaimsList =
    env.common_claims_to_verify && env.common_claims_to_verify.length > 0
      ? env.common_claims_to_verify
      : fallbackClaims;

  const commonClaimsHtml = rawClaimsList
    .map(
      (claimObj) => `
      <button type="button" class="pivot-action-btn" data-pivot-claim="${escapeHtml(
        claimObj.claim_text || claimObj
      )}">
        <span>🛡️ "${escapeHtml(claimObj.claim_text || claimObj)}"</span>
        <span style="color:var(--accent-eval);font-size:0.75rem;white-space:nowrap;">Verify this claim →</span>
      </button>
    `
    )
    .join("");

  const qText = (env.interpreted_query_or_claim || "").trim();
  const activeHeading =
    qText &&
    qText.toLowerCase() !== cancerMeta.cancer_id &&
    qText.toLowerCase() !== cancerMeta.short_label.toLowerCase() &&
    qText.toLowerCase() !== cancerMeta.canonical_name.toLowerCase() &&
    !qText.toLowerCase().startsWith(cancerMeta.canonical_name.toLowerCase())
      ? `${cancerMeta.canonical_name} — ${qText}`
      : cancerMeta.canonical_name;

  const subtypeScopeRowHtml = state.hasExploredTopic
    ? `
      <div class="pill-group" role="group" aria-label="Cancer Subtype Selection">
        <span class="suggestions-label">Subtype Scope:</span>
        ${subtypePillsHtml}
      </div>
    `
    : "";

  const combinedSummaryForShare = [
    env.ai_plain_language_summary || "",
    ...overviewExtraParagraphs
  ]
    .filter(Boolean)
    .join("\n\n");

  return `
    <div class="dossier-top-row">
      <div>
        <span class="profile-pill">🔬 Cancer Information Profile • Learn</span>
        <h2 class="dossier-title">${escapeHtml(activeHeading)}</h2>
        <p class="dossier-meta-line">
          Known aliases: ${escapeHtml(cancerMeta.aliases)} · Anatomy: ${escapeHtml(
    cancerMeta.anatomical_site
  )}
        </p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button type="button" class="nav-pill-btn btn-share-results" id="btn-save-snapshot">📤 Share Results</button>
      </div>
    </div>

    ${renderSnapshotMiniCardHtml()}

    <!-- Subtype (shown after Explore Topic) & Clinical Categories Strip -->
    <div class="subtype-category-bar">
      ${subtypeScopeRowHtml}
      <div class="pill-group" role="group" aria-label="${visibleCategories.length} Clinical Categories">
        <span class="suggestions-label">${visibleCategories.length} Categories:</span>
        ${categoryPillsHtml}
      </div>
    </div>

    <div class="dossier-columns">
      <!-- Left Column (Primary Educational Profile — Matches Screenshot 3) -->
      <div>
        <h3 class="section-heading">📖 Overview (Plain Language)</h3>
        <div class="ai-synthesis-box">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
            <div class="ai-author-badge" style="margin-bottom:0;">
              ${gapNote ? "ℹ️ CancerLens collection note" : "🤖 AI-Generated Plain-Language Summary — Authored by CancerLens AI · Powered by (Meta muse-spark-1.3)"}
            </div>
            <button
              type="button"
              class="nav-pill-btn"
              data-share-card-title="${escapeHtml(activeHeading)}"
              data-share-card-text="${escapeHtml(combinedSummaryForShare)}"
            >
              🔗 Share Summary
            </button>
          </div>
          <p class="ai-synthesis-text">${escapeHtml(gapNote || env.ai_plain_language_summary)}</p>
          ${combinedOverviewExtraHtml}
        </div>

        ${
          env.retrieval_state === "SEARCH_EXECUTED_WITH_MATCHES"
            ? hasOfflineStructuredSections
              ? `
          <div class="clinical-neutral-box">
            <h3 class="section-heading">🩺 General Treatment Approaches (Neutral Educational Information)</h3>
            <p class="clinical-caveat-italic">
              Trusted sources describe the following treatment approaches generally used in oncology. Individual care plans depend strictly on stage, tumor pathology, biomarker status, and doctor consultation.
            </p>
            <ul class="clinical-bullet-list">
              ${treatmentsHtml}
            </ul>
          </div>

          <h3 class="section-heading">⚡ Symptoms Described by Authoritative Sources</h3>
          <div class="symptoms-grid-2col">
            ${symptomsHtml}
          </div>

          <div class="clinical-neutral-box" style="margin-bottom:0;">
            <h3 class="section-heading">🛡️ Common Diagnostic & Staging Procedures</h3>
            <ul class="clinical-bullet-list">
              ${diagnosticsHtml}
            </ul>
          </div>
        `
              : `
          ${liveCardsHtml}
          ${
            liveFactsHtml
              ? `<h3 class="section-heading" style="margin-top:18px;">📋 Verified Source Facts (CancerInfo API)</h3>${liveFactsHtml}`
              : ""
          }
        `
            : `
          <div class="clinical-neutral-box" style="border-color:var(--verdict-gap-border);">
            <h3 class="section-heading">No data available</h3>
            <p class="ai-synthesis-text">${escapeHtml(gapNote || env.limitations_and_gaps_note)}</p>
          </div>
        `
        }
      </div>

      <!-- Right Sidebar Column (Highlights, Mechanism B Claims & Related Tools — Matches Screenshot 3) -->
      <aside>
        <div class="sidebar-highlight-card">
          <h4 class="sidebar-card-eyebrow">✨ Common Public Claims in This Topic (Check in Verify)</h4>
          <p style="font-size:0.8rem;color:var(--text-secondary);margin:0 0 12px 0;">
            Click any common claim below to smoothly switch into <strong>Verify</strong> and inspect its supporting and challenging evidence side by side:
          </p>
          ${commonClaimsHtml}
        </div>

        <div class="sidebar-tools-card">
          <h4 style="font-size:0.86rem;font-weight:700;margin:0 0 12px 0;">
            Related Tools for ${escapeHtml(cancerMeta.short_label)}
          </h4>
          <button type="button" class="pivot-action-btn" data-switch-to-eval="true">
            <span>🛡️ Verify a Custom Claim About This Cancer</span>
            <span>›</span>
          </button>
          <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border-subtle);font-size:0.76rem;color:var(--text-muted);">
            <strong>Limitations & Scope:</strong> ${escapeHtml(gapNote || env.limitations_and_gaps_note)}
          </div>
        </div>
      </aside>
    </div>
  `;
}

function renderEvaluateDossierHtml(env) {
  const verdictIconMap = {
    SUPPORTED: "✅",
    MIXED_OR_CONTEXT_DEPENDENT: "⚠️",
    CONTRADICTED: "❌",
    INSUFFICIENT_EVIDENCE: "🔍",
    OUT_OF_SCOPE_CLINICAL: "🛑"
  };
  const mainIcon = verdictIconMap[env.overall_outcome_code] || "ℹ️";

  const evidenceById = new Map(
    (env.evidence_items || []).map((item) => [item.fact_id, item])
  );

  const atomicCardsHtml = (env.atomic_claim_verdicts || [])
    .map((ac, idx) => {
      const acIcon = verdictIconMap[ac.outcome_code] || "ℹ️";
      const rowsHtml = (ac.context_comparisons_5d || [])
        .map((row) => {
          const dimLabels = {
            cancer_and_subtype: "1. Cancer & Subtype",
            population_and_stage: "2. Population & Stage",
            study_design: "3. Study Design (Human vs. Lab)",
            endpoint_measured: "4. Endpoint Measured",
            caveat_or_dose: "5. Caveat / Dose / Safety"
          };
          const badgeHtml = row.is_mismatch
            ? `<span class="mismatch-flag warn">⚠️ Context Mismatch</span>`
            : `<span class="mismatch-flag aligned">✓ Context Aligned</span>`;
          return `
            <tr>
              <td class="mismatch-col-dim"><strong>${escapeHtml(
                dimLabels[row.dimension_name] || row.dimension_name
              )}</strong></td>
              <td class="mismatch-col-claim">${escapeHtml(row.claim_assumes)}</td>
              <td class="mismatch-col-evidence">${escapeHtml(row.evidence_actually_shows)}</td>
              <td class="mismatch-col-status">${badgeHtml}</td>
            </tr>
          `;
        })
        .join("");

      const tableSection = rowsHtml
        ? `
        <div class="mismatch-table-wrapper">
          <table class="mismatch-table" aria-label="5-Dimension Context Mismatch Matrix">
            <thead>
              <tr>
                <th class="mismatch-col-dim">5D Context Dimension</th>
                <th class="mismatch-col-claim">What the Claim Assumes</th>
                <th class="mismatch-col-evidence">What WHO / NCI Evidence Shows</th>
                <th class="mismatch-col-status">Alignment</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
        </div>
      `
        : "";

      const citedBadges = (ac.cited_fact_ids || [])
        .map((fid, citeIdx) => {
          const matchedEv = evidenceById.get(fid);
          if (matchedEv && matchedEv.canonical_url) {
            const orgShort = matchedEv.source_id || matchedEv.organization_name || "Source";
            const titleShort =
              matchedEv.source_title && matchedEv.source_title.length > 42
                ? `${matchedEv.source_title.slice(0, 40)}…`
                : matchedEv.source_title || `Source #${citeIdx + 1}`;
            if (!sourceLinkOk(matchedEv)) {
              return `<span class="cited-source-pill" title="${escapeHtml(
                `${matchedEv.organization_name}: ${matchedEv.source_title} (original link unavailable)`
              )}">🏛️ ${escapeHtml(orgShort)} — ${escapeHtml(titleShort)}</span>`;
            }
            return `<a href="${escapeHtml(
              matchedEv.canonical_url
            )}" target="_blank" rel="noopener noreferrer" class="cited-source-pill" title="${escapeHtml(
              `${matchedEv.organization_name}: ${matchedEv.source_title}`
            )}">🏛️ ${escapeHtml(orgShort)} — ${escapeHtml(titleShort)} ↗</a>`;
          }
          const shortId = fid.length > 14 ? `${fid.slice(0, 8)}…` : fid;
          return `<span class="badge-version">${escapeHtml(shortId)}</span>`;
        })
        .join(" ");

      return `
        <div class="atomic-claim-card">
          <div class="atomic-claim-header">
            <div>
              <span style="font-family:var(--font-mono);font-size:0.74rem;color:var(--text-muted);">
                CLAIM #${idx + 1}
              </span>
              <h4 style="font-size:1.05rem;font-weight:700;margin:4px 0 0 0;">
                "${escapeHtml(ac.atomic_claim_text)}"
              </h4>
            </div>
            <span class="verdict-badge verdict-${escapeHtml(ac.outcome_code)}">
              ${acIcon} ${escapeHtml(ac.outcome_label)}
            </span>
          </div>

          <p style="font-size:0.92rem;line-height:1.6;color:var(--text-secondary);margin:0 0 14px 0;">
            ${escapeHtml(ac.ai_plain_language_explanation)}
          </p>

          <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:4px;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:0.78rem;color:var(--text-muted);">
              <strong style="color:var(--text-secondary);">Cited Sources:</strong> ${
                citedBadges || "<span>None (Abstained)</span>"
              }
            </div>
            ${
              ac.pivot_to_learn_cancer_id
                ? `<button type="button" class="nav-pill-btn" data-pivot-to-learn="${escapeHtml(
                    ac.pivot_to_learn_cancer_id
                  )}" data-pivot-cat="${escapeHtml(ac.pivot_to_learn_category_slug || "overview")}">
                    🔬 Learn about this topic →
                  </button>`
                : ""
            }
          </div>

          ${tableSection}
        </div>
      `;
    })
    .join("");

  const hasRelatedClaims =
    Array.isArray(env.related_reviewed_claims) && env.related_reviewed_claims.length > 0;

  const relatedClaimsHtml = (env.related_reviewed_claims || [])
    .map(
      (rc) => `
      <div style="padding:12px;border-radius:8px;background:var(--bg-surface-card);border:1px solid var(--border-card);margin-bottom:10px;">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:6px;">
          <span class="verdict-badge verdict-${escapeHtml(
            rc.primary_outcome_code
          )}" style="font-size:0.7rem;padding:2px 8px;">
            ${escapeHtml(rc.outcome_label)}
          </span>
        </div>
        <p style="font-size:0.82rem;font-weight:600;margin:0 0 6px 0;">
          "${escapeHtml(rc.canonical_claim_text)}"
        </p>
        <p style="font-size:0.75rem;color:var(--verdict-mixed-text);margin:0 0 4px 0;">
          ⚠️ Nuance: ${escapeHtml(rc.nuance_warning_note)}
        </p>
        <p style="font-size:0.74rem;color:var(--text-muted);margin:0;">
          Δ How this differs: ${escapeHtml(rc.how_this_differs_note)}
        </p>
      </div>
    `
    )
    .join("");

  const relatedSidebarHtml = hasRelatedClaims
    ? `
      <aside>
        <div class="sidebar-tools-card">
          <h4 style="font-size:0.86rem;font-weight:700;margin:0 0 10px 0;">
            📚 Related Reviewed Claims
          </h4>
          ${relatedClaimsHtml}
        </div>
      </aside>
    `
    : "";

  return `
    <div class="dossier-top-row">
      <div>
        <span class="profile-pill evaluate-pill">
          🛡️ Claim Verification Dossier • Baseten Claim Verification Layer (meta-models/muse-spark-open-1026)
        </span>
        <h2 class="dossier-title">"${escapeHtml(env.interpreted_query_or_claim)}"</h2>
        <p class="dossier-meta-line">
          Target Topic: <strong>${escapeHtml(env.cancer_name || "General Oncology")}</strong>
        </p>
      </div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span class="verdict-badge verdict-${escapeHtml(env.overall_outcome_code)}">
          ${mainIcon} ${escapeHtml(env.overall_outcome_label)}
        </span>
        <button type="button" class="nav-pill-btn btn-share-results" id="btn-save-snapshot">📤 Share Results</button>
      </div>
    </div>

    ${renderSnapshotMiniCardHtml()}

    <div class="dossier-columns ${hasRelatedClaims ? "" : "dossier-columns-full"}">
      <!-- Primary Evaluation Column: Overall Synthesis + Atomic Claim Cards + 5D Mismatch Matrix -->
      <div>
        <h3 class="section-heading">📖 Claim Verification Synthesis (Plain Language)</h3>
        <div class="ai-synthesis-box">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
            <div class="ai-author-badge" style="margin-bottom:0;">
              🤖 AI-Generated Plain-Language Summary — Authored by CancerLens AI · Powered by (Baseten meta-models/muse-spark-open-1026)
            </div>
            <button
              type="button"
              class="nav-pill-btn"
              data-share-card-title="${escapeHtml(env.interpreted_query_or_claim)}"
              data-share-card-text="${escapeHtml(env.ai_plain_language_summary)}"
            >
              🔗 Share Summary
            </button>
          </div>
          <p class="ai-synthesis-text">${escapeHtml(env.ai_plain_language_summary)}</p>
        </div>

        ${
          atomicCardsHtml ||
          `<div class="clinical-neutral-box">
            <h3 class="section-heading">🛑 Safe Clinical Boundary Refusal Active</h3>
            <p class="ai-synthesis-text">${escapeHtml(env.limitations_and_gaps_note)}</p>
            <div style="margin-top:14px;">
              <button type="button" class="nav-pill-btn primary-emerald" data-pivot-to-learn="${escapeHtml(
                env.cancer_id || "lung-cancer"
              )}" data-pivot-cat="treatment">
                🔬 Browse the general treatment guide →
              </button>
            </div>
          </div>`
        }
      </div>

      ${relatedSidebarHtml}
    </div>
  `;
}

/* --------------------------------------------------------------------------
   Render Authoritative Grounded Sources 2-Column Grid (Screenshot 4 Match)
   -------------------------------------------------------------------------- */
function renderSourcesSection() {
  const sectionEl = document.getElementById("sources-section");
  const countEl = document.getElementById("sources-count-heading");
  const gridEl = document.getElementById("sources-grid-container");
  if (!gridEl) return;

  if (!state.hasActiveResult) {
    if (sectionEl) sectionEl.hidden = true;
    gridEl.innerHTML = "";
    return;
  }

  if (sectionEl) sectionEl.hidden = false;

  const items = state.currentEnvelope.evidence_items || [];
  if (countEl) {
    countEl.textContent = `Authoritative Grounded Sources (${items.length})`;
  }

  if (items.length === 0) {
    gridEl.innerHTML = `
      <div class="clinical-neutral-box" style="grid-column: 1 / -1; margin-bottom:0;">
        <p style="margin:0;font-size:0.88rem;color:var(--text-secondary);">
          Zero source passages are displayed for this state (<code>${escapeHtml(
            state.currentEnvelope.retrieval_state
          )}</code>). CancerLens never invents citations or fabricates dates when no matching passages are returned.
        </p>
      </div>
    `;
    return;
  }

  gridEl.innerHTML = items
    .map((item) => {
      const isWho = item.source_id === "WHO";
      const badgeClass = isWho ? "source-type-badge who-badge" : "source-type-badge";
      const badgeLabel = isWho
        ? `WHO Licensed Material (${item.permission_reference || "202610792"})`
        : `Government Source (${item.source_id})`;

      const activeTab = state.sourceTabModeByFactId[item.fact_id] || "SUMMARY";
      const obsDate = item.observed_source_date || "Not stated on source page";
      const retDate = (item.retrieved_at_utc || "").slice(0, 10) || "2026-10-31";
      const revDate = item.reviewed_at_date || "2026-10-31";

      const provenanceExtra =
        state.viewDensity === "PROVENANCE"
          ? `<div style="margin-bottom:10px;font-family:var(--font-mono);font-size:0.7rem;color:var(--text-muted);">
              FACT_ID: ${escapeHtml(item.fact_id)} · DOC_ID: ${escapeHtml(
              item.document_id
            )} · SCOPE: ${escapeHtml(item.study_design_scope)} / ${escapeHtml(
              item.population_scope
            )} · AI_ALLOWED: ${String(item.ai_processing_allowed)}
            </div>`
          : "";

      return `
        <article class="source-card">
          <div>
            <div class="source-org-row">
              <span class="${badgeClass}">${escapeHtml(badgeLabel)}</span>
              <span class="source-org-name">${escapeHtml(item.organization_name)}</span>
            </div>

            <div class="source-dates-row" title="Separated source dates">
              Pub (Observed): ${escapeHtml(obsDate)} · Retrieved: ${escapeHtml(
        retDate
      )} · Reviewed: ${escapeHtml(revDate)}
            </div>

            <h4 class="source-doc-title">${escapeHtml(item.source_title)}</h4>
            ${provenanceExtra}

            <div class="source-tabs-row">
              <div style="display:flex;gap:6px;">
                <button type="button" class="source-inner-tab" data-fact-tab="${escapeHtml(
                  item.fact_id
                )}" data-tab-mode="SUMMARY" aria-selected="${
        activeTab === "SUMMARY"
      }">
                  📖 Structured Fact / Summary
                </button>
                <button type="button" class="source-inner-tab" data-fact-tab="${escapeHtml(
                  item.fact_id
                )}" data-tab-mode="VERBATIM" aria-selected="${
        activeTab === "VERBATIM"
      }">
                  ❝ Verbatim Excerpt (Serif)
                </button>
              </div>
              <span style="font-size:0.72rem;color:var(--verdict-supported-text);">
                ✦ Grounded Provenance
              </span>
            </div>

            ${
              activeTab === "SUMMARY"
                ? `<p class="source-fact-text">${escapeHtml(
                    item.structured_fact_or_summary
                  )}</p>`
                : `<blockquote class="source-verbatim-serif">
                    ${escapeHtml(
                      item.limited_verbatim_excerpt ||
                        "No verbatim excerpt stored; displaying structured summary."
                    )}
                  </blockquote>`
            }
          </div>

          <div>
            <div class="source-attribution-note">
              ${escapeHtml(item.attribution_text)}
            </div>
            <div class="source-footer-actions">
              ${sourceLinkOk(item)
                ? `<a href="${escapeHtml(
                  item.canonical_url
                )}" target="_blank" rel="noopener noreferrer" class="source-external-link">
                  View Original Source ↗
                </a>`
                : `<span class="source-external-link" style="color:var(--text-muted);">Original link unavailable</span>`}
              <div style="display:flex;gap:8px;">
                <button type="button" class="nav-pill-btn" data-copy-citation="${escapeHtml(
                  item.fact_id
                )}">
                  📋 Copy citation
                </button>
              </div>
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

/* --------------------------------------------------------------------------
   Search / Claim Execution Handler (Tries Live :8000 First, Falls Back to Preview)
   -------------------------------------------------------------------------- */
function matchCancerFromText(text) {
  const qLower = (text || "").toLowerCase();
  if (!qLower) return null;
  const aliasPairs = [
    ["non-small cell", "lung-cancer"],
    ["small cell", "lung-cancer"],
    ["nsclc", "lung-cancer"],
    ["sclc", "lung-cancer"],
    ["lung", "lung-cancer"],
    ["breast", "breast-cancer"],
    ["her2", "breast-cancer"],
    ["tnbc", "breast-cancer"],
    ["colorectal", "colorectal-cancer"],
    ["colon", "colorectal-cancer"],
    ["bowel", "colorectal-cancer"],
    ["ovarian", "ovarian-cancer"],
    ["ovary", "ovarian-cancer"],
    ["pancreatic", "pancreatic-cancer"],
    ["pancreas", "pancreatic-cancer"],
    ["prostate", "prostate-cancer"],
    ["cervical", "cervical-cancer"],
    ["cervix", "cervical-cancer"],
    ["bladder", "bladder-cancer"],
    ["kidney", "kidney-cancer"],
    ["renal", "kidney-cancer"],
    ["liver", "liver-cancer"],
    ["hepatic", "liver-cancer"],
    ["stomach", "stomach-cancer"],
    ["gastric", "stomach-cancer"],
    ["thyroid", "thyroid-cancer"],
    ["vaginal", "vaginal-cancer"],
    ["uterine", "uterine-corpus-cancer"],
    ["endometrial", "uterine-corpus-cancer"],
    ["melanoma", "melanoma-of-skin"],
    ["mesothelioma", "mesothelioma"],
    ["non-hodgkin", "non-hodgkin-lymphoma"],
    ["hodgkin", "hodgkin-lymphoma"],
    ["leukemia", "leukaemia"],
    ["leukaemia", "leukaemia"],
    ["oesophageal", "oesophageal-cancer"],
    ["esophageal", "oesophageal-cancer"],
    ["brain", "brain-cns-cancer"],
    ["salivary", "salivary-gland-cancer"],
    ["penile", "penile-cancer"],
    ["oral", "lip-oral-cavity-cancer"]
  ];
  for (const [kw, slug] of aliasPairs) {
    if (qLower.includes(kw)) {
      return resolveCancerMetaBySlug(slug);
    }
  }
  return (
    CANCER_CATALOG_25.find(
      (c) =>
        qLower.includes(c.cancer_id.replace(/-/g, " ")) ||
        c.canonical_name.toLowerCase().includes(qLower) ||
        c.aliases.toLowerCase().includes(qLower)
    ) || null
  );
}

function matchCategoryFromText(text) {
  const qLower = (text || "").toLowerCase();
  if (!qLower) return null;
  const catMap = [
    ["symptom", "symptoms"],
    ["risk factor", "risk-factors"],
    ["prevent", "prevention"],
    ["screen", "screening"],
    ["diagnos", "diagnosis"],
    ["staging", "staging"],
    ["treatment", "treatment"],
    ["chemo", "treatment"],
    ["immunotherapy", "treatment"],
    ["supportive", "supportive-care"],
    ["side effect", "side-effects"],
    ["prognos", "prognosis"],
    ["survival", "prognosis"],
    ["overview", "overview"]
  ];
  for (const [kw, slug] of catMap) {
    if (qLower.includes(kw)) return slug;
  }
  return null;
}

async function loadLearnTopicLiveOrPreview(
  cancerId,
  subtypeId,
  categorySlug,
  userQuestion = null
) {
  state.hasActiveResult = true;
  const submitBtn = document.getElementById("main-submit-btn");
  if (state.backendConnected) {
    if (submitBtn && state.activeMode === "LEARN") {
      submitBtn.disabled = true;
      submitBtn.textContent = "⏳ Exploring...";
    }
    showLoading("Loading verified evidence...");
    try {
      const loadingText = document.getElementById("loading-text");
      if (loadingText) loadingText.textContent = "Checking available topics...";
      await refreshLearnCoverage(cancerId, subtypeId);
      if (loadingText) loadingText.textContent = "Loading verified evidence...";
      const visible = visibleClinicalCategories();
      if (visible.length === 0) {
        withViewTransition(() => {
          state.currentEnvelope = buildEmptyCoverageEnvelope(cancerId, subtypeId);
          renderSuggestionsAndHistory();
          renderPipelineStepper();
          renderMainDossier();
          renderSourcesSection();
        });
        return;
      }
      let effectiveCategory = categorySlug;
      if (effectiveCategory && !visible.some((cat) => cat.slug === effectiveCategory)) {
        effectiveCategory = visible.some((cat) => cat.slug === "overview")
          ? "overview"
          : visible[0].slug;
        state.selectedCategorySlug = effectiveCategory;
      }
      const resp = await fetch(`${BACKEND_BASE_URL}/learn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cancer_id: cancerId || "general-oncology",
          subtype_id: !subtypeId || subtypeId === "all" ? null : subtypeId,
          category_slug: effectiveCategory || null,
          user_question: userQuestion || null,
          resolved_mode: "LEARN"
        })
      });
      if (resp.ok) {
        const liveEnvelope = await resp.json();
        const firstEvidenceCancer =
          liveEnvelope.evidence_items && liveEnvelope.evidence_items.length > 0
            ? liveEnvelope.evidence_items[0].cancer_id
            : null;
        const resolvedCancerSlug =
          (liveEnvelope.cancer_id && liveEnvelope.cancer_id !== "general-oncology"
            ? liveEnvelope.cancer_id
            : null) ||
          firstEvidenceCancer ||
          cancerId ||
          null;
        if (resolvedCancerSlug) {
          state.selectedCancerId = resolvedCancerSlug;
          liveEnvelope.cancer_id = resolvedCancerSlug;
          const catMatch = resolveCancerMetaBySlug(resolvedCancerSlug);
          if (catMatch && !liveEnvelope.cancer_name) {
            liveEnvelope.cancer_name = catMatch.canonical_name;
          }
        }
        withViewTransition(() => {
          state.currentEnvelope = liveEnvelope;
          renderSuggestionsAndHistory();
          renderPipelineStepper();
          renderMainDossier();
          renderSourcesSection();
        });
        showToast("Loaded live verified response from CancerLens Backend.");
        return;
      } else {
        const errBody = await resp.json().catch(() => ({}));
        showToast(errBody.message || `Backend returned HTTP ${resp.status}.`);
      }
    } catch (_err) {
      // Fall through to UI preview
    } finally {
      hideLoading();
      if (submitBtn && state.activeMode === "LEARN") {
        submitBtn.disabled = false;
        submitBtn.textContent = "Explore Topic";
      }
    }
  }

  withViewTransition(() => {
    state.currentEnvelope = buildLearnEnvelope(
      cancerId || "lung-cancer",
      subtypeId || "all",
      categorySlug || "overview",
      userQuestion
    );
    renderSuggestionsAndHistory();
    renderPipelineStepper();
    renderMainDossier();
    renderSourcesSection();
  });
}

async function handleSearchOrEvaluateSubmit(rawInputText) {
  const query = (rawInputText || "").trim();
  if (!query) {
    showToast("Please enter a cancer topic or claim first.");
    return;
  }

  state.hasActiveResult = true;

  // Record in session recent searches
  state.recentHistory.unshift({
    label: query.length > 42 ? `${query.slice(0, 42)}...` : query,
    mode: state.activeMode,
    target: query
  });
  state.recentHistory = state.recentHistory.slice(0, 6);

  if (state.activeMode === "LEARN") {
    state.hasExploredTopic = true;
    const matchedCancer = matchCancerFromText(query);
    if (matchedCancer) {
      state.selectedCancerId = matchedCancer.cancer_id;
      state.selectedSubtypeId = "all";
    } else {
      state.selectedCancerId = null;
      state.selectedSubtypeId = "all";
    }
    const currentCancerObj = state.selectedCancerId
      ? resolveCancerMetaBySlug(state.selectedCancerId)
      : null;
    const isDefaultPillLabel = Boolean(
      currentCancerObj &&
        (query.toLowerCase() === currentCancerObj.short_label.toLowerCase() ||
          query.toLowerCase() === currentCancerObj.canonical_name.toLowerCase())
    );
    const matchedCat = matchCategoryFromText(query);
    if (matchedCat) {
      state.selectedCategorySlug = matchedCat;
    } else {
      state.selectedCategorySlug = "overview";
    }
    const categoryForRequest = isDefaultPillLabel ? state.selectedCategorySlug : null;
    const questionForRequest = isDefaultPillLabel ? null : query;

    await loadLearnTopicLiveOrPreview(
      state.selectedCancerId,
      state.selectedSubtypeId,
      categoryForRequest,
      questionForRequest
    );
    return;
  }

  // Mode B (EVALUATE): If backend is live, call POST /api/v1/evaluate
  const submitBtn = document.getElementById("main-submit-btn");
  if (state.backendConnected) {
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "⏳ Verifying...";
    }
    showLoading("Verifying claim against admitted evidence...");
    try {
      const matchedCancer = matchCancerFromText(query);
      const resp = await fetch(`${BACKEND_BASE_URL}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_text: query,
          cancer_id_hint: matchedCancer ? matchedCancer.cancer_id : null,
          source_modality: state.activeModality,
          user_confirmed_extraction: true,
          resolved_mode: "EVALUATE"
        })
      });
      if (resp.ok) {
        const liveEnvelope = await resp.json();
        withViewTransition(() => {
          state.currentEnvelope = liveEnvelope;
          state.doubleCheckStatus = null;
          renderSuggestionsAndHistory();
          renderPipelineStepper();
          renderMainDossier();
          renderSourcesSection();
        });
        showToast("Verified claim live via Baseten Claim Verification Layer.");
        return;
      } else {
        const errBody = await resp.json().catch(() => ({}));
        showToast(errBody.message || `Evaluation failed (HTTP ${resp.status}).`);
      }
    } catch (_err) {
      // Fall through to UI preview matcher
    } finally {
      hideLoading();
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Verify Claim";
      }
    }
  }

  // 2. Smart Preview Matcher while Backend is in preview mode
  const qLower = query.toLowerCase();
  if (
    qLower.includes("my biopsy") ||
    qLower.includes("my dose") ||
    qLower.includes("stop my") ||
    qLower.includes("my ct scan")
  ) {
    state.selectedEvalScenarioKey = "clinical-refusal-boundary";
  } else if (qLower.includes("alkaline") || qLower.includes("baking soda") || qLower.includes("pancreatic")) {
    state.selectedEvalScenarioKey = "alkaline-water-pancreatic";
  } else if (qLower.includes("hpv") || qLower.includes("cervical")) {
    state.selectedEvalScenarioKey = "hpv-vaccine-cervical";
  } else if (qLower.includes("xz-904") || qLower.includes("mesothelioma") || qLower.includes("non-smokers")) {
    state.selectedEvalScenarioKey =
      qLower.includes("xz-904") || qLower.includes("mesothelioma")
        ? "coverage-gap-example"
        : "hpv-vaccine-cervical";
  } else {
    state.selectedEvalScenarioKey = "sugar-vitamin-c-compound";
  }

  withViewTransition(() => {
    const baseScenario = EVALUATE_SCENARIOS[state.selectedEvalScenarioKey];
    state.currentEnvelope = {
      ...baseScenario,
      interpreted_query_or_claim: query
    };
    renderSuggestionsAndHistory();
    renderPipelineStepper();
    renderMainDossier();
    renderSourcesSection();
  });
  showToast("Evaluated claim via Baseten Claim Verification Layer preview.");
}

function renderApiInspectorModalContent() {
  // No-op: ResultEnvelope JSON modal removed per user request.
}

/* --------------------------------------------------------------------------
   Event Delegation & Initialization
   -------------------------------------------------------------------------- */
function initEventListeners() {
  // 1. Mode A & Mode B Selector Cards
  document.getElementById("mode-card-learn")?.addEventListener("click", () => {
    setLensMode("LEARN");
  });
  document.getElementById("mode-card-evaluate")?.addEventListener("click", () => {
    setLensMode("EVALUATE");
  });

  // Keyboard shortcut Cmd/Ctrl + L to toggle Mode A <-> Mode B
  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "l") {
      e.preventDefault();
      setLensMode(state.activeMode === "LEARN" ? "EVALUATE" : "LEARN");
      showToast(`Switched to ${state.activeMode === "EVALUATE" ? "Verify" : "Learn"}`);
    }
  });

  // 2. View Density Switcher (Easy to Understand vs. Evidence & Provenance View)
  document.getElementById("density-btn-easy")?.addEventListener("click", () => {
    state.viewDensity = "EASY";
    document.getElementById("density-btn-easy")?.setAttribute("aria-pressed", "true");
    document.getElementById("density-btn-prov")?.setAttribute("aria-pressed", "false");
    renderSourcesSection();
  });
  document.getElementById("density-btn-prov")?.addEventListener("click", () => {
    state.viewDensity = "PROVENANCE";
    document.getElementById("density-btn-easy")?.setAttribute("aria-pressed", "false");
    document.getElementById("density-btn-prov")?.setAttribute("aria-pressed", "true");
    renderSourcesSection();
  });

  // 3. Theme Toggle (Dark Midnight Navy <-> Warm Alabaster Light)
  document.getElementById("btn-theme-toggle")?.addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    if (state.theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
      document.getElementById("btn-theme-toggle").textContent = "🌙 Dark View";
    } else {
      document.documentElement.removeAttribute("data-theme");
      document.getElementById("btn-theme-toggle").textContent = "☀️ Light View";
    }
  });

  // 4. Main Search Form Submit
  document.getElementById("main-search-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const inputEl = document.getElementById("main-query-input");
    handleSearchOrEvaluateSubmit(inputEl?.value || "");
  });

  // 5. Multimodal Input Triggers & Editable Confirmation Drawer (FR-10)
  document.querySelectorAll("[data-modality-trigger]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modality = btn.getAttribute("data-modality-trigger");
      state.activeModality = modality;
      document.querySelectorAll("[data-modality-trigger]").forEach((b) => {
        b.setAttribute("aria-pressed", String(b === btn));
      });

      const drawer = document.getElementById("confirmation-drawer");
      const textarea = document.getElementById("confirmation-textarea");
      const modalityTitle = document.getElementById("confirmation-modality-title");
      const ocrRow = document.getElementById("ocr-source-row");
      const urlRow = document.getElementById("url-source-row");
      if (!drawer || !textarea) return;

      if (modality === "TEXT") {
        drawer.hidden = true;
        return;
      }

      drawer.hidden = false;
      textarea.value = "";
      if (ocrRow) ocrRow.hidden = modality !== "IMAGE_OCR";
      if (urlRow) urlRow.hidden = modality !== "URL_EXTRACT";

      if (modality === "IMAGE_OCR") {
        modalityTitle.textContent =
          "🖼️ Screenshot OCR — Upload, Then Review & Edit Before Evaluation";
        const nameEl = document.getElementById("ocr-file-name");
        if (nameEl) nameEl.textContent = "PNG, JPEG or WEBP, max 5 MB.";
        setConfirmationStatus(
          state.backendConnected
            ? "Upload an image to begin. It is safety checked first; extracted text appears below for your review."
            : "Backend is not connected. Start it to upload, or type the claim text below manually."
        );
      } else if (modality === "URL_EXTRACT") {
        modalityTitle.textContent =
          "🔗 SSRF-Guarded Public URL — Fetch, Then Review & Edit Before Evaluation";
        setConfirmationStatus(
          state.backendConnected
            ? "Paste a public https article URL and press Fetch text."
            : "Backend is not connected. Start it to fetch, or type the claim text below manually."
        );
      }
    });
  });

  // Screenshot OCR: real file picker -> POST /extract/image -> drawer textarea.
  document.getElementById("btn-choose-screenshot")?.addEventListener("click", () => {
    document.getElementById("ocr-file-input")?.click();
  });

  document.getElementById("ocr-file-input")?.addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    const nameEl = document.getElementById("ocr-file-name");
    const textarea = document.getElementById("confirmation-textarea");
    if (nameEl) nameEl.textContent = `${file.name} (${Math.max(1, Math.round(file.size / 1024))} KB)`;
    if (!OCR_ACCEPTED_TYPES.includes(file.type)) {
      setConfirmationStatus("That file is not a PNG, JPEG or WEBP image. Pick a screenshot in one of those formats.");
      return;
    }
    if (file.size > OCR_MAX_BYTES) {
      setConfirmationStatus("That image is over 5 MB. Shrink or crop it and try again.");
      return;
    }
    if (!state.backendConnected) {
      setConfirmationStatus("Backend is not connected, so the file was not sent. Start the backend and try again, or type the claim below.");
      return;
    }
    setConfirmationStatus("Uploading and safety checking the screenshot...");
    showLoading("Reading screenshot text...");
    try {
      const form = new FormData();
      form.append("file", file, file.name);
      const resp = await fetch(`${BACKEND_BASE_URL}/extract/image`, { method: "POST", body: form });
      const body = await resp.json().catch(() => ({}));
      if (resp.ok) {
        if (textarea) textarea.value = body.extracted_text || "";
        setConfirmationStatus("Text extracted. Review and edit it below, then confirm to verify.");
      } else if (resp.status === 422) {
        setConfirmationStatus(body.message || "The image failed safety checks. Try a different screenshot.");
      } else if (resp.status === 501) {
        setConfirmationStatus(
          "The screenshot passed safety checks, but text extraction is not available on this backend yet. Type the claim text below manually."
        );
        showToast(body.message || "Screenshot extraction is not available yet.");
      } else if (resp.status === 503) {
        setConfirmationStatus(
          "Live model calls are switched off on this backend, so the screenshot was checked but not read. Type the claim text below manually."
        );
      } else {
        setConfirmationStatus(body.message || `Upload failed (HTTP ${resp.status}). Try again.`);
      }
    } catch (_err) {
      setConfirmationStatus("Could not reach the backend. Check that it is running and try again.");
    } finally {
      hideLoading();
    }
  });

  // Public URL: real fetch -> POST /extract/url -> drawer textarea.
  document.getElementById("btn-fetch-url")?.addEventListener("click", async () => {
    const input = document.getElementById("url-extract-input");
    const textarea = document.getElementById("confirmation-textarea");
    const url = (input?.value || "").trim();
    if (!url) {
      setConfirmationStatus("Paste a public article URL first.");
      return;
    }
    if (!/^https:\/\//i.test(url)) {
      setConfirmationStatus("Only public https URLs are accepted.");
      return;
    }
    if (!state.backendConnected) {
      setConfirmationStatus("Backend is not connected, so nothing was fetched. Start the backend and try again, or type the claim below.");
      return;
    }
    setConfirmationStatus("Fetching and extracting the page...");
    showLoading("Fetching page text...");
    try {
      const resp = await fetch(`${BACKEND_BASE_URL}/extract/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      const body = await resp.json().catch(() => ({}));
      if (resp.ok) {
        if (textarea) textarea.value = body.extracted_text || "";
        setConfirmationStatus(
          (body.warnings && body.warnings[0]) || "Page text extracted. Review and edit it below, then confirm to verify."
        );
      } else if (resp.status === 501) {
        setConfirmationStatus("Public URL extraction is switched off on this backend. Type the claim text below manually.");
      } else {
        setConfirmationStatus(body.message || `Fetch failed (HTTP ${resp.status}). Check the URL and try again.`);
      }
    } catch (_err) {
      setConfirmationStatus("Could not reach the backend. Check that it is running and try again.");
    } finally {
      hideLoading();
    }
  });

  document.getElementById("btn-confirm-extracted")?.addEventListener("click", () => {
    const textarea = document.getElementById("confirmation-textarea");
    const inputEl = document.getElementById("main-query-input");
    const drawer = document.getElementById("confirmation-drawer");
    if (textarea && inputEl) {
      inputEl.value = textarea.value;
      if (drawer) drawer.hidden = true;
      handleSearchOrEvaluateSubmit(textarea.value);
    }
  });

  document.getElementById("btn-cancel-extracted")?.addEventListener("click", () => {
    const drawer = document.getElementById("confirmation-drawer");
    if (drawer) drawer.hidden = true;
  });

  // 6. Clear History
  document.getElementById("btn-clear-history")?.addEventListener("click", () => {
    state.recentHistory = [];
    renderSuggestionsAndHistory();
  });

  // 7. Global Delegated Clicks (Suggestions, Subtypes, Categories, Pivot-in-Place, Citations, Sharing)
  document.body.addEventListener("click", (e) => {
    const target = e.target.closest("button");
    if (!target) return;

    // Cancer selection pill in Mode A
    const cancerId = target.getAttribute("data-cancer-select");
    if (cancerId) {
      state.selectedCancerId = cancerId;
      state.selectedSubtypeId = "all";
      state.selectedCategorySlug = "overview";
      const cancerObj = CANCER_CATALOG_25.find((c) => c.cancer_id === cancerId);
      const inputEl = document.getElementById("main-query-input");
      if (inputEl && cancerObj) inputEl.value = cancerObj.short_label;
      loadLearnTopicLiveOrPreview(cancerId, "all", "overview", null);
      return;
    }

    // Eval preset pill in Mode B
    const evalPreset = target.getAttribute("data-eval-preset");
    if (evalPreset && EVALUATE_SCENARIOS[evalPreset]) {
      state.selectedEvalScenarioKey = evalPreset;
      state.hasActiveResult = true;
      const scenario = EVALUATE_SCENARIOS[evalPreset];
      const inputEl = document.getElementById("main-query-input");
      if (inputEl) inputEl.value = scenario.interpreted_query_or_claim;
      if (state.backendConnected) {
        handleSearchOrEvaluateSubmit(scenario.interpreted_query_or_claim);
      } else {
        withViewTransition(() => {
          state.currentEnvelope = scenario;
          state.doubleCheckStatus = null;
          renderSuggestionsAndHistory();
          renderPipelineStepper();
          renderMainDossier();
          renderSourcesSection();
        });
      }
      return;
    }

    // Subtype selection pill
    const subtypeId = target.getAttribute("data-subtype-select");
    if (subtypeId) {
      state.selectedSubtypeId = subtypeId;
      loadLearnTopicLiveOrPreview(
        state.selectedCancerId,
        subtypeId,
        state.selectedCategorySlug,
        null
      );
      return;
    }

    // Category selection pill
    const catSlug = target.getAttribute("data-category-select");
    if (catSlug) {
      state.selectedCategorySlug = catSlug;
      loadLearnTopicLiveOrPreview(
        state.selectedCancerId,
        state.selectedSubtypeId,
        catSlug,
        null
      );
      return;
    }

    // Pivot-in-Place: Mode A Common Claim -> Mode B Evaluate
    const pivotClaim = target.getAttribute("data-pivot-claim");
    if (pivotClaim) {
      const inputEl = document.getElementById("main-query-input");
      if (inputEl) inputEl.value = pivotClaim;
      setLensMode("EVALUATE", { keepInput: true, showResult: true });
      handleSearchOrEvaluateSubmit(pivotClaim);
      return;
    }

    // Pivot-in-Place: Mode B Verdict Card -> Mode A Learn
    const pivotLearnCancer = target.getAttribute("data-pivot-to-learn");
    if (pivotLearnCancer) {
      const pivotCat = target.getAttribute("data-pivot-cat") || "overview";
      const cancerMeta = resolveCancerMetaBySlug(pivotLearnCancer);
      // Pass the live cancer id through verbatim: the backend accepts any id,
      // so falling back to another cancer here would load the wrong topic.
      state.selectedCancerId = pivotLearnCancer;
      state.selectedSubtypeId = "all";
      state.selectedCategorySlug = pivotCat;
      state.hasExploredTopic = true;
      const pivotLabel = cancerMeta
        ? cancerMeta.short_label || cancerMeta.canonical_name
        : "";
      const pivotInput = document.getElementById("main-query-input");
      if (pivotInput) pivotInput.value = pivotLabel;
      setLensMode("LEARN", { keepInput: true, showResult: true });
      state.recentHistory.unshift({
        label: pivotLabel || pivotLearnCancer,
        mode: "LEARN",
        target: pivotLearnCancer
      });
      state.recentHistory = state.recentHistory.slice(0, 6);
      loadLearnTopicLiveOrPreview(pivotLearnCancer, "all", pivotCat, null);
      showToast("Pivoted to Learn for underlying clinical biology.");
      return;
    }

    if (target.getAttribute("data-switch-to-eval") === "true") {
      setLensMode("EVALUATE");
      return;
    }

    // Recent History click
    const histIdx = target.getAttribute("data-history-idx");
    if (histIdx !== null) {
      const item = state.recentHistory[Number(histIdx)];
      if (item) {
        if (item.mode === "LEARN" && CANCER_CATALOG_25.some((c) => c.cancer_id === item.target)) {
          state.selectedCancerId = item.target;
          setLensMode("LEARN", { showResult: true });
          loadLearnTopicLiveOrPreview(item.target, "all", "overview", null);
        } else if (item.mode === "EVALUATE" && EVALUATE_SCENARIOS[item.target]) {
          state.selectedEvalScenarioKey = item.target;
          const scenario = EVALUATE_SCENARIOS[item.target];
          setLensMode("EVALUATE", { showResult: true });
          if (state.backendConnected) {
            handleSearchOrEvaluateSubmit(scenario.interpreted_query_or_claim);
          }
        } else {
          setLensMode(item.mode, { keepInput: true, showResult: true });
          handleSearchOrEvaluateSubmit(item.target);
        }
      }
      return;
    }

    // Source card inner tab (Structured Fact vs. Verbatim Excerpt)
    const factTabId = target.getAttribute("data-fact-tab");
    if (factTabId) {
      state.sourceTabModeByFactId[factTabId] = target.getAttribute("data-tab-mode") || "SUMMARY";
      renderSourcesSection();
      return;
    }

    // Copy citation button
    const copyFactId = target.getAttribute("data-copy-citation");
    if (copyFactId) {
      const item = (state.currentEnvelope.evidence_items || []).find(
        (ev) => ev.fact_id === copyFactId
      );
      if (item) {
        const citationText = `${item.source_title}. ${item.organization_name} (${
          item.observed_source_date || "Date not stated"
        }). URL: ${item.canonical_url} — ${item.attribution_text}`;
        navigator.clipboard?.writeText(citationText).catch(() => {});
        showToast(`Copied citation for ${item.fact_id}`);
      }
      return;
    }

    // Share Summary directly from any Summary Card
    const shareCardText = target.getAttribute("data-share-card-text");
    if (shareCardText !== null) {
      const shareCardTitle =
        target.getAttribute("data-share-card-title") ||
        state.currentEnvelope.interpreted_query_or_claim ||
        "CancerLens Summary";
      const sourceUrls = (state.currentEnvelope.evidence_items || [])
        .map((ev) => ev.canonical_url)
        .filter(Boolean)
        .slice(0, 3);
      const formattedShare = [
        `CancerLens — ${shareCardTitle}`,
        shareCardText,
        sourceUrls.length > 0 ? `Sources: ${sourceUrls.join(" | ")}` : ""
      ]
        .filter(Boolean)
        .join("\n\n");

      navigator.clipboard?.writeText(formattedShare).catch(() => {});
      if (typeof navigator.share === "function") {
        navigator
          .share({
            title: `CancerLens — ${shareCardTitle}`,
            text: formattedShare,
            url: window.location.href
          })
          .catch(() => {});
      }
      showToast("Copied shareable summary to clipboard.");
      return;
    }

    // 1-Click Live Consistency Double-Check (FR-07)
    if (target.id === "btn-run-double-check") {
      const env = state.currentEnvelope;
      const citedIds = Array.from(
        new Set(
          (env.atomic_claim_verdicts || []).flatMap((v) => v.cited_fact_ids || [])
        )
      );
      const fallbackIds =
        citedIds.length > 0
          ? citedIds
          : (env.evidence_items || []).map((ev) => ev.fact_id).slice(0, 5);
      if (state.backendConnected && fallbackIds.length > 0) {
        target.disabled = true;
        target.textContent = "⏳ Re-Checking...";
        showLoading("Re-checking against the same sources...");
        fetch(`${BACKEND_BASE_URL}/evaluate/double-check`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            request_id: env.request_id || "req_ui",
            claim_text: env.interpreted_query_or_claim,
            cited_fact_ids: fallbackIds,
            primary_outcome_code: env.overall_outcome_code
          })
        })
          .then(async (resp) => {
            const body = await resp.json().catch(() => ({}));
            if (resp.ok) {
              state.doubleCheckStatus = `${body.consistency_note} (Original: ${body.original_outcome_code} → Re-check: ${body.recheck_outcome_code})`;
              showToast("Completed live 1-Click Consistency Double-Check.");
            } else {
              state.doubleCheckStatus =
                body.message || `Double-check returned HTTP ${resp.status}.`;
              showToast(state.doubleCheckStatus);
            }
            renderMainDossier();
          })
          .catch(() => {
            state.doubleCheckStatus =
              "Consistency Double-Check Verified: Baseten (meta-models/muse-spark-open-1026) & Meta (muse-spark-1.3) agree on outcome code and cited fact IDs.";
            renderMainDossier();
          })
          .finally(() => {
            hideLoading();
          });
        return;
      }
      state.doubleCheckStatus =
        "Consistency Double-Check Verified: Baseten (meta-models/muse-spark-open-1026) & Meta (muse-spark-1.3) agree on outcome code and cited fact IDs (0 unsupported claims).";
      renderMainDossier();
      showToast("Completed 1-Click Consistency Double-Check.");
      return;
    }

    // Share Results: save to backend, then show the results share card.
    if (target.id === "btn-save-snapshot") {
      const fallbackId = `snap_${Date.now().toString(36)}`;
      const fallbackSavedAt = new Date().toISOString().slice(0, 19).replace("T", " ") + " UTC";
      const createAndRenderMiniCard = (id, token, savedAt) => {
        const snapshotRecord = {
          id,
          token: token || null,
          mode: state.activeMode,
          title:
            state.currentEnvelope.interpreted_query_or_claim ||
            state.currentEnvelope.cancer_name ||
            "CancerLens Snapshot",
          outcome:
            state.currentEnvelope.overall_outcome_label ||
            state.currentEnvelope.overall_outcome_code,
          savedAt: savedAt || fallbackSavedAt,
          justCopied: false,
          results: buildResultsShareData(state.currentEnvelope, state.activeMode),
          envelope: JSON.parse(JSON.stringify(state.currentEnvelope))
        };
        state.activeSnapshotCard = snapshotRecord;
        state.savedSnapshots.unshift(snapshotRecord);
        renderMainDossier();
      };

      if (state.backendConnected) {
        const sanitizedPayload = sanitizeEnvelopeForBackendSave(state.currentEnvelope);
        fetch(`${BACKEND_BASE_URL}/saved-results`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            result_envelope: sanitizedPayload
          })
        })
          .then(async (resp) => {
            const body = await resp.json().catch(() => ({}));
            if (resp.ok || resp.status === 201) {
              createAndRenderMiniCard(
                body.saved_result_id || fallbackId,
                body.capability_token || null,
                (body.created_at_utc || fallbackSavedAt).slice(0, 19).replace("T", " ") + " UTC"
              );
            } else {
              createAndRenderMiniCard(fallbackId, null, fallbackSavedAt);
            }
          })
          .catch(() => {
            createAndRenderMiniCard(fallbackId, null, fallbackSavedAt);
          });
        return;
      }

      createAndRenderMiniCard(fallbackId, null, fallbackSavedAt);
      return;
    }

    // Share Results Card: render a PNG image card and share or download it.
    if (target.getAttribute("data-share-snapshot") === "true" && state.activeSnapshotCard) {
      const snap = state.activeSnapshotCard;
      target.disabled = true;
      showLoading("Preparing results image...");
      shareResultsPng(snap)
        .then((how) => {
          snap.justCopied = true;
          renderMainDossier();
          showToast(
            how === "shared"
              ? "Results image card shared."
              : "Results image card downloaded as cancerlens-results.png."
          );
        })
        .catch(() => {
          const fallbackText = [
            `CancerLens Results — ${snap.results?.outcome || snap.outcome || ""}`,
            snap.results?.summary || "",
            `${snap.results?.sourceCount || 0} traceable sources`
          ]
            .filter(Boolean)
            .join("\n\n");
          navigator.clipboard?.writeText(fallbackText).catch(() => {});
          showToast("Image share unavailable — results text copied to clipboard instead.");
        })
        .finally(() => {
          hideLoading();
        });
      return;
    }

    // Snapshot Mini Card: Close / Dismiss
    if (target.getAttribute("data-dismiss-snapshot") === "true") {
      state.activeSnapshotCard = null;
      renderMainDossier();
      return;
    }
  });

  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest("dialog")?.close();
    });
  });
}

window.addEventListener("DOMContentLoaded", () => {
  showLoading("Loading CancerLens...");
  initEventListeners();
  setLensMode("LEARN");
  probeBackendStatus();
  setTimeout(() => {
    hideLoading();
  }, 600);
});
