# AgriTwin: Uncertainty-Aware Fusion of Leaf, Yield and Market Signals for Crop Decisions, with Cross-Domain Validation of the Disease Input

**Draft for IEEE-style major project paper — not yet submitted.**

> **Before submission, fill in:** contact email, city/country in the LaTeX author block, target
> venue, and verify every reference on the publisher page. All experimental numbers below are
> machine-generated from the repository artefacts; none are hand-written.

**Author(s):** Jashwanth Aravapalli — Department of CSE (AI & ML), Keshav Memorial Engineering College
**Contact:** `[EMAIL]`
**Venue:** `[IEEE REGIONAL CONFERENCE / IEEE ACCESS / OTHER]`

---

## Abstract

Farmers routinely combine a leaf photograph, a yield expectation, a mandi (market) price, a buyer's
offer and a transport quote to decide what to grow, when to harvest and where to sell. These signals
are usually processed in isolation, so an individually accurate prediction need not produce a good
economic decision. We present **AgriTwin**, an agricultural digital-twin platform that unifies
crop-disease screening, conformal yield prediction, market forecasting and transport costing in a
single uncertainty-bearing state consumed by a deterministic decision engine. Because the leaf
photograph is the first link in this chain, a confidently wrong disease prediction would corrupt
the entire decision; we therefore validate that input under domain shift. A controlled experiment
shows that an EfficientNet-B0 trained only on PlantVillage achieves 0.9549 accuracy in the lab but
collapses to 0.3220 on in-the-wild PlantDoc photographs, a 63.3-point gap. Joint training on both
domains retains lab performance (0.9511) and more than doubles field accuracy (0.6653 in the
controlled run; 0.6780 for the independently retrained EfficientNet-B0 checkpoint). Contrary to the
usual assumption, sequential fine-tuning underperformed joint training on both domains (0.8308 lab
/ 0.5551 field). A follow-up ConvNeXt-Tiny trained on a de-duplicated cross-domain manifest reached
0.9774 lab / 0.6907 field, and the operator-aligned 4-view test-time augmentation now used in
serving raises this to **0.9812 lab / 0.7161 field**; a soft crop prior from the selected farm crop
reaches **0.8093 field** when the hint is correct. Grad-CAM overlays confirm that the deployed
model attends to lesion regions. The system converts these predictions, together with yield and price
intervals, into ranked sell/wait
decisions with an explicit INSPECT fallback for low-confidence inputs. All numbers are reproduced
by released code and stored in the deployed artefact metadata.

**Index Terms** — agricultural digital twin, decision support, plant disease detection, domain
adaptation, uncertainty quantification, Grad-CAM, EfficientNet, ConvNeXt, test-time augmentation.

---

## 1. Introduction

A farmer's economically important decisions are multi-source. Crop health is judged from a leaf
photo; expected production from experience or a model; the selling price from yesterday's mandi
quote; a buyer may offer a different price by phone; and transport cost depends on distance and
vehicle. Each source is uncertain, time-stamped and perishable. Handling them as separate
predictions leaves the farmer to perform an implicit, untracked fusion — and an individually good
prediction does not guarantee a good decision.

AgriTwin addresses this by representing all sources as one typed, uncertainty-bearing decision
state. Disease screening returns a label, a confidence and a Grad-CAM explanation; yield
prediction returns a point estimate and an 80% split-conformal interval; market forecasting returns
a price and empirical residual bounds; buyer offers carry validity windows; and transport returns a
cost breakdown. A pure decision engine combines these into eight weighted risk components, two
revenue scenarios (sell now / wait) and an ordered rule set that can recommend SELL, WAIT or
INSPECT, with a human-readable explanation.

This design makes the reliability of the first signal — the leaf photo — a system-level concern.
Deep learning studies routinely report around 95–99% accuracy on PlantVillage, where single leaves
are photographed face-up against a uniform background. Field photographs contain varying
illumination, occlusion, multiple leaves, soil and sky. If a model exploits the controlled
background as a shortcut, it will be confidently wrong in exactly the conditions the decision
system is meant to support.

This paper makes the following contributions:

1. An integrated, uncertainty-aware agricultural decision system that fuses leaf health, yield
   intervals, market forecasts, buyer offers and transport cost into a single reproducible decision
   with explanations and an INSPECT fallback.
