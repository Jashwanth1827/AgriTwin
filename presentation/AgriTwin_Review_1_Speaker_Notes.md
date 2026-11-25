# AgriTwin — Review 1 Speaker Notes

**Duration target:** 9–11 minutes for 13 slides (≈ 30–60 s each)
**Speaker:** Jashwanth Aravapalli
**Rule:** do not read the slide. Say the sentence the slide cannot say.

> **Historical snapshot — Review 1.** If asked about current crop-health accuracy, use the v2
> figures in `docs/FINAL_REPORT.md` §12–13, not the v1 numbers in this deck.

---

## Before you start (30 seconds, not a slide)

- Deck open in Presenter View; notes visible on your laptop only.
- Demo tab already logged in at `http://localhost:5173` in case faculty ask for a live check.
- Water nearby. Breathe once before slide 1.
- If asked something you do not know: *"That is not implemented yet — it is on the Review 2 plan."* That answer is always better than inventing one.

---

## Slide 1 — Title
**Time:** 40 s

> Good morning. I am Jashwanth Aravapalli, and my major project is **AgriTwin — an AI-driven crop health and market intelligence system**.
>
> The one-line idea is this: farmers already receive many predictions — a disease label, a yield number, a price forecast — but they still have to decide what to do. AgriTwin connects crop health, yield, market prices, buyers and transport into one explainable recommendation: **sell, wait, or inspect**.
>
> I want to be clear from the start: this is a working full-stack prototype, not a slide concept. Today I will show the architecture, the trained models, the decision engine and the results that are actually running. I will also separate clearly what is complete from what is planned.

**Transition:** *"Let me start with why this problem matters."*

---

## Slide 2 — Introduction
**Time:** 50 s

> Indian farmers make one high-stakes decision every season: when and where to sell. The information needed for that decision is scattered — a leaf photo, a yield expectation, a mandi price, a buyer's phone call, a transport quote.
>
> Each of those signals can be correct on its own and still lead to a bad economic decision. The highest quoted buyer price is often **not** the best choice once transport and commission are subtracted.
>
> AgriTwin's vision is to convert those scattered data points into one explainable, economically informed recommendation. The flow on the right is the whole project in five boxes: farmer, data collection, AI analysis, decision engine, action.
>
> The decision engine is the research contribution — not another prediction screen.

**Transition:** *"So what exactly is the problem, and what are the objectives?"*

---

## Slide 3 — Problem Statement & Objectives
**Time:** 50 s

> The problem is deliberately narrow. It is not that India lacks agricultural data or machine-learning models. It is that the outputs are fragmented and do not answer the farmer's real question: **what should I do now?**
>
> So the objectives follow the decision chain. Detect disease from an image, explain it, estimate yield with a range, forecast price, compare buyers, estimate transport, compute net realisation, quantify risk, and finally recommend sell, wait or inspect with reasons.
>
> The ninth objective is the one that ties everything together. That is why the decision engine is treated as the core contribution rather than an add-on.
>
> Notice that objectives one to eight are inputs to objective nine. That ordering is intentional.

**Transition:** *"Here is the architecture that implements those objectives."*

---

## Slide 4 — Proposed Architecture
**Time:** 60 s

> This is the seven-layer architecture. Reading from the bottom: raw inputs, then processing, then the three prediction families, then the decision engine, then outputs and impact.
>
> Layer 3 is crop health: an EfficientNet-B0 classifier over 38 PlantVillage classes, with Grad-CAM. Layer 4 covers yield and market intelligence, including the harvest window, buyer analysis and transport cost.
>
> Layer 5, highlighted in amber, is the contribution. It does not average predictions. It converts each prediction into an uncertainty and risk term, computes net realisation for every eligible buyer and for the mandi, applies ordered policy rules, and produces an explanation.
>
> Layer 6 is what the farmer actually sees. Layer 7 is the intended impact.
>
> Every layer in this diagram is implemented in the repository. I will show the evidence module by module.

**Transition:** *"The next slide shows the order in which those layers run."*

---

## Slide 5 — Methodology
**Time:** 50 s

> The methodology follows the order in which information becomes a decision.
>
> We collect raw signals, preprocess them, run the three prediction families, compare buyers and transport, fuse uncertainty, and apply decision rules.
>
> One design choice I want to highlight: **the pipeline is chronological wherever time matters**. Yield validation uses a future year, and market forecasts validate on a held-out tail. We never shuffle time-series data, because that leaks the future into training and inflates the metrics.
>
> The serpentine layout shows the sequence: steps one to four across the top, then down and back for five to seven. All seven stages are implemented and exercised by the smoke tests.

