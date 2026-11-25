"""Excess-green (ExG) background suppression, shared by training and serving.

Origin
------
Adapted from the ReVit crop/weed segmentation project, where an ExG gate
``sigmoid(2G - R - B)`` suppresses soil and highlights plant tissue. AgriTwin's
failure mode on field/Google images is the opposite problem from the lab: the
classifier latches onto the background instead of the lesion. This transform
provides the same plant-vs-background prior as an *optional preprocessing step*.

Design notes
------------
* Applied to raw 8-bit RGB (before ImageNet normalization). Computing ExG on
  normalized tensors, as the original ReVit notebook did, weakens the prior.
* ``strength`` blends the suppression so brown lesions are not erased outright —
  disease symptoms are frequently non-green, so aggressive suppression can hurt.
  The correct value is a hyperparameter to be decided by the ablation, not assumed.
* Pure numpy/PIL, no torch dependency, so the inference service can import it.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from PIL import Image

# Mean RGB of the ImageNet normalization in 0-255 space (0.485, 0.456, 0.406)*255.
IMAGENET_MEAN_RGB = (124.0, 116.0, 104.0)


class ExGBackgroundSuppression:
    """Blend non-green pixels toward the dataset mean, preserving green tissue.

    This is a stateless transform: ``image -> Image.Image``. It can be inserted
    anywhere in a torchvision ``Compose`` before ``ToTensor``.
    """

    def __init__(
        self,
        strength: float = 0.8,
        gain: float = 4.0,
        neutral: Sequence[float] = IMAGENET_MEAN_RGB,
    ) -> None:
        if not 0.0 <= strength <= 1.0:
            raise ValueError("strength must be in [0, 1]")
        self.strength = float(strength)
        self.gain = float(gain)
        self.neutral = np.asarray(neutral, dtype=np.float32).reshape(1, 1, 3)

    def __call__(self, image: Image.Image) -> Image.Image:
        if not isinstance(image, Image.Image):
            return image
        if image.mode != "RGB":
            image = image.convert("RGB")
        array = np.asarray(image, dtype=np.float32)
        red, green, blue = array[..., 0], array[..., 1], array[..., 2]

        # ExG index scaled back to roughly [-1, 2] for an 8-bit image.
        excess_green = (2.0 * green - red - blue) / 255.0
        alpha = 1.0 / (1.0 + np.exp(-self.gain * excess_green))
        alpha = self.strength * alpha + (1.0 - self.strength)
        alpha = alpha[..., None]

        blended = array * alpha + self.neutral * (1.0 - alpha)
        return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8), mode="RGB")

    def __repr__(self) -> str:
        return f"ExGBackgroundSuppression(strength={self.strength}, gain={self.gain})"
