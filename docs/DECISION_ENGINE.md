# AgriTwin Decision Engine

The decision engine is the core contribution of AgriTwin. It answers a single
practical question for a farmer:

> **Should I sell now, wait, or inspect the crop first?**

It is a deterministic, explainable, pure-Python module. It does not call a
language model, does not query the database and does not make network requests.
All inputs arrive as typed dataclasses, so the whole decision path can be
unit-tested without a server.

| Property | Implementation |
| --- | --- |
| Module | `backend/app/services/decision/` |
| Entry point | `decide(inputs, policy) -> DecisionOutcome` |
| Policy | `backend/app/config/decision_policy.json` (version `1.0.1`) |
| Money arithmetic | `decimal.Decimal`, rounded half-up to paise |
| DB bridge | `backend/app/services/decision_service.py` |
| API | `POST /api/v1/decisions`, `GET /api/v1/decisions/policy` |
| Unit tests | `backend/tests/test_decision_engine.py` (17 tests) |
| API tests | `backend/tests/test_decisions_api.py` (6 tests) |

---

## 1. Inputs

`DecisionInput` (`backend/app/services/decision/models.py`) carries:

| Group | Fields |
| --- | --- |
| Crop | `crop_name`, `quantity_quintals`, `risk_preference` (`low`/`medium`/`high`), `today` |
| Yield | mean/low/high total quintals, confidence, age in days, availability |
| Price | expected price, lower/upper bound, market name, forecast points, data age, model name |
| Health | label, healthy flag, severity, confidence, age, availability |
| Harvest | readiness status, days to harvest, confidence |
| Buyers | active offers with price, quantity bounds, validity window, distance, transport cost, demo flag |
| Context | weather risk, transport availability, free-text notes |

Every optional group has an `available` flag. Absence is treated as a risk and
reported to the user — it is never silently replaced with a fabricated value.

## 2. Outputs

`DecisionOutcome` contains:

- `action` — `SELL`, `WAIT` or `INSPECT`
- `explanation` — a sentence naming the channel, net realisation, risk score and top contributors
- `factors` — every risk component with direction, weight, value and description, plus buyer premium and wait uplift
- `buyer_evaluations` — every offer, eligible or not, with ineligibility reasons and rank
- `scenarios` — immediate, mandi and wait economics
- `revenue_interval` — low/high gross revenue
- `data_freshness` — ages and warnings
- `missing_inputs`, `assumptions`
- `confidence`, `data_completeness`, `risk_score`, `risk_category`

The API persists all of this so a decision can be audited later.

---

## 3. Policy

All thresholds live in `decision_policy.json`. The schema is validated at load
time (`policy.py`), including the requirement that the eight risk weights sum
to **1.0**.

### Finance

| Parameter | Value |
| --- | --- |
| `commission_pct` | 1.0% of gross |
| `other_selling_cost_per_quintal` | ₹5.00 |

### Risk

| Parameter | Value |
| --- | --- |
| `yield_relative_half_width_reference` | 0.50 |
| `price_relative_half_width_reference` | 0.30 |
| `market_freshness_reference_days` | 30 |
| `low_max` | 0.33 |
| `medium_max` | 0.66 |
| `risk_premium_lambda` | 0.5 |
| `risk_preference_max_scores.low` | 0.45 |
| `risk_preference_max_scores.medium` | 0.72 |
| `risk_preference_max_scores.high` | 0.85 |

### Inspect rules

| Parameter | Value |
| --- | --- |
| `min_health_confidence` | 0.55 |
| `max_health_severity` | 0.65 |
| `min_data_completeness` | 0.60 |
| `max_yield_relative_interval` | 0.50 |
| `max_price_age_days` | 90 |

### Wait rules

| Parameter | Value |
| --- | --- |
| `min_days_to_harvest` | 10 |
| `min_expected_wait_uplift_pct` | 4% |
| `holding_cost_per_quintal_per_day` | ₹2.00 |
| `crop_deterioration_per_day` | 0.15% |
| `max_recommended_wait_days` | 45 |
| `risk_margin` | 5% of immediate net |

---

## 4. Buyer evaluation

Every offer is evaluated in this order:

1. **Eligibility** — the offer must be active, for the same crop, already
   started, not expired, priced above zero, and the sale quantity must meet the
   offer's minimum.
2. **Quantity allocation** — if the offer has a maximum, the engine sells
   `min(quantity, max)` and flags a partial sale. Transport cost is allocated
   proportionally and the assumption is disclosed, because a partial load may
   still require a full trip.
