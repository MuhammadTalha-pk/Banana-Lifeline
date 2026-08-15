"""Live view of an in-progress training run.

The run writes history.csv every epoch, so this reflects real progress even while stdout
is still sitting in a buffer. Ctrl-C to stop watching; it does not touch the training.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

RUNS = Path(__file__).parent / "runs"


def show() -> bool:
    """Print the current state. Returns True once everything looks finished."""
    finished = True
    for name in ("cpu_clean", "cpu_original"):
        history = RUNS / name / "history.csv"
        if not history.is_file():
            print(f"{name:14} not started")
            finished = False
            continue

        frame = pd.read_csv(history)
        if frame.empty:
            continue

        best = frame.loc[frame["val_macro_f1"].idxmax()]
        last = frame.iloc[-1]
        pace = frame["seconds"].tail(3).mean() / 60

        print(f"{name:14} epoch {int(last.epoch) + 1:>2}/20   "
              f"macro-F1 {last.val_macro_f1:.3f}   "
              f"panama {last.val_panama_recall:.3f}   "
              f"acc {last.val_accuracy:.3f}   "
              f"[best F1 {best.val_macro_f1:.3f} @ ep{int(best.epoch) + 1}]   "
              f"{pace:.1f} min/ep")

        if int(last.epoch) + 1 < 20:
            finished = False

    report = Path(__file__).parent / "reports" / "model_evaluation.md"
    if report.is_file():
        print("\nFINAL REPORT READY -> reports/model_evaluation.md")
        return True
    return False


if __name__ == "__main__":
    try:
        while True:
            print("\033[2J\033[H", end="")  # clear screen
            print(f"Banana Lifeline — training watch   {time.strftime('%H:%M:%S')}\n")
            if show():
                break
            print("\n(updates every 30s — Ctrl-C to stop watching; training keeps running)")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nstopped watching (training continues)")
