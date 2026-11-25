# data.gov.in Agriculture API shortlist for AgriTwin

**Reviewed:** 2026-11-25  
**Scope:** Research shortlist plus the verified dual-source live-rate integration. Model weights, held-out tests and crop-health behaviour were not changed.

## 1. Confirming the 146-API figure

The user-supplied count is correct for the **APIs** page filtered to Agriculture:

- Browser evidence: `https://www.data.gov.in/apis?sectors=Agriculture$` displayed **“1 - 8 of 146 API(s)”**.
- Machine-readable evidence:

  ```text
  GET https://api.data.gov.in/lists?format=json
      &notfilters[source]=visualize.data.gov.in
      &filters[active]=1
      &limit=200
      &offset=0
      &sort[created]=desc
      &filters[sector][]=Agriculture
  ```

  Response on 2026-11-25: `status="ok"`, `total=146`, `count=146`, `records=146`.

This count is specific to the API-enabled, active resources exposed by the **APIs** list. Other data.gov.in search endpoints return larger counts because they index resource metadata more broadly; those are a different universe and were not used for this shortlist.

## 2. Screening method

Each candidate was checked with a direct resource call:

```text
GET https://api.data.gov.in/resource/{uuid}?api-key=<YOUR_KEY>&format=json&limit=5
```

A browser-like `User-Agent` was used because the data.gov.in gateway rejects library-default agents such as `python-httpx`. All shortlisted UUIDs below returned HTTP 200 and `status="ok"` during the review.

Screening rules:

1. Direct relevance to AgriTwin’s current modules: market rates, crop context, advisory evidence, or farmer reach.
2. Structured fields and a stable resource UUID.
3. Explicit treatment of freshness: `updated_date` is metadata change time, **not** the observation date. Sample records were inspected separately.
4. Provenance recorded from organisation metadata.
5. Licence basis: the portal states published content is owned by the respective Ministries/Departments/Organisations and licensed under **Government Open Data License-India**. Confirm the resource page before any external redistribution.
6. Nothing here is proposed as crop-health training data. The deployed model and its held-out tests stay unchanged.

## 3. Recommended shortlist

### Tier A — highest value for current AgriTwin scope

| Priority | Resource / UUID | Organisation | Direct verification | Suggested use | Caveat |
|---|---|---|---|---|---|
| A1 — already deployed | **Current Daily Price of Various Commodities from Various Markets (Mandi)** `9ef84268-d588-465a-a308-a864a43d0070` | Ministry of Agriculture and Farmers Welfare / DA&FW | `total=16171`; sample `arrival_date=25/11/2026`; fields include `state`, `district`, `market`, `commodity`, `variety`, `grade`, `min_price`, `max_price`, `modal_price` | Keep as the official primary source for `/api/v1/market/live-rates` | Requires a valid API key and browser-like headers; already implemented |
| A2 | **Variety-wise Daily Market Prices Data of Commodity** `35985678-0d79-46b4-9ed6-6f13308a1d24` | DA&FW / Directorate of Marketing and Inspection | `total=83306132`; default sample `Arrival_Date=11/11/2009`, but `sort[Arrival_Date]=desc` returns `25/11/2026`; same core price fields plus `Commodity_Code` | Variety-level live companion to A1; improve variety aliases and backfill analysis | Must sort by `Arrival_Date` descending or filter a date range; field names use `Arrival_Date`, `Modal_Price`, `State`, etc. `updated_date` is metadata, not the observation date |
| A3 | **Kisan Call Centre (KCC) — Transcripts of farmers queries & answers** `cef25fe2-9231-4128-8aec-2c948fedd43f` | DA&FW | `total=48355671`; sample `CreatedOn=2023-02-03`; fields include `Crop`, `QueryText`, `KccAns`, `StateName`, `DistrictName`, `QueryType` | Real advisory-evidence corpus for retrieval or topic exploration | Multilingual and scheme-related; not crop-health training data. Contains location granularity, so review before exposing raw records |
| A4 | **District-wise, season-wise crop production statistics from 1997** `35be999b-0208-4354-b557-f6ca9a5355de` | DA&FW | `total=246091`; sample `crop_year=2000`; fields `State_Name`, `District_Name`, `Crop_Year`, `Season`, `Crop`, `Area`, `Production` | Regional crop/season context and a sanity check for serving-time crop priors | Historical baseline, not a current-season forecast |

### Tier B — useful only with clear scope labels

