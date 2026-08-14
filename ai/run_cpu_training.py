"""Unattended CPU training driver.

Runs the two comparison models back to back, then evaluates and writes the report.

Ordering matters: the clean (honest) split trains first. If the machine sleeps, the battery
dies, or anything else cuts the run short, the result that actually gets reported is the one
already finished.

Progress goes to reports/cpu_training.log as well as stdout, so the run can be inspected
after the fact without scrollback.
"""

from __future__ import annotations

import sys
import time
import traceback
from datetime import datetime

import pandas as pd

from banana_lifeline.config import get_paths, load_data_config, load_train_config
from banana_lifeline.data.dataset import load_manifest, manifest_path
from banana_lifeline.vision.train import train

paths = get_paths()
paths.reports.mkdir(parents=True, exist_ok=True)
LOG = paths.reports / "cpu_training.log"


def log(message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    data_cfg = load_data_config()
    train_cfg = load_train_config(paths.configs / "train_cpu.yaml")

    log("=" * 70)
    log("CPU training started")
    log(f"  {train_cfg.model.architecture} @ {train_cfg.image_size}px, "
        f"batch {train_cfg.batch_size}, up to {train_cfg.epochs} epochs")
    log(f"  monitoring {train_cfg.monitor_metric}, early stop after "
        f"{train_cfg.early_stop_patience} flat epochs")

    clean = load_manifest(manifest_path(paths, "clean"))
    original = load_manifest(manifest_path(paths, "original"))

    started = time.time()
    runs: dict[str, object] = {}

    # ---- 1. The honest split -----------------------------------------------------------
    log("\n--- RUN 1/2: clean split (the number that gets reported) ---")
    try:
        runs["clean"] = train(clean, train_cfg, data_cfg, paths, run_name="cpu_clean")
        log(f"clean run finished in {(time.time() - started) / 60:.0f} min")
    except Exception:
        log("clean run FAILED:\n" + traceback.format_exc())
        return 1

    # ---- 2. The contaminated split, for comparison --------------------------------------
    log("\n--- RUN 2/2: original contaminated split (for the comparison table) ---")
    mark = time.time()
    try:
        runs["original"] = train(original, train_cfg, data_cfg, paths, run_name="cpu_original")
        log(f"original run finished in {(time.time() - mark) / 60:.0f} min")
    except Exception:
        log("original run FAILED (clean result is still valid):\n" + traceback.format_exc())

    # ---- 3. Evaluate, calibrate, compare ------------------------------------------------
    log("\n--- Evaluation ---")
    try:
        from banana_lifeline.vision.calibrate import calibrate
        from banana_lifeline.vision.evaluate import (
            background_ablation,
            comparison_report,
            predict,
            write_evaluation,
        )
        from banana_lifeline.vision.model import load_checkpoint

        loaded = load_checkpoint(paths.runs / "cpu_clean" / "best.pt")
        test_rows = clean[clean["split"] == "test"]
        val_rows = clean[clean["split"] == "val"]

        clean_out = predict(loaded.model, test_rows, loaded.train_config, data_cfg, paths)
        log(f"HONEST  : {clean_out.metrics.headline()}")

        # Calibration is fitted on validation, never on test -- fitting on test leaks it.
        val_out = predict(loaded.model, val_rows, loaded.train_config, data_cfg, paths)
        calibration = calibrate(val_out.logits, val_out.labels)
        log(f"calibration: {calibration.summary()}")

        # Write the fitted calibration back into the checkpoint. Without this the file ships
        # temperature=1.0 and every consumer silently gets overconfident scores.
        from banana_lifeline.vision.model import attach_calibration

        attach_calibration(
            paths.runs / "cpu_clean" / "best.pt",
            temperature=calibration.temperature,
            abstain_threshold=calibration.threshold,
            extra={
                "coverage_at_threshold": calibration.coverage_at_threshold,
                "target_risk": calibration.target_risk,
                "ece_after": calibration.ece_after,
            },
        )
        log("calibration written into runs/cpu_clean/best.pt")

        original_metrics = clean_out.metrics
        if "original" in runs:
            other = load_checkpoint(paths.runs / "cpu_original" / "best.pt")
            original_metrics = predict(
                other.model,
                original[original["split"] == "test"],
                other.train_config,
                data_cfg,
                paths,
            ).metrics
            log(f"CLAIMED : {original_metrics.headline()}")

        ablation = background_ablation(
            loaded.model, test_rows, loaded.train_config, data_cfg, paths
        )
        drop = clean_out.metrics.macro_f1 - ablation.macro_f1
        verdict = "reading the leaf" if drop < 0.10 else "LIKELY BACKGROUND SHORTCUT"
        log(f"ablation: macro-F1 {clean_out.metrics.macro_f1:.3f} -> "
            f"{ablation.macro_f1:.3f} (drop {drop:.3f}) -- {verdict}")

        report = comparison_report(
            clean_out.metrics,
            original_metrics,
            ablation=ablation,
            calibration=calibration.to_dict(),
        )
        destination = write_evaluation(
            report,
            {
                "clean": clean_out.metrics.to_dict(),
                "original": original_metrics.to_dict(),
                "ablation": ablation.to_dict(),
                "calibration": calibration.to_dict(),
                "device": "cpu",
                "config": "train_cpu.yaml",
            },
            paths,
        )
        log(f"report written: {destination}")

        pd.DataFrame([clean_out.metrics.to_dict()]).to_json(
            paths.reports / "cpu_clean_metrics.json", orient="records", indent=2
        )
    except Exception:
        log("evaluation FAILED (checkpoints are still on disk):\n" + traceback.format_exc())
        return 1

    log(f"\nALL DONE in {(time.time() - started) / 60:.0f} min total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
