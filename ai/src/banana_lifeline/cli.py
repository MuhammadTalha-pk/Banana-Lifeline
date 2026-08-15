"""Command-line entry points for the Banana Lifeline AI layer.

Phase 1 is fully driven from here:

    banana audit      # fingerprint the corpus, measure contamination, write the report
    banana split      # group-aware split + quarantine + expert review sheet
    banana cache      # build the 512px training cache
    banana status     # what exists on disk right now
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from banana_lifeline.config import get_paths, load_data_config

# Windows consoles default to cp1252, which cannot encode Urdu. Since this CLI prints
# farmer questions verbatim, that turns a successful evaluation into a UnicodeEncodeError
# at the point of reporting the result -- losing the run, not just the formatting.
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(
    add_completion=False,
    help="Banana Lifeline — dataset, vision, and knowledge pipeline.",
    no_args_is_help=True,
)

CLUSTERS_FILENAME = "clusters.csv"


def _echo_header(text: str) -> None:
    typer.secho(f"\n{text}", fg=typer.colors.CYAN, bold=True)


def _load_or_build_clusters(force: bool) -> pd.DataFrame:
    """Fingerprint the corpus, reusing the cached frame unless ``force``.

    Fingerprinting reads all 3.5 GB, so it is cached to disk; every later command reuses it.
    """
    from banana_lifeline.data.fingerprint import build_clusters

    paths = get_paths()
    data_cfg = load_data_config()
    destination = paths.manifests / CLUSTERS_FILENAME

    if destination.is_file() and not force:
        typer.echo(f"Reusing fingerprints from {destination} (--force to recompute)")
        return pd.read_csv(destination)

    typer.echo("Fingerprinting the raw corpus (reads every file once)...")
    frame = build_clusters(data_cfg, paths)
    paths.manifests.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    typer.echo(f"Wrote {destination}")
    return frame


@app.command()
def audit(
    force: bool = typer.Option(False, "--force", help="Recompute fingerprints from scratch."),
) -> None:
    """Measure dataset contamination and write reports/data_audit.md."""
    from banana_lifeline.data.audit import audit_clusters, write_report

    paths = get_paths()
    data_cfg = load_data_config()
    frame = _load_or_build_clusters(force)
    result = audit_clusters(frame, data_cfg)

    _echo_header("Contamination")
    typer.echo(f"  files                      {result.n_files}")
    typer.echo(f"  unique MD5 (byte-level)    {result.n_unique_md5}")
    typer.echo(f"  unique scenes (perceptual) {result.n_clusters}")
    typer.echo(f"  corrupted filenames        {result.n_corrupted_names}")
    typer.echo(f"  scenes spanning splits     {result.n_cross_split_clusters}")

    rate = result.holdout_contamination_rate * 100
    colour = typer.colors.RED if rate > 5 else typer.colors.GREEN
    typer.secho(
        f"  holdout with train twin    {result.n_holdout_with_train_twin}"
        f"/{result.n_holdout_total} ({rate:.0f}%)",
        fg=colour,
        bold=True,
    )
    typer.secho(f"  label-conflict scenes      {len(result.conflict_clusters)}", fg=colour)

    _echo_header("Scenes per class")
    for label, count in result.scenes_per_class.items():
        typer.echo(f"  {label:<10} {result.files_per_class[label]:>5} files  {count:>5} scenes")

    destination = write_report(result, frame[frame["error"].isna()], data_cfg, paths)
    typer.secho(f"\nReport written to {destination}", fg=typer.colors.GREEN)


@app.command()
def split(
    force: bool = typer.Option(False, "--force", help="Recompute fingerprints from scratch."),
) -> None:
    """Generate the leakage-free split, the comparison split, and the review sheet."""
    from banana_lifeline.data.review import write_review_page
    from banana_lifeline.data.split import (
        build_clean_split,
        build_original_split,
        summarise,
        to_manifest,
        verify_no_leakage,
    )
    from banana_lifeline.data.verdicts import load_if_present

    paths = get_paths()
    data_cfg = load_data_config()
    frame = _load_or_build_clusters(force)

    # Expert rulings, when recorded, pull contested scenes back into training.
    verdicts = load_if_present(paths)
    if verdicts is not None:
        typer.secho(
            f"Applying expert verdicts: {verdicts.n_resolved} scenes resolved, "
            f"{verdicts.n_discarded} discarded.",
            fg=typer.colors.CYAN,
        )

    clean, quarantine = build_clean_split(frame, data_cfg, verdicts)
    original = build_original_split(frame, quarantine)

    clean_manifest = to_manifest(clean, data_cfg, paths)
    original_manifest = to_manifest(original, data_cfg, paths)

    verify_no_leakage(clean_manifest)

    paths.manifests.mkdir(parents=True, exist_ok=True)
    clean_manifest.to_csv(paths.manifests / "splits_clean.csv", index=False)
    original_manifest.to_csv(paths.manifests / "splits_original.csv", index=False)

    summary = summarise(clean, quarantine)
    _echo_header("Clean split (group-aware, no scene spans two splits)")
    for split_name in ("train", "val", "test"):
        files = summary.files_per_split.get(split_name, 0)
        scenes = summary.scenes_per_split.get(split_name, 0)
        typer.echo(f"  {split_name:<6} {files:>5} files   {scenes:>5} scenes")
    typer.echo(f"\n{summary.class_matrix.to_string()}")

    if summary.n_quarantined_files:
        review_path = write_review_page(quarantine, data_cfg, paths)
        quarantine_manifest = to_manifest(quarantine.assign(label="unknown"), data_cfg, paths)
        quarantine_manifest.to_csv(paths.manifests / "splits_quarantine.csv", index=False)
        typer.secho(
            f"\nQuarantined {summary.n_quarantined_files} files "
            f"across {summary.n_quarantined_scenes} contested scenes.",
            fg=typer.colors.YELLOW,
        )
        typer.echo(f"  Expert review sheet: {review_path}")

    typer.secho("\nLeakage check passed: no scene spans two splits.", fg=typer.colors.GREEN)


@app.command(name="import-verdicts")
def import_verdicts(
    path: Path | None = typer.Option(
        None, help="Verdicts CSV. Defaults to data/review/verdicts.csv."
    ),
    apply: bool = typer.Option(True, help="Regenerate the manifests with the verdicts applied."),
) -> None:
    """Validate expert rulings on contested scenes and fold them into the split."""
    from banana_lifeline.data.split import resolve_cluster_labels
    from banana_lifeline.data.verdicts import coverage_report, load_verdicts, verdicts_path

    paths = get_paths()
    source = path or verdicts_path(paths)

    # Validate against the *originally* contested scenes, recomputed from the fingerprints --
    # not against splits_quarantine.csv. That file shrinks as verdicts are applied, so using
    # it would make this command reject its own output on a second run.
    frame = _load_or_build_clusters(force=False)
    _, contested = resolve_cluster_labels(frame[frame["error"].isna()])
    quarantined = set(contested)

    # A missing or malformed verdicts file is ordinary user error, not a crash.
    try:
        verdicts = load_verdicts(source, quarantined=quarantined)
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(f"\n{exc}", fg=typer.colors.RED)
        raise typer.Exit(1) from None

    decided, pending = coverage_report(verdicts, quarantined)

    _echo_header("Verdicts")
    typer.echo(f"  resolved to a class  {verdicts.n_resolved}")
    typer.echo(f"  discarded            {verdicts.n_discarded}")

    counts: dict[str, int] = {}
    for label in verdicts.labels.values():
        counts[label] = counts.get(label, 0) + 1
    for label, count in sorted(counts.items()):
        typer.echo(f"    -> {label:<10} {count}")

    if pending:
        typer.secho(
            f"\n  {len(pending)} scenes still undecided: {sorted(pending)}",
            fg=typer.colors.YELLOW,
        )
        typer.echo("  These stay excluded from training until ruled on.")
    else:
        typer.secho(f"\n  All {len(decided)} contested scenes decided.", fg=typer.colors.GREEN)

    if apply:
        typer.echo("\nRegenerating manifests with verdicts applied...")
        split(force=False)


@app.command()
def cache(
    variant: str = typer.Option("clean", help="Manifest to cache: clean | original."),
    force: bool = typer.Option(False, "--force", help="Rewrite entries that already exist."),
    workers: int = typer.Option(8, help="Parallel resize workers."),
) -> None:
    """Build the pre-resized training cache."""
    from banana_lifeline.data.cache import build_cache
    from banana_lifeline.data.dataset import load_manifest, manifest_path

    paths = get_paths()
    data_cfg = load_data_config()
    manifest = load_manifest(manifest_path(paths, variant))

    stats = build_cache(manifest, data_cfg, paths, force=force, workers=workers)
    _echo_header("Cache")
    typer.echo(f"  written {stats.written}   skipped {stats.skipped}   failed {len(stats.failed)}")
    typer.echo(f"  total   {stats.megabytes:.0f} MB at {paths.cache}")
    for failure in stats.failed[:5]:
        typer.secho(f"  ! {failure}", fg=typer.colors.RED)


@app.command(name="train")
def train_command(
    variant: str = typer.Option("clean", help="Manifest to train on: clean | original."),
    config: Path | None = typer.Option(None, help="Training config; default configs/train.yaml."),
    epochs: int | None = typer.Option(None, help="Override the epoch count."),
    batch_size: int | None = typer.Option(None, help="Override batch size (lower this on OOM)."),
    run_name: str | None = typer.Option(None, help="Run directory name; default a timestamp."),
    resume: Path | None = typer.Option(
        None, help="Checkpoint to resume from, e.g. runs/<id>/last.pt."
    ),
) -> None:
    """Train the disease classifier."""
    from banana_lifeline.config import load_train_config
    from banana_lifeline.data.dataset import load_manifest, manifest_path
    from banana_lifeline.vision.train import train as run_training

    paths = get_paths()
    data_cfg = load_data_config()
    train_cfg = load_train_config(config)

    overrides = {}
    if epochs is not None:
        overrides["epochs"] = epochs
    if batch_size is not None:
        overrides["batch_size"] = batch_size
    if overrides:
        train_cfg = train_cfg.model_copy(update=overrides)

    manifest = load_manifest(manifest_path(paths, variant))

    _echo_header(f"Training on the {variant} split")
    typer.echo(f"  architecture   {train_cfg.model.architecture}")
    typer.echo(f"  resolution     {train_cfg.image_size}px")
    typer.echo(f"  batch          {train_cfg.batch_size} x {train_cfg.grad_accum_steps} accum")
    typer.echo(f"  precision      {'amp:' + train_cfg.amp_dtype if train_cfg.amp else 'fp32'}")
    typer.echo(f"  monitoring     {train_cfg.monitor_metric}")
    typer.echo(f"  train images   {(manifest['split'] == 'train').sum()}")

    run_dir = run_training(manifest, train_cfg, data_cfg, paths, run_name=run_name, resume=resume)
    typer.secho(f"\nRun complete: {run_dir}", fg=typer.colors.GREEN)


@app.command(name="evaluate")
def evaluate_command(
    clean_run: Path = typer.Option(..., help="Run dir or checkpoint trained on the clean split."),
    original_run: Path | None = typer.Option(
        None, help="Run dir or checkpoint trained on the contaminated split, for comparison."
    ),
    ablation: bool = typer.Option(True, help="Run the background-shortcut ablation."),
    gradcam: bool = typer.Option(True, help="Write Grad-CAM overlays."),
) -> None:
    """Evaluate on the test set and write the honest-vs-contaminated comparison."""
    from banana_lifeline.data.dataset import load_manifest, manifest_path
    from banana_lifeline.vision.calibrate import calibrate
    from banana_lifeline.vision.evaluate import (
        background_ablation,
        comparison_report,
        predict,
        write_evaluation,
    )
    from banana_lifeline.vision.model import load_checkpoint

    paths = get_paths()
    data_cfg = load_data_config()

    def _resolve(path: Path) -> Path:
        return path / "best.pt" if path.is_dir() else path

    loaded = load_checkpoint(_resolve(clean_run))
    train_cfg = loaded.train_config

    clean_manifest = load_manifest(manifest_path(paths, "clean"))
    test_rows = clean_manifest[clean_manifest["split"] == "test"]
    val_rows = clean_manifest[clean_manifest["split"] == "val"]

    _echo_header("Evaluating on the clean test split")
    clean_output = predict(loaded.model, test_rows, train_cfg, data_cfg, paths)
    typer.echo(f"  {clean_output.metrics.headline()}")

    # Calibration is fitted on validation, never on test: fitting on test would leak.
    val_output = predict(loaded.model, val_rows, train_cfg, data_cfg, paths)
    calibration = calibrate(val_output.logits, val_output.labels)
    typer.echo(f"  {calibration.summary()}")

    original_metrics = clean_output.metrics
    if original_run is not None:
        original_loaded = load_checkpoint(_resolve(original_run))
        original_manifest = load_manifest(manifest_path(paths, "original"))
        original_metrics = predict(
            original_loaded.model,
            original_manifest[original_manifest["split"] == "test"],
            original_loaded.train_config,
            data_cfg,
            paths,
        ).metrics
        typer.echo(f"  contaminated split: {original_metrics.headline()}")
    else:
        typer.secho(
            "  No --original-run given; the comparison table will be incomplete.",
            fg=typer.colors.YELLOW,
        )

    ablation_metrics = None
    if ablation:
        ablation_metrics = background_ablation(loaded.model, test_rows, train_cfg, data_cfg, paths)
        drop = clean_output.metrics.macro_f1 - ablation_metrics.macro_f1
        colour = typer.colors.GREEN if drop < 0.10 else typer.colors.RED
        typer.secho(f"  background ablation: macro-F1 drops {drop:.3f}", fg=colour)

    report = comparison_report(
        clean_output.metrics,
        original_metrics,
        ablation=ablation_metrics,
        calibration=calibration.to_dict(),
    )
    destination = write_evaluation(
        report,
        {
            "clean": clean_output.metrics.to_dict(),
            "original": original_metrics.to_dict(),
            "ablation": ablation_metrics.to_dict() if ablation_metrics else None,
            "calibration": calibration.to_dict(),
        },
        paths,
    )
    typer.secho(f"\nReport written to {destination}", fg=typer.colors.GREEN)

    if gradcam:
        from banana_lifeline.vision.explain import generate_overlays

        overlay_dir = generate_overlays(loaded.model, test_rows, train_cfg, data_cfg, paths)
        typer.echo(f"Grad-CAM overlays: {overlay_dir}")


rag_app = typer.Typer(help="Knowledge corpus: fetch, build, query.", no_args_is_help=True)
app.add_typer(rag_app, name="rag")


@rag_app.command("sources")
def rag_sources() -> None:
    """List the source registry and what it covers."""
    from banana_lifeline.rag.sources import REGISTRY, coverage_summary

    _echo_header("Source registry")
    for source in REGISTRY:
        typer.echo(
            f"  {source.slug:<28} {source.source:<32} "
            f"{source.region:<8} {'/'.join(source.diseases)}"
        )

    summary = coverage_summary()
    _echo_header("Coverage")
    typer.echo(f"  documents      {summary['documents']}")
    for disease, count in summary["per_disease"].items():
        typer.echo(f"    {disease:<12} {count} sources")
    typer.echo(f"  regions        {', '.join(summary['regions'])}")

    if summary["pakistani_sources"] == 0:
        typer.secho(
            "\n  No Pakistani sources. Pesticide registration is jurisdiction-specific, so\n"
            "  chemical advice from these documents needs a 'verify local registration'\n"
            "  caveat until PARC or provincial extension material is added.",
            fg=typer.colors.YELLOW,
        )


@rag_app.command("fetch")
def rag_fetch(
    force: bool = typer.Option(False, "--force", help="Re-download sources already cached."),
    only: str | None = typer.Option(None, help="Fetch a single source by slug."),
) -> None:
    """Download the source documents and record their provenance."""
    from banana_lifeline.rag.fetch import fetch_all

    paths = get_paths()
    _echo_header("Fetching sources")
    typer.echo("  one at a time, with a delay between requests\n")

    results = fetch_all(paths, force=force, only=only)

    total = 0
    for result in results:
        if result.skipped:
            typer.secho(
                f"  -- {result.slug:<28} cached ({len(result.files)} files)",
                fg=typer.colors.BRIGHT_BLACK,
            )
        elif result.ok and result.error:
            typer.secho(f"  ~  {result.slug:<28} {result.error}", fg=typer.colors.YELLOW)
        elif result.ok:
            typer.secho(
                f"  OK {result.slug:<28} {len(result.files)} files, "
                f"{result.total_bytes / 1e6:.2f} MB",
                fg=typer.colors.GREEN,
            )
        else:
            typer.secho(f"  !! {result.slug:<28} {result.error}", fg=typer.colors.RED)
        total += result.total_bytes

    ok = sum(1 for r in results if r.ok)
    typer.echo(f"\n  {ok}/{len(results)} sources available, {total / 1e6:.1f} MB total")
    typer.echo(f"  {paths.corpus / 'raw'}")


@rag_app.command("parse")
def rag_parse() -> None:
    """Convert fetched documents into structured text."""
    from banana_lifeline.rag.parse import parse_corpus, write_text_corpus

    paths = get_paths()
    _echo_header("Parsing corpus")

    documents = parse_corpus(paths)
    usable = [d for d in documents if d.usable]
    rejected = [d for d in documents if not d.usable]

    by_slug: dict[str, list[int]] = {}
    for document in usable:
        by_slug.setdefault(document.slug, []).append(document.n_chars)

    for slug, sizes in sorted(by_slug.items()):
        typer.secho(
            f"  OK {slug:<28} {len(sizes):>2} docs  {sum(sizes):>8,} chars", fg=typer.colors.GREEN
        )

    for document in rejected:
        typer.secho(
            f"  !! {document.slug:<28} {document.filename}: {document.warning}",
            fg=typer.colors.YELLOW,
        )

    total = sum(d.n_chars for d in usable)
    headings = sum(d.n_headings for d in usable)
    typer.echo(
        f"\n  {len(usable)}/{len(documents)} documents usable, "
        f"{total:,} characters, {headings:,} headings"
    )
    typer.echo(f"  roughly {total // 4:,} tokens, ~{total // 1800:,} pages")

    destination = write_text_corpus(documents, paths)
    typer.secho(f"  written to {destination}", fg=typer.colors.GREEN)


@rag_app.command("chunk")
def rag_chunk() -> None:
    """Split parsed text into chunks and assign disease/topic metadata."""
    from banana_lifeline.rag.chunk import chunk_corpus, write_chunks
    from banana_lifeline.rag.classify import classify_chunks
    from banana_lifeline.rag.sources import REGISTRY

    paths = get_paths()
    _echo_header("Chunking")

    chunks = chunk_corpus(paths)
    declared = {s.slug: s.diseases for s in REGISTRY}
    stats = classify_chunks(chunks, declared)

    typer.echo(f"  chunks         {stats.n_chunks}")
    typer.echo(f"  mean tokens    {sum(c.n_tokens for c in chunks) // max(len(chunks), 1)}")

    _echo_header("Disease")
    for disease, count in stats.disease_counts.most_common():
        typer.echo(f"  {disease:<12} {count:>5}  ({count / stats.n_chunks:.0%})")

    _echo_header("Topic")
    for topic, count in stats.topic_counts.most_common():
        typer.echo(f"  {topic:<12} {count:>5}  ({count / stats.n_chunks:.0%})")

    if stats.ambiguous_disease:
        typer.secho(
            f"\n  {stats.ambiguous_disease} chunks from disease-specific documents stayed "
            "'general'.\n  Left unassigned deliberately: a chunk filed under the wrong "
            "disease is worse\n  than one filed under none, because the filter would surface "
            "it confidently.",
            fg=typer.colors.YELLOW,
        )

    destination = write_chunks(chunks, paths)
    typer.secho(f"\n  written to {destination}", fg=typer.colors.GREEN)


@rag_app.command("index")
def rag_index(
    model: str = typer.Option(None, help="Embedding model. Defaults to BAAI/bge-m3."),
    batch_size: int = typer.Option(8, help="Lower this if the machine runs out of memory."),
    recreate: bool = typer.Option(True, help="Drop and rebuild the collection."),
) -> None:
    """Embed the chunks and load them into Qdrant."""
    from banana_lifeline.rag.chunk import read_chunks
    from banana_lifeline.rag.embed import DEFAULT_MODEL, Embedder
    from banana_lifeline.rag.index import index_chunks

    paths = get_paths()
    chunks = read_chunks(paths)

    _echo_header("Indexing")
    typer.echo(f"  chunks   {len(chunks)}")
    typer.echo(f"  model    {model or DEFAULT_MODEL}")
    typer.echo("  first run downloads the model (~2 GB) and is slow on CPU\n")

    embedder = Embedder(model or DEFAULT_MODEL, batch_size=batch_size)
    embedder.load()
    typer.echo(
        f"  loaded   {embedder.model_name}  dim={embedder.dimension}  "
        f"sparse={'yes' if embedder.produces_sparse else 'no'}"
    )

    with typer.progressbar(length=len(chunks), label="  embedding") as bar:
        state = {"done": 0}

        def advance(done: int, _total: int) -> None:
            bar.update(done - state["done"])
            state["done"] = done

        stats = index_chunks(
            chunks, embedder, batch_size=batch_size, recreate=recreate, progress=advance
        )

    typer.secho(
        f"\n  {stats.n_points} points in '{stats.collection}' "
        f"(dim {stats.dense_dim}, sparse {'on' if stats.has_sparse else 'off'})",
        fg=typer.colors.GREEN,
    )


@rag_app.command("ask")
def rag_ask(
    question: str = typer.Argument(..., help="The question, in English or Urdu."),
    disease: str = typer.Option(None, help="Disease from the CNN: panama | sigatoka."),
    topic: str = typer.Option(None, help="Narrow to a topic, e.g. treatment."),
    top_k: int = typer.Option(5, help="Passages to return."),
    rerank: bool = typer.Option(True, help="Cross-encoder reranking (slower, better)."),
) -> None:
    """Retrieve passages for a question."""
    from banana_lifeline.rag.retrieve import retrieve

    _echo_header("Retrieving")
    result = retrieve(question, disease=disease, topic=topic, top_k=top_k, rerank=rerank)

    if result.is_empty:
        typer.secho("  nothing found", fg=typer.colors.RED)
        raise typer.Exit(1)

    if result.fell_back:
        typer.secho("  (filters relaxed to find results)", fg=typer.colors.YELLOW)
    if result.is_weak:
        typer.secho(
            "  WEAK MATCH — generation should refuse rather than answer from this.",
            fg=typer.colors.YELLOW,
        )

    for rank, passage in enumerate(result.passages, 1):
        typer.secho(f"\n  [{rank}] {passage.score:.3f}  {passage.citation()}", fg=typer.colors.CYAN)
        typer.echo(f"      {passage.disease}/{passage.topic} · {passage.region}")
        body = " ".join(passage.text.split())
        typer.echo(f"      {body[:260]}...")


@rag_app.command("eval")
def rag_eval(
    top_k: int = typer.Option(5, help="Cut-off for recall."),
    rerank: bool = typer.Option(True, help="Cross-encoder reranking."),
) -> None:
    """Score retrieval against the golden set."""
    from banana_lifeline.rag.embed import Embedder
    from banana_lifeline.rag.eval import evaluate_retrieval, write_report
    from banana_lifeline.rag.golden import GOLDEN_SET
    from banana_lifeline.rag.retrieve import retrieve

    paths = get_paths()
    embedder = Embedder()
    embedder.load()

    _echo_header("Evaluating retrieval")
    typer.echo(
        f"  {len(GOLDEN_SET)} questions "
        f"({sum(1 for q in GOLDEN_SET if q.unanswerable)} unanswerable)\n"
    )

    def retriever(question: str, disease: str | None, topic: str | None) -> Any:
        return retrieve(
            question, disease=disease, topic=topic, embedder=embedder, top_k=top_k, rerank=rerank
        )

    with typer.progressbar(GOLDEN_SET, label="  querying") as bar:
        report = evaluate_retrieval(list(bar), retriever, top_k=top_k)

    typer.secho(f"\n  {report.summary()}", fg=typer.colors.GREEN, bold=True)

    if report.per_language:
        _echo_header("By language")
        for language, value in sorted(report.per_language.items()):
            typer.echo(f"  {language}   Recall@{top_k} {value:.2f}")

    misses = [r for r in report.results if r.correctly_refused is None and not r.hit_at_5]
    if misses:
        _echo_header(f"Missed ({len(misses)})")
        for miss in misses:
            typer.echo(f"  - {miss.question[:72]}")

    bad_refusals = [r for r in report.results if r.correctly_refused is False]
    if bad_refusals:
        _echo_header(f"Answered when it should have refused ({len(bad_refusals)})")
        for bad in bad_refusals:
            typer.secho(
                f"  - {bad.question[:60]} -> {bad.top_source} ({bad.top_score:.3f})",
                fg=typer.colors.RED,
            )

    destination = write_report(report, paths)
    typer.secho(f"\n  report: {destination}", fg=typer.colors.GREEN)


@app.command()
def status() -> None:
    """Show which pipeline artefacts currently exist."""
    paths = get_paths()
    data_cfg = load_data_config()

    artefacts: list[tuple[str, Path]] = [
        ("raw corpus", data_cfg.resolved_raw_root(paths)),
        ("fingerprints", paths.manifests / CLUSTERS_FILENAME),
        ("clean split", paths.manifests / "splits_clean.csv"),
        ("original split", paths.manifests / "splits_original.csv"),
        ("quarantine", paths.manifests / "splits_quarantine.csv"),
        ("review sheet", paths.review / "review.html"),
        ("audit report", paths.reports / "data_audit.md"),
        ("image cache", paths.cache),
    ]

    _echo_header(f"Banana Lifeline — {paths.ai_root}")
    for name, path in artefacts:
        exists = path.exists()
        mark = "OK " if exists else "-- "
        colour = typer.colors.GREEN if exists else typer.colors.BRIGHT_BLACK
        detail = ""
        if exists and path.is_dir():
            detail = f"  ({sum(1 for _ in path.glob('**/*.jpg'))} images)"
        typer.secho(f"  {mark} {name:<16} {path}{detail}", fg=colour)

    # Credentials: presence only. Values are never printed, logged, or written to a report.
    from banana_lifeline.secrets import load_credentials

    credentials = load_credentials()
    _echo_header("Service credentials (.env)")

    services: list[tuple[str, bool, str]] = [
        ("DeepSeek API key", credentials.has_deepseek, "needed for Phase 5 answer generation"),
        (
            "Qdrant URL",
            credentials.has_qdrant,
            "cluster endpoint, e.g. https://<id>.<region>.aws.cloud.qdrant.io:6333",
        ),
        ("Qdrant API key", bool(credentials.qdrant_api_key), "needed for Phase 4 retrieval"),
    ]
    for name, present, hint in services:
        mark = "OK " if present else "-- "
        colour = typer.colors.GREEN if present else typer.colors.YELLOW
        suffix = "" if present else f"   <- missing: {hint}"
        typer.secho(f"  {mark} {name:<18}{suffix}", fg=colour)

    if credentials.qdrant_api_key and not credentials.has_qdrant:
        typer.secho(
            "\n  A Qdrant API key without a cluster URL cannot connect. Find the URL on your\n"
            "  Qdrant Cloud dashboard under the cluster's Details tab, then add to .env:\n"
            "    QDRANT_URL=https://<cluster-id>.<region>.aws.cloud.qdrant.io:6333",
            fg=typer.colors.YELLOW,
        )


if __name__ == "__main__":
    app()
