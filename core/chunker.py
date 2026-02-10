"""Split extracted text into translation-ready chunks."""
import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    index: int
    text: str
    start_page: int
    end_page: int
    chapter_label: str = ""
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.text.split())


# Patterns that indicate chapter boundaries (multi-language)
CHAPTER_PATTERNS = [
    r'^(?:chapter|capítulo|capitulo|chapitre|kapitel|capitolo|capítulo)\s+\d+',
    r'^(?:part|parte|partie|teil)\s+[IVXLCDM\d]+',
    r'^(?:appendix|apéndice|apendice|annexe|anhang|appendice)\s+[A-Z\d]',
    r'^(?:introduction|introducción|introduccion|epilogue|epílogo|epilogo)',
    r'^(?:bibliography|bibliografía|bibliografia|references|referencias)',
    r'^(?:prologue|prólogo|prologo|preface|prefacio)',
]


def chunk_text(pages, target_words=5000, source_lang="auto") -> list[Chunk]:
    """Split pages into chunks for translation.

    Respects chapter boundaries and avoids splitting mid-paragraph.

    Args:
        pages: list of PageContent from extractor
        target_words: approximate words per chunk
        source_lang: source language hint for chapter detection

    Returns:
        List of Chunk objects ready for translation.
    """
    chapter_breaks = _detect_chapter_breaks(pages)
    sections = _split_at_chapters(pages, chapter_breaks)

    chunks = []
    for section in sections:
        section_chunks = _split_section(section, target_words)
        for sc in section_chunks:
            chunks.append(Chunk(
                index=len(chunks),
                text=sc["text"],
                start_page=sc["start_page"],
                end_page=sc["end_page"],
                chapter_label=sc.get("chapter_label", ""),
            ))

    return chunks


def _detect_chapter_breaks(pages) -> list[dict]:
    """Find page numbers where new chapters begin."""
    breaks = []
    combined_pattern = '|'.join(f'({p})' for p in CHAPTER_PATTERNS)

    for page in pages:
        lines = page.text.split('\n')
        for line in lines[:10]:  # Check first 10 lines of each page
            stripped = line.strip()
            if stripped and re.match(combined_pattern, stripped, re.IGNORECASE):
                breaks.append({
                    "page_num": page.page_num,
                    "label": stripped[:80],
                })
                break

    return breaks


def _split_at_chapters(pages, breaks) -> list[dict]:
    """Group pages into chapter-level sections."""
    if not breaks:
        return [{"pages": pages, "chapter_label": "", "start_page": pages[0].page_num if pages else 1}]

    sections = []
    break_pages = [b["page_num"] for b in breaks]
    break_labels = {b["page_num"]: b["label"] for b in breaks}

    current_pages = []
    current_label = ""

    for page in pages:
        if page.page_num in break_pages and current_pages:
            sections.append({
                "pages": current_pages,
                "chapter_label": current_label,
                "start_page": current_pages[0].page_num,
            })
            current_pages = []
            current_label = break_labels.get(page.page_num, "")
        elif page.page_num in break_pages:
            current_label = break_labels.get(page.page_num, "")

        current_pages.append(page)

    if current_pages:
        sections.append({
            "pages": current_pages,
            "chapter_label": current_label,
            "start_page": current_pages[0].page_num,
        })

    return sections


def _split_section(section, target_words) -> list[dict]:
    """Split a section into sub-chunks if it exceeds target_words."""
    full_text = "\n\n".join(p.text for p in section["pages"])
    word_count = len(full_text.split())

    if word_count <= target_words * 1.3:
        return [{
            "text": full_text,
            "start_page": section["start_page"],
            "end_page": section["pages"][-1].page_num,
            "chapter_label": section.get("chapter_label", ""),
        }]

    # Split into paragraphs and group
    paragraphs = re.split(r'\n\s*\n', full_text)
    sub_chunks = []
    current_text = []
    current_words = 0
    chunk_start_page = section["start_page"]

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > target_words and current_text:
            sub_chunks.append({
                "text": "\n\n".join(current_text),
                "start_page": chunk_start_page,
                "end_page": section["pages"][-1].page_num,
                "chapter_label": section.get("chapter_label", "") if not sub_chunks else "",
            })
            current_text = []
            current_words = 0

        current_text.append(para)
        current_words += para_words

    if current_text:
        sub_chunks.append({
            "text": "\n\n".join(current_text),
            "start_page": chunk_start_page,
            "end_page": section["pages"][-1].page_num,
            "chapter_label": "",
        })

    return sub_chunks
