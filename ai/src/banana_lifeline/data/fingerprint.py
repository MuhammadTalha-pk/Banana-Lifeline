"""Perceptual fingerprinting and scene clustering.

This module exists because of a specific bug in the raw corpus. 440 of its 2,636 files are
``0`` -> ``P`` filename-corrupted copies (``2P2512P5_161415.jpg`` beside
``20251205_161415.jpg``), created by a find-and-replace that ran *before* the train/val/test
split. The copies were re-encoded as they were written, so they are byte-different: **MD5
deduplication reports the corpus perfectly clean while 59% of the holdout set sits in
train.**

Content hashing cannot see this. Perceptual hashing can. Everything downstream -- splits,
metrics, the model card -- keys on the ``cluster_id`` produced here rather than on filenames.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

from banana_lifeline.config import DataConfig, FingerprintConfig, Paths

# Popcount lookup for one byte. numpy>=2 has bitwise_count, but we support numpy 1.26 too.
_POPCOUNT_U8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


@dataclass(frozen=True, slots=True)
class ImageRecord:
    """One raw file, as found on disk."""

    path: Path
    split_original: str
    label_original: str
    filename: str


def dhash_from_image(image: Image.Image, size: int = 8) -> int:
    """Difference hash: compare each pixel to its right-hand neighbour.

    Robust to re-encoding, mild resizing, and JPEG quality changes -- exactly the
    transformations that made the duplicate copies in this corpus byte-different.
    """
    grey = image.convert("L").resize((size + 1, size), Image.Resampling.BILINEAR)
    pixels = np.asarray(grey, dtype=np.int16)
    bits = pixels[:, 1:] > pixels[:, :-1]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return value


def fingerprint_file(path: Path, cfg: FingerprintConfig) -> tuple[int, str, int, int, int]:
    """Return ``(dhash, md5, width, height, size_bytes)`` from a single read of the file.

    The file is read once into memory and used for both hashes. MD5 is kept even though it
    finds nothing here, because "content hashing says clean, perceptual hashing says 59%
    contaminated" is the finding, and the audit has to be able to demonstrate both halves.
    """
    raw = path.read_bytes()
    md5 = hashlib.md5(raw).hexdigest()

    with Image.open(io.BytesIO(raw)) as image:
        width, height = image.size
        # draft() lets libjpeg decode straight to a smaller size; ~10x faster on 5000px photos.
        target = cfg.dhash_size * cfg.decode_scale
        image.draft("L", (target, target))
        value = dhash_from_image(image, cfg.dhash_size)

    return value, md5, width, height, len(raw)


def discover_images(data_cfg: DataConfig, paths: Paths) -> list[ImageRecord]:
    """Walk the read-only raw corpus and record where each file currently sits.

    ``split_original`` captures the *contaminated* split so it can be reproduced for the
    comparison run. It is never used to decide what a model trains on.
    """
    root = data_cfg.resolved_raw_root(paths)
    if not root.is_dir():
        raise FileNotFoundError(f"Raw dataset not found at {root}")

    records: list[ImageRecord] = []
    for split in data_cfg.raw_splits:
        for label in data_cfg.class_names:
            folder = root / split / label
            if not folder.is_dir():
                continue
            for file_path in sorted(folder.glob(data_cfg.image_glob)):
                records.append(
                    ImageRecord(
                        path=file_path,
                        split_original=split,
                        label_original=label,
                        filename=file_path.name,
                    )
                )
    if not records:
        raise RuntimeError(f"No images matched {data_cfg.image_glob!r} under {root}")
    return records


def fingerprint_corpus(
    records: Sequence[ImageRecord],
    cfg: FingerprintConfig,
    *,
    show_progress: bool = True,
) -> pd.DataFrame:
    """Fingerprint every image into a tidy frame, one row per file."""
    rows: list[dict[str, object]] = []
    iterator: Iterable[ImageRecord] = records
    if show_progress:
        iterator = tqdm(records, desc="fingerprinting", unit="img")

    for record in iterator:
        try:
            value, md5, width, height, size_bytes = fingerprint_file(record.path, cfg)
        except Exception as exc:  # corrupt file: record it, never silently drop it
            rows.append(
                {
                    "filename": record.filename,
                    "split_original": record.split_original,
                    "label_original": record.label_original,
                    "relpath": str(record.path),
                    "dhash": None,
                    "md5": None,
                    "width": None,
                    "height": None,
                    "bytes": None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        rows.append(
            {
                "filename": record.filename,
                "split_original": record.split_original,
                "label_original": record.label_original,
                "relpath": str(record.path),
                "dhash": value,
                "md5": md5,
                "width": width,
                "height": height,
                "bytes": size_bytes,
                "error": None,
            }
        )

    return pd.DataFrame(rows)


def _hashes_to_bytes(hashes: Sequence[int], n_bits: int) -> np.ndarray:
    """Pack integer hashes into an ``(n, n_bytes)`` uint8 matrix for vectorised popcount."""
    n_bytes = (n_bits + 7) // 8
    packed = np.zeros((len(hashes), n_bytes), dtype=np.uint8)
    for row, value in enumerate(hashes):
        for byte_index in range(n_bytes):
            shift = 8 * (n_bytes - 1 - byte_index)
            packed[row, byte_index] = (value >> shift) & 0xFF
    return packed


class _UnionFind:
    __slots__ = ("parent", "rank")

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # path halving
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def cluster_hashes(
    hashes: Sequence[int],
    *,
    n_bits: int = 64,
    threshold: int = 5,
    chunk_size: int = 512,
) -> np.ndarray:
    """Group hashes into scenes via transitive closure of Hamming distance <= ``threshold``.

    Union-find over the thresholded pairwise distance matrix. Transitivity is deliberate:
    a burst of near-identical shots forms one chain, and the whole chain must land in the
    same split or the leak reopens through the middle of it.

    Returns dense cluster ids in ``[0, n_clusters)``, stable for a given input order.
    """
    n = len(hashes)
    if n == 0:
        return np.zeros(0, dtype=np.int64)

    packed = _hashes_to_bytes(hashes, n_bits)
    uf = _UnionFind(n)

    # Chunked upper-triangular scan: (chunk, n, n_bytes) uint8 stays well inside memory.
    for start in range(0, n, chunk_size):
        stop = min(start + chunk_size, n)
        block = packed[start:stop]
        xor = np.bitwise_xor(block[:, None, :], packed[None, :, :])
        distances = _POPCOUNT_U8[xor].sum(axis=2)

        rows, cols = np.nonzero(distances <= threshold)
        for row, col in zip(rows.tolist(), cols.tolist(), strict=True):
            global_row = start + row
            if global_row < col:  # upper triangle only; skips self-pairs too
                uf.union(global_row, col)

    roots = np.array([uf.find(i) for i in range(n)], dtype=np.int64)
    _, dense = np.unique(roots, return_inverse=True)
    return dense.astype(np.int64)


def build_clusters(
    data_cfg: DataConfig,
    paths: Paths,
    *,
    show_progress: bool = True,
) -> pd.DataFrame:
    """Full Phase-1 fingerprint pass: discover, hash, cluster.

    Returns one row per file with a ``cluster_id``. This frame is the single source of truth
    for every split decision downstream.
    """
    records = discover_images(data_cfg, paths)
    frame = fingerprint_corpus(records, data_cfg.fingerprint, show_progress=show_progress)

    usable = frame["error"].isna()
    n_bits = data_cfg.fingerprint.dhash_size**2
    cluster_ids = cluster_hashes(
        frame.loc[usable, "dhash"].astype("int64").tolist(),
        n_bits=n_bits,
        threshold=data_cfg.fingerprint.hamming_threshold,
    )

    frame["cluster_id"] = pd.Series(dtype="Int64")
    frame.loc[usable, "cluster_id"] = cluster_ids
    return frame
