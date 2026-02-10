"""Extract and manage images from PDF files."""
import io
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImageInfo:
    page_num: int
    image_data: bytes
    width: int
    height: int
    temp_path: str = ""


def extract_images(pdf_source, min_size=60) -> list[ImageInfo]:
    """Extract meaningful images from a PDF by rendering pages.

    Uses PyMuPDF page rendering to capture images exactly as they appear,
    which handles custom fonts and vector graphics correctly.

    Args:
        pdf_source: file path (str) or file-like object
        min_size: minimum dimension to filter out tiny icons

    Returns:
        List of ImageInfo objects with image data and metadata.
    """
    import fitz
    from PIL import Image

    if isinstance(pdf_source, str):
        doc = fitz.open(pdf_source)
    else:
        data = pdf_source.read() if hasattr(pdf_source, 'read') else pdf_source
        if hasattr(pdf_source, 'seek'):
            pdf_source.seek(0)
        doc = fitz.open(stream=data, filetype="pdf")

    images = []
    temp_dir = tempfile.mkdtemp(prefix="pdf_images_")

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_images = page.get_images(full=True)

        # Filter: only pages with real images (not tiny icons)
        real_images = [img for img in page_images if img[2] > min_size and img[3] > min_size]
        if not real_images:
            continue

        # Render the full page at 2x resolution
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        page_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # For each real image on this page, crop it from the rendered page
        for img_info in real_images:
            xref = img_info[0]
            try:
                img_rects = page.get_image_rects(xref)
                if not img_rects:
                    continue

                rect = img_rects[0]
                # Scale coordinates to 2x rendered resolution
                x0 = int(rect.x0 * 2)
                y0 = int(rect.y0 * 2)
                x1 = int(rect.x1 * 2)
                y1 = int(rect.y1 * 2)

                # Add small padding
                padding = 4
                x0 = max(0, x0 - padding)
                y0 = max(0, y0 - padding)
                x1 = min(pix.width, x1 + padding)
                y1 = min(pix.height, y1 + padding)

                cropped = page_img.crop((x0, y0, x1, y1))

                if cropped.width < min_size or cropped.height < min_size:
                    continue

                # Save to temp file
                temp_path = Path(temp_dir) / f"page{page_idx + 1}_img{xref}.png"
                cropped.save(str(temp_path))

                buf = io.BytesIO()
                cropped.save(buf, format="PNG")
                buf.seek(0)

                images.append(ImageInfo(
                    page_num=page_idx + 1,
                    image_data=buf.getvalue(),
                    width=cropped.width,
                    height=cropped.height,
                    temp_path=str(temp_path),
                ))
            except Exception:
                continue

    doc.close()
    return images


def get_images_for_page(images: list[ImageInfo], page_num: int) -> list[ImageInfo]:
    """Get all images from a specific page."""
    return [img for img in images if img.page_num == page_num]


def get_images_for_range(images: list[ImageInfo], start_page: int, end_page: int) -> list[ImageInfo]:
    """Get all images within a page range."""
    return [img for img in images if start_page <= img.page_num <= end_page]
