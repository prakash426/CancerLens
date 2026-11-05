/**
 * CancerLens — Frontend Taxonomy & Exact `ResultEnvelope` Wire Contract Preview Data
 * Strictly adheres to `Track1_Stage1_Backend_Handoff.md` (`snake_case` wire format).
 * Clearly badged as "UI Preview Envelope" whenever `http://127.0.0.1:8000` is offline.
 */

window.CancerLensData = window.CancerLensData || {};

const CLINICAL_CATEGORIES = [
  { slug: "overview", title: "Overview", icon: "📖", status: "COVERED" },
  { slug: "symptoms", title: "Symptoms", icon: "🩺", status: "COVERED" },
  { slug: "risk_factors", title: "Risk Factors", icon: "⚠️", status: "COVERED" },
  { slug: "prevention", title: "Prevention", icon: "🛡️", status: "COVERED" },
  { slug: "screening", title: "Screening", icon: "🔍", status: "COVERED" },
  { slug: "diagnosis", title: "Diagnosis", icon: "🧪", status: "COVERED" },
  { slug: "staging", title: "Staging", icon: "📊", status: "COVERED" },
  { slug: "treatment", title: "Treatment", icon: "💊", status: "COVERED" },
  { slug: "supportive_care", title: "Supportive Care", icon: "🤝", status: "PARTIAL" },
  { slug: "side_effects", title: "Side Effects", icon: "📋", status: "PARTIAL" },
  { slug: "prognosis_survival", title: "Prognosis & Survival", icon: "📈", status: "COVERAGE_GAP" }
];

