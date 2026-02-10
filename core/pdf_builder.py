"""Generate formatted PDF from translated text with book-like layout."""
import os
import re
from pathlib import Path

from fpdf import FPDF

FONTS_DIR = Path(__file__).parent.parent / "fonts"


class BookPDF(FPDF):
    def __init__(self, title="", author=""):
        super().__init__()
        self.book_title = title
        self.book_author = author

    def header(self):
        if self.page_no() > 2:
            self.set_font('DejaVu', '', 8)
            self.set_text_color(150, 150, 150)
            label = self.book_title
            if self.book_author:
                label += f' — {self.book_author}'
            self.cell(0, 8, label, new_x="LMARGIN", new_y="NEXT", align='C')
            self.ln(10)

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-18)
            self.set_font('DejaVu', '', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, str(self.page_no() - 1), new_x="RIGHT", new_y="TOP", align='C')


class PDFBuilder:
    def __init__(self, title="Translated Document", author="", subtitle=""):
        self.title = title
        self.author = author
        self.subtitle = subtitle
        self.pdf = BookPDF(title=title, author=author)
        self.pdf.set_auto_page_break(auto=True, margin=25)
        self.pdf.set_margins(28, 22, 28)
        self._setup_fonts()
        self._chapters = []
        self._last_chapter = None

    def _setup_fonts(self):
        regular = str(FONTS_DIR / "DejaVuSans.ttf")
        bold = str(FONTS_DIR / "DejaVuSans-Bold.ttf")
        italic = str(FONTS_DIR / "DejaVuSans-Oblique.ttf")
        bold_italic = str(FONTS_DIR / "DejaVuSans-BoldOblique.ttf")

        if os.path.exists(regular):
            self.pdf.add_font('DejaVu', '', regular)
            self.pdf.add_font('DejaVu', 'B', bold)
            self.pdf.add_font('DejaVu', 'I', italic)
            self.pdf.add_font('DejaVu', 'BI', bold_italic)
            self.font_family = 'DejaVu'
        else:
            self.font_family = 'Helvetica'

    def add_title_page(self):
        self.pdf.add_page()
        self.pdf.ln(60)
        self.pdf.set_font(self.font_family, 'B', 28)
        self.pdf.set_text_color(30, 30, 30)
        self.pdf.multi_cell(0, 14, self.title, align='C')
        if self.subtitle:
            self.pdf.ln(6)
            self.pdf.set_font(self.font_family, 'I', 13)
            self.pdf.set_text_color(90, 90, 90)
            self.pdf.multi_cell(0, 10, self.subtitle, align='C')
        if self.author:
            self.pdf.ln(20)
            self.pdf.set_font(self.font_family, '', 13)
            self.pdf.set_text_color(60, 60, 60)
            self.pdf.cell(0, 9, self.author, new_x="LMARGIN", new_y="NEXT", align='C')

    def add_chapter(self, label, title):
        key = f"{label}|{title}"
        if self._last_chapter == key:
            return
        self._last_chapter = key
        self._chapters.append((label, title))

        self.pdf.add_page()
        self.pdf.ln(8)
        if label:
            self.pdf.set_font(self.font_family, '', 11)
            self.pdf.set_text_color(120, 120, 120)
            self.pdf.cell(0, 8, label, new_x="LMARGIN", new_y="NEXT", align='L')
            self.pdf.ln(2)
        self.pdf.set_font(self.font_family, 'B', 18)
        self.pdf.set_text_color(30, 30, 30)
        self.pdf.multi_cell(0, 10, title, align='L')
        self.pdf.ln(2)
        self.pdf.set_draw_color(180, 180, 180)
        self.pdf.line(self.pdf.l_margin, self.pdf.get_y(),
                      self.pdf.w - self.pdf.r_margin, self.pdf.get_y())
        self.pdf.ln(10)

    def add_section(self, title):
        self.pdf.ln(6)
        self.pdf.set_font(self.font_family, 'B', 12)
        self.pdf.set_text_color(40, 40, 40)
        self.pdf.multi_cell(0, 7.5, title, align='L')
        self.pdf.ln(4)

    def add_subsection(self, title):
        self.pdf.ln(3)
        self.pdf.set_font(self.font_family, 'B', 10.5)
        self.pdf.set_text_color(55, 55, 55)
        self.pdf.multi_cell(0, 7, title, align='L')
        self.pdf.ln(3)

    def add_paragraph(self, text):
        self.pdf.set_font(self.font_family, '', 10.5)
        self.pdf.set_text_color(35, 35, 35)
        self.pdf.multi_cell(0, 6.5, text, align='J')
        self.pdf.ln(4)

    def add_epigraph(self, text):
        self.pdf.set_font(self.font_family, 'I', 9.5)
        self.pdf.set_text_color(100, 100, 100)
        old_l = self.pdf.l_margin
        old_r = self.pdf.r_margin
        self.pdf.set_left_margin(38)
        self.pdf.set_right_margin(38)
        self.pdf.set_x(38)
        self.pdf.multi_cell(self.pdf.w - 76, 6, text, align='L')
        self.pdf.set_left_margin(old_l)
        self.pdf.set_right_margin(old_r)
        self.pdf.ln(10)

    def add_numbered(self, text):
        self.pdf.set_font(self.font_family, '', 10.5)
        self.pdf.set_text_color(35, 35, 35)
        self.pdf.set_x(33)
        self.pdf.multi_cell(self.pdf.w - 61, 6.5, text, align='L')
        self.pdf.ln(3)

    def add_indented(self, text):
        self.pdf.set_font(self.font_family, '', 10.5)
        self.pdf.set_text_color(35, 35, 35)
        self.pdf.set_x(35)
        self.pdf.multi_cell(self.pdf.w - 63, 6.5, text, align='L')
        self.pdf.ln(3)

    def add_italic_paragraph(self, text):
        self.pdf.set_font(self.font_family, 'I', 10.5)
        self.pdf.set_text_color(70, 70, 70)
        self.pdf.multi_cell(0, 6.5, text, align='J')
        self.pdf.ln(4)

    def add_image(self, image_path_or_bytes):
        from PIL import Image as PILImage
        import io

        if isinstance(image_path_or_bytes, bytes):
            img = PILImage.open(io.BytesIO(image_path_or_bytes))
            tmp = "/tmp/_pdf_builder_temp_img.png"
            img.save(tmp)
            image_path = tmp
        else:
            img = PILImage.open(image_path_or_bytes)
            image_path = image_path_or_bytes

        aspect = img.height / img.width
        avail_w = self.pdf.w - self.pdf.l_margin - self.pdf.r_margin
        display_w = min(avail_w * 0.85, 140)
        display_h = display_w * aspect

        space_left = self.pdf.h - self.pdf.get_y() - 30
        if display_h + 15 > space_left:
            self.pdf.add_page()
            self.pdf.ln(10)

        x_offset = (self.pdf.w - display_w) / 2
        self.pdf.ln(6)
        self.pdf.image(image_path, x=x_offset, y=self.pdf.get_y(), w=display_w)
        self.pdf.set_y(self.pdf.get_y() + display_h + 3)
        self.pdf.ln(8)

    def render_translated_text(self, text, images=None):
        """Parse markdown-style translated text and render to PDF.

        Handles: chapter headers, sections (##), bold sections (**...**),
        epigraphs, numbered/lettered lists, indented items, paragraphs.

        Args:
            text: translated text with markdown-like formatting
            images: optional list of ImageInfo to insert at relevant points
        """
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line or line.startswith('====') or line == '---':
                i += 1
                continue

            # Skip meta-commentary from translator
            if line.startswith('Now let me') or line.startswith('Let me'):
                i += 1
                continue

            # Chapter header patterns
            chapter_match = re.match(
                r'^#?\s*(?:CAPÍTULO|CAPITULO|Capítulo|Capitulo|CHAPTER|Chapter|CHAPITRE|Chapitre|KAPITEL|Kapitel|CAPITOLO|Capitolo)\s+(\d+)\s*(?:\(.*?\))?\s*(?:[:—–-]?\s*)(.*)',
                line, re.IGNORECASE)
            if chapter_match:
                ch_num = chapter_match.group(1)
                ch_title = chapter_match.group(2).strip().rstrip('*').strip()
                if not ch_title:
                    j = i + 1
                    while j < len(lines):
                        nl = lines[j].strip()
                        if nl and not nl.startswith('===='):
                            ch_title = nl
                            i = j
                            break
                        j += 1
                self.add_chapter(f'Chapter {ch_num}', ch_title)
                i += 1
                continue

            # Standalone chapter number line
            chapter_match2 = re.match(
                r'^(?:CAPÍTULO|Capítulo|Capitulo|CHAPTER|Chapter)\s+(\d+)\s*$',
                line, re.IGNORECASE)
            if chapter_match2:
                ch_num = chapter_match2.group(1)
                j = i + 1
                ch_title = ''
                while j < len(lines):
                    nl = lines[j].strip()
                    if nl and not nl.startswith('===='):
                        ch_title = nl
                        i = j
                        break
                    j += 1
                self.add_chapter(f'Chapter {ch_num}', ch_title)
                i += 1
                continue

            # Epilogue
            if re.match(r'^#?\s*(?:EPÍLOGO|Epílogo|Epilogo|EPILOGUE|Epilogue)', line, re.IGNORECASE):
                title = re.sub(r'^#?\s*', '', line).strip()
                if ':' in title:
                    parts = title.split(':', 1)
                    self.add_chapter(parts[0].strip(), parts[1].strip())
                elif '—' in title:
                    parts = title.split('—', 1)
                    self.add_chapter(parts[0].strip(), parts[1].strip())
                else:
                    self.add_chapter('', title)
                i += 1
                continue

            # Appendix
            appendix_match = re.match(
                r'^#?\s*(?:APÉNDICE|Apéndice|Apendice|APPENDIX|Appendix|ANNEXE|Annexe)\s+([A-Z\d]+)\s*[:—–-]?\s*(.*)',
                line, re.IGNORECASE)
            if appendix_match:
                self.add_chapter(f'Appendix {appendix_match.group(1)}',
                                 appendix_match.group(2).strip())
                i += 1
                continue

            # Bibliography
            if re.match(r'^#?\s*(?:BIBLIOGRAFÍA|Bibliografía|BIBLIOGRAPHY|Bibliography|RÉFÉRENCES|REFERENZEN)',
                        line, re.IGNORECASE):
                title = re.sub(r'^#?\s*', '', line).strip()
                self.add_chapter('', title or 'Bibliography')
                i += 1
                continue

            # Section header: "## Title"
            section_match = re.match(r'^##\s+(.*)', line)
            if section_match:
                self.add_section(section_match.group(1).strip())
                i += 1
                continue

            # Standalone bold line = subsection
            bold_section = re.match(r'^\*\*([^*]+)\*\*\s*$', line)
            if bold_section:
                self.add_subsection(bold_section.group(1).strip())
                i += 1
                continue

            # Bold label + text: **Label:** rest
            bold_para = re.match(r'^\*\*([^*]+)\*\*\s*(.*)', line)
            if bold_para and bold_para.group(2):
                label = bold_para.group(1).strip()
                rest = bold_para.group(2).strip()
                j = i + 1
                while j < len(lines):
                    nl = lines[j].strip()
                    if not nl or nl.startswith('#') or nl.startswith('**') or nl.startswith('====') or re.match(r'^\d+\.', nl):
                        break
                    rest += ' ' + nl
                    j += 1
                self.add_paragraph(f'{label}: {rest}')
                i = j
                continue

            # Epigraph
            if line.startswith('*"') or line.startswith('*«') or (line.startswith('"') and line.endswith('*')):
                quote = line.strip('*').strip()
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('—'):
                    quote += ' ' + lines[i + 1].strip()
                    i += 1
                self.add_epigraph(quote)
                i += 1
                continue

            if line.startswith('"') and ('—' in line or '–' in line):
                self.add_epigraph(line)
                i += 1
                continue

            # Numbered list
            numbered = re.match(r'^(\d+)\.\s+(.*)', line)
            if numbered:
                text = f'{numbered.group(1)}. {numbered.group(2)}'
                j = i + 1
                while j < len(lines):
                    nl = lines[j].strip()
                    if not nl or re.match(r'^\d+\.', nl) or nl.startswith('#') or nl.startswith('**'):
                        break
                    text += ' ' + nl
                    j += 1
                self.add_numbered(text)
                i = j
                continue

            # Lettered list
            lettered = re.match(r'^([A-Z])\.\s+(.*)', line)
            if lettered and len(line) > 5:
                text = f'{lettered.group(1)}. {lettered.group(2)}'
                j = i + 1
                while j < len(lines):
                    nl = lines[j].strip()
                    if not nl or re.match(r'^[A-Z]\.', nl) or nl.startswith('#') or nl.startswith('**'):
                        break
                    text += ' ' + nl
                    j += 1
                self.add_indented(text)
                i = j
                continue

            # Italic standalone
            if line.startswith('*') and line.endswith('*') and not line.startswith('**'):
                self.add_italic_paragraph(line.strip('*').strip())
                i += 1
                continue

            # Indented with colon
            if line.startswith('  ') and ':' in lines[i]:
                self.add_indented(line.strip())
                i += 1
                continue

            # Regular paragraph — collect continuation lines
            para_lines = [line]
            j = i + 1
            while j < len(lines):
                nl = lines[j].strip()
                if not nl:
                    break
                if (nl.startswith('#') or nl.startswith('====') or nl.startswith('---') or
                        nl.startswith('**') or re.match(r'^\d+\.\s', nl) or
                        re.match(r'^[A-Z]\.\s', nl) or nl.startswith('*"') or nl.startswith('*«')):
                    break
                para_lines.append(nl)
                j += 1

            full = ' '.join(para_lines)
            full = re.sub(r'\*\*([^*]+)\*\*', r'\1', full)
            full = re.sub(r'\*([^*]+)\*', r'\1', full)
            if full.strip():
                self.add_paragraph(full)
            i = j if j > i + 1 else i + 1

    def save(self, output_path: str):
        self.pdf.output(output_path)
        return output_path

    def get_bytes(self) -> bytes:
        return bytes(self.pdf.output())

    @property
    def page_count(self) -> int:
        return self.pdf.page_no()
