# Live check: public URL extraction (Gate 6 SSRF + Gate 1 multimodality)

Date: 2026-11-04. Backend 0.1.0-stage2, local server, URL_EXTRACTION_ENABLED=true
in backend/.env.local only (template default stays false, suite stays hermetic).

## What ran

1. POST /api/v1/extract/url with the NCI ovarian treatment article URL previously
   cited by live evidence. Result: HTTP 200, modality URL_EXTRACT, readable text
   truncated at 1500 chars, requires_user_confirmation true, review warning present.
2. POST /api/v1/extract/url with http://127.0.0.1:1/. Result: HTTP 422
   INVALID_REQUEST, "Only https URLs are allowed." Guard held live with no fetch.

## Limitations

Single page, single blocked address. Redirect chains, IPv6 literals, and DNS
rebinding variants are covered by the offline suite (mocked DNS), not re-proven
live here. Extraction is a plain HTML strip plus PII scrub, so nav boilerplate
survives and the user confirmation drawer is the intended trim step. Zero LLM cost.