const CANCER_CATALOG_25 = [
  {
    cancer_id: "lung-cancer",
    canonical_name: "Lung Cancer (Non-Small Cell & Small Cell)",
    short_label: "Lung cancer (Non-Small Cell & Small Cell)",
    group: "Common (20)",
    aliases: "Bronchogenic carcinoma, NSCLC, SCLC, Pulmonary neoplasm",
    anatomical_site: "Lungs, bronchi, and pleural membranes",
    featured_suggestion: true,
    subtypes: [
      { id: "all", label: "All Subtypes (NSCLC & SCLC)" },
      { id: "nsclc", label: "NSCLC (Non-Small Cell — ~85%)" },
      { id: "sclc", label: "SCLC (Small Cell — ~15%)" }
    ]
  },
  {
    cancer_id: "breast-cancer",
    canonical_name: "Breast Cancer (Invasive & Ductal/Lobular Subtypes)",
    short_label: "Breast cancer",
    group: "Common (20)",
    aliases: "Mammary carcinoma, IDC, ILC, HER2+ breast cancer, TNBC",
    anatomical_site: "Breast ducts, lobules, and regional lymph nodes",
    featured_suggestion: true,
    subtypes: [
      { id: "all", label: "All Subtypes" },
      { id: "hr-pos-her2-neg", label: "HR+ / HER2- (Luminal)" },
      { id: "her2-pos", label: "HER2-Positive" },
      { id: "tnbc", label: "Triple-Negative (TNBC)" }
    ]
  },
  {
    cancer_id: "colorectal-cancer",
    canonical_name: "Colorectal Cancer (Colon & Rectal Adenocarcinoma)",
    short_label: "Colorectal cancer",
    group: "Common (20)",
    aliases: "Bowel cancer, Colon adenocarcinoma, Rectal carcinoma, CRC",
    anatomical_site: "Colon, rectum, and gastrointestinal tract",
    featured_suggestion: true,
    subtypes: [
      { id: "all", label: "All Subtypes" },
      { id: "msi-h", label: "MSI-High / dMMR" },
      { id: "mss", label: "Microsatellite Stable (MSS)" }
    ]
  },
  {
    cancer_id: "ovarian-cancer",
    canonical_name: "Ovarian Cancer (Epithelial, Germ Cell & Stromal)",
    short_label: "Ovarian cancer",
    group: "Common (20)",
    aliases: "Ovarian epithelial carcinoma, High-grade serous ovarian cancer, Fallopian tube / Peritoneal cancer",
    anatomical_site: "Ovaries, fallopian tubes, and peritoneum",
    featured_suggestion: true,
    subtypes: [
      { id: "all", label: "All Ovarian Subtypes" },
      { id: "epithelial", label: "Epithelial Ovarian (~90%)" },
      { id: "germ-cell", label: "Germ Cell & Stromal" }
    ]
  },
  {
    cancer_id: "cervical-cancer",
    canonical_name: "Cervical Cancer (Squamous Cell & Adenocarcinoma)",
    short_label: "Cervical cancer",
    group: "Common (20)",
    aliases: "Uterine cervix carcinoma, HPV-associated cervical neoplasm",
    anatomical_site: "Cervix uteri (transformation zone)",
    featured_suggestion: true,
    subtypes: [
      { id: "all", label: "All Subtypes" },
      { id: "scc", label: "Squamous Cell Carcinoma" },
      { id: "adenocarcinoma", label: "Cervical Adenocarcinoma" }
    ]
  },
  {
    cancer_id: "pancreatic-cancer",
    canonical_name: "Pancreatic Cancer (Ductal Adenocarcinoma & Neuroendocrine)",
    short_label: "Pancreatic cancer",
    group: "Common (20)",
    aliases: "PDAC, Pancreatic exocrine carcinoma, PanNET",
    anatomical_site: "Exocrine and endocrine pancreas",
    featured_suggestion: true,
    subtypes: [
      { id: "all", label: "All Subtypes" },
      { id: "pdac", label: "Exocrine (PDAC — ~95%)" },
      { id: "pannet", label: "Pancreatic Neuroendocrine (PanNET)" }
    ]
  },
  {
    cancer_id: "prostate-cancer",
    canonical_name: "Prostate Cancer (Acinar Adenocarcinoma)",
    short_label: "Prostate cancer",
    group: "Common (20)",
    aliases: "Prostatic adenocarcinoma, mCRPC, mHSPC",
    anatomical_site: "Prostate gland",
    featured_suggestion: true,
    subtypes: [{ id: "all", label: "All Prostate Subtypes" }]
  },
  {
    cancer_id: "leukaemia",
    canonical_name: "Leukemia (AML, ALL, CLL & CML)",
    short_label: "Leukemia (AML / ALL)",
    group: "Common (20)",
    aliases: "Leukaemia, Acute myeloid leukemia (AML), Acute lymphoblastic leukemia (ALL), CLL, CML",
    anatomical_site: "Bone marrow, blood, and hematopoietic system",
    featured_suggestion: true,
    subtypes: [
      { id: "all", label: "All Leukemia Subtypes" },
      { id: "aml", label: "Acute Myeloid (AML)" },
      { id: "all-sub", label: "Acute Lymphoblastic (ALL)" }
    ]
  },
  {
    cancer_id: "mesothelioma",
    canonical_name: "Mesothelioma (Pleural & Peritoneal Asbestos-Associated)",
    short_label: "Pleural mesothelioma (Rare)",
    group: "Rare / Critical (5)",
    aliases: "Malignant pleural mesothelioma, MPM, Peritoneal mesothelioma",
    anatomical_site: "Pleural and peritoneal mesothelium",
    featured_suggestion: true,
    subtypes: [{ id: "all", label: "Epithelioid / Sarcomatoid / Biphasic" }]
  },
  {
    cancer_id: "bladder-cancer",
    canonical_name: "Bladder Cancer (Urothelial Carcinoma)",
    short_label: "Bladder cancer",
    group: "Common (20)",
    aliases: "Urothelial carcinoma, Transitional cell carcinoma, NMIBC, MIBC",
    anatomical_site: "Urinary bladder and urothelial tract",
    subtypes: [
      { id: "all", label: "All Bladder Subtypes" },
      { id: "nmibc", label: "Non-Muscle Invasive (NMIBC)" },
      { id: "mibc", label: "Muscle-Invasive (MIBC)" }
    ]
  },
  {
    cancer_id: "kidney-cancer",
    canonical_name: "Kidney Cancer (Renal Cell Carcinoma)",
    short_label: "Kidney cancer",
    group: "Common (20)",
    aliases: "Renal cell carcinoma, Clear cell RCC, Renal adenocarcinoma",
    anatomical_site: "Renal cortex and kidney parenchyma",
    subtypes: [{ id: "all", label: "All Renal Subtypes (ccRCC & Non-Clear Cell)" }]
  },
  {
    cancer_id: "liver-cancer",
    canonical_name: "Liver Cancer (Hepatocellular Carcinoma & Cholangiocarcinoma)",
    short_label: "Liver cancer",
    group: "Common (20)",
    aliases: "Hepatocellular carcinoma (HCC), Intrahepatic bile duct cancer",
    anatomical_site: "Liver hepatocytes and intrahepatic bile ducts",
    subtypes: [{ id: "all", label: "All Liver Subtypes (HCC & Bile Duct)" }]
  },
  {
    cancer_id: "stomach-cancer",
    canonical_name: "Stomach (Gastric) Cancer",
    short_label: "Stomach cancer",
    group: "Common (20)",
    aliases: "Gastric adenocarcinoma, Gastroesophageal junction cancer",
    anatomical_site: "Stomach lining and gastric mucosa",
    subtypes: [{ id: "all", label: "All Gastric Subtypes" }]
  },
  {
    cancer_id: "thyroid-cancer",
    canonical_name: "Thyroid Cancer (Papillary, Follicular, Medullary & Anaplastic)",
    short_label: "Thyroid cancer",
    group: "Common (20)",
    aliases: "Papillary thyroid carcinoma, Follicular thyroid cancer, MTC, ATC",
    anatomical_site: "Thyroid gland",
    subtypes: [{ id: "all", label: "All Thyroid Subtypes" }]
  },
  {
    cancer_id: "uterine-corpus-cancer",
    canonical_name: "Uterine & Endometrial Cancer",
    short_label: "Uterine / Endometrial cancer",
    group: "Common (20)",
    aliases: "Endometrial carcinoma, Uterine sarcoma, Corpus uteri cancer",
    anatomical_site: "Uterine endometrium and myometrium",
    subtypes: [{ id: "all", label: "All Uterine / Endometrial Subtypes" }]
  },
  {
    cancer_id: "melanoma-of-skin",
    canonical_name: "Melanoma of the Skin",
    short_label: "Melanoma of skin",
    group: "Common (20)",
    aliases: "Cutaneous melanoma, Malignant melanoma, BRAF-mutant melanoma",
    anatomical_site: "Cutaneous melanocytes (skin)",
    subtypes: [{ id: "all", label: "All Cutaneous Melanoma Subtypes" }]
  },
  {
    cancer_id: "non-hodgkin-lymphoma",
    canonical_name: "Non-Hodgkin Lymphoma (B-Cell & T-Cell)",
    short_label: "Non-Hodgkin lymphoma",
    group: "Common (20)",
    aliases: "NHL, DLBCL, Follicular lymphoma",
    anatomical_site: "Lymph nodes and lymphatic system",
    subtypes: [{ id: "all", label: "All NHL Subtypes (B-Cell & T-Cell)" }]
  },
  {
    cancer_id: "hodgkin-lymphoma",
    canonical_name: "Hodgkin Lymphoma",
    short_label: "Hodgkin lymphoma",
    group: "Common (20)",
    aliases: "Classical Hodgkin lymphoma (cHL), Reed-Sternberg lymphoma",
    anatomical_site: "Lymph nodes and lymphoid tissue",
    subtypes: [{ id: "all", label: "All Hodgkin Subtypes" }]
  },
  {
    cancer_id: "oesophageal-cancer",
    canonical_name: "Esophageal (Oesophageal) Cancer",
    short_label: "Esophageal cancer",
    group: "Common (20)",
    aliases: "Oesophageal squamous cell carcinoma, Esophageal adenocarcinoma",
    anatomical_site: "Esophagus and gastroesophageal junction",
    subtypes: [{ id: "all", label: "Squamous Cell & Adenocarcinoma" }]
  },
  {
    cancer_id: "brain-cns-cancer",
    canonical_name: "Brain & Central Nervous System (CNS) Tumors",
    short_label: "Brain & CNS cancer",
    group: "Common (20)",
    aliases: "Glioblastoma, Astrocytoma, Meningioma, Primary CNS neoplasm",
    anatomical_site: "Brain and spinal cord (CNS)",
    subtypes: [{ id: "all", label: "All Primary Brain & CNS Subtypes" }]
  },
  {
    cancer_id: "lip-oral-cavity-cancer",
    canonical_name: "Lip & Oral Cavity (Head and Neck) Cancer",
    short_label: "Oral cavity cancer",
    group: "Common (20)",
    aliases: "Oral squamous cell carcinoma, Mouth and tongue cancer",
    anatomical_site: "Lips, tongue, gums, and oral cavity",
    subtypes: [{ id: "all", label: "All Oral Cavity Subtypes" }]
  },
  {
    cancer_id: "laryngeal-cancer",
    canonical_name: "Laryngeal (Voice Box) Cancer",
    short_label: "Laryngeal cancer",
    group: "Common (20)",
    aliases: "Glottic, Supraglottic, and Subglottic laryngeal carcinoma",
    anatomical_site: "Larynx (glottis, supraglottis, subglottis)",
    subtypes: [{ id: "all", label: "All Laryngeal Subtypes" }]
  },
  {
    cancer_id: "gallbladder-cancer",
    canonical_name: "Gallbladder & Biliary Tract Cancer",
    short_label: "Gallbladder cancer",
    group: "Rare / Critical (5)",
    aliases: "Gallbladder adenocarcinoma, Extrahepatic biliary cancer",
    anatomical_site: "Gallbladder and extrahepatic bile ducts",
    subtypes: [{ id: "all", label: "All Gallbladder Subtypes" }]
  },
  {
    cancer_id: "salivary-gland-cancer",
    canonical_name: "Salivary Gland Cancer (Rare)",
    short_label: "Salivary gland cancer (Rare)",
    group: "Rare / Critical (5)",
    aliases: "Parotid, Submandibular, and Minor salivary gland carcinoma",
    anatomical_site: "Major and minor salivary glands",
    subtypes: [{ id: "all", label: "All Salivary Gland Subtypes" }]
  },
  {
    cancer_id: "vaginal-cancer",
    canonical_name: "Vaginal Cancer (Rare)",
    short_label: "Vaginal cancer (Rare)",
    group: "Rare / Critical (5)",
    aliases: "Vaginal squamous cell carcinoma, Vaginal adenocarcinoma",
    anatomical_site: "Vaginal epithelium",
    subtypes: [{ id: "all", label: "All Vaginal Subtypes" }]
  },
  {
    cancer_id: "penile-cancer",
    canonical_name: "Penile Cancer (Rare)",
    short_label: "Penile cancer (Rare)",
    group: "Rare / Critical (5)",
    aliases: "Squamous cell carcinoma of the penis",
    anatomical_site: "Penile tissue",
    subtypes: [{ id: "all", label: "All Penile Subtypes" }]
  }
];

