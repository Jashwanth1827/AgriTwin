# AgriTwin Research Paper Plan

**Goal:** a publishable, verifiable paper (IEEE conference or Scopus-indexed journal) built from
work that is genuinely novel and already implemented in this repository.

> Honest boundary: I can write the paper draft, structure the experiments, generate the result
> tables/figures, and prepare submission-ready LaTeX. I cannot submit on your behalf, pay fees,
> create an IEEE account, or guarantee acceptance. The verification/review is done by the venue.

---

## 0. Problem statement (the paper's actual headline)

> Farmers decide what to grow, when to harvest and where to sell using disconnected sources: a
> leaf photo, a yield guess, yesterday's mandi price, a phone offer and a transport quote.
> Individual predictions do not automatically produce the best economic decision. AgriTwin
> integrates these sources into a unified, uncertainty-aware decision-support system.

**The contribution is the system, not a better classifier.** A disease model is an *enabler*: if
the leaf photo is confident but wrong under real-world conditions, the decision engine receives a
false signal and the "uncertainty-aware" promise breaks at its first link. The cross-domain work
therefore measures and fixes the **reliability of the leaf-photo input** so it can be trusted by
the fusion layer. Do not present the classifier as the novelty; present it as the input-quality
evidence for the integrated decision.

Verified system hooks (unchanged by this work):
- `services/decision/risk.py` weights `crop_health` into the risk score and discounts low-confidence detections.
- `services/decision/fusion.py` blends health confidence into overall decision confidence.
- `services/decision/engine.py` has an INSPECT rule gated by `min_health_confidence`.

---

## 1. What is actually novel here (your "innovation")

Most leaf-disease papers report ~99% accuracy on **PlantVillage** — single leaves photographed
face-up on a uniform background. Published cross-domain studies show accuracy collapses on real
photographs. We measured that collapse directly: **0.9549 lab accuracy → 0.3220 on PlantDoc**
for the lab-only baseline.

| Asset | Already in repo? | Paper value |
| --- | --- | --- |
| **Unified uncertainty-aware decision engine** (leaf + yield + prices + offers + transport) | **Yes** | **Main contribution** |
| FastAPI + React + Postgres digital-twin platform | Yes | Deployment / system contribution |
| Grad-CAM explainability integrated in the API | Yes | XAI contribution |
| Yield regression + conformal intervals + market forecaster | Yes | Decision-support contribution |
| EfficientNet-B0 transfer learning, 38 classes | Yes | Historical controlled study |
| ConvNeXt-Tiny transfer learning + 4-view TTA, 38 classes | Yes | Deployed model |
| Weighted loss, cosine LR, early stopping, metadata-driven serving | Yes | Rigor / reproducibility |
| **Cross-domain evaluation (lab → field) with PlantDoc** | **Now completed** | **Input-reliability evidence** |
| **Measured negative result: two-stage adaptation underperforms joint training** | **Now completed** | Honest, reviewable finding |
| External web-image test set (your failed Google images) | Optional | External validation |
| ExG-guided background suppression (from ReVit UAV segmentation) | Implemented as an optional ablation | Claim only if measured accuracy improves |
| Hardware efficiency benchmark (params, GFLOPs, latency, FPS) | Yes — `benchmark.py` | Supports edge-deployment discussion |

**Title options**

1. *AgriTwin: Uncertainty-Aware Fusion of Leaf, Yield and Market Signals for Crop Decisions, with Cross-Domain Validation of the Disease Input*
2. *From Leaf Photo to Sell Decision: An Uncertainty-Aware Agricultural Digital Twin with Honest Field Validation*
3. *Beyond Lab Accuracy: Reliable Disease Inputs for an Integrated Crop Decision-Support System*

Option 1 is my recommendation: it leads with the system and still signals the cross-domain evidence.

**Contribution paragraph (ready to adapt):**

