"""
pdf_export.py
-------------
Generates a professional PDF report summarizing the student's profile,
favorite universities, AI recommendation, and university comparison.

Built with ReportLab's Platypus layer so the report reflows nicely
regardless of content length.
"""

from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils import AppState, University

ACCENT_COLOR = colors.HexColor("#2f6fed")
DARK_TEXT = colors.HexColor("#1a1d24")
MUTED_TEXT = colors.HexColor("#5a6072")


class PDFReportGenerator:
    """Builds the exportable PDF report from the current AppState."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._register_custom_styles()

    def _register_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name="ReportTitle", fontSize=22, leading=26, textColor=ACCENT_COLOR,
            spaceAfter=4, fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="ReportSubtitle", fontSize=10, textColor=MUTED_TEXT, spaceAfter=18,
        ))
        self.styles.add(ParagraphStyle(
            name="SectionHeading", fontSize=14, textColor=DARK_TEXT, spaceBefore=18,
            spaceAfter=8, fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="BodyTextCustom", fontSize=10, leading=15, textColor=DARK_TEXT,
        ))

    def generate(self, filepath: str, state: AppState) -> None:
        """Write the PDF report to `filepath`. Raises on I/O failure."""
        doc = SimpleDocTemplate(
            filepath, pagesize=LETTER,
            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
            leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        )
        story = []

        story.append(Paragraph("AI College Finder", self.styles["ReportTitle"]))
        story.append(Paragraph("Personalized University Report", self.styles["ReportSubtitle"]))
        story.append(HRFlowable(width="100%", color=ACCENT_COLOR, thickness=1.2))

        story.extend(self._build_profile_section(state))
        story.extend(self._build_favorites_section(state.favorites))
        story.extend(self._build_text_section("AI Recommendation", state.last_recommendation))
        story.extend(self._build_text_section("University Comparison", state.last_comparison))

        doc.build(story)

    # -- section builders -----------------------------------------------------

    def _build_profile_section(self, state: AppState) -> list:
        elements = [Paragraph("Student Profile", self.styles["SectionHeading"])]
        data = [[k, v] for k, v in state.profile.as_dict().items()]
        table = Table(data, colWidths=[1.8 * inch, 4.2 * inch])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (-1, -1), DARK_TEXT),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#dfe3ec")),
        ]))
        elements.append(table)
        return elements

    def _build_favorites_section(self, favorites: List[University]) -> list:
        elements = [Paragraph("Favorite Universities", self.styles["SectionHeading"])]
        if not favorites:
            elements.append(Paragraph("No favorites saved yet.", self.styles["BodyTextCustom"]))
            return elements

        items = [
            ListItem(Paragraph(
                f"<b>{u.name}</b> — {u.country}"
                + (f" ({u.website})" if u.website else ""),
                self.styles["BodyTextCustom"],
            ))
            for u in favorites
        ]
        elements.append(ListFlowable(items, bulletType="bullet", leftIndent=14))
        return elements

    def _build_text_section(self, heading: str, text: str) -> list:
        elements = [Paragraph(heading, self.styles["SectionHeading"])]
        if not text or not text.strip():
            elements.append(Paragraph(
                f"No {heading.lower()} generated yet.", self.styles["BodyTextCustom"]
            ))
            return elements

        # Preserve paragraph breaks from the AI response.
        for block in text.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            safe_block = block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_block = safe_block.replace("\n", "<br/>")
            elements.append(Paragraph(safe_block, self.styles["BodyTextCustom"]))
            elements.append(Spacer(1, 6))
        return elements
