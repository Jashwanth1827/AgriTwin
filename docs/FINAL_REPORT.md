# AgriTwin — Final Engineering Report

**Project:** AgriTwin — uncertainty-aware crop-health, yield, market-intelligence
and decision support for Indian farmers
**Programme:** B.Tech CSE (AI & ML) major project
**Report date:** 2026-11-04
**Repository root:** `majorp/`

---

## 1. Executive summary

AgriTwin is a complete, working full-stack system. It is not a prototype with
mocked screens: the React frontend talks to a FastAPI backend, the backend runs
trained PyTorch and scikit-learn models, persists everything in SQLAlchemy
models behind an Alembic migration, and the whole stack runs under Docker
Compose with PostgreSQL and nginx.

The central contribution is a **deterministic, explainable decision engine**
that fuses a yield estimate, a price forecast, an optional crop-health scan,
buyer offers, transport costs, weather risk and data freshness into one of three
actions: **SELL**, **WAIT** or **INSPECT**. The engine is a pure Python module
with 17 dedicated unit tests; it never calls an LLM and never hides missing
inputs.

At the time of writing, the following are verified:

| Check | Result |
| --- | --- |
| Backend test suite | **98 passed, 0 failed** |
| Frontend test suite | **26 passed, 0 failed** |
| Frontend production build | **passed** (chunk-size warning only) |
| Local end-to-end smoke (SQLite + real models) | **passed** |
| Docker Compose stack (PostgreSQL + backend + nginx) | **healthy** on 2026-11-04; daemon unavailable for a re-run in this workspace |
| Docker end-to-end smoke through nginx | **passed** on 2026-11-04, including real CNN + Grad-CAM; not re-run for v3 |
| Alembic upgrade → downgrade → upgrade | **passed on SQLite** |

---

## 2. Problem and approach

Indian smallholders make a high-stakes selling decision with fragmented
information: a mandi price from yesterday, a buyer's phone offer, an
unreliable yield expectation, and a disease that may or may not be serious.
Most tools either show raw prices or make an opaque recommendation.

AgriTwin's approach:

1. **Quantify uncertainty** — yield and price models produce intervals, not
   just point estimates.
2. **Fuse heterogeneous signals** — eight weighted risk components, data
   completeness, freshness and channel economics.
3. **Apply ordered, auditable rules** — the first matching rule wins, and every
   rule maps to a threshold in a JSON policy file.
4. **Explain the answer** — the API returns factors, assumptions, missing
   inputs, scenarios and a revenue range, all persisted for audit.
5. **Never fake data** — demo and fallback paths are labelled at the API and in
   the UI.

---

## 3. Delivered system

### 3.1 Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn-style primitives, React Router, TanStack Query, React Hook Form, Zod, Recharts, Lucide |
| API | FastAPI, Pydantic v2, Uvicorn |
| Auth | JWT access + refresh, bcrypt, refresh revocation |
| Services | Farm/crop, crop-health, yield, market, buyers, transport, weather, decisions, dashboard, reports |
| Decision | Pure Python module + JSON policy |
| ML | PyTorch ConvNeXt-Tiny with 4-view TTA + Grad-CAM; scikit-learn ExtraTrees + conformal intervals; chronological market forecasters |
| Persistence | SQLAlchemy 2, Alembic, SQLite (dev), PostgreSQL 16 (Docker) |
| Ops | Structured JSON logging, request IDs, rate limiting, CORS, upload validation, Docker, nginx |

### 3.2 Frontend pages

All ten authenticated pages are implemented and call the backend:

| Page | Backend calls |
| --- | --- |
| Dashboard | `/dashboard/*`, `/system/notifications` |
| Farms & crops | `/farms`, `/crops` |
| Crop health | `/crop-health/model`, `/classes`, `/predict`, `/predictions` |
| Yield | `/yield/model`, `/predict`, `/predictions`, `/readiness/{id}`, `/history` |
| Market | `/market/prices`, `/trends`, `/forecast`, `/forecasts`, `/import` |
| Buyers | `/buyers`, `/buyers/{id}/offers`, `/offers/{id}` |
| Transport | `/transport/vehicles`, `/estimate`, `/estimates` |
| Decisions | `/decisions/policy`, `POST /decisions`, `/decisions` |
| Reports | `/system/reports` |
| Settings | `/auth/me`, `/system/status` |