**Transition:** *"Let me list the technologies that are actually used."*

---

## Slide 6 — Technologies Used
**Time:** 45 s

> This is a technology inventory, not a wish list. Everything in the six cards is actually imported and used by the code in this repository.
>
> Frontend: React with TypeScript, Vite, Tailwind, TanStack Query and Recharts. Backend: FastAPI, Pydantic, SQLAlchemy and Alembic, with JWT authentication. AI: PyTorch for the CNN, scikit-learn for yield and market models, and a custom Grad-CAM implementation. Data: PostgreSQL in Docker, SQLite for development, and three real public datasets.
>
> The amber box is important for honesty. IoT sensors and live buyer APIs are **planned, not built**. OSRM routing is implemented, but our automated tests only exercise the geodesic fallback, so I do not claim routing is fully verified.

**Transition:** *"Now the modules themselves."*

---

## Slide 7 — Module Description
**Time:** 45 s

> The system is split into seven functional modules, and each one has a clear contract: purpose, inputs, processing and outputs.
>
> Modules one and two handle data. Module three is crop health. Module four is yield and market. Module five is buyer and transport. Module six is the decision engine, highlighted because it consumes every other module's output. Module seven is the dashboard.
>
> The key architectural point is that modules do not reach into each other's internals. The decision engine receives typed dataclasses, not database rows. That is what lets us test the policy without a server, and it is why the engine could be reused behind a different UI or API.
>
> That separation is also why the engine has seventeen focused unit tests.

**Transition:** *"Let me show the first module with real evidence."*

---

## Slide 8 — Crop Health Implementation
**Time:** 60 s

> Module three is complete and running in real mode.
>
> The dataset is PlantVillage from Hugging Face: 38 crop-disease classes, and we trained on a balanced subset of 50 images per class — 1,900 images total. The split is 70/15/15, stratified by image.
>
> The model is EfficientNet-B0 with ImageNet transfer learning, 192-pixel input, six epochs. On the held-out 266-image test split it reached **93.61 percent accuracy and 93.61 percent macro-F1**, with 95.15 percent macro-precision. Training took about 788 seconds on an RTX 5060.
>
> The screenshot is a genuine API response at 98 percent confidence, and the Grad-CAM overlay is generated by the running model.
>
> I also want to address the CropAndWeed question directly. That dataset and the U-Net checkpoint are **not in this repository**. Those were earlier segmentation experiments. The deployed system is a classifier, and I am not claiming segmentation capability.

**Transition:** *"From crop health to yield and market."*

---

## Slide 9 — Yield & Market Intelligence
**Time:** 60 s

> Module four has two halves.
>
> Yield prediction is regression. The target is quintals per hectare. We use crop, season, state, area, and expanding historical averages computed only from prior years. The split is chronological: train up to 2012, validate on 2013–14, test on 2015. ExtraTrees won the validation comparison. On the held-out year it achieved **MAE 14.72 quintals per hectare and R-squared 0.953**, with 84.9 percent empirical coverage for the nominal 80 percent interval.
>
> I will be honest about the weakness: MAPE is 57.5 percent because yields are right-skewed and small plots dominate percentage error. Absolute error and interval coverage are the meaningful metrics here.
>
> Market forecasting fits five models and validates on a held-out tail. For onion, LinearTrendWeekly won with MAE 410 rupees per quintal. The 14-day forecast is **6,441 rupees with a 5,884 to 6,998 interval**. If a crop has fewer than 21 observations, the API returns 422 instead of inventing a forecast — Sugarcane currently falls into that category.

**Transition:** *"Now the most important slide — the decision engine."*

---

## Slide 10 — Decision Engine & Integration
**Time:** 75 s (this is the slide to slow down on)

> This is the slide I would defend most carefully, because it is the contribution.
>
> For every eligible buyer we compute gross revenue, subtract transport, commission and other selling costs, and divide by quantity. That gives **net realisation per quintal**. We also rank by a risk-adjusted net, so a risky offer does not automatically win.
>
> The table is a **real decision from the running system**. The mandi at Ammapet nets 6,371 rupees per quintal. The best buyer offer is 6,150, which nets 6,071 after transport. So the highest headline offer is not the best choice here — and that is exactly the mistake the engine prevents.
>
> On the left is the risk model: eight weighted components summing to one. On the bottom right are the ordered rules — the first matching rule wins, which makes the policy auditable.
>
> The output is **SELL**, at 6,371.67 per quintal, medium risk, 93 percent confidence. Every factor and assumption is stored with the decision, so the recommendation can be explained after the fact.

