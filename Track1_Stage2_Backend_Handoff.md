# Track 1 (Stage 2) Backend Build Plan & Instructions

- **Target:** Track 1 Stage 2 backend guards, verifier hardening and live `Cancer Info API` adapter
- **Date Prepared:** November 2, 2026 (`America/Chicago`)
- **Submission Deadline:** Wednesday, November 4, 2026 at 9:00 PM EST (8:00 PM CST)
- **Folder Scope:** Strictly `backend/` (do **not** modify `frontend/`)
- **Upstream Baseline (`HO-1` from Stage 1):** The Stage 1 build has already completed **Track 1 Stage 1** in `backend/` with **37 passing offline unit and pipeline tests** (`$0.00` credit spend).

---

## 1. Context Files for the Stage 2 Build (In Order of Authority)

Attach or provide the following files from `/Users/prakash/Meta Hackathon/CancerLens/` when starting the Stage 2 build:

1. **`Track1_Stage2_Backend_Handoff.md` (THIS FILE)** — Exact Stage 2 scope, file targets, function signatures, and acceptance gates.
2. **`backend/README.md`** — the Stage 1 completion notes, assumptions, and `HO-1` extension points.
3. **`backend/app/investigator/hooks.py`** — The exact Stage 1 baseline hooks (`check_clinical_boundary`, `sanitize_pii`, `guard_image_upload`, `guard_public_url`, `run_stage4_verifier`) to harden/complete in Stage 2.
4. **`backend/app/clients/cancerinfo_client.py` & `backend/app/config.py`** — The single live `CancerInfoAPIClient` that needs to be aligned with the now-live **`https://cancerinfo-api.onrender.com/`** service.
5. **`CancerLens_Consolidated_Implementation_Plan.md`** — Master 3-layer architecture, `SG-01`–`SG-10` safeguards, and WHO Licence `202610792` controls.
6. **`SECURITY.md` & `TESTING.md`** — Authoritative specification for `SEC-01`–`SEC-06` and Verification Gates 1–8.

---

## 2. Hard Non-Negotiable Rules (Read Before Writing Any Code)

1. **Preserve All Stage 1 Public Signatures & 37 Passing Tests:**
   - Do **not** break any existing imports or function signatures in `backend/app/investigator/hooks.py`, `backend/app/schemas/`, `backend/app/providers/`, or `backend/app/api/routes.py`.
   - All 37 existing tests in `backend/tests/test_stage1_units.py` and `backend/tests/test_stage1_pipelines.py` **must continue to pass** alongside your new Stage 2 test suite (`backend/tests/test_stage2_guards_and_verifier.py`).
2. **Zero `FixtureCancerInfoAPIClient`, Zero Custom GPU Code, Zero Voice Input (`D11`):**
   - `backend/tests/test_stage1_units.py` (`test_no_fixture_client_or_gpu_code_in_app` and `test_voice_input_removed_from_contract`) actively scans `backend/app/` and fails if the strings `FixtureCancerInfoAPIClient`, `truss`, `medcpt`, `deberta`, `torch`, or `VOICE_TRANSCRIPT` appear anywhere in `backend/app/`.
   - Voice input is **out of scope** (`TEXT`, `IMAGE_OCR`, and `URL_EXTRACT` only).
3. **Zero Duplicate Medical Corpus on Disk:**
   - Never add medical corpus tables to `cancerlens_app.db` or write `Cancer Info API` responses to disk.
4. **Strict `$0.00` LLM Credit Spend During Stage 2 Tests:**
   - Keep `LIVE_LLM_CALLS_ENABLED: bool = False` as the default in `backend/app/config.py`. All automated `pytest` suites must run offline using mocked `httpx.MockTransport` (`$0.00` spend on Meta `$150` pool and Baseten `$100` pool).

---

## 3. Exact Stage 2 Deliverables

### Deliverable 1: Align `CancerInfoAPIClient` & `Settings` with Live `https://cancerinfo-api.onrender.com/`
**Files:** `backend/app/config.py`, `backend/.env.example`, `backend/app/clients/cancerinfo_client.py`

When Stage 1 was built on Nov 1, the live `Cancer Info API` URL was not yet deployed, so `cancerinfo_client.py` used assumed paths (`/v1/cancers`, `/v1/evidence/search`, `/v1/facts`) and assumed every returned record already had all 21 flat fields of `CancerInfoEvidenceItem`. Now **`https://cancerinfo-api.onrender.com/` is live**.

1. **Inspect Live `https://cancerinfo-api.onrender.com/` Endpoints & Schema:**
   - Inspect `https://cancerinfo-api.onrender.com/openapi.json` (and live responses such as `/v1/cancers`, `/v1/cancers/breast-cancer`, `/v1/cancers/breast-cancer/symptoms?country=US`, etc.).
