"""Regression coverage for every architecture the crop-health service can load."""

from __future__ import annotations

import pytest
import torch
from PIL import Image

from app.ml.crop_health.gradcam import resolve_target_layer
from app.ml.crop_health.service import (
    build_architecture,
    tta_probabilities,
    tta_view_probabilities,
)

SUPPORTED = (
    "efficientnet_b0",
    "efficientnet_b3",
    "efficientnet_v2_s",
    "resnet50",
    "mobilenet_v3_large",
    "convnext_tiny",
    "convnext_small",
)


@pytest.mark.parametrize("architecture", SUPPORTED)
def test_build_architecture_head_has_38_outputs(architecture: str) -> None:
    model = build_architecture(architecture, 38).eval()
    assert model(torch.zeros(2, 3, 64, 64)).shape == (2, 38)


@pytest.mark.parametrize("architecture", SUPPORTED)
def test_gradcam_target_layer_is_available(architecture: str) -> None:
    model = build_architecture(architecture, 38)
    target = resolve_target_layer(model, architecture)
    assert isinstance(target, torch.nn.Module)


class CountingModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        self.calls += tensor.shape[0]
        return torch.tensor([[1.0, 2.0, 0.5]]).repeat(tensor.shape[0], 1)


@pytest.mark.parametrize(("views", "expected"), [(1, 1), (2, 2), (4, 4)])
def test_tta_helper_uses_the_measured_view_grid(views: int, expected: int) -> None:
    model = CountingModel()
    meta = {"input_size": 32, "resize_size": 40}
    image = Image.new("RGB", (80, 80), (120, 160, 90))

    probabilities, base_tensor = tta_probabilities(model, meta, image, views)

    assert model.calls == expected
    assert probabilities.shape == (3,)
    assert base_tensor.shape == (3, 32, 32)
    per_view, _ = tta_view_probabilities(CountingModel(), meta, image, views)
    assert len(per_view) == expected
