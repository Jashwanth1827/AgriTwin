"""Train a field-robust AgriTwin crop-health model and measure the lab-to-field gap.

This is the research-grade replacement for ``train.py``. It uses the manifest produced
by ``prepare_field_dataset.py`` and runs controlled cross-domain experiments so the
paper can report *honest* numbers instead of only the misleading 0.94 lab accuracy.

Experiments (``--mode all`` runs every one and writes a comparison table):

    baseline_pv   train PlantVillage -> test PlantVillage and PlantDoc  (exposes the gap)
    plantdoc_only train PlantDoc     -> test PlantDoc
    mixed         train PlantVillage + PlantDoc -> test both  (measured winner; default deploy)
    two_stage     pretrain PlantVillage, fine-tune on PlantDoc -> test both  (ablation; underperformed)

The winning experiment's weights + metadata are written to the SAME artifact directory
the FastAPI service reads, with the SAME 38-class index order, so the app needs no code
change.

Usage
-----
    python ml/crop_health/training/train_field_robust.py \
        --manifest ml/crop_health/data/field_robust/manifest.json \
        --mode all --epochs 12 --deploy-experiment mixed

For a quick smoke test (2 epochs, baseline only):
    python ml/crop_health/training/train_field_robust.py --mode baseline_pv --epochs 2

Outputs
-------
    backend/app/ml/artifacts/crop_health/model.pt
    backend/app/ml/artifacts/crop_health/metadata.json
    ml/crop_health/evaluation/cross_domain_results.json
    ml/crop_health/evaluation/gradcam/*.png
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from torch import nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import (
    ConvNeXt_Small_Weights,
    ConvNeXt_Tiny_Weights,
    EfficientNet_B0_Weights,
    EfficientNet_B3_Weights,
    EfficientNet_V2_S_Weights,
    MobileNet_V3_Large_Weights,
    ResNet50_Weights,
    convnext_small,
    convnext_tiny,
    efficientnet_b0,
    efficientnet_b3,
    efficientnet_v2_s,
    mobilenet_v3_large,
    resnet50,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.crop_health.labels import class_display  # noqa: E402
from app.ml.crop_health.gradcam import (  # noqa: E402
    GradCAM,
    resolve_target_layer,
    save_gradcam_visuals,
)
from app.ml.crop_health.exg import ExGBackgroundSuppression  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "ml" / "crop_health" / "data" / "field_robust" / "manifest.json"
DEFAULT_ARTIFACTS = REPO_ROOT / "backend" / "app" / "ml" / "artifacts" / "crop_health"
DEFAULT_EVAL_DIR = REPO_ROOT / "ml" / "crop_health" / "evaluation"
MODEL_VERSION = "crop-health-v2.0.0-field-robust"
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

DOMAINS = ("pv", "pd", "web")


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
class ImageListDataset(Dataset):
    def __init__(self, items: list[dict[str, Any]], transform) -> None:
        self.items = items
        self.transform = transform

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int):
        entry = self.items[index]
        path = REPO_ROOT / entry["path"] if not Path(entry["path"]).is_absolute() else Path(entry["path"])
        with Image.open(path) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, int(entry["label_index"])


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(
            f"Manifest not found: {path}\n"
            "Run: python ml/crop_health/training/prepare_field_dataset.py"
        )
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def select(entries: list[dict], domains: tuple[str, ...], split: str) -> list[dict]:
    return [e for e in entries if e["domain"] in domains and e["split"] == split]


# --------------------------------------------------------------------------------------
# Model / transforms
# --------------------------------------------------------------------------------------
def build_model(architecture: str, num_classes: int) -> nn.Module:
    if architecture == "efficientnet_b0":
        model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    elif architecture == "efficientnet_b3":
        model = efficientnet_b3(weights=EfficientNet_B3_Weights.IMAGENET1K_V1)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    elif architecture == "resnet50":
        model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    elif architecture == "mobilenet_v3_large":
        model = mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.IMAGENET1K_V2)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    elif architecture == "convnext_tiny":
        model = convnext_tiny(weights=ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
        model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes)
    elif architecture == "convnext_small":
        model = convnext_small(weights=ConvNeXt_Small_Weights.IMAGENET1K_V1)
        model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes)
    elif architecture == "efficientnet_v2_s":
        model = efficientnet_v2_s(weights=EfficientNet_V2_S_Weights.IMAGENET1K_V1)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    else:
        raise ValueError(f"Unsupported architecture: {architecture}")
    return model


def make_transforms(image_size: int, strong_augmentation: bool, erasing: bool,
                    exg_suppression: bool = False, exg_strength: float = 0.8,
                    trivial_augment: bool = False):
    common_tail = [
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ]
    if trivial_augment:
        # Data-autosearched policy (TrivialAugment) replaces the hand-tuned colour
        # jitter stack. It samples one operation and magnitude per image, which is
        # a stronger, more diverse regulariser for in-the-wild field photographs.
        augmentations = [
            transforms.Resize(int(image_size * 1.25)),
            transforms.RandomResizedCrop(image_size, scale=(0.65, 1.0), ratio=(0.8, 1.25)),
            transforms.TrivialAugmentWide(num_magnitude_bins=31),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(p=0.15),
        ]
    elif strong_augmentation:
        augmentations = [
            transforms.Resize(int(image_size * 1.25)),
            transforms.RandomResizedCrop(image_size, scale=(0.65, 1.0), ratio=(0.8, 1.25)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(p=0.15),
            transforms.RandomRotation(degrees=15),
            transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.2, hue=0.03),
            transforms.RandomGrayscale(p=0.05),
        ]
    else:
        augmentations = [
            transforms.Resize(int(image_size * 1.25)),
            transforms.RandomResizedCrop(image_size, scale=(0.75, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
        ]
    if erasing:
        augmentations.append(transforms.RandomErasing(p=0.2, scale=(0.02, 0.12)))

    # ExG suppression must run on raw 8-bit RGB, i.e. after PIL augmentations but
    # before ToTensor/Normalize. Applied to both train and eval so the deployed
    # service can reproduce the exact same preprocessing via metadata.
    exg_step = [ExGBackgroundSuppression(strength=exg_strength)] if exg_suppression else []
    train_transform = transforms.Compose(augmentations + exg_step + common_tail)
    eval_transform = transforms.Compose(
        [
            transforms.Resize(int(image_size * 1.25)),
            transforms.CenterCrop(image_size),
            *exg_step,
            *common_tail,
        ]
    )
    return train_transform, eval_transform


def make_criterion(
    train_items: list[dict],
    num_classes: int,
    device: torch.device,
    label_smoothing: float = 0.0,
) -> nn.CrossEntropyLoss:
    """Inverse-frequency weighted CE, with optional label smoothing for noisy field labels."""
    counts = np.bincount([e["label_index"] for e in train_items], minlength=num_classes)
    weights_array = np.array(
        [len(train_items) / (num_classes * max(count, 1)) for count in counts], dtype=np.float32
    )
    weights = torch.tensor(weights_array, dtype=torch.float32, device=device)
    return nn.CrossEntropyLoss(weight=weights, label_smoothing=label_smoothing)


def mixup_criterion(criterion, logits, labels_a, labels_b, lam):
    """Weighted cross-entropy on mixup soft targets, with label smoothing.

    Reuses the configured class weights and smoothing factor so every experiment
    keeps an identical loss formulation; only the target construction changes.
    """
    num_classes = logits.size(1)
    targets = (
        lam * F.one_hot(labels_a, num_classes)
        + (1.0 - lam) * F.one_hot(labels_b, num_classes)
    ).float()
    eps = float(getattr(criterion, "label_smoothing", 0.0))
    if eps > 0.0:
        targets = targets * (1.0 - eps) + eps / num_classes
    log_probs = F.log_softmax(logits.float(), dim=1)
    per_example = -(targets * log_probs)
    weight = getattr(criterion, "weight", None)
    if weight is not None:
        per_example = per_example * weight.unsqueeze(0)
    return per_example.sum(dim=1).mean()


# --------------------------------------------------------------------------------------
# Train / evaluate
# --------------------------------------------------------------------------------------
def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def make_amp(device: torch.device, enabled: bool):
    """Return (use_amp, scaler). Safe on CPU and on older torch versions."""
    use = bool(enabled and device.type == "cuda")
    try:
        scaler = torch.amp.GradScaler("cuda", enabled=use)
    except (AttributeError, TypeError):  # pragma: no cover - older torch
        scaler = torch.cuda.amp.GradScaler(enabled=use)
    return use, scaler


def evaluate(model, loader, criterion, device) -> tuple[dict, np.ndarray, np.ndarray]:
    model.eval()
    losses = 0.0
    y_true: list[int] = []
    y_pred: list[int] = []
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            losses += float(criterion(logits, labels).item()) * len(labels)
            y_true.extend(labels.cpu().tolist())
            y_pred.extend(logits.argmax(dim=1).cpu().tolist())
    true, pred = np.array(y_true), np.array(y_pred)
    return (
        {
            "loss": round(losses / max(len(true), 1), 4),
            "accuracy": round(float(accuracy_score(true, pred)), 4),
            "precision_macro": round(float(precision_score(true, pred, average="macro", zero_division=0)), 4),
            "recall_macro": round(float(recall_score(true, pred, average="macro", zero_division=0)), 4),
            "f1_macro": round(float(f1_score(true, pred, average="macro", zero_division=0)), 4),
            "f1_weighted": round(float(f1_score(true, pred, average="weighted", zero_division=0)), 4),
            "support": int(len(true)),
        },
        true,
        pred,
    )


def run_stage(
    *,
    name: str,
    model: nn.Module,
    train_items: list[dict],
    val_items: list[dict],
    class_order: list[str],
    device: torch.device,
    train_transform,
    eval_transform,
    epochs: int,
    batch_size: int,
    lr: float,
    patience: int,
    criterion: nn.CrossEntropyLoss,
    use_amp: bool = False,
    scaler=None,
    mixup_alpha: float = 0.0,
) -> tuple[nn.Module, list[dict], dict]:
    loader = DataLoader(
        ImageListDataset(train_items, train_transform),
        batch_size=batch_size, shuffle=True, num_workers=0,
    )
    val_loader = DataLoader(
        ImageListDataset(val_items, eval_transform), batch_size=batch_size, num_workers=0
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(epochs, 1))

    def compute_loss(images, labels):
        if mixup_alpha > 0.0 and labels.size(0) > 1:
            lam = float(np.random.beta(mixup_alpha, mixup_alpha))
            index = torch.randperm(labels.size(0), device=device)
            mixed_images = lam * images + (1.0 - lam) * images[index]
            return mixup_criterion(
                criterion, model(mixed_images), labels, labels[index], lam
            )
        return criterion(model(images), labels)

    best_f1, best_state, stale, history = -1.0, None, 0, []
    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            if use_amp and scaler is not None:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    loss = compute_loss(images, labels)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss = compute_loss(images, labels)
                loss.backward()
                optimizer.step()
            running += float(loss.item()) * len(labels)
        scheduler.step()
        train_loss = running / max(len(train_items), 1)
        val_metrics, _, _ = evaluate(model, val_loader, criterion, device)
        history.append({"epoch": epoch, "train_loss": round(train_loss, 4), "validation": val_metrics})
        print(
            f"  [{name}] epoch {epoch}/{epochs} train_loss={train_loss:.4f} "
            f"val_acc={val_metrics['accuracy']} val_f1={val_metrics['f1_macro']}"
        )
        if val_metrics["f1_macro"] > best_f1:
            best_f1 = val_metrics["f1_macro"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                print(f"  [{name}] early stopping at epoch {epoch}")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, history, {"best_val_f1": round(best_f1, 4), "epochs_completed": len(history)}


def evaluate_all_domains(
    model,
    entries: list[dict],
    class_order: list[str],
    eval_transform,
    criterion,
    device,
    batch_size: int,
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for domain in DOMAINS:
        test_items = select(entries, (domain,), "test")
        if not test_items:
            continue
        loader = DataLoader(
            ImageListDataset(test_items, eval_transform), batch_size=batch_size, num_workers=0
        )
        metrics, true, pred = evaluate(model, loader, criterion, device)
        report = classification_report(
            true, pred, labels=list(range(len(class_order))),
            target_names=[class_display(c) for c in class_order],
            output_dict=True, zero_division=0,
        )
        per_class = {}
        for name in class_order:
            key = class_display(name)
            if key in report:
                per_class[name] = {
                    "precision": round(float(report[key]["precision"]), 4),
                    "recall": round(float(report[key]["recall"]), 4),
                    "f1-score": round(float(report[key]["f1-score"]), 4),
                    "support": int(report[key]["support"]),
                }
        results[domain] = {
            "metrics": metrics,
            "per_class_metrics": per_class,
            "confusion_matrix": confusion_matrix(
                true, pred, labels=list(range(len(class_order)))
            ).tolist(),
        }
        print(f"  TEST[{domain}] acc={metrics['accuracy']} f1={metrics['f1_macro']} n={metrics['support']}")
    return results


def save_gradcam_examples(
    model,
    entries: list[dict],
    class_order: list[str],
    eval_transform,
    architecture: str,
    image_size: int,
    output_dir: Path,
    device: torch.device,
    per_domain: int = 3,
) -> list[str]:
    """Offline Grad-CAM figures for the paper (verify attention is on the lesion)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    model.eval()
    for domain in ("pd", "web", "pv"):
        samples = [e for e in entries if e["domain"] == domain and e["split"] == "test"][:per_domain]
        for index, entry in enumerate(samples):
            path = REPO_ROOT / entry["path"]
            try:
                with Image.open(path) as image:
                    rgb = image.convert("RGB")
                    # The model lives on `device`; Grad-CAM backprops through it, so the
                    # input must be on the same device (this was a device-mismatch bug).
                    tensor = eval_transform(rgb).unsqueeze(0).to(device)
            except Exception:
                continue
            target = resolve_target_layer(model, architecture)
            cam = GradCAM(model, target)
            try:
                with torch.no_grad():
                    logits = model(tensor)
                predicted = int(logits.argmax(dim=1)[0])
                array = cam.generate(tensor, predicted)
                _, overlay = save_gradcam_visuals(
                    array, rgb, output_dir, f"{domain}_{index}_{class_order[predicted]}", image_size
                )
                saved.append(str(relative_path(overlay)))
            except Exception as exc:  # pragma: no cover
                print(f"  Grad-CAM skipped for {path.name}: {exc}")
            finally:
                cam.close()
    return saved