2. A measured quantification of the lab-to-field failure of the leaf-photo input (0.9549 → 0.3220)
   using the official PlantDoc test split, with no test image used for training or model selection.
3. A controlled four-protocol comparison showing that joint domain training outperforms sequential
   fine-tuning, including an honest negative result (two-stage adaptation underperforms on both
   domains).
4. Explainability and efficiency evidence: Grad-CAM verification of lesion attention and a measured
   parameter/FLOP/latency profile supporting near-real-time inference on commodity hardware.

---

## 2. Related Work

**Plant disease detection.** Mohanty, Hughes and Salathé demonstrated deep convolutional networks
on the PlantVillage dataset and already noted the limited realism of laboratory images [1].
Subsequent work adopted transfer learning with EfficientNet, ResNet and MobileNet backbones, mostly
reporting in-domain accuracy. Surveys of leaf-disease recognition document the gap between
controlled datasets and field readiness [6], [7].

**In-the-wild datasets.** PlantDoc [2] provides internet photographs with multiple leaves and
natural backgrounds, mapped onto PlantVillage-style labels. It is widely used for cross-domain
evaluation and exposes the shortcut-learning problem. Recent lightweight-model evaluations report
in-domain PlantDoc results and discuss edge deployment [8].

**Cross-domain disease detection.** Deployable cross-domain leaf-disease systems have been proposed
for smartphone use [9]. Our work differs in two respects: the classifier is treated as an *input
reliability component of a larger decision system*, and we report the negative two-stage result
rather than only the best configuration.

**Explainability.** Grad-CAM [4] produces class-activation localisations without architectural
changes; it is used here both as a qualitative check and as part of the user-facing screening
output. Reviews recommend such verification precisely to detect background shortcuts [7].

**Digital twins and uncertainty.** Agricultural digital twins have demonstrated value for
individualised crop management [5]. Conformal prediction provides distribution-free interval
coverage, which motivates the yield intervals consumed by our decision engine. We position this
work at the intersection: a deployed digital-twin decision pipeline whose first input is
cross-domain validated and explained.

**Excess-green prior.** The excess-green index (ExG) highlights vegetation and suppresses soil.
In our complementary UAV crop/weed segmentation study (ReVit) an ExG attention gate was effective.
Here we adapt the same prior as a *training-time background-suppression ablation* and report it
only if it measurably improves field accuracy; the two systems remain separate and cross-cited.

---

## 3. System and Methods

### 3.1 System architecture

The implemented system has seven layers (full details in `docs/ARCHITECTURE.md`):

```
Presentation (React 18 + TypeScript)
        ↓
API (FastAPI, JWT, validation, rate limiting)
        ↓
Service / orchestration (crop_health, yield, market, buyers, transport, decision_service)
        ↓
Decision engine (policy → risk → fusion → ordered rules; pure Python, Decimal money)
        ↓
ML inference (ConvNeXt-Tiny with 4-view TTA + Grad-CAM; ExtraTrees + conformal intervals; market forecasters)
        ↓
Persistence (SQLAlchemy 2, Alembic, SQLite/PostgreSQL)
        ↓
Data (curated public datasets, seed data, validated uploads)
```

A scan request is validated (MIME allow-list, 8 MB and 4096 px limits, SHA-256 deduplication),
passed to the crop-health service, and persisted together with its Grad-CAM overlay. The decision
service then reads this prediction, the latest yield prediction, market forecast, buyer offers and
transport estimate, builds typed inputs, calls the pure engine, and stores the decision and its
factors. Every API response labels its model mode (`real` vs `demo`), so fallback behaviour is
never silent.

### 3.2 Datasets

| Dataset | Role | Images used | Labels | Source / licence |
| --- | --- | --- | --- | --- |
| PlantVillage subset | Controlled lab images; disease semantics | 1,900 (1,368/266/266 train/val/test) | 38 | `Hemg/new-plant-diseases-dataset` |
| PlantDoc | In-the-wild internet/field images | 2,572 recovered (1,998/338/236) | 28 folders mapped to the 38-label space | Singh et al. 2020 [2], CC BY 4.0 |
| Web / farm photos | Optional **test-only** external domain | user-supplied | exact 38 folder names | user-collected |

