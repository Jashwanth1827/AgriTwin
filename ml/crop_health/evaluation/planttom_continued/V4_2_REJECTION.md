# PlantTom v4.2 continued-training candidate — rejected

Candidate: `crop-health-v4.2.0-planttom-continued`
Artifact: `backend/app/ml/artifacts/crop_health_v4_continued`
Manifest: `ml/crop_health/data/field_robust/manifest_planttom_balanced.json`
Training: continued from deployed `crop-health-v3.0.0-convnext`, 6 requested
epochs (stopped at 3), lr `1e-5`, ConvNeXt-Tiny, seed 42, AMP, 192 px,
field-domain validation, 800 capped PlantTom images.

## Result on the unchanged 236-image PlantDoc field test

| Inference | Accuracy | Macro-F1 |
| --- | ---: | ---: |
| Deployed v3 single view | 0.6907 | 0.6833 |
| v4.2 single view | 0.6907 | 0.6789 |
| Deployed v3 4-view TTA | 0.7161 | 0.7093 |
| v4.2 4-view TTA | **0.6864** | see `tta_4view_v4_continued_results.json` |

Lab accuracy stayed at 0.9774. TTA slightly reduced field accuracy, so even the
single-view parity did not translate into a promotion.

## Decision

**Rejected.** Unconstrained 4-view field accuracy `0.6864` does not beat
`0.7161`. The deployed v3 artefact was not modified.

Evidence:
- `ml/crop_health/evaluation/planttom_continued/cross_domain_results.json`
- `ml/crop_health/evaluation/planttom_continued/tta_4view_v4_continued_results.json`
- `ml/crop_health/evaluation/planttom_dedupe_balanced_report.json`
