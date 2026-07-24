import io
import re
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

_PDF_REQUEST = re.compile(
    r"\b(?:create|convert|download|export|make|save|turn|write)\b"
    r".{0,60}\bpdf\b",
    re.IGNORECASE | re.DOTALL,
)


def is_pdf_export_request(text: str) -> bool:
    stripped = text.strip()
    return stripped == "/pdf" or stripped.startswith("/pdf ") or bool(
        _PDF_REQUEST.search(stripped)
    )


def explicit_pdf_text(text: str) -> str | None:
    stripped = text.strip()
    if not stripped.startswith("/pdf "):
        return None
    value = stripped.removeprefix("/pdf ").strip()
    return value or None


def render_pdf(text: str, *, title: str = "Assistant Response") -> bytes:
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=title,
        author="Private Ollama",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "ExportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=HexColor("#172033"),
        alignment=TA_LEFT,
        spaceAfter=7,
    )
    heading = ParagraphStyle(
        "ExportHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        textColor=HexColor("#0F766E"),
        spaceBefore=8,
        spaceAfter=6,
    )
    title_style = ParagraphStyle(
        "ExportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=HexColor("#0F766E"),
        spaceAfter=14,
    )
    story = [Paragraph(escape(title), title_style), Spacer(1, 2 * mm)]
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 2.5 * mm))
            continue
        if line == "---PAGE BREAK---":
            story.append(PageBreak())
        elif line.startswith(("### ", "## ", "# ")):
            story.append(Paragraph(escape(line.lstrip("#").strip()), heading))
        elif line.startswith(("- ", "* ", "• ")):
            story.append(
                Paragraph(
                    f"• {escape(line[2:].strip())}",
                    body,
                    bulletText="",
                )
            )
        else:
            cleaned = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(line))
            story.append(Paragraph(cleaned, body))
    document.build(story)
    return output.getvalue()
