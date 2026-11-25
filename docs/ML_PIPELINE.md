# AgriTwin ML Pipeline

AgriTwin trains and serves three model families. This document records exactly
what data was used, how the splits were built, which metrics were produced and
where the approach is weak. No number in this document is hand-written: every
metric comes from the training scripts and is stored in the artifact
`metadata.json` files.

| Model | Task | Artifact | Serving |
| --- | --- | --- | --- |
| Crop health | 38-class leaf-disease classification + Grad-CAM | `crop_health/model.pt` | `app/ml/crop_health/service.py` |
| Yield | Per-hectare yield regression + 80% interval | `yield_prediction/model.joblib` | `app/ml/yield_prediction/inference.py` |
| Market | Short-horizon price forecasting | none (computed on demand) | `app/ml/market_forecasting/forecast.py` |

---

## 1. Datasets

### 1.1 Crop production (yield model)

| Property | Value |
| --- | --- |
| File | `backend/app/data/crop_production.csv` |
| Source | India district-level crop production, 1997–2015; public mirror of `data.world/thatzprem/agriculture-india` (Kaggle `abhinand05/crop-production-in-india`) |
| Rows | 246,091 |
| Columns | state, district, year, season, crop, area (ha), production (tonnes) |
| Target | `yield_q_per_ha = production_tonnes × 10 / area_ha` |

The unit conversion matters: the source production column is in tonnes and area
in hectares. Quintals per hectare is the standard Indian yield unit, so the
factor of 10 is applied once during cleaning. Rows with non-positive area or
production are dropped.

### 1.2 Agmarknet market prices

| Property | Value |
| --- | --- |
| File | `backend/app/data/market_prices.csv` |
| Source | Agmarknet daily mandi prices, CC BY 4.0 archive `github.com/kunal-rajput-317/mandi-data`, derived from Government of India OGD resource `9ef84268-d588-465a-a308-a864a43d0070` |
| Rows | 2,229 |
| Crops | 14 |
| Coverage | 2026-07-02 → 2026-09-24 |
| Price | `modal_price` in INR per quintal |
| Attribution | Original `source` column preserved |

These are real observations, not synthetic values. The window is short — roughly
three months — which limits forecast horizon and seasonal modelling. This is
stated in the UI and in the system status endpoint.

### 1.3 PlantVillage (crop-health model)

| Property | Value |
| --- | --- |
| Source | `Hemg/new-plant-diseases-dataset` on Hugging Face |
| Classes | 38 (crop + disease/healthy) |
| Subset | 50 images per class = 1,900 images |
| Split | 70 / 15 / 15 stratified by image → 1,368 train / 266 val / 266 test |
| Storage | `ml/crop_health/data/plantvillage_subset/<class>/` (downloaded, not committed) |
| Licence note | Research dataset; cite the original PlantVillage work |

Images are downloaded from the three parquet shards with
`scripts/prepare_datasets.py`. The parquet schema is an `image` struct plus an
integer `label`; the preparation script maps labels to sanitized class folder
names.

---

## 2. Crop-health classifier

> **Historical v1 section (superseded).** The settings and metrics in §2.1–§2.2 describe the
> original lab-only `crop-health-v1.0.0` model. They are preserved for provenance only and must
> **not** be quoted as current performance. The current deployed model is the ConvNeXt-Tiny v3
> checkpoint in §2.6 (0.9812 lab / **0.7161 field** with 4-view TTA); the cross-domain table in
> §2.5 is the historical EfficientNet-B0 comparison that preceded it.

### 2.1 Architecture and training (v1, historical)

| Setting | Value |
| --- | --- |
| Backbone | EfficientNet-B0, ImageNet pre-trained |
| Input | 192 × 192, resize 240 then center crop |
| Normalisation | ImageNet mean `[0.485, 0.456, 0.406]`, std `[0.229, 0.224, 0.225]` |
| Augmentation (train) | RandomResizedCrop(192, scale 0.75–1.0), horizontal flip, colour jitter (0.15/0.15/0.1) |
| Loss | Cross-entropy with inverse-frequency class weights |
| Optimiser | AdamW, lr 3e-4, weight decay 1e-4 |
| Scheduler | Cosine annealing over 6 epochs |
| Batch size | 32 |
| Epochs | 6 (early-stopping patience 2 on validation macro-F1) |
| Seed | 42 |
| Device | CUDA (RTX 5060), 788 s total |

