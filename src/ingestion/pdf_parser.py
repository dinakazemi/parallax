import fitz  # PyMuPDF
import re
import httpx
from pathlib import Path
from src.models import PaperContent

_SKIP_SECTION_PATTERNS = re.compile(
    r"^\s*(materials? and methods?|experimental (setup|procedure)|"
    r"(supplementary|appendix)|acknowledgements?|references?|"
    r"data availability|author contributions?)\b",
    re.IGNORECASE,
)

_MAX_BODY_CHARS = 60_000  # ~15k tokens — enough for Claude to grasp the science


def parse_pdf(source: str | Path) -> PaperContent:
    """Accept a local file path, a PDF URL, or raw bytes."""
    source = str(source)

    if source.startswith("http://") or source.startswith("https://"):
        pdf_bytes = _fetch_bytes(source)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    else:
        doc = fitz.open(source)

    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    title, abstract, body = _split_sections(full_text)
    return PaperContent(
        title=title,
        abstract=abstract,
        body=body[:_MAX_BODY_CHARS],
        source=source,
    )


def parse_pdf_bytes(pdf_bytes: bytes, source_label: str) -> PaperContent:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    title, abstract, body = _split_sections(full_text)
    return PaperContent(
        title=title,
        abstract=abstract,
        body=body[:_MAX_BODY_CHARS],
        source=source_label,
    )


def _fetch_bytes(url: str) -> bytes:
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def _split_sections(text: str) -> tuple[str, str, str]:
    lines = text.split("\n")
    title = _extract_title(lines)
    abstract = _extract_abstract(text)
    body = _extract_body(text)
    return title, abstract, body


def _extract_title(lines: list[str]) -> str:
    candidates = []
    for line in lines[:30]:
        stripped = line.strip()
        if stripped and len(stripped) > 10:
            candidates.append(stripped)
            if len(candidates) >= 3:
                break
    return " ".join(candidates) if candidates else "Unknown Title"


def _extract_abstract(text: str) -> str:
    match = re.search(
        r"\bAbstract\b[\s\.\:\-]*(.*?)(?=\n\s*\n|\b1\.?\s+Introduction\b)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()[:3000]
    return text[:1000].strip()


def _extract_body(text: str) -> str:
    intro_match = re.search(r"\b1\.?\s+Introduction\b", text, re.IGNORECASE)
    start = intro_match.start() if intro_match else 0

    body_lines = []
    current_section_skipped = False

    for line in text[start:].split("\n"):
        stripped = line.strip()
        if _is_section_header(stripped):
            current_section_skipped = bool(_SKIP_SECTION_PATTERNS.match(stripped))
        if not current_section_skipped:
            body_lines.append(line)

    return "\n".join(body_lines).strip()


def _is_section_header(line: str) -> bool:
    return bool(re.match(r"^(\d+\.?\s+)?[A-Z][a-zA-Z ]{3,40}$", line))