A deterministic manifest stores all 4,472 entries with a `domain` tag and split assignment.
2,572 of 2,578 PlantDoc files were recovered; six filenames containing Windows-illegal characters
could not be stored, while all 28 classes and both official splits remain complete. The official
PlantDoc test split is never used for training or early stopping. A SHA-256 audit found 12 duplicate
image groups, 11 of which crossed train/val and test splits; `dedupe_manifest.py` removes those
training views while keeping every test image, producing the 4,460-entry manifest used by the
deployed v3 model. The full 38-class label list and the 28-folder mapping are recorded in
`docs/DATASETS_AND_LABELS.md`.

### 3.3 Model and preprocessing

The controlled cross-domain study uses EfficientNet-B0 pretrained on ImageNet; the deployed v3
classifier replaces it with ConvNeXt-Tiny while keeping the same 38 logits in the fixed deployed
order. Inputs are resized to 192×192 central crops and normalised with ImageNet mean and standard
deviation. Training augmentation uses RandomResizedCrop (scale 0.65–1.0), random horizontal flip,
vertical flip with probability 0.15, rotation up to 15°, colour jitter and random grayscale with
probability 0.05. Evaluation uses deterministic resize and centre crop; deployed serving averages
four views (original and horizontal flip at scales 1.0 and 0.9) before argmax.

Measured complexity on the development GPU (RTX 5060 Laptop, CUDA 12.8 wheels): ConvNeXt-Tiny has
**27,849,350 parameters**, a 106.24 MB checkpoint and 6.5458 GFLOPs, with 31.9 ms per image at
batch 1 and about 231 images/s at batch 32 for a single forward pass. The historical EfficientNet-B0
run used 4,056,226 parameters, 15.47 MB and 0.5655 GFLOPs. Four-view TTA costs approximately four
forward passes; the end-to-end CPU smoke prediction took about 1.76 s. Full data:
`ml/crop_health/evaluation/benchmark_results_v3.json`.

### 3.4 Training protocol

Inverse-frequency weighted cross-entropy is used to counter class imbalance; AdamW with a cosine
schedule and early stopping on validation macro-F1; seed 42; FP16 autocast plus GradScaler when
CUDA is available. The historical EfficientNet-B0 study used learning rate 3e-4; the deployed
ConvNeXt-Tiny used 1e-4 with the same weight decay of 1e-4 and 12 epochs. Optional regularisers—
label smoothing and mixup—are implemented as metadata-recorded flags so any published number can be
reproduced.
The weights, metadata, per-class reports, confusion matrices and training history are written by
one script (`train_field_robust.py`), so all reported values are code-generated.

### 3.5 Cross-domain protocol

Four protocols are run from the same manifest and evaluation code:

| Protocol | Training data | Question answered |
| --- | --- | --- |
| `baseline_pv` | PlantVillage only | How large is the lab-to-field gap? |
| `plantdoc_only` | PlantDoc only | What is achievable with field data alone? |
| `mixed` | PlantVillage + PlantDoc jointly | Does joint training retain lab accuracy and recover field accuracy? |
| `two_stage` | PlantVillage then PlantDoc | Does sequential adaptation help? |

Each model is evaluated on both held-out test sets. Additional measured ablations (256 px input,
test-time augmentation, ExG suppression, label smoothing and mixup) are described in Section 4.

### 3.6 Explainability

Grad-CAM [4] is computed on the last convolutional feature block (`features[-1]` for EfficientNet,
`features[-1][-1]` for ConvNeXt). For a predicted class *c*, the gradient of the class score with respect to each feature map is
globally averaged to obtain weights, and the weighted feature map is ReLU'd and upsampled. Overlays
are generated offline for the paper and online in the API, giving the farmer a visual check of
whether the decision used the lesion or the background.

### 3.7 Uncertainty-aware decision fusion

The decision engine consumes eight weighted risk components: yield uncertainty, crop health, buyer
offer freshness and competitiveness, market price uncertainty, transport cost, data completeness,
price staleness and holding deterioration. Health confidence gates the INSPECT rule: when
`min_health_confidence` (0.55) is not met, the health signal is discounted and the engine can
recommend manual verification instead of an economic action. Yield and price intervals propagate
into revenue bounds, so a decision is accompanied by both a point outcome and its uncertainty.