3. **Net realisation** — for the allocated quantity `q`:

```
gross       = price_per_quintal × q
commission  = gross × commission_pct
other       = q × other_selling_cost_per_quintal
net         = gross − commission − other − transport_cost
net_per_q   = net / q
```

4. **Offer risk** — mean of available components:

| Component | Value |
| --- | --- |
| Offer age | `min(1, age_days / 14)` |
| Expiry proximity | `clamp(1 − days_to_expiry / 3)` |
| Demo buyer | 0.75 (added only when true) |
| Approximate transport | 0.55 (added only when true) |

5. **Risk-adjusted net** — `net − λ × offer_risk × gross`, with λ = 0.5.
   Eligible offers are ranked by risk-adjusted net **per quintal**.

Eligibility is never silently dropped: rejected offers appear in the output
with their reasons.

---

## 5. Channel selection

The engine computes two immediate channels:

- **Mandi**: `price × quantity − commission − other` (no transport; farm-gate basis).
- **Buyer**: the best eligible offer by risk-adjusted net per quintal, including transport.

The **immediate channel is the one with the higher absolute net realisation**,
not the higher headline price. This prevents a low buyer offer from overriding a
clearly better local market. The chosen channel is reported as `mandi` or
`buyer:<name>`, and `selected_buyer_id` is `null` when the mandi wins even if a
buyer's name is echoed in the explanation.

## 6. Risk model

The composite score is a weighted sum of eight components, each in `[0, 1]`:

| Component | Weight | How the value is computed |
| --- | --- | --- |
| Yield uncertainty | 0.20 | `clamp(relative_half_width / 0.50)`; 0.45 if no interval; 0.55 if unavailable |
| Price uncertainty | 0.18 | `clamp(relative_half_width / 0.30)`; 0.40 if no interval; 0.60 if unavailable |
| Crop health | 0.18 | 0.05 if healthy; `clamp(0.35 + 0.65 × severity)` if diseased; 0.45 if no scan |
| Weather | 0.07 | Weather risk; floored at 0.40 when no live feed was used |
| Buyer offer | 0.10 | Mean of age, expiry, demo and approximate-transport components; 0.55 if no offer |
| Transport | 0.05 | `clamp(0.15 + 0.6 × distance_km/500 + 0.25 if approximate)`; 0.80 if no routing |
| Data completeness | 0.10 | `1 − completeness` |
| Market freshness | 0.12 | `clamp(age_days / 30)`; 0.50 if age unknown |

```
score = Σ (value_i × weight_i), clamped to [0, 1]
category = low if score ≤ 0.33, medium if ≤ 0.66, else high
```

The `risk_preference` cap is separate from the category: a **low** preference
inspects above 0.45, **medium** above 0.72 and **high** above 0.85. This lets a
risk-averse farmer reject a decision that is only "medium" by absolute score.

### Completeness

Weights sum to 1.0:

| Signal | Weight |
| --- | --- |
| Yield | 0.25 |
| Price | 0.20 |
| Health | 0.15 |
| Buyers | 0.15 |
| Harvest readiness | 0.10 |
| Location / coordinates | 0.10 |
| Transport | 0.05 |

### Confidence

```
confidence = 0.50 × completeness
           + 0.20 × yield_confidence
           + 0.15 × health_confidence
           + 0.10 × price_quality
           + 0.05 × harvest_confidence
```

`price_quality = 1 − clamp(half_width / 0.5)`. The result is capped at 0.95:
AgriTwin never claims certainty.

---

## 7. Ordered decision rules

The rules are evaluated top to bottom. The first match wins, which makes the
policy auditable and prevents contradictory recommendations.

| # | Condition | Action |
| --- | --- | --- |
| 1 | Latest scan says diseased **and** (severity ≥ 0.65 **or** confidence < 0.55) | **INSPECT** |
| 2 | Crop not harvest-ready and days-to-harvest > 0 | **WAIT** |
| 3 | Data completeness < 0.60 | **INSPECT** |
| 4 | Yield relative interval > 0.50 | **INSPECT** |
| 5 | Market price age > 90 days | **INSPECT** |
| 6 | Risk score > preference cap | **INSPECT** |
| 7 | Wait scenario is recommended | **WAIT** |
| 8 | Immediate net per quintal ≥ 0 | **SELL** |
| 9 | Otherwise | **INSPECT** |

