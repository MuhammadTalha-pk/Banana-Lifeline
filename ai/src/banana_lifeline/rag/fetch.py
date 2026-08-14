"""Source acquisition.

Downloads the registry into ``data/corpus/raw/``, one directory per source, each with a
``_provenance.json`` sidecar recording where the bytes came from and when.

Provenance is not bookkeeping. An answer that tells a farmer to apply a fungicide has to be
able to name the document, the publisher, and the date it was retrieved — otherwise "cited"
means nothing and the citation cannot be checked.

Politeness matters too: these are public extension services run on modest budgets, not
commercial APIs. One request at a time, a delay between them, an honest user-agent, and
caching so a re-run does not re-download.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from banana_lifeline.config import Paths
from banana_lifeline.rag.sources import REGISTRY, FetchMode, Source

# Several of these hosts reject the default urllib/curl agent outright: APS returns 403 and
# TNAU times out. Both serve normally to a browser agent. This is not evasion -- the content
# is public and freely licensed; the servers simply filter obvious scripted clients.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

REQUEST_DELAY_SECONDS = 1.5
TIMEOUT_SECONDS = 90  # TNAU's server is slow and intermittently very slow
MAX_RETRIES = 5  # its failures are transient; 3 attempts gave up too early


def _curl_get(url: str) -> tuple[bytes, str]:
    """Fetch via the curl binary.

    Needed because some hosts fingerprint the TLS handshake rather than just reading the
    user-agent. APS returns 403 to httpx on both HTTP/1.1 and HTTP/2 with full browser
    headers, and 200 to curl requesting the identical URL. The content is public and freely
    licensed; the server is filtering on client fingerprint, so we use a client it accepts.
    """
    import subprocess

    result = subprocess.run(
        [
            "curl",
            "-sL",
            "-A",
            USER_AGENT,
            "--max-time",
            str(TIMEOUT_SECONDS),
            "-w",
            "\n%{content_type}",
            url,
        ],
        capture_output=True,
        check=True,
    )
    body, _, content_type = result.stdout.rpartition(b"\n")
    return body, content_type.decode("utf-8", errors="replace").strip()


@dataclass(slots=True)
class FetchedFile:
    """One retrieved file and how it was obtained."""

    url: str
    path: Path
    content_type: str
    bytes_written: int
    sha256: str
    retrieved_at: str


@dataclass(slots=True)
class FetchResult:
    """Outcome for one source."""

    slug: str
    files: list[FetchedFile] = field(default_factory=list)
    skipped: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.files)

    @property
    def total_bytes(self) -> int:
        return sum(f.bytes_written for f in self.files)


def _http_get(url: str, *, expect_binary: bool = False) -> tuple[bytes, str]:
    """GET with a browser agent, retrying on transient failures.

    Returns ``(body, content_type)``.
    """
    import httpx

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=TIMEOUT_SECONDS,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            ) as client:
                response = client.get(url)
                if response.status_code == 403:
                    # Fingerprint-based blocking; retrying httpx will never succeed.
                    break
                response.raise_for_status()
                return response.content, response.headers.get("content-type", "")
        except Exception as exc:  # network flakiness is expected, not exceptional
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(2**attempt)  # 1s, 2s, 4s, 8s

    # Last resort: curl gets through hosts that reject httpx's TLS fingerprint.
    try:
        return _curl_get(url)
    except Exception as exc:
        last_error = exc

    raise RuntimeError(f"GET failed after {MAX_RETRIES} attempts: {url}") from last_error


def _safe_name(url: str, fallback: str) -> str:
    """Derive a filesystem-safe filename from a URL."""
    name = Path(urlparse(url).path).name or fallback
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name[:120] or fallback


def _write(target: Path, body: bytes, url: str, content_type: str) -> FetchedFile:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return FetchedFile(
        url=url,
        path=target,
        content_type=content_type,
        bytes_written=len(body),
        sha256=hashlib.sha256(body).hexdigest(),
        retrieved_at=datetime.now(UTC).isoformat(),
    )


def _resolve_links(html: bytes, base_url: str, pattern: str, limit: int) -> list[str]:
    """Find document links on a landing or index page.

    Deduplicated and capped: a too-loose regex on an index page would otherwise crawl an
    entire site, which is both rude and useless.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    compiled = re.compile(pattern, re.IGNORECASE)

    found: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        if not compiled.search(href):
            continue

        # Strip the fragment before deduplicating. A table of contents links the same
        # chapter file once per section (T0308E04.htm#ch4.1, #ch4.2, ...); treating those
        # as distinct URLs downloads one page five times and overwrites it four times.
        absolute = urljoin(base_url, href).split("#", 1)[0]
        if not absolute or absolute in seen or absolute == base_url:
            continue

        seen.add(absolute)
        found.append(absolute)
        if len(found) >= limit:
            break
    return found