/**
 * Mode A (`LEARN`) Envelopes keyed by `cancer_id`
 */
const LEARN_ENVELOPES = {
  "lung-cancer": {
    request_id: "req_learn_lung_20261101",
    resolved_mode: "LEARN",
    pipeline_state: "DISPLAYABLE",
    retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
    interpreted_query_or_claim: "Lung Cancer (Non-Small Cell & Small Cell) — Overview, Symptoms, Treatment & Provenance",
    cancer_id: "lung-cancer",
    cancer_name: "Lung Cancer (Non-Small Cell & Small Cell)",
    subtype_id: "all",
    category_slug: "overview",
    overall_outcome_code: "SUPPORTED",
    overall_outcome_label: "Authoritative Multi-Source Profile (WHO + NCI + CDC)",
    ai_plain_language_summary:
      "Lung cancer affects the breathing organs and airways. It is divided clinically into Non-Small Cell Lung Cancer (NSCLC, accounting for ~85% of cases) and Small Cell Lung Cancer (SCLC, ~15% of cases, which tends to grow more rapidly). While tobacco smoking is the primary preventable risk factor, lung cancer also occurs in people who have never smoked due to radon gas, second-hand smoke, occupational exposures (such as asbestos), air pollution, or specific somatic driver mutations (such as EGFR, ALK, or ROS1).",
    treatment_approaches: [
      "Surgical lobectomy, segmentectomy, or wedge resection for early-stage resectable Non-Small Cell Lung Cancer (NSCLC)",
      "Stereotactic body radiation therapy (SBRT) for medically inoperable early-stage tumors",
      "Immune checkpoint inhibitors (anti-PD-1 / anti-PD-L1) either alone or combined with platinum-based chemotherapy",
      "Targeted oral kinase inhibitors for NSCLC tumors harboring verified driver mutations (e.g., EGFR, ALK, ROS1, BRAF)",
      "Concurrent platinum-etoposide chemotherapy and thoracic radiotherapy (with immunotherapy where indicated) for Small Cell Lung Cancer (SCLC)"
    ],
    symptoms_list: [
      "Persistent cough that does not improve after 2 to 3 weeks or changes character",
      "Coughing up blood or rust-colored sputum (hemoptysis)",
      "Progressive shortness of breath, wheezing, or unexplained hoarseness",
      "Dull or aching chest, shoulder, or back pain worsened by deep breathing or coughing",
      "Recurrent respiratory infections such as bronchitis or pneumonia that do not clear",
      "Unexplained weight loss, persistent fatigue, or loss of appetite"
    ],
    diagnostic_procedures: [
      "Low-dose computed tomography (LDCT) annual screening in eligible high-risk adults with heavy smoking history",
      "Tissue biopsy (bronchoscopy, endobronchial ultrasound EBUS, or CT-guided core needle biopsy) to confirm histology (NSCLC vs. SCLC)",
      "Comprehensive molecular biomarker testing (EGFR, ALK, ROS1, PD-L1 expression) before selecting systemic therapy in advanced NSCLC"
    ],
    common_claims_to_verify: [
      {
        claim_text: "Does high-dose IV vitamin C cure stage IV lung cancer without chemotherapy?",
        badge: "Preclinical vs. Human Mismatch"
      },
      {
        claim_text: "Can non-smokers develop EGFR-mutated non-small cell lung cancer?",
        badge: "Supported Clinical Fact"
      },
      {
        claim_text: "Do herbal lung detox teas reverse smoking-induced lung tumors?",
        badge: "Contradicted by Evidence"
      }
    ],
    evidence_items: [
      {
        fact_id: "CIAPI-WHO-LC-001",
        document_id: "DOC-WHO-LUNG-2026",
        source_id: "WHO",
        origin_source_id: "WHO-HQ",
        organization_name: "World Health Organization (WHO)",
        permission_reference: "WHO Licence 202610792",
        source_title: "WHO Cancer Fact Sheet — Lung Cancer Prevention, Early Detection & Management",
        canonical_url: "https://www.who.int/news-room/fact-sheets/detail/lung-cancer",
        cancer_id: "lung-cancer",
        subtype_id: "all",
        category_slug: "overview",
        structured_fact_or_summary:
          "WHO reports that lung cancer is the leading cause of cancer-related mortality worldwide. Tobacco smoking accounts for approximately 85% of cases, while radon, occupational carcinogens, and indoor/outdoor air pollution contribute to cases in non-smokers.",
        limited_verbatim_excerpt:
          "\"Lung cancer is the leading cause of cancer-related deaths worldwide, with non-small cell lung cancer (NSCLC) and small cell lung cancer (SCLC) requiring distinct diagnostic and therapeutic pathways.\"",
        study_design_scope: "guideline",
        population_scope: "human_adult_general",
        jurisdiction_code: "GLOBAL",
        observed_source_date: "2023-06-26",
        retrieved_at_utc: "2026-10-31T18:30:00Z",
        reviewed_at_date: "2026-10-31",
        attribution_text:
          "Source: World Health Organization (WHO), Lung Cancer Fact Sheet. Used under WHO Non-Exclusive Licence 202610792. Independently developed; not published, endorsed, or sponsored by WHO.",
        ai_processing_allowed: true
      },
      {
        fact_id: "CIAPI-NCI-LC-004",
        document_id: "DOC-NCI-PDQ-NSCLC",
        source_id: "NCI",
        origin_source_id: "NIH-NCI",
        organization_name: "National Cancer Institute (NCI) & CDC",
        permission_reference: "US Government Public Domain / NCI PDQ Reuse Policy",
        source_title: "Non-Small Cell Lung Cancer Treatment (PDQ) & CDC Screening Guidance",
        canonical_url: "https://www.cancer.gov/types/lung/patient/non-small-cell-lung-treatment-pdq",
        cancer_id: "lung-cancer",
        subtype_id: "nsclc",
        category_slug: "treatment",
        structured_fact_or_summary:
          "NCI PDQ guidelines specify that treatment selection for NSCLC depends on stage, histology, performance status, and actionable molecular alterations (including EGFR, ALK, ROS1, BRAF, MET, RET, and NTRK). Low-dose CT (LDCT) screening reduces lung cancer mortality in eligible high-risk adults.",
        limited_verbatim_excerpt:
          "\"Patients with advanced non-small cell lung cancer should undergo testing for actionable oncogenic driver mutations and PD-L1 expression prior to initiating systemic therapy.\"",
        study_design_scope: "guideline",
        population_scope: "human_adult_general",
        jurisdiction_code: "US",
        observed_source_date: "2026-02-14",
        retrieved_at_utc: "2026-10-31T18:30:00Z",
        reviewed_at_date: "2026-10-31",
        attribution_text:
          "Source: National Cancer Institute (NCI), Non-Small Cell Lung Cancer Treatment (PDQ®). Public domain US federal health resource; NCI does not endorse third-party applications.",
        ai_processing_allowed: true
      }
    ],
    limitations_and_gaps_note:
      "General educational summary only. Prognosis and survival statistics vary substantially by TNM stage at diagnosis, molecular subtype, and individual clinical factors. Not personal medical advice.",
    telemetry: {
      request_id: "req_learn_lung_20261101",
      pipeline_state: "DISPLAYABLE",
      retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
      primary_provider: "meta_model_api",
      primary_model: "muse-spark-1.3",
      total_latency_ms: 840,
      hops_executed: 1,
      learned_query_mapping_applied: null,
      meta_pool_spent_usd: 0.0042,
      meta_pool_remaining_usd: 149.99,
      baseten_pool_spent_usd: 0.0018,
      baseten_pool_remaining_usd: 99.99
    }
  },

  "breast-cancer": {
    request_id: "req_learn_breast_20261101",
    resolved_mode: "LEARN",
    pipeline_state: "DISPLAYABLE",
    retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
    interpreted_query_or_claim: "Breast Cancer (HR+/HER2-, HER2+, Triple-Negative TNBC) — Overview & Evidence Profile",
    cancer_id: "breast-cancer",
    cancer_name: "Breast Cancer (Invasive Ductal, Lobular & Molecular Subtypes)",
    subtype_id: "all",
    category_slug: "overview",
    overall_outcome_code: "SUPPORTED",
    overall_outcome_label: "Authoritative Multi-Source Profile (WHO + NCI)",
    ai_plain_language_summary:
      "Breast cancer arises in the lining cells (epithelium) of the ducts (85%) or lobules (15%) in the glandular tissue of the breast. Treatment and biology depend heavily on receptor status: Hormone Receptor-positive (ER+/PR+), HER2-positive (HER2 protein overexpression), and Triple-Negative Breast Cancer (TNBC, lacking ER, PR, and HER2). Early detection through organized mammography screening and timely multimodality therapy substantially improves survival outcomes.",
    treatment_approaches: [
      "Breast-conserving surgery (lumpectomy plus radiation) or mastectomy with sentinel lymph node biopsy for localized disease",
      "Endocrine therapy (tamoxifen or aromatase inhibitors, often paired with CDK4/6 inhibitors) for ER+/PR+ breast cancer",
      "HER2-targeted monoclonal antibodies and antibody-drug conjugates (trastuzumab, pertuzumab, T-DXd) for HER2-positive and HER2-low subtypes",
      "Neoadjuvant/adjuvant chemotherapy plus immune checkpoint blockade (pembrolizumab) or PARP inhibitors (for germline BRCA1/2 carriers) in Triple-Negative Breast Cancer (TNBC)"
    ],
    symptoms_list: [
      "A painless lump or thickening in the breast or underarm (axilla) that persists",
      "Change in the size, shape, or contour of the breast",
      "Dimpling, puckering, redness, or pitting of the breast skin (resembling orange peel)",
      "Nipple inversion, skin flaking around the nipple, or spontaneous bloody/clear nipple discharge"
    ],
    diagnostic_procedures: [
      "Diagnostic mammography and targeted breast ultrasound",
      "Core needle biopsy with immunohistochemistry (IHC) and ISH testing for Estrogen Receptor (ER), Progesterone Receptor (PR), and HER2 status",
      "Germline genetic testing (BRCA1, BRCA2, PALB2) in eligible patients"
    ],
    common_claims_to_verify: [
      {
        claim_text: "I read that eating sugar directly causes breast cancer and vitamin C cures breast cancer.",
        badge: "Compound Claim (T3 Test Case)"
      },
      {
        claim_text: "Do underwire bras or antiperspirants cause breast cancer?",
        badge: "Contradicted by Epidemiology"
      }
    ],
    evidence_items: [
      {
        fact_id: "CIAPI-WHO-BC-001",
        document_id: "DOC-WHO-BREAST-2026",
        source_id: "WHO",
        origin_source_id: "WHO-HQ",
        organization_name: "World Health Organization (WHO)",
        permission_reference: "WHO Licence 202610792",
        source_title: "WHO Fact Sheet: Breast Cancer Global Burden, Risk Factors & Control",
        canonical_url: "https://www.who.int/news-room/fact-sheets/detail/breast-cancer",
        cancer_id: "breast-cancer",
        subtype_id: "all",
        category_slug: "overview",
        structured_fact_or_summary:
          "WHO states that breast cancer is the most commonly diagnosed cancer globally in women. Approximately half of breast cancers develop in women with no identifiable specific risk factor other than sex and age (over 40 years).",
        limited_verbatim_excerpt:
          "\"Breast cancer treatment can be highly effective, achieving survival probabilities of 90% or higher, particularly when the disease is identified early.\"",
        study_design_scope: "guideline",
        population_scope: "human_adult_general",
        jurisdiction_code: "GLOBAL",
        observed_source_date: "2024-03-13",
        retrieved_at_utc: "2026-10-31T18:30:00Z",
        reviewed_at_date: "2026-10-31",
        attribution_text:
          "Source: World Health Organization (WHO), Breast Cancer Fact Sheet. Used under WHO Non-Exclusive Licence 202610792. Independently developed; not published, endorsed, or sponsored by WHO.",
        ai_processing_allowed: true
      },
      {
        fact_id: "CIAPI-NCI-BC-009",
        document_id: "DOC-NCI-PDQ-BREAST",
        source_id: "NCI",
        origin_source_id: "NIH-NCI",
        organization_name: "National Cancer Institute (NCI)",
        permission_reference: "US Government Public Domain / NCI PDQ Reuse Policy",
        source_title: "Breast Cancer Treatment (PDQ) — Health Professional & Patient Version",
        canonical_url: "https://www.cancer.gov/types/breast/patient/breast-treatment-pdq",
        cancer_id: "breast-cancer",
        subtype_id: "all",
        category_slug: "treatment",
        structured_fact_or_summary:
          "NCI PDQ documents that hormone receptor status (ER/PR), HER2 expression, anatomic stage, and menopausal status govern systemic therapy selection.",
        limited_verbatim_excerpt:
          "\"Estrogen receptor (ER), progesterone receptor (PR), and HER2 status must be determined on all invasive breast cancers to guide systemic therapy.\"",
        study_design_scope: "guideline",
        population_scope: "human_adult_general",
        jurisdiction_code: "US",
        observed_source_date: "2026-01-19",
        retrieved_at_utc: "2026-10-31T18:30:00Z",
        reviewed_at_date: "2026-10-31",
        attribution_text:
          "Source: National Cancer Institute (NCI), Breast Cancer Treatment (PDQ®). Public domain federal health information.",
        ai_processing_allowed: true
      }
    ],
    limitations_and_gaps_note:
      "Educational overview only. Subtype-specific therapy decisions require pathology review by a licensed oncology team.",
    telemetry: {
      request_id: "req_learn_breast_20261101",
      pipeline_state: "DISPLAYABLE",
      retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
      primary_provider: "meta_model_api",
      primary_model: "muse-spark-1.3",
      total_latency_ms: 790,
      hops_executed: 1,
      learned_query_mapping_applied: null,
      meta_pool_spent_usd: 0.0042,
      meta_pool_remaining_usd: 149.99,
      baseten_pool_spent_usd: 0.0018,
      baseten_pool_remaining_usd: 99.99
    }
  }
};

