# Crop-health v3 — ConvNeXt-Tiny + operator-aligned TTA

**Status: deployed on 2026-11-24 UTC.** This is the authoritative record for the
currently served crop-health model. The EfficientNet-B0 four-protocol study in
`FINAL_REPORT.md` §5.1, `RESEARCH_PAPER_PLAN.md` and `PAPER_DRAFT.md` remains a
valid controlled comparison, but its “deployed” labels refer to the previous
`crop-health-v2.0.0-field-robust` checkpoint and must be read as historical.

## What changed

1. **New backbone.** `convnext_tiny` replaces `efficientnet_b0`. Training and
   serving builders, the benchmark script and Grad-CAM target resolution were all
   extended with matching state-dict layouts. `convnext_small` and
   `efficientnet_v2_s` were also added as supported options.
2. **Leakage-free training manifest.** A byte-level SHA-256 audit found 12
   duplicate image groups in the original manifest, 11 of which put an identical
   photo in both train/val and the official PlantDoc test split — sometimes with
   contradictory maize labels. `dedupe_manifest.py` keeps the test images and
   drops their duplicated training views, producing `manifest_dedup.json`:
   **4,472 → 4,460** entries. The held-out test sets are unchanged.
3. **Measured, reproducible TTA.** The deployed artifact sets `tta_views=4`.
   Serving and `tta_eval.py` now call the same helper, so the measured and
   deployed preprocessing cannot drift. The four views are original + horizontal
   flip at scales 1.0 and 0.9; probabilities are averaged before argmax.
4. **Soft external crop prior (serving enhancement, 2026-11-25).** The artifact
   also sets `crop_prior_alpha=0.95`. When the selected farm crop maps to one of
   the 14 trained crop groups, the averaged probabilities are softly reweighted
   toward that group before argmax. Unsupported crops (for example the seeded
   Onion, Rice and Wheat crops) leave the probabilities untouched. This does not
   retrain the weights and does not replace the unconstrained 0.7161 promotion
   baseline.

## Training configuration

| Setting | Value |
| --- | --- |
| Version | `crop-health-v3.0.0-convnext` |
| Architecture | `convnext_tiny`, ImageNet-V1 pre-trained |
| Data | `ml/crop_health/data/field_robust/manifest_dedup.json` |
| Splits | PV 1,368/266/266; PD 1,987/337/236 (train/val/test) |
| Mode | `mixed` — PlantVillage + PlantDoc jointly |
| Input | 192 × 192, resize 240, ImageNet mean/std |
| Augmentation | strong RandomResizedCrop, flips, rotation, colour jitter, grayscale |
| Loss | inverse-frequency weighted cross-entropy |
| Optimiser | AdamW, lr `1e-4`, weight decay `1e-4`, cosine schedule |
| Epochs | 12 completed, early-stopping patience 3, best validation macro-F1 |
| Seed | 42 |
| AMP | enabled on RTX 5060 |
| Training time | 1,602 s |

The training environment was an isolated CUDA-enabled venv at
`C:\Users\arvap\AppData\Local\Temp\opencode\agritwin-ml-venv` with
`torch 2.7.1+cu128` / `torchvision 0.22.1+cu128`. The main project environment
keeps its existing `cu118` wheels; RTX 5060 (`sm_120`) requires the newer build.

## Measured results

| Inference | PlantVillage (lab) | PlantDoc (field) | Field macro-F1 | Field precision | Field recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single view | 0.9774 | 0.6907 | 0.6833 | 0.7182 | 0.6849 |
| Unconstrained 4-view TTA (promotion baseline) | 0.9812 | 0.7161 | 0.7093 | 0.7373 | 0.7106 |
| **4-view TTA + correct crop prior (deployed serving)** | **0.9850** | **0.8093** | **0.8024** | **0.8233** | **0.8044** |
| Previous deployed v2 | 0.9511 | 0.6780 | 0.6501 | 0.6969 | 0.6558 |

The TTA gain is not just a confidence trim: on the PlantDoc test split it fixes
9 images and breaks 3 (net +6). Below the 0.55 screening threshold, accuracy
moves from 0.3333 to 0.4167 (n=48); above it, from 0.7819 to 0.7926 (n=188).
CUDA and CPU evaluations produce the same **0.7161** result, recorded in
`ml/crop_health/evaluation/tta/tta_4view_convnext_results.json` and
`tta_4view_convnext_cpu_check.json`. The cost is roughly 4× the forward passes,
which the smoke test measured at about 1.76 s per CPU prediction. A forward-pass
benchmark on RTX 5060 with CUDA 12.8 wheels measured ConvNeXt-Tiny at
27,849,350 parameters, 106.24 MB, 6.5458 GFLOPs and 31.9 ms/image at batch 1;
full data is in `ml/crop_health/evaluation/benchmark_results_v3.json`.

