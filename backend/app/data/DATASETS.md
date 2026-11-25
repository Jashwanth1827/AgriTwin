# Bundled datasets

These files are curated slices of public datasets. They are real observations,
not synthetic values.

## crop_production.csv

- Source: India district-level crop production (1997-2015), public mirror of
  `data.world/thatzprem/agriculture-india` (Kaggle `abhinand05/crop-production-in-india`).
- Columns: state, district, year, season, crop, area (ha), production (tonnes).
- Used for: yield-model training and historical yield records.

## historical_yield_sample.csv

- A 3,000-row sample of the above for 2010-2015 and the 14 supported crops.
- Used for: regional yield comparisons in the UI and seed records.

## market_prices.csv

- Source: Agmarknet daily mandi prices, CC BY 4.0 archive maintained at
  `github.com/kunal-rajput-317/mandi-data`, derived from the Government of India
  Open Government Data feed (resource `9ef84268-d588-465a-a308-a864a43d0070`).
- Scope: three markets per supported crop, daily observations from 2026-07 onward.
- Prices are INR per quintal. Original source attribution is preserved in the
  `source` column.
- Limitation: the archive window is short (about four months); forecasts are
  short-horizon and labelled experimental.

## Live mandi rates (on-demand, not bundled)

- Primary: Agmarknet daily prices published by the Government of India through
  the data.gov.in API, resource `9ef84268-d588-465a-a308-a864a43d0070`
  (`https://api.data.gov.in/resource/...`). Fields used: `state`, `district`,
  `market`, `commodity`, `variety`, `grade`, `arrival_date`, `min_price`,
  `max_price`, `modal_price`. Licence: Government of India Open Government Data.
  A free API key is required; `DATA_GOV_API_KEY` is read from the environment.
- Companion: the variety-wise daily market-price resource
  `35985678-0d79-46b4-9ed6-6f13308a1d24`, also published by DA&FW / DMI under
  Government of India Open Government Data. It is queried with
  `sort[Arrival_Date]=desc`, and its uppercase fields are mapped to the same
  row shape. Rows are deduplicated against the primary feed; duplicates prefer
  the primary feed, while unique variety rows are reserved up to half of the
  requested limit. `LIVE_MARKET_USE_VARIETY_SOURCE=false` disables it.
- Fallback: `https://mandi-api.onrender.com/v1/prices`, a keyless mirror of the
  same Agmarknet/data.gov.in records, **CC BY-NC-SA 4.0**, limited to
  Maharashtra, Uttar Pradesh, Punjab, Madhya Pradesh and Karnataka. It resyncs
  daily at 8:30 PM IST and was observed ~40 days behind the official feed during
  verification, so it is labelled with its own source and observation date.
- `GET /api/v1/market/live-rates` reports the provider, both contributing
  resources in `sources`, source URLs, licence, observation date and freshness
  on every response. `is_demo` is always `false`.
  Results are cached for `EXTERNAL_CACHE_TTL_SECONDS` and can be refreshed with
  `?refresh=true`. The data.gov.in gateway rejects library default user agents,
  so the client sends a normal browser user agent. Verified on 2026-11-25 for all
  14 crops and the five South India filter states: official provider, 0-day
  freshness, and rows from both resources.

## PlantVillage subset (not committed)

- Source: `Hemg/new-plant-diseases-dataset` on Hugging Face (PlantVillage,
  CC BY-SA / public research dataset).
- The training script downloads a balanced subset; model weights are kept under
  `backend/app/ml/artifacts/` and excluded from git by default.

## PlantDoc (not committed)

- Source: `github.com/pratikkayal/PlantDoc-Dataset`, paper
  `https://arxiv.org/abs/1911.10317`, licence **CC BY 4.0**.
- 2,578 images across `train/` and `test/`; 28 official class folders mapped to
  the same 38-label PlantVillage space used by the deployed model.
- Used only for cross-domain training/evaluation. It supplies the in-the-wild
  domain that exposes the lab-to-field accuracy gap; the original test split is
  kept as an external test domain.
- Optional `ml/crop_health/data/web_images/` holds self-collected field/Google
  images in the same 38 class folders and is always test-only.
- Deterministic splits and provenance are recorded in
  `ml/crop_health/data/field_robust/manifest.json` (see
  `ml/crop_health/training/prepare_field_dataset.py`).
