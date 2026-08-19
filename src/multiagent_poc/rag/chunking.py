"""Two chunking strategies for runbook markdown, compared in Week 2.

fixed_size_chunks: naive sliding window over raw text, strategy-agnostic to
document structure. section_chunks: splits on markdown headings (## / ###),
producing self-contained, structurally meaningful chunks.
"""

from dataclasses import dataclass
import re


@dataclass
class Chunk:
    text: str
    heading_path: str | None  # e.g. "4. Rozbieżności ilościowe i jakościowe > 4.3 Pomyłka dostawcy"
    source: str
    strategy: str


def fixed_size_chunks(text: str, source: str, size: int = 500, overlap: int = 50) -> list[Chunk]:
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(
            Chunk(text=text[start:end], heading_path=None, source=source, strategy="fixed_size")
        )
        if end >= len(text):
            break
        start = end - overlap
    return chunks


_HEADING_RE = re.compile(r"^(#{2,3})\s+(.*)$", re.MULTILINE)


def section_chunks(text: str, source: str) -> list[Chunk]:
    """Split on ## and ### headings; each chunk keeps its ancestor heading(s)
    prefixed in `heading_path` so a lone "### 4.3 ..." chunk still carries the
    context of its parent "## 4. ..." section.
    """
    matches = list(_HEADING_RE.finditer(text))
    chunks: list[Chunk] = []
    path: list[tuple[int, str]] = []  # (level, heading text) stack

    for i, match in enumerate(matches):
        level = len(match.group(1))  # 2 for "##", 3 for "###"
        heading = match.group(2).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()

        path = [p for p in path if p[0] < level]
        path.append((level, heading))
        heading_path = " > ".join(h for _, h in path)

        if body:
            chunks.append(
                Chunk(
                    text=f"{heading_path}\n\n{body}",
                    heading_path=heading_path,
                    source=source,
                    strategy="section",
                )
            )
    return chunks