**Transition:** *"Here is the evidence from the live application."*

---

## Slide 11 — Results / Current Output
**Time:** 55 s

> This is the evidence page. Each screenshot is from the live application, not a mock-up.
>
> Top left is crop health: a real 98 percent prediction with Grad-CAM. Top right is yield: 392 quintals with a 331 to 453 interval, plus the harvest window.
>
> Bottom left is the market forecast: 6,441 rupees with empirical bounds and a model-comparison table. Bottom right is the decision: SELL through the mandi at 6,371 rupees per quintal, risk 0.44.
>
> I have paired every result with its limitation, because a review is not credible if we only show the good numbers. The crop model is trained on controlled images, the yield model lacks soil and weather, the market window is short, and the buyer offers are demo data.
>
> What these results prove is that the full chain runs: image in, models, database, decision, UI and report.

**Transition:** *"So what comes next?"*

---

## Slide 12 — Future Work
**Time:** 45 s

> The left column is what already exists, so future work is clearly separated from current capability.
>
> The next phase has four themes. **Data:** broader disease images, live market feeds and real buyer networks. **Models:** better calibration, richer yield features including soil and weather, and price models with arrivals and rainfall. **Deployment:** route-based logistics and IoT sensors where available. **Evidence:** field trials and a real deployment.
>
> If a faculty member asks what is missing, this is the honest list. The prototype proves the integration; the next phase proves the impact.
>
> We are prioritising field data and validation over adding new model families, because more models on the same data would not answer the questions a reviewer should ask.

**Transition:** *"To conclude."*

---

## Slide 13 — Conclusion
**Time:** 40 s

> To conclude: AgriTwin is not another prediction dashboard. It is a decision-support system that treats uncertainty as a first-class input.
>
> The three contributions are **uncertainty-awareness, explainability and economic grounding**. The engine compares net realisation, not headline prices, and it shows the farmer why.
>
> The prototype is running end-to-end today: trained models, real data, a tested decision engine, a complete UI and a Docker deployment. The next phase is field validation.
>
> **From fields to better decisions.** Thank you — I am happy to take questions.

---

## If you are running short on time

Cut, in this order:

1. Slide 6 — say only: *"All technologies shown are in the repository; the amber box lists what is planned."*
2. Slide 7 — say only: *"Seven modules with typed contracts; the decision engine is module six."*
3. Slide 12 — say only: *"Future work is data breadth and field validation; the list is on the slide."*

**Never cut slide 10.** It is the contribution.

---

## If you are running long

You have room to expand:

- Slide 8: mention the weakest per-class F1 and why (7 test images per class).
- Slide 9: explain conformal prediction in one sentence — *"we calibrate residuals on 2013–14 and use them to build an interval that covers about 80 percent of unseen cases."*
- Slide 10: explain the risk-adjusted ranking formula and why λ = 0.5.

---

## Delivery reminders

| Do | Don't |
|---|---|
| Point at the amber box on slide 8 when you mention CropAndWeed | Let the faculty discover it themselves |
| Say "real decision from the running system" on slide 10 | Call the buyer table "illustrative" — it is real API output |
| Say "demo buyer records" when describing buyers | Imply real buyer partnerships |
| Pause after "SELL, 6,371 rupees per quintal" | Rush through the money numbers |
| Own the limitations before you are asked | Defend a weak metric |

---

## Numbers you must know without looking

| Number | Meaning |
|---|---|
| **93.61 %** | crop-health test accuracy and macro-F1 |
| **1,900 / 38** | PlantVillage subset images / disease classes |
| **14.72** | yield MAE, quintals per hectare |
| **0.953** | yield R² on the 2015 held-out year |
| **84.9 %** | empirical coverage of the nominal 80 % interval |
| **410.34** | onion forecast MAE, INR per quintal |
| **₹6,441** | 14-day onion forecast, interval ₹5,884–₹6,998 |
| **₹6,371.67** | net realisation per quintal in decision #4 |
| **0.4415** | composite risk in decision #4 (medium) |
| **0.932** | confidence in decision #4 |
| **75 / 26** | backend / frontend tests |
| **70 / 21** | API routes / database tables |
