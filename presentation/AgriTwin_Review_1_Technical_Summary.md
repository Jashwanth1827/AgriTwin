# AgriTwin — Technical Summary

**Project:** AgriTwin: AI-Driven Crop Health and Market Intelligence System
**Student:** Jashwanth Aravapalli
**Programme:** B.Tech CSE (AI & ML), Keshav Memorial Engineering College
**Review:** Review 1 — 5 November 2026
**Evidence date:** 4 November 2026

> **Historical snapshot.** Model numbers here are the Review 1 v1 results. Current deployed
> figures and all completed ablations are in `docs/FINAL_REPORT.md` §12–13.

---

## 1. One-paragraph description

AgriTwin is a full-stack agricultural decision-support system. A farmer records farms and crops, uploads a leaf photograph, requests a yield estimate, browses mandi prices and buyer offers, and compares transport options. The system then answers one question: **should the farmer sell now, wait, or inspect the crop first?** The answer is produced by a deterministic, explainable decision engine that fuses model outputs, prediction intervals, data freshness, buyer eligibility, transport cost and an eight-component risk score. It is not an LLM prompt and it is not a black box.

---

## 2. Research contribution

The contribution is **Uncertainty-Aware Fusion and Optimization** — Layer 5 of the architecture.

Most agricultural tools stop at a prediction: a disease label, a yield number, a price forecast. AgriTwin treats each prediction as a *distribution with a reliability profile* and converts it into an economic decision:

1. **Uncertainty is explicit.** Yield and price enter as intervals, not point values.
2. **Economics is net, not gross.** Every channel is scored by net realisation after transport, commission and other selling costs, in `Decimal` arithmetic.
3. **Risk is decomposed.** Eight weighted components produce a composite score with a human-readable contribution per factor.
4. **Rules are ordered and auditable.** The first matching rule wins, and the policy lives in a versioned JSON file.
5. **Every decision is persisted** with its inputs, factors, assumptions and missing inputs.

---

## 3. Architecture — seven layers

```
┌──────────────────────────────────────────────────────────────────────┐
│ 7. IMPACT      healthier crops · better income · reduced risk        │
├──────────────────────────────────────────────────────────────────────┤
│ 6. OUTPUT      health + Grad-CAM · yield interval · harvest window   │
│                buyer comparison · net realisation · SELL/WAIT/INSPECT│
├──────────────────────────────────────────────────────────────────────┤
│ 5. FUSION      uncertainty-aware fusion & optimization  ◄── research │
│                8-component risk · completeness · confidence · rules  │
├──────────────────────────────────────────────────────────────────────┤
│ 4. INTELLIGENCE  yield (ExtraTrees + interval) · market (5 models)   │
│                  harvest readiness · buyers · transport cost         │
├──────────────────────────────────────────────────────────────────────┤
│ 3. CROP HEALTH   EfficientNet-B0 · 38 classes · Grad-CAM             │
├──────────────────────────────────────────────────────────────────────┤
│ 2. PROCESSING    validation · encoding · scaling · chronological     │
│                  series · distance and cost                          │
├──────────────────────────────────────────────────────────────────────┤
│ 1. INPUT         image · crop & stage · soil · weather · yield ·     │
│                  prices · buyers · transport                         │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.1 Request flow (decision)

```
Browser
  │  POST /api/v1/decisions  (farm_id, crop_id, risk_preference, quantity?)
  ▼
FastAPI route (decisions.py)
  │  1. load farm, crop, health, yield, price, buyers, transport
  │  2. auto-compute any missing prediction
  ▼
DecisionInput (typed dataclasses — no ORM objects)
  ▼
decide(inputs, policy)
  │  ├─ evaluate_buyers()        → BuyerEvaluation[]  (Decimal)
  │  ├─ _market_scenario()       → mandi net realisation
  │  ├─ _wait_scenario()         → uplift after holding + deterioration
  │  ├─ fusion.risk()            → 8 components → composite
  │  ├─ fusion.confidence()      → completeness × data quality
  │  └─ ordered rules            → action + primary reason
  ▼
DecisionOutcome → persisted (decision_results + decision_factors)
  ▼