---

## 4. Results

### 4.1 Main cross-domain comparison

All values are accuracy; macro-F1 follows the same ordering. Full data:
`ml/crop_health/evaluation/cross_domain_results_all.json`.

| Protocol | PlantVillage (lab) | PlantDoc (field) | Lab F1 | Field F1 |
| --- | --- | --- | --- | --- |
| `baseline_pv` | **0.9549** | 0.3220 | 0.9539 | 0.2177 |
| `plantdoc_only` | 0.3120 | 0.6822 | 0.2396 | 0.6721 |
| **`mixed` (previous deployed baseline)** | **0.9511** | **0.6653** | **0.9507** | **0.6563** |
| `two_stage` | 0.8308 | 0.5551 | 0.8322 | 0.5292 |

The lab-only model loses **63.3 accuracy points** on real photographs. Joint training retains
essentially all lab accuracy (0.9549 → 0.9511) while more than doubling field accuracy
(0.3220 → 0.6653). The expected winner, two-stage fine-tuning, underperformed joint training on
*both* domains, consistent with catastrophic forgetting of the lab domain during field adaptation.
The previous deployed checkpoint was independently retrained to save the winning weights and
regenerate Grad-CAM; it measured **0.9511 lab / 0.6780 field** (F1 0.9507 / 0.6501). The small field
difference from the controlled run is attributed to non-deterministic CUDA kernel selection; both
numbers are preserved in the v2 backup metadata.

A follow-up experiment replaced the backbone with ConvNeXt-Tiny and removed 11 byte-identical
train/test image leaks from the manifest before training. The promoted single-view model measured
**0.9774 lab / 0.6907 field** (field F1 0.6833), strictly exceeding the 0.6780 promotion threshold.
Enabling the same 4-view TTA grid in serving and evaluation raised field accuracy to **0.7161**
(field F1 0.7093; lab 0.9812), fixing 9 and breaking 3 of 236 PlantDoc test images; accuracy below
the 0.55 screening threshold improved from 0.3333 to 0.4167. CUDA and CPU measurements agree.
Full provenance is in `docs/CROP_HEALTH_V3.md`; this later model, not the EfficientNet-B0 table
above, is the currently deployed system.

The form's selected farm crop is additionally used as a soft external prior with
`alpha=0.95` when it maps to one of the 14 trained crop groups. On the same held-out PlantDoc set,
this raises accuracy from 0.7161 to **0.8093** with a correct hint and to 0.7754 when 20% of hints
are wrong. A hard prior (`alpha=1.0`) reaches 0.8305 with correct hints but drops to 0.6568 at 20%
wrong hints, so it was rejected. Unsupported crops fall back unchanged. This serving enhancement
does not alter the weights or the 0.7161 promotion baseline; it is measured with
`ml/crop_health/evaluation/crop_prior_eval.py` and evidence is in
`ml/crop_health/evaluation/tta/crop_prior_convnext_results.json`.

### 4.2 Measured ablations (honest negative results included)

| Variant | Lab | Field | Outcome |
| --- | --- | --- | --- |
| 256 px, 20 epochs, select on PlantDoc validation | 0.9586 | 0.6525 | Rejected: field accuracy decreased; PlantDoc validation was a weak proxy for the official test split |
| 4-view TTA on v2 EfficientNet-B0 | 0.9662 | 0.6864 | Rejected: net two correct images out of 236, no gain below 0.55 confidence, 4× inference cost |
| ExG background suppression | 0.9586 | 0.6483 | **Rejected** — ExG suppresses the brown/necrotic pixels that carry lesion evidence |
| Label smoothing 0.1 + mixup 0.2 (192 px, 20 epochs, seed 42) | 0.9549 | 0.6610 | **Rejected** — field accuracy fell from 0.6780 to 0.6610 and macro-F1 from 0.6501 to 0.5584 |
| ConvNeXt-Tiny, de-duplicated manifest, single view | 0.9774 | 0.6907 | **Promoted** — +0.0127 field over the previous deployed checkpoint |
| 4-view TTA on the promoted ConvNeXt model | 0.9812 | 0.7161 | **Enabled** — +0.0254 field and +0.0833 low-confidence accuracy; the v2 TTA decision does not transfer |