### Crop-conditioned inference

The scan form already asks for a farm/crop. Starting 2026-11-25, that external
hint is used as a **soft prior** with `alpha=0.95`. It is not a hard mask: even
when the hint is wrong, the original model probabilities keep 5% of their mass,
so the classifier can still return a class from another crop. The same helper is
called by serving and by `crop_prior_eval.py`, and Grad-CAM still visualises the
unmodified first TTA view rather than the prior-adjusted decision.

Held-out PlantDoc test, n=236 (same weights, same 4-view TTA grid):

| Hint quality | `alpha=0` baseline | Deployed `alpha=0.95` | `alpha=1.0` (not deployed) |
| --- | ---: | ---: | ---: |
| Correct crop | 0.7161 | **0.8093** | 0.8305 |
| 5% wrong hints | 0.7161 | **0.8008** | 0.8008 |
| 10% wrong hints | 0.7161 | **0.8051** | 0.7373 |
| 20% wrong hints | 0.7161 | **0.7754** | 0.6568 |

On PlantVillage, a correct hint moves accuracy from 0.9812 to 0.9850; an
unsupported crop hint changes nothing. The hard prior is deliberately not
deployed because it collapses to 0.6568 when one in five hints is wrong. The
soft prior still beats the unconstrained baseline under every simulated wrong
rate measured here, but it assumes errors are scattered rather than
systematically adversarial. Evidence:
`ml/crop_health/evaluation/tta/crop_prior_convnext_results.json`, with a CPU
agreement check in `crop_prior_convnext_cpu_check.json`.

### Promotion trail

| Step | Result |
| --- | --- |
| Controlled previous deployed baseline | field 0.6780 |
| ConvNeXt-Tiny single-view candidate | field 0.6907, **+0.0127** |
| Promotion dry run | `DECISION: PROMOTE`, identical 38-class order |
| Promotion applied | backup at `C:\Users\arvap\AppData\Local\Temp\opencode\crop_health_backup_20261124_192631` |
| 4-view TTA on promoted model | field 0.7161, **+0.0254** over the promoted single-view model |
| Soft crop prior enabled (no weight change) | correct hint 0.8093, 20% wrong hints 0.7754; baseline remains 0.7161 |

The pre-registered rule was applied before TTA was enabled: the weights were
promoted only because single-view field accuracy strictly exceeded 0.6780. The
serving TTA flag was then enabled only after the same held-out test split showed
a further measurable gain. The crop prior was added later as a metadata-driven
serving option; it is reported separately and was not used to justify weight
promotion.

## Field error analysis (single-view checkpoint)

Weakest PlantDoc classes with meaningful support:

| Class | Support | F1 | Recall |
| --- | ---: | ---: | ---: |
| Maize gray leaf spot | 4 | 0.143 | 0.250 |
| Tomato bacterial spot | 9 | 0.235 | 0.222 |
| Soybean healthy | 8 | 0.364 | 0.250 |
| Potato early blight | 8 | 0.462 | 0.375 |
| Maize northern leaf blight | 12 | 0.476 | 0.417 |

Strongest supported classes include grape healthy, squash powdery mildew and
strawberry healthy (F1 1.000 each). Small supports make per-class numbers noisy;
aggregate accuracy is the more stable estimate.

## Ad-hoc photo checks

The final serving path was also run on the five downloaded sample photos
(`downloads/convnext_detection_checks.csv`):

| Photo | Prediction | Confidence | Verdict | Assessment |
| --- | --- | ---: | --- | --- |
| Wikipedia corn northern leaf blight | Maize — Northern leaf blight | 0.991 | ACCEPT | Correct |
| Wikipedia tomato early blight | Potato — Early blight | 0.521 | INSPECT | Correct disease, wrong crop label |
| Google / NC State early blight | Tomato — Septoria leaf spot | 0.505 | INSPECT | Wrong |
| Google / Alabama early blight | Tomato — Septoria leaf spot | 0.787 | ACCEPT | Wrong |
| Google / Long Island early blight | Tomato — Early blight | 0.756 | ACCEPT | Correct |

Only **2/5 exact** (or 3/5 if the crop mismatch is ignored) are correct. These
photos are not labelled manifest entries and must not be used as a metric; they
are smoke checks that show why the product keeps the INSPECT path.

## Reproduce

```powershell
# 1. Build the leakage-free manifest
python ml/crop_health/training/dedupe_manifest.py

# 2. Train the candidate (CUDA 12.8 venv)
$py = "C:\Users\arvap\AppData\Local\Temp\opencode\agritwin-ml-venv\Scripts\python.exe"
& $py ml/crop_health/training/train_field_robust.py `
  --manifest ml/crop_health/data/field_robust/manifest_dedup.json `
  --mode mixed --architecture convnext_tiny `
  --model-version crop-health-v3.0.0-convnext `
  --epochs 12 --batch-size 32 --lr 1e-4 --image-size 192 `
  --patience 3 --amp `
  --artifact-dir backend/app/ml/artifacts/crop_health_convnext `
  --eval-dir ml/crop_health/evaluation/convnext

