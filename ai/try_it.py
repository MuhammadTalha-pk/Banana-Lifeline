"""Interactive smoke test — run this to see the whole system work.

    python try_it.py                    # runs every check below
    python try_it.py path/to/photo.jpg  # diagnose your own photo

Must be run with the project venv (ai/.venv), not a system or Anaconda interpreter.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Fail with an explanation rather than a bare ModuleNotFoundError. The usual cause is running
# this with Anaconda or the system Python: the package is installed only in ai/.venv, and the
# project pins 3.11 because 3.13 lacks wheels for parts of the training stack.
try:
    from banana_lifeline.config import get_paths
except ModuleNotFoundError as exc:  # pragma: no cover - startup guard
    if exc.name != "banana_lifeline":
        raise

    here = Path(__file__).parent
    venv = here / (".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python")

    lines = [
        "banana_lifeline is not installed for this interpreter.",
        "",
        f"  you ran  : {sys.executable}   (Python {sys.version.split()[0]})",
        f"  you want : {venv}",
        "",
        "Run it with the project venv:",
        f"    {venv} {Path(__file__).name}",
        "",
        "If that venv does not exist yet:",
        "    py -3.11 -m venv .venv",
        '    .venv/Scripts/pip install -e ".[vision,rag,gen]"',
        "",
        "In VS Code: Ctrl+Shift+P -> 'Python: Select Interpreter' -> choose the .venv one.",
    ]
    print("\n".join(lines), file=sys.stderr)
    raise SystemExit(1) from None

import pandas as pd

paths = get_paths()


def rule(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}", flush=True)


def show(result: object, label: str = "") -> None:
    r = result
    print(f"{label}action={r.action}  disease={r.disease}  confidence={r.confidence:.3f}")
    if r.message:
        print(f"  message: {r.message[:120]}")
    if r.follow_up_questions:
        print(f"  asks {len(r.follow_up_questions)} follow-up questions:")
        for question in r.follow_up_questions:
            print(f"    - {question}")
    if r.answer:
        print(f"  answer ({len(r.citations)} sources): {' '.join(r.answer.split())[:220]}...")
    if r.safety_violations:
        print(f"  safety: {r.safety_violations}")


def main() -> int:
    from banana_lifeline.pipeline import ask, diagnose

    if len(sys.argv) > 1:
        rule(f"Your photo: {sys.argv[1]}")
        show(diagnose(sys.argv[1]))
        return 0

    import numpy as np
    from PIL import Image

    manifest = pd.read_csv(paths.manifests / "splits_clean.csv")
    test = manifest[manifest["split"] == "test"]
    scratch = Path(tempfile.gettempdir())

    rule("1. Real test photos, one per class")
    for label in ("healthy", "sigatoka", "panama"):
        row = test[test["label"] == label].iloc[0]
        show(diagnose(paths.cache / str(row["cache_path"]), generate=False), f"{label:9} ")

    rule("2. A photo that is not a banana leaf")
    junk = scratch / "not_a_leaf.jpg"
    Image.fromarray(np.full((400, 400, 3), 128, dtype=np.uint8)).save(junk)
    show(diagnose(junk, generate=False), "flat grey ")

    rule("3. A blurry photo")
    blurry = scratch / "blurry.jpg"
    base = np.zeros((400, 400, 3), dtype=np.uint8)
    base[:, :, 0], base[:, :, 1], base[:, :, 2] = 110, 150, 60
    Image.fromarray(base).save(blurry)
    show(diagnose(blurry, generate=False), "blurry    ")

    rule("4. A question with no photo (English)")
    show(ask("How much space should I leave between banana plants?"))

    rule("5. The same kind of question in Urdu")
    show(ask("کیلے کی فصل کے لیے کون سی مٹی بہترین ہے؟", language="ur"))

    rule("6. Asking for a Panama cure — the safety rule should block this")
    show(ask("What fungicide will cure Panama disease?", disease="panama"))

    rule("7. A question the corpus cannot answer — should refuse")
    show(ask("What is the market price of bananas in Lahore today?"))

    print("\nDone.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
