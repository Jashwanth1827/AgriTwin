"""Crop-health upload, inference and persistence."""

from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import DEMO_DATA_NOTICE
from app.core.errors import AppError, NotFoundError
from app.ml.crop_health.service import CropHealthService
from app.models.crop_health import (
    CropHealthPrediction,
    DiseaseClass,
    ModelVersion,
    Recommendation,
)
from app.models.farm import Crop, Farm, UploadedFile
from app.models.user import User

EXTENSION_BY_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def _service() -> CropHealthService:
    return CropHealthService.instance()


def model_info() -> dict:
    return _service().info()


def store_upload(
    db: Session,
    user: User,
    *,
    farm: Farm,
    crop: Crop,
    filename: str,
    content_type: str | None,
    content: bytes,
) -> UploadedFile:
    if not content:
        raise AppError("The uploaded file is empty", status_code=422)
    if len(content) > settings.max_upload_bytes:
        raise AppError(
            f"Image exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit",
            status_code=413,
            code="payload_too_large",
        )
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared and declared not in settings.allowed_image_mime:
        raise AppError(
            "Only JPEG, PNG and WebP images are accepted",
            status_code=415,
            code="unsupported_media_type",
        )
    try:
        with Image.open(io.BytesIO(content)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(content)) as probe:
            width, height = probe.size
            image_format = (probe.format or "").upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise AppError("The file is not a valid image", status_code=422) from exc
    if image_format not in EXTENSION_BY_FORMAT:
        raise AppError("Only JPEG, PNG and WebP images are accepted", status_code=415)
    if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
        raise AppError(
            f"Image dimensions exceed {settings.MAX_IMAGE_DIMENSION}px", status_code=422
        )
    if width < 32 or height < 32:
        raise AppError("Image is too small to analyse", status_code=422)

    digest = hashlib.sha256(content).hexdigest()
    existing = db.scalar(
        select(UploadedFile).where(
            UploadedFile.sha256 == digest, UploadedFile.user_id == user.id
        )
    )
    if existing is not None and (settings.UPLOAD_DIR / existing.stored_path).exists():
        return existing

    relative = Path(str(user.id)) / digest[:2] / f"{digest}{EXTENSION_BY_FORMAT[image_format]}"
    target = settings.UPLOAD_DIR / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    record = UploadedFile(
        user_id=user.id,
        farm_id=farm.id,
        crop_id=crop.id,
        original_name=(filename or "upload")[:255],
        stored_path=str(relative),
        mime_type=declared or f"image/{image_format.lower()}",
        size_bytes=len(content),
        sha256=digest,
        width=width,
        height=height,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _model_version(db: Session, version: str, info: dict) -> ModelVersion:
    existing = db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_type == "crop_health", ModelVersion.version == version
        )
    )
    if existing is not None:
        return existing
    row = ModelVersion(
        model_type="crop_health",
        version=version,
        artifact_path=str(settings.CROP_HEALTH_ARTIFACT_DIR),
        dataset_provenance=info.get("dataset_provenance"),
        metrics=info.get("metrics"),
        is_active=True,
        is_demo=info.get("mode") == "demo",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def predict(
    db: Session, user: User, *, farm: Farm, crop: Crop, upload: UploadedFile
) -> CropHealthPrediction:
    service = _service()
    source = settings.UPLOAD_DIR / upload.stored_path
    if not source.exists():
        raise NotFoundError("The stored image could not be found")
    output_dir = settings.UPLOAD_DIR / "gradcam" / str(user.id)
    stem = f"pred_{uuid.uuid4().hex[:12]}"
    try:
        result = service.predict(
            source,
            output_dir=output_dir,
            explanation_stem=stem,
            crop_hint=crop.crop_name,
        )
    except Exception as exc:
        raise AppError(
            f"Crop-health inference failed: {exc}",
            status_code=503,
            code="inference_failed",
        ) from exc

    gradcam_relative: str | None = None
    if result.get("gradcam_path"):
        try:
            gradcam_relative = str(Path(result["gradcam_path"]).relative_to(settings.UPLOAD_DIR))
        except ValueError:
            gradcam_relative = result["gradcam_path"]

    info = service.info()
    version_row = _model_version(db, str(result["model_version"]), info)
    notes = result.get("notes") or ""
    if result["crop"].lower() != crop.crop_name.lower():
        mismatch = (
            f"The image was analysed against the selected crop '{crop.crop_name}', but the "
            f"model's best match is '{result['crop']}'. Confirm that the photo and crop "
            "selection are correct."
        )
        notes = f"{notes} {mismatch}".strip()
    if result.get("model_mode") == "demo":
        notes = f"{notes} {DEMO_DATA_NOTICE}".strip()

    prediction = CropHealthPrediction(
        user_id=user.id,
        farm_id=farm.id,
        crop_id=crop.id,
        file_id=upload.id,
        model_version_id=version_row.id,
        predicted_label=result["label"],
        predicted_crop=result["crop"],
        is_healthy=bool(result["is_healthy"]),
        confidence=float(result["confidence"]),
        severity=float(result["severity"]),
        probabilities=result["probabilities"],
        gradcam_path=gradcam_relative,
        inference_ms=float(result["inference_ms"]),
        model_version=str(result["model_version"]),
        model_mode=result["model_mode"],
        is_demo=bool(result["is_demo"]),
        notes=notes or None,
        predicted_at=datetime.now(timezone.utc),
    )
    db.add(prediction)
    db.flush()
    for item in result["recommendations"]:
        db.add(
            Recommendation(
                prediction_id=prediction.id,
                title=item["title"][:200],
                body=item["body"],
                category=item["category"],
                source="agritwin_rules",
            )
        )
    db.commit()
    db.refresh(prediction)
    return prediction


def list_predictions(
    db: Session, user: User, *, farm_id: int | None = None, crop_id: int | None = None
) -> list[CropHealthPrediction]:
    query = select(CropHealthPrediction).where(CropHealthPrediction.user_id == user.id)
    if farm_id is not None:
        query = query.where(CropHealthPrediction.farm_id == farm_id)
    if crop_id is not None:
        query = query.where(CropHealthPrediction.crop_id == crop_id)
    return list(db.scalars(query.order_by(CropHealthPrediction.predicted_at.desc())))


def get_prediction(db: Session, user: User, prediction_id: int) -> CropHealthPrediction:
    prediction = db.get(CropHealthPrediction, prediction_id)
    if prediction is None or prediction.user_id != user.id:
        raise NotFoundError("Crop-health prediction not found")
    return prediction


def latest_for_crop(db: Session, user: User, crop_id: int) -> CropHealthPrediction | None:
    return db.scalar(
        select(CropHealthPrediction)
        .where(
            CropHealthPrediction.user_id == user.id,
            CropHealthPrediction.crop_id == crop_id,
        )
        .order_by(CropHealthPrediction.predicted_at.desc())
        .limit(1)
    )


def delete_prediction(db: Session, prediction: CropHealthPrediction) -> None:
    db.delete(prediction)
    db.commit()


def disease_classes(db: Session) -> list[DiseaseClass]:
    return list(db.scalars(select(DiseaseClass).order_by(DiseaseClass.crop, DiseaseClass.name)))
