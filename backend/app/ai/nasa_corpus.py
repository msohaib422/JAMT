"""Build the JAMT NASA knowledge base from original NASA publications.

The pipeline (download -> extract -> chunk) lives here so it can be reused by
the CLI (``scripts/ingest_nasa_documents.py``) and by tests.  No scientific
content is written by hand — every passage comes from the live full text of
the NASA publications listed in ``app/ai/data/nasa_documents.json``.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

MANIFEST_PATH = Path(__file__).with_name("data") / "nasa_documents.json"
OUTPUT_PATH = Path(__file__).with_name("data") / "nasa_knowledge.json"
CACHE_DIR = Path(__file__).with_name("data").with_name("data_cache")

TARGET_CHUNK_CHARS = 1200  # roughly one screen of text per chunk
MIN_CHUNK_CHARS = 220
CHUNK_OVERLAP_CHARS = 180


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def load_manifest(path: Path | None = None) -> List[Dict[str, Any]]:
    data = json.loads((path or MANIFEST_PATH).read_text(encoding="utf-8"))
    return data["documents"]


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean_line(line: str) -> str:
    return _CONTROL_RE.sub("", line).rstrip()


def _collapse_blank_lines(text: str) -> str:
    lines = [_clean_line(line) for line in text.splitlines()]
    collapsed: List[str] = []
    blank = 0
    for line in lines:
        line = line.rstrip()
        if not line.strip():
            blank += 1
            if blank > 1:
                continue
            collapsed.append("")
        else:
            collapsed.append(line)
            blank = 0
    return "\n".join(collapsed).strip("\n")


def _merge_hyphenated_linebreaks(text: str) -> str:
    """Join PDF hyphenation (``explo-\nration`` -> ``exploration``)."""
    return re.sub(r"([a-z])-\n([a-z])", r"\1\2", text)


def parse_xhtml(raw: str) -> List[Tuple[Optional[str], str]]:
    """Split a Tika-style XHTML fulltext into ``(page_label, text)`` tuples.

    Two XHTML flavours exist in NTRS:

    * PDF full texts use ``<div class="page">`` per page (page index preserved).
    * Word full texts hold all content under ``<body>`` without page wrappers
      (page attribution is not available from the document metadata).
    """
    pages: List[Tuple[Optional[str], str]] = []
    if '<div class="page">' in raw:
        segments = re.split(r'<div class="page">', raw)
        for index, segment in enumerate(segments[1:], start=1):
            page_text = _extract_text_from_html_fragment(segment)
            if page_text.strip():
                pages.append((str(index), page_text))
        return pages

    body_match = re.search(r"<body[^>]*>(.*?)</body>", raw, flags=re.S | re.I)
    body = body_match.group(1) if body_match else raw
    text = _extract_text_from_html_fragment(body)
    if text.strip():
        pages.append((None, text))
    return pages


def _extract_text_from_html_fragment(fragment: str) -> str:
    fragment = re.sub(r"<(head|meta|title|style|script)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    fragment = re.sub(r"<[^>]+>", "\n", fragment)
    fragment = html.unescape(fragment)
    fragment = _merge_hyphenated_linebreaks(fragment)
    return _collapse_blank_lines(fragment)


def parse_plain_text(raw: str, footer_regex: Optional[str] = None) -> List[Tuple[Optional[str], str]]:
    """Split a plain-text PDF dump into page tuples.

    When a ``footer_regex`` (with exactly one capture group — the trailing
    page numeral) is provided in the manifest, the text is split on the running
    footer line and each captured numeral is kept as the page label.  Without
    one, the whole document is treated as a single page (``page == None``).
    """
    text = _merge_hyphenated_linebreaks(raw)
    text = _collapse_blank_lines(text)
    if footer_regex:
        regex = re.compile(footer_regex, flags=re.M)
        matches = list(regex.finditer(text))
        if len(matches) >= 2:
            labels = [match.group(1) for match in matches]
            bodies: List[str] = []
            prev_end = 0
            for match in matches:
                body = text[prev_end:match.start()].strip("\n")
                prev_end = match.end()
                bodies.append(body)
            pages: List[Tuple[Optional[str], str]] = []
            for label, body in zip(labels, bodies):
                if body.strip():
                    pages.append((label, body))
            tail = text[prev_end:].strip("\n")
            if tail.strip():
                pages.append((None, tail))
            return pages
    return [(None, text)]


def _split_paragraphs(text: str) -> List[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_sentences(text: str) -> List[str]:
    """Only used when a single paragraph exceeds the chunk target."""
    return re.split(r"(?<=[.;:])\s+(?=[A-Z0-9“\"'])", text)


SECTION_HEADING_RE = re.compile(
    r"^(?P<head>(?:Appendix\s+[A-Z](?:\.\d+)*(?:\.\d+)*|\d{1,2}(?:\.\d{1,2}){0,2})\.?\s+[A-Z][^\n]{3,80})$"
)


class ChunkBuilder:
    """Accumulate paragraphs into ~TARGET_CHUNK_CHARS chunks with overlap."""

    def __init__(self, doc_meta: Dict[str, Any]):
        self.doc_meta = doc_meta
        self.chunks: List[Dict[str, Any]] = []
        self._current: List[str] = []
        self._current_chars = 0
        self._page: Optional[str] = None
        self._section: Optional[str] = None
        self._chunk_index = 0

    def _flush(self, *, force: bool = False) -> None:
        if not self._current:
            return
        content = "\n\n".join(self._current).strip()
        if len(content) < MIN_CHUNK_CHARS and self.chunks and not force:
            return
        self._chunk_index += 1
        self.chunks.append(self._make_chunk(content))
        overlap_chars = 0
        overlap: List[str] = []
        for para in reversed(self._current):
            if overlap_chars + len(para) > CHUNK_OVERLAP_CHARS:
                break
            overlap.append(para)
            overlap_chars += len(para)
        self._current = list(reversed(overlap))
        self._current_chars = sum(len(p) for p in self._current)

    def _make_chunk(self, content: str) -> Dict[str, Any]:
        meta = self.doc_meta
        return {
            "id": f"{meta['key']}-{self._chunk_index:04d}",
            "ntrs_id": meta["ntrs_id"],
            "title": meta["title"],
            "source": "NASA Technical Reports Server",
            "document_id": meta.get("document_id"),
            "sti_type": meta.get("sti_type"),
            "publication_date": meta.get("publication_date") or None,
            "distribution": meta.get("distribution"),
            "url": meta["ntrs_url"],
            "pdf_url": meta.get("pdf_url"),
            "fulltext_url": meta["fulltext_url"],
            "category": meta["category"],
            "topics": list(meta.get("topics", [])),
            "planetary_body": meta.get("planetary_body"),
            "license": meta.get("license"),
            "retrieved": meta.get("retrieved"),
            "section": self._section,
            "page": self._page,
            "content": content,
        }

    def add_page(self, page_label: Optional[str], page_text: str) -> None:
        self._page = page_label
        for paragraph in _split_paragraphs(page_text):
            heading = SECTION_HEADING_RE.match(paragraph)
            if heading:
                self._section = heading.group("head").strip()
            if len(paragraph) > TARGET_CHUNK_CHARS * 1.4:
                sentences = _split_sentences(paragraph)
                for sentence in sentences:
                    self._add_paragraph(sentence[:TARGET_CHUNK_CHARS * 2])
                continue
            self._add_paragraph(paragraph)
        self._flush()

    def _add_paragraph(self, paragraph: str) -> None:
        paragraph = paragraph.strip()
        if not paragraph:
            return
        if self._current_chars + len(paragraph) > TARGET_CHUNK_CHARS and self._current:
            self._flush()
        self._current.append(paragraph)
        self._current_chars += len(paragraph)
        if self._current_chars >= TARGET_CHUNK_CHARS:
            self._flush()

    def finalize(self) -> List[Dict[str, Any]]:
        tail = list(self._current)
        current_len = self._current_chars
        if self._current_chars:
            content = "\n\n".join(tail).strip()
            if len(content) >= MIN_CHUNK_CHARS:
                self._chunk_index += 1
                self.chunks.append(self._make_chunk(content))
        return self.chunks


def build_document_chunks(doc_meta: Dict[str, Any], raw_bytes: bytes, retrieved_date: str) -> List[Dict[str, Any]]:
    """Extract chunks for one document; returns ``[]`` on extraction failure."""
    text = raw_bytes.decode("utf-8", errors="replace")
    signature = hashlib.sha256(raw_bytes).hexdigest()
    meta = dict(doc_meta)
    meta["retrieved"] = retrieved_date
    meta["sha256"] = signature

    if "<div class=\"page\"" in text or text.lstrip().startswith("<html") or text.lstrip().startswith("<?xml"):
        pages = parse_xhtml(text)
    else:
        footer_regex = doc_meta.get("footer_regex")
        pages = parse_plain_text(text, footer_regex)

    if not pages:
        return []

    builder = ChunkBuilder(meta)
    for page_label, page_text in pages:
        if not page_text.strip():
            continue
        builder.add_page(page_label, page_text)
    chunks = builder.finalize()
    # Final de-duplication on normalised content
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for chunk in chunks:
        fingerprint = hashlib.sha256(re.sub(r"\s+", " ", chunk["content"].lower()).encode("utf-8")).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(chunk)
    return unique


# ---------------------------------------------------------------------------
# Download + build
# ---------------------------------------------------------------------------

def download_document(client: httpx.Client, doc_meta: Dict[str, Any], timeout: float = 90.0) -> bytes:
    response = client.get(doc_meta["fulltext_url"], timeout=timeout, follow_redirects=True)
    if response.status_code >= 400:
        raise RuntimeError(f"NTRS download failed for {doc_meta['key']}: HTTP {response.status_code}")
    return response.content


def build_dataset(*, retrieved_date: Optional[str] = None, timeout: float = 90.0, cache_dir: Optional[Path] = None, force: bool = False) -> Dict[str, Any]:
    """Fetch every manifest document, extract chunks and write the dataset."""
    retrieved_date = retrieved_date or datetime.now(timezone.utc).date().isoformat()
    documents = load_manifest()
    cache_dir = cache_dir or CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    all_chunks: List[Dict[str, Any]] = []
    report: List[Dict[str, Any]] = []
    failures: List[Dict[str, str]] = []

    with httpx.Client(headers={"User-Agent": "JAMT-NASA-Ingest/1.0"}) as client:
        for doc_meta in documents:
            raw: Optional[bytes] = None
            cache_file = cache_dir / f"{doc_meta['key']}.txt"
            if not force and cache_file.exists():
                raw = cache_file.read_bytes()
                source = "cache"
            else:
                try:
                    raw = download_document(client, doc_meta, timeout=timeout)
                    cache_file.write_bytes(raw)
                    source = "network"
                except Exception as exc:  # noqa: BLE001 - reported in the summary
                    failures.append({"key": doc_meta["key"], "error": str(exc)})
                    continue
            chunks = build_document_chunks(doc_meta, raw, retrieved_date)
            all_chunks.extend(chunks)
            report.append({
                "key": doc_meta["key"],
                "ntrs_id": doc_meta["ntrs_id"],
                "title": doc_meta["title"],
                "document_id": doc_meta.get("document_id"),
                "url": doc_meta["ntrs_url"],
                "publication_date": doc_meta.get("publication_date"),
                "source": source,
                "extracted_chunks": len(chunks),
                "bytes": len(raw),
            })

    return {
        "manifest_size": len(documents),
        "retrieved": retrieved_date,
        "documents": report,
        "failures": failures,
        "total_chunks": len(all_chunks),
        "chunks": all_chunks,
    }


def write_dataset(chunks: List[Dict[str, Any]], path: Path | None = None) -> Path:
    path = path or OUTPUT_PATH
    payload = {
        "description": (
            "JAMT NASA knowledge base. Every passage is extracted verbatim (character-cleaning only) "
            "from the NASA publications listed in nasa_documents.json. Do not add hand-written content."
        ),
        "retrieved": chunks[0]["retrieved"] if chunks else datetime.now(timezone.utc).date().isoformat(),
        "documents_indexed": len({chunk["ntrs_id"] for chunk in chunks}),
        "chunks": chunks,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