> This paper presents AgriTwin, an agricultural digital-twin platform that unifies a
> smartphone-accessible crop disease screening service, a conformal yield predictor, a market
> forecaster, and a deterministic decision engine so that a farmer's grow/harvest/sell decision is
> made from one uncertainty-bearing state rather than disconnected guesses. We study the
> reliability of the leaf-photo input under domain shift: reporting the measured drop from 0.9549
> in-domain accuracy to 0.3220 on in-the-wild PlantDoc images, and comparing four training
> protocols. Contrary to the common assumption, two-stage fine-tuning underperformed joint
> training (0.5551 vs 0.6653 PlantDoc accuracy). Joint PlantVillage + PlantDoc training won the
> historical EfficientNet-B0 study (0.9511 lab / 0.6653 field; 0.6780 in its v2 re-run). The
> deployed system now uses a ConvNeXt-Tiny trained on a de-duplicated joint manifest with
> metadata-driven 4-view TTA: **0.9812 lab / 0.7161 field**, with a soft external crop prior
> reaching **0.8093 field** when the selected crop is correct. Grad-CAM visualizations verify that
> the deployed model attends to lesion regions. All numbers are generated by released code and
> stored in metadata.

---

## 2. Paper structure (IEEE conference format, 6 pages)

### Abstract (150–200 words)
Lead with the farmer decision problem, then the system, then the measured domain gap and the
joint-training fix. Headline numbers from `cross_domain_results_all.json`; use
`docs/CROP_HEALTH_V3.md` for the currently deployed v3/TTA numbers.

### 1. Introduction
- Farmers combine disconnected signals; individual predictions do not imply a good economic decision.
- The "99% trap": lab accuracy does not transfer (cite Mohanty et al. 2016; Singh et al. 2020).
- Why a digital twin matters: the disease signal feeds yield, market and sell/wait decisions.
- Contributions as a bullet list (use the paragraph above).

### 2. Related Work
- CNN/transfer learning on PlantVillage (EfficientNet, ResNet, MobileNet).
- In-the-wild datasets: PlantDoc, field datasets; cross-domain plant disease studies.
- XAI in plant pathology: Grad-CAM / Grad-CAM++ / LIME.
- Digital twins in agriculture (Kim & Heo 2024 Nature Communications; 2025/2026 surveys).
- Decision support under uncertainty / conformal prediction.
- Explicitly position: *few works validate a deployed decision system whose first input is
  cross-domain validated and explained.*
- Excess-green (ExG): cite a standard ExG reference; state that this work adapts the idea from our
  complementary UAV crop/weed segmentation study (ReVit) and reports it **only** as an ablation.
  See `docs/REVIT_RELEVANCE_TO_AGRITWIN.md` for why the two models are separate systems — keep the
  papers separate and cross-cite them.

### 3. Materials and Methods
3.1 **Datasets** — PlantVillage subset (1,900 images, 38 classes), PlantDoc (2,578 images,
28 folders mapped to the same 38 labels, CC BY 4.0), optional external web set.
2,572/2,578 PlantDoc images were recovered; six edge-case filenames are unavailable on Windows.
Include a size table and a sentence on the mapping.
3.2 **Preprocessing & augmentation** — 192×192 crop, ImageNet normalization, RandomResizedCrop,
flips, rotation, colour jitter, optional RandomErasing.
3.3 **Model** — the controlled study used EfficientNet-B0 (ImageNet weights) with a 38-logit
head; the deployed v3 model uses ConvNeXt-Tiny with the same fixed class order. Parameter counts
and FLOPs are in `benchmark_results_v3.json` (the historical cu118 run is preserved in
`benchmark_results.json`).
3.4 **Training protocol** — weighted cross-entropy, AdamW (3e-4 for the historical study, 1e-4
for v3), cosine schedule, early stopping on macro-F1, seed 42, AMP on RTX 5060.
3.5 **Cross-domain protocol** — the four experiments in Section 3 below. This is the input-quality study.
3.6 **Explainability** — Grad-CAM formulation; target layer `features[-1]` for EfficientNet and
`features[-1][-1]` for ConvNeXt.
3.7 **System integration** — one paragraph + architecture diagram: upload → FastAPI → 4-view TTA
model + Grad-CAM → risk/confidence fusion → decision engine → React dashboard. This is the core figure.

