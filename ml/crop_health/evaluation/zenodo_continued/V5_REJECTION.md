# Zenodo v5 candidate — rejected

Candidate: `crop-health-v5.0.0-zenodo-continued`
Artifact: `backend/app/ml/artifacts/crop_health_v5_zenodo`
Manifest: `ml/crop_health/data/field_robust/manifest_zenodo_balanced.json`
Source: Zenodo Crop Health Monitoring Dataset, DOI `10.5281/zenodo.10628735`, CC BY 4.0.

Training: continued from deployed `crop-health-v3.0.0-convnext`, ConvNeXt-Tiny,
seed 42, AMP, 192 px, lr `5e-6`, 6 requested epochs (early stopped at 3),
field-domain validation, 1,558 deduplicated multi-crop images mapped into the
existing 38-class label space.

## Result on the unchanged 236-image PlantDoc field test

| Inference | Accuracy | Macro-F1 |
| --- | ---: | ---: |
| Deployed v3 single view | 0.6907 | 0.6833 |
| v5 single view | 0.6864 | 0.6788 |
| Deployed v3 4-view TTA | 0.7161 | 0.7093 |
| v5 4-view TTA | **0.6822** | see `tta_4view_v5_zenodo_results.json` |

Lab (PlantVillage) accuracy fell from `0.9774` to `0.9699` and did not recover
with TTA.

## Decision

**Rejected.** Unconstrained 4-view field accuracy `0.6822` does not beat the
`0.7161` promotion baseline. The deployed v3 artefact was not modified:

- version: `crop-health-v3.0.0-convnext`
- `model.pt` bytes: `111452123`
- SHA-256: `4500C4FF14C99D3E7AFEC2F838AA555BADB3809656227CE77340391F14BD3A75`

## Per-class observation

The largest field macro-F1 regressions were `Apple___healthy` (`-0.1378`),
`Cherry_including_sour___healthy` (`-0.1075`) and
`Tomato___Tomato_mosaic_virus` (`-0.0833`). Small gains included
`Peach___healthy` (`+0.0857`), `Tomato___Septoria_leaf_spot` (`+0.0468`) and
`Apple___Apple_scab` (`+0.0457`). These are single-split observations on a small
test set and do not justify promotion.

The likely cause is the same as for PlantTom: continued training on a new image
domain moved the decision boundary without adding enough in-the-wild field
examples to improve the PlantDoc protocol.

Evidence:
- `ml/crop_health/evaluation/zenodo_continued/cross_domain_results.json`
- `ml/crop_health/evaluation/zenodo_continued/tta_4view_v5_zenodo_results.json`
- `ml/crop_health/evaluation/zenodo_dedupe_report.json`
- `ml/crop_health/evaluation/zenodo_dedupe_balanced_report.json`
