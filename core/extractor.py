"""Extract text and metadata from PDF files."""
import io
from dataclasses import dataclass, field


@dataclass
class PageContent:
    page_num: int
    text: str
    has_images: bool = False
    image_count: int = 0


def extract_text(pdf_source) -> list[PageContent]:
    """Extract text from a PDF file.

    Args:
        pdf_source: file path (str) or file-like object (BytesIO/UploadedFile)

    Returns:
        List of PageContent with text per page.
    """
    try:
        return _extract_with_pymupdf(pdf_source)
    except Exception:
        return _extract_with_pypdf2(pdf_source)


def _extract_with_pymupdf(pdf_source) -> list[PageContent]:
    import fitz

    if isinstance(pdf_source, str):
        doc = fitz.open(pdf_source)
    else:
        data = pdf_source.read() if hasattr(pdf_source, 'read') else pdf_source
        if hasattr(pdf_source, 'seek'):
            pdf_source.seek(0)
        doc = fitz.open(stream=data, filetype="pdf")

    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        images = page.get_images(full=True)
        real_images = [img for img in images if img[2] > 50 and img[3] > 50]
        pages.append(PageContent(
            page_num=i + 1,
            text=text,
            has_images=len(real_images) > 0,
            image_count=len(real_images),
        ))
    doc.close()
    return pages


def _extract_with_pypdf2(pdf_source) -> list[PageContent]:
    from PyPDF2 import PdfReader

    if isinstance(pdf_source, str):
        reader = PdfReader(pdf_source)
    else:
        if hasattr(pdf_source, 'seek'):
            pdf_source.seek(0)
        reader = PdfReader(pdf_source)

    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(PageContent(
            page_num=i + 1,
            text=text,
        ))
    return pages


def get_pdf_info(pdf_source) -> dict:
    """Get basic PDF metadata."""
    import fitz

    if isinstance(pdf_source, str):
        doc = fitz.open(pdf_source)
    else:
        data = pdf_source.read() if hasattr(pdf_source, 'read') else pdf_source
        if hasattr(pdf_source, 'seek'):
            pdf_source.seek(0)
        doc = fitz.open(stream=data, filetype="pdf")

    info = {
        "pages": len(doc),
        "title": doc.metadata.get("title", "") if doc.metadata else "",
        "author": doc.metadata.get("author", "") if doc.metadata else "",
    }

    total_words = 0
    total_images = 0
    for page in doc:
        text = page.get_text("text")
        total_words += len(text.split())
        images = page.get_images(full=True)
        total_images += len([img for img in images if img[2] > 50 and img[3] > 50])

    info["word_count"] = total_words
    info["image_count"] = total_images
    doc.close()
    return info
