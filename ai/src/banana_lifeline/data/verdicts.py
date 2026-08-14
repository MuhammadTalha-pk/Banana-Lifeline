"""Expert verdicts on label-conflict scenes.

Reads the CSV produced by ``data/review/review.html`` and validates it hard before it is
allowed to influence training data. A verdict changes what the model learns about the
panama/sigatoka boundary, so a typo here is a labelling error with real consequences --
every row is checked against the quarantine set and the class list, and anything unrecognised
raises rather than being silently dropped.

``discard`` is a first-class verdict: when a leaf photo genuinely cannot distinguish the two
diseases, excluding it is the correct call, not a failure to decide.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from banana_lifeline.config import CLASS_NAMES, Paths

DISCARD = "discard"
VALID_VERDICTS: frozenset[str] = frozenset({*CLASS_NAMES, DISCARD})
REQUIRED_COLUMNS: frozenset[str] = frozenset({"cluster_id", "verdict"})


@dataclass(slots=True)
class VerdictSet:
    """Validated expert rulings, keyed by scene."""

    labels: dict[int, str]
    """Scenes resolved to a real class; these re-enter training."""

    discarded: set[int]
    """Scenes the expert judged undecidable; these stay out."""

    notes: dict[int, str]

    @property
    def n_resolved(self) -> int:
        return len(self.labels)

    @property
    def n_discarded(self) -> int:
        return len(self.discarded)

    def resolved_label(self, cluster_id: int) -> str | None:
        return self.labels.get(cluster_id)


def verdicts_path(paths: Paths) -> Path:
    return paths.review / "verdicts.csv"


def load_verdicts(
    path: Path,
    *,
    quarantined: set[int] | None = None,
) -> VerdictSet:
    """Parse and validate a verdicts CSV.

    Raises on anything ambiguous rather than guessing: unknown columns are tolerated, but an
    unknown verdict, a duplicate ruling, or a ruling on a scene that was never contested is
    an error worth stopping for.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"No verdicts at {path}. Open data/review/review.html, record a decision for each "
            "scene, then click 'Download verdicts.csv' and save it into data/review/."
        )

    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {sorted(missing)}")

    frame = frame.dropna(subset=["cluster_id", "verdict"]).copy()
    frame["cluster_id"] = frame["cluster_id"].astype("int64")
    frame["verdict"] = frame["verdict"].astype(str).str.strip().str.lower()

    unknown = set(frame["verdict"]) - VALID_VERDICTS
    if unknown:
        raise ValueError(
            f"{path.name} contains unrecognised verdicts: {sorted(unknown)}. "
            f"Valid values are {sorted(VALID_VERDICTS)}."
        )

    duplicated = frame[frame.duplicated("cluster_id", keep=False)]
    if not duplicated.empty:
        raise ValueError(
            f"{path.name} rules on the same scene more than once: "
            f"{sorted(set(duplicated['cluster_id']))}"
        )

    if quarantined is not None:
        stray = set(frame["cluster_id"]) - quarantined
        if stray:
            raise ValueError(
                f"{path.name} rules on scenes that were never contested: {sorted(stray)}. "
                "Was it generated from a stale review sheet?"
            )

    # Pull columns out as plain lists: pandas row tuples are loosely typed, and these values
    # end up as training labels, so they are worth converting explicitly.
    ids: list[int] = [int(v) for v in frame["cluster_id"].tolist()]
    rulings: list[str] = [str(v) for v in frame["verdict"].tolist()]

    notes: dict[int, str] = {}
    if "reviewer_note" in frame.columns:
        raw_notes = frame["reviewer_note"].tolist()
        notes = {
            cluster_id: str(note).strip()
            for cluster_id, note in zip(ids, raw_notes, strict=True)
            if pd.notna(note) and str(note).strip()
        }

    return VerdictSet(
        labels={
            cluster_id: ruling
            for cluster_id, ruling in zip(ids, rulings, strict=True)
            if ruling != DISCARD
        },
        discarded={
            cluster_id for cluster_id, ruling in zip(ids, rulings, strict=True) if ruling == DISCARD
        },
        notes=notes,
    )


def load_if_present(paths: Paths, quarantined: set[int] | None = None) -> VerdictSet | None:
    """Load verdicts when they exist, otherwise return ``None``.

    Lets ``banana split`` pick verdicts up automatically once they are recorded, without
    needing a separate flag.
    """
    path = verdicts_path(paths)
    if not path.is_file():
        return None
    return load_verdicts(path, quarantined=quarantined)


def coverage_report(verdicts: VerdictSet, quarantined: set[int]) -> tuple[set[int], set[int]]:
    """Return ``(decided, still_pending)`` scene ids."""
    decided = set(verdicts.labels) | verdicts.discarded
    return decided, quarantined - decided