The test split is never used for training or model selection. Checkpoint
selection uses validation macro-F1 only.

### 2.2 Held-out test metrics (v1, historical; 266 images, 7 per class)

| Metric | Value |
| --- | --- |
| Loss | 0.2520 |
| Accuracy | **0.9361** |
| Macro precision | 0.9515 |
| Macro recall | 0.9361 |
| Macro F1 | **0.9361** |
| Weighted F1 | 0.9361 |

Weakest classes on the held-out split:

| Class | F1 |
| --- | --- |
| Tomato target spot | 0.6667 |
| Peach bacterial spot | 0.7273 |
| Tomato spider mites | 0.7273 |
| Tomato bacterial spot | 0.8333 |
| Apple healthy | 0.8750 |
| Corn gray leaf spot | 0.8750 |

With only seven test images per class, a single error moves a class F1 by about
0.07–0.14. Per-class numbers are therefore indicative, not precise. The
aggregate accuracy is the more stable estimate.

### 2.3 Grad-CAM

`GradCAM` registers forward and full-backward hooks on the last convolutional
block (`model.features[-1]` for EfficientNet/MobileNet, `model.layer4[-1]` for
ResNet, `model.features[-1][-1]` for ConvNeXt, `model.features[-1]` for
EfficientNetV2). The CAM is the ReLU of the gradient-weighted activation sum,
min-max normalised to `[0, 1]`.

Visuals are saved at model-input resolution as:

- `<stem>_heatmap.png` — JET colour map
- `<stem>_overlay.png` — 55% original image + 45% heat map

The colour map is implemented in NumPy (`jet_colormap`) rather than OpenCV so
the deployment image does not need an extra ~60 MB dependency. The function
matches OpenCV's `COLORMAP_JET` at the anchor points (0 → dark blue,
0.5 → green, 1 → dark red).

The overlay is served read-only from `/uploads/gradcam/...` and its URL is
returned with the prediction.

### 2.4 Inference and degradation

- The service is a process-wide singleton with a thread lock; the checkpoint is
  loaded once.
- `metadata.json` is authoritative for class order, input size and
  normalisation.
- If `model.pt` is missing or fails to load, the service returns a **clearly
  labelled** colour/texture heuristic with `model_mode="demo"` and
  `is_demo=true`. The UI shows a warning banner. Demo results are never
  presented as a trained-model diagnosis.
- Uploads are validated by MIME type, size (8 MB), pixel dimensions (4096) and
  image decode before inference; identical files are deduplicated by SHA-256.

### 2.5 Field-robust extension (new research work)

The v1 numbers above are **in-domain only** and should not be quoted as evidence
of field performance. `train_field_robust.py` replaces this pipeline for the
paper: it builds a domain-tagged manifest (`pv` / `pd` / `web`) and runs four
cross-domain experiments plus an optional ExG ablation.

| Script / artifact | Purpose |
| --- | --- |
| `ml/crop_health/training/prepare_field_dataset.py` | Builds the domain-tagged manifest from PlantVillage + PlantDoc + optional web images |
| `ml/crop_health/training/dedupe_manifest.py` | Removes byte-identical train/test duplicates while preserving the held-out test sets |
| `ml/crop_health/training/train_field_robust.py` | Cross-domain experiments, per-class metrics, Grad-CAM, drop-in deployment |
| `ml/crop_health/evaluation/benchmark.py` | Parameters, GFLOPs, latency, FPS and GPU memory |
| `backend/app/ml/crop_health/exg.py` | Optional ExG background suppression (shared by training and serving) |
| `docs/REVIT_RELEVANCE_TO_AGRITWIN.md` | Why the ReVit segmentation model is a separate system, and what transfers |