### 4. Results
4.1 Main cross-domain table (measured values below).
4.2 Negative result: two-stage catastrophic forgetting (lab 0.9549 → 0.8308, field only 0.5551).
4.3 Per-class analysis from the promoted ConvNeXt-Tiny model's PlantDoc confusion matrix.
4.4 Grad-CAM qualitative comparison: lab model vs deployed model attention on lesions.
4.5 Deployed v3 table: single-view vs 4-view TTA, including the low-confidence subgroup.
4.6 Soft external crop prior: 0.7161 baseline, 0.8093 with a correct hint, 0.7754 at 20% wrong
hints; hard prior rejected at 0.6568 under 20% wrong hints.
4.7 System metrics: inference latency from `inference_ms` (v3 TTA ≈1.76 s on CPU); backend 98 tests,
frontend 26 tests and the smoke test all passed on 2026-11-25.

### 5. Discussion
- Why the gap exists (background, illumination, occlusion, capture angle).
- Why joint training beat sequential fine-tuning (no catastrophic forgetting; shared augmentation).
- False-positive risk: abiotic stress misclassified as disease — keep the screening disclaimer.
- Confidence threshold and the INSPECT rule when `min_health_confidence` is not met.
- Limitations: PlantDoc is ~2.6k images; single-leaf assumption; web set optional and small.

### 6. Conclusion and Future Work
Prospective field validation, TFLite edge deployment, multi-label/co-occurring diseases, severity
scoring, active learning with farmer feedback.

### References
Use the real works listed in Section 6 below. Do not invent citations.

---

## 3. Experiment matrix — MEASURED (RTX 5060, EfficientNet-B0, 192 px, seed 42, AMP)

Full data: `ml/crop_health/evaluation/cross_domain_results_all.json`.
The historical v2 copy of the table is in the backup metadata; the current deployed metadata keeps
`single_view_metrics` and TTA metrics in `backend/app/ml/artifacts/crop_health/metadata.json`.

| # | Training data | Test: PV lab | Test: PlantDoc | Purpose |
| --- | --- | --- | --- | --- |
| E1 `baseline_pv` | PlantVillage only | **0.9549** | **0.3220** | Reproduces the gap (63.3-point collapse) |
| E2 `plantdoc_only` | PlantDoc only | 0.3120 | 0.6822 | Small-data in-domain reference |
| E3 `mixed` | PV + PD jointly | **0.9511** | **0.6653** | **Best combined; previous deployed baseline** |
| E4 `two_stage` | PV then PD fine-tune | 0.8308 | 0.5551 | Negative result — underperforms E3 |
| E5 | E3 + ExG suppression | 0.9586 | 0.6483 | Rejected negative result — field accuracy decreased |

Macro-F1 follows the same ordering: E1 (PV 0.9539 / PD 0.2177), E2 (0.2396 / 0.6721),
E3 (0.9507 / 0.6563), E4 (0.8322 / 0.5292).

The **previous v2 checkpoint** was produced by an independent re-run of E3 so that the winning
weights could be saved and Grad-CAM regenerated. It measured **0.9511 lab / 0.6780 field**
(F1 0.9507 / 0.6501). The small field difference from E3 in the table above (0.6653) reflects
non-deterministic CUDA kernel selection, not a protocol change. Use the table for the controlled
four-way comparison and the v2 re-run only as the historical promotion baseline. The deployed v3
model is described separately below.

**Additional ablations attempted (all measured, none deployed unless stated):**

| Variant | Lab | Field | Outcome |
| --- | --- | --- | --- |
| 256 px, 20 epochs, select on PlantDoc val | 0.9586 | 0.6525 | Rejected — field got worse; PD-val is a weak proxy for the official test set |
| 4-view TTA on the historical v2 EfficientNet-B0 | 0.9662 | 0.6864 | Rejected — net +2 images, no gain on low-confidence cases, 4× latency ([results JSON](../ml/crop_health/evaluation/tta/tta_4view_results.json)) |
| E3 + ExG background suppression (E5) | 0.9586 | 0.6483 | **Rejected** — field accuracy dropped below the then-deployed v2 baseline of 0.6780; brown lesions are non-green and ExG can erase disease evidence |
| Label smoothing 0.1 + mixup 0.2 (192 px, 20 epochs) | 0.9549 | 0.6610 | **Rejected** — field accuracy below the then-deployed v2 baseline of 0.6780; macro-F1 dropped to 0.5584 |
| ConvNeXt-Tiny on de-duplicated manifest, single view | 0.9774 | 0.6907 | **Promoted** — +0.0127 field over the v2 baseline |
| 4-view TTA on the promoted ConvNeXt-Tiny | 0.9812 | 0.7161 | **Enabled** — +0.0254 field and +0.0833 low-confidence accuracy |