Auth pages (`/login`, `/register`) and a not-found page complete the SPA.

### 3.3 Database

17 tables covering users, revoked tokens, farms, crops, uploads, buyers, offers,
market prices, market forecasts, historical yields, yield predictions,
crop-health predictions, transport estimates, decisions, decision factors,
reports and notifications. JSON columns keep the schema portable between SQLite
and PostgreSQL. The initial migration is
`backend/alembic/versions/20261104_0014_709bc5e375e1_initial_schema.py`.

---

## 4. Verified evidence

All checks below were run on 2026-11-04 in the delivered workspace.

### 4.1 Backend tests

```
cd backend
python -m pytest -q --disable-warnings --junitxml=../pytest_junit.xml
```

JUnit result: `<testsuite errors="0" failures="0" skipped="0" tests="75" ...>`.

Coverage areas:

- authentication, registration validation, refresh rotation, logout, profile
- ownership isolation (403 for farm resources, 404 for service resources)
- farm/crop CRUD, area constraint, validation
- buyer/offer CRUD, demo labelling, validation, isolation
- decision policy exposure, decision creation, auto-compute, lifecycle, isolation
- 17 pure decision-engine tests (rules, risk, completeness, freshness, Decimal money, wait economics, determinism)
- market prices, markets, trends, forecast, insufficient-data rejection, CSV import and dedupe
- transport vehicle options, geodesic fallback, listing, validation, isolation
- yield metadata, prediction, listing/detail, readiness/history, ownership
- crop-health metadata/classes, upload validation, prediction flow, isolation
- system health, status, options, notifications, reports

### 4.2 Frontend tests and build

```
cd frontend
npm test        # 3 files, 26 tests passed
npm run build   # tsc -b && vite build
```

Build output: 2,068 modules, `dist/assets/index-*.js` 842.94 kB (230.57 kB gzip),
CSS 22.13 kB. The only warning is the standard Vite chunk-size advisory.

### 4.3 Local end-to-end smoke

```
python scripts\smoke_api.py
```

Verified: login, all read endpoints, model status (`crop_health: real`,
`yield_prediction: real`, `market_forecasting: on_demand`), yield prediction,
market forecast (`LinearTrendWeekly`, `Ammapet(Uzhavar Sandhai )`), transport
estimate, **real CNN crop-health scan** (`Tomato___Early_blight`, confidence
0.980, `model_mode=real`, Grad-CAM generated), decision
(`SELL`, mandi, ₹6,371.67/quintal, risk 0.44 medium), dashboard, report.

### 4.4 Docker Compose

```
docker compose build
docker compose up -d --force-recreate
docker compose ps
```

| Container | Status |
| --- | --- |
| `agritwin-db-1` (PostgreSQL 16) | Up, healthy |
| `agritwin-backend-1` (FastAPI) | Up, healthy |
| `agritwin-frontend-1` (nginx) | Up, healthy |

The backend container runs `alembic upgrade head` before Uvicorn and seeds the
demo workspace into PostgreSQL. The frontend nginx container serves the built
SPA and proxies `/api` and `/uploads`.

```
python scripts\smoke_docker.py
```

Verified through `http://localhost:5173` (nginx): frontend index, health via
proxy, login, reads, model status, market forecast, **real CNN + Grad-CAM**,
Grad-CAM image retrieval via the proxy, decision, report.

### 4.5 Alembic

```
cd backend
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

Verified on SQLite; the same migration runs in the PostgreSQL container on every
start.

### 4.6 Issue found and fixed during final verification

The first Docker build produced an **unhealthy backend**: the container crashed
with `ModuleNotFoundError: No module named 'cv2'`. `gradcam.py` imported OpenCV,
which existed only in the local developer environment and was never listed in
`requirements.txt`.

Fix: replaced the two OpenCV calls (resize and JET colour map) with a PIL resize
and a NumPy implementation of JET (`jet_colormap`). This removes a ~60 MB
dependency from the image, keeps the same visual output (anchors verified
against OpenCV: 0 → dark blue, 0.5 → green, 1 → dark red), and makes the
container build reproducible from `requirements.txt` alone. The backend was
rebuilt, the stack restarted and all Docker checks re-run successfully.

A second issue surfaced immediately afterwards: the **frontend container was
reported unhealthy even though nginx served traffic correctly**. The health
probe used `http://localhost/`, and busybox `wget` resolves `localhost` to IPv6
`::1` first while nginx listens on IPv4 `0.0.0.0:80`, producing
`Connection refused`. The compose-level `healthcheck` overrides the Dockerfile
one, so both were changed to the IPv4 literal `http://127.0.0.1/`. After
recreating the container, `docker compose ps` reports all three services as
**healthy** and the Docker smoke test passes.

