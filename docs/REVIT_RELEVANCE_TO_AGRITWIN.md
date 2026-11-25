# Is ReVit useful for AgriTwin?

**Short answer: the trained ReVit model is NOT reusable in AgriTwin, but three things
from ReVit ARE useful — and one of them is a genuine novelty for the AgriTwin paper.**

## Why the model itself cannot be dropped in

| Property | ReVit (`ExG_Attention_V4_0`) | AgriTwin (crop health) |
| --- | --- | --- |
| Task | Dense semantic **segmentation** | Whole-image **classification** |
| Input | UAV aerial field images (512 px) | Leaf close-ups / field leaf photos (192 px) |
| Output | Pixel mask, H×W×3 | One of 38 disease labels |
| Classes | Crop / Weed / Soil | 38 crop–disease combinations |
| Backbone | SegFormer-B2 (transformer) | ConvNeXt-Tiny (deployed); EfficientNet-B0 (historical study) |
| Weights | `custom_model_best.pth` (~106 MB) | separate `model.pt` |

A segmentation head predicts a class *per pixel*; a classifier predicts one class *per
image*. The number of output channels, the loss, and the label space are all different.
Loading ReVit weights into AgriTwin is impossible without discarding the entire decoder
and classifier — at which point nothing has been transferred. **Do not use ReVit weights
as initialization; the aerial-vs-leaf domain mismatch would likely hurt accuracy.**

The two projects also answer different research questions. ReVit's result (mIoU 0.8707,
"energy-efficient real-time" pruning) belongs in its own UAV paper. It is not evidence
for AgriTwin's disease-classification claims.

## What IS useful

### 1. ExG background suppression — the transferable novelty (recommended)

ReVit's best idea is the **ExG attention gate**: `sigmoid(2G − R − B)`, an excess-green
prior that suppresses soil and highlights plant tissue. AgriTwin's exact failure mode on
Google images is the model latching onto background (soil, table, sky) instead of the
lesion. The same prior can be moved across:

- **Training-time ExG-guided suppression** (no inference architecture change):
  for each training image compute `alpha = sigmoid(2G − R − B)`, then blend non-green
  pixels toward the ImageNet mean: `x' = alpha·x + (1−alpha)·mean`. The classifier is
  forced to use leaf texture, not background. Drop-in compatible — the deployed model
  stays a plain EfficientNet and the FastAPI service needs no change.
- Report it as a fifth ablation: `mixed` (the measured winner) vs `mixed + ExG suppression`.
  If field accuracy improves, that is a defensible, reproducible contribution linking the
  two works instead of two disconnected projects. If it does not improve, report the
  negative result — brown lesions are non-green and ExG can erase disease evidence.

Caveat from the ReVit notebook: ExG must be computed on **raw [0, 255] RGB**, not on
ImageNet-normalized pixels (the notebook computed it after normalization, which weakens
the prior). Implement it before normalization in the transform pipeline.

### 2. The research-engineering package (already applied to AgriTwin)

The clean ReVit scripts introduced a standard that AgriTwin now matches:

| Capability | ReVit research scripts | AgriTwin status |
| --- | --- | --- |
| Deterministic seed | ✅ | ✅ |
| Ablation matrix | full / no_exg / no_detail / vanilla | baseline / plantdoc_only / mixed / two_stage |
| Per-class metrics | per-class IoU | per-class precision/recall/F1 + confusion matrix |
| JSON results | `ablation_results.json` | `cross_domain_results.json` |
| Leakage-aware split | grouped by field/flight | official PlantDoc train/test kept separate |
| Mixed precision (AMP) | ✅ | ✅ **added** |
| Efficiency benchmark | params / FLOPs / FPS | ✅ **added** (`benchmark.py`: params, GFLOPs, latency, FPS, GPU memory) |
| Explainability | (none) | ✅ Grad-CAM figures |

### 3. System-level complementarity for the digital-twin story

AgriTwin can present both perception modules as one platform:

- **ReVit module** — "where are the crop plants and weeds?" (UAV, real-time, edge).
- **AgriTwin module** — "what disease does this crop leaf have?" (field/Google imagery).

That is a strong *systems* narrative for a college major project and can be described in
the paper's future-work / integration section. It does not require either model to share
weights. Keep the two papers separate; cross-cite them instead of merging results.

## Verdict

- **Reuse the trained ReVit model?** No — wrong task, output and label space.
- **Reuse its ExG idea?** Yes — best candidate for a new AgriTwin contribution.
- **Reuse its research code patterns?** Yes — benchmark, AMP and structured metrics
  are now in AgriTwin too.
- **Mention it in the paper?** Yes, as (a) a related-work/integration paragraph and
  (b) an ablation if ExG suppression is implemented and measured.

## Completed experiment (negative result)

The ExG suppression ablation was run with the joint (`mixed`) protocol on 2026-11-24.
It reached 0.9586 lab / **0.6483** field accuracy, below the then-deployed v2 checkpoint's
0.6780 field accuracy, so it was **rejected and not promoted** (data:
`ml/crop_health/evaluation/exg/cross_domain_results.json`). By construction ExG removes
non-green pixels, which discards the brown and necrotic tissue that carries lesion
evidence. The idea remains valuable in the complementary ReVit crop/weed task, where it
was originally validated; here it is only cross-cited as an honest negative result.

The paper's main contribution remains the uncertainty-aware decision system — the
cross-domain work is the evidence that its leaf-photo input is reliable (joint training
won both the historical EfficientNet-B0 study and the deployed ConvNeXt-Tiny v3 model;
two-stage fine-tuning underperformed on both domains).
