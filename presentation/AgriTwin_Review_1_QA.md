# AgriTwin — Review 1: Faculty Questions & Answers

**Purpose:** prepare technically correct, defensible answers grounded in the actual implementation.
**Rule:** every answer below is consistent with the code and the captured evidence. Where something is not implemented, the answer says so.

> **Historical snapshot — Review 1 (5 November 2026).** Crop-health figures below refer to v1.
> The deployed model and completed ablations as of 2026-11-24 are documented in
> `docs/FINAL_REPORT.md` §12–13 and `docs/RESUME_TOMORROW.md`.

---

## A. Motivation and problem framing

### 1. Why did you select AgriTwin?

Agriculture is the largest employer in India, yet the decision that determines a farmer's income — when and where to sell — is still made from fragmented information. I did not want to build another disease-detection demo, because disease detection alone does not tell a farmer what to do. AgriTwin was chosen because it forces the integration problem: health, yield, price, buyers and transport must agree before a recommendation is defensible.

### 2. What problem does the project actually solve?

It converts fragmented predictions into one economically grounded action. The farmer gets a **SELL / WAIT / INSPECT** recommendation with net realisation, risk and a written reason — not five separate numbers.

### 3. Isn't this just a dashboard over existing models?

No. The models are necessary but not the contribution. The contribution is **Layer 5**: converting prediction intervals and data quality into a risk score, computing net realisation per buyer, and applying ordered, versioned policy rules. A dashboard would stop at displaying predictions; AgriTwin decides between them.

---

## B. Crop health and ML fundamentals

### 4. What is the difference between crop disease classification and segmentation?

- **Classification** assigns one label to the whole image: *"this leaf has Tomato Early Blight."*
- **Segmentation** assigns a label to every pixel and produces a mask: *"these pixels are lesion, these are healthy tissue."*
- **Object detection** draws boxes around instances.

AgriTwin uses **classification**. Grad-CAM produces a coarse heat map for explanation, not a segmentation mask. I want to be precise about this because the project's historical notes mention a U-Net segmentation experiment — that model is **not** in this repository and is not part of the deployed system.

### 5. Why EfficientNet?

Three reasons. First, compound scaling gives strong accuracy per parameter, which matters on a single GPU. Second, ImageNet-pretrained weights are available, so transfer learning converges quickly on a small dataset. Third, it is small enough to serve inference in about 120 ms on CPU-class hardware, which keeps the API responsive.

### 6. What is transfer learning and why is it needed here?

Transfer learning reuses a network trained on a large dataset (ImageNet) and fine-tunes it on a smaller target dataset. With 1,900 images, training from scratch would overfit badly. Reusing learned edge, texture and colour filters lets us reach 93.6 % in six epochs and 788 seconds.

### 7. What is Grad-CAM?

Gradient-weighted Class Activation Mapping. It takes the gradient of the predicted class score with respect to the last convolutional feature maps, weights the maps by those gradients, and produces a heat map showing which regions most influenced the prediction. It is an **explanation aid** — it is not a diagnosis and it is not pixel-accurate.

### 8. What is a confusion matrix and did you use one?

A table of predicted versus actual classes. The diagonal is correct predictions; off-diagonal cells show which classes get confused. We computed a full 38 × 38 matrix and stored it in `crop_health/metadata.json`. With only 7 test images per class, individual cells are coarse, so we report macro-F1 and the weakest classes rather than claiming per-class precision.

### 9. Why precision, recall and F1 instead of just accuracy?

Accuracy hides class imbalance. **Precision** answers "when we say disease, how often are we right?" **Recall** answers "of the diseased leaves, how many did we catch?" **F1** balances them. We report **macro-F1** so every class counts equally, which is the honest choice for a 38-class problem.

### 10. Which dataset are you using, and what is its size?

PlantVillage via Hugging Face: **38 classes**, and we trained on a balanced subset of **50 images per class = 1,900 images**, split **1,368 / 266 / 266** (train / validation / test), stratified.

### 11. What are the limitations of PlantVillage?

Images are captured under controlled conditions — uniform background, good lighting, single leaf. Field photographs have clutter, occlusion, varying light and multiple leaves. Field accuracy will be lower than 93.6 %. That is why the UI labels results as a **screening aid, not a diagnosis**, and why field-image collection is on the Review 2 plan.

### 12. How do you prevent overfitting?

ImageNet pretraining, a small number of epochs with validation-based checkpointing, augmentation during training, and a held-out test split that is never used for model selection. The validation curve plateaus after epoch 3–4 while training loss keeps falling, which is the expected signature; we selected on validation macro-F1, not on training loss.

