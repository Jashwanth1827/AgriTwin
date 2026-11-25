# AgriTwin

**Uncertainty-aware crop-health, yield, market-intelligence and decision support for Indian farmers.**

AgriTwin is a full-stack B.Tech CSE (AI & ML) major project. A farmer records farms and crops, uploads a leaf photograph, requests a yield estimate, explores mandi prices and buyer offers, compares transport options, and asks one practical question:

> *Should I sell now, wait, or inspect the crop first?*

The answer comes from a **deterministic, explainable decision engine** that fuses model outputs, data freshness, buyer eligibility, transport cost and risk. It is not an LLM prompt and it is not a black box.

---

## Table of contents

- [What is implemented](#what-is-implemented)
- [Architecture at a glance](#architecture-at-a-glance)
- [Quick start (local)](#quick-start-local)
- [Docker Compose](#docker-compose)
- [Demo account](#demo-account)
- [Real vs demo mode](#real-vs-demo-mode)
- [API surface](#api-surface)
- [Tests and verification](#tests-and-verification)
- [Datasets and model provenance](#datasets-and-model-provenance)
- [Project layout](#project-layout)
- [Documentation](#documentation)
- [Known limitations](#known-limitations)
- [Security notes](#security-notes)

---

## What is implemented

| Area | Capability |
| --- | --- |
| Authentication | JWT access + refresh tokens, bcrypt password hashing, register/login/refresh/logout, profile update |
| Ownership isolation | Every farm, crop, buyer, offer, prediction, decision and report is scoped to its owner |
| Farms & crops | CRUD, Indian states, seasons, soil types, growth stages, harvest dates, geo-coordinates |
| Crop health | 38-class cross-domain ConvNeXt-Tiny (4-view TTA + soft crop prior), Grad-CAM heat-map, severity/advisory text, real/demo labelling |
| Yield | ExtraTrees regressor with split-conformal 80% prediction intervals and harvest readiness |
| Market | Agmarknet price history, trends, chronological forecast comparison, empirical 80% intervals, CSV import |
| Buyers | Buyer CRM, price offers with quantity/expiry constraints, eligibility evaluation |
| Transport | Vehicle profiles, distance and cost estimates, OSRM routing with geodesic fallback |
| Weather | Open-Meteo current conditions and forecast-derived risk, with caching and graceful degradation |
| Decision engine | Ordered SELL / WAIT / INSPECT rules, 8-component weighted risk, scenario comparison, revenue bounds, explanations |
| Dashboard | Aggregate farm/crop/health/yield/market/decision summaries and notifications |
| Reports | Persisted, downloadable JSON reports built from live data |
| Frontend | React 18 + TypeScript SPA with 10 authenticated pages, charts, forms and validation |
| Database | SQLAlchemy 2 models, Alembic migration, SQLite for development and PostgreSQL 16 in Docker |
| Operations | Structured JSON logging, request IDs, rate limiting, CORS, upload validation, health/readiness, Docker Compose |

### The decision engine

The engine answers with one of three actions:

- **SELL** — an eligible channel produces a positive net realisation, data is complete and fresh, risk is within the farmer's preference, and waiting does not clear the uplift threshold after costs.
- **WAIT** — the crop is not harvest-ready, or the forecast shows a material net improvement after holding, deterioration and transport costs.
- **INSPECT** — a severe/low-confidence health result, incomplete data, an over-wide yield interval, stale prices, or risk above the preference cap.

It compares the best eligible buyer offer against the mandi channel on **net realisation**, applies commission and selling costs with `Decimal` arithmetic, and returns a full explanation, factor list, assumptions, missing inputs, data-freshness warnings, scenario values and a revenue interval.

See [docs/DECISION_ENGINE.md](docs/DECISION_ENGINE.md).

---

## Architecture at a glance

```
React SPA (Vite + TypeScript)
        │  /api/v1 (JSON, JWT)
        ▼
FastAPI routers ── auth, farms, crop-health, yield, market,
        │          buyers, transport, weather, decisions,
        │          dashboard, system
        ▼
Service / orchestration layer
        │  decision_service, yield_service, market, transport,
        │  weather, crop_health, buyers, reports, dashboard
        ├──────────────► Decision engine (pure Python)
        │                 policy → risk → fusion → rules
        ▼
ML / inference layer
        │  ConvNeXt-Tiny (4-view TTA) + Grad-CAM
        │  ExtraTrees yield + conformal intervals
        │  Chronological market forecasting
        ▼
Persistence layer
        │  SQLAlchemy models + Alembic
        ▼
PostgreSQL 16 (Docker) / SQLite (local dev)
```

The seven documented layers are: **data, persistence, ML/inference, decision, service/orchestration, API, presentation**. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Quick start (local)

### Prerequisites

- Python **3.12**
- Node.js **20+** and npm
- Optional: Docker Desktop (for the PostgreSQL/nginx stack)
- Optional: internet access for live weather and OSRM routing

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The API starts at `http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`.

On first start the app:

1. creates the SQLite database at `backend/agritwin.db` (development only),
2. creates upload directories,
3. seeds the demo workspace (when `DEMO_MODE=true`),
4. loads the bundled ML artifacts.

The seed is idempotent and loads 2,229 real Agmarknet price rows, 3,000 real historical yield rows and 38 disease classes.

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

The UI starts at `http://localhost:5173`. Vite proxies `/api` and `/uploads` to `http://localhost:8000`.

### 3. Production build

```powershell
cd frontend
npm run build
```

### 4. Tests

```powershell
# Backend (76 tests)
cd backend
python -m pytest -q --disable-warnings

# Frontend (26 tests)
cd frontend
npm test
```

### 5. End-to-end smoke test

With the backend importable from the repository root:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts\smoke_api.py
```

The smoke test logs in, reads every major resource, runs a yield prediction, a market forecast, a transport estimate, a **real CNN crop-health scan with Grad-CAM**, a decision, the dashboard and a report. It fails loudly if any step regresses.

---

## Docker Compose

```powershell
copy .env.example .env
docker compose build
docker compose up -d
docker compose ps
```

| Service | URL / port |
| --- | --- |
| Frontend (nginx) | `http://localhost:5173` |
| Backend (FastAPI) | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` |
| PostgreSQL | `localhost:5432` |

The backend container runs `alembic upgrade head` before starting Uvicorn. The frontend nginx container serves the built SPA and proxies `/api` and `/uploads` to `backend:8000`.

Once the stack is healthy, verify it end-to-end through nginx:

```powershell
python scripts\smoke_docker.py
```

The script checks the SPA, health, login, reads, model modes, a market forecast, a real CNN scan with Grad-CAM (including fetching the overlay through the proxy), a decision and a report.

> The default credentials in `.env.example` are **development-only**. Change `JWT_SECRET_KEY`, `POSTGRES_PASSWORD` and `DEMO_MODE` before any real deployment.

To stop and remove containers:

```powershell
docker compose down
```

Add `-v` only when you intentionally want to delete the database and upload volumes.

---

## Demo account

| Field | Value |
| --- | --- |
| Email | `demo@agritwin.in` |
| Password | `Demo@12345` |

The demo workspace contains:

- **Kisan Green Farm** (Maharashtra): Onion harvest-ready, Tomato approaching harvest
- **Yamuna Wheat Fields** (Uttar Pradesh): Wheat just sown
- **Cauvery Paddy Plot** (Tamil Nadu): Rice harvest-ready
- Clearly labelled demo buyers and offers for Onion, Wheat, Rice and Tomato

---

## Real vs demo mode

AgriTwin never silently substitutes synthetic data.

| Signal | Real mode | Demo / fallback mode |
| --- | --- | --- |
| Crop health | Trained `model.pt`; `model_mode="real"`; Grad-CAM generated | Colour/texture heuristic; `model_mode="demo"`, `is_demo=True`, UI warning |
| Yield | Trained `model.joblib`; model version `yield-v1.0.0` | Historical state/crop average, flagged as `historical_average` |
| Market prices | Bundled real Agmarknet observations | — (no synthetic prices) |
| Buyers/offers | User-created records | Seeded records have `is_demo=True` and are labelled in the UI and decisions |
| Weather | Live Open-Meteo | Graceful "unavailable" state; a risk floor is applied |
| Transport | OSRM route when available | Geodesic distance × detour factor, flagged `approximate` |

`GET /api/v1/system/status` reports each model's mode, version, metrics and data freshness so the UI and operators can see exactly what is running.

---

## API surface

Base path: `/api/v1`. Mutating routes and user-data routes require a Bearer access token. The public
read-only endpoints are `GET /`, `GET /system/health`, `GET /system/status`, `GET /system/options`,
`GET /crop-health/model`, `GET /yield/model`, `GET /transport/vehicles`, plus
`POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` and `POST /auth/logout`.
All other routes require authentication. Uploaded images under `/uploads` are served statically
without authentication; treat uploaded filenames as unguessable and keep the deployment behind
access control if leaf photos are sensitive.

| Router | Representative endpoints |
| --- | --- |
| `auth` | `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`, `GET/PATCH /me` |
| `system` | `GET /health`, `GET /status`, `GET /options`, notifications, `GET/POST/DELETE /reports` |
| `farms` | `GET/POST /farms`, `GET/PATCH/DELETE /farms/{id}`, `GET/POST /crops`, `GET/PATCH/DELETE /crops/{id}` |
| `crop-health` | `GET /model`, `GET /classes`, `POST /predict`, `GET /predictions`, `GET/DELETE /predictions/{id}` |
| `yield` | `GET /model`, `POST /predict`, `GET /predictions`, `GET /predictions/{id}`, `GET /readiness/{crop_id}`, `GET /history` |
| `market` | `GET /crops`, `GET /prices`, `GET /markets`, `GET /trends`, `POST /forecast`, `GET /forecasts`, `POST /import` |
| `buyers` | CRUD `/buyers`, CRUD `/buyers/{id}/offers`, `/offers/{id}` |
| `transport` | `GET /vehicles`, `POST /estimate`, `GET /estimates` |
| `weather` | `GET /geocode/search`, `GET /{farm_id}` |
| `decisions` | `GET /policy`, `POST ""`, `GET ""`, `GET/DELETE /{id}` |
| `dashboard` | `GET /overview`, `GET /crop-health`, `GET /market`, `GET /decisions` |

Errors use a consistent JSON envelope with `code`, `message`, `details` and `request_id`. Ownership failures return **403** for farm-scoped resources and **404** for service-scoped resources to avoid leaking existence.

---

## Tests and verification

| Suite | Command | Verified result |
| --- | --- | --- |
| Backend | `python -m pytest -q --disable-warnings` | **98 passed** |
| Frontend | `npm test -- --run` | **26 passed** |
| Frontend build | `npm run build` | **passed** (chunk-size warning only) |
| End-to-end API | `python scripts\smoke_api.py` | **passed**, real ConvNeXt-Tiny + Grad-CAM + TTA |
| Docker stack | `python scripts\smoke_docker.py` | **passed** on 2026-11-04 through nginx + PostgreSQL; daemon unavailable for a re-run in this workspace |
| Alembic | `alembic upgrade head` / `downgrade base` / `upgrade head` | **verified on SQLite** |

The backend suite covers authentication and token refresh, ownership isolation, farm/crop CRUD, buyer and offer validation, decision-engine unit rules, decision API, market data and forecasting, transport, yield readiness and prediction, crop-health upload validation and demo fallback, and system health/status.

---

## Datasets and model provenance

| Artifact | Source | Notes |
| --- | --- | --- |
| `backend/app/data/crop_production.csv` | India district-level crop production 1997–2015 (public mirror of `data.world/thatzprem/agriculture-india`, Kaggle `abhinand05/crop-production-in-india`) | 246,091 rows; production interpreted as tonnes; `yield_q_per_ha = production_tonnes * 10 / area_ha` |
| `backend/app/data/historical_yield_sample.csv` | 3,000-row sample of the above, 2010–2015, 14 supported crops | Seeded regional comparisons |
| `backend/app/data/market_prices.csv` | Agmarknet daily mandi prices, CC BY 4.0 archive `github.com/kunal-rajput-317/mandi-data`, derived from Government of India OGD resource `9ef84268-d588-465a-a308-a864a43d0070` | 2,229 rows, 14 crops, 2026-07-02 → 2026-09-24 |
| PlantVillage subset | `Hemg/new-plant-diseases-dataset` on Hugging Face | 50 images × 38 classes = 1,900 images; not committed; weights are bundled |

Full provenance and limitations: [backend/app/data/DATASETS.md](backend/app/data/DATASETS.md) and [docs/ML_PIPELINE.md](docs/ML_PIPELINE.md).

### Verified model metrics

**Crop health — ConvNeXt-Tiny, 38 classes, 192 px, joint PlantVillage + PlantDoc**

Deployed checkpoint `crop-health-v3.0.0-convnext` with metadata-driven 4-view TTA:

| Metric | PlantVillage (lab) | PlantDoc (field) |
| --- | --- | --- |
| Accuracy | 0.9812 | 0.7161 |
| Macro precision | — | 0.7373 |
| Macro recall | — | 0.7106 |
| Macro F1 | — | 0.7093 |
| Weighted F1 | — | 0.7183 |
| Test images | 266 | 236 |

Without TTA the same weights measure 0.9774 lab / 0.6907 field; both are in
[docs/CROP_HEALTH_V3.md](docs/CROP_HEALTH_V3.md). The previous deployed EfficientNet-B0
re-run was 0.9511 lab / 0.6780 field.

A **soft crop prior** (`alpha=0.95`) is also enabled: when the selected farm crop maps to one
of the 14 trained crop groups, probabilities are reweighted toward that crop before argmax.
On the held-out PlantDoc set this measures **0.8093** with a correct hint and **0.7754** when
20% of hints are wrong; unsupported crops (such as the seeded Onion/Rice/Wheat) fall back to the
unconstrained 0.7161 result. The hard prior is not deployed because it fails under wrong hints.
This is a serving enhancement, not a new promotion metric.

Controlled four-protocol comparison (historical EfficientNet-B0 study, same manifest and seed):

| Protocol | Lab accuracy | Field accuracy |
| --- | --- | --- |
| Lab only (`baseline_pv`) | 0.9549 | 0.3220 |
| Field only (`plantdoc_only`) | 0.3120 | 0.6822 |
| **Joint (`mixed`, previous deployed baseline)** | **0.9511** | **0.6653** |
| Two-stage (`two_stage`) | 0.8308 | 0.5551 |

The 63-point lab→field collapse of the old lab-only model is the reason for the cross-domain work; two-stage adaptation underperformed joint training on both domains and is reported as an honest negative result. Full data: `ml/crop_health/evaluation/cross_domain_results_all.json` and [docs/RESEARCH_PAPER_PLAN.md](docs/RESEARCH_PAPER_PLAN.md).

**Yield — ExtraTrees (selected on 2013–2014 validation)**

| Metric | Held-out 2015 |
| --- | --- |
| MAE | 14.7151 q/ha |
| RMSE | 36.5968 q/ha |
| R² | 0.9533 |
| MAPE | 57.52% |
| 80% interval coverage | 0.8492 |
| Mean half-width | 17.4339 q/ha |

The yield model is intentionally reported with its weak MAPE: yield is highly skewed and small-denominator rows inflate percentage error. MAE/RMSE and interval coverage are the primary selection metrics.

---

## Project layout

```
majorp/
├── backend/
│   ├── alembic/                     # migration environment + initial schema
│   ├── app/
│   │   ├── api/v1/                  # FastAPI routers
│   │   ├── config/                  # decision policy, crop calendar, transport defaults
│   │   ├── core/                    # config, DB, security, logging, errors, rate limit
│   │   ├── data/                    # curated public datasets + provenance
│   │   ├── db/seed.py               # idempotent demo seed
│   │   ├── ml/                      # inference services + trained artifacts
│   │   ├── models/                  # SQLAlchemy models
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/                # orchestration + decision engine
│   │   └── main.py                  # app factory, middleware, lifespan
│   ├── tests/                       # 93 pytest tests
│   ├── Dockerfile
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── components/              # layout + shadcn-style UI primitives
│   │   ├── hooks/                   # reference-data hooks
│   │   ├── lib/                     # API client, auth context, utilities
│   │   ├── pages/                   # 10 authenticated pages + auth pages
│   │   ├── test/                    # 26 Vitest tests
│   │   └── types/
│   ├── Dockerfile
│   └── nginx.conf
├── ml/
│   ├── crop_health/training/        # download, prepare, train
│   └── yield_prediction/training/   # train/evaluate yield model
├── scripts/
│   ├── prepare_datasets.py
│   ├── smoke_api.py
│   └── smoke_docker.py
├── docs/
├── docker-compose.yml
└── .env.example
```

---

## Documentation

- [docs/CROP_HEALTH_V3.md](docs/CROP_HEALTH_V3.md) — authoritative record for the deployed ConvNeXt model and TTA
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — seven layers, data model, request flows, security
- [docs/DECISION_ENGINE.md](docs/DECISION_ENGINE.md) — policy, risk weights, ordered rules, formulas, worked example
- [docs/ML_PIPELINE.md](docs/ML_PIPELINE.md) — datasets, training, splits, metrics, inference, Grad-CAM, limitations
- [docs/DATASETS_AND_LABELS.md](docs/DATASETS_AND_LABELS.md) — dataset provenance, all 38 labels, testing your own photos
- [docs/RESEARCH_PAPER_PLAN.md](docs/RESEARCH_PAPER_PLAN.md) — experiment matrix, measured cross-domain results, paper plan
- [docs/PAPER_DRAFT.md](docs/PAPER_DRAFT.md) — full IEEE-style paper draft generated from the measured results
- [docs/RESUME_TOMORROW.md](docs/RESUME_TOMORROW.md) — current experiment state and exact commands
- [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md) — acceptance criteria, verification evidence, known gaps

---

## Known limitations

1. **Domain shift is real and measured.** A lab-only model drops from 0.9549 accuracy on PlantVillage to 0.3220 on in-the-wild PlantDoc; the deployed ConvNeXt model reaches 0.7161 in the field with 4-view TTA, or 0.8093 when the selected crop hint is correct. Field photographs remain harder, and the app presents results as a screening aid, not a diagnosis. Test your own photos with `python ml/crop_health/evaluation/test_my_images.py --image <path>`.
2. **The Agmarknet slice is short** (2026-07-02 → 2026-09-24). Forecasts are short-horizon and experimental; the UI flags data age. Sugarcane has only 7 observations and cannot be forecast (minimum 21).
3. **The yield model has no soil or weather features** because the historical dataset has no paired soil/weather records. It uses crop, season, state, area and expanding historical averages.
4. **Yield MAPE is high (57.52%)** on the held-out year; absolute error and interval coverage are more meaningful.
5. **OSRM routing is not covered by automated tests.** The smoke test and decision auto-computation use the geodesic fallback (`use_routing=false`); OSRM is implemented but depends on a public network service.
6. **Weather depends on Open-Meteo** and degrades gracefully when offline.
7. **The bundled demo market data ends 2026-09-24.** It is inside the 90-day INSPECT limit at the time of writing but carries a freshness-risk component.
8. **Docker verification requires Docker Desktop.** The Compose stack (PostgreSQL, backend, nginx) was built and smoke-tested successfully; local SQLite verification is independent of Docker.
9. **The demo seed is illustrative.** Demo buyers and offers are labelled and must not be treated as real counterparties.
10. **No payment, logistics booking or government-API integration** is implemented; transport is an estimate and market import is CSV-based.

---

## Security notes

- Passwords are hashed with bcrypt; JWT secrets must be replaced in production.
- Access tokens expire in 60 minutes by default; refresh tokens in 7 days.
- Uploads are restricted by MIME type, size (8 MB) and image dimensions; files are stored under `uploads/` and served read-only.
- Rate limiting is enabled by default (120 requests/minute; 20 for auth).
- CORS origins are explicit and configurable.
- Production startup does **not** call `create_all`; Alembic owns the schema.
- The API returns generic ownership errors and never exposes another user's records.
- Demo credentials and default secrets are clearly marked development-only.

---

## License and attribution

The application code is the project author's work. Datasets retain their original licences and attribution:

- Crop production data: public mirror of the India district-level dataset.
- Agmarknet market data: CC BY 4.0, Government of India Open Government Data, archive by `kunal-rajput-317`.
- PlantVillage: research dataset distributed via Hugging Face (`Hemg/new-plant-diseases-dataset`).
- Weather and geocoding: Open-Meteo.
- Routing: OSRM public demo server.

If you use this project academically, cite the original dataset sources as well as this repository.