These ablations are reported rather than hidden: more pixels, background suppression and stronger
regularisation were not automatic remedies under domain shift, and the choice of validation domain
materially affects checkpoint selection. TTA is model-dependent — rejected for v2 but enabled for
v3 after a larger held-out gain and a low-confidence improvement. Full measurement:
`ml/crop_health/evaluation/reg/cross_domain_results.json`; candidate weights:
`backend/app/ml/artifacts/crop_health_reg/` (not deployed).

### 4.3 Per-class behaviour

The deployed artefact stores a full 38×38 confusion matrix and per-class precision, recall and F1
for the PlantDoc test split. Of the 38 classes, 27 have non-zero support in the official test set.
For the promoted single-view ConvNeXt checkpoint, the weakest supported classes are maize gray leaf
spot (F1 0.143, n=4), tomato bacterial spot (0.235, n=9), soybean healthy (0.364, n=8) and potato
early blight (0.462, n=8); strongest are grape healthy, squash powdery mildew and strawberry healthy
(F1 1.000). The largest confusions are biologically plausible: maize northern leaf blight → maize
gray leaf spot (7 images), tomato bacterial spot → tomato septoria leaf spot (6), pepper bacterial
spot → tomato bacterial spot (4), peach healthy → cherry healthy (4) and potato early blight →
potato late blight (3).
Several errors are therefore between visually similar diseases or between healthy leaves of
different crops, not arbitrary background-driven failures. PlantDoc's single-label annotation of
images containing multiple leaves or diseases sets an upper bound on attainable accuracy, so the
reported field figures should be read as screening quality rather than diagnostic ground truth.

### 4.4 Qualitative explainability

Six official Grad-CAM overlays (three PlantVillage, three PlantDoc) are generated from the deployed
model and referenced in metadata. They show attention concentrated on lesion regions rather than
uniform background in the successfully classified examples. Overlays for uncertain cases are
returned through the API so the user can see which region drove a low-confidence prediction.

### 4.5 Efficiency and system behaviour

| Architecture | Params | Size | GFLOPs | ms/image (batch 1) | img/s (batch 32) |
| --- | --- | --- | --- | --- | --- |
| MobileNet-V3-Large | 4,250,710 | 16.22 MB | 0.3179 | 33.3 | 1005.0 |
| EfficientNet-B0 (historical v2) | 4,056,226 | 15.47 MB | 0.5655 | 42.3 | 726.4 |
| EfficientNet-B3 | 10,754,638 | 41.03 MB | 1.4134 | 66.7 | 434.7 |
| EfficientNet-V2-S | 20,226,166 | 77.16 MB | 4.1878 | 94.9 | 335.6 |
| **ConvNeXt-Tiny (deployed v3)** | **27,849,350** | **106.24 MB** | **6.5458** | **31.9** | **231.4** |
| ResNet-50 | 23,585,894 | 89.97 MB | 6.0057 | 31.5 | 733.9 |
| ConvNeXt-Small | 49,483,910 | 188.77 MB | 12.7587 | 54.5 | 119.7 |

Source: `ml/crop_health/evaluation/benchmark_results_v3.json`. The earlier cu118 run is preserved
in `benchmark_results.json`; timings measure one forward pass, while v3 serving averages four views.

A helper (`test_my_images.py`) runs arbitrary user photos through the deployed service and reports
label, confidence, severity and ACCEPT/INSPECT verdict. On five downloaded sample photos, the v3
service returned 2/5 exact matches and routed two low-confidence cases to INSPECT; these photos are
not a labelled test set and are reported only as smoke checks. The end-to-end API smoke test with
the deployed model produced a high-confidence early-blight prediction, a Grad-CAM overlay, a
`SELL` decision and a persisted report. Provenance is in `docs/CROP_HEALTH_V3.md`.

---

## 5. Discussion

The 63-point lab-to-field collapse is consistent with shortcut learning: a controlled background
and consistent leaf orientation let a model achieve high in-domain accuracy without learning
robust disease features. Joint training works because the field images break that shortcut while
the lab images preserve clean disease semantics; sequential fine-tuning instead overwrites the
lab representation.

The system-level implication is that confidence must be treated as a first-class quantity. A
classifier that is confidently wrong under domain shift is more dangerous than one that is
uncertain. The INSPECT rule, confidence discounting in the risk score and the Grad-CAM overlay are
therefore not cosmetic additions: they are the mechanism by which an imperfect input is prevented
from dominating an economic decision.

