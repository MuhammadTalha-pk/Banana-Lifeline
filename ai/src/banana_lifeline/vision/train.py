"""Training loop.

Built for a Colab T4 and for the fact that Colab sessions die. Every epoch writes a
checkpoint and a metrics row, so a disconnect costs one epoch rather than the whole run, and
``--resume`` picks up where it stopped.

Run artefacts land in ``runs/<timestamp>/``: the resolved config, the git SHA, per-epoch
history, and the best checkpoint. A reported number can always be traced back to the exact
code and configuration that produced it.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from banana_lifeline.config import DataConfig, Paths, TrainConfig
from banana_lifeline.vision.metrics import ClassificationMetrics, compute_metrics
from banana_lifeline.vision.model import build_model, parameter_groups, save_checkpoint


@dataclass(slots=True)
class EpochResult:
    epoch: int
    train_loss: float
    val_loss: float
    val_macro_f1: float
    val_accuracy: float
    val_panama_recall: float
    learning_rate: float
    seconds: float


def _git_sha() -> str:
    """Record which commit produced a run. Unknown is acceptable; wrong is not."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def set_seed(seed: int) -> None:
    """Seed every RNG that affects training.

    Determinism is not merely tidy here: the honest-versus-contaminated comparison is only
    meaningful if the two runs differ solely in their split.
    """
    import random

    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = True  # fixed input size, so autotuning pays off


def build_dataloaders(
    manifest: pd.DataFrame,
    train_cfg: TrainConfig,
    data_cfg: DataConfig,
    paths: Paths,
) -> tuple[Any, Any]:
    """Create train and validation loaders from a manifest."""
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    from banana_lifeline.data.dataset import BananaLeafDataset, sample_weights
    from banana_lifeline.vision.transforms import build_eval_transform, build_train_transform

    train_rows = manifest[manifest["split"] == "train"].reset_index(drop=True)
    val_rows = manifest[manifest["split"] == "val"].reset_index(drop=True)

    train_set = BananaLeafDataset(
        train_rows,
        paths,
        data_cfg,
        transform=build_train_transform(train_cfg.image_size, train_cfg.augment),
    )
    val_set = BananaLeafDataset(
        val_rows,
        paths,
        data_cfg,
        transform=build_eval_transform(train_cfg.image_size),
    )

    sampler = None
    shuffle = True
    if train_cfg.balanced_sampling:
        # Oversample panama so the gradient signal is not dominated by sigatoka.
        weights = torch.as_tensor(sample_weights(train_rows), dtype=torch.double)
        sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)
        shuffle = False

    common = {
        "batch_size": train_cfg.batch_size,
        "num_workers": train_cfg.num_workers,
        "pin_memory": True,
        "persistent_workers": train_cfg.num_workers > 0,
    }
    return (
        DataLoader(train_set, sampler=sampler, shuffle=shuffle, drop_last=True, **common),
        DataLoader(val_set, shuffle=False, **common),
    )


def evaluate_epoch(
    model: Any,
    loader: Any,
    criterion: Any,
    device: Any,
    *,
    channels_last: bool,
) -> tuple[float, ClassificationMetrics, np.ndarray]:
    """Run one validation pass. Returns ``(loss, metrics, logits)``."""
    import torch

    model.eval()
    losses: list[float] = []
    all_logits: list[np.ndarray] = []
    all_labels: list[np.ndarray] = []
    all_clusters: list[np.ndarray] = []

    with torch.no_grad():
        for batch in loader:
            images = batch["image"].to(device, non_blocking=True)
            if channels_last:
                images = images.to(memory_format=torch.channels_last)
            labels = batch["label"].to(device, non_blocking=True)

            logits = model(images)
            losses.append(float(criterion(logits, labels).item()))

            all_logits.append(logits.float().cpu().numpy())
            all_labels.append(labels.cpu().numpy())
            all_clusters.append(batch["cluster_id"].numpy())

    logits_array = np.concatenate(all_logits)
    labels_array = np.concatenate(all_labels)
    clusters_array = np.concatenate(all_clusters)

    metrics = compute_metrics(
        labels_array,
        logits_array.argmax(axis=1),
        cluster_ids=clusters_array,
    )
    return float(np.mean(losses)), metrics, logits_array