JSON response (money as strings/Decimal, factors, assumptions, missing_inputs)
```

---

## 4. Module detail

### 4.1 Crop health — classification, not segmentation

| Property | Value |
|---|---|
| Task | 38-class image classification (disease / healthy) |
| Dataset | PlantVillage subset, Hugging Face |
| Images | 1,900 (50 per class) |
| Split | 1,368 train / 266 validation / 266 test, stratified |
| Architecture | EfficientNet-B0, ImageNet-pretrained |
| Input | 192 × 192 px, standard normalisation |
| Training | 6 epochs, 788 s, RTX 5060, seed 42 |
| Test accuracy | **0.9361** |
| Test macro-F1 | **0.9361** |
| Test macro-precision | **0.9515** |
| Test loss | **0.252** |
| Explainability | Grad-CAM from the last convolutional block |
| Serving | Real mode; live response 98.0 % confidence, 122 ms |

**Per-class weakness:** with only 7 test images per class, per-class F1 is coarse. The weakest classes are reported on slide 8 rather than hidden.

**Important scope clarification.** No CropAndWeed dataset and no `unet_res34_2class_best.pth` exist in this repository. The deployed model is a classifier. Grad-CAM is an explanation overlay, not a segmentation mask.

### 4.2 Yield prediction

| Property | Value |
|---|---|
| Task | Regression — quintals per hectare |
| Model | ExtraTrees (selected from ExtraTrees, RandomForest, HistGradientBoosting, GradientBoosting, mean baseline) |
| Training rows | 80,000 |
| Validation rows | 9,867 |
| Test rows | 305 |
| Split | train ≤ 2012 · validation 2013–14 · test 2015 (held-out future year) |
| Features | crop, season, state, area, log-area, expanding crop×state / crop / state historical means |
| MAE | **14.7151 q/ha** |
| RMSE | **36.5968 q/ha** |
| R² | **0.9533** |
| MAPE | **57.52 %** |
| Interval | split conformal, nominal 80 % |
| Empirical coverage | **0.8492** |
| Half-width | **17.4339 q/ha** |

**Why MAPE is high:** yield is right-skewed and small plots dominate percentage error. Absolute error (MAE) and interval coverage are the meaningful metrics; this is stated on the slide.

**Leakage control:** all historical aggregates are *expanding* means computed only from prior years, and the split is chronological by year. No future information enters training.

### 4.3 Market forecasting

| Property | Value |
|---|---|
| Data | `market_prices.csv`, 2,229 real rows |
| Coverage | 14 crops, 35 markets, 2026-07-02 → 2026-09-24 |
| Candidate models | LinearTrendWeekly, GradientBoosting, RandomForest, MovingAverage, SeasonalNaive |
| Validation | chronological held-out tail |
| Selected (onion) | **LinearTrendWeekly** — MAE **410.34**, RMSE **447.14** INR/quintal |
| 14-day forecast | **₹6,441/q**, interval **₹5,884–₹6,998** |
| Interval method | `empirical_absolute_residual_q80_widened_by_sqrt_step` |
| Guard | fewer than 21 observations → **HTTP 422** (Sugarcane: 7 observations) |
| Freshness | 41 days at capture; surfaced as a risk component |

Forecasts are fitted at request time on the chronological series and labelled **experimental** in both API and UI.

### 4.4 Buyer intelligence

- CRUD for buyers and offers; eligibility, capacity, offer age and price deviation.
- Offer risk combines age and deviation from the market reference.
- Ranking uses **risk-adjusted net realisation**: `net − λ × offer_risk × gross`, with λ = 0.5.
- Buyer capacity is respected in the assumptions: in decision #4, Nashik can absorb 80 q and Sahyadri 120 q of the 392 q lot, so the comparison is per-quintal and the remainder needs another buyer.

### 4.5 Transportation

```
distance_km  = OSRM road distance   (fallback: haversine × road factor)
trips        = ceil(quantity / vehicle_capacity)
cost         = trips × (distance_km × rate_per_km) + fixed_charges
```

Vehicle classes: tempo, mini truck, truck, large truck, tractor trolley. The geodesic fallback is covered by tests; the live OSRM path is implemented but not covered by an automated contract test.

### 4.6 Decision engine

**Money arithmetic**

```
gross          = quantity × offered_price
commission     = gross × commission_pct            (1.0 %)
other_costs    = quantity × other_cost_per_quintal (₹5/q)
net            = gross − transport − commission − other_costs
net_per_q      = net / quantity
```

All monetary values use Python `Decimal`; floats are only used at the API boundary.

**Wait scenario**

```
adjusted_qty   = quantity × (1 − deterioration_per_day × days)
holding        = quantity × holding_cost_per_q_per_day × days
wait_net       = price_after_wait × adjusted_qty − holding − other_costs − transport
uplift         = (wait_net − immediate_net) / |immediate_net|
recommend_wait = uplift ≥ 4 %  AND  risk within margin  AND  days ≤ 45
```

**Risk model — eight components, weights sum to 1.0**

| Component | Weight | Normalisation |
|---|---|---|
| Yield uncertainty | 0.20 | relative half-width ÷ 0.50 reference |
| Price uncertainty | 0.18 | relative half-width ÷ 0.30 reference |
| Crop health | 0.18 | severity × confidence penalty |
| Market freshness | 0.12 | price age ÷ 30-day reference |
| Buyer offer | 0.10 | age + price deviation |
| Data completeness | 0.10 | 1 − completeness |
| Weather | 0.07 | adverse-weather flag |
| Transport | 0.05 | distance / availability |

Composite score → **low ≤ 0.33 < medium ≤ 0.66 < high**.

**Ordered rules (first match wins)**

| # | Condition | Action |
|---|---|---|
| 1 | Disease severity ≥ 0.65 or confidence < 0.55 | **INSPECT** |
| 2 | Crop not harvest-ready and days-to-harvest > 0 | **WAIT** |
| 3 | Data completeness < 0.60 | **INSPECT** |
| 4 | Yield interval > ±50 % | **INSPECT** |
| 5 | Price age > 90 days | **INSPECT** |
| 6 | Composite risk > risk-preference cap (low 0.45 / medium 0.72 / high 0.85) | **INSPECT** |
| 7 | Wait uplift ≥ 4 % after costs, within margin, ≤ 45 days | **WAIT** |
| 8 | Net per quintal ≥ configured floor (0) | **SELL** |
| 9 | Otherwise | **INSPECT** |

**Worked example — decision #4 (4 Nov 2026)**

| Field | Value |
|---|---|
| Farm / crop | Kisan Green Farm / Onion, 3.5 ha |
| Expected yield | 392.028 q (80 % interval 331–453 q) |
| Price basis | ₹6,441.08/q (₹5,884–₹6,998) |
| Gross revenue | ₹25,25,083.71 |
| Other selling costs | ₹27,210.98 |
| Transport | ₹0 (not available; recorded as an assumption) |
| Net realisation | **₹24,97,872.73** |
| Net per quintal | **₹6,371.67** |
| Risk | **0.4415** — medium |
| Confidence | **0.932** |
| Completeness | 1.00 |
| Action | **SELL** via Ammapet mandi |
| Policy | 1.0.1 |

Buyer comparison: Nashik Fresh Produce ₹6,150 → net ₹6,071.75; Sahyadri FPC ₹6,030 → net ₹5,946.94. The mandi wins after costs.

**Risk contributions in this decision:** crop health 71 % of the composite, market freshness 100 % of its reference, yield uncertainty 31 % of its reference.

---

## 5. Data model — 21 tables

| Group | Tables |
|---|---|
| Identity | `users`, `revoked_tokens` |
| Farm domain | `farms`, `crops`, `uploaded_files` |
| Crop health | `crop_health_predictions`, `disease_classes`, `recommendations` |
| Yield | `yield_predictions`, `historical_yield_records` |
| Market | `market_price_records`, `market_forecasts` |
| Buyers | `buyers`, `buyer_offers` |
| Transport | `transportation_estimates` |
| Decisions | `decision_results`, `decision_factors` |
| Platform | `weather_records`, `notifications`, `reports`, `model_versions` |

One Alembic migration: `20261104_0014_709bc5e375e1_initial_schema.py`. In production the container runs `alembic upgrade head` before Uvicorn; in development `Base.metadata.create_all` is used for convenience.

---

## 6. API surface — 70 routes

| Router | Routes | Examples |
|---|---|---|
| `auth` | 6 | register, login, refresh, logout, me |
| `system` | 11 | health, status, options, notifications, reports |
| `farms` | 11 | farms CRUD, crops CRUD |
| `crop_health` | 6 | model info, classes, predict, prediction history |
| `yield_` | 5 | model, predict, history, readiness |
| `market` | 7 | crops, prices, markets, trends, forecasts, import |
| `buyers` | 8 | buyers CRUD, offers list/patch/delete |
| `transport` | 2 | vehicles, estimates |
| `weather` | 2 | geocode search, farm weather |
| `decisions` | 5 | policy, run, list, detail, delete |
| `dashboard` | 4 | overview, crop-health, market, decisions |

Authentication: JWT bearer on every non-public route; per-user scoping in queries; rate limiting; upload type and size validation.

---

## 7. Frontend

- React 18.3 + TypeScript 5.7 + Vite 6.
- TanStack Query 5 for server state; React Hook Form + Zod for validation.
- Tailwind CSS 3.4; Recharts 2.15 for charts; lucide-react icons.
- 11 routes: login, register, dashboard, farms, crop-health, yield, market, buyers, transport, decisions, reports, settings, 404.
- Demo data is labelled in every table and every API response (`is_demo`).

---

## 8. Verification and testing

| Suite | Count | Result |
|---|---|---|
| Backend Pytest | **75** | pass |
| — decision engine unit | 17 | pass |
| — decisions API | 6 | pass |
| — crop health | 7 | pass |
| — market | 11 | pass |
| — auth | 8 | pass |
| — farms / buyers / transport / yield / system | 26 | pass |
| Frontend Vitest | **26** | pass |
| Frontend production build | — | succeeds |
| Docker end-to-end smoke | — | passes |

Test distribution: `test_auth.py` 8, `test_buyers.py` 4, `test_crop_health.py` 7, `test_decision_engine.py` 17, `test_decisions_api.py` 6, `test_farms.py` 5, `test_market.py` 11, `test_system.py` 6, `test_transport.py` 5, `test_yield.py` 6.

---

## 9. Deployment

```
docker-compose.yml
├── db        postgres:16 + volume + healthcheck
├── backend   uvicorn + alembic upgrade head + healthcheck
└── frontend  multi-stage build → nginx, proxies /api to backend
```

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000` (`/docs` for OpenAPI)
- Logging: structured JSON
- Config: environment variables via `.env` (see `.env.example`)