These are useful honest findings for the Discussion: more pixels, ExG and stronger regularisation
are not automatic wins under domain shift, and the validation domain used for checkpoint selection
matters. TTA is model-dependent: it was rejected for v2 but enabled for v3 after a larger held-out
gain and a low-confidence improvement. ExG from the ReVit study remains in a separate paper and is
only cross-cited here.

**Deployed v3 (authoritative record: `docs/CROP_HEALTH_V3.md`).** A SHA-256 audit found 12
duplicate image groups in the original manifest, 11 of which crossed train/val and the official
PlantDoc test split. `dedupe_manifest.py` removes those training views while retaining all test
images (4,472 → 4,460 entries). ConvNeXt-Tiny was trained with `mixed` data, 192 px, lr 1e-4,
12 epochs, seed 42 and AMP on CUDA 12.8. Single-view field accuracy 0.6907 strictly beat the
0.6780 promotion threshold; after `promote_candidate.py --apply`, metadata-driven 4-view TTA was
enabled because it raised field accuracy to 0.7161 (field F1 0.7093, lab 0.9812), fixed 9 and
broke 3 of 236 images, and improved accuracy below the 0.55 threshold from 0.3333 to 0.4167.
CUDA and CPU evaluations agree; serving and `tta_eval.py` share the same transform helper.

**Honest interpretation:** joint training keeps essentially all lab accuracy (0.9549 → 0.9511)
while more than doubling field accuracy (0.3220 → 0.6653). Sequential fine-tuning forgets the
lab domain and does not fully recover the field domain. This reverses the originally expected
ranking; report it as a finding, not a failure to hide.

Run:
```bash
python ml/crop_health/training/prepare_field_dataset.py --plantdoc-dir ml/crop_health/data/plantdoc --web-dir ml/crop_health/data/web_images
python ml/crop_health/training/train_field_robust.py --mode all --epochs 12 --deploy-experiment mixed --amp

# E5: same protocol with ReVit-derived ExG preprocessing into a separate artifact dir
python ml/crop_health/training/train_field_robust.py --mode mixed --epochs 12 --amp \
    --exg-suppression --exg-strength 0.8 \
    --artifact-dir backend/app/ml/artifacts/crop_health_exg \
    --eval-dir ml/crop_health/evaluation/exg
```

Results land in `ml/crop_health/evaluation/cross_domain_results.json` (the full four-experiment
run is preserved as `cross_domain_results_all.json`; the E5 run writes to `.../exg/`). The
`--exg-suppression` flag is recorded in metadata so the FastAPI service reproduces the same
preprocessing at inference.

**Measured efficiency on the development GPU (RTX 5060 Laptop, input 192 px, 38 classes):**

| Architecture | Params | Model size | GFLOPs | ms/image (batch 1) | img/s (batch 32) |
| --- | --- | --- | --- | --- | --- |
| MobileNet-V3-Large | 4,250,710 | 16.22 MB | 0.3179 | 33.3 | 1005.0 |
| EfficientNet-B0 (historical v2) | 4,056,226 | 15.47 MB | 0.5655 | 42.3 | 726.4 |
| EfficientNet-B3 | 10,754,638 | 41.03 MB | 1.4134 | 66.7 | 434.7 |
| EfficientNet-V2-S | 20,226,166 | 77.16 MB | 4.1878 | 94.9 | 335.6 |
| **ConvNeXt-Tiny (deployed v3)** | **27,849,350** | **106.24 MB** | **6.5458** | **31.9** | **231.4** |
| ResNet-50 | 23,585,894 | 89.97 MB | 6.0057 | 31.5 | 733.9 |
| ConvNeXt-Small | 49,483,910 | 188.77 MB | 12.7587 | 54.5 | 119.7 |