2. **Update `backend/app/config.py` & `backend/.env.example`:**
   - Set default `CANCER_INFO_API_BASE_URL: str = "https://cancerinfo-api.onrender.com"`.
   - Increase default `CANCER_INFO_API_TIMEOUT_SECONDS: float = Field(default=45.0, gt=0, le=120)` so a Render free/starter cold start (`30–40s` spin-up after idle) does not falsely trigger `RetrievalState.TOOL_FAILED`.
   - Expand `CORS_ALLOWED_ORIGINS` in `backend/app/config.py` to include common local static servers used by the Option 2 `frontend/`:
     ```python
     CORS_ALLOWED_ORIGINS: list[str] = [
         "http://localhost:3000",
         "http://127.0.0.1:3000",
         "http://localhost:5500",
         "http://127.0.0.1:5500",
         "http://localhost:8080",
         "http://127.0.0.1:8080",
     ]
     ```
3. **Add a Flexible Record Adapter in `backend/app/clients/cancerinfo_client.py`:**
   - Keep complete backward compatibility with flat `CancerInfoEvidenceItem` dicts (so all Stage 1 unit tests pass untouched), **and** add a normalizer function `_coerce_record_to_evidence_item(record: dict, context: dict | None = None) -> dict` inside `cancerinfo_client.py` that maps `https://cancerinfo-api.onrender.com/`'s live JSON fields (including nested `cancer` / `source` / `provenance` / `facts` structures or `/v1/cancers/{slug}/{category}` fallback routes if `/v1/evidence/search` is structured differently) into valid `CancerInfoEvidenceItem` objects.
   - **Truthfulness Rules (`SG-08` / Gate 2):**
     - Never fabricate `observed_source_date` (keep `None` if absent).
     - Never fabricate `ai_processing_allowed`: default to `True` **only** when the live API explicitly marks the source as reusable/cleared (or provides `ai_processing_allowed=True`); if a source is marked restricted, set `ai_processing_allowed=False`.
     - Preserve exact `canonical_url` and `attribution_text` (including WHO Licence `202610792` non-endorsement wording where applicable).

---

### Deliverable 2: Implement Stage 2 Security, Privacy, Image & SSRF Guards (`backend/app/guards/` + `hooks.py`)
**Files to Create:**
- `backend/app/guards/__init__.py`
- `backend/app/guards/clinical_boundary.py` (`SEC-03`)
- `backend/app/guards/pii_sanitizer.py` (`SG-10` / `SEC-06`)
- `backend/app/guards/image_upload_guard.py` (`SEC-03`)
- `backend/app/guards/ssrf_url_guard.py` (`SEC-04`)

**File to Update:**
- `backend/app/investigator/hooks.py` (delegate `check_clinical_boundary`, `sanitize_pii`, `guard_image_upload`, and `guard_public_url` to `backend/app/guards/` while preserving exact return types)

#### 2.1 `clinical_boundary.py` (`check_clinical_boundary(text: str) -> tuple[bool, str | None]`)
- **Must Refuse (`(True, reason)` $\rightarrow$ `OUT_OF_SCOPE_CLINICAL`):**
  - Personal symptom triage or self-diagnosis (*"Do I have cancer?"*, *"I found a hard lump in my breast and have night sweats, what is it?"*, *"Does my biopsy / pathology / CT / MRI / PET scan / mammogram / PSA level mean stage 3?"*).
  - Personal treatment selection or drug dosing (*"Should I take pembrolizumab or skip chemo?"*, *"How many mg of tamoxifen should I take?"*, *"Can I stop my radiation therapy early?"*).
  - Requests to interpret personal clinical lesions, moles, X-rays, pathology slides, or lab panels.
- **Must Allow (`(False, None)`):**
  - General educational questions and public claims (*"What are the common symptoms of non-small cell lung cancer?"*, *"How does immunotherapy work for breast cancer?"*, *"Does eating sugar directly cause breast cancer?"*, *"What is the difference between stage II and stage III colorectal cancer?"*).

#### 2.2 `pii_sanitizer.py` (`sanitize_pii(text: str) -> str`)
- Scrub personal identifiers before any query or canonical claim is processed or stored:
  - Email addresses $\rightarrow$ `[EMAIL]`
  - Phone numbers (US & international formats, without mangling years like `2026` or NCT trial numbers like `NCT01234567`) $\rightarrow$ `[PHONE]`
  - SSNs (`\b\d{3}-\d{2}-\d{4}\b`) and MRN / Patient ID / Policy / Accession numbers $\rightarrow$ `[ID]`
  - Dates of birth (`DOB: ...`, `born on ...`) $\rightarrow$ `[DOB]`
  - First-person name/age introductions (`"My name is John Doe"`, `"I am a 54-year-old female named ..."`) $\rightarrow$ `[REDACTED_PERSON]`

