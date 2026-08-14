"""Tests for expert verdict handling.

A verdict rewrites a training label on the panama/sigatoka boundary, which is the model's
hardest and most consequential distinction. So the loader is required to reject anything
ambiguous rather than interpret it charitably -- a silently dropped or misread row here is a
mislabelled scene nobody notices.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from banana_lifeline.data.verdicts import DISCARD, coverage_report, load_verdicts


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "verdicts.csv"
    path.write_text(body, encoding="utf-8")
    return path


def test_loads_labels_and_discards(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "cluster_id,verdict,reviewer_note\n"
        "348,sigatoka,clear streaking\n"
        "354,panama,\n"
        "360,discard,leaf photo cannot tell\n",
    )
    verdicts = load_verdicts(path)

    assert verdicts.labels == {348: "sigatoka", 354: "panama"}
    assert verdicts.discarded == {360}
    assert verdicts.notes[348] == "clear streaking"
    assert verdicts.resolved_label(360) is None


def test_verdicts_are_case_and_space_insensitive(tmp_path: Path) -> None:
    """Reviewers type by hand; casing should not silently drop a ruling."""
    path = _write(tmp_path, "cluster_id,verdict\n348, Sigatoka \n349,DISCARD\n")
    verdicts = load_verdicts(path)

    assert verdicts.labels == {348: "sigatoka"}
    assert verdicts.discarded == {349}


def test_rejects_unknown_verdict(tmp_path: Path) -> None:
    path = _write(tmp_path, "cluster_id,verdict\n348,blackspot\n")
    with pytest.raises(ValueError, match="unrecognised verdicts"):
        load_verdicts(path)


def test_rejects_duplicate_rulings(tmp_path: Path) -> None:
    """Two rulings on one scene means the reviewer changed their mind; ask, don't guess."""
    path = _write(tmp_path, "cluster_id,verdict\n348,panama\n348,sigatoka\n")
    with pytest.raises(ValueError, match="more than once"):
        load_verdicts(path)


def test_rejects_rulings_on_uncontested_scenes(tmp_path: Path) -> None:
    """Catches a verdicts file generated from a stale review sheet."""
    path = _write(tmp_path, "cluster_id,verdict\n999,panama\n")
    with pytest.raises(ValueError, match="never contested"):
        load_verdicts(path, quarantined={348, 354})


def test_rejects_missing_columns(tmp_path: Path) -> None:
    path = _write(tmp_path, "cluster,decision\n348,panama\n")
    with pytest.raises(ValueError, match="missing required columns"):
        load_verdicts(path)


def test_missing_file_explains_how_to_produce_one(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"review\.html"):
        load_verdicts(tmp_path / "nope.csv")


def test_blank_rows_are_ignored(tmp_path: Path) -> None:
    """Undecided scenes come back as empty rows; they are pending, not errors."""
    path = _write(tmp_path, "cluster_id,verdict\n348,panama\n,\n")
    assert load_verdicts(path).labels == {348: "panama"}


def test_coverage_report_lists_pending(tmp_path: Path) -> None:
    path = _write(tmp_path, "cluster_id,verdict\n348,panama\n")
    decided, pending = coverage_report(load_verdicts(path), {348, 354, 360})

    assert decided == {348}
    assert pending == {354, 360}


def test_verdicts_reinstate_contested_scenes_into_the_split() -> None:
    """End to end: a ruled scene rejoins training under the expert's label."""
    from banana_lifeline.config import DataConfig
    from banana_lifeline.data.split import build_clean_split
    from banana_lifeline.data.verdicts import VerdictSet

    frame = pd.DataFrame(
        [
            {
                "filename": f"{label}_{i}.jpg",
                "split_original": "train",
                "label_original": label,
                "relpath": f"train/{label}/{label}_{i}.jpg",
                "cluster_id": idx,
                "error": None,
            }
            for idx, (label, i) in enumerate(
                [(c, i) for c in ("healthy", "panama", "sigatoka") for i in range(8)]
            )
        ]
    )
    # A contested scene: same photo, two labels.
    contested_id = 999
    for label in ("panama", "sigatoka"):
        frame.loc[len(frame)] = {
            "filename": "contested.jpg",
            "split_original": "train",
            "label_original": label,
            "relpath": f"train/{label}/contested.jpg",
            "cluster_id": contested_id,
            "error": None,
        }

    _, quarantine = build_clean_split(frame, DataConfig())
    assert contested_id in set(quarantine["cluster_id"])

    verdicts = VerdictSet(labels={contested_id: "sigatoka"}, discarded=set(), notes={})
    clean, quarantine_after = build_clean_split(frame, DataConfig(), verdicts)

    assert contested_id not in set(quarantine_after["cluster_id"])
    reinstated = clean[clean["cluster_id"] == contested_id]
    assert set(reinstated["label"]) == {"sigatoka"}


def test_discarded_scenes_stay_out_of_training() -> None:
    from banana_lifeline.data.verdicts import VerdictSet

    verdicts = VerdictSet(labels={}, discarded={348}, notes={})
    assert verdicts.resolved_label(348) is None
    assert verdicts.n_resolved == 0
    assert verdicts.n_discarded == 1


def test_discard_is_a_valid_verdict_constant() -> None:
    assert DISCARD == "discard"


def test_applying_verdicts_twice_is_stable() -> None:
    """Importing verdicts must be idempotent.

    Once a ruling is applied the scene leaves quarantine, so validating against the *current*
    quarantine set would make the second run reject rulings it accepted on the first. The
    contested set must be recomputed from the fingerprints, which never change.
    """
    from banana_lifeline.config import DataConfig
    from banana_lifeline.data.split import build_clean_split, resolve_cluster_labels
    from banana_lifeline.data.verdicts import VerdictSet

    rows = [
        {
            "filename": f"{label}_{i}.jpg",
            "split_original": "train",
            "label_original": label,
            "relpath": f"train/{label}/{label}_{i}.jpg",
            "cluster_id": idx,
            "error": None,
        }
        for idx, (label, i) in enumerate(
            [(c, i) for c in ("healthy", "panama", "sigatoka") for i in range(8)]
        )
    ]
    for label in ("panama", "sigatoka"):
        rows.append(
            {
                "filename": "contested.jpg",
                "split_original": "train",
                "label_original": label,
                "relpath": f"train/{label}/contested.jpg",
                "cluster_id": 999,
                "error": None,
            }
        )
    frame = pd.DataFrame(rows)

    verdicts = VerdictSet(labels={999: "sigatoka"}, discarded=set(), notes={})

    # The contested set is a property of the corpus, not of the current quarantine file,
    # so it stays the same whether or not verdicts have already been applied.
    _, before = resolve_cluster_labels(frame)
    _, after = resolve_cluster_labels(frame, verdicts)
    assert before == after == [999]

    first, _ = build_clean_split(frame, DataConfig(), verdicts)
    second, _ = build_clean_split(frame, DataConfig(), verdicts)
    pd.testing.assert_frame_equal(first, second)