Full data: `ml/crop_health/evaluation/benchmark_results_v3.json` (CUDA 12.8 wheels, measured
for this work). The earlier cu118 run remains in `benchmark_results.json`. Regenerate with
`python ml/crop_health/evaluation/benchmark.py --architecture all`. Timings cover only the
forward pass; v3 serving also averages four views, measured at about 1.76 s per CPU prediction in
the smoke test.

---

## 4. Figures and tables to generate

| Item | Source | Caption hint |
| --- | --- | --- |
| Cross-domain accuracy table | `cross_domain_results_all.json` → `summary` | "In-domain vs out-of-domain accuracy" |
| Confusion matrix (PlantDoc) | same JSON → `experiments.mixed.results.pd.confusion_matrix` | 38×38 heatmap or top-confused pairs |
| Grad-CAM overlays | `backend/uploads/gradcam/**/*.png` (live predictions) or regenerate with `scripts/smoke_api.py` | "Attention on lesion vs background" |
| Architecture diagram | draw from `docs/ARCHITECTURE.md` | "Seven-layer AgriTwin architecture with uncertainty fusion" |
| Training curves | `metadata.json` → `history` | "Validation macro-F1 for the deployed joint model" |
| Lab vs field sample images | PlantVillage + PlantDoc examples | "Visual manifestation of the domain gap" |

---

## 5. Reproducibility checklist

- [x] Seed fixed (42), recorded in metadata.
- [x] Exact dataset provenance and licence recorded (PlantDoc CC BY 4.0).
- [x] Train/val/test splits deterministic and stored in the manifest.
- [x] No test image used for early stopping.
- [x] Hyperparameters listed in a table (below).
- [x] All metrics generated by code, none hand-written, including the historical v2 TTA rejection
      (`ml/crop_health/evaluation/tta/tta_4view_results.json`) and the deployed v3 TTA evidence
      (`tta_4view_convnext_results.json`, reproduced with
      `python ml/crop_health/evaluation/tta_eval.py --artifact-dir backend/app/ml/artifacts/crop_health
      --manifest ml/crop_health/data/field_robust/manifest_dedup.json --views 4 --domain both --detail
      --device cuda --output ...`).
- [x] Model version and SHA-256 of `model.pt` recorded (see below).
- [x] Failure/disclaimer behaviour documented (screening, not diagnosis).
- [ ] Code + metadata released in a public repo (GitHub) with a DOI via Zenodo — **owner action**;
      the repository is local and the trained weights are intentionally gitignored.

### Training hyperparameters

| Setting | Historical v2 `mixed` run | Regularizer candidate | Deployed v3 run |
| --- | --- | --- | --- |
| Architecture | EfficientNet-B0 (4,056,226 params) | EfficientNet-B0 | ConvNeXt-Tiny (27,849,350 params) |
| Manifest | `manifest.json` | `manifest.json` | `manifest_dedup.json` (4,460 entries) |
| Image size | 192 px | 192 px | 192 px (resize 240) |
| Seed | 42 | 42 | 42 |
| Epochs requested / completed | 12 / 12 | 20 / 16 (early stop) | 12 / 12 |
| Batch size | 32 | 32 | 32 |
| Optimizer | AdamW, lr 3e-4, weight decay 1e-4 | same | AdamW, lr 1e-4, weight decay 1e-4 |
| Scheduler | cosine annealing (`T_max = epochs`) | same | same |
| Loss | inverse-frequency weighted cross-entropy | + label smoothing 0.1 | inverse-frequency weighted cross-entropy |
| Mixup | off | alpha 0.2 | off |
| AMP | on | on | on (CUDA 12.8 wheels) |
| Checkpoint selection | validation macro-F1 | validation macro-F1 | validation macro-F1 |
| Patience | 3 | 5 | 3 |
| Serving TTA | none (v2 rejected 4 views) | none | 4 views, metadata-driven |

