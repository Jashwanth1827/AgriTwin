"""Measure the efficiency claims for the AgriTwin crop-health model.

The ReVit paper reports parameters, FLOPs, latency and FPS, so the AgriTwin paper
needs the same evidence.  This script is dependency-free (no fvcore/thop needed):
it counts MACs with forward hooks on Conv2d/Linear and times real inference on the
device that is available.

Usage
-----
    python ml/crop_health/evaluation/benchmark.py

    # benchmark every supported architecture at several batch sizes
    python ml/crop_health/evaluation/benchmark.py --architecture all \
        --batch-sizes 1 8 32 --output ml/crop_health/evaluation/benchmark_results.json

Only the *deployed* architecture is read from metadata when --architecture is
"deployed" (the default), so the reported numbers always describe the model the
app actually serves.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from torch import nn
from torchvision import models

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

DEFAULT_METADATA = REPO_ROOT / "backend" / "app" / "ml" / "artifacts" / "crop_health" / "metadata.json"
DEFAULT_OUTPUT = REPO_ROOT / "ml" / "crop_health" / "evaluation" / "benchmark_results.json"

SUPPORTED = (
    "efficientnet_b0", "efficientnet_b3", "efficientnet_v2_s",
    "resnet50", "mobilenet_v3_large", "convnext_tiny", "convnext_small",
)


def build(architecture: str, num_classes: int) -> nn.Module:
    """Build a weights-free model with the same classifier heads as training/serving."""
    if architecture == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    elif architecture == "efficientnet_b3":
        model = models.efficientnet_b3(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    elif architecture == "resnet50":
        model = models.resnet50(weights=None)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    elif architecture == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    elif architecture == "convnext_tiny":
        model = models.convnext_tiny(weights=None)
        model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes)
    elif architecture == "convnext_small":
        model = models.convnext_small(weights=None)
        model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes)
    elif architecture == "efficientnet_v2_s":
        model = models.efficientnet_v2_s(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    else:
        raise ValueError(f"Unsupported architecture: {architecture}")
    return model


class MACCounter:
    """Count multiply-accumulate operations without an external profiling library."""

    def __init__(self) -> None:
        self.macs = 0
        self._handles: list[torch.utils.hooks.RemovableHandle] = []

    def _conv_hook(self, module, inputs, output):
        if not isinstance(module, nn.modules.conv._ConvNd):
            return
        out_h, out_w = output.shape[-2], output.shape[-1]
        in_ch = module.in_channels // module.groups
        self.macs += int(out_h * out_w * in_ch * module.out_channels
                         * module.kernel_size[0] * module.kernel_size[1])

    def _linear_hook(self, module, inputs, output):
        x = inputs[0]
        batch = 1
        for dim in x.shape[:-1]:
            batch *= int(dim)
        self.macs += int(batch * module.in_features * module.out_features)

    def __enter__(self):
        for module in self._modules():
            if isinstance(module, nn.modules.conv._ConvNd):
                self._handles.append(module.register_forward_hook(self._conv_hook))
            elif isinstance(module, nn.Linear):
                self._handles.append(module.register_forward_hook(self._linear_hook))
        return self

    def __exit__(self, *args):
        for handle in self._handles:
            handle.remove()
        self._handles.clear()

    def _modules(self):
        # set later by attach()
        return getattr(self, "_module_list", [])

    def attach(self, model: nn.Module) -> "MACCounter":
        self._module_list = list(model.modules())
        return self


def count_macs(model: nn.Module, device: torch.device, input_size: int) -> dict:
    macs = MACCounter().attach(model)
    dummy = torch.zeros(1, 3, input_size, input_size, device=device)
    with macs, torch.no_grad():
        model(dummy)
    return {
        "macs": macs.macs,
        "gflops": round(2 * macs.macs / 1e9, 4),  # 1 MAC = 2 FLOPs
    }


def time_inference(
    model: nn.Module,
    device: torch.device,
    input_size: int,
    batch_size: int,
    warmup: int = 10,
    repeats: int = 50,
    use_amp: bool = False,
) -> dict:
    model.eval()
    dummy = torch.randn(batch_size, 3, input_size, input_size, device=device)
    use_amp = use_amp and device.type == "cuda"

    def run():
        with torch.no_grad():
            if use_amp:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    model(dummy)
            else:
                model(dummy)

    for _ in range(warmup):
        run()
    if device.type == "cuda":
        torch.cuda.synchronize()
        start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        start.record()
        for _ in range(repeats):
            run()
        end.record()
        torch.cuda.synchronize()
        total_ms = start.elapsed_time(end)
    else:
        t0 = time.perf_counter()
        for _ in range(repeats):
            run()
        total_ms = (time.perf_counter() - t0) * 1000.0

    ms_per_batch = total_ms / repeats
    return {
        "batch_size": batch_size,
        "ms_per_batch": round(ms_per_batch, 3),
        "ms_per_image": round(ms_per_batch / batch_size, 3),
        "images_per_second": round(batch_size * 1000.0 / ms_per_batch, 1),
        "amp": use_amp,
    }


def benchmark(model: nn.Module, device: torch.device, input_size: int, batch_sizes: list[int],
              amp: bool) -> dict:
    params = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    bytes_per_param = {torch.float32: 4, torch.float16: 2}
    model_bytes = sum(
        p.numel() * bytes_per_param.get(p.dtype, 4) for p in model.parameters()
    )

    result = {
        "parameters": params,
        "trainable_parameters": trainable,
        "model_size_mb": round(model_bytes / 1024**2, 2),
        "device": str(device),
        "input_size": input_size,
        "flops": count_macs(model, device, input_size),
        "latency": [],
    }

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for batch_size in batch_sizes:
        result["latency"].append(
            time_inference(model, device, input_size, batch_size, use_amp=amp)
        )
    if device.type == "cuda":
        result["peak_gpu_memory_mb"] = round(torch.cuda.max_memory_allocated() / 1024**2, 1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--architecture", default="deployed",
                        help="'deployed', one of %s, or 'all'" % ", ".join(SUPPORTED))
    parser.add_argument("--num-classes", type=int, default=None)
    parser.add_argument("--input-size", type=int, default=None)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 8, 32])
    parser.add_argument("--amp", action="store_true", help="also time FP16 autocast on CUDA")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    metadata: dict = {}
    if args.metadata.exists():
        metadata = json.loads(args.metadata.read_text(encoding="utf-8"))

    num_classes = args.num_classes or len(metadata.get("classes", [])) or 38
    input_size = args.input_size or int(metadata.get("input_size", 192))

    if args.architecture == "all":
        architectures = list(SUPPORTED)
    elif args.architecture == "deployed":
        architectures = [metadata.get("architecture", "efficientnet_b0")]
    else:
        architectures = [args.architecture]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        try:
            probe = torch.ones(1, device=device)
            _ = (probe * probe).item()
        except Exception as exc:
            print(f"CUDA unusable ({exc}); falling back to CPU")
            device = torch.device("cpu")
    print(f"device={device} input_size={input_size} classes={num_classes}")

    results = {}
    for architecture in architectures:
        print(f"\n=== {architecture} ===")
        model = build(architecture, num_classes).to(device).eval()
        results[architecture] = benchmark(
            model, device, input_size, args.batch_sizes, args.amp
        )
        row = results[architecture]
        print(f"  params={row['parameters']:,}  size={row['model_size_mb']} MB  "
              f"GFLOPs={row['flops']['gflops']}")
        for timing in row["latency"]:
            print(f"  batch={timing['batch_size']:<3} {timing['ms_per_image']} ms/image "
                  f"~{timing['images_per_second']} img/s"
                  f"{' (AMP)' if timing['amp'] else ''}")
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata_version": metadata.get("version"),
        "device_detail": torch.cuda.get_device_name(0) if device.type == "cuda" else "CPU",
        "torch_version": torch.__version__,
        "num_classes": num_classes,
        "results": results,
        "note": (
            "MACs counted with forward hooks (Conv2d/Linear); GFLOPs = 2 x MACs. "
            "Latency includes only the forward pass, not preprocessing or network I/O. "
            "FPS is the reciprocal of ms/image for the stated batch size."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