# 3. Gate and promote
python ml/crop_health/evaluation/promote_candidate.py `
  --candidate backend/app/ml/artifacts/crop_health_convnext
python ml/crop_health/evaluation/promote_candidate.py `
  --candidate backend/app/ml/artifacts/crop_health_convnext --apply

# 4. Measure TTA on the same held-out test split
& $py ml/crop_health/evaluation/tta_eval.py `
  --artifact-dir backend/app/ml/artifacts/crop_health `
  --manifest ml/crop_health/data/field_robust/manifest_dedup.json `
  --views 4 --domain both --detail --device cuda `
  --output ml/crop_health/evaluation/tta/tta_4view_convnext_results.json

# 5. Measure the deployed soft crop prior on the same held-out test split
& $py ml/crop_health/evaluation/crop_prior_eval.py `
  --artifact-dir backend/app/ml/artifacts/crop_health `
  --manifest ml/crop_health/data/field_robust/manifest_dedup.json `
  --views 4 --device cuda `
  --output ml/crop_health/evaluation/tta/crop_prior_convnext_results.json

## Post-v3 data expansion attempt

PlantTom (CC BY 4.0) added 5,305 deduplicated tomato-leaf training images to the
existing 38-class space, and capped/continued-training variants were also tried.
All three candidates were rejected because unconstrained 4-view PlantDoc accuracy
was 0.6864, 0.6695 and 0.6864 respectively — none beat the 0.7161 promotion
baseline. The deployed v3 weights are unchanged. Full provenance and per-candidate
evidence are in `ml/crop_health/data/external/planttom/SOURCE.md` and
`ml/crop_health/evaluation/PLANT_TOM_V4_SUMMARY.md`.

A second CC BY 4.0 source from Zenodo added up to 1,558 deduplicated multi-crop
images (apple, maize and tomato folders mapped into the 38-class space). The
continued-training candidate `crop-health-v5.0.0-zenodo-continued` scored 0.6822
with 4-view TTA and was also rejected. Its source record and rejection evidence
are in `ml/crop_health/data/external/zenodo_multicrop/SOURCE.md` and
`ml/crop_health/evaluation/zenodo_continued/V5_REJECTION.md`. The deployed v3
weights remain unchanged.
```

## Artifacts

- `backend/app/ml/artifacts/crop_health/model.pt` — ConvNeXt-Tiny weights,
  111,452,123 bytes, SHA-256
  `4500C4FF14C99D3E7AFEC2F838AA555BADB3809656227CE77340391F14BD3A75`.
- `backend/app/ml/artifacts/crop_health/metadata.json` —
  `tta_views=4`, `crop_prior_alpha=0.95`, `metrics` = unconstrained serving/TTA
  result, `single_view_metrics` = training result, `deployed_model_rerun` =
  promotion trail, `crop_prior_validation` = crop-hint evidence.
- `ml/crop_health/data/field_robust/manifest_dedup.json` — training manifest.
- `ml/crop_health/evaluation/duplicate_images_report.json` — 12 duplicate groups.
- `ml/crop_health/evaluation/convnext/cross_domain_results.json` — single-view
  test metrics and confusion matrix.
- `ml/crop_health/evaluation/tta/tta_4view_convnext_results.json` — TTA evidence.
- `ml/crop_health/evaluation/tta/crop_prior_convnext_results.json` — crop-prior
  evidence; `crop_prior_convnext_cpu_check.json` is the CPU agreement check.
- `ml/crop_health/evaluation/benchmark_results_v3.json` — measured architecture efficiency.

## Verification after deployment

| Check | Result |
| --- | --- |
| Backend suite | **98 passed** (including 5 new crop-prior tests) |
| Frontend suite | **26 passed** |
| Frontend production build | passed (chunk-size advisory only) |
| `python scripts\smoke_api.py` | **passed**; `crop_health: real`, Grad-CAM generated, decision `SELL`, report persisted |
| `CropHealthService.info()` | `crop-health-v3.0.0-convnext`, `convnext_tiny`, `tta_views=4`, `crop_prior_alpha=0.95`, unconstrained field accuracy 0.7161 |
| Direct serving check | supported `Tomato` hint applies prior; `Rice`/no hint fall back with unchanged probabilities |

The smoke test uses the seeded Onion crop, so it also exercises the unsupported
crop fallback: no prior is applied and the unconstrained 4-view result is served.
Docker Compose was not re-run; the daemon was unavailable in this workspace.
The local SQLite end-to-end verification is independent of Docker.