---

## C. Yield prediction

### 13. How is crop yield predicted?

It is a **regression** problem. The target is quintals per hectare, derived from production and area. Features are crop, season, state, area, log-area, and expanding historical means for crop×state, crop, and state. The model is **ExtraTrees**, selected against RandomForest, HistGradientBoosting, GradientBoosting and a mean baseline.

### 14. What is the difference between regression and classification?

Classification predicts a discrete label from a fixed set. Regression predicts a continuous quantity. Crop health is classification; yield and price are regression/forecasting.

### 15. How do you prevent data leakage in the yield model?

Three controls. First, the split is **chronological by year**: train ≤ 2012, validation 2013–14, test 2015. Second, all historical aggregates are **expanding means computed only from prior years** — a row for 2013 cannot see 2013 or later. Third, the test year is touched once, after model selection.

### 16. Your R² is 0.953 but MAPE is 57.5 %. Isn't that contradictory?

No, and it is an important point. R² measures explained variance in absolute terms; MAPE divides the error by the true value, so it explodes on small yields. The dataset has many small plots with low yields, which dominate percentage error. **MAE (14.72 q/ha)** and **interval coverage (84.9 %)** are the meaningful metrics for this distribution. I report MAPE rather than hide it.

---

## D. Market forecasting

### 17. How do you forecast market prices?

We fit five models on the chronological price series — LinearTrendWeekly, GradientBoosting, RandomForest, MovingAverage and SeasonalNaive — validate on a held-out tail, and refit the best model on the full history. For onion, **LinearTrendWeekly** won with MAE 410.34 INR/quintal.

### 18. Why is the forecast labelled experimental?

The available Agmarknet window is 2026-07-02 to 2026-09-24 — roughly three months, 59 observations per crop. That is enough for a short-horizon trend, not for seasonality. So the API and UI label forecasts experimental, show the data age (41 days at capture), and the risk model penalises stale prices.

### 19. What happens if there is not enough data?

The API returns **HTTP 422** rather than a fabricated number. The minimum is 21 observations. Sugarcane currently has 7 and is refused — that guard is deliberate and tested.

---

## E. Buyers and transport

### 20. How do you calculate transportation cost?

```
distance = OSRM road distance (fallback: haversine × road factor)
trips    = ceil(quantity / vehicle_capacity)
cost     = trips × distance × rate_per_km + fixed_charges
```

Vehicle classes are tempo, mini truck, truck, large truck and tractor trolley.

### 21. Why is the highest buyer price not necessarily the best choice?

Because the farmer is paid on **net realisation**, not headline price. A distant buyer offering ₹6,150 may net less than a nearby mandi offering ₹6,441 once transport and commission are subtracted. In decision #4, Nashik's ₹6,150 nets ₹6,071.75, while the mandi nets ₹6,371.67.

### 22. What is net realisation?

```
gross       = quantity × offered price
commission  = gross × 1.0 %
other costs = quantity × ₹5/quintal
net         = gross − transport − commission − other costs
net/q       = net ÷ quantity
```

All computed in Python `Decimal` to avoid floating-point drift in money.

### 23. How does buyer eligibility and capacity work?

Offers are checked for eligibility, capacity, age and deviation from the market reference. Offer risk combines age and price deviation, and ranking uses `net − λ × offer_risk × gross` with λ = 0.5. Capacity matters: in decision #4, Nashik can absorb 80 q and Sahyadri 120 q of a 392 q lot, so the comparison is per-quintal and the remainder needs another buyer. That is recorded in the assumptions.

---

## F. Uncertainty, risk and the decision engine

### 24. What is prediction uncertainty?

The range of plausible values around a point prediction. AgriTwin represents it explicitly: yield has an 80 % interval, price has an 80 % interval, and each interval width becomes a risk component.

### 25. What is a prediction interval?

A range expected to contain the true value with a stated probability. AgriTwin's yield interval is an 80 % interval with **empirical coverage 84.9 %** on the held-out year — slightly conservative, which is acceptable.

### 26. What is conformal prediction?

A distribution-free method that uses residuals on a calibration set to build intervals with a coverage guarantee. We calibrate absolute residuals on 2013–14, take the 80th percentile, and widen it by the square root of the forecast step for multi-step price forecasts. It does not assume a normal error distribution.

### 27. How does the decision engine work, step by step?