---

## 5. Model results

### 5.1 Crop health — historical EfficientNet-B0 cross-domain study

The current deployed model is the ConvNeXt-Tiny v3 checkpoint described in §14.
The results below are the controlled EfficientNet-B0 comparison that preceded it.

Previous deployed field-robust checkpoint (`crop-health-v2.0.0-field-robust`, `mixed`):

| Metric | PlantVillage (lab) | PlantDoc (field) |
| --- | --- | --- |
| Accuracy | 0.9511 | 0.6780 |
| Macro precision | — | 0.6969 |
| Macro recall | — | 0.6558 |
| Macro F1 | 0.9507 | 0.6501 |
| Weighted F1 | — | 0.6809 |
| Test images | 266 | 236 |

Controlled cross-domain comparison (same manifest and seed):

| Protocol | Lab accuracy | Field accuracy |
| --- | --- | --- |
| Lab only (`baseline_pv`) | 0.9549 | 0.3220 |
| Field only (`plantdoc_only`) | 0.3120 | 0.6822 |
| **Joint (`mixed`, previous deployed baseline)** | **0.9511** | **0.6653** |
| Two-stage (`two_stage`) | 0.8308 | 0.5551 |

Trained jointly on PlantVillage (1,900 images) and PlantDoc (2,572 recovered
images), 192 px, 12 epochs, AdamW, inverse-frequency weighted cross-entropy,
cosine schedule and early stopping on validation macro-F1. No test image is used
for training or checkpoint selection. Grad-CAM is generated from the last
convolutional block and saved as heat map + overlay. The original lab-only
`crop-health-v1.0.0` metrics (0.9361) are historical and are preserved only in
the backup directory; they are not valid field performance. Full data:
`ml/crop_health/evaluation/cross_domain_results_all.json`.

### 5.2 Yield (ExtraTrees + split-conformal 80% interval)

| Metric | Held-out 2015 |
| --- | --- |
| MAE | 14.7151 q/ha |
| RMSE | 36.5968 q/ha |
| R² | 0.9533 |
| MAPE | 57.52% |
| 80% interval coverage | 0.8492 |
| Mean half-width | 17.4339 q/ha |

Chronological split (train ≤ 2012, validation 2013–2014, test 2015). ExtraTrees
won the validation comparison against RandomForest, HistGradientBoosting,
GradientBoosting and a mean baseline. MAPE is high because yields are skewed and
small-area plots dominate percentage error; MAE/RMSE and coverage are the
primary metrics.

### 5.3 Market forecasting

Five candidates (seasonal naive, moving average, linear trend weekly, random
forest, gradient boosting) are compared on a chronological tail by MAE, then the
winner is refitted on the full history. Intervals are empirical 80% absolute
residuals, widened by `√step`. Minimum 21 observations; Sugarcane (7
observations) correctly returns `422 insufficient_data`.

The bundled Agmarknet window is 2026-07-02 → 2026-09-24, so forecasts are
short-horizon and labelled experimental.

Live rates are served separately by `GET /api/v1/market/live-rates`, which
combines the official Agmarknet/data.gov.in daily mandi feed with the
variety-wise daily market-price resource, deduplicated with the primary feed
preferred (or a clearly-labelled keyless five-state mirror when no API key is
set). Each response carries the real provider, both contributing resources in
`sources`, source URLs, licence, observation date and freshness, with
`is_demo=false`. The Market page opens on a farmer-first live view: the best
price per kg, the mandi offering it, freshness and a few nearby mandis are shown
first; resource IDs, licences and the full raw table remain available behind
“View data details”. The bundled series remains the offline fallback. Verified
on 2026-11-25: official provider, latest
observation 2026-11-25, both official resources contributing rows, and 0 days
old for all 14 crops and the five South India filter states.

---

## 6. Acceptance criteria

