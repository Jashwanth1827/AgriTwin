# PlantTom v4.1 candidate — rejected

Candidate: `crop-health-v4.1.0-planttom-balanced`
Artifact: `backend/app/ml/artifacts/crop_health_v4_balanced`
Manifest: `ml/crop_health/data/field_robust/manifest_planttom_balanced.json`
Training: ConvNeXt-Tiny from ImageNet, 12 epochs, seed 42, AMP, 192 px,
field-domain validation (`--val-domain pd`), label smoothing `0.1`.
Added 800 PlantTom images (100 per tomato class) after the same deduplication.

## Result on the unchanged 236-image PlantDoc field test

| Inference | Accuracy | Macro-F1 |
| --- | ---: | ---: |
| Deployed v3 single view | 0.6907 | 0.6833 |
| v4.1 single view | 0.6610 | 0.5879 |
| Deployed v3 4-view TTA | 0.7161 | 0.7093 |
| v4.1 4-view TTA | **0.6695** | see `tta_4view_v4_balanced_results.json` |

Lab (PlantVillage) accuracy: 0.9737 single view, 0.9774 with 4-view TTA.

## Decision

**Rejected.** Unconstrained 4-view field accuracy `0.6695` does not beat the
`0.7161` promotion baseline. The deployed v3 artefact was not modified.

Capping the tomato images reduced the over-weighting seen in v4, but training from
ImageNet still lost field performance. A final low-learning-rate continuation from
the deployed checkpoint is being evaluated separately.

Evidence:
- `ml/crop_health/evaluation/planttom_balanced/cross_domain_results.json`
- `ml/crop_health/evaluation/planttom_balanced/tta_4view_v4_balanced_results.json`
- `ml/crop_health/evaluation/planttom_dedupe_balanced_report.json`