Optional flags: `--amp` (CUDA mixed precision), `--exg-suppression` with
`--exg-strength` (ReVit-derived preprocessing ablation). The ExG flag is stored
in metadata so the FastAPI service applies identical preprocessing at inference;
older artifacts keep byte-identical preprocessing. Results:
`ml/crop_health/evaluation/cross_domain_results_all.json` (full four-experiment
run), `ml/crop_health/evaluation/benchmark_results_v3.json` (current benchmark)
and `benchmark_results.json` (historical cu118 run).

**Measured cross-domain results** (EfficientNet-B0, 192 px, seed 42, AMP, RTX 5060):

| Experiment | Training data | Lab (PV) accuracy | Field (PlantDoc) accuracy | Lab F1 | Field F1 |
| --- | --- | --- | --- | --- | --- |
| `baseline_pv` | PV only | 0.9549 | 0.3220 | 0.9539 | 0.2177 |
| `plantdoc_only` | PD only | 0.3120 | 0.6822 | 0.2396 | 0.6721 |
| **`mixed` (previous deployed baseline)** | PV + PD | **0.9511** | **0.6653** | **0.9507** | **0.6563** |
| `two_stage` | PV → PD | 0.8308 | 0.5551 | 0.8322 | 0.5292 |

The lab-only baseline collapses by **63.3 accuracy points** on real-world PlantDoc
images. Joint training retains essentially all lab accuracy while doubling field
accuracy, so `mixed` won this historical comparison. The expected `two_stage`
winner underperformed on both domains (catastrophic forgetting of the lab
domain), and is reported as an honest negative result. Full metrics, per-class
reports and confusion matrices are in `cross_domain_results_all.json`.

The previous deployed EfficientNet-B0 checkpoint was retrained independently (to
save the winning weights and regenerate Grad-CAM) and measured **0.9511 lab /
0.6780 field** accuracy (F1 0.9507 / 0.6501). The small difference from the
table's `mixed` row is due to non-deterministic CUDA kernel selection; it is
preserved under `deployed_model_rerun` in the v2 backup metadata.

Four further EfficientNet-B0 attempts were measured and rejected: 256 px input
with 20 epochs and PlantDoc-validation checkpoint selection (0.9586 lab / 0.6525
field), 4-view TTA on v2 (0.9662 lab / 0.6864 field — only two net
correct images, no low-confidence gain, 4× latency), ReVit-derived ExG background
suppression (0.9586 lab / 0.6483 field — ExG suppresses the brown/necrotic
pixels that carry lesion evidence), and label smoothing + mixup (0.9549 lab /
0.6610 field, macro-F1 0.5584). None was deployed because
`promote_candidate.py` found no strict field-accuracy improvement. Scripts:
`tta_eval.py`, `promote_candidate.py`, and the `--val-domain`,
`--label-smoothing` and `--mixup-alpha` flags in `train_field_robust.py`.

### 2.6 Deployed v3 — ConvNeXt-Tiny + 4-view TTA

The current artifact is `crop-health-v3.0.0-convnext`. It was trained with the
same `mixed` protocol on `manifest_dedup.json`, which removes 11 train/test
duplicate images from the original manifest (4,472 → 4,460 entries) while keeping
the held-out test sets unchanged. ConvNeXt-Tiny, `convnext_small` and
`efficientnet_v2_s` are now supported consistently by training, serving,
benchmarking and Grad-CAM. Training used 192 px, lr `1e-4`, 12 epochs, seed 42
and AMP on RTX 5060 with a CUDA 12.8 PyTorch build.

| Architecture | Params | Model size | GFLOPs | ms/image (batch 1) | img/s (batch 32) |
| --- | ---: | ---: | ---: | ---: | ---: |
| **ConvNeXt-Tiny (deployed)** | **27,849,350** | **106.24 MB** | **6.5458** | **31.9** | **231.4** |
| MobileNet-V3-Large | 4,250,710 | 16.22 MB | 0.3179 | 33.3 | 1005.0 |
| EfficientNet-B0 (historical v2) | 4,056,226 | 15.47 MB | 0.5655 | 42.3 | 726.4 |
| ResNet-50 | 23,585,894 | 89.97 MB | 6.0057 | 31.5 | 733.9 |

