# AgriTwin — project state

**State: research and engineering work complete (verified 2026-11-25).**
The current deployed crop-health model is `crop-health-v3.0.0-convnext` with
4-view TTA. See [CROP_HEALTH_V3.md](CROP_HEALTH_V3.md) for the authoritative
training, promotion and verification record.

## Done

- PlantDoc download complete: **2,572 / 2,578 images** (949 MB). Six edge-case filenames with
  Windows-illegal characters could not be stored; all 28 classes and both official splits are
  present. Recovery scripts live in `C:\Users\arvap\AppData\Local\Temp\opencode\`.
- Manifest built: 4,472 entries — PV 1,368/266/266 and PD 1,998/338/236 (train/val/test).
- Full four-experiment EfficientNet-B0 cross-domain training finished on RTX 5060 with `--amp`.
  It established the domain-shift finding and the historical `mixed` winner.
- A SHA-256 audit found 12 duplicate image groups, 11 crossing train/val and test. Built
  `ml/crop_health/data/field_robust/manifest_dedup.json` with 4,460 entries; the test sets are
  unchanged.
- Trained **ConvNeXt-Tiny** on the de-duplicated manifest with the same `mixed` protocol.
  It measured **0.9774 lab / 0.6907 field** single-view and beat the then-deployed v2 baseline of
  0.6780.
- Ran the promotion gate (dry run, then `--apply`) and deployed the new weights with a backup.
- Enabled metadata-driven 4-view TTA after measuring **0.7161 field** accuracy on the same
  held-out PlantDoc test split. Serving and `tta_eval.py` share one preprocessing helper.
- Grad-CAM device + `no_grad` bugs fixed; new ConvNeXt overlays generated and smoke-verified.
- Deployed the **soft crop prior** (`alpha=0.95`) on 2026-11-25 with fallback for unsupported crops.
- **All 98 backend tests, 26 frontend tests, the TypeScript production build and the end-to-end
  API smoke test pass** with the deployed artifact.
- Research docs updated: `RESEARCH_PAPER_PLAN.md`, `ML_PIPELINE.md`, `ARCHITECTURE.md`,
  `DATASETS.md`, `REVIT_RELEVANCE_TO_AGRITWIN.md`, `AgriTwin_Field_Robust_Colab.ipynb`.
- Paper draft and LaTeX source complete: `docs/PAPER_DRAFT.md`, `docs/paper/agritwin.tex`.

## Current deployed metrics

| Inference | Lab (PV) acc | Field (PD) acc | Field F1 | Field precision | Field recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single-view checkpoint | 0.9774 | 0.6907 | 0.6833 | 0.7182 | 0.6849 |
| **Deployed 4-view TTA** | **0.9812** | **0.7161** | **0.7093** | **0.7373** | **0.7106** |

Previous deployed EfficientNet-B0 re-run: 0.9511 lab / 0.6780 field, F1 0.9507 / 0.6501.

## Historical cross-domain numbers (`cross_domain_results_all.json`)

| Experiment | Lab (PV) acc | Field (PD) acc | Lab F1 | Field F1 |
| --- | --- | --- | --- | --- |
| `baseline_pv` | 0.9549 | 0.3220 | 0.9539 | 0.2177 |
| `plantdoc_only` | 0.3120 | 0.6822 | 0.2396 | 0.6721 |
| **`mixed` (previous deployed baseline)** | **0.9511** | **0.6653** | **0.9507** | **0.6563** |
| `two_stage` | 0.8308 | 0.5551 | 0.8322 | 0.5292 |

Interpretation: 63.3-point lab→field collapse for the lab-only model; joint training keeps lab
accuracy and roughly doubles field accuracy; sequential fine-tuning forgets the lab domain.
These four rows are the controlled EfficientNet-B0 study, not the current served model.

## Artifact

- `backend/app/ml/artifacts/crop_health/model.pt` — 111,452,123 bytes
- SHA-256 `4500C4FF14C99D3E7AFEC2F838AA555BADB3809656227CE77340391F14BD3A75`
- `version = crop-health-v3.0.0-convnext`, `training_mode = mixed`, `architecture = convnext_tiny`
- `tta_views = 4`; `metrics` is the TTA result and `single_view_metrics` preserves training metrics.

## Completed ablations and decisions

| Variant | Lab acc | Field acc | Decision |
| --- | --- | --- | --- |
| 256 px, 20 epochs, PlantDoc-validation selection | 0.9586 | 0.6525 | Rejected |
| 4-view TTA on v2 EfficientNet-B0 | 0.9662 | 0.6864 | Rejected for v2 (+2 images, no low-confidence gain, 4× cost) |
| ExG background suppression | 0.9586 | 0.6483 | Rejected (removes lesion evidence) |
| Label smoothing 0.1 + mixup 0.2 | 0.9549 | 0.6610 | Rejected (macro-F1 0.5584 vs 0.6501) |
| ConvNeXt-Tiny on de-duplicated manifest | 0.9774 | 0.6907 | **Promoted** (+0.0127 field) |
| 4-view TTA on v3 ConvNeXt-Tiny | 0.9812 | 0.7161 | **Enabled** (+0.0254 field, +0.0833 low-confidence) |

TTA was reproduced on CUDA and CPU:
`python ml/crop_health/evaluation/tta_eval.py --artifact-dir backend/app/ml/artifacts/crop_health --manifest ml/crop_health/data/field_robust/manifest_dedup.json --views 4 --domain both --detail --device cuda --output ml/crop_health/evaluation/tta/tta_4view_convnext_results.json`.

## Audit hardening (2026-11-24)

- PATCH endpoints now enforce the same validation as POST (merged-state revalidation in
  `app/schemas/common.py`), with a new regression test.
- Frontend Settings tab now reacts to `?tab=` changes; Dashboard uses SPA navigation; 404 uses
  real links; nine unused imports/removed redundant `/system/options` request.
- README auth statement now lists all ten public endpoints and discloses static `/uploads`.
- Review 1 presentation docs are marked as historical snapshots pointing to `FINAL_REPORT.md` §12–14.

## Still needed from the user

- Contact email, city/country and target venue for the IEEE-style paper. The author name and
  affiliation were recovered from the Review 1 records and filled in; these are the only remaining
  `[...]` placeholders in `docs/paper/agritwin.tex`.
- Bibliography entries marked `TODO_BIB` must be verified against publisher pages before submission.
- Optional: failed Google images in class folders for an additional external test domain — see
  `prepare_field_dataset.py` for the expected layout. The five ad-hoc photos currently in
  `downloads/` are smoke checks only and are reported in `docs/CROP_HEALTH_V3.md`.

## Old artifact backups

- `C:\Users\arvap\AppData\Local\Temp\opencode\crop_health_v1_backup` — original lab-only
  `crop-health-v1.0.0` (0.9361).
- `C:\Users\arvap\AppData\Local\Temp\opencode\crop_health_backup_20261124_192631` — previous
  `crop-health-v2.0.0-field-robust` checkpoint and metadata before v3 promotion.

## Next session plan — expand crop coverage (saved 2026-11-25)

The deployed model is still `crop-health-v3.0.0-convnext` with 4-view TTA and unconstrained field accuracy
**0.7161**. The soft crop prior from the earlier experiment was deployed on 2026-11-25 as a serving
enhancement, but the weights and the 0.7161 promotion baseline were not changed.

### Crop-hint findings (held-out PlantDoc test, n=236)

The scan form asks the user to select a farm/crop. Serving now uses that external hint as a soft
prior (`alpha=0.95`) when it maps to one of the 14 trained crop groups; unsupported crops fall back
to the unconstrained 4-view result. The table below is the measured result of reweighting the 38
TTA probabilities toward the selected crop:

| Case | Field accuracy |
| --- | ---: |
| Unconstrained 4-view TTA baseline (deployed weights) | 0.7161 |
| Correct crop hint, hard constraint | 0.8305 |
| Correct crop hint, soft prior `alpha=0.95` | 0.8093 |
| 5% wrong crop hints, soft prior `alpha=0.95` | 0.8008 |
| 10% wrong crop hints, soft prior `alpha=0.95` | 0.8051 |
| 20% wrong crop hints, soft prior `alpha=0.95` | 0.7754 |
| 20% wrong crop hints, hard constraint | 0.6568 |

Baseline crop-level accuracy is 0.8559. Of 67 wrong disease predictions, 34 are cross-crop and
33 are same-crop disease confusions. The soft prior is the deployed setting; the hard constraint
was rejected because it falls to 0.6568 with 20% wrong hints.

Self-conditioning from the model's own top crop gives **no gain** (0.7161), so a real external hint
(user/farm crop) is required. The evaluation is reproducible via
`ml/crop_health/evaluation/crop_prior_eval.py`, and the serving helper is
`apply_crop_prior()` in `backend/app/ml/crop_health/service.py`. Evidence files:
`ml/crop_health/evaluation/tta/crop_prior_convnext_results.json` and
`crop_prior_convnext_cpu_check.json`. The seeded Onion/Rice/Wheat crops are unsupported and
therefore use the fallback, so no benefit should be claimed for them until labelled classes exist.

### Current limitation

The classifier supports 14 crop groups: Apple, Blueberry, Cherry, Grape, Maize, Orange, Peach,
Pepper, Potato, Raspberry, Soyabean, Squash, Strawberry and Tomato. There are **zero** images for
Rice, Wheat, Cotton, Groundnut, Onion, Sugarcane, Chickpea, Mustard and Banana, so those crops
cannot be added by mapping code alone. Until new classes are trained, they must fall back to
unconstrained v3 inference.

### Dataset collection requirements

For each new crop, collect labelled leaf photos with licence/provenance notes:

- healthy class plus the important local diseases for that crop;
- both controlled/lab-style and real-field photos if field robustness is claimed;
- aim for at least ~100–200 usable images per class, with a held-out field test split;
- keep original filenames and a source URL/licence record;
- avoid train/test duplicates using `ml/crop_health/training/dedupe_manifest.py`;
- use class names `<Crop>___<disease>`, e.g. `Rice___leaf_blast`, `Wheat___yellow_rust`.

### Implementation order for the next session

1. Decide priority crops/diseases and inspect the collected folder layout.
2. Add new entries to `backend/app/ml/crop_health/labels.py` (`CLASS_INFO`). Existing aliases
   Corn→Maize, Chilli→Pepper and Soybean→Soyabean are already in place.
3. Build a new manifest with an expanded `class_order`; keep the existing 236 PlantDoc test images
   as a regression set and add new held-out field images for every new crop.
4. Train a new v4 candidate with the same de-duplicated, mixed-domain protocol on RTX 5060 using
   `C:\Users\arvap\AppData\Local\Temp\opencode\agritwin-ml-venv`.
5. Evaluate single-view first, then 4-view TTA; promote only if the shared held-out field score
   strictly beats **0.7161** and the old 236-image PlantDoc set does not regress.
6. The soft crop prior (`alpha=0.95`) is already deployed as a separately measured serving option
   with fallback for unsupported crops. When v4 classes are added, re-measure the prior on the new
   held-out protocol and keep it separate from the promotion number.

### PlantTom expansion attempt — 2026-11-25 (all candidates rejected)

A CC BY 4.0 tomato-leaf dataset, PlantTom, was downloaded from
`huggingface.co/datasets/vaskormostafa/PlantTom` and filtered into the existing
38-class label space. Provenance and filtering are recorded in
`ml/crop_health/data/external/planttom/SOURCE.md` and
`ml/crop_health/evaluation/planttom_dedupe_report.json`. The 502 official test
entries were kept byte-for-byte identical.

| Candidate | Added training images | Single-view field | 4-view TTA field | Decision |
| --- | ---: | ---: | ---: | --- |
| `v4.0.0-planttom` | 5,305 | 0.6695 | 0.6864 | Rejected |
| `v4.1.0-planttom-balanced` | 800 (100/class) | 0.6610 | 0.6695 | Rejected |
| `v4.2.0-planttom-continued` | 800, continued from v3 at lr 1e-5 | 0.6907 | 0.6864 | Rejected |

None beat the promotion baseline of **0.7161** on the unchanged 236-image
PlantDoc test set, so `crop-health-v3.0.0-convnext` remains deployed with its
original SHA-256 `4500C4FF14C99D3E7AFEC2F838AA555BADB3809656227CE77340391F14BD3A75`.
Detailed rejection notes are in each candidate's evaluation directory. The lesson
is that more tomato-only images do not fix the field gap; the next useful data
should add labelled field images for unsupported crops and under-performing
classes, not more near-duplicate tomato images.

### Zenodo multi-crop dataset — selected 2026-11-25

A broader CC BY 4.0 dataset was selected from Zenodo:
`Crop Health Monitoring Dataset: Disease Classification in Maize, Tea,
Tomatoes, Apples, and Beans` (DOI `10.5281/zenodo.10628735`, Gibson and Förster).
The source record, direct download, checksum and class mapping are in
`ml/crop_health/data/external/zenodo_multicrop/SOURCE.md`.

Only unambiguous folders were mapped into the deployed 38-class space. The
leakage-free filter removed 158 byte-identical duplicates, 12 near-test
duplicates and 4 intra-source perceptual duplicates. The full manifest accepts
3,544 images; a capped 300-per-class manifest accepts 1,558 images. Both keep
the 502 official test entries unchanged. Reports are in
`ml/crop_health/evaluation/zenodo_dedupe_report.json` and
`zenodo_dedupe_balanced_report.json`.

A continued low-learning-rate candidate from deployed v3 was evaluated first:
`crop-health-v5.0.0-zenodo-continued`, artifact
`backend/app/ml/artifacts/crop_health_v5_zenodo`. It scored **0.6864** single
view and **0.6822** with 4-view TTA on the unchanged PlantDoc field test, so it
was rejected against the `0.7161` promotion baseline. Full evidence is in
`ml/crop_health/evaluation/zenodo_continued/V5_REJECTION.md`. The deployed v3
weights remain unchanged.
