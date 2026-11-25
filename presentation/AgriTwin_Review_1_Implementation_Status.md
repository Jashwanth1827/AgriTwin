# AgriTwin — Review 1 Implementation Status

**Project:** AgriTwin: AI-Driven Crop Health and Market Intelligence System
**Student:** Jashwanth Aravapalli — B.Tech CSE (AI & ML), Keshav Memorial Engineering College
**Review:** Review 1 — 5 November 2026
**Audit date:** 4 November 2026
**Audit method:** direct inspection of the working tree, model artifacts, datasets, API surface, database schema, test suite, and the running Docker Compose stack (`http://localhost:5173`, API `http://localhost:8000`).

> This document is deliberately conservative. A module is marked **Completed and verified** only when (a) the code exists, (b) it runs, and (c) there is direct evidence — a passing test, a live API response, or a captured screenshot. A file that merely exists is not treated as evidence.

> **Historical snapshot — 4 November 2026.** The crop-health numbers below are the original v1
> (`crop-health-v1.0.0`, 0.9361 lab accuracy) results recorded at Review 1. They were superseded
> on 2026-11-24 by the deployed `crop-health-v2.0.0-field-robust` checkpoint
> (**0.9511 lab / 0.6780 field**, macro-F1 0.9507 / 0.6501) and the completed ExG, 256 px, TTA and
> regularizer ablations. Before quoting crop-health figures, use `docs/FINAL_REPORT.md` §12–13 and
> `docs/RESUME_TOMORROW.md`.

---

## 1. Status legend

| Status | Meaning in this report |
|---|---|
| **Completed and verified** | Implemented, exercised at runtime, and evidenced by tests and/or a live capture. |
| **Implemented but not fully tested** | Code path exists and runs, but at least one branch lacks automated coverage. |
| **Partially implemented** | A working subset exists; a named capability within the module is absent. |
| **In progress** | Scaffolding or design exists; the user-facing behaviour is not dependable yet. |
| **Planned** | Designed or stated as future work; no working implementation in this repository. |
| **Blocked** | Cannot proceed without an external dependency (data feed, credential, hardware, approval). |

---

## 2. Module implementation matrix

### 2.1 Platform modules

| Module | Status | Evidence inspected | Remaining work |
|---|---|---|---|
| **Frontend** | **Completed and verified** | 13 page files in `frontend/src/pages/` (10 authenticated + login + register + not-found); 11 routes in `frontend/src/App.tsx`; production build succeeds; 26 Vitest tests across 3 files; live screenshots of dashboard, crop health, market, yield, decisions, buyers, transport. | Field usability testing with real farmers; accessibility audit; mobile-specific layout review. |
| **Backend API** | **Completed and verified** | 70 route decorators across 11 router modules in `backend/app/api/v1/`; FastAPI 0.115.5; 75 Pytest tests, all passing; OpenAPI schema served at `/docs`; structured JSON logging, CORS, rate limiting. | OpenAPI contract tests; load testing; pagination review on large result sets. |
| **Database** | **Completed and verified** | 21 mapped tables (`__tablename__`) in `backend/app/models/`; one Alembic migration `20261104_0014_709bc5e375e1_initial_schema.py`; PostgreSQL 16 in Docker; SQLite for local dev; `alembic upgrade head` runs before Uvicorn in the container. | Seed/rollback runbook; index review on `market_price_records` as data grows. |
| **Authentication & security** | **Completed and verified** | JWT access + refresh tokens (`PyJWT` 2.15.1), bcrypt 5.0.0 hashing, `revoked_tokens` table, per-user scoping on every query, upload type/size validation, rate limiting; 8 auth tests. | Password-reset flow; refresh-token rotation policy; audit log export. |
| **Deployment** | **Completed and verified** | `docker-compose.yml` with `db`, `backend`, `frontend`; nginx serving the built SPA and proxying `/api`; healthchecks; stack is currently healthy. | CI pipeline; HTTPS termination; managed database and backups. |
| **Reports & notifications** | **Completed and verified** | `system.py` routes for reports (create/list/get/delete) and notifications (list/mark read/mark all read); `reports` and `notifications` tables; report generation exercised by the smoke run. | Scheduled/email delivery. |

### 2.2 Intelligence modules