def train(
    manifest: pd.DataFrame,
    train_cfg: TrainConfig,
    data_cfg: DataConfig,
    paths: Paths,
    *,
    run_name: str | None = None,
    resume: Path | None = None,
) -> Path:
    """Train a classifier and return the run directory.

    Early stopping monitors macro-F1, never accuracy, for the imbalance reason documented in
    ``metrics.py``.
    """
    import torch
    from torch import nn

    set_seed(train_cfg.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    stamp = run_name or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    run_dir = paths.runs / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "config.json").write_text(
        json.dumps(
            {
                "train": train_cfg.model_dump(),
                "data": data_cfg.model_dump(mode="json"),
                "git_sha": _git_sha(),
                "device": str(device),
                "started": datetime.now(UTC).isoformat(),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    train_loader, val_loader = build_dataloaders(manifest, train_cfg, data_cfg, paths)

    model = build_model(train_cfg.model).to(device)
    if train_cfg.channels_last:
        model = model.to(memory_format=torch.channels_last)

    criterion = nn.CrossEntropyLoss(label_smoothing=train_cfg.optim.label_smoothing)
    optimizer = torch.optim.AdamW(
        parameter_groups(model, train_cfg.optim.learning_rate, train_cfg.optim.backbone_lr_scale),
        weight_decay=train_cfg.optim.weight_decay,
    )

    steps_per_epoch = max(len(train_loader) // train_cfg.grad_accum_steps, 1)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=[group["lr"] for group in optimizer.param_groups],
        epochs=train_cfg.epochs,
        steps_per_epoch=steps_per_epoch,
        pct_start=min(train_cfg.optim.warmup_epochs / max(train_cfg.epochs, 1), 0.5),
    )

    # T4 is Turing: fp16 only, and fp16 needs a loss scaler to avoid gradient underflow.
    use_amp = train_cfg.amp and device.type == "cuda"
    amp_dtype = torch.float16 if train_cfg.amp_dtype == "float16" else torch.bfloat16
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp and amp_dtype == torch.float16)

    start_epoch = 0
    best_score = -1.0
    epochs_without_improvement = 0
    history: list[dict[str, Any]] = []

    if resume and resume.is_file():
        payload = torch.load(resume, map_location=device, weights_only=False)
        model.load_state_dict(payload["state_dict"])
        if "optimizer" in payload:
            optimizer.load_state_dict(payload["optimizer"])
        start_epoch = int(payload.get("epoch", 0)) + 1
        best_score = float(payload.get("best_score", -1.0))
        history = list(payload.get("history", []))
        print(f"Resumed from {resume} at epoch {start_epoch}")

    for epoch in range(start_epoch, train_cfg.epochs):
        started = time.time()
        model.train()
        batch_losses: list[float] = []
        optimizer.zero_grad(set_to_none=True)

        for step, batch in enumerate(train_loader):
            images = batch["image"].to(device, non_blocking=True)
            if train_cfg.channels_last:
                images = images.to(memory_format=torch.channels_last)
            labels = batch["label"].to(device, non_blocking=True)

            with torch.autocast(device.type, dtype=amp_dtype, enabled=use_amp):
                loss = criterion(model(images), labels) / train_cfg.grad_accum_steps

            scaler.scale(loss).backward()
            batch_losses.append(float(loss.item()) * train_cfg.grad_accum_steps)

            if (step + 1) % train_cfg.grad_accum_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                if scheduler.last_epoch < scheduler.total_steps - 1:
                    scheduler.step()

        val_loss, val_metrics, _ = evaluate_epoch(
            model, val_loader, criterion, device, channels_last=train_cfg.channels_last
        )

        result = EpochResult(
            epoch=epoch,
            train_loss=float(np.mean(batch_losses)),
            val_loss=val_loss,
            val_macro_f1=val_metrics.macro_f1,
            val_accuracy=val_metrics.accuracy,
            val_panama_recall=val_metrics.panama_recall,
            learning_rate=float(optimizer.param_groups[-1]["lr"]),
            seconds=time.time() - started,
        )
        history.append(asdict(result))
        print(
            f"epoch {epoch + 1:>3}/{train_cfg.epochs}  "
            f"train {result.train_loss:.4f}  val {result.val_loss:.4f}  "
            f"{val_metrics.headline()}  ({result.seconds:.0f}s)"
        )

        score = getattr(val_metrics, train_cfg.monitor_metric, val_metrics.macro_f1)

        # Checkpoint every epoch: Colab disconnects, and losing a whole run to a dropped
        # session is avoidable with one file write.
        torch.save(
            {
                "state_dict": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "epoch": epoch,
                "best_score": max(best_score, score),
                "history": history,
                "train_config": train_cfg.model_dump(),
            },
            run_dir / "last.pt",
        )

        if score > best_score:
            best_score = score
            epochs_without_improvement = 0
            save_checkpoint(
                run_dir / "best.pt",
                model,
                train_cfg,
                val_metrics.to_dict(),
                extra={"epoch": epoch},
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= train_cfg.early_stop_patience:
                print(f"Early stop: no improvement for {train_cfg.early_stop_patience} epochs.")
                break

        pd.DataFrame(history).to_csv(run_dir / "history.csv", index=False)

    pd.DataFrame(history).to_csv(run_dir / "history.csv", index=False)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "best_" + train_cfg.monitor_metric: best_score,
                "epochs_run": len(history),
                "finished": datetime.now(UTC).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nBest {train_cfg.monitor_metric}: {best_score:.4f}\nRun directory: {run_dir}")
    return run_dir