| Requirement | Status | Evidence |
| --- | --- | --- |
| Seven-layer architecture | Done | `docs/ARCHITECTURE.md` |
| Decision engine as a separate testable module | Done | `app/services/decision/`, 17 unit tests |
| FastAPI + Pydantic + SQLAlchemy + Alembic | Done | routers, schemas, models, migration |
| PostgreSQL with SQLite dev fallback | Done | Compose PostgreSQL verified; SQLite tests |
| React + Vite + TS + Tailwind + shadcn-style UI | Done | 10 authenticated pages |
| TanStack Query, RHF, Zod, Recharts, Lucide | Done | used across pages |
| JWT access/refresh, ownership isolation | Done | auth and isolation tests |
| Upload validation, rate limiting, CORS, logging | Done | service/middleware + tests |
| PyTorch CNN + Grad-CAM | Done | real mode verified locally and in Docker |
| sklearn yield model + calibrated uncertainty | Done | conformal coverage 0.8492 |
| Chronological market forecasting | Done | tail validation, no shuffle |
| Real vs demo clearly separated | Done | `model_mode`, `is_demo`, UI banners, status endpoint |
| Real public datasets, no invented data | Done | provenance in `DATASETS.md` and `ML_PIPELINE.md` |
| Every button calls the backend | Done | all pages wired to `/api/v1` |
| Tests written and run | Done | 104 backend + 26 frontend |
| Dockerfiles, compose, README, docs | Done | all present and verified |
| End-to-end workflow verified | Done | local and Docker smoke tests |

---

## 7. Security posture

- bcrypt password hashing; JWT HS256 with `jti`, type and expiry claims.
- Access tokens default to 60 minutes; refresh tokens to 7 days and are rotated.
- Logout revokes the presented refresh token; revoked JTIs are persisted.
- Ownership enforced in every service query; farm-level dependency returns 403,
  service-level lookups return 404 to avoid leaking existence.
- Uploads: MIME allow-list, 8 MB limit, 4096 px limit, decode verification,
  SHA-256 dedupe, read-only static serving.
- Rate limiting: 120 requests/minute, 20 for auth routes; disabled in tests.
- CORS origins are explicit and configurable.
- Production does not call `create_all`; Alembic owns the schema.
- Errors use a generic envelope with a request ID; internals are logged, not
  returned.
- Default secrets and demo credentials are marked development-only in
  `.env.example` and the README.

---

## 8. Known limitations and unverified items

These are stated explicitly rather than hidden:

1. **PlantVillage is controlled-condition data.** Field accuracy will be lower;
   the app presents crop health as a screening aid, not a diagnosis.
2. **The market window is ~3 months.** Annual seasonality cannot be learned;
   long horizons are unreliable. Sugarcane cannot be forecast at all (7
   observations).
3. **The yield model has no soil, weather, irrigation or fertiliser features**
   because the historical dataset has no paired records. This is the largest
   accuracy limitation.
4. **Yield MAPE is 57.52%** on the held-out year; absolute error and interval
   coverage are the meaningful metrics.
5. **OSRM routing is implemented but not covered by automated tests.** Tests and
   smoke runs use the geodesic fallback (`use_routing=false`); OSRM depends on a
   public network service.
6. **Weather depends on Open-Meteo.** It degrades gracefully and applies a risk
   floor when offline; the smoke run did reach the live service.
7. **No browser-driven E2E suite.** Frontend correctness is covered by unit
   tests, the TypeScript build and API-level smoke tests. The pages are wired to
   the backend but are not exercised by Playwright/Cypress.
8. **Demo records are illustrative.** Demo buyers and offers are labelled and
   must not be treated as real counterparties.
9. **No payment, logistics booking or government-API integration.** Transport is
   an estimate; market import is CSV-based.
10. **Docker verification requires Docker Desktop.** Local SQLite verification
    is independent of Docker.

---

## 9. How to run

### Local

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and sign in with `demo@agritwin.in` /
`Demo@12345`.

### Docker

```powershell
copy .env.example .env
docker compose build
docker compose up -d
docker compose ps
```

Frontend `http://localhost:5173`, API `http://localhost:8000`,
docs `http://localhost:8000/docs`, PostgreSQL `localhost:5432`.

### Tests

```powershell
cd backend; python -m pytest -q --disable-warnings
cd frontend; npm test
python scripts\smoke_api.py
python scripts\smoke_docker.py      # requires the Compose stack
```