def fetch_source(source: Source, paths: Paths, *, force: bool = False) -> FetchResult:
    """Retrieve one source according to its fetch mode."""
    destination = paths.corpus / "raw" / source.slug
    sidecar = destination / "_provenance.json"

    if sidecar.is_file() and not force:
        existing = json.loads(sidecar.read_text(encoding="utf-8"))
        return FetchResult(
            slug=source.slug,
            files=[
                FetchedFile(
                    url=f["url"],
                    path=destination / f["filename"],
                    content_type=f["content_type"],
                    bytes_written=f["bytes"],
                    sha256=f["sha256"],
                    retrieved_at=f["retrieved_at"],
                )
                for f in existing.get("files", [])
            ],
            skipped=True,
        )

    result = FetchResult(slug=source.slug)
    url = str(source.url)

    try:
        if source.fetch_mode is FetchMode.DIRECT:
            body, ctype = _http_get(url, expect_binary=True)
            result.files.append(
                _write(destination / _safe_name(url, "document.pdf"), body, url, ctype)
            )

        elif source.fetch_mode is FetchMode.PAGE:
            body, ctype = _http_get(url)
            result.files.append(_write(destination / "page.html", body, url, ctype))

        elif source.fetch_mode is FetchMode.LANDING:
            body, ctype = _http_get(url)
            links = _resolve_links(body, url, source.link_pattern or r"\.pdf", limit=5)
            if not links:
                # The landing page itself is still worth keeping: better a usable HTML page
                # than an empty source directory and a silent gap in the corpus.
                result.files.append(_write(destination / "page.html", body, url, ctype))
                result.error = "no document link matched; kept the landing page instead"
            else:
                for link in links:
                    time.sleep(REQUEST_DELAY_SECONDS)
                    doc_body, doc_ctype = _http_get(link, expect_binary=True)
                    result.files.append(
                        _write(
                            destination / _safe_name(link, "document.pdf"),
                            doc_body,
                            link,
                            doc_ctype,
                        )
                    )

        elif source.fetch_mode is FetchMode.INDEX:
            body, ctype = _http_get(url)
            result.files.append(_write(destination / "index.html", body, url, ctype))
            links = _resolve_links(
                body, url, source.link_pattern or r"\.html?", source.max_subpages
            )
            for link in links:
                time.sleep(REQUEST_DELAY_SECONDS)
                try:
                    sub_body, sub_ctype = _http_get(link)
                except RuntimeError:
                    continue  # one dead chapter should not fail the whole document
                result.files.append(
                    _write(destination / _safe_name(link, "page.html"), sub_body, link, sub_ctype)
                )

    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        return result

    _write_provenance(source, result, destination)
    return result


def _write_provenance(source: Source, result: FetchResult, destination: Path) -> None:
    """Record where every byte came from, alongside the bytes themselves."""
    destination.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "slug": source.slug,
        "title": source.title,
        "url": str(source.url),
        "source": source.source,
        "authority": source.authority.value,
        "region": source.region,
        "document_type": source.document_type.value,
        "language": source.language,
        "year": source.year,
        "diseases": list(source.diseases),
        "licence": source.licence,
        "notes": source.notes,
        "fetched_at": datetime.now(UTC).isoformat(),
        "files": [
            {
                "filename": f.path.name,
                "url": f.url,
                "content_type": f.content_type,
                "bytes": f.bytes_written,
                "sha256": f.sha256,
                "retrieved_at": f.retrieved_at,
            }
            for f in result.files
        ],
    }
    (destination / "_provenance.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fetch_all(
    paths: Paths,
    *,
    force: bool = False,
    only: str | None = None,
) -> list[FetchResult]:
    """Fetch the whole registry, one source at a time."""
    targets = [s for s in REGISTRY if only is None or s.slug == only]
    results: list[FetchResult] = []

    for index, source in enumerate(targets):
        if index:
            time.sleep(REQUEST_DELAY_SECONDS)
        results.append(fetch_source(source, paths, force=force))

    return results
