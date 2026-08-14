"""Pre-resized image cache.

The raw corpus is 3.5 GB of 2--20 megapixel phone photos. Decoding those every epoch makes
training I/O-bound, and uploading them to a cloud GPU box is slow and expensive. Resizing
once to a 512px cache costs a few minutes and turns the dataset into roughly 200 MB.

512 is chosen against the 384px training resolution: large enough that random-resized-crop
still has headroom, small enough to stay cheap. Going lower would destroy Sigatoka's fine
speckling, which is the signal the classifier depends on.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from PIL import Image, ImageOps
from tqdm import tqdm

from banana_lifeline.config import CacheConfig, DataConfig, Paths


@dataclass(slots=True)
class CacheStats:
    written: int
    skipped: int
    failed: list[str]
    bytes_out: int

    @property
    def megabytes(self) -> float:
        return self.bytes_out / 1e6


def resize_one(source: Path, destination: Path, cfg: CacheConfig) -> int:
    """Resize one image, preserving aspect ratio. Returns bytes written."""
    with Image.open(source) as handle:
        # Phone photos carry EXIF rotation; bake it in now so orientation is consistent
        # everywhere downstream and never depends on the decoder's EXIF handling.
        oriented = ImageOps.exif_transpose(handle) or handle
        image = oriented.convert("RGB")
        image.thumbnail((cfg.longest_side, cfg.longest_side), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="JPEG", quality=cfg.jpeg_quality, optimize=True)
    return destination.stat().st_size


def build_cache(
    manifest: pd.DataFrame,
    data_cfg: DataConfig,
    paths: Paths,
    *,
    force: bool = False,
    workers: int = 8,
) -> CacheStats:
    """Materialise the resized cache for every file in a manifest.

    Idempotent: existing cache entries are skipped unless ``force``. Threaded because the
    work is PIL decode/encode, which releases the GIL.
    """
    raw_root = data_cfg.resolved_raw_root(paths)
    paths.cache.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[Path, Path]] = []
    skipped = 0
    for row in manifest.itertuples():
        source = raw_root / str(row.relpath)
        destination = paths.cache / str(row.cache_path)
        if destination.exists() and not force:
            skipped += 1
            continue
        jobs.append((source, destination))

    written = 0
    bytes_out = 0
    failed: list[str] = []

    def _run(job: tuple[Path, Path]) -> tuple[str, int | None]:
        source, destination = job
        try:
            return str(source), resize_one(source, destination, data_cfg.cache)
        except Exception as exc:
            return f"{source}: {type(exc).__name__}: {exc}", None

    if jobs:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for name, size in tqdm(
                pool.map(_run, jobs), total=len(jobs), desc="caching", unit="img"
            ):
                if size is None:
                    failed.append(name)
                else:
                    written += 1
                    bytes_out += size

    # Report the whole cache's size, not just this run's writes, so the number is meaningful
    # on a re-run where everything was skipped.
    total_bytes = sum(p.stat().st_size for p in paths.cache.glob("*.jpg"))

    return CacheStats(written=written, skipped=skipped, failed=failed, bytes_out=total_bytes)