def relative_path(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--eval-dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--architecture", default="efficientnet_b0")
    parser.add_argument("--init-from", type=Path, default=None,
                        help="initialise from an existing artifact instead of ImageNet weights")
    parser.add_argument("--model-version", default=MODEL_VERSION,
                        help="version string written into candidate metadata")
    parser.add_argument("--mode", default="all",
                        choices=["all", "baseline_pv", "plantdoc_only", "mixed", "two_stage"])
    parser.add_argument("--deploy-experiment", default="mixed",
                        choices=["baseline_pv", "plantdoc_only", "mixed", "two_stage"])
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--stage1-epochs", type=int, default=None)
    parser.add_argument("--stage2-epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--stage2-lr", type=float, default=5e-5)
    parser.add_argument("--image-size", type=int, default=192)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--label-smoothing", type=float, default=0.0,
                        help="target smoothing epsilon (0.1 is a good default for noisy labels)")
    parser.add_argument("--mixup-alpha", type=float, default=0.0,
                        help="Beta alpha for mixup regularization (0 disables, 0.2 typical)")
    parser.add_argument("--val-domain", default="all", choices=["all", "pv", "pd"],
                        help="which domain to use for early stopping/model selection "
                             "(use 'pd' to optimise in-the-wild accuracy)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--erasing", action="store_true")
    parser.add_argument("--trivial-augment", action="store_true",
                        help="use TrivialAugmentWide instead of the hand-tuned colour augmentation")
    parser.add_argument("--no-strong-augmentation", action="store_true")
    parser.add_argument("--skip-gradcam", action="store_true")
    parser.add_argument("--amp", action="store_true",
                        help="use CUDA mixed precision (FP16 autocast + GradScaler)")
    parser.add_argument("--exg-suppression", action="store_true",
                        help="apply ReVit-derived ExG background suppression as an ablation")
    parser.add_argument("--exg-strength", type=float, default=0.8,
                        help="strength of ExG suppression (0=off, 1=full)")
    args = parser.parse_args()

    started = time.time()
    seed_everything(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        try:
            probe = torch.ones(1, device=device)
            _ = (probe * probe).item()
        except Exception as exc:
            print(f"CUDA unusable ({exc}); falling back to CPU")
            device = torch.device("cpu")
    print(f"Device: {device}")
    use_amp, scaler = make_amp(device, args.amp)
    print(f"Mixed precision: {use_amp}")

    manifest = load_manifest(args.manifest)
    entries: list[dict] = manifest["entries"]
    class_order: list[str] = manifest["class_order"]
    num_classes = len(class_order)
    print(f"Manifest: {len(entries)} images | {num_classes} classes")

    init_state = None
    if args.init_from is not None:
        init_meta_path = args.init_from / "metadata.json"
        init_meta = json.loads(init_meta_path.read_text(encoding="utf-8"))
        if init_meta.get("architecture") != args.architecture:
            raise SystemExit(
                f"--init-from architecture {init_meta.get('architecture')} != {args.architecture}"
            )
        if init_meta.get("classes") != class_order:
            raise SystemExit("--init-from class order differs from manifest class order")
        init_state = torch.load(
            args.init_from / "model.pt", map_location="cpu", weights_only=True
        )
        print(f"Initialising from {args.init_from} (continued training)")

    for domain in DOMAINS:
        counts = Counter(e["split"] for e in entries if e["domain"] == domain)
        if counts:
            print(f"  {domain}: train={counts['train']} val={counts['val']} test={counts['test']}")
    if not select(entries, ("pd",), "train"):
        print("\nWARNING: no PlantDoc training images. Results will not address the field gap.")

    train_transform, eval_transform = make_transforms(
        args.image_size, not args.no_strong_augmentation, args.erasing,
        exg_suppression=args.exg_suppression, exg_strength=args.exg_strength,
        trivial_augment=args.trivial_augment,
    )
    if args.trivial_augment:
        print("TrivialAugmentWide ENABLED")
    if args.exg_suppression:
        print(f"ExG background suppression ENABLED (strength={args.exg_strength})")

    pv_train = select(entries, ("pv",), "train")
    pv_val = select(entries, ("pv",), "val")
    pd_train = select(entries, ("pd",), "train")
    pd_val = select(entries, ("pd",), "val")
    external_train = select(entries, ("web",), "train")
    mixed_train = pv_train + pd_train + external_train
    mixed_val = pv_val + pd_val
    if external_train:
        print(f"  Including {len(external_train)} deduplicated external training images (domain=web)")
    if args.val_domain != "all":
        mixed_val = [e for e in mixed_val if e["domain"] == args.val_domain]
        print(f"Model selection on '{args.val_domain}' validation only: {len(mixed_val)} images")

    experiments: dict[str, dict] = {}
    models: dict[str, nn.Module] = {}
    histories: dict[str, list[dict]] = {}
    stage1_epochs = args.stage1_epochs or args.epochs
    stage2_epochs = args.stage2_epochs or args.epochs

    def fresh() -> nn.Module:
        seed_everything(args.seed)
        model = build_model(args.architecture, num_classes)
        if init_state is not None:
            model.load_state_dict(init_state)
        return model.to(device)

    def criterion_for(items: list[dict]):
        return make_criterion(
            items, num_classes, device, label_smoothing=args.label_smoothing
        )

    # --- Stage 1 / baseline ----------------------------------------------------------------
    if args.mode in {"all", "baseline_pv", "two_stage"}:
        print("\n=== Experiment: baseline_pv (train on controlled lab images) ===")
        model = fresh()
        model, history, meta = run_stage(
            name="baseline_pv", model=model, train_items=pv_train, val_items=pv_val,
            class_order=class_order, device=device, train_transform=train_transform,
            eval_transform=eval_transform, epochs=stage1_epochs, batch_size=args.batch_size,
            lr=args.lr, patience=args.patience,
            criterion=criterion_for(pv_train), use_amp=use_amp, scaler=scaler,
            mixup_alpha=args.mixup_alpha,
        )
        models["baseline_pv"], histories["baseline_pv"] = model, history
        experiments["baseline_pv"] = {
            "description": "EfficientNet trained only on PlantVillage; measures the lab-to-field gap.",
            "training_domains": ["pv"], "stage": meta,
            "results": evaluate_all_domains(
                model, entries, class_order, eval_transform,
                criterion_for(pv_train), device, args.batch_size,
            ),
        }

    # --- PlantDoc only ----------------------------------------------------------------------
    if args.mode in {"all", "plantdoc_only"}:
        if not pd_train:
            print("\nSkipping plantdoc_only (no PlantDoc training images)")
        else:
            print("\n=== Experiment: plantdoc_only (train on in-the-wild images) ===")
            model = fresh()
            model, history, meta = run_stage(
                name="plantdoc_only", model=model, train_items=pd_train, val_items=pd_val,
                class_order=class_order, device=device, train_transform=train_transform,
                eval_transform=eval_transform, epochs=args.epochs, batch_size=args.batch_size,
                lr=args.lr, patience=args.patience,
                criterion=criterion_for(pd_train), use_amp=use_amp, scaler=scaler,
                mixup_alpha=args.mixup_alpha,
            )
            models["plantdoc_only"], histories["plantdoc_only"] = model, history
            experiments["plantdoc_only"] = {
                "description": "EfficientNet trained only on PlantDoc; lower in-domain data volume.",
                "training_domains": ["pd"], "stage": meta,
                "results": evaluate_all_domains(
                    model, entries, class_order, eval_transform,
                    criterion_for(pd_train), device, args.batch_size,
                ),
            }

    # --- Mixed domains ----------------------------------------------------------------------
    if args.mode in {"all", "mixed"}:
        print("\n=== Experiment: mixed (joint PlantVillage + PlantDoc + optional external) ===")
        model = fresh()
        model, history, meta = run_stage(
            name="mixed", model=model, train_items=mixed_train, val_items=mixed_val,
            class_order=class_order, device=device, train_transform=train_transform,
            eval_transform=eval_transform, epochs=args.epochs, batch_size=args.batch_size,
            lr=args.lr, patience=args.patience,
            criterion=criterion_for(mixed_train), use_amp=use_amp, scaler=scaler,
            mixup_alpha=args.mixup_alpha,
        )
        models["mixed"], histories["mixed"] = model, history
        experiments["mixed"] = {
            "description": "Joint training on controlled, in-the-wild and deduplicated external images.",
            "training_domains": ["pv", "pd", "web"] if external_train else ["pv", "pd"],
            "stage": meta,
            "results": evaluate_all_domains(
                model, entries, class_order, eval_transform,
                criterion_for(mixed_train), device, args.batch_size,
            ),
        }

    # --- Two-stage domain adaptation ---------------------------------------------------------
    if args.mode in {"all", "two_stage"}:
        if not pd_train:
            print("\nSkipping two_stage (no PlantDoc training images)")
        else:
            print("\n=== Experiment: two_stage (pretrain lab, fine-tune field) ===")
            base = models.get("baseline_pv")
            if base is None:
                base = fresh()
                base, _, _ = run_stage(
                    name="two_stage/stage1", model=base, train_items=pv_train, val_items=pv_val,
                    class_order=class_order, device=device, train_transform=train_transform,
                    eval_transform=eval_transform, epochs=stage1_epochs, batch_size=args.batch_size,
                    lr=args.lr, patience=args.patience,
                    criterion=criterion_for(pv_train), use_amp=use_amp, scaler=scaler,
                    mixup_alpha=args.mixup_alpha,
                )
            # Copy the stage-1 weights: fine-tuning must not mutate the baseline model,
            # otherwise deploying '--deploy-experiment baseline_pv' would deploy this one.
            model = fresh()
            model.load_state_dict(
                {key: value.detach().cpu().clone() for key, value in base.state_dict().items()}
            )
            model = model.to(device)
            model, history2, meta2 = run_stage(
                name="two_stage/stage2", model=model, train_items=pd_train, val_items=pd_val,
                class_order=class_order, device=device, train_transform=train_transform,
                eval_transform=eval_transform, epochs=stage2_epochs, batch_size=args.batch_size,
                lr=args.stage2_lr, patience=args.patience,
                criterion=criterion_for(pd_train), use_amp=use_amp, scaler=scaler,
                mixup_alpha=args.mixup_alpha,
            )
            models["two_stage"], histories["two_stage"] = model, histories.get("baseline_pv", []) + history2
            experiments["two_stage"] = {
                "description": (
                    "Stage 1 learns disease semantics on PlantVillage; stage 2 adapts the whole "
                    "network to natural backgrounds/illumination with a low learning rate."
                ),
                "training_domains": ["pv", "pd"],
                "stage": {"stage2": meta2, "stage1": experiments.get("baseline_pv", {}).get("stage")},
                "results": evaluate_all_domains(
                    model, entries, class_order, eval_transform,
                    criterion_for(pd_train), device, args.batch_size,
                ),
            }

    if not experiments:
        raise SystemExit("No experiment was run. Check --mode and the manifest contents.")

    # --- Comparison table --------------------------------------------------------------------
    summary = []
    for name, payload in experiments.items():
        row = {"experiment": name, "training_domains": payload["training_domains"]}
        for domain in DOMAINS:
            if domain in payload["results"]:
                row[f"{domain}_accuracy"] = payload["results"][domain]["metrics"]["accuracy"]
                row[f"{domain}_f1_macro"] = payload["results"][domain]["metrics"]["f1_macro"]
        summary.append(row)
    print("\n=== Cross-domain summary ===")
    for row in summary:
        print("  " + json.dumps(row))

    args.eval_dir.mkdir(parents=True, exist_ok=True)
    with (args.eval_dir / "cross_domain_results.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "architecture": args.architecture,
                "image_size": args.image_size,
                "seed": args.seed,
                "amp": use_amp,
                "exg_suppression": args.exg_suppression,
                "exg_strength": args.exg_strength if args.exg_suppression else 0.0,
                "trivial_augment": args.trivial_augment,
                "label_smoothing": args.label_smoothing,
                "mixup_alpha": args.mixup_alpha,
                "manifest": str(args.manifest),
                "experiments": experiments,
                "summary": summary,
            },
            handle, indent=2,
        )

    # --- Deploy the selected model ------------------------------------------------------------
    deploy_name = args.deploy_experiment
    if deploy_name not in models:
        print(f"Requested deployment of '{deploy_name}' but it was not run; deploying first available.")
        deploy_name = next(iter(models))
    deploy_model = models[deploy_name]
    deploy_results = experiments[deploy_name]["results"]

    gradcam_paths: list[str] = []
    if not args.skip_gradcam:
        print("\nGenerating Grad-CAM figures for the paper ...")
        gradcam_paths = save_gradcam_examples(
            deploy_model, entries, class_order, eval_transform,
            args.architecture, args.image_size, args.eval_dir / "gradcam", device,
        )

    primary = deploy_results.get("pd", deploy_results.get("pv", {})).get("metrics", {})
    metadata = {
        "version": args.model_version,
        "architecture": args.architecture,
        "input_size": args.image_size,
        "resize_size": int(args.image_size * 1.25),
        "normalization": {"mean": IMAGENET_MEAN, "std": IMAGENET_STD},
        "classes": class_order,
        "class_display": {name: class_display(name) for name in class_order},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "amp": use_amp,
        "val_domain": args.val_domain,
        "label_smoothing": args.label_smoothing,
        "mixup_alpha": args.mixup_alpha,
        "exg_suppression": args.exg_suppression,
        "exg_strength": args.exg_strength if args.exg_suppression else 0.0,
        "trivial_augment": args.trivial_augment,
        "training_mode": deploy_name,
        "init_from": str(relative_path(args.init_from)) if args.init_from is not None else None,
        "epochs_requested": args.epochs,
        "epochs_completed": len(histories.get(deploy_name, [])),
        "training_images": len(
            {"baseline_pv": pv_train, "plantdoc_only": pd_train,
             "mixed": mixed_train, "two_stage": pd_train}[deploy_name]
        ),
        "validation_images": len(
            {"baseline_pv": pv_val, "plantdoc_only": pd_val,
             "mixed": mixed_val, "two_stage": pd_val}[deploy_name]
        ),
        "test_images": len(select(entries, ("pd",), "test")) + len(select(entries, ("pv",), "test")),
        "dataset_provenance": (
            "Cross-domain training. PlantVillage (controlled lab) + PlantDoc (CC BY 4.0, "
            "in-the-wild) + external images mapped onto the original 38-class PlantVillage "
            "label space. The held-out test split is unchanged. External source: "
            + str(manifest.get("extension_source", "unrecorded external source"))
            + ". See cross_domain_results.json and the matching *_dedupe_report.json for provenance."
            if external_train else
            "Cross-domain training. PlantVillage (controlled lab) + PlantDoc (CC BY 4.0, "
            "in-the-wild) mapped onto the original 38-class PlantVillage label space; optional "
            "web-collected external test images. See ml/crop_health/evaluation/"
            "cross_domain_results.json for the full experiment matrix."
        ),
        "metrics": primary,
        "per_class_metrics": deploy_results.get("pd", deploy_results.get("pv", {})).get("per_class_metrics", {}),
        "evaluation_by_domain": deploy_results,
        "cross_domain_summary": summary,
        "gradcam_examples": gradcam_paths,
        "class_order": class_order,
        "history": histories.get(deploy_name, []),
        "device": str(device),
        "training_seconds": round(time.time() - started, 1),
        "notes": (
            "Field-robust model trained with cross-domain evaluation. In-domain lab accuracy is "
            "reported separately from in-the-wild accuracy; the app must keep presenting results "
            "as screening support, not a definitive diagnosis."
        ),
    }

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    torch.save(deploy_model.state_dict(), args.artifact_dir / "model.pt")
    with (args.artifact_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    print(f"\nDeployed '{deploy_name}' to {args.artifact_dir}")
    print("Full results:", args.eval_dir / "cross_domain_results.json")


if __name__ == "__main__":
    main()