1. Assemble typed inputs: health, yield, price, buyers, transport, harvest, completeness.
2. Compute net realisation for the mandi and for every eligible buyer.
3. Compute the wait scenario after holding cost and deterioration.
4. Compute eight risk components and the weighted composite.
5. Compute confidence from completeness and data quality.
6. Apply **nine ordered rules**; the first match wins.
7. Persist the outcome with factors, assumptions and missing inputs.

### 28. How do you calculate risk?

Eight weighted components summing to 1.0:

| Component | Weight |
|---|---|
| Yield uncertainty | 0.20 |
| Price uncertainty | 0.18 |
| Crop health | 0.18 |
| Market freshness | 0.12 |
| Buyer offer | 0.10 |
| Data completeness | 0.10 |
| Weather | 0.07 |
| Transport | 0.05 |

Each component is normalised against a documented reference (for example, yield half-width ÷ 50 %). The composite maps to low ≤ 0.33 < medium ≤ 0.66 < high.

### 29. What do SELL, WAIT and INSPECT mean?

- **SELL** — net realisation clears the floor and no material wait advantage exists.
- **WAIT** — the crop is not harvest-ready, or waiting clears a 4 % uplift threshold after holding and deterioration costs.
- **INSPECT** — something must be verified first: severe disease, low completeness, a yield interval wider than ±50 %, stale prices beyond 90 days, or risk above the farmer's preference cap.

### 30. What is the novelty of AgriTwin?

The novelty is not a new CNN. It is the **fusion layer**: prediction intervals and data-quality signals are converted into an auditable risk score, and channels are ranked by net realisation rather than headline price. The policy is externalised in versioned JSON, the rules are ordered and deterministic, and every decision stores its factors and assumptions so it can be explained later.

### 31. How is this different from existing agricultural apps?

Most apps are single-purpose: a disease scanner, a mandi price board, or a weather app. Some give advisory text. AgriTwin is different in three ways: it **joins** health, yield, price, buyers and transport; it **quantifies uncertainty** instead of hiding it; and it produces a **decision with money arithmetic and reasons**, not a generic recommendation.

### 32. Why not use an LLM for the recommendation?

Because a recommendation that moves money must be reproducible and auditable. The engine is pure Python, deterministic, and unit-tested — the same inputs and policy always produce the same output. An LLM could be used to *phrase* the explanation, but not to compute the decision.

---

## G. System design and implementation

### 33. How do the modules communicate?

Through typed service interfaces and dataclasses, not through shared database rows. The API layer assembles a `DecisionInput`, the engine returns a `DecisionOutcome`, and persistence happens afterwards. That is why the engine can be tested with no database, network or clock.

### 34. What is your tech stack, and why?

React 18 + TypeScript + Vite for a fast, typed frontend; FastAPI + Pydantic v2 for typed, self-documenting APIs; SQLAlchemy 2 + Alembic for the schema; PostgreSQL 16 in Docker; PyTorch for the CNN; scikit-learn for tabular models; nginx to serve the SPA and proxy the API.

### 35. How is the database designed?

**21 tables** in five groups: identity (`users`, `revoked_tokens`), farm domain (`farms`, `crops`, `uploaded_files`), predictions (`crop_health_predictions`, `yield_predictions`, `market_forecasts`, `transportation_estimates`), market and buyers (`market_price_records`, `buyers`, `buyer_offers`), and decisions (`decision_results`, `decision_factors`). One Alembic migration creates the initial schema, and the container runs `alembic upgrade head` before Uvicorn.

### 36. How do you handle missing data?

Three ways. The yield and market models handle missing values internally where appropriate. The decision engine computes a **completeness score** from seven expected inputs; below 0.60 it returns INSPECT. And when transport cost is missing, it is excluded and explicitly recorded in `assumptions` — as in decision #4, where the mandi transport is treated as zero and flagged.

---

## H. Evaluation, limitations and next steps

### 37. What are the limitations of the project?

Stated plainly:

1. PlantVillage is controlled-condition imagery; field accuracy is unknown.
2. Yield lacks soil, weather, irrigation and variety features; MAPE is 57.5 %.
3. Market history is ~3 months; forecasts are short-horizon.
4. Buyer offers are demo records.
5. OSRM routing has no automated contract test — only the fallback is tested.
6. Mandi transport is zero in decision #4 and flagged as an assumption.
7. No field validation has been done.

### 38. How will you evaluate the system?

Four levels. **Model level:** accuracy, macro-F1, MAE, R², interval coverage. **Engine level:** unit tests and rule-coverage tests. **System level:** end-to-end smoke tests and API tests. **Impact level (planned):** a farmer pilot measuring decision uptake and realised price versus a baseline.