---

## 10. Limitations — stated deliberately

1. **Crop health** uses controlled-condition PlantVillage images; field accuracy will be lower.
2. **Yield** lacks soil, weather, irrigation and variety features; MAPE is 57.5 % on right-skewed small plots.
3. **Market** history covers roughly three months; forecasts are short-horizon and experimental.
4. **Buyer offers** are demo records, labelled as such.
5. **Transport** has a tested geodesic fallback but no automated OSRM contract test.
6. **Decision #4** treats missing mandi transport as zero and records that as an assumption.
7. **No field validation** has been conducted; impact on farmer income is unproven.

These are data and validation gaps, not missing architecture.

---

## 11. Provenance

| Asset | Source |
|---|---|
| Crop production | India district-level crop production 1997–2015; public mirror of `data.world/thatzprem/agriculture-india` |
| Market prices | Agmarknet daily mandi prices, CC BY 4.0 archive `github.com/kunal-rajput-317/mandi-data`, derived from OGD resource `9ef84268-d588-465a-a308-a864a43d0070` |
| Crop images | PlantVillage via Hugging Face |
| Weather | Open-Meteo (live, graceful fallback) |
| Routing | OSRM (implemented) with haversine fallback |

---

## 12. Glossary for the viva

| Term | Meaning |
|---|---|
| **Classification** | One label per image from a fixed set of classes. |
| **Segmentation** | A label per pixel; produces masks. Not used here. |
| **Transfer learning** | Reusing ImageNet weights and fine-tuning on a smaller target dataset. |
| **Grad-CAM** | Gradient-weighted class activation map — a coarse heat map showing which regions influenced a classifier's decision. |
| **Macro-F1** | Unweighted mean of per-class F1; treats rare classes equally. |
| **Conformal prediction** | Distribution-free method that turns residuals on a calibration set into intervals with a coverage guarantee. |
| **Prediction interval** | A range expected to contain the true value at a stated confidence. |
| **Net realisation** | Revenue after transport, commission and other selling costs. |
| **Risk-adjusted ranking** | Ranking by net realisation penalised by offer risk. |
| **Deterministic engine** | Same inputs and policy always produce the same output; no randomness, no LLM. |
