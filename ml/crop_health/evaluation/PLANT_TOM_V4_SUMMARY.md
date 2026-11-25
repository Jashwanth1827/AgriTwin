# PlantTom v4 experiment summary

Date: 2026-11-25
Source: PlantTom, CC BY 4.0, Vaskor Mostafa, Hugging Face.
Full provenance: `ml/crop_health/data/external/planttom/SOURCE.md`.

The goal was to add more real leaf images and retrain without changing the
38-class output space or weakening the deployed model. The held-out test set was
never changed: all 502 test entries in `manifest_planttom.json` and
`manifest_planttom_balanced.json` are byte-for-byte identical to
`manifest_dedup.json`, including the 236 PlantDoc field images.

## Candidates

| Candidate | Training data | Single-view field | 4-view TTA field | Lab TTA | Decision |
| --- | --- | ---: | ---: | ---: | --- |
| `crop-health-v4.0.0-planttom` | 5,305 PlantTom images, fresh ImageNet init | 0.6695 | 0.6864 | 0.9887 | Rejected |
| `crop-health-v4.1.0-planttom-balanced` | 800 PlantTom images, fresh init, field val, smoothing 0.1 | 0.6610 | 0.6695 | 0.9774 | Rejected |
| `crop-health-v4.2.0-planttom-continued` | 800 PlantTom images, continued from v3 at lr 1e-5 | 0.6907 | 0.6864 | 0.9774 | Rejected |
| Deployed `crop-health-v3.0.0-convnext` | no PlantTom | 0.6907 | **0.7161** | 0.9812 | Current |

## Decision

No candidate beat the strict `0.7161` unconstrained field-accuracy gate. The
deployed model was not changed:

- version: `crop-health-v3.0.0-convnext`
- `model.pt` bytes: `111452123`
- SHA-256: `4500C4FF14C99D3E7AFEC2F838AA555BADB3809656227CE77340391F14BD3A75`

## Why this is a negative but useful result

Adding many tomato-only images changed the class balance and hurt categories such
as Tomato mosaic virus, Tomato early blight and Potato early blight. Capping the
new images and continuing from the deployed checkpoint restored single-view
parity, but TTA still reduced field accuracy. The field gap is therefore not
solved by more tomato images alone; future data should provide labelled field
images for unsupported crops and under-performing classes.

## Files

- `planttom/V4_REJECTION.md`
- `planttom/tta_4view_v4_results.json`
- `planttom_balanced/V4_1_REJECTION.md`
- `planttom_balanced/tta_4view_v4_balanced_results.json`
- `planttom_continued/V4_2_REJECTION.md`
- `planttom_continued/tta_4view_v4_continued_results.json`
- `planttom_dedupe_report.json`
- `planttom_dedupe_balanced_report.json`
