# AgriTwin — datasets, labels and real-photo behaviour

This is the practical reference for what the crop-health model was trained on, what it can
predict, and what happens when you give it a Google image or a photo taken in a farm.

---

## 1. Datasets used

| Dataset | Role | Images used | Classes | Licence / source |
| --- | --- | --- | --- | --- |
| **PlantVillage subset** | Controlled lab images; teaches disease semantics | 1,900 (1,368 train / 266 val / 266 test) | 38 | Public research dataset, `Hemg/new-plant-diseases-dataset` on Hugging Face |
| **PlantDoc** | In-the-wild internet/field images; exposes and fixes the lab→field gap | 2,572 recovered (1,998 train / 338 val / 236 official test) | 28 folders mapped onto the same 38 labels | **CC BY 4.0**, `github.com/pratikkayal/PlantDoc-Dataset`, Singh et al. 2020 |
| **PlantTom** | Additional field/Roboflow tomato-leaf examples for existing tomato labels | 5,305 accepted from its `train` split | 8 of the 38 | **CC BY 4.0**, Vaskor Mostafa, `huggingface.co/datasets/vaskormostafa/PlantTom` |
| **Your web / farm images** | Optional external domain; ad-hoc photos are test-only unless separately licensed and manifested | as many as you add | must use the exact 38 folder names below | your own photos |

The v3 deterministic split lives in `ml/crop_health/data/field_robust/manifest_dedup.json`
(4,460 leakage-free entries). The v4 candidate adds PlantTom training images through
`manifest_planttom.json` (9,765 entries) but keeps all 502 official test entries byte-for-byte
identical. PlantTom's own validation/test splits were not used. Its train images were filtered
for ambiguous labels, byte-identical copies and perceptual near-duplicates of the held-out set;
see `ml/crop_health/evaluation/planttom_dedupe_report.json` and
`ml/crop_health/data/external/planttom/SOURCE.md`.

The official PlantDoc `test/` folder is kept completely separate — no test image influences
training or model selection. Six PlantDoc files with Windows-illegal characters in their names
could not be stored; all 28 classes and both splits are intact.

**Why both datasets:** PlantVillage alone scores ~95% in the lab but only ~32% on PlantDoc.
Joint training (the deployed model) keeps ~95% in the lab and reaches ~68% on real photos.

---

## 2. The 38 output labels (exact order)

The order below is the model's index order and must never change. It is stored in
`backend/app/ml/artifacts/crop_health/metadata.json` and read by the serving code at startup.

