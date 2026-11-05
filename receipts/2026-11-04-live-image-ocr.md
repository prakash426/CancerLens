# Live check: screenshot OCR via Meta image understanding

Date: 2026-11-04. Backend 0.1.0-stage2 plus OCR wiring. Model `muse-spark-1.3`
on `POST /v1/responses` with an `input_image` block carrying a base64 data URL
(docs: https://dev.meta.ai/docs/image-understanding). Note: `muse-image` was
evaluated and rejected for this task: it is an image generation and editing
model whose output is images, not text, so it cannot transcribe screenshots.

## What ran

`POST /api/v1/extract/image` against all three `assets/testing-images/*.png`
(guard, then live Meta transcription, then PII scrub, 3000 chars, user
confirmation required). Each image holds 3 claims (1 true, 1 partial, 1 false
per `assets/testing-images/README.md`).

## Result

PASS. HTTP 200 on all 3 uploads, 9/9 expected claim strings matched verbatim
in the transcriptions (whitespace normalized). Reading order, line breaks and
claim numbering preserved; no added facts, descriptions or advice observed.

Ledger (local estimate, 3 calls): 8034 input / 934 output tokens (662
reasoning subset), $0.0008 booked against the Meta pool. Per-call cost is a
fraction of a cent at the currently configured Meta prices.

## Limitations

Three synthetic images with large clean text on plain panels. Rotated photos,
handwriting, dense layouts, tiny fonts and non English text were not tested.
The `NO_READABLE_TEXT` fallback for textless images is prompt level only and
was not observed live. Transcribed text is untrusted input: it always lands in
the confirmation drawer for user review before any verification run.