#### 2.3 `image_upload_guard.py` (`guard_image_upload(data: bytes, content_type: str | None) -> bytes`)
- Enforce all `SEC-03` screenshot upload rules strictly in memory (zero disk writes):
  1. Reject empty payloads or payloads $> 5 \times 1024 \times 1024$ bytes (`5 MB`) with `ValueError`.
  2. Validate actual file magic bytes (`PNG`: `\x89PNG\r\n\x1a\n`, `JPEG`: `\xff\xd8\xff`, `WEBP`: starts with `RIFF` and bytes `8:12 == b"WEBP"`). If `content_type` is provided, verify it matches one of `image/png`, `image/jpeg`, `image/webp` and matches the magic bytes; otherwise raise `ValueError`.
  3. Parse image width & height directly from the `PNG` IHDR chunk, `JPEG` SOF0–SOF15 markers, or `WEBP` (`VP8 ` / `VP8L` / `VP8X`) header in pure Python (no external C library required!) and reject any image with `width <= 0`, `height <= 0`, `width > 4096`, or `height > 4096` with `ValueError`.
  4. Strip metadata/EXIF in memory:
     - For `JPEG`: strip `APP1` (`0xFFE1` EXIF/XMP) and `COM` (`0xFFFE`) segments while preserving image data.
     - For `PNG`: strip ancillary metadata chunks (`tEXt`, `zTXt`, `iTXt`, `eXIf`, `tIME`) while keeping critical chunks (`IHDR`, `PLTE`, `IDAT`, `IEND`).
     - For `WEBP`: strip `EXIF` and `XMP ` RIFF chunks if present.
  5. Return the sanitized image `bytes`.

