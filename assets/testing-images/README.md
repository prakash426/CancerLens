# Screenshot OCR test images

Three PNGs for testing Mode B Screenshot OCR upload and claim verification.
Each shows health imagery (green drinks plus body organs) with three numbered
claims: one fully true per the cited sources, one partially true, one false.

Grounding sources (live Cancer Info API, National Cancer Institute,
https://www.cancer.gov/types/ovarian/patient/ovarian-prevention-pdq):

- `506bf981-63f3-4cab-a045-7f898eb30c64` (risk_factors): risk factors include
  smoking; quitting smoking and exercising may help prevent some cancers.
- `dfab76f3-2919-4ce7-97aa-9720eac3c335` (prevention): prevention lowers the
  chance of getting cancer; exercise and healthy diet may be protective; risk
  reduction is not a guarantee.

## Answer key

### ocr-test-1-green-smoothie-lungs.png

1. TRUE: "Smoking is a risk factor for some types of cancer, and quitting
   smoking may help prevent some cancers." Fully supported by `506bf981`.
2. PARTIAL: "Quitting smoking and exercising guarantee you will never get
   cancer." The protective part is source verified; the guarantee is
   contradicted ("does not mean that you will not get cancer").
3. FALSE: "Drinking green detox drinks cures cancer and removes cancer cells
   from the body." No source supports a cure claim.

### ocr-test-2-green-juice-heart.png

1. TRUE: "Regular exercise and a healthy diet may be protective factors for
   some types of cancer." Near verbatim from `dfab76f3`.
2. PARTIAL: "Changing eating habits is being studied as a way to prevent
   cancer, and it works for every cancer type." The studied part is source
   verified; "every cancer type" is unsupported.
3. FALSE: "Green juice cleanses the blood of all cancer cells within 30 days."
   Fabricated; no source supports it.

### ocr-test-3-digestive-smoothie-bowl.png

1. TRUE: "Cancer prevention is action taken to lower the chance of getting
   cancer." Verbatim from `dfab76f3`.
2. PARTIAL: "Some cancer risk factors can be avoided, and avoiding them means
   you will not get cancer." The first half is source verified; the guarantee
   is contradicted by the same source.
3. FALSE: "Doctors guarantee that prevention methods stop all cancers from
   starting." Contradicted; sources state the opposite.

## File constraints (all verified)

PNG magic bytes, 1400x1444 px (guard limit 4096), each well under 5 MB, and
each passes `guard_image_upload` in the backend. Expected OCR text is exactly
the quoted claim strings above plus the "Test claims for screenshot OCR"
heading.