### 39. How will you deploy it?

Docker Compose today: PostgreSQL, FastAPI behind Uvicorn, nginx serving the built SPA. For production, the plan is HTTPS, a managed database with backups, a CI pipeline, and environment-based secrets.

### 40. What are your next implementation milestones?

1. Longer market history and live Agmarknet ingestion.
2. Real buyer onboarding and capacity-constrained allocation.
3. Field-image dataset with a reported field-accuracy figure.
4. Yield features: soil, weather, irrigation, variety.
5. OSRM contract tests and multi-stop routing.
6. Classifier calibration.
7. Farmer pilot with an evaluation protocol.

### 41. How many tests do you have, and what do they cover?

**75 backend Pytest tests** — 17 for the decision engine, 6 for the decisions API, 11 for market, 8 for auth, 7 for crop health, and the rest for farms, buyers, transport, yield and system. Plus **26 frontend Vitest tests** across API, auth and utilities. All pass, and the frontend production build succeeds.

### 42. If I gave you one more month, what would you do?

Collect field images and report field accuracy. That single change would answer the biggest open question about the crop-health module, and it would make the risk component honest. Everything else — more models, more UI — is secondary to evidence.

---

## Weak points a faculty member may challenge

| # | Likely challenge | Honest, defensible response |
|---|---|---|
| 1 | **"Your notes mention CropAndWeed and a U-Net. Where is it?"** | It is not in this repository. Those were earlier segmentation experiments. The deployed model is a 38-class classifier. I have marked that explicitly on slide 8 rather than let the notes imply a capability I do not have. |
| 2 | **"93.6 % on PlantVillage is easy. What about real fields?"** | Correct — PlantVillage is controlled-condition. I do not claim field accuracy. The UI labels results as a screening aid, and field-image collection is the top Review 2 item. |
| 3 | **"Your MAPE is 57 %. That is a bad model."** | MAPE is the wrong headline metric for a right-skewed target with many small plots. MAE is 14.72 q/ha, R² is 0.953, and the 80 % interval covers 84.9 %. I report MAPE because hiding it would be dishonest, not because it is the primary metric. |
| 4 | **"Three months of price data cannot support a forecast."** | It supports a **short-horizon trend**, which is exactly what the API claims. It is labelled experimental, the horizon is capped, the data age is shown, and stale prices raise risk or force INSPECT beyond 90 days. |
| 5 | **"Your buyer offers are fake."** | They are **demo records**, labelled in every table and every API response with `is_demo`. The decision arithmetic on them is real. Real buyer onboarding is planned. |
| 6 | **"Transport is zero for the mandi. That is a bug."** | It is a **missing input**, not a bug: no transport estimate was available for that channel. The engine excludes it and records the assumption in the response. The correct fix is to require a transport estimate before ranking channels — that is on the plan. |
| 7 | **"Buyer capacity is 80 q but you are selling 392 q."** | Correct, and the engine states it in the assumptions: the comparison is **per quintal**, and the remainder requires another buyer. A capacity-constrained allocation across buyers is future work. |
| 8 | **"OSRM is untested."** | The geodesic fallback is tested; the live OSRM path is implemented but not covered by an automated contract test. I say so on slide 6 rather than claim full verification. |
| 9 | **"What is actually novel here? EfficientNet is off the shelf."** | The models are off the shelf by design — the contribution is the fusion layer: interval-aware risk, net-realisation ranking, ordered versioned policy, and persisted explanations. Novelty is in the decision layer, not the CNN. |
| 10 | **"Why not just use an LLM?"** | Money decisions must be reproducible and auditable. The engine is deterministic and unit-tested; an LLM could phrase the explanation but must not compute the number. |
| 11 | **"Is the system actually integrated, or separate scripts?"** | One FastAPI application with 70 routes, 21 tables, one migration, a single React SPA, and an end-to-end Docker stack. The captured decision #4 was produced by the running stack, not by a notebook. |
| 12 | **"How do you know your recommendation is right?"** | Today I can prove the arithmetic and the rule coverage; I cannot prove income impact. That requires a farmer pilot with a baseline — which is stated as future work, not claimed as a result. |

---

## Three sentences to memorise

1. **"The models are standard; the contribution is the uncertainty-aware fusion layer that turns predictions into an auditable money decision."**
2. **"The deployed crop-health model is a 38-class classifier with Grad-CAM, not a segmentation model — the CropAndWeed U-Net is not in this repository."**
3. **"The prototype proves integration; field validation is the next phase, and I am not claiming impact yet."**