Forward-pass benchmark from `benchmark_results_v3.json`; v3 serving averages four
views, about 1.76 s per CPU prediction in the smoke test.

| Inference | Lab accuracy | Field accuracy | Field macro-F1 |
| --- | ---: | ---: | ---: |
| Single view | 0.9774 | 0.6907 | 0.6833 |
| Unconstrained 4-view TTA (promotion baseline) | 0.9812 | 0.7161 | 0.7093 |
| **4-view TTA + correct crop prior (deployed serving)** | **0.9850** | **0.8093** | **0.8024** |

The single-view result strictly beat the previous deployed 0.6780 field
accuracy, so `promote_candidate.py --apply` promoted it after a dry run. TTA was
then enabled in metadata because it added a further +0.0254 field accuracy,
fixed 9 images and broke 3, and improved low-confidence accuracy from 0.3333 to
0.4167. `CropHealthService.predict()` and `tta_eval.py` now call the same
`tta_probabilities()` helper, and CUDA/CPU evaluations agree. Full details:
[docs/CROP_HEALTH_V3.md](CROP_HEALTH_V3.md). All 98 backend tests pass with this
artifact.

The selected farm crop is also applied as a soft prior (`alpha=0.95`) when it maps
to one of the 14 trained crop groups. On the same held-out PlantDoc split the
unconstrained 0.7161 result becomes 0.8093 with a correct hint and 0.7754 when
20% of hints are wrong; hard masking is not deployed (0.6568 at 20% wrong).
Unsupported crops fall back unchanged. The measurement uses
`ml/crop_health/evaluation/crop_prior_eval.py` and the same `apply_crop_prior()`
helper called by serving, with evidence in
`ml/crop_health/evaluation/tta/crop_prior_convnext_results.json`.

### 2.7 Limitations

1. PlantVillage is captured under controlled conditions. Field photos with
   clutter, occlusion, multiple leaves or poor lighting will be harder.
2. The model classifies the *whole image*; it does not localise multiple
   diseases on one leaf.
3. 38 classes cover 14 crop species; unsupported crops will still be forced
   into one of the 38 labels, so the UI frames the result as a screening aid.
4. The subset uses 50 images per class, not the full dataset, to keep training
   time reasonable.

---

## 3. Yield model

### 3.1 Target and features

Target: `yield_q_per_ha` (quintals per hectare).

| Feature | Description |
| --- | --- |
| `crop` | Categorical crop name |
| `season` | Kharif / Rabi / Summer / Whole Year |
| `state` | Categorical state |
| `area_ha` | Sown area |
| `log_area` | `log1p(area_ha)` |
| `crop_state_hist_avg` | Expanding historical mean yield for crop × state, computed from prior years only |
| `crop_hist_avg` | Expanding historical mean for crop |
| `state_hist_avg` | Expanding historical mean for state |

Categorical features are one-hot encoded inside a scikit-learn
`ColumnTransformer` fitted **only on the training period**. Expanding averages
are built chronologically so a row never sees its own year or the future.

### 3.2 Chronological split

| Split | Years | Rows | Role |
| --- | --- | --- | --- |
| Train | ≤ 2012 | 80,000 (sampled from the full set, seed 42) | Fit candidate models |
| Validation | 2013–2014 | 9,867 | Model comparison + conformal calibration |
| Test | 2015 | 305 | Final held-out evaluation |

The 305 test rows are the 14 supported crops in 2015 after cleaning. The small
test set means the test metrics carry sampling noise; the validation comparison
is the more reliable model-selection signal.

### 3.3 Candidate comparison (validation RMSE)