| Module | Status | Evidence inspected | Remaining work |
|---|---|---|---|
| **Crop Health AI** | **Completed and verified** | `model.pt` (16,504,531 bytes) + `metadata.json` in `backend/app/ml/artifacts/crop_health/`; EfficientNet-B0, 38 PlantVillage classes, 192 px input; trained 6 epochs in 788 s; test accuracy **0.9361**, macro-F1 **0.9361**, macro-precision **0.9515**, loss **0.252** on 266 held-out images; Grad-CAM implemented from the last convolutional block; served in **real mode** (live response: Tomato Early blight, 98.0 % confidence, 122 ms); 7 crop-health tests. | Field-condition evaluation; calibration (temperature scaling); more classes; per-class decision thresholds. |
| **Yield Prediction** | **Completed and verified** | `model.joblib` (314,174,501 bytes) + `metadata.json`; ExtraTrees; 80,000 train / 9,867 validation / 305 test rows; chronological split (train ≤ 2012, validation 2013–14, test 2015); MAE **14.7151 q/ha**, RMSE **36.5968**, R² **0.9533**, MAPE **57.52 %**; split-conformal 80 % interval with empirical coverage **0.8492** and half-width **17.4339 q/ha**; 6 yield tests. | Add soil, weather, irrigation and variety features; reduce MAPE on small plots; regional re-training. |
| **Market Intelligence** | **Completed and verified** (experimental forecasting) | `market_prices.csv`: 2,229 real rows, 14 crops, 35 markets, 2026-07-02 → 2026-09-24; five forecasters fitted chronologically; LinearTrendWeekly selected for onion with MAE **410.34** and RMSE **447.14** INR/quintal; 14-day forecast ₹6,441/q (₹5,884–₹6,998); 41-day data age surfaced in the UI; 11 market tests; insufficient-data guard returns **422** (Sugarcane has 7 observations). | Longer historical window; arrivals and rainfall features; live Agmarknet ingestion; model persistence instead of per-request fitting. |
| **Buyer Intelligence** | **Completed and verified** (demo records) | 8 endpoints (CRUD buyers, list/patch/delete offers); `buyers`, `buyer_offers` tables; eligibility, capacity and offer-age risk computed; 4 buyer tests. | Real buyer network and verified offers; buyer-side onboarding; capacity-aware allocation across multiple buyers. |
| **Transportation** | **Implemented but not fully tested** | Vehicle catalogue (tempo, mini truck, truck, large truck, tractor trolley); distance × trips × rate cost model; OSRM road routing implemented with a geodesic haversine fallback; 5 transport tests. **Only the fallback path is covered by automated tests.** | Contract test against a live OSRM instance; multi-stop route optimisation; toll and loading/unloading charges. |
| **Decision Engine** | **Completed and verified** | `backend/app/services/decision/` — pure Python, no I/O, no clock dependency; policy externalised to `config/decision_policy.json` v1.0.1; 8 weighted risk components; buyer-vs-mandi net realisation in `Decimal`; 9 ordered rules; 17 unit tests + 6 API tests; live decision #4 produced SELL at ₹6,371.67/q with risk 0.4415 and confidence 0.932. | Sensitivity analysis; back-testing against realised prices; farmer-facing explanation study. |
| **Weather** | **Implemented but not fully tested** | Open-Meteo geocoding and forecast integration with a graceful fallback; `weather_records` table; `weather_max_age_days = 3` freshness rule. | Offline cache tests; provider-outage tests. |

### 2.3 Explicitly not implemented

| Capability | Status | Note |
|---|---|---|
| IoT soil sensors | **Planned** | No sensor integration or ingestion endpoint exists. Soil data is user-entered. |
| Live buyer / mandi API | **Planned** | Buyer offers are demo records, labelled as such in the UI and in every API response. |
| Payment or logistics booking | **Planned** | Transport is cost estimation only; nothing is booked. |
| Route optimisation (multi-stop) | **Partially implemented** | Single-leg road distance is available; no vehicle-routing optimisation. |
| Field-level validation | **Planned** | No farmer trial or field dataset yet. |
| Crop/weed segmentation | **Not present in this repository** | See §5. |
| Mobile application | **Planned** | The web UI is responsive; no native app. |
| Multi-language UI | **Partially implemented** | An `En` language control exists; additional locales are not complete. |

---

## 3. Repository evidence inventory

