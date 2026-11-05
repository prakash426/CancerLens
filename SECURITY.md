# CancerLens — Security, Privacy, WHO Licence `202610792` & Medical Boundary Specification (`SECURITY.md`)

- **Date:** November 2, 2026 (`America/Chicago`)
- **Status:** Authoritative Specification (Aligned with WHO Permission `202610792` Clauses 1–13, Live `https://cancerinfo-api.onrender.com/` Boundary, and `SG-01`–`SG-10` Safeguards)

---

## 1. Trust Boundaries & Zero-Duplicate-Corpus Security Model

1. **Protected `Cancer Info API` Connection (`SEC-01`):**
   - `CancerLens` communicates with **`Cancer Info API`** (`CANCER_INFO_API_BASE_URL=https://cancerinfo-api.onrender.com/`) using `CANCER_INFO_API_BASE_URL` and `CANCER_INFO_API_KEY` loaded strictly from `.env.local`.
   - All outbound HTTPS calls enforce TLS certificate verification via `ssl.create_default_context(cafile=certifi.where())` (`SG-09` — never `verify=False`).
   - `CancerLens` **never stores a persistent copy of WHO or `Cancer Info API` medical documents on disk**, caching only non-restricted responses in short-TTL ephemeral RAM (`cachetools.TTLCache`, 5-minute TTL). Raw WHO-derived API responses are never exposed publicly.
2. **WHO Licence `202610792` Clause 3, 5, 6 & 7–9 Enforcement (`SEC-02`):**
   - **Clause 6 AI Transmission Gate (`store=false`):** Every request to Meta Model API (`/v1/responses`) sets `"store": false` and passes only `Cancer Info API` structured facts, concise summaries, and short approved excerpts for records where `ai_processing_allowed == True`. Full WHO webpages are never transmitted or reproduced.
   - **Authorship & Attribution Separation (Clauses 3 & 6):** AI-generated plain-language explanations are explicitly labeled as authored by CancerLens AI and never attributed to WHO. WHO may be cited as a supporting source with its bibliographical reference, original URL, and non-endorsement notice (*"Independently developed; not published, endorsed, or sponsored by the World Health Organization"*).
   - **No WHO Emblem / No Commercialization (Clauses 7–9):** Zero use of the WHO logo/emblem, zero implied endorsement, and zero advertisements, sponsorships, or paid plans.
3. **Medical Boundary & Clinical Image Refusal (`SEC-03`):**
   - Refuse personal diagnosis, symptom triage, treatment selection, drug dosing, and clinical images (skin lesions, X-rays, scans, pathology slides, lab reports) with `OUT_OF_SCOPE_CLINICAL` and safe educational links.
   - Screenshot uploads (`POST /api/v1/extract/image`) enforce magic-byte validation (`PNG`/`JPEG`/`WEBP`), $\le 5\text{ MB}$, $\le 4096 \times 4096\text{ px}$, in-memory EXIF stripping, and immediate RAM disposal after text extraction.
4. **Public URL SSRF Defense (`SEC-04`):**
   - Allow `https://` on port `443` only; resolve DNS and block loopback, RFC 1918 private, link-local (`169.254.0.0/16`), CGNAT, and IPv6 local addresses before connecting and across up to 3 redirects.
5. **Prompt Injection, Pending-Tool Prose Purge & Stage-4 Provenance Verification (`SEC-05` / `SG-02` / `SG-08`):**
   - Wrap untrusted user/OCR/URL text in `<untrusted_user_input>` delimiters.
   - Whenever a Baseten (`meta-models/muse-spark-open-1026`) or Meta (`muse-spark-1.3`) response has `finish_reason == "tool_calls"` or `message.tool_calls`, **immediately discard `message.content`** (`SG-02`).
   - Stage 4 deterministically verifies in Python that every cited `fact_id` / `document_id` and verbatim excerpt matches `Cancer Info API`'s actual response for that request (`SG-08`). Any ungrounded assertion or unverified citation triggers safe downgrade or abstention.
6. **Privacy, PII Scrubbing, Review Gates & Dual-Pool Budget Breakers (`SEC-06`):**
   - Strip PII (names, emails, phones, MRNs, first-person identifiers) before indexing canonical claims in `claim_memory_library`, and require `review_status = 'APPROVED'` before surfacing entries in shared views or applying `learned_query_mappings`. Never log secrets or raw `reasoning_content`.
   - Enforce pre-submission circuit breakers in `budget_ledger` (`$115` on the `$150` Meta Model API pool; `$65` on the `$100` Baseten Model API pool) so `$35` in each pool remains untouched for judging.