| Resource / UUID | Direct verification | Possible use | Limitation |
|---|---|---|---|
| **Village and Gender-wise Beneficiaries under PM-KISAN** `388208c6-d82a-4190-90df-91aa2c326fec` | `total=13589350`; sample quadrimester `2025-12-01` → `2026-03-31` | Farmer-reach/demographic context | Aggregate scheme data, not agronomy; handle location granularity carefully |
| **Product wise and Month wise production of chemical Fertilizers** `373358c8-63fd-4612-8f2b-9ce483422312` | `total=64`; sample `2014-2015`, `UREA`, `DAP` | Input-supply context | Historical and small |
| **One District One Product List with Description** `6ca5aa0a-b475-43c0-8bb7-b5e53a6b95d5` | `total=1241`; sample includes state, district, product, GI status, description | Local product/GI context | Contains external photo links; do not ingest photos as model data |
| **List of certified varieties of horticultural crops** `46f587a9-7476-443e-915f-fc756a6b4e2c` | `total=13`; fields only cover 2002–2009 | Variety metadata lookup | Tiny and old |
| **Treatable area under PMKSY WDC 2.0 project** `b97cc264-b94f-4f2a-b4a8-1a95bdbdd0d6` | `total=63`; sample Bagalkot, Karnataka | Watershed/water-conservation context | Karnataka-specific |
| **District-wise market arrivals of Paddy crop from 1978 to 2021** `93fc715e-22cc-4db9-ba35-6aaaea3e6246` | `total=23`; sample Gurdaspur/Pathankot, Punjab | Historical supply/arrival context | Punjab-specific, paddy-only, ends 2021 |
| **Year-wise Damage Caused Due To Floods, Cyclonic Storm, Landslides etc** `f5fc3381-dfca-4b22-bf10-dd8f03996b05` | `total=12`; sample `2001-02`; field `Cropped areas affected (in lakh ha)` | Disaster-risk context | National aggregate, old |
| **Third Advance Estimates of Area, Production and Yield of Oil seeds crops of Gujarat State for 2023-24** `0e2f71a5-6f48-4c07-9593-1c2cc55655b1` | `total=7`; sample Groundnut, Castor seed | State/oilseed context only | Tiny, Gujarat-specific |

## 4. What was deliberately not shortlisted

The 146 APIs are not all equally useful for AgriTwin. By title screening:

- 83 were last updated in 2018; many are one-off state tables.
- 37 relate to animal husbandry/dairy (milk, egg, wool, meat, veterinary infrastructure), outside the current crop-health and mandi-price scope.
- 11 relate to insurance/enrolment/claim schemes.
- 7 relate to land holdings or land-use classification.
- Several fertilizer feeds are month/port-specific snapshots from 2013–2015.

These are not rejected because the data is invalid; they are simply not warranted by the current project scope. Adding them would create provenance and maintenance burden without improving the deployed model or live market module.

## 5. Recommendation

A1 remains the authoritative primary live feed. A2 is directly verified as current when sorted by `Arrival_Date` descending and is now implemented as a variety-level companion. A3 and A4 remain future candidates, each requiring its own licence/provenance record and freshness label. No shortlist data should retrain the crop-health model without a separate, approved experiment and a strict accuracy comparison against the deployed `0.7161` 4-view field baseline.

## 6. Implemented dual-source live rates

`GET /api/v1/market/live-rates` now merges both official resources:

1. A1 `9ef84268-d588-465a-a308-a864a43d0070` — current daily mandi prices, primary.
2. A2 `35985678-0d79-46b4-9ed6-6f13308a1d24` — variety-wise daily prices, sorted with `sort[Arrival_Date]=desc`.

Rules:

- A2 failures are logged but never replace a working A1 response; the keyless mirror remains the fallback for a failed primary feed.
- Rows are deduplicated by date, state, district, market, commodity, variety and grade; duplicates prefer A1. Unique A2 rows are reserved up to half of the requested limit so the variety feed remains visible even when A1 already fills the page.
- Every row carries `source`, `source_resource_id` and, where A2 supplied it, `commodity_code`.
- The response lists both resources in `sources` with contributed row counts and observation dates.
- `LIVE_MARKET_USE_VARIETY_SOURCE=false` disables A2 without changing A1 behaviour.
- No crop-health artifacts, manifest entries or held-out tests were changed.

Verification on 2026-11-25: all 14 supported crops returned `provider=data_gov`,
`is_demo=false`, `latest_observation_date=2026-11-25` and 0-day freshness, with
A1 and A2 both contributing rows at limit 5. The South India quick filter was
also checked for Andhra Pradesh, Karnataka, Kerala, Tamil Nadu and Telangana;
all five returned the same official, zero-day-fresh dual-source result.
