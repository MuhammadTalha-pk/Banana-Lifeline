"""Expert review sheet for label-conflict scenes.

The 18 contested scenes are the highest-value labelling work in the project: they sit on the
panama/sigatoka boundary, and panama is both the smallest class and the most costly to get
wrong. This module renders them as a self-contained page an agronomist can open and rule on
without installing anything.

The verdicts come back as a CSV that ``banana import-verdicts`` folds into the manifests.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import pandas as pd

from banana_lifeline.config import DataConfig, Paths

_PAGE_CSS = """
:root { --bg:#fbfaf7; --fg:#1a1a1a; --muted:#666; --line:#e2ded6; --warn:#b45309; }
* { box-sizing:border-box; }
body { margin:0; padding:2rem clamp(1rem,4vw,3rem); background:var(--bg); color:var(--fg);
       font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif; }
h1 { font-size:1.6rem; margin:0 0 .25rem; }
.sub { color:var(--muted); margin:0 0 2rem; }
.note { background:#fff8ed; border-left:3px solid var(--warn); padding:1rem 1.25rem;
        margin:0 0 2rem; border-radius:0 6px 6px 0; }
.cluster { background:#fff; border:1px solid var(--line); border-radius:10px;
           padding:1.25rem; margin:0 0 1.75rem; }
.cluster header { display:flex; justify-content:space-between; align-items:baseline;
                  gap:1rem; flex-wrap:wrap; margin-bottom:1rem; }
.cid { font-weight:600; }
.conflict { color:var(--warn); font-weight:600; }
.strip { display:flex; gap:1rem; overflow-x:auto; padding-bottom:.5rem; }
figure { margin:0; flex:0 0 240px; }
figure img { width:240px; height:240px; object-fit:cover; border-radius:6px;
             border:1px solid var(--line); background:#f0ede8; }
figcaption { font-size:.78rem; color:var(--muted); margin-top:.4rem; word-break:break-all; }
figcaption b { color:var(--fg); }
.verdict { margin-top:1rem; padding-top:1rem; border-top:1px solid var(--line);
           display:flex; gap:1.25rem; align-items:center; flex-wrap:wrap; }
.verdict label { display:flex; gap:.4rem; align-items:center; cursor:pointer; }
button { font:inherit; padding:.6rem 1.1rem; border-radius:6px; border:1px solid var(--fg);
         background:var(--fg); color:var(--bg); cursor:pointer; }
#out { width:100%; min-height:9rem; margin-top:1rem; font-family:ui-monospace,monospace;
       font-size:.8rem; padding:.75rem; border:1px solid var(--line); border-radius:6px; }
.footer { display:flex; gap:1rem; align-items:center; flex-wrap:wrap;
          position:sticky; bottom:0; background:var(--bg); padding:1rem 0; }
#progress { color:var(--muted); font-size:.9rem; }
#progress.done { color:#15803d; font-weight:600; }
code { background:#f0ede8; padding:.1rem .35rem; border-radius:3px; font-size:.85em; }
"""

_PAGE_JS = """
const TOTAL = document.querySelectorAll('.cluster').length;

function buildCsv() {
  const rows = [['cluster_id','verdict','reviewer_note']];
  document.querySelectorAll('.cluster').forEach(el => {
    const picked = el.querySelector('input[type=radio]:checked');
    if (!picked) return;
    const note = el.querySelector('input[type=text]').value.replaceAll('"', "'");
    rows.push([el.dataset.cluster, picked.value, '"' + note + '"']);
  });
  return { csv: rows.map(r => r.join(',')).join('\\n'), decided: rows.length - 1 };
}

function refreshProgress() {
  const { decided } = buildCsv();
  const el = document.getElementById('progress');
  el.textContent = decided + ' of ' + TOTAL + ' scenes decided';
  el.className = decided === TOTAL ? 'done' : '';
}

// Persist choices locally so a closed tab does not throw away the review.
function save() {
  const state = {};
  document.querySelectorAll('.cluster').forEach(el => {
    const picked = el.querySelector('input[type=radio]:checked');
    state[el.dataset.cluster] = {
      verdict: picked ? picked.value : null,
      note: el.querySelector('input[type=text]').value
    };
  });
  localStorage.setItem('banana-verdicts', JSON.stringify(state));
  refreshProgress();
}

function restore() {
  const raw = localStorage.getItem('banana-verdicts');
  if (!raw) { refreshProgress(); return; }
  const state = JSON.parse(raw);
  document.querySelectorAll('.cluster').forEach(el => {
    const saved = state[el.dataset.cluster];
    if (!saved) return;
    if (saved.verdict) {
      const input = el.querySelector('input[value="' + saved.verdict + '"]');
      if (input) input.checked = true;
    }
    el.querySelector('input[type=text]').value = saved.note || '';
  });
  refreshProgress();
}

function downloadVerdicts() {
  const { csv, decided } = buildCsv();
  if (decided === 0) {
    alert('No decisions recorded yet.');
    return;
  }
  if (decided < TOTAL &&
      !confirm(decided + ' of ' + TOTAL + ' scenes decided. Download anyway?')) {
    return;
  }
  const blob = new Blob([csv], { type: 'text/csv' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'verdicts.csv';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
  document.getElementById('out').value = csv;
}

document.addEventListener('change', save);
document.addEventListener('input', save);
window.addEventListener('DOMContentLoaded', restore);
"""


def _figure(row: Any, review_dir: Path, raw_root: Path) -> str:
    src = Path(str(row.relpath))
    if not src.is_absolute():
        src = raw_root / src
    try:
        rel = Path(
            *([".."] * len(review_dir.relative_to(raw_root.parent).parts))
        ) / src.relative_to(raw_root.parent)
        href = rel.as_posix()
    except ValueError:
        href = src.as_uri()

    return (
        f'<figure><img loading="lazy" src="{html.escape(href)}" '
        f'alt="{html.escape(str(row.filename))}">'
        f"<figcaption><b>{html.escape(str(row.label_original))}</b> "
        f"&middot; {html.escape(str(row.split_original))}<br>"
        f"{html.escape(str(row.filename))}</figcaption></figure>"
    )


def render_review_page(frame: pd.DataFrame, data_cfg: DataConfig, paths: Paths) -> str:
    """Render every contested scene as a labelled image strip with a verdict control."""
    raw_root = data_cfg.resolved_raw_root(paths)
    review_dir = paths.review
    cluster_ids = sorted(frame["cluster_id"].dropna().unique().tolist())

    blocks: list[str] = []
    for cluster_id in cluster_ids:
        members = frame[frame["cluster_id"] == cluster_id]
        labels = sorted(members["label_original"].unique())
        figures = "".join(_figure(row, review_dir, raw_root) for row in members.itertuples())
        options = "".join(
            f'<label><input type="radio" name="v{cluster_id}" value="{html.escape(name)}">'
            f"{html.escape(name)}</label>"
            for name in (*data_cfg.class_names, "discard")
        )
        blocks.append(
            f'<section class="cluster" data-cluster="{int(cluster_id)}">'
            f'<header><span class="cid">Scene {int(cluster_id)}</span>'
            f'<span class="conflict">labelled {" vs ".join(html.escape(x) for x in labels)}</span>'
            f"<span>{len(members)} copies</span></header>"
            f'<div class="strip">{figures}</div>'
            f'<div class="verdict">{options}'
            f'<input type="text" placeholder="note (optional)" style="flex:1;min-width:12rem;'
            f'padding:.45rem;border:1px solid var(--line);border-radius:6px;font:inherit"></div>'
            f"</section>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Banana Lifeline — Label Conflict Review</title>
<style>{_PAGE_CSS}</style></head>
<body>
<h1>Label conflict review</h1>
<p class="sub">{len(cluster_ids)} scenes are labelled as more than one disease.</p>

<div class="note">
<p style="margin:0 0 .5rem"><b>What you are looking at.</b> Each row is a single photograph
that exists several times in the dataset under different disease labels. At least one label
is wrong. These images are excluded from model training until a verdict is recorded.</p>
<p style="margin:0"><b>Worth remembering while judging:</b> Sigatoka presents as dark streaks
and spots with yellowing spreading from the leaf margin. Panama wilt is a vascular disease —
its reliable signs are whole-plant yellowing from the oldest leaves upward, leaf collapse
around the pseudostem, and brown discolouration inside a cut stem. If a close-up leaf photo
genuinely cannot distinguish the two, choose <b>discard</b>. That is a legitimate answer and
a more useful one than a guess.</p>
</div>

{"".join(blocks)}

<div class="footer">
  <button onclick="downloadVerdicts()">Download verdicts.csv</button>
  <span id="progress">0 of {len(cluster_ids)} scenes decided</span>
</div>
<p class="sub" style="margin-top:.75rem">Save the downloaded file into
<code>ai/data/review/</code>, then run <code>banana import-verdicts</code>.
Your choices are saved in this browser as you go, so closing the tab will not lose them.</p>
<textarea id="out" placeholder="The CSV appears here once you download, in case you prefer to copy it."></textarea>
<script>{_PAGE_JS}</script>
</body></html>
"""


def write_review_page(frame: pd.DataFrame, data_cfg: DataConfig, paths: Paths) -> Path:
    paths.review.mkdir(parents=True, exist_ok=True)
    destination = paths.review / "review.html"
    destination.write_text(render_review_page(frame, data_cfg, paths), encoding="utf-8")
    frame.to_csv(paths.review / "conflicts.csv", index=False)
    return destination
