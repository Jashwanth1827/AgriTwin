"""Train the AgriTwin crop-health CNN (transfer learning, CPU friendly).

Usage:
    python ml/crop_health/training/train.py \
        --data-dir ml/crop_health/data/plantvillage_subset \
        --epochs 6 --per-class 40

Outputs:
    backend/app/ml/artifacts/crop_health/model.pt
    backend/app/ml/artifacts/crop_health/metadata.json

Metrics are computed on a stratified hold-out split that is never used for
training or early stopping.  No metric in metadata is hand-written.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

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

DEFAULT_DATA = REPO_ROOT / "ml" / "crop_health" / "data" / "plantvillage_subset"
DEFAULT_ARTIFACTS = REPO_ROOT / "backend" / "app" / "ml" / "artifacts" / "crop_health"
MODEL_VERSION = "crop-health-v1.0.0"
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class ImageListDataset(Dataset):
    def __init__(self, items: list[tuple[Path, int]], transform) -> None:
        self.items = items
        self.transform = transform

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int):
        path, label = self.items[index]
        with Image.open(path) as image:
            image = image.convert("RGB")
            tensor = self.transform(image)
        return tensor, label


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def split_items(root: Path, seed: int) -> tuple[list, list, list, list[str]]:
    rng = random.Random(seed)
    class_dirs = sorted([p for p in root.iterdir() if p.is_dir()])
    classes = [p.name for p in class_dirs]
    train, val, test = [], [], []
    for index, class_dir in enumerate(class_dirs):
        files = sorted(class_dir.glob("*.jpg"))
        rng.shuffle(files)
        n = len(files)
        n_test = max(1, int(n * 0.15))
        n_val = max(1, int(n * 0.15))
        test.extend((path, index) for path in files[:n_test])
        val.extend((path, index) for path in files[n_test : n_test + n_val])
        train.extend((path, index) for path in files[n_test + n_val :])
    rng.shuffle(train)
    return train, val, test, classes


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


def evaluate(model, loader, criterion, device) -> tuple[dict, np.ndarray, np.ndarray]:
    model.eval()
    losses = []
    all_labels: list[int] = []
    all_preds: list[int] = []
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            losses.append(float(criterion(logits, labels).item()) * len(labels))
            all_labels.extend(labels.cpu().tolist())
            all_preds.extend(logits.argmax(dim=1).cpu().tolist())
    y_true = np.array(all_labels)
    y_pred = np.array(all_preds)
    metrics = {
        "loss": round(sum(losses) / max(len(y_true), 1), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_macro": round(float(precision_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
    }
    return metrics, y_true, y_pred


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--architecture", default="efficientnet_b0")
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--image-size", type=int, default=192)
    parser.add_argument("--per-class", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patience", type=int, default=2)
    args = parser.parse_args()

    if not args.data_dir.exists():
        raise SystemExit(f"Dataset directory not found: {args.data_dir}")
    seed_everything(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        try:
            probe = torch.ones(1, device=device)
            _ = (probe * probe).item()
        except Exception as exc:
            print(f"CUDA is not usable with this PyTorch build ({exc}); falling back to CPU")
            device = torch.device("cpu")
    print(f"Device: {device}")

    train_items, val_items, test_items, classes = split_items(args.data_dir, args.seed)
    if not train_items:
        raise SystemExit("No training images found")
    print(f"Train {len(train_items)} | Val {len(val_items)} | Test {len(test_items)} | Classes {len(classes)}")

    train_transform = transforms.Compose(
        [
            transforms.Resize(int(args.image_size * 1.25)),
            transforms.RandomResizedCrop(args.image_size, scale=(0.75, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )
    eval_transform = transforms.Compose(
        [
            transforms.Resize(int(args.image_size * 1.25)),
            transforms.CenterCrop(args.image_size),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )
    train_loader = DataLoader(
        ImageListDataset(train_items, train_transform),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(ImageListDataset(val_items, eval_transform), batch_size=args.batch_size)
    test_loader = DataLoader(ImageListDataset(test_items, eval_transform), batch_size=args.batch_size)

    model = build_model(args.architecture, len(classes)).to(device)
    class_counts = np.bincount([label for _, label in train_items], minlength=len(classes))
    weights = torch.tensor(
        [len(train_items) / (len(classes) * max(count, 1)) for count in class_counts],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_f1 = -1.0
    best_state = None
    epochs_without_improvement = 0
    history: list[dict] = []
    started = time.time()

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * len(labels)
        scheduler.step()
        train_loss = running_loss / max(len(train_items), 1)
        val_metrics, _, _ = evaluate(model, val_loader, criterion, device)
        history.append(
            {"epoch": epoch, "train_loss": round(train_loss, 4), "validation": val_metrics}
        )
        print(
            f"Epoch {epoch}/{args.epochs} train_loss={train_loss:.4f} "
            f"val_acc={val_metrics['accuracy']} val_f1={val_metrics['f1_macro']}"
        )
        if val_metrics["f1_macro"] > best_f1:
            best_f1 = val_metrics["f1_macro"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= args.patience:
                print("Early stopping triggered")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    test_metrics, y_true, y_pred = evaluate(model, test_loader, criterion, device)
    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(classes))),
        target_names=[class_display(name) for name in classes],
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(y_true, y_pred, labels=list(range(len(classes)))).tolist()
    per_class = {
        name: {
            key: round(float(report[class_display(name)][key]), 4)
            for key in ["precision", "recall", "f1-score"]
        }
        | {"support": int(report[class_display(name)]["support"])}
        for name in classes
        if class_display(name) in report
    }

    metadata = {
        "version": MODEL_VERSION,
        "architecture": args.architecture,
        "input_size": args.image_size,
        "resize_size": int(args.image_size * 1.25),
        "normalization": {"mean": IMAGENET_MEAN, "std": IMAGENET_STD},
        "classes": classes,
        "class_display": {name: class_display(name) for name in classes},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "epochs_requested": args.epochs,
        "epochs_completed": len(history),
        "training_images": len(train_items),
        "validation_images": len(val_items),
        "test_images": len(test_items),
        "dataset_provenance": (
            "PlantVillage (Hemg/new-plant-diseases-dataset on Hugging Face), balanced subset "
            f"of up to {args.per_class} images per class, "
            "stratified 70/15/15 split by image. Transfer learning from ImageNet weights."
        ),
        "metrics": test_metrics,
        "per_class_metrics": per_class,
        "confusion_matrix": matrix,
        "class_order": classes,
        "history": history,
        "device": str(device),
        "training_seconds": round(time.time() - started, 1),
        "notes": (
            "PlantVillage images are captured under relatively controlled conditions. "
            "Accuracy on field photographs is expected to be lower; the app labels this "
            "limitation and does not present the result as a diagnosis."
        ),
    }

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), args.artifact_dir / "model.pt")
    with (args.artifact_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    print("\nTest metrics:")
    print(json.dumps(test_metrics, indent=2))
    print(f"Artifacts written to {args.artifact_dir}")


if __name__ == "__main__":
    main()
