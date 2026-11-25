"""PlantVillage class metadata and safe, non-prescriptive agronomic advice.

The labels mirror the class mapping of the trained model.  Advice is limited to
inspection, monitoring, sanitation and "consult an expert" guidance.  No
pesticide product or dosage is recommended.
"""

from __future__ import annotations

import re
from typing import Any

CLASS_INFO: dict[str, dict[str, Any]] = {
    "Apple___Apple_scab": {
        "display": "Apple — Apple scab",
        "crop": "Apple",
        "severity": "moderate",
        "description": "A fungal leaf/fruit disease causing olive-green to dark velvety spots, often with yellowing around lesions.",
        "inspection": ["Check upper and lower leaf surfaces for velvety olive spots.", "Inspect fruit for corky scab lesions.", "Note whether lesions are spreading after rain."],
        "prevention": ["Remove and dispose of fallen infected leaves.", "Improve canopy airflow through pruning.", "Avoid overhead irrigation that prolongs leaf wetness."],
        "expert": "Consult a local horticulture extension officer if lesions are spreading on fruit.",
    },
    "Apple___Black_rot": {
        "display": "Apple — Black rot",
        "crop": "Apple",
        "severity": "high",
        "description": "A fungal disease producing brown leaf spots and firm, dark, concentric fruit rot.",
        "inspection": ["Look for brown leaf spots with dark margins.", "Inspect fruit for dark concentric rings.", "Check for cankers on branches."],
        "prevention": ["Prune out cankers and dead wood.", "Remove mummified fruit from the orchard.", "Maintain tree vigour and avoid wounding."],
        "expert": "Seek expert advice if cankers or fruit rot are widespread.",
    },
    "Apple___Cedar_apple_rust": {
        "display": "Apple — Cedar apple rust",
        "crop": "Apple",
        "severity": "moderate",
        "description": "A rust disease with bright yellow-orange spots on leaves; alternate host is juniper/cedar.",
        "inspection": ["Check for yellow-orange spots on leaves.", "Inspect nearby juniper for galls.", "Assess spread after wet weather."],
        "prevention": ["Reduce nearby juniper where practical.", "Improve airflow.", "Monitor new growth during wet periods."],
        "expert": "Consult an extension specialist for orchard-level rust management.",
    },
    "Apple___healthy": {"display": "Apple — healthy", "crop": "Apple", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting of leaves and fruit."], "prevention": ["Maintain balanced nutrition and orchard sanitation."], "expert": "No immediate expert consultation indicated by this image."},
    "Blueberry___healthy": {"display": "Blueberry — healthy", "crop": "Blueberry", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting."], "prevention": ["Maintain soil pH and irrigation appropriate for blueberries."], "expert": "No immediate expert consultation indicated by this image."},
    "Cherry_(including_sour)___Powdery_mildew": {
        "display": "Cherry — Powdery mildew",
        "crop": "Cherry",
        "severity": "moderate",
        "description": "A fungal disease producing white powdery growth on leaves and young shoots.",
        "inspection": ["Check leaf undersides for white powdery patches.", "Inspect new shoots for distortion.", "Assess canopy humidity."],
        "prevention": ["Improve airflow and avoid dense canopies.", "Avoid excessive nitrogen.", "Remove heavily affected shoots."],
        "expert": "Consult a horticulture advisor if powdery growth is widespread.",
    },
    "Cherry_(including_sour)___healthy": {"display": "Cherry — healthy", "crop": "Cherry", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting."], "prevention": ["Maintain orchard sanitation and balanced nutrition."], "expert": "No immediate expert consultation indicated by this image."},
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": {
        "display": "Maize — Cercospora / grey leaf spot",
        "crop": "Maize",
        "severity": "high",
        "description": "A fungal disease causing long, rectangular grey-brown lesions between leaf veins.",
        "inspection": ["Check lower leaves for rectangular lesions.", "Estimate the percentage of affected leaf area.", "Note progression after humid weather."],
        "prevention": ["Rotate away from maize for a season.", "Use resistant hybrids where available.", "Incorporate residue and improve field drainage."],
        "expert": "Consult an agronomist if lesions reach the upper canopy before grain filling.",
    },
    "Corn_(maize)___Common_rust_": {
        "display": "Maize — Common rust",
        "crop": "Maize",
        "severity": "moderate",
        "description": "A fungal disease with small reddish-brown pustules on both leaf surfaces.",
        "inspection": ["Look for raised rust-coloured pustules.", "Check whether pustules are on lower or upper leaves.", "Assess spread after cool, moist weather."],
        "prevention": ["Choose tolerant hybrids.", "Avoid excessive nitrogen.", "Monitor fields during cool, humid periods."],
        "expert": "Consult an agronomist if rust appears early and spreads rapidly.",
    },
    "Corn_(maize)___Northern_Leaf_Blight": {
        "display": "Maize — Northern leaf blight",
        "crop": "Maize",
        "severity": "high",
        "description": "A fungal disease producing long, cigar-shaped grey-green lesions on leaves.",
        "inspection": ["Check for cigar-shaped lesions on lower leaves.", "Estimate affected leaf area.", "Track progression towards the ear leaf."],
        "prevention": ["Rotate crops and manage residue.", "Use resistant hybrids.", "Avoid dense planting and improve airflow."],
        "expert": "Consult an agronomist if the disease reaches the ear leaf early.",
    },
    "Corn_(maize)___healthy": {"display": "Maize — healthy", "crop": "Maize", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting, especially after rain."], "prevention": ["Maintain balanced nutrition and weed control."], "expert": "No immediate expert consultation indicated by this image."},
    "Grape___Black_rot": {
        "display": "Grape — Black rot",
        "crop": "Grape",
        "severity": "high",
        "description": "A fungal disease causing brown leaf lesions and shrivelled black fruit.",
        "inspection": ["Inspect leaves for brown spots with dark borders.", "Check berries for black shrivelling.", "Look for mummified berries on the vine."],
        "prevention": ["Remove mummified fruit and infected canes.", "Improve canopy airflow.", "Keep foliage dry where possible."],
        "expert": "Consult a viticulture advisor if fruit symptoms are present.",
    },
    "Grape___Esca_(Black_Measles)": {
        "display": "Grape — Esca (black measles)",
        "crop": "Grape",
        "severity": "high",
        "description": "A wood disease complex associated with leaf tiger-striping and fruit spotting.",
        "inspection": ["Check leaves for interveinal chlorosis/tiger stripes.", "Inspect fruit for dark spotting.", "Look for declining vines or dieback."],
        "prevention": ["Avoid pruning wounds during wet weather.", "Remove severely affected vines under expert guidance.", "Sanitise pruning tools."],
        "expert": "Esca is a wood disease; consult a viticulture specialist before removal decisions.",
    },
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": {
        "display": "Grape — Leaf blight (Isariopsis leaf spot)",
        "crop": "Grape",
        "severity": "moderate",
        "description": "A fungal leaf spot disease causing brown lesions and premature defoliation.",
        "inspection": ["Check for brown angular leaf spots.", "Assess defoliation in the lower canopy.", "Monitor after humid weather."],
        "prevention": ["Remove fallen leaves.", "Improve airflow and avoid overhead irrigation.", "Maintain vine vigour."],
        "expert": "Consult a viticulture advisor if defoliation is significant.",
    },
    "Grape___healthy": {"display": "Grape — healthy", "crop": "Grape", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting."], "prevention": ["Maintain canopy management and vineyard sanitation."], "expert": "No immediate expert consultation indicated by this image."},
    "Orange___Haunglongbing_(Citrus_greening)": {
        "display": "Orange — Huanglongbing (citrus greening)",
        "crop": "Orange",
        "severity": "high",
        "description": "A bacterial disease spread by psyllids, causing blotchy mottle, yellow shoots and misshapen fruit.",
        "inspection": ["Check for asymmetrical blotchy leaf mottle.", "Look for yellow shoots and lopsided fruit.", "Inspect for psyllid activity."],
        "prevention": ["Use certified disease-free planting material.", "Manage psyllid vectors with expert guidance.", "Remove confirmed infected trees under official advice."],
        "expert": "Citrus greening is serious and regulated in many areas; contact the local horticulture authority promptly.",
    },
    "Peach___Bacterial_spot": {
        "display": "Peach — Bacterial spot",
        "crop": "Peach",
        "severity": "moderate",
        "description": "A bacterial disease causing small water-soaked leaf spots and fruit blemishes.",
        "inspection": ["Check leaves for small dark angular spots.", "Inspect fruit for pitted blemishes.", "Note spread after wind-driven rain."],
        "prevention": ["Use resistant varieties where available.", "Avoid overhead irrigation.", "Remove infected twigs and fallen leaves."],
        "expert": "Consult a horticulture advisor if fruit blemishes affect marketability.",
    },
    "Peach___healthy": {"display": "Peach — healthy", "crop": "Peach", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting."], "prevention": ["Maintain orchard sanitation and balanced nutrition."], "expert": "No immediate expert consultation indicated by this image."},
    "Pepper,_bell___Bacterial_spot": {
        "display": "Bell pepper — Bacterial spot",
        "crop": "Pepper",
        "severity": "moderate",
        "description": "A bacterial disease causing water-soaked leaf spots that turn brown, and scabby fruit lesions.",
        "inspection": ["Check leaves for small dark water-soaked spots.", "Inspect fruit for scabby lesions.", "Assess spread after rain."],
        "prevention": ["Rotate away from solanaceous crops.", "Use clean seed/transplants.", "Avoid working in wet fields."],
        "expert": "Consult an extension officer if fruit lesions are widespread.",
    },
    "Pepper,_bell___healthy": {"display": "Bell pepper — healthy", "crop": "Pepper", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting."], "prevention": ["Maintain sanitation and balanced irrigation."], "expert": "No immediate expert consultation indicated by this image."},
    "Potato___Early_blight": {
        "display": "Potato — Early blight",
        "crop": "Potato",
        "severity": "moderate",
        "description": "A fungal disease with dark brown lesions showing concentric rings, usually on older leaves.",
        "inspection": ["Check lower leaves for target-like brown lesions.", "Estimate defoliation.", "Monitor after warm, humid weather."],
        "prevention": ["Rotate crops and remove infected residue.", "Maintain balanced nitrogen.", "Avoid prolonged leaf wetness."],
        "expert": "Consult an agronomist if lesions are spreading rapidly before tuber bulking.",
    },
    "Potato___Late_blight": {
        "display": "Potato — Late blight",
        "crop": "Potato",
        "severity": "high",
        "description": "A fast-spreading oomycete disease causing water-soaked grey-green lesions and white mould in humid conditions.",
        "inspection": ["Check for dark water-soaked leaf lesions.", "Inspect leaf undersides for white mould in humid weather.", "Look for rapid collapse of foliage."],
        "prevention": ["Use certified seed potatoes.", "Avoid overhead irrigation and dense canopies.", "Remove infected plants promptly and monitor neighbours."],
        "expert": "Late blight can devastate a crop quickly; contact an agronomist or extension officer immediately.",
    },
    "Potato___healthy": {"display": "Potato — healthy", "crop": "Potato", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting, especially in humid weather."], "prevention": ["Use certified seed and maintain field sanitation."], "expert": "No immediate expert consultation indicated by this image."},
    "Raspberry___healthy": {"display": "Raspberry — healthy", "crop": "Raspberry", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting."], "prevention": ["Maintain airflow and cane sanitation."], "expert": "No immediate expert consultation indicated by this image."},
    "Soybean___healthy": {"display": "Soyabean — healthy", "crop": "Soyabean", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting."], "prevention": ["Maintain rotation and balanced nutrition."], "expert": "No immediate expert consultation indicated by this image."},
    "Squash___Powdery_mildew": {
        "display": "Squash — Powdery mildew",
        "crop": "Squash",
        "severity": "moderate",
        "description": "A fungal disease producing white powdery patches on leaves and stems.",
        "inspection": ["Check leaf surfaces for white powdery growth.", "Assess spread from older to younger leaves.", "Note canopy humidity."],
        "prevention": ["Improve airflow and spacing.", "Avoid excessive nitrogen.", "Remove heavily affected leaves."],
        "expert": "Consult an extension officer if powdery growth covers most of the canopy.",
    },
    "Strawberry___Leaf_scorch": {
        "display": "Strawberry — Leaf scorch",
        "crop": "Strawberry",
        "severity": "moderate",
        "description": "A fungal disease causing dark purple spots that enlarge and give leaves a scorched appearance.",
        "inspection": ["Check older leaves for purple-brown spots.", "Assess leaf edge scorching.", "Monitor after wet weather."],
        "prevention": ["Remove infected leaves.", "Improve airflow and avoid overhead irrigation.", "Rotate planting beds."],
        "expert": "Consult a horticulture advisor if symptoms spread to new leaves.",
    },
    "Strawberry___healthy": {"display": "Strawberry — healthy", "crop": "Strawberry", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting."], "prevention": ["Maintain bed sanitation and balanced irrigation."], "expert": "No immediate expert consultation indicated by this image."},
    "Tomato___Bacterial_spot": {
        "display": "Tomato — Bacterial spot",
        "crop": "Tomato",
        "severity": "moderate",
        "description": "A bacterial disease causing small dark water-soaked spots on leaves and scabby fruit lesions.",
        "inspection": ["Check leaves for small dark spots with yellow halos.", "Inspect fruit for raised scabby spots.", "Assess spread after rain."],
        "prevention": ["Use clean seed and transplants.", "Rotate away from solanaceous crops.", "Avoid handling plants when wet."],
        "expert": "Consult an extension officer if fruit symptoms are widespread.",
    },
    "Tomato___Early_blight": {
        "display": "Tomato — Early blight",
        "crop": "Tomato",
        "severity": "moderate",
        "description": "A fungal disease with brown concentric-ring lesions on older leaves and stem cankers.",
        "inspection": ["Check lower leaves for target-like lesions.", "Inspect stems for dark cankers.", "Estimate defoliation."],
        "prevention": ["Mulch to reduce soil splash.", "Remove infected lower leaves.", "Rotate crops and stake plants for airflow."],
        "expert": "Consult an agronomist if lesions spread to upper leaves or fruit.",
    },
    "Tomato___Late_blight": {
        "display": "Tomato — Late blight",
        "crop": "Tomato",
        "severity": "high",
        "description": "A fast-spreading oomycete disease causing water-soaked lesions, white mould and rapid fruit rot.",
        "inspection": ["Check for dark water-soaked lesions on leaves and stems.", "Inspect undersides for white mould in humid weather.", "Look for rapid collapse."],
        "prevention": ["Improve airflow and avoid overhead irrigation.", "Remove infected plants promptly.", "Avoid dense planting."],
        "expert": "Contact an agronomist or extension officer immediately; late blight spreads very quickly.",
    },
    "Tomato___Leaf_Mold": {
        "display": "Tomato — Leaf mould",
        "crop": "Tomato",
        "severity": "moderate",
        "description": "A fungal disease favoured by high humidity, causing pale yellow leaf spots and olive-green mould underneath.",
        "inspection": ["Check upper leaves for pale yellow patches.", "Inspect leaf undersides for olive mould.", "Assess greenhouse humidity."],
        "prevention": ["Increase ventilation and reduce humidity.", "Avoid overhead watering.", "Remove affected leaves."],
        "expert": "Consult a protected-cultivation advisor if mould recurs.",
    },
    "Tomato___Septoria_leaf_spot": {
        "display": "Tomato — Septoria leaf spot",
        "crop": "Tomato",
        "severity": "moderate",
        "description": "A fungal disease causing many small circular spots with grey centres and dark margins.",
        "inspection": ["Check lower leaves for small spots with pale centres.", "Estimate defoliation.", "Look for spread after rain splash."],
        "prevention": ["Mulch and remove infected leaves.", "Stake plants and improve airflow.", "Rotate crops."],
        "expert": "Consult an agronomist if defoliation is severe.",
    },
    "Tomato___Spider_mites Two-spotted_spider_mite": {
        "display": "Tomato — Two-spotted spider mite",
        "crop": "Tomato",
        "severity": "moderate",
        "description": "A piercing-sucking pest causing stippling, bronzing and fine webbing, often in hot dry conditions.",
        "inspection": ["Check leaf undersides for mites and fine webbing.", "Look for yellow stippling on upper leaves.", "Check field margins first."],
        "prevention": ["Maintain adequate irrigation and avoid drought stress.", "Encourage natural predators.", "Remove heavily infested leaves."],
        "expert": "Consult an extension officer before using any acaricide; resistance is common.",
    },
    "Tomato___Target_Spot": {
        "display": "Tomato — Target spot",
        "crop": "Tomato",
        "severity": "moderate",
        "description": "A fungal disease with brown lesions that develop concentric rings on leaves and fruit.",
        "inspection": ["Check leaves for target-like lesions.", "Inspect fruit for sunken spots.", "Assess canopy humidity."],
        "prevention": ["Improve airflow and avoid overhead irrigation.", "Remove infected debris.", "Rotate crops."],
        "expert": "Consult an agronomist if fruit lesions appear.",
    },
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
        "display": "Tomato — Yellow leaf curl virus",
        "crop": "Tomato",
        "severity": "high",
        "description": "A whitefly-transmitted virus causing upward leaf curling, yellowing and stunted growth.",
        "inspection": ["Check for upward curling and yellowing of new leaves.", "Inspect for whiteflies.", "Look for stunted plants."],
        "prevention": ["Use virus-free transplants and tolerant varieties.", "Manage whitefly vectors with expert guidance.", "Remove severely affected plants."],
        "expert": "Viral diseases cannot be cured in the field; consult an extension officer for vector management.",
    },
    "Tomato___Tomato_mosaic_virus": {
        "display": "Tomato — Tomato mosaic virus",
        "crop": "Tomato",
        "severity": "high",
        "description": "A mechanically transmitted virus causing mottled light/dark green leaves and distorted growth.",
        "inspection": ["Check for mosaic mottling and leaf distortion.", "Compare new and old growth.", "Review hygiene practices."],
        "prevention": ["Use clean seed and tools.", "Wash hands/tools between plants.", "Remove infected plants."],
        "expert": "Consult an extension officer; virus management focuses on prevention and sanitation.",
    },
    "Tomato___healthy": {"display": "Tomato — healthy", "crop": "Tomato", "severity": "none", "description": "No disease pattern is visible in the image.", "inspection": ["Continue routine scouting of lower leaves."], "prevention": ["Maintain staking, mulching and balanced irrigation."], "expert": "No immediate expert consultation indicated by this image."},
}

SEVERITY_SCORE = {"none": 0.0, "low": 0.25, "moderate": 0.55, "high": 0.85}


def safe_slug(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", label)


def _normalise(label: str) -> str:
    """Collapse punctuation so sanitised dataset folder names still resolve.

    The PlantVillage archive stores names such as ``Cherry_(including_sour)``
    and ``Pepper,_bell``.  Dataset preparation sanitises those characters when
    creating folders, so a trained model can emit either spelling.  Matching on
    an alphanumeric-only key keeps the advisory text attached to both.
    """
    return re.sub(r"[^a-z0-9]+", "", label.lower())


_INFO_BY_NORMALISED: dict[str, dict[str, Any]] = {
    _normalise(name): info for name, info in CLASS_INFO.items()
}


def class_info(label: str) -> dict[str, Any] | None:
    return CLASS_INFO.get(label) or _INFO_BY_NORMALISED.get(_normalise(label))


def class_display(label: str) -> str:
    info = class_info(label)
    if info:
        return info["display"]
    crop, _, disease = label.partition("___")
    return f"{crop.replace('_', ' ').strip()} — {disease.replace('_', ' ').strip() or 'unknown'}"


def class_crop(label: str) -> str:
    info = class_info(label)
    if info:
        return info["crop"]
    crop = label.split("___")[0]
    crop = crop.replace("Corn_(maize)", "Maize").replace("Soybean", "Soyabean")
    return crop.replace("_", " ").strip()


_CROP_GROUPS = sorted({info["crop"] for info in CLASS_INFO.values()})
_CROP_GROUP_BY_KEY = {_normalise(crop): crop for crop in _CROP_GROUPS}
_CROP_ALIASES = {
    "corn": "Maize",
    "cornmaize": "Maize",
    "sweetcorn": "Maize",
    "chilli": "Pepper",
    "chili": "Pepper",
    "bellpepper": "Pepper",
    "capsicum": "Pepper",
    "soybean": "Soyabean",
}


def normalise_crop(value: str | None) -> str | None:
    """Map a farm crop name to a trained crop group, or ``None`` if unsupported."""
    if not value:
        return None
    key = _normalise(str(value))
    return _CROP_ALIASES.get(key) or _CROP_GROUP_BY_KEY.get(key)


def supported_crops() -> tuple[str, ...]:
    return tuple(_CROP_GROUPS)


def is_healthy(label: str) -> bool:
    return label.lower().endswith("healthy")


def severity_for(label: str) -> float:
    info = class_info(label) or {}
    return SEVERITY_SCORE.get(info.get("severity", "moderate"), 0.55)


def recommendation_bundle(label: str, confidence: float) -> list[dict[str, str]]:
    info = class_info(label)
    if not info:
        return [
            {
                "title": "Unrecognised class — inspect manually",
                "body": "The model returned a class without configured advisory text. Inspect the crop and consult a local agricultural extension officer.",
                "category": "general",
            }
        ]
    recs: list[dict[str, str]] = []
    recs.append(
        {
            "title": f"What this may be: {info['display']}",
            "body": info["description"],
            "category": "disease_information",
        }
    )
    for step in info["inspection"]:
        recs.append({"title": "Inspection step", "body": step, "category": "inspection"})
    for practice in info["prevention"]:
        recs.append({"title": "Preventive practice", "body": practice, "category": "prevention"})
    recs.append(
        {
            "title": "When to consult an expert",
            "body": info["expert"],
            "category": "expert_advice",
        }
    )
    if confidence < 0.6:
        recs.append(
            {
                "title": "Low model confidence",
                "body": "The image-based confidence is low. Capture additional clear photos of affected and healthy leaves, and do not treat this as a confirmed diagnosis.",
                "category": "uncertainty",
            }
        )
    recs.append(
        {
            "title": "Important limitation",
            "body": "This is an image-based screening result, not a laboratory diagnosis. It does not establish the biological cause and does not replace an agronomist's field inspection.",
            "category": "limitation",
        }
    )
    return recs