/**
 * Mode B (`EVALUATE`) Scenarios Powered by the Baseten Claim Verification Layer (`meta-models/muse-spark-open-1026`)
 */
const EVALUATE_SCENARIOS = {
  "sugar-vitamin-c-compound": {
    request_id: "req_eval_t3_compound_20261101",
    resolved_mode: "EVALUATE",
    pipeline_state: "DISPLAYABLE",
    retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
    interpreted_query_or_claim:
      "I read that eating sugar directly causes breast cancer and vitamin C cures breast cancer.",
    cancer_id: "breast-cancer",
    cancer_name: "Breast Cancer",
    subtype_id: "all",
    category_slug: "risk_factors",
    overall_outcome_code: "MIXED_OR_CONTEXT_DEPENDENT",
    overall_outcome_label: "Compound Claim Split (2 Atomic Claims): Context-Dependent + Contradicted",
    ai_plain_language_summary:
      "Baseten's Claim Verification Layer (`meta-models/muse-spark-open-1026`) split your submission into two distinct atomic claims and verified each against rights-cleared WHO and NCI evidence. First, eating dietary sugar does not directly cause breast cancer on its own, though chronic excess caloric intake leading to obesity is an established risk factor for postmenopausal breast cancer. Second, vitamin C (whether oral or intravenous) does not cure breast cancer; human clinical trials have shown no curative efficacy, and substituting vitamin C for standard oncology care lowers survival.",
    atomic_claim_verdicts: [
      {
        subclaim_id: "subclaim-1",
        atomic_claim_text: "Eating dietary sugar directly causes breast cancer in humans.",
        outcome_code: "MIXED_OR_CONTEXT_DEPENDENT",
        outcome_label: "Mixed / Context-Dependent (Indirect Obesity Pathway Only)",
        ai_plain_language_explanation:
          "Glucose is utilized by all healthy and malignant cells in the body; eating carbohydrates or sugar does not directly initiate breast tumors. However, WHO and NCI note that high-calorie diets contributing to overweight/obesity and hyperinsulinemia indirectly increase postmenopausal breast cancer risk.",
        cited_fact_ids: ["CIAPI-WHO-BC-001", "CIAPI-NCI-NUTR-01"],
        cited_document_ids: ["DOC-WHO-BREAST-2026", "DOC-NCI-PDQ-NUTRITION"],
        verbatim_quote_verified: true,
        stage4_downgraded: false,
        stage4_downgrade_reason: null,
        pivot_to_learn_cancer_id: "breast-cancer",
        pivot_to_learn_category_slug: "risk_factors",
        context_comparisons_5d: [
          {
            dimension_name: "cancer_and_subtype",
            claim_assumes: "All breast cancers directly triggered by dietary sugar",
            evidence_actually_shows: "Postmenopausal hormone-receptor-positive risk linked to adiposity/obesity, not direct sugar toxicity",
            is_mismatch: true
          },
          {
            dimension_name: "population_and_stage",
            claim_assumes: "General human population regardless of metabolic state",
            evidence_actually_shows: "Epidemiological risk is mediated by BMI/adiposity and physical inactivity",
            is_mismatch: true
          },
          {
            dimension_name: "study_design",
            claim_assumes: "Direct causal proof in humans",
            evidence_actually_shows: "Cell-culture Warburg effect studies vs. human observational cohort studies",
            is_mismatch: true
          },
          {
            dimension_name: "endpoint_measured",
            claim_assumes: "Direct tumor initiation from sugar consumption",
            evidence_actually_shows: "Long-term weight-related incidence risk",
            is_mismatch: true
          },
          {
            dimension_name: "caveat_or_dose",
            claim_assumes: "Eliminating all dietary carbohydrates starves tumors",
            evidence_actually_shows: "Extreme restriction during treatment can cause dangerous weight loss and cachexia",
            is_mismatch: true
          }
        ]
      },
      {
        subclaim_id: "subclaim-2",
        atomic_claim_text: "Vitamin C cures breast cancer in humans.",
        outcome_code: "CONTRADICTED",
        outcome_label: "Contradicted by Human Clinical Evidence",
        ai_plain_language_explanation:
          "While high-concentration ascorbic acid can slow cancer cell growth in laboratory Petri dishes (in vitro) or mouse xenografts, randomized human clinical trials and NCI PDQ reviews confirm that neither oral nor intravenous vitamin C cures breast cancer.",
        cited_fact_ids: ["CIAPI-NCI-CAM-VITC-02"],
        cited_document_ids: ["DOC-NCI-PDQ-IV-VITC"],
        verbatim_quote_verified: true,
        stage4_downgraded: false,
        stage4_downgrade_reason: null,
        pivot_to_learn_cancer_id: "breast-cancer",
        pivot_to_learn_category_slug: "treatment",
        context_comparisons_5d: [
          {
            dimension_name: "cancer_and_subtype",
            claim_assumes: "Curative monotherapy for human breast cancer",
            evidence_actually_shows: "Investigated only as an adjunct for supportive quality-of-life endpoints",
            is_mismatch: true
          },
          {
            dimension_name: "population_and_stage",
            claim_assumes: "Patients with invasive or metastatic breast cancer",
            evidence_actually_shows: "Cytotoxic effects observed only in isolated cell lines / mouse models",
            is_mismatch: true
          },
          {
            dimension_name: "study_design",
            claim_assumes: "Proven in human clinical trials",
            evidence_actually_shows: "Preclinical in vitro studies vs. negative randomized controlled human trials",
            is_mismatch: true
          },
          {
            dimension_name: "endpoint_measured",
            claim_assumes: "Complete cure / tumor eradication",
            evidence_actually_shows: "No overall survival or curative benefit as standalone therapy in humans",
            is_mismatch: true
          },
          {
            dimension_name: "caveat_or_dose",
            claim_assumes: "Oral or IV vitamin C replaces standard therapy",
            evidence_actually_shows: "High-dose IV vitamin C can interact with certain chemotherapies and cause renal oxalate toxicity in G6PD deficiency",
            is_mismatch: true
          }
        ]
      }
    ],
    related_reviewed_claims: [
      {
        claim_memory_id: "CM-REV-001",
        canonical_claim_text: "Strict ketogenic or zero-sugar diets alone cure advanced solid tumors without systemic therapy.",
        primary_outcome_code: "CONTRADICTED",
        outcome_label: "Contradicted (Reviewed Library Entry)",
        nuance_warning_note: "Preclinical mouse diet studies do not translate to standalone human cures.",
        how_this_differs_note: "Focuses on ketogenic diet monotherapy rather than sugar as an etiology risk factor."
      },
      {
        claim_memory_id: "CM-REV-002",
        canonical_claim_text: "Intravenous high-dose vitamin C is FDA-approved as a curative cancer treatment.",
        primary_outcome_code: "CONTRADICTED",
        outcome_label: "Contradicted (Reviewed Library Entry)",
        nuance_warning_note: "Not FDA-approved for treating cancer; studied only in supportive/adjunctive trials.",
        how_this_differs_note: "Addresses regulatory approval status specifically."
      }
    ],
    evidence_items: [
      {
        fact_id: "CIAPI-NCI-CAM-VITC-02",
        document_id: "DOC-NCI-PDQ-IV-VITC",
        source_id: "NCI",
        origin_source_id: "NIH-NCI",
        organization_name: "National Cancer Institute (NCI)",
        permission_reference: "US Government Public Domain / NCI PDQ Reuse Policy",
        source_title: "Intravenous Vitamin C (PDQ®) — Integrative, Alternative, and Complementary Therapies",
        canonical_url: "https://www.cancer.gov/about-cancer/treatment/cam/patient/vitamin-c-pdq",
        cancer_id: "breast-cancer",
        subtype_id: "all",
        category_slug: "treatment",
        structured_fact_or_summary:
          "NCI PDQ reports that randomized controlled trials of oral vitamin C in patients with advanced cancer showed no survival benefit, and intravenous vitamin C is not approved as a standalone treatment for breast or other cancers.",
        limited_verbatim_excerpt:
          "\"The U.S. Food and Drug Administration (FDA) has not approved the use of intravenous high-dose vitamin C as a treatment for cancer.\"",
        study_design_scope: "rct_meta",
        population_scope: "human_adult_general",
        jurisdiction_code: "US",
        observed_source_date: "2025-11-08",
        retrieved_at_utc: "2026-10-31T19:15:00Z",
        reviewed_at_date: "2026-10-31",
        attribution_text:
          "Source: National Cancer Institute (NCI), Intravenous Vitamin C (PDQ®). Public domain US federal health resource.",
        ai_processing_allowed: true
      },
      {
        fact_id: "CIAPI-WHO-BC-001",
        document_id: "DOC-WHO-BREAST-2026",
        source_id: "WHO",
        origin_source_id: "WHO-HQ",
        organization_name: "World Health Organization (WHO)",
        permission_reference: "WHO Licence 202610792",
        source_title: "WHO Fact Sheet: Breast Cancer Modifiable Risk Factors",
        canonical_url: "https://www.who.int/news-room/fact-sheets/detail/breast-cancer",
        cancer_id: "breast-cancer",
        subtype_id: "all",
        category_slug: "risk_factors",
        structured_fact_or_summary:
          "WHO identifies age, obesity, harmful use of alcohol, family history, radiation exposure, reproductive history, tobacco use, and postmenopausal hormone therapy as established breast cancer risk factors.",
        limited_verbatim_excerpt:
          "\"Certain factors increase the risk of breast cancer including increasing age, obesity, harmful use of alcohol, family history of breast cancer, history of radiation exposure, reproductive history, tobacco use and postmenopausal hormone therapy.\"",
        study_design_scope: "guideline",
        population_scope: "human_adult_general",
        jurisdiction_code: "GLOBAL",
        observed_source_date: "2024-03-13",
        retrieved_at_utc: "2026-10-31T19:15:00Z",
        reviewed_at_date: "2026-10-31",
        attribution_text:
          "Source: World Health Organization (WHO), Breast Cancer Fact Sheet. Used under WHO Non-Exclusive Licence 202610792. Independently developed; not published, endorsed, or sponsored by WHO.",
        ai_processing_allowed: true
      }
    ],
    limitations_and_gaps_note:
      "Evaluated strictly against rights-cleared WHO and NCI PDQ evidence. Does not constitute individualized nutritional or oncology prescribing advice.",
    telemetry: {
      request_id: "req_eval_t3_compound_20261101",
      pipeline_state: "DISPLAYABLE",
      retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
      primary_provider: "baseten_model_api",
      primary_model: "meta-models/muse-spark-open-1026",
      total_latency_ms: 1420,
      hops_executed: 2,
      learned_query_mapping_applied: "sugar feeds cancer -> dietary glycemic load adiposity risk",
      meta_pool_spent_usd: 0.0042,
      meta_pool_remaining_usd: 149.99,
      baseten_pool_spent_usd: 0.0029,
      baseten_pool_remaining_usd: 99.99
    }
  },

  "alkaline-water-pancreatic": {
    request_id: "req_eval_alkaline_20261101",
    resolved_mode: "EVALUATE",
    pipeline_state: "DISPLAYABLE",
    retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
    interpreted_query_or_claim: "Drinking alkaline water or baking soda cures stage IV pancreatic cancer.",
    cancer_id: "pancreatic-cancer",
    cancer_name: "Pancreatic Cancer",
    subtype_id: "pdac",
    category_slug: "treatment",
    overall_outcome_code: "CONTRADICTED",
    overall_outcome_label: "Contradicted by Human Physiology & Clinical Oncology Evidence",
    ai_plain_language_summary:
      "Baseten's Claim Verification Layer (`meta-models/muse-spark-open-1026`) evaluated this claim against NCI evidence. Human blood pH is tightly regulated between 7.35 and 7.45 by the lungs and kidneys regardless of dietary alkaline water intake. No human clinical study shows that alkaline water or sodium bicarbonate cures pancreatic adenocarcinoma.",
    atomic_claim_verdicts: [
      {
        subclaim_id: "subclaim-1",
        atomic_claim_text: "Drinking alkaline water alters systemic blood pH to cure stage IV pancreatic cancer.",
        outcome_code: "CONTRADICTED",
        outcome_label: "Contradicted",
        ai_plain_language_explanation:
          "Stomach acid neutralizes ingested alkaline water before it reaches the bloodstream. While solid tumors create a localized acidic microenvironment due to glycolysis, drinking alkaline water cannot selectively alkalinize or eradicate pancreatic tumors in humans.",
        cited_fact_ids: ["CIAPI-NCI-PAAD-003"],
        cited_document_ids: ["DOC-NCI-PDQ-PANCREATIC"],
        verbatim_quote_verified: true,
        stage4_downgraded: false,
        stage4_downgrade_reason: null,
        pivot_to_learn_cancer_id: "pancreatic-cancer",
        pivot_to_learn_category_slug: "treatment",
        context_comparisons_5d: [
          {
            dimension_name: "cancer_and_subtype",
            claim_assumes: "Stage IV Pancreatic Ductal Adenocarcinoma (PDAC)",
            evidence_actually_shows: "Standard systemic therapy uses FOLFIRINOX or gemcitabine/nab-paclitaxel",
            is_mismatch: true
          },
          {
            dimension_name: "population_and_stage",
            claim_assumes: "Human patients with metastatic disease",
            evidence_actually_shows: "Cell-culture dish pH experiments only; zero human survival benefit",
            is_mismatch: true
          },
          {
            dimension_name: "study_design",
            claim_assumes: "Clinical efficacy in humans",
            evidence_actually_shows: "In vitro extracellular pH buffers vs. human systemic physiology",
            is_mismatch: true
          },
          {
            dimension_name: "endpoint_measured",
            claim_assumes: "Complete remission / cure",
            evidence_actually_shows: "No tumor regression in human clinical oncology",
            is_mismatch: true
          },
          {
            dimension_name: "caveat_or_dose",
            claim_assumes: "Excess baking soda / alkaline intake is harmless and curative",
            evidence_actually_shows: "Excessive sodium bicarbonate ingestion can cause metabolic alkalosis and electrolyte imbalances",
            is_mismatch: true
          }
        ]
      }
    ],
    related_reviewed_claims: [],
    evidence_items: [
      {
        fact_id: "CIAPI-NCI-PAAD-003",
        document_id: "DOC-NCI-PDQ-PANCREATIC",
        source_id: "NCI",
        origin_source_id: "NIH-NCI",
        organization_name: "National Cancer Institute (NCI)",
        permission_reference: "US Government Public Domain / NCI PDQ Reuse Policy",
        source_title: "Pancreatic Cancer Treatment (PDQ®) — Patient & Health Professional Overview",
        canonical_url: "https://www.cancer.gov/types/pancreatic/patient/pancreatic-treatment-pdq",
        cancer_id: "pancreatic-cancer",
        subtype_id: "pdac",
        category_slug: "treatment",
        structured_fact_or_summary:
          "NCI PDQ states that stage IV pancreatic cancer is treated with systemic chemotherapy, targeted therapy for specific biomarker-defined subsets, palliative radiation, and supportive care.",
        limited_verbatim_excerpt:
          "\"Standard treatment options for stage IV pancreatic cancer include systemic chemotherapy, targeted therapy, and clinical trials.\"",
        study_design_scope: "guideline",
        population_scope: "human_adult_general",
        jurisdiction_code: "US",
        observed_source_date: "2026-01-30",
        retrieved_at_utc: "2026-10-31T19:20:00Z",
        reviewed_at_date: "2026-10-31",
        attribution_text:
          "Source: National Cancer Institute (NCI), Pancreatic Cancer Treatment (PDQ®).",
        ai_processing_allowed: true
      }
    ],
    limitations_and_gaps_note: "General informational evaluation only. Always consult a board-certified oncologist.",
    telemetry: {
      request_id: "req_eval_alkaline_20261101",
      pipeline_state: "DISPLAYABLE",
      retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
      primary_provider: "baseten_model_api",
      primary_model: "meta-models/muse-spark-open-1026",
      total_latency_ms: 1180,
      hops_executed: 1,
      learned_query_mapping_applied: null,
      meta_pool_spent_usd: 0.0042,
      meta_pool_remaining_usd: 149.99,
      baseten_pool_spent_usd: 0.0038,
      baseten_pool_remaining_usd: 99.99
    }
  },

  "hpv-vaccine-cervical": {
    request_id: "req_eval_hpv_20261101",
    resolved_mode: "EVALUATE",
    pipeline_state: "DISPLAYABLE",
    retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
    interpreted_query_or_claim: "HPV vaccination prevents the majority of cervical cancer cases.",
    cancer_id: "cervical-cancer",
    cancer_name: "Cervical Cancer",
    subtype_id: "all",
    category_slug: "prevention",
    overall_outcome_code: "SUPPORTED",
    overall_outcome_label: "Supported by WHO & NCI Population-Scale Clinical Evidence",
    ai_plain_language_summary:
      "Baseten's Claim Verification Layer (`meta-models/muse-spark-open-1026`) verified that this claim is strongly supported by both WHO and NCI evidence. Persistent infection with high-risk human papillomavirus (HPV types 16 and 18 alone cause ~70% of cervical cancers, and nonavalent vaccines cover types responsible for ~90%) is the primary cause of cervical cancer. Vaccination prior to HPV exposure prevents the vast majority of cervical pre-cancers and invasive cervical cancers.",
    atomic_claim_verdicts: [
      {
        subclaim_id: "subclaim-1",
        atomic_claim_text: "HPV vaccination prevents the majority of cervical cancer cases when administered before exposure.",
        outcome_code: "SUPPORTED",
        outcome_label: "Supported (High-Confidence Guideline & Population Cohort Consensus)",
        ai_plain_language_explanation:
          "Large randomized clinical trials and national registry registries confirm that HPV vaccination dramatically reduces high-grade cervical intraepithelial neoplasia (CIN2/3) and invasive cervical cancer incidence.",
        cited_fact_ids: ["CIAPI-WHO-CC-001"],
        cited_document_ids: ["DOC-WHO-CERVICAL-2026"],
        verbatim_quote_verified: true,
        stage4_downgraded: false,
        stage4_downgrade_reason: null,
        pivot_to_learn_cancer_id: "cervical-cancer",
        pivot_to_learn_category_slug: "prevention",
        context_comparisons_5d: [
          {
            dimension_name: "cancer_and_subtype",
            claim_assumes: "Cervical squamous cell carcinoma and adenocarcinoma",
            evidence_actually_shows: "HPV types 16 and 18 cause >70% of all cervical cancers globally; 9-valent covers ~90%",
            is_mismatch: false
          },
          {
            dimension_name: "population_and_stage",
            claim_assumes: "Adolescents and young adults prior to HPV exposure",
            evidence_actually_shows: "Highest efficacy when given at ages 9–14 before sexual debut; routine cervical screening remains recommended",
            is_mismatch: false
          },
          {
            dimension_name: "study_design",
            claim_assumes: "Human clinical trials and population registries",
            evidence_actually_shows: "Phase III RCTs and nationwide population registry studies",
            is_mismatch: false
          },
          {
            dimension_name: "endpoint_measured",
            claim_assumes: "Prevention of invasive cervical cancer",
            evidence_actually_shows: "Substantial reduction in both CIN3 precancerous lesions and invasive cervical carcinoma",
            is_mismatch: false
          },
          {
            dimension_name: "caveat_or_dose",
            claim_assumes: "Primary preventive vaccination",
            evidence_actually_shows: "Prophylactic (does not treat existing HPV infections); vaccinated individuals still require routine cervical screening",
            is_mismatch: false
          }
        ]
      }
    ],
    related_reviewed_claims: [],
    evidence_items: [
      {
        fact_id: "CIAPI-WHO-CC-001",
        document_id: "DOC-WHO-CERVICAL-2026",
        source_id: "WHO",
        origin_source_id: "WHO-HQ",
        organization_name: "World Health Organization (WHO)",
        permission_reference: "WHO Licence 202610792",
        source_title: "WHO Fact Sheet: Cervical Cancer Elimination & HPV Vaccination",
        canonical_url: "https://www.who.int/news-room/fact-sheets/detail/cervical-cancer",
        cancer_id: "cervical-cancer",
        subtype_id: "all",
        category_slug: "prevention",
        structured_fact_or_summary:
          "WHO reports that almost all cervical cancer cases (99%) are linked to infection with high-risk human papillomaviruses (HPV), and prophylactic vaccination of girls aged 9–14 years is a highly effective primary prevention intervention.",
        limited_verbatim_excerpt:
          "\"Being vaccinated at age 9–14 years is a very effective way to prevent HPV infection, cervical cancer and other HPV-related cancers.\"",
        study_design_scope: "guideline",
        population_scope: "human_adult_general",
        jurisdiction_code: "GLOBAL",
        observed_source_date: "2024-03-05",
        retrieved_at_utc: "2026-10-31T19:25:00Z",
        reviewed_at_date: "2026-10-31",
        attribution_text:
          "Source: World Health Organization (WHO), Cervical Cancer Fact Sheet. Used under WHO Non-Exclusive Licence 202610792. Independently developed; not published, endorsed, or sponsored by WHO.",
        ai_processing_allowed: true
      }
    ],
    limitations_and_gaps_note: "Prophylactic HPV vaccination does not replace routine cervical cancer screening.",
    telemetry: {
      request_id: "req_eval_hpv_20261101",
      pipeline_state: "DISPLAYABLE",
      retrieval_state: "SEARCH_EXECUTED_WITH_MATCHES",
      primary_provider: "baseten_model_api",
      primary_model: "meta-models/muse-spark-open-1026",
      total_latency_ms: 980,
      hops_executed: 1,
      learned_query_mapping_applied: null,
      meta_pool_spent_usd: 0.0042,
      meta_pool_remaining_usd: 149.99,
      baseten_pool_spent_usd: 0.0046,
      baseten_pool_remaining_usd: 99.99
    }
  },

  "coverage-gap-example": {
    request_id: "req_eval_gap_20261101",
    resolved_mode: "EVALUATE",
    pipeline_state: "DISPLAYABLE",
    retrieval_state: "SEARCH_EXECUTED_NO_MATCHES",
    interpreted_query_or_claim: "Does experimental compound XZ-904 prevent pleural mesothelioma?",
    cancer_id: "pleural-mesothelioma",
    cancer_name: "Pleural Mesothelioma (Rare)",
    subtype_id: "all",
    category_slug: "prevention",
    overall_outcome_code: "INSUFFICIENT_EVIDENCE",
    overall_outcome_label: "Insufficient Evidence in CancerLens Collection (Corpus Coverage Gap)",
    ai_plain_language_summary:
      "This topic is not yet covered in the rights-cleared Cancer Info API collection. Zero matching passages in our database means we cannot verify this claim—it does NOT establish that evidence does not exist elsewhere, and CancerLens never guesses a medical verdict without admitted source passages.",
    atomic_claim_verdicts: [
      {
        subclaim_id: "subclaim-gap-1",
        atomic_claim_text: "Experimental compound XZ-904 prevents pleural mesothelioma.",
        outcome_code: "INSUFFICIENT_EVIDENCE",
        outcome_label: "Not Assessed — No Admitted Passages Returned",
        ai_plain_language_explanation:
          "CancerInfoAPIClient executed a live search for 'XZ-904 pleural mesothelioma' and returned 0 matching facts (`SEARCH_EXECUTED_NO_MATCHES`). Rather than hallucinating citations or falsely labeling the claim 'Contradicted', CancerLens abstains safely.",
        cited_fact_ids: [],
        cited_document_ids: [],
        verbatim_quote_verified: false,
        stage4_downgraded: false,
        stage4_downgrade_reason: null,
        pivot_to_learn_cancer_id: "pleural-mesothelioma",
        pivot_to_learn_category_slug: "overview",
        context_comparisons_5d: []
      }
    ],
    related_reviewed_claims: [],
    evidence_items: [],
    limitations_and_gaps_note:
      "Consult ClinicalTrials.gov or the National Cancer Institute (1-800-4-CANCER) for investigational agents not yet indexed in Cancer Info API.",
    telemetry: {
      request_id: "req_eval_gap_20261101",
      pipeline_state: "DISPLAYABLE",
      retrieval_state: "SEARCH_EXECUTED_NO_MATCHES",
      primary_provider: "baseten_model_api",
      primary_model: "meta-models/muse-spark-open-1026",
      total_latency_ms: 410,
      hops_executed: 2,
      learned_query_mapping_applied: null,
      meta_pool_spent_usd: 0.0042,
      meta_pool_remaining_usd: 149.99,
      baseten_pool_spent_usd: 0.0051,
      baseten_pool_remaining_usd: 99.99
    }
  },

  "clinical-refusal-boundary": {
    request_id: "req_eval_refusal_20261101",
    resolved_mode: "EVALUATE",
    pipeline_state: "DISPLAYABLE",
    retrieval_state: "TOOL_NOT_EXECUTED",
    interpreted_query_or_claim: "Personal Medical Advice / Treatment Dosing Request Intercepted",
    cancer_id: "lung-cancer",
    cancer_name: "Lung Cancer",
    subtype_id: "all",
    category_slug: "treatment",
    overall_outcome_code: "OUT_OF_SCOPE_CLINICAL",
    overall_outcome_label: "Out of Scope — Personal Clinical Advice & Dosing Refusal",
    ai_plain_language_summary:
      "I can explain general cancer information and evaluate public health claims, but I cannot assess your personal symptoms, interpret personal biopsy/scan reports, or recommend whether you should start, stop, or change a medication dose. Please contact your oncology care team directly before making any change to your treatment plan.",
    atomic_claim_verdicts: [],
    related_reviewed_claims: [],
    evidence_items: [],
    limitations_and_gaps_note:
      "Personal clinical triage, dosing, and scan/lesion interpretation are strictly disabled in CancerLens (`OUT_OF_SCOPE_CLINICAL`). Zero personal data was stored in Claim Memory (`SG-10`).",
    telemetry: {
      request_id: "req_eval_refusal_20261101",
      pipeline_state: "DISPLAYABLE",
      retrieval_state: "TOOL_NOT_EXECUTED",
      primary_provider: "clinical_boundary_guard",
      primary_model: "deterministic_guard_v1",
      total_latency_ms: 8,
      hops_executed: 0,
      learned_query_mapping_applied: null,
      meta_pool_spent_usd: 0.0042,
      meta_pool_remaining_usd: 149.99,
      baseten_pool_spent_usd: 0.0051,
      baseten_pool_remaining_usd: 99.99
    }
  }
};

window.CancerLensData = {
  CLINICAL_CATEGORIES,
  CANCER_CATALOG_25,
  LEARN_ENVELOPES,
  EVALUATE_SCENARIOS
};
