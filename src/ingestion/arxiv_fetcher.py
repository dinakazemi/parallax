import re
from src.models import PaperContent
from src.ingestion.pdf_parser import parse_pdf

_ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}"


def fetch_arxiv(source: str) -> PaperContent:
    """Fetch a paper by ArXiv ID or URL (e.g. '2301.07658', 'arxiv:2301.07658', or an arxiv.org URL)."""
    arxiv_id = _normalize_id(source)
    pdf_url = _ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    return parse_pdf(pdf_url)


def _normalize_id(source: str) -> str:
    source = source.strip()
    source = re.sub(r"^(arxiv:|https?://arxiv\.org/(abs|pdf)/)", "", source, flags=re.IGNORECASE)
    source = re.sub(r"\.pdf$", "", source)
    return source