---

## 10. Future work

1. Add soil, weather and irrigation features to the yield model using a paired
   dataset (e.g. district-level weather joins).
2. Extend the market feed to multiple years and add arrivals/rainfall features.
3. Add a browser E2E suite and OSRM integration tests with a local routing
   container.
4. Add Hindi/Marathi localisation and voice input for low-literacy users.
5. Integrate real buyer channels and logistics booking behind the existing
   service interfaces.
6. Calibrate the decision policy with farmer field trials and track realised
   outcomes against recommendations.
7. Train crop health on field photographs with domain adaptation, not only
   PlantVillage.

---

## 11. Conclusion

AgriTwin delivers a working, tested, documented and containerised system that
connects real datasets and trained models to a decision the farmer actually
faces. The decision engine is the differentiator: deterministic, explainable,
uncertainty-aware and independently testable. The project is honest about its
limits — a short market window, a controlled-condition image dataset and a yield
model without soil or weather inputs — and every one of those limits is surfaced
in the product rather than concealed.

---

## 12. Addendum — final verification and last experiment (2026-11-24)

The delivered workspace was re-verified on 2026-11-24 after the last training experiment:

| Check | Result |
| --- | --- |
| Backend suite (`python -m pytest -q --disable-warnings`) | **98 passed** |
| Frontend suite (`npm test -- --run`) | **26 passed** |
| Frontend production build (`npm run build`, includes `tsc -b`) | **passed** (chunk-size advisory only) |
| Local end-to-end smoke (`python scripts\smoke_api.py`) | **passed**; `crop_health: real`, Grad-CAM generated, decision `SELL`, report persisted |

**Label-smoothing + mixup experiment — completed and rejected.** The last pending run
(`--label-smoothing 0.1 --mixup-alpha 0.2`, 192 px, seed 42, 20 epochs, patience 5, AMP) reached
0.9549 lab / **0.6610** field accuracy with macro-F1 0.5584
(`ml/crop_health/evaluation/reg/cross_domain_results.json`). Lab accuracy improved by 0.0038, but
field accuracy fell by 0.0170 and macro-F1 by 0.0917 relative to the then-deployed v2 checkpoint
(0.6780 / 0.6501). Per the pre-registered promotion rule — promote only if field accuracy beats
0.6780 — the candidate at `backend/app/ml/artifacts/crop_health_reg/` was **not** promoted. The
paper draft and LaTeX macros now record this as an honest negative result; no `[FINAL]` markers
remain.

Docker Compose verification from section 4.4 remains valid as recorded on 2026-11-04. The Docker
CLI is installed in the current workspace, but the daemon was not running on 2026-11-24, so the
containers were not re-built on that date; the SQLite/local verification above is independent of
Docker.

The author name and affiliation were recovered from the project's own Review 1 records and filled
into `docs/PAPER_DRAFT.md` and `docs/paper/agritwin.tex`. The remaining submission items (contact
email, city/country, target venue and bibliography verification) still require the project owner
and are listed in `docs/RESUME_TOMORROW.md`.

---

## 13. Addendum — code audit hardening (2026-11-24)

Independent backend and frontend audits confirmed that both tiers are substantive implementations
with no stubs, broken routes or missing production endpoints. The concrete defects they found were
fixed and re-verified:

**Backend — PATCH validation parity.** Several update schemas accepted values that the matching
create schema rejected (invalid enums, unpaired coordinates, harvest before sowing, offer expiry
before the offer date and min/max quantity inversions). `validate_patch()` in
`backend/app/schemas/common.py` now merges the stored record with the partial update and re-runs
the create schema's validators, returning a standard 422 error envelope. It is used by the buyer,
offer, farm and crop update services; `UserUpdate` also gained name-trimming and state validation.
`backend/tests/test_patch_validation.py` covers ten of these cases. The backend suite is now
**98 passed** (including the new architecture and TTA regression tests).

**Frontend — navigation and hygiene.** The Settings page now keeps its visible tab in sync with
`?tab=` when the notification bell is clicked while the page is mounted. Dashboard navigation uses
React Router instead of a full-page reload, and the 404 page uses real links instead of nested
`<a>`/`<button>` elements. Nine unused imports/locals (including a redundant `/system/options`
request) were removed. TypeScript, 26 tests and the production build all pass.