**Deployed artifact:** `backend/app/ml/artifacts/crop_health/model.pt`, version
`crop-health-v3.0.0-convnext`, SHA-256
`4500C4FF14C99D3E7AFEC2F838AA555BADB3809656227CE77340391F14BD3A75`, `tta_views=4`. The weights
are gitignored because of their size (111,452,123 bytes); a fresh clone must restore them from the
project archive or retrain with the command in `docs/CROP_HEALTH_V3.md`. The previous v2 backup
SHA-256 was `6426E87F8F5C5F6EFF57444D61286A0B85406D6FE4704A1CF1E35F581D318ED6`.

---

## 6. Reference seed list (verify details before citing)

1. Mohanty, S. P., Hughes, D. P., & Salathé, M. (2016). *Using deep learning for image-based plant disease detection.* Frontiers in Plant Science, 7, 1419. — original PlantVillage + the lab-to-field caveat.
2. Singh, D., Jain, N., Jain, P., Kayal, P., Kumawat, S., & Batra, N. (2020). *PlantDoc: A Dataset for Visual Plant Disease Detection.* ACM CoDS-COMAD, 249–253. DOI 10.1145/3371158.3371196. — the in-the-wild dataset.
3. Tan, M., & Le, Q. (2019). *EfficientNet: Rethinking Model Scaling for CNNs.* ICML. — backbone.
4. Selvaraju, R. R. et al. (2017). *Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization.* ICCV. — XAI method.
5. Kim, S., & Heo, S. (2024). *An agricultural digital twin for mandarins demonstrates the potential for individualized agriculture.* Nature Communications, 15, 1561. — digital-twin framing.
6. *Past, present and future of deep plant leaf disease recognition: A survey.* Computers and Electronics in Agriculture (2025), 110128. — reviews 18 datasets and the field-readiness gap.
7. *Artificial Intelligence-Driven Plant Disease Detection and Diagnosis: A Comprehensive Review* (PMC13066816, 2025/2026) — warns about PlantVillage shortcuts and recommends Grad-CAM verification.
8. *A comprehensive evaluation of lightweight deep learning models for tomato disease classification on edge computing environments.* Scientific Reports (2026) — in-domain PlantDoc evaluation and edge deployment.
9. *Deployable Deep Learning for Cross-Domain Plant Leaf Disease Detection.* IEEE (2025), document 11107438. — closest related cross-domain smartphone work.

Check every DOI/year on the publisher page before final submission.

---

## 7. Suggested venues

**IEEE conferences (good fit for a 6-page systems + ML paper):**
- IEEE Region conferences (e.g., R10 / TENCON) — most realistic for a student project
- IEEE International Conference on Smart Agriculture / IEEE Global Conference on AI, IoT and Robotics
- IEEE International Conference on Image Processing (ICIP)
- IEEE/CVF Winter Conference on Applications of Computer Vision (WACV) — competitive

**Scopus / IEEE-indexed journals with applied-agriculture scope:**
- IEEE Access (open access; article processing charge applies)
- Smart Agricultural Technology (Elsevier)
- Computers and Electronics in Agriculture (Elsevier; high bar)
- Frontiers in Plant Science / Frontiers in Artificial Intelligence
- Scientific Reports (Nature Portfolio)

For a first submission, an IEEE regional conference or *IEEE Access* is the most realistic
"verified IEEE" route. Confirm the venue's scope, APC, and review timeline before writing the
final version.

---

## 8. What I need from you to finish the paper

1. Author names/affiliations, target venue and contact email for the paper front matter.
2. Optional: put your failed Google images into class folders as described in
   `prepare_field_dataset.py` and tell me the folder path (external test domain).
3. Verify bibliography entries against publisher pages before citing.

Already done: all four experiments, the ExG ablation (E5, rejected), the label-smoothing/mixup
ablation (rejected), and the final test-suite/build/smoke re-run on 2026-11-24 (76 backend tests,
26 frontend tests, production build and end-to-end smoke all pass). No further training is
required for the main table.