| Item | Count / value | Where |
|---|---|---|
| API route decorators | 70 | `backend/app/api/v1/*.py` |
| API router modules | 11 | auth, system, farms, crop_health, yield, market, buyers, transport, weather, decisions, dashboard |
| Frontend page files | 13 | `frontend/src/pages/` |
| Frontend routes | 11 | `frontend/src/App.tsx` |
| Database tables | 21 | `backend/app/models/*.py` |
| Alembic migrations | 1 | `backend/alembic/versions/` |
| Backend tests | 75 (all passing) | `backend/tests/` |
| Decision-engine unit tests | 17 | `backend/tests/test_decision_engine.py` |
| Frontend tests | 26 | `api.test.ts` (11), `auth.test.tsx` (6), `utils.test.ts` (9) |
| Documentation | 4 documents | `docs/ARCHITECTURE.md`, `ML_PIPELINE.md`, `DECISION_ENGINE.md`, `FINAL_REPORT.md` |

### 3.1 Datasets (verified by reading the files)

| Dataset | Rows / images | Coverage | File |
|---|---|---|---|
| India district crop production | **246,091 rows** | 1997–2015; columns `State_Name, District_Name, Crop_Year, Season, Crop, Area, Production` | `backend/app/data/crop_production.csv` |
| Agmarknet mandi prices | **2,229 rows** | 14 crops, 35 markets, 2026-07-02 → 2026-09-24 | `backend/app/data/market_prices.csv` |
| Historical yield sample | **3,000 rows** | state, district, crop, season, year, area, production, yield | `backend/app/data/historical_yield_sample.csv` |
| PlantVillage subset | **1,900 images** | 38 classes × 50 images; split 1,368 / 266 / 266 | `ml/crop_health/data/plantvillage_subset/` |

### 3.2 Model artifacts (verified by file size and metadata)

| Artifact | Size | Version | Key metrics |
|---|---|---|---|
| `crop_health/model.pt` | 16,504,531 B | `crop-health-v1.0.0` | acc 0.9361 · macro-F1 0.9361 · precision 0.9515 · loss 0.252 |
| `crop_health/metadata.json` | 28,216 B | — | 6 epochs, 788 s, 38 classes, per-class metrics, confusion matrix |
| `yield_prediction/model.joblib` | 314,174,501 B | `yield-v1.0.0` | MAE 14.7151 · R² 0.9533 · coverage 0.8492 |
| `yield_prediction/metadata.json` | 2,462 B | — | split definition, model comparison, conformal calibration |

---

## 4. Verified live behaviour (4 November 2026)

| Check | Result |
|---|---|
| Docker stack health | `agritwin-db-1`, `agritwin-backend-1`, `agritwin-frontend-1` all healthy |
| Login | `demo@agritwin.in` / `Demo@12345` → JWT issued, dashboard loads as "Demo Farmer" |
| Crop-health inference | Real leaf upload → Tomato Early blight, **98.0 %**, 122 ms, Grad-CAM overlay returned |
| Yield prediction | Onion, Kisan Green Farm, 3.5 ha → **392 q**, 80 % interval **331–453 q**, confidence 82 %, completeness 100 % |
| Market forecast | Onion, 14-day → **₹6,441/q**, interval **₹5,884–₹6,998**, LinearTrendWeekly, 41-day data age |
| Decision engine | Decision #4 → **SELL**, 392.028 q, **₹6,371.67/q**, net **₹2,497,872.73**, risk **0.4415** (medium), confidence **0.932** |
| Buyer comparison | Nashik ₹6,150 → net ₹6,071.75; Sahyadri ₹6,030 → net ₹5,946.94; mandi wins |
| Insufficient-data guard | Sugarcane forecast → HTTP **422** rather than a fabricated number |

---

## 5. The CropAndWeed / U-Net question — audit finding

The review brief references a previously developed `CropAndWeed_Final` dataset (8,034 images; 6,427 train / 1,607 validation) and a checkpoint `unet_res34_2class_best.pth`.

**Audit result: neither exists in this repository.**

- A recursive search for `cropandweed`, `unet`, `res34`, `*.pth` and `*.pt` returned only the current crop-health artifact `model.pt`.
- The only image dataset present is the 38-class PlantVillage subset under `ml/crop_health/data/`.
- The only segmentation-like output in the running system is Grad-CAM, which is an **explanation overlay for a classifier**, not a segmentation mask.

**Consequence for the review:** AgriTwin's crop-health module is **image-level multi-class classification** (38 disease/healthy classes), not semantic segmentation. The presentation states this explicitly in a scope-note box on slide 8. The historical CropAndWeed work should be described as an earlier, separate experiment — not as part of this codebase and not as a segmentation capability of AgriTwin.