| Model | MAE | RMSE | R² | MAPE |
| --- | --- | --- | --- | --- |
| **ExtraTrees (selected)** | **18.0492** | **48.2509** | **0.9259** | 41.79% |
| RandomForest | 19.2180 | 49.2146 | 0.9229 | 47.96% |
| HistGradientBoosting | 19.0524 | 50.5802 | 0.9186 | 46.34% |
| GradientBoosting | 20.8495 | 55.4185 | 0.9023 | 47.78% |
| DummyMean (baseline) | 100.3552 | 177.4095 | −0.0014 | 475.60% |

The baseline confirms the features carry real signal: RMSE falls from 177.4 to
48.3 q/ha. ExtraTrees wins on validation RMSE and is refit on train +
validation before the final test evaluation.

### 3.4 Held-out 2015 metrics

| Metric | Value |
| --- | --- |
| MAE | **14.7151 q/ha** |
| RMSE | **36.5968 q/ha** |
| R² | **0.9533** |
| MAPE | 57.52% |
| 80% interval coverage | **0.8492** (nominal 0.80) |
| Mean half-width | 17.4339 q/ha |

**Why MAPE is high.** Yield distributions are strongly right-skewed and include
small-area plots with near-zero yields, so percentage error explodes even when
absolute error is small. MAE, RMSE and interval coverage are the primary
selection metrics; MAPE is reported for completeness and honesty.

**Interval method.** Split conformal calibration: absolute residuals are
computed on the 2013–2014 validation period and the 80th percentile becomes a
constant half-width. Coverage on the held-out year (0.8492) is close to the
nominal 0.80, slightly conservative. The half-width is in q/ha and is scaled by
the crop's area to produce total-quintal bounds.

### 3.5 Serving

`YieldModelService` loads the joblib bundle once (lazy, thread-safe) and returns:

- point estimate in q/ha,
- total quintals after multiplying by `crop.area_hectares`,
- low/high total quintals from the conformal half-width,
- a confidence score derived from input completeness and interval width,
- feature values and model version for auditability.

If the artifact is missing, the service reports `available=false`; the decision
service then uses a **transparent historical average** for the crop × state
(labelled `historical_average`) instead of inventing a prediction.

### 3.6 Limitations

1. No soil, weather, irrigation or fertiliser features — the historical dataset
   has no paired records. This is the single largest accuracy limitation.
2. The model is trained on 1997–2015 district aggregates. It does not know
   current varieties, practices or climate.
3. Predictions are for a crop × season × state × area profile, not a specific
   field.
4. The 2015 test set has only 305 rows, so test metrics are noisy.
5. MAPE is high for the reasons above; the UI shows the interval, not just the
   point estimate.

---

## 4. Market forecasting

### 4.1 Series preparation

- Daily `modal_price` per crop and market.
- Duplicate dates are aggregated (mean); the index is a complete daily range
  with missing days forward-filled only inside the observed window.
- At least **21 valid observations** are required. Below that the API returns
  `422 insufficient_data` rather than fabricating a forecast.
- Sugarcane currently has only 7 observations and therefore cannot be
  forecast — this is verified by a test.

### 4.2 Candidate models

| Model | Description |
| --- | --- |
| SeasonalNaive | Repeat the price from 7 days earlier |
| MovingAverage | Mean of the last 7 observations |
| LinearTrendWeekly | Linear trend + day-of-week dummies |
| RandomForest | Lag features `[1,2,3,7,14,21,28]`, recursive multi-step |
| GradientBoosting | Same lag features, recursive multi-step |

### 4.3 Chronological validation and selection

```
test_days = min(max(7, n // 5), 21, n − 14)
```

The last `test_days` observations are held out; every candidate is fitted on the
earlier history and scored by MAE, RMSE and MAPE. The best MAE wins. The winner
is then refitted on the full history and used to forecast the requested horizon
(1–120 days).

There is no random shuffle and no future leakage: validation always predicts a
later period than it trains on.

### 4.4 Intervals

Residuals from the held-out tail are used to build an empirical 80% interval:

- For steps inside the validation length, the 80th percentile of absolute
  residuals at that step is used.