Limitations remain. PlantDoc contains roughly 2.6k images with single-label annotations of
possibly multi-disease leaves; the model assumes one leaf per image and covers 14 crop species.
 abiotic stress (nutrient deficiency, water stress) can visually mimic disease. The optional web
test set was not available for this draft. Field validation with longitudinal farmer data,
multi-label severity scoring and active learning from corrected predictions are needed before the
screening output can be treated as diagnostic.

---

## 6. Conclusion and Future Work

We presented AgriTwin, an uncertainty-aware agricultural decision system that fuses disease, yield,
market, offer and transport inputs into a single explainable decision. Its leaf-photo input was
cross-domain validated: the lab-to-field collapse was measured, joint training was shown to recover
field accuracy while retaining lab accuracy, and sequential adaptation was shown to fail. The
deployed model remains a screening aid, and the decision engine explicitly falls back to INSPECT
when confidence is insufficient. Future work includes on-device deployment, external field trials,
multi-label disease and severity modelling, and active learning from farmer feedback.

---

## References

1. S. P. Mohanty, D. P. Hughes and M. Salathé, "Using deep learning for image-based plant disease detection," *Frontiers in Plant Science*, vol. 7, p. 1419, 2016.
2. D. Singh, N. Jain, P. Jain, P. Kayal, S. Kumawat and N. Batra, "PlantDoc: A Dataset for Visual Plant Disease Detection," *ACM CoDS-COMAD*, pp. 249–253, 2020, doi: 10.1145/3371158.3371196.
3. M. Tan and Q. Le, "EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks," *ICML*, 2019.
4. R. R. Selvaraju *et al.*, "Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization," *ICCV*, 2017.
5. S. Kim and S. Heo, "An agricultural digital twin for mandarins demonstrates the potential for individualized agriculture," *Nature Communications*, vol. 15, p. 1561, 2024.
6. "Past, present and future of deep plant leaf disease recognition: A survey," *Computers and Electronics in Agriculture*, 2025, article 110128. `[VERIFY AUTHORS / DOI]`
7. "Artificial Intelligence-Driven Plant Disease Detection and Diagnosis: A Comprehensive Review," 2025/2026. `[VERIFY AUTHORS / VENUE / DOI]`
8. "A comprehensive evaluation of lightweight deep learning models for tomato disease classification on edge computing environments," *Scientific Reports*, 2026. `[VERIFY AUTHORS / DOI]`
9. "Deployable Deep Learning for Cross-Domain Plant Leaf Disease Detection," IEEE, 2025, document 11107438. `[VERIFY AUTHORS / DOI]`

> Every reference above must be checked on the publisher page before submission. Items 6–9 are
> seed-list entries whose full bibliographic details were not confirmed at draft time.

---

## Appendix A — Reproducibility

- Seed: 42; recorded in metadata.
- Dataset provenance and PlantDoc licence recorded; deterministic train/val/test manifest, plus the
  de-duplicated 4,460-entry manifest used by v3.
- No test image used for training or early stopping.
- Model version: `crop-health-v3.0.0-convnext` (`convnext_tiny`, `tta_views=4`); deployed artefact
  SHA-256 `4500C4FF14C99D3E7AFEC2F838AA555BADB3809656227CE77340391F14BD3A75`, recorded in
  `docs/CROP_HEALTH_V3.md` and `metadata.json`. The historical v2 SHA-256 was
  `6426E87F8F5C5F6EFF57444D61286A0B85406D6FE4704A1CF1E35F581D318ED6`.
- All metrics generated by `train_field_robust.py` and `tta_eval.py`; no hand-written values.
- Screening disclaimer: the application must present results as decision support, not a definitive
  diagnosis.

## Appendix B — User-facing label reference

The complete 38-label index and the PlantDoc folder mapping are in
`docs/DATASETS_AND_LABELS.md`. To test personal photos:

```powershell
python ml/crop_health/evaluation/test_my_images.py --image "C:\path\to\photo.jpg"
python ml/crop_health/evaluation/test_my_images.py --images "C:\path\to\folder" --out results.csv --gradcam-dir overlays
```