Rule 1 uses the *combination* of severity and confidence: a severe but
uncertain detection still triggers inspection, and a confident but mild one does
not. Rule 2 precedes the data-quality rules because an unripe crop cannot be
sold regardless of data quality.

---

## 8. Wait economics

The wait scenario is only computed when a future forecast point or a harvest
delay exists. Wait days are `min(days_to_harvest or nearest forecast point,
45)`.

```
adjusted_quantity = quantity × (1 − deterioration_per_day × wait_days)
gross             = wait_price × adjusted_quantity
commission        = gross × commission_pct
other             = adjusted_quantity × other_cost_per_quintal
holding           = quantity × holding_cost_per_quintal_per_day × wait_days
net_wait          = gross − commission − other − transport − holding
uplift            = (net_wait − net_immediate) / net_immediate
```

**Price basis consistency.** When the immediate channel is a buyer offer, the
forecast's *relative* move is applied to that offer price:

```
wait_price = offer_price × (forecast_point_price / forecast_expected_price)
```

This avoids comparing a farm-gate offer with a mandi price, which was a real
bug fixed during development.

Waiting is recommended when:

- the crop is not ready (waiting is mandatory), **or**
- `uplift ≥ 4%` **and** `net_wait > net_immediate + 5% × |net_immediate|`
  (the second condition is the risk margin).

The wait scenario is computed but **not** used to change the SELL channel's
price bounds; those are rebased from the selected channel as described below.

---

## 9. Revenue interval

```
low  = yield_low_quintals  × price_low
high = yield_high_quintals × price_high
```

Price bounds are rebased to the selected channel:

```
price_low_channel  = immediate_price × forecast_lower / forecast_expected
price_high_channel = immediate_price × forecast_upper / forecast_expected
```

The method is labelled in the output as *"yield 80% interval × price interval
(independence assumption)"*. It is deliberately conservative: multiplying
bounds assumes independence and can overstate the extreme tails. It is a
planning range, not a confidence interval.

---

## 10. Worked example (verified)

From the Docker end-to-end smoke run (`scripts/smoke_docker.py`, 2026-11-04),
Onion on the demo Maharashtra farm with the bundled Agmarknet data:

| Output | Value |
| --- | --- |
| Action | `SELL` |
| Channel | `mandi` |
| Net realisation | ₹6,371.67 per quintal |
| Risk score | 0.44 |
| Risk category | medium |
| Forecast model | `LinearTrendWeekly` |
| Market | `Ammapet(Uzhavar Sandhai )` |

The engine chose the mandi because its net realisation exceeded the best
eligible demo buyer offer after commission, other costs and transport. The
decision's factors list shows which components contributed most to the risk
score; the output is stored and downloadable in a report.

These numbers are data-dependent and will change when the market feed is
refreshed. They are included as evidence that the pipeline produces a coherent,
explainable result, not as a claim about current onion prices.

---

## 11. Determinism and money handling

- Money is converted to `Decimal` before multiplication and rounded
  `ROUND_HALF_UP` to `Decimal("0.01")`.
- No floating-point accumulation is used for the final rupee figures.
- The engine has no randomness, clocks, I/O or global state; the same
  `DecisionInput` always produces the same `DecisionOutcome`. This is asserted
  by `test_engine_is_deterministic`.
- Risk-adjusted ranking and channel comparison use absolute rupees, so a large
  partial sale cannot outrank a smaller, better-priced one per quintal.

---

## 12. Degradation behaviour

| Missing input | Engine behaviour |
| --- | --- |
| No yield prediction | Moderate yield-risk penalty; decision service falls back to a state/crop historical average and says so |
| No price forecast | Price risk high; buyer offers become the price basis; revenue interval omitted |
| No health scan | Moderate health-risk penalty; assumption recorded |
| No buyer offers | Mandi channel only; buyer risk penalty; assumption recorded |
| No routing | Transport risk high; transport treated as zero; assumption recorded |
| No weather | Weather risk floored at 0.40 and flagged |
| Stale prices | Freshness risk rises; INSPECT above 90 days |

Every degradation appears in `missing_inputs` or `assumptions` in the API
response and in the UI, so the farmer can see what the recommendation is based
on.

---

## 13. Changing the policy

1. Edit `backend/app/config/decision_policy.json`.
2. Keep the eight risk weights summing to 1.0 (validated on load).
3. Run `python -m pytest tests/test_decision_engine.py tests/test_decisions_api.py`.
4. Update the tables in this document and the policy version string.

Because thresholds are data, not code, a domain expert can tune the system
without touching Python.