**Documentation precision.** The README auth statement now lists all ten public endpoints and
discloses that `/uploads` is served statically. Stale "ExG pending" and v1-model claims in
`docs/RESEARCH_PAPER_PLAN.md`, `docs/REVIT_RELEVANCE_TO_AGRITWIN.md` and the research docs were
replaced with the measured v2 results and the rejected ablations.

**Known limitations deliberately left unchanged** (documented, not defects): development-only
config defaults (insecure JWT secret, demo mode, SQLite) are for local use and must be overridden
in production; rate limiting is in-process and unsuitable for multi-worker deployments; model
weights are gitignored because of their size; and 12 class names differ by punctuation between the
deployed metadata and the advisory catalogue, which `labels.py` normalises before lookup.

---

## 14. Addendum — ConvNeXt-Tiny deployment and operator-aligned TTA

A new candidate was trained to improve on the v2 field baseline rather than only
re-test the original EfficientNet-B0 recipe. The authoritative record is
[docs/CROP_HEALTH_V3.md](CROP_HEALTH_V3.md); the key acceptance facts are:

| Item | Result |
| --- | --- |
| New architecture | `convnext_tiny` (training, serving, benchmark and Grad-CAM all updated) |
| Data hygiene | 12 duplicate image groups found; 11 train/test leaks removed via `manifest_dedup.json` (4,472 → 4,460 entries) |
| Single-view candidate | 0.9774 lab / **0.6907 field**, macro-F1 0.9773 / 0.6833 |
| Promotion gate | field delta **+0.0127** over 0.6780; identical 38-class order; dry run then `--apply` |
| Unconstrained deployed inference | 4-view TTA, **0.9812 lab / 0.7161 field**, field macro-F1 0.7093 |
| TTA evidence | +0.0254 field over the promoted single-view model; fixes 9 / breaks 3 images; low-confidence accuracy 0.3333 → 0.4167 |
| Soft crop prior (2026-11-25) | deployed `alpha=0.95`; 0.8093 field with correct hint, 0.7754 with 20% wrong hints; hard prior rejected |
| Reproducibility | CUDA and CPU TTA both return 0.7161; crop-prior CUDA/CPU checks agree |
| Backup | `C:\Users\arvap\AppData\Local\Temp\opencode\crop_health_backup_20261124_192631` |

The promotion rule was applied before TTA was enabled: the weights were promoted
only after the single-view field accuracy strictly exceeded 0.6780. The TTA flag
was then enabled in metadata only after a further gain was measured on the same
held-out PlantDoc test split. `metadata.json` keeps `single_view_metrics`
separate from the serving `metrics`, and `info()` exposes `tta_views=4`.

TTA is now powered by a single helper shared by `CropHealthService.predict()`
and `tta_eval.py`, so the measured transform grid cannot drift from production.
The earlier v2 decision to reject 4-view TTA remains valid for that model (only
+0.0085 field and no low-confidence gain); the v3 model has a materially larger
gain and therefore a different decision.

The selected farm crop is now used as a soft external prior on 2026-11-25.
`apply_crop_prior()` reweights the 4-view probabilities toward the chosen crop's
classes only when that crop maps to a trained group; unsupported crops such as
Onion, Rice and Wheat fall back unchanged. With `alpha=0.95`, held-out PlantDoc
accuracy is 0.8093 for a correct hint and 0.7754 when 20% of hints are wrong.
`alpha=1.0` scores 0.8305 with correct hints but collapses to 0.6568 with 20%
wrong hints, so it was not deployed. This is a serving enhancement measured with
`ml/crop_health/evaluation/crop_prior_eval.py`; the promotion baseline remains
0.7161. Full evidence is in `docs/CROP_HEALTH_V3.md`.

Final verification after this change: backend **98 passed**, frontend **26
passed**, frontend production build passed, and `python scripts\smoke_api.py`
passed with `crop_health: real`, ConvNeXt-Tiny loaded, Grad-CAM generated,
decision `SELL` and report persisted. The served prediction took about 1.76 s on
CPU with TTA, the expected cost of four forward passes. The five ad-hoc
Wikipedia/Google photos were rechecked and are reported honestly in
`docs/CROP_HEALTH_V3.md`: 2/5 exact matches, with two low-confidence INSPECT
results. They are smoke checks, not a labelled evaluation set.
