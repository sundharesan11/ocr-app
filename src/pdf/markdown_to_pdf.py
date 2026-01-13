"""Markdown to PDF converter - Preserves original document structure.

Uses Mistral's basic OCR markdown output and converts it to a
professionally formatted PDF that matches the original document layout.
"""

import io
import re

from fpdf import FPDF

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MarkdownPDF(FPDF):
    """FPDF subclass for rendering markdown content."""

    def __init__(self):
        super().__init__()
        self.set_left_margin(15)
        self.set_right_margin(15)
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)

        # Use built-in fonts only
        self.set_font("Helvetica", size=10)

    def add_title(self, text: str):
        """Add a main title (H1)."""
        try:
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(26, 54, 93)  # Dark blue
            # Clean and truncate
            text = text[:150] if len(text) > 150 else text
            text = text.replace("☑", "[X]").replace("☐", "[ ]")
            text = text.encode("latin-1", errors="replace").decode("latin-1")
            self.multi_cell(0, 10, text)
            self.ln(2)
            # Add underline
            self.set_draw_color(44, 82, 130)
            self.line(15, self.get_y(), 195, self.get_y())
            self.ln(5)
            self.set_text_color(0, 0, 0)
        except Exception:
            self.ln(5)

    def add_heading(self, text: str, level: int = 2):
        """Add a heading (H2, H3, etc.)."""
        try:
            if level == 2:
                self.set_font("Helvetica", "B", 13)
                self.set_text_color(44, 82, 130)
            elif level == 3:
                self.set_font("Helvetica", "B", 11)
                self.set_text_color(45, 55, 72)
            else:
                self.set_font("Helvetica", "B", 10)
                self.set_text_color(0, 0, 0)

            self.ln(3)
            # Clean and truncate
            text = text[:200] if len(text) > 200 else text
            text = text.replace("☑", "[X]").replace("☐", "[ ]")
            text = text.encode("latin-1", errors="replace").decode("latin-1")
            self.multi_cell(0, 7, text)
            self.ln(2)
            self.set_text_color(0, 0, 0)
            self.set_font("Helvetica", size=10)
        except Exception:
            self.set_font("Helvetica", size=10)
            self.ln(3)

    def add_paragraph(self, text: str):
        """Add a paragraph of text."""
        self.set_font("Helvetica", size=10)
        # Handle special characters
        text = text.replace("☑", "[X]").replace("☐", "[ ]")
        # Remove any problematic characters
        text = text.encode("latin-1", errors="replace").decode("latin-1")
        # Split very long words
        if text and len(text) > 0:
            try:
                self.multi_cell(0, 5, text)
                self.ln(2)
            except Exception:
                # Fallback: just skip this line if it can't render
                pass

    def add_table(self, rows: list[list[str]]):
        """Add a simple table."""
        if not rows:
            return

        try:
            self.set_font("Helvetica", size=8)

            # Calculate column widths
            page_width = self.w - 30  # margins
            num_cols = len(rows[0]) if rows else 1
            col_width = min(page_width / num_cols, 60)  # Cap column width

            # Header row
            if rows:
                self.set_font("Helvetica", "B", 8)
                self.set_fill_color(247, 250, 252)
                for cell in rows[0]:
                    cell_text = str(cell).replace("☑", "[X]").replace("☐", "[ ]")
                    cell_text = cell_text.encode("latin-1", errors="replace").decode("latin-1")
                    self.cell(col_width, 7, cell_text[:25], border=1, fill=True)
                self.ln()

            # Data rows
            self.set_font("Helvetica", size=8)
            for row in rows[1:]:
                for cell in row:
                    cell_text = str(cell).replace("☑", "[X]").replace("☐", "[ ]")
                    cell_text = cell_text.encode("latin-1", errors="replace").decode("latin-1")
                    self.cell(col_width, 6, cell_text[:25], border=1)
                self.ln()

            self.ln(3)
        except Exception:
            # Skip table if it can't render
            pass

    def add_list_item(self, text: str, bullet: str = "*"):
        """Add a list item."""
        try:
            self.set_font("Helvetica", size=10)
            text = text.replace("☑", "[X]").replace("☐", "[ ]")
            text = text.encode("latin-1", errors="replace").decode("latin-1")
            self.cell(8, 5, bullet)
            self.multi_cell(0, 5, text)
        except Exception:
            pass


def parse_markdown_table(lines: list[str], start_idx: int) -> tuple[list[list[str]], int]:
    """Parse a markdown table starting at given index.

    Returns tuple of (table_rows, end_index).
    """
    rows = []
    idx = start_idx

    while idx < len(lines):
        line = lines[idx].strip()
        if not line.startswith("|"):
            break

        # Skip separator lines (|---|---|)
        if re.match(r"^\|[\s\-:]+\|", line):
            idx += 1
            continue

        # Parse table cells
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if cells:
            rows.append(cells)

        idx += 1

    return rows, idx


def ocr_text_to_pdf(raw_text: str, title: str = "Digitized Document") -> bytes:
    """Convert raw OCR text (markdown format) to PDF.

    This preserves the original document structure including:
    - Headers and sections
    - Tables
    - Checkboxes
    - Formatting

    Args:
        raw_text: Raw text from Mistral OCR (in markdown format)
        title: Document title

    Returns:
        PDF file as bytes
    """
    logger.info("Converting markdown to PDF", title=title)

    pdf = MarkdownPDF()
    lines = raw_text.split("\n")

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        # Skip empty lines
        if not line:
            idx += 1
            continue

        # H1 Title
        if line.startswith("# "):
            pdf.add_title(line[2:])
            idx += 1
            continue

        # H2 Heading
        if line.startswith("## "):
            pdf.add_heading(line[3:], level=2)
            idx += 1
            continue

        # H3 Heading
        if line.startswith("### "):
            pdf.add_heading(line[4:], level=3)
            idx += 1
            continue

        # Table
        if line.startswith("|"):
            table_rows, idx = parse_markdown_table(lines, idx)
            if table_rows:
                pdf.add_table(table_rows)
            continue

        # List item
        if line.startswith("- ") or line.startswith("* "):
            pdf.add_list_item(line[2:])
            idx += 1
            continue

        # Numbered list
        if re.match(r"^\d+\.\s", line):
            match = re.match(r"^(\d+)\.\s(.+)", line)
            if match:
                pdf.add_list_item(match.group(2), bullet=f"{match.group(1)}.")
            idx += 1
            continue

        # Regular paragraph
        pdf.add_paragraph(line)
        idx += 1

    # Generate PDF bytes
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()

    logger.info(f"PDF generated, size: {len(pdf_bytes)} bytes")
    return pdf_bytes
