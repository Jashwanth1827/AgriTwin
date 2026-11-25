"""Crop-conditioned inference tests."""

from __future__ import annotations

import torch

from app.ml.crop_health.labels import normalise_crop
from app.ml.crop_health.service import apply_crop_prior

CLASSES = [
    "Tomato___Early_blight",
    "Tomato___healthy",
    "Potato___Early_blight",
    "Apple___healthy",
]


def test_crop_aliases_map_to_trained_groups() -> None:
    assert normalise_crop("Tomato") == "Tomato"
    assert normalise_crop("Corn") == "Maize"
    assert normalise_crop("corn_(maize)") == "Maize"
    assert normalise_crop("Chilli") == "Pepper"
    assert normalise_crop("Bell pepper") == "Pepper"
    assert normalise_crop("Soybean") == "Soyabean"
    assert normalise_crop("Rice") is None
    assert normalise_crop(None) is None


def test_soft_crop_prior_reweights_toward_supported_classes() -> None:
    probabilities = torch.tensor([0.20, 0.10, 0.50, 0.20])

    adjusted, group, alpha = apply_crop_prior(probabilities, CLASSES, "Tomato", 0.95)

    assert group == "Tomato"
    assert alpha == 0.95
    assert int(adjusted.argmax()) == 0
    assert torch.isclose(adjusted.sum(), torch.tensor(1.0))
    assert torch.allclose(probabilities, torch.tensor([0.20, 0.10, 0.50, 0.20]))


def test_unsupported_hint_does_not_change_probabilities() -> None:
    probabilities = torch.tensor([0.20, 0.10, 0.50, 0.20])

    adjusted, group, alpha = apply_crop_prior(probabilities, CLASSES, "Rice", 0.95)

    assert group is None
    assert alpha == 0.0
    assert torch.allclose(adjusted, probabilities)


def test_zero_alpha_is_a_noop() -> None:
    probabilities = torch.tensor([0.20, 0.10, 0.50, 0.20])

    adjusted, group, alpha = apply_crop_prior(probabilities, CLASSES, "Tomato", 0.0)

    assert group is None
    assert alpha == 0.0
    assert torch.allclose(adjusted, probabilities)