| Index | Label | Crop | Condition |
| ---: | --- | --- | --- |
| 0 | `Apple___Apple_scab` | Apple | Apple scab |
| 1 | `Apple___Black_rot` | Apple | Black rot |
| 2 | `Apple___Cedar_apple_rust` | Apple | Cedar apple rust |
| 3 | `Apple___healthy` | Apple | Healthy |
| 4 | `Blueberry___healthy` | Blueberry | Healthy |
| 5 | `Cherry_including_sour___healthy` | Cherry | Healthy |
| 6 | `Cherry_including_sour___Powdery_mildew` | Cherry | Powdery mildew |
| 7 | `Corn_maize___Cercospora_leaf_spot_Gray_leaf_spot` | Maize | Gray leaf spot |
| 8 | `Corn_maize___Common_rust_` | Maize | Common rust |
| 9 | `Corn_maize___healthy` | Maize | Healthy |
| 10 | `Corn_maize___Northern_Leaf_Blight` | Maize | Northern leaf blight |
| 11 | `Grape___Black_rot` | Grape | Black rot |
| 12 | `Grape___Esca_Black_Measles` | Grape | Esca (black measles) |
| 13 | `Grape___healthy` | Grape | Healthy |
| 14 | `Grape___Leaf_blight_Isariopsis_Leaf_Spot` | Grape | Isariopsis leaf spot |
| 15 | `Orange___Haunglongbing_Citrus_greening` | Orange | Huanglongbing (citrus greening) |
| 16 | `Peach___Bacterial_spot` | Peach | Bacterial spot |
| 17 | `Peach___healthy` | Peach | Healthy |
| 18 | `Pepper_bell___Bacterial_spot` | Bell pepper | Bacterial spot |
| 19 | `Pepper_bell___healthy` | Bell pepper | Healthy |
| 20 | `Potato___Early_blight` | Potato | Early blight |
| 21 | `Potato___healthy` | Potato | Healthy |
| 22 | `Potato___Late_blight` | Potato | Late blight |
| 23 | `Raspberry___healthy` | Raspberry | Healthy |
| 24 | `Soybean___healthy` | Soybean | Healthy |
| 25 | `Squash___Powdery_mildew` | Squash | Powdery mildew |
| 26 | `Strawberry___healthy` | Strawberry | Healthy |
| 27 | `Strawberry___Leaf_scorch` | Strawberry | Leaf scorch |
| 28 | `Tomato___Bacterial_spot` | Tomato | Bacterial spot |
| 29 | `Tomato___Early_blight` | Tomato | Early blight |
| 30 | `Tomato___healthy` | Tomato | Healthy |
| 31 | `Tomato___Late_blight` | Tomato | Late blight |
| 32 | `Tomato___Leaf_Mold` | Tomato | Leaf mold |
| 33 | `Tomato___Septoria_leaf_spot` | Tomato | Septoria leaf spot |
| 34 | `Tomato___Spider_mites_Two-spotted_spider_mite` | Tomato | Spider mites |
| 35 | `Tomato___Target_Spot` | Tomato | Target spot |
| 36 | `Tomato___Tomato_mosaic_virus` | Tomato | Mosaic virus |
| 37 | `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | Tomato | Yellow leaf curl virus |

**Important limitation:** 14 crop species are covered. A photo of an unsupported crop is still
forced into one of these 38 labels — the service reports this as screening support, not a
diagnosis, and the decision engine can route low-confidence results to INSPECT.

### PlantDoc folder → label mapping (28 folders)

`Apple Scab Leaf → Apple___Apple_scab`, `Apple leaf → Apple___healthy`,
`Apple rust leaf → Apple___Cedar_apple_rust`,
`Bell_pepper leaf spot → Pepper_bell___Bacterial_spot`, `Bell_pepper leaf → Pepper_bell___healthy`,
`Blueberry leaf → Blueberry___healthy`, `Cherry leaf → Cherry_including_sour___healthy`,
`Corn Gray leaf spot → Corn_maize___Cercospora_leaf_spot_Gray_leaf_spot`,
`Corn leaf blight → Corn_maize___Northern_Leaf_Blight`, `Corn rust leaf → Corn_maize___Common_rust_`,
`Peach leaf → Peach___healthy`, `Potato leaf early blight → Potato___Early_blight`,
`Potato leaf late blight → Potato___Late_blight`, `Raspberry leaf → Raspberry___healthy`,
`Soyabean leaf → Soybean___healthy`, `Squash Powdery mildew leaf → Squash___Powdery_mildew`,
`Strawberry leaf → Strawberry___healthy`,
`Tomato Early blight leaf → Tomato___Early_blight`,
`Tomato Septoria leaf spot → Tomato___Septoria_leaf_spot`,
`Tomato leaf bacterial spot → Tomato___Bacterial_spot`,
`Tomato leaf late blight → Tomato___Late_blight`,
`Tomato leaf mosaic virus → Tomato___Tomato_mosaic_virus`,
`Tomato leaf yellow virus → Tomato___Tomato_Yellow_Leaf_Curl_Virus`,
`Tomato leaf → Tomato___healthy`, `Tomato mold leaf → Tomato___Leaf_Mold`,
`Tomato two spotted spider mites leaf → Tomato___Spider_mites_Two-spotted_spider_mite`,
`grape leaf black rot → Grape___Black_rot`, `grape leaf → Grape___healthy`.

---

## 3. What happens with a Google image or a farm photo

1. The image is validated (MIME, ≤8 MB, ≤4096 px) and decoded.
2. The deployed ConvNeXt-Tiny (4-view TTA) predicts one of the 38 labels and a **confidence**.
3. A **Grad-CAM overlay** is generated so you can see which part of the image drove the decision.
4. The confidence flows into the decision engine:
   - `confidence ≥ 0.55` → prediction is weighted into the risk score normally.
   - `confidence < 0.55` → the detection is discounted and the **INSPECT** rule can trigger,
     telling the user to verify manually rather than acting on a shaky prediction.
   - Low confidence, unknown crop, or an abiotic-stress lookalike are exactly the cases where
     the system is designed to say "I am not sure".

This is why cross-domain validation matters: a model that is confidently wrong on real photos
would defeat the uncertainty-aware decision system. The deployed joint-trained model is the one
that keeps the leaf-photo input reliable enough to fuse.

### Test your own images

```powershell
# One photo
python ml/crop_health/evaluation/test_my_images.py --image "C:\path\to\photo.jpg"

# A folder of Google/farm photos, with a CSV report and Grad-CAM overlays
python ml/crop_health/evaluation/test_my_images.py `
  --images "C:\path\to\my_photos" `
  --out ml/crop_health/evaluation/my_results.csv `
  --gradcam-dir ml/crop_health/evaluation/my_gradcam
```

To add them as a formal external test domain for the manifest, put them in class folders named
exactly as in the table above:

```
ml/crop_health/data/web_images/Tomato___Early_blight/IMG_001.jpg
ml/crop_health/data/web_images/Tomato___healthy/IMG_002.jpg
...
python ml/crop_health/training/prepare_field_dataset.py --plantdoc-dir ml/crop_health/data/plantdoc --web-dir ml/crop_health/data/web_images
```

Web images are **test-only** — they never enter training or early stopping.
