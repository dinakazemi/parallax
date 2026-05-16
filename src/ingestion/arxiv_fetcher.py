import re
import httpx
import arxiv
from src.models import PaperContent
from src.ingestion.pdf_parser import parse_pdf_bytes

_ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}"


def fetch_arxiv(arxiv_id: str) -> PaperContent:
    """Fetch a paper by ArXiv ID (e.g. '2301.07658' or 'arxiv:2301.07658')."""
    arxiv_id = _normalize_id(arxiv_id)

    # Pull structured metadata from the ArXiv API
    # Use a Client with delay+retries to avoid 429s from the public API
    client = arxiv.Client(delay_seconds=5.0, num_retries=5)
    search = arxiv.Search(id_list=[arxiv_id])
    results = list(client.results(search))
    if not results:
        raise ValueError(f"No ArXiv paper found for ID: {arxiv_id}")

    paper = results[0]
    pdf_url = _ARXIV_PDF_URL.format(arxiv_id=arxiv_id)

    pdf_bytes = _download_pdf(pdf_url)
    content = parse_pdf_bytes(pdf_bytes, source_label=f"arxiv:{arxiv_id}")

    # Override title with the clean metadata title
    content.title = paper.title
    # Prepend the structured abstract (cleaner than PDF-extracted one)
    content.abstract = paper.summary.replace("\n", " ")

    return content


def _normalize_id(arxiv_id: str) -> str:
    arxiv_id = arxiv_id.strip()
    # Strip common prefixes like "arxiv:", "https://arxiv.org/abs/"
    arxiv_id = re.sub(r"^(arxiv:|https?://arxiv\.org/(abs|pdf)/)", "", arxiv_id, flags=re.IGNORECASE)
    # Strip trailing .pdf
    arxiv_id = re.sub(r"\.pdf$", "", arxiv_id)
    return arxiv_id


def _download_pdf(url: str) -> bytes:
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content
