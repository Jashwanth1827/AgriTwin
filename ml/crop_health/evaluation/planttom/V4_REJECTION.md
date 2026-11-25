# PlantTom v4 candidate — rejected

Candidate: `crop-health-v4.0.0-planttom`
Artifact: `backend/app/ml/artifacts/crop_health_v4`
Manifest: `ml/crop_health/data/field_robust/manifest_planttom.json`
Training: ConvNeXt-Tiny, 12 epochs, mixed domain, 192 px, seed 42, AMP.
Added 5,305 deduplicated PlantTom train images for eight existing tomato classes.

## Result on the unchanged 236-image PlantDoc field test

| Inference | Accuracy | Macro-F1 |
| --- | ---: | ---: |
| Deployed v3 single view | 0.6907 | 0.6833 |
| v4 single view | 0.6695 | 0.5968 |
| Deployed v3 4-view TTA | 0.7161 | 0.7093 |
| v4 4-view TTA | **0.6864** | see `tta_4view_v4_results.json` |

Lab (PlantVillage) accuracy: 0.9887 single view and 0.9887 with 4-view TTA.

## Decision

**Rejected.** The promotion rule requires unconstrained 4-view field accuracy to
strictly exceed `0.7161`; v4 reached only `0.6864`. The deployed
`crop-health-v3.0.0-convnext` artefact was not modified.

The largest regressions were Tomato mosaic virus (-0.2885 macro-F1), Tomato early
blight (-0.2511), Potato early blight (-0.1282) and Tomato late blight (-0.1000).
Interpretation: 5,305 tomato-heavy images over-weighted the tomato label space and
did not transfer to the PlantDoc field distribution, despite improved validation F1.

Evidence:
- `ml/crop_health/evaluation/planttom/cross_domain_results.json`
- `ml/crop_health/evaluation/planttom/tta_4view_v4_results.json`
- `ml/crop_health/evaluation/planttom_dedupe_report.json`