| Question | Answer |
|---|---|
| Is the deployed model segmentation? | No — classification. |
| Is there a U-Net in the repository? | No. |
| Is there a 2-class crop/weed model? | No. |
| Is Grad-CAM a segmentation mask? | No — a coarse localisation heat map from classifier gradients. |
| What does the model output? | A 38-way probability distribution over disease classes, plus severity and recommendations. |

---

## 6. Screenshot and asset inventory

All screenshots were captured from the running application on 4 November 2026. None were mocked up in static HTML.

| File | Source | Size (px) | Used on |
|---|---|---|---|
| `assets/login.jpeg` | `/login` | 1140 × 958 | backup |
| `assets/dashboard.png` | `/dashboard` after demo login | 1120 × 958 | backup |
| `assets/crop-health.png` | `/crop-health` — real inference result | 1120 × 958 | slide 8, 11 |
| `assets/market-intelligence.png` | `/market` — onion 14-day forecast | 1120 × 958 | slide 11 |
| `assets/yield-prediction.png` | `/yield` — onion prediction | 1120 × 958 | slide 11 |
| `assets/decision-engine.png` | `/decisions` — decision #4, SELL | 1120 × 958 | slide 11 |
| `assets/buyers.png` | `/buyers` | 1120 × 958 | backup |
| `assets/transport.png` | `/transport` | 1120 × 958 | backup |
| `assets/gradcam.png` | API `gradcam_url` | 192 × 192 | slides 1, 8 |
| `assets/leaf.jpg` | API `image_url` (real uploaded leaf) | 256 × 256 | slide 1 |
| `assets/decision_4.json` | `GET /api/v1/decisions/4` | — | chart + table source |
| `assets/chart_crop_training.png` | `crop_health/metadata.json` history | — | slide 8 |
| `assets/chart_crop_classes.png` | `crop_health/metadata.json` per-class F1 | — | slide 8 |
| `assets/chart_yield_models.png` | `yield_prediction/metadata.json` comparison | — | slide 9 |
| `assets/chart_market_models.png` | live forecast model comparison | — | slide 9 |
| `assets/chart_buyer_net.png` | `decision_4.json` buyer evaluations | — | slide 10 |
| `assets/chart_risk.png` | `decision_4.json` risk factors | — | slide 10 |

**Validation performed:** every image opened with PIL; dimensions and standard deviation recorded to confirm non-blank, non-uniform content. The model used for this audit cannot visually inspect images, so authenticity rests on the capture path (live browser against the running stack), not on visual review.

---

## 7. Honest gaps and how to answer them

| Gap | Why it matters | Current mitigation | Next step |
|---|---|---|---|
| PlantVillage is controlled-condition imagery | Field accuracy will be lower than 93.6 % | UI labels results as a screening aid, not a diagnosis | Collect field images; report field accuracy separately |
| Yield MAPE is 57.5 % | Percentage error is dominated by small, right-skewed plots | MAE, R² and interval coverage reported alongside | Add features; stratify error by area |
| Market window is ~3 months | Short-horizon only; no seasonality | UI flags data age; forecasts marked experimental | Ingest a multi-year Agmarknet history |
| Buyer offers are demo records | Net realisation depends on synthetic offers | Every response and screen labels demo data | Onboard real buyers |
| Mandi transport cost treated as zero in decision #4 | Understates cost for the mandi channel | Recorded as an explicit assumption in the API response | Require a transport estimate or block the comparison |
| Buyer capacity is limited (80 q and 120 q of 392 q) | Ranking is per-quintal, not a full-allocation plan | Capacity surfaced in assumptions | Solve a capacity-constrained allocation across buyers |
| OSRM routing lacks automated coverage | Road distance may differ from haversine | Geodesic fallback is tested | Add an OSRM contract test |
| No field validation | Impact on farmer income is unproven | Prototype proves integration only | Design a pilot with a local FPO |

---

## 8. What remains for Review 2

1. Longer market history and live ingestion.
2. Real buyer onboarding and capacity-constrained allocation.
3. Field-image dataset and a reported field-accuracy figure.
4. Yield features: soil, weather, irrigation, variety.
5. OSRM contract tests and multi-stop routing.
6. Calibration of the crop-health classifier.
7. Farmer pilot and an evaluation protocol for decision quality.
8. CI pipeline, HTTPS, managed database, backups.

---

## 9. Bottom line

The repository contains a **working, tested, end-to-end prototype** — not a slide concept. Seven layers are implemented, three model families are trained and serving, the decision engine is deterministic and unit-tested, the database and API are live, and the UI has been captured from the running system.

The honest limitations are data breadth and field validation, not missing architecture. The presentation is structured to make that distinction explicit.