- Beyond the validation length, the interval is widened by `√(step / n_val)`
  to reflect growing horizon uncertainty.

Bounds are floored at ₹1. The method is stored with every forecast as
`empirical_absolute_residual_q80_widened_by_sqrt_step`.

### 4.5 Market selection

When the caller does not name a market, the service prefers a market in the
farm's state if it has enough observations; otherwise it falls back to the
market with the most observations for that crop. This is why the demo onion
decision uses a Tamil Nadu market when the Maharashtra market has too little
history — and the decision output names the market it used.

### 4.6 Limitations

1. The bundled window is only ~3 months, so weekly seasonality is estimated
   from few cycles and annual seasonality cannot be learned at all.
2. Forecasts are short-horizon. Beyond ~21 days the interval widening dominates.
3. Mandi prices are noisy, sparse and sometimes missing for a market/day; the
   series is regularised, which can smooth genuine jumps.
4. The model does not use arrivals, rainfall, fuel prices or policy events.
5. Forecasts are labelled experimental in the UI and in `system/status`.

---

## 5. Artifact inventory

| Artifact | Size | SHA-256 |
| --- | --- | --- |
| `backend/app/ml/artifacts/crop_health/model.pt` | 16,504,531 bytes | `6426E87F8F5C5F6EFF57444D61286A0B85406D6FE4704A1CF1E35F581D318ED6` (v2 field-robust, `mixed`) |
| `backend/app/ml/artifacts/yield_prediction/model.joblib` | 314,174,501 bytes | `B761196F38D43D42067406B658312E61FE24430C474760A427DC49C7FBA9FC40` |

Metadata files (`metadata.json`) sit beside each artifact and contain version,
classes, features, splits, metrics, comparison tables and limitations. The
`.gitignore` excludes the binary artifacts from version control; they are
delivered in the project folder.

---

## 6. Reproducing the models

### Crop health

```powershell
# 1. Download the three PlantVillage parquet shards (~1.1 GB)
python ml\crop_health\training\download_dataset.py --out C:\temp\pv

# 2. Build the balanced 50-per-class subset
python ml\crop_health\training\prepare_dataset.py `
  --parquet-dir C:\temp\pv `
  --out ml\crop_health\data\plantvillage_subset `
  --per-class 50

# 3. Train the original lab-only model (writes model.pt + metadata.json)
python ml\crop_health\training\train.py `
  --data-dir ml\crop_health\data\plantvillage_subset `
  --epochs 6 --per-class 50 --image-size 192

# --- New: field-robust cross-domain model (paper pipeline) ---

# 4. Build the domain-tagged manifest (PlantDoc required; add --web-dir for your web images)
python ml\crop_health\training\prepare_field_dataset.py `
  --plantdoc-dir ml\crop_health\data\plantdoc

# 5. Train all four experiments and deploy the measured winner (joint training)
python ml\crop_health\training\train_field_robust.py `
  --mode all --epochs 12 --deploy-experiment mixed --amp

# 6. Hardware efficiency numbers for the paper
python ml\crop_health\evaluation\benchmark.py --architecture all
```

### Yield

```powershell
python ml\yield_prediction\training\train.py `
  --csv backend\app\data\crop_production.csv `
  --train-sample 80000 --seed 42
```

### Market

There is no offline training step. The forecast module fits and validates on
demand from `market_price_records`, so a refreshed CSV is picked up immediately
after import.

---

## 7. Evaluation philosophy

- **Chronology over randomness.** Both supervised pipelines validate on future
  periods. A random split would leak future information and inflate metrics.
- **Uncertainty is part of the output.** Yield and price intervals feed the
  risk score, revenue bounds and INSPECT rules. A point estimate alone is not
  considered a usable prediction.
- **Weak numbers are reported.** Yield MAPE is high, the market window is short
  and the crop-health subset is small. Hiding these would make the project less
  credible, not more.
- **No synthetic training data.** All three pipelines use real public
  observations; demo fallbacks are labelled at the API and UI level.
