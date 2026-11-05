# CancerLens Engineering Conventions (`CODE_STYLE.md`)

Status: AUTHORITATIVE SPECIFICATION (Updated November 2, 2026).

## Purpose and development workflow
Engineering conventions for the CancerLens build, organized by area:
- **Stage 1 backend:** Track 1 Stage 1 backend core (`backend/app/schemas/`, `db/`, `clients/`, `providers/`, `investigator/`, `api/`).
- **Stage 2 guards:** Track 1 Stage 2 security guards (`hooks.py` / `guards/`), multimodal extraction guards, and automated security/verifier regression tests.
- **Stage 2 adapter and review:** `muse-spark-1.3` prompt/response auditing, live `Cancer Info API` (`https://cancerinfo-api.onrender.com/`) contract alignment, and Gate 1–8 evaluation review.
- **Frontend:** Track 2 frontend UI (`frontend/index.html`, `frontend/css/styles.css`, `frontend/js/data.js`, `frontend/js/app.js`), architecture synthesis, and E2E integration.

Product and safety rules (`SG-01`–`SG-10`, WHO Licence `202610792` Clauses 1–13) belong in deterministic Python code and tests, not just prompts. Keep the repository free of credentials, duplicate medical corpus tables, and personal health submissions.

## Stack and layout
- **Backend (`backend/`):** Python 3.12+, FastAPI, Pydantic v2 (`extra="forbid"`), `httpx` with `certifi` TLS (`SG-09`), `cachetools.TTLCache` (5-minute RAM cache), and SQLite 3.45+ `STRICT` with FTS5 (`cancerlens_app.db` storing operational metadata only).
- **Frontend (`frontend/` — Option 2):** Zero-dependency modern HTML5, CSS3, and Vanilla ES6+ JavaScript (`index.html`, `css/styles.css`, `js/data.js`, `js/app.js`) consuming `http://127.0.0.1:8000/api/v1/*` (`backend/openapi.json`).
- **Single Medical Source of Truth:** Live HTTPS callouts to **`Cancer Info API`** (`https://cancerinfo-api.onrender.com/`) via `backend/app/clients/cancerinfo_client.py`. Zero `FixtureCancerInfoAPIClient`, zero custom GPU containers (`Truss`), and zero voice input (`D11`).

## Types, contracts and errors
Use typed request and response models with a versioned schema, validation at every boundary, nullable unknown dates and explicit outcome enums. Keep source, model and prompt versions. A malformed model response is an error or safe abstention, not a guessed result. Do not force a subtype or clinical interpretation. Use typed errors for invalid input, rights blocked, provider unavailable, exhausted application budget and evidence missing. The UI should present useful recovery actions without exposing stack traces.

## Provider, budget and evidence modules
Route model calls through a small provider interface with explicit model identity, bounded timeouts, usage and retry behavior. Verify real capabilities before implementing provider-specific assumptions. Reserve estimated maximum spend transactionally before dispatch, reconcile, handle uncertain calls and check provider billing; no local safeguard guarantees zero card charges. Make the evidence repository responsible for per-use admission filters. A SQLite view alone is not authorization. Check IDs and quotes mechanically; assess semantic grounding separately. Do not write unreviewed user claims or learned mappings into shared indexes.

## Quality and review
Use formatting, linting and type checks appropriate to the chosen versions, plus focused tests. Avoid unnecessary abstraction and duplicate contracts. Keep migrations repeatable and back up persistent storage. Use scoped commits and a contribution log. Review generated code for rights bypass, privacy, source accuracy, source date fabrication, model identity, safe failure, injection, resource limits and accessibility. If two collaborators exchange mock JSON, validate it against the same published schema; record contract changes. Cross-review does not replace live tests or human evidence review.

## Open decisions
Runtime provider, exact framework and library versions, deployment, authentication, final repository layout and CI commands require verification on the chosen environment. No commands in an earlier plan establish that a test was run.
