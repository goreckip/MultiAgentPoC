"""Builds the standalone, emailable case study from its two sources.

Two output forms exist for the same content and they differ in one way only:

- ``docs/_case_study_body.html`` is a *fragment*. It is what gets published as
  a Claude Artifact, which supplies its own <!doctype>/<head>/<body> wrapper
  and renders ```mermaid``` blocks natively.
- ``docs/case_study.html`` (built here) is a *standalone file* meant to be
  attached to an email. It therefore needs the full document skeleton, its own
  CSS reset, and — crucially — no network dependency at all, so the Mermaid
  block is swapped for a pre-rendered inline SVG (``docs/_graph_diagram.svg``).

Run: python scripts/build_case_study_html.py
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BODY = ROOT / "docs" / "_case_study_body.html"
SVG = ROOT / "docs" / "_graph_diagram.svg"
OUT = ROOT / "docs" / "case_study.html"

SKELETON = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  /* Minimal reset — the hosted Artifact runtime supplies one; a standalone
     file has to bring its own so it looks identical opened from disk. */
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{ margin: 0; }}
  img, svg {{ max-width: 100%; }}
  @media print {{
    body {{ background: #fff; }}
    .player, .controls {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def build() -> Path:
    body = BODY.read_text(encoding="utf-8")
    svg = SVG.read_text(encoding="utf-8").strip()

    title_match = re.search(r"<title>(.*?)</title>", body, re.S)
    title = title_match.group(1).strip() if title_match else "Case study"
    # The <title> belongs in <head>, so drop it from the fragment copy.
    body = re.sub(r"<title>.*?</title>\s*", "", body, count=1, flags=re.S)

    # Swap the Mermaid source block for the pre-rendered SVG: a standalone file
    # must not depend on a Mermaid runtime being present.
    body, swapped = re.subn(
        r'<pre class="mermaid">.*?</pre>',
        lambda _: f'<div class="graph-figure">{svg}</div>',
        body,
        flags=re.S,
    )
    if swapped != 1:
        raise SystemExit(f"expected exactly one mermaid block to replace, replaced {swapped}")

    OUT.write_text(SKELETON.format(title=title, body=body), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.0f} KB, self-contained)")
