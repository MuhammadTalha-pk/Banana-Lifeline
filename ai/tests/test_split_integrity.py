"""Regression tests for the dataset leakage bug.

The raw corpus shipped with a train/val/test split in which 59% of held-out images had a
near-identical twin in training, because the split was made on filenames after a
find-and-replace had duplicated the library. These tests exist so that bug cannot come back
quietly. ``test_clean_manifest_has_no_scene_overlap`` is the important one: if it ever fails,
every metric in the project is invalid.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from banana_lifeline.config import CLASS_NAMES, DataConfig, get_paths
from banana_lifeline.data.dataset import class_weights, load_manifest, manifest_path
from banana_lifeline.data.fingerprint import cluster_hashes, dhash_from_image
from banana_lifeline.data.split import (
    build_clean_split,
    build_original_split,
    resolve_cluster_labels,
    verify_no_leakage,
)

# --------------------------------------------------------------------------------------
# Unit tests — no corpus required
# --------------------------------------------------------------------------------------


def test_dhash_is_stable_under_jpeg_reencoding() -> None:
    """The property the whole audit rests on: re-encoding changes bytes, not the fingerprint.

    This is precisely what defeated MD5 deduplication on the raw corpus.
    """
    from io import BytesIO

    from PIL import Image

    rng = np.random.default_rng(0)
    base = Image.fromarray(rng.integers(0, 255, (256, 256, 3), dtype=np.uint8))

    buffer = BytesIO()
    base.save(buffer, format="JPEG", quality=70)
    buffer.seek(0)
    reencoded = Image.open(buffer)

    original_hash = dhash_from_image(base)
    reencoded_hash = dhash_from_image(reencoded)

    distance = bin(original_hash ^ reencoded_hash).count("1")
    assert distance <= 5, f"re-encoding shifted the fingerprint by {distance} bits"


def test_cluster_hashes_groups_near_duplicates() -> None:
    """Hashes within the threshold merge; distant hashes stay apart."""
    hashes = [
        0b0000_0000,
        0b0000_0001,  # 1 bit from the first -> same scene
        0b1111_1111,  # far away -> its own scene
    ]
    clusters = cluster_hashes(hashes, n_bits=8, threshold=2)
    assert clusters[0] == clusters[1]
    assert clusters[2] != clusters[0]


def test_cluster_hashes_is_transitive() -> None:
    """A chain of near-duplicates forms one scene.

    Burst photos drift gradually: A~B and B~C while A and C exceed the threshold. Without
    transitivity the chain would be cut in the middle and leak across splits.
    """
    hashes = [0b0000_0000, 0b0000_0011, 0b0000_1111]
    clusters = cluster_hashes(hashes, n_bits=8, threshold=2)
    assert len(set(clusters.tolist())) == 1


def test_cluster_hashes_empty_input() -> None:
    assert cluster_hashes([], n_bits=64, threshold=5).size == 0


def _synthetic_frame() -> pd.DataFrame:
    """A miniature corpus reproducing the real failure modes."""
    rows = []
    cluster_id = 0
    for label in CLASS_NAMES:
        for scene in range(12):
            # Duplicate copies of one scene, deliberately scattered across splits.
            for copy in range(2 if scene % 3 == 0 else 1):
                rows.append(
                    {
                        "filename": f"{label}_{scene}_{copy}.jpg",
                        "split_original": ["train", "val", "test"][(scene + copy) % 3],
                        "label_original": label,
                        "relpath": f"train/{label}/{label}_{scene}_{copy}.jpg",
                        "cluster_id": cluster_id,
                        "error": None,
                    }
                )
            cluster_id += 1

    # One contested scene: the same photo labelled two ways, as in the real corpus.
    for split_name, label in (("train", "panama"), ("test", "sigatoka")):
        rows.append(
            {
                "filename": "contested.jpg",
                "split_original": split_name,
                "label_original": label,
                "relpath": f"{split_name}/{label}/contested.jpg",
                "cluster_id": cluster_id,
                "error": None,
            }
        )
    return pd.DataFrame(rows)


def test_contested_scenes_are_quarantined_not_voted() -> None:
    """A scene with disagreeing labels must never be silently assigned one."""
    frame = _synthetic_frame()
    labels, contested = resolve_cluster_labels(frame)

    assert len(contested) == 1
    assert pd.isna(labels[contested[0]])


def test_clean_split_keeps_scenes_intact() -> None:
    frame = _synthetic_frame()
    clean, quarantine = build_clean_split(frame, DataConfig())

    verify_no_leakage(clean)
    assert len(quarantine) == 2
    assert set(clean["split"]) <= {"train", "val", "test"}


def test_original_split_excludes_quarantined_scenes() -> None:
    """Both manifests drop contested scenes so the comparison isolates one variable."""
    frame = _synthetic_frame()
    clean, quarantine = build_clean_split(frame, DataConfig())
    original = build_original_split(frame, quarantine)

    contested = set(quarantine["cluster_id"])
    assert not contested & set(original["cluster_id"])
    assert not contested & set(clean["cluster_id"])


def test_verify_no_leakage_detects_a_leak() -> None:
    """The guard itself must actually fire."""
    leaking = pd.DataFrame(
        {"cluster_id": [1, 1], "split": ["train", "test"], "relpath": ["a.jpg", "b.jpg"]}
    )
    with pytest.raises(AssertionError, match="leaking"):
        verify_no_leakage(leaking)


def test_split_is_deterministic() -> None:
    frame = _synthetic_frame()
    first, _ = build_clean_split(frame, DataConfig())
    second, _ = build_clean_split(frame, DataConfig())
    pd.testing.assert_frame_equal(first, second)


def test_class_weights_favour_the_rare_class() -> None:
    """Panama is ~4x rarer than sigatoka; weighting must compensate."""
    frame = pd.DataFrame({"label": ["sigatoka"] * 80 + ["panama"] * 20})
    weights = class_weights(frame)
    assert weights[CLASS_NAMES.index("panama")] > weights[CLASS_NAMES.index("sigatoka")]


# --------------------------------------------------------------------------------------
# Integration tests — run against the generated manifests when they exist
# --------------------------------------------------------------------------------------


def _manifest_or_skip(variant: str) -> pd.DataFrame:
    path = manifest_path(get_paths(), variant)
    if not path.is_file():
        pytest.skip(f"{path.name} not generated yet; run `banana split`")
    return load_manifest(path)


def test_clean_manifest_has_no_scene_overlap() -> None:
    """THE regression test. If this fails, every reported metric is invalid."""
    manifest = _manifest_or_skip("clean")
    verify_no_leakage(manifest)

    by_split = {split: set(group["cluster_id"]) for split, group in manifest.groupby("split")}
    for left in by_split:
        for right in by_split:
            if left < right:
                overlap = by_split[left] & by_split[right]
                assert not overlap, f"{len(overlap)} scenes shared between {left} and {right}"


def test_clean_manifest_covers_every_class_in_every_split() -> None:
    manifest = _manifest_or_skip("clean")
    for split in ("train", "val", "test"):
        present = set(manifest[manifest["split"] == split]["label"])
        assert present == set(CLASS_NAMES), f"{split} is missing {set(CLASS_NAMES) - present}"


def test_quarantined_scenes_never_reach_training() -> None:
    quarantine_path = manifest_path(get_paths(), "quarantine")
    if not quarantine_path.is_file():
        pytest.skip("no quarantined scenes")

    contested = set(pd.read_csv(quarantine_path)["cluster_id"])
    for variant in ("clean", "original"):
        manifest = _manifest_or_skip(variant)
        leaked = contested & set(manifest["cluster_id"])
        assert not leaked, f"{len(leaked)} contested scenes leaked into splits_{variant}.csv"


def test_original_manifest_is_still_contaminated() -> None:
    """Sanity check on the comparison baseline.

    The original split is kept *because* it leaks. If this ever passes a leakage check, the
    wrong file is being written and the comparison is meaningless.
    """
    manifest = _manifest_or_skip("original")
    spans = manifest.groupby("cluster_id")["split"].nunique()
    assert (spans > 1).sum() > 0, "expected the preserved original split to still leak"


def test_manifests_reference_files_that_exist() -> None:
    manifest = _manifest_or_skip("clean")
    paths = get_paths()
    root = DataConfig().resolved_raw_root(paths)
    if not root.is_dir():
        pytest.skip(f"raw corpus is not available at {root}")
    sample = manifest.sample(min(50, len(manifest)), random_state=0)
    for relpath in sample["relpath"]:
        assert (root / str(relpath)).is_file(), f"manifest points at a missing file: {relpath}"


def test_cache_paths_are_unique() -> None:
    """The 0->P bug means basenames repeat across folders; flattened names must not collide."""
    manifest = _manifest_or_skip("clean")
    assert manifest["cache_path"].is_unique