#### 2.4 `ssrf_url_guard.py` (`guard_public_url(url: str, resolver: Callable | None = None) -> str`)
- Enforce all `SEC-04` SSRF defenses before any outbound URL request:
  1. Parse URL via `urllib.parse.urlsplit`. Require `scheme == "https"`, non-empty `hostname`, no embedded credentials (`username` or `password` must be `None`), and `port in (None, 443)`. Reject anything else with `ValueError`.
  2. Reject hostnames `localhost`, `.local`, `.internal`, `.arpa`, or raw IP literals that fail validation.
  3. Resolve all IPv4/IPv6 addresses for `hostname` via `socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)` (allow injecting a custom `resolver` in unit tests so tests run offline with zero DNS flakiness).
  4. For every resolved IP address (`ipaddress.ip_address(ip_str)`), (including IPv4-mapped IPv6 addresses `ip.ipv4_mapped`), reject with `ValueError` if **any** of the following is True:
     - `ip.is_private` (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`)
     - `ip.is_loopback` (`127.0.0.0/8`, `::1`)
     - `ip.is_link_local` (`169.254.0.0/16` AWS/GCP/Render metadata service, `fe80::/10`)
     - `ip.is_multicast`, `ip.is_reserved`, `ip.is_unspecified` (`0.0.0.0`, `::`)
     - Carrier-Grade NAT (`100.64.0.0/10`)
  5. Return the normalized URL string (with `#fragment` stripped).

---

### Deliverable 3: Wire Safe Public URL Extraction & Image Guard in `backend/app/api/routes.py`
**File:** `backend/app/api/routes.py`

1. **`POST /api/v1/extract/url` (`extract_url`):**
   - Call `safe_url = guard_public_url(body.url)` first (invalid/private URLs raise `ValueError` $\rightarrow$ `HTTP 422 INVALID_REQUEST`).
   - Perform a safe, bounded HTTP fetch (up to `max_redirects = 3`, re-running `guard_public_url` on every redirect `Location` header before following it; `timeout = 10.0s`; `verify = create_verified_ssl_context()`; read at most `512 KB`).
   - Extract readable text from HTML (`html.parser` stripping `<script>`, `<style>`, `<nav>`, `<footer>`, `<noscript>`), normalize whitespace, truncate to `1500` chars, apply `sanitize_pii`, and return:
     ```python
     ExtractionResponse(
         modality=InputModality.URL_EXTRACT,
         extracted_text=extracted_text,
         requires_user_confirmation=True,
         warnings=["Review and edit the extracted webpage text before running verification."],
     )
     ```
2. **`POST /api/v1/extract/image` (`extract_image`):**
   - Call `sanitized_bytes = guard_image_upload(data, file.content_type)` first so invalid magic bytes, $>5\text{ MB}$ payloads, or $>4096\text{ px}$ dimensions deterministically return `HTTP 422 INVALID_REQUEST` (`TEST-SEC-03`).
   - After `guard_image_upload` succeeds, keep the honest `CapabilityNotReadyError` (`HTTP 501`) if `LIVE_LLM_CALLS_ENABLED` is False or multimodal OCR is not enabled, so no unverified vision call is made.

---

### Deliverable 4: Stage-4 Verifier Module & Audit (`backend/app/verifiers/stage4_verifier.py` + `hooks.py`)
**Files:** `backend/app/verifiers/__init__.py`, `backend/app/verifiers/stage4_verifier.py`, `backend/app/investigator/hooks.py`

1. Factor and harden `run_stage4_verifier` into `backend/app/verifiers/stage4_verifier.py` and re-export `run_stage4_verifier` and `normalize_for_quote_match` from `backend/app/investigator/hooks.py` (preserving exact signature `run_stage4_verifier(envelope: ResultEnvelope, retrieved_items: list[CancerInfoEvidenceItem], claimed_quotes: Mapping[str, str] | None = None) -> ResultEnvelope`).
2. Verify all Gate 5 (`TESTING.md`) citation and quote edge cases:
   - Non-existent `fact_id` or `document_id` $\rightarrow$ downgrades sub-claim to `OutcomeCode.INSUFFICIENT_EVIDENCE` (`stage4_downgraded=True`).
   - `SUPPORTED` / `CONTRADICTED` / `MIXED_OR_CONTEXT_DEPENDENT` verdict with empty `cited_fact_ids` $\rightarrow$ downgrades to `OutcomeCode.INSUFFICIENT_EVIDENCE`.
   - Paraphrased or altered quote passed in `claimed_quotes` that is not a normalized substring of a cited item's `limited_verbatim_excerpt` $\rightarrow$ downgrades to `OutcomeCode.INSUFFICIENT_EVIDENCE` (`verbatim_quote_verified=False`).
   - Exact substring quote (ignoring smart-quote / dash / whitespace normalization) $\rightarrow$ sets `verbatim_quote_verified=True`.
   - Evidence item with empty `attribution_text` or empty `canonical_url` $\rightarrow$ stripped from `envelope.evidence_items`.
   - `observed_source_date=None` is preserved as `None` (never fabricated).

---

### Deliverable 5: Stage 2 Zero-Cost Automated Test Suite (`backend/tests/test_stage2_guards_and_verifier.py`)
**File:** `backend/tests/test_stage2_guards_and_verifier.py`

Write a comprehensive `$0.00` offline `pytest` suite testing:
1. **`clinical_boundary` (`SEC-03`):**
   - Refuses personal symptom triage, biopsy/scan interpretation, treatment choice, and dosing questions (`OUT_OF_SCOPE_CLINICAL`).
   - Allows general educational questions and public claims about symptoms, screening, staging, and treatments.
2. **`pii_sanitizer` (`SG-10`):**
   - Scrubs emails, US/international phone numbers, SSNs, MRNs, DOBs, and `"My name is ..."` while preserving clinical terms, years (`2026`), and trial IDs (`NCT01234567`).
3. **`image_upload_guard` (`SEC-03`):**
   - Accepts valid `PNG`, `JPEG`, and `WEBP` headers within `4096x4096` and $\le 5\text{ MB}$.
   - Strips JPEG `APP1` EXIF and PNG `tEXt`/`eXIf` metadata chunks in memory.
   - Rejects spoofed magic bytes (e.g., `application/pdf` or executable renamed to `.png`), payloads $> 5\text{ MB}$, and dimensions $> 4096\text{ px}$ with `ValueError` (`HTTP 422` on `POST /api/v1/extract/image`).
4. **`ssrf_url_guard` & `POST /api/v1/extract/url` (`SEC-04`):**
   - Rejects `http://`, non-443 ports (`https://example.com:8443/`), credentials in URL, `localhost`, `127.0.0.1`, `10.x.x.x`, `172.16.x.x`, `192.168.x.x`, `169.254.169.254` (cloud metadata), `100.64.0.1` (CGNAT), `::1`, `fe80::1`, and `::ffff:127.0.0.1` (IPv4-mapped IPv6).
   - Rejects an `https://` public URL that redirects (`302`) to a private/loopback IP.
   - Extracts clean text from a mocked public `https://` HTML page and sets `requires_user_confirmation=True`.
5. **Stage-4 Verifier (`SG-08` / Gate 5) & Live `Cancer Info API` Adapter:**
   - Tests all citation tamper, quote tamper, missing attribution, and `https://cancerinfo-api.onrender.com/` record normalization paths.

---

## 4. Verification Commands Before Completing Stage 2

Run from `backend/`:
```bash
pytest
python scripts/export_openapi.py
```

Confirm:
- `pytest` passes **100%** of `test_stage1_units.py`, `test_stage1_pipelines.py`, and `test_stage2_guards_and_verifier.py` with **`$0.00` LLM spend** (real outbound LLM sockets remain blocked in `conftest.py`).
- `backend/openapi.json` is up to date.
