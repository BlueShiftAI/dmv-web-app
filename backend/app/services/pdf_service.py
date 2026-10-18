"""
PDF generation service — Demo Registration Preparation Summary.

Generates a clearly-labelled demo PDF using reportlab.
This is NOT an official SCDMV form. It is a preparation aid only.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _format_value(v: object) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "Yes" if v else "No"
    return str(v)


def _section_table(data: dict) -> Table | None:
    if not data:
        return None
    rows = [[_format_value(k.replace("_", " ").title()), _format_value(v)]
            for k, v in data.items()]
    t = Table(rows, colWidths=[2.4 * inch, 4.0 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def generate_preparation_pdf(case_id: str, draft_data: dict) -> bytes:
    """
    Build and return a PDF bytes object for the demo preparation summary.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # ------------------------------------------------------------------
    # Header / disclaimer banner
    # ------------------------------------------------------------------
    banner_style = ParagraphStyle(
        "Banner",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#92400e"),
        backColor=colors.HexColor("#fef3c7"),
        borderColor=colors.HexColor("#fcd34d"),
        borderWidth=1,
        borderPadding=(4, 6, 4, 6),
        leading=12,
    )
    story.append(Paragraph(
        "<b>EDUCATIONAL PROTOTYPE — NOT AN OFFICIAL SCDMV DOCUMENT</b><br/>"
        "This summary is for preparation purposes only. It is not an officially accepted "
        "form, electronic submission, or legally binding document. You must complete and "
        "sign the actual SCDMV Form 400 at the DMV office.",
        banner_style,
    ))
    story.append(Spacer(1, 0.15 * inch))

    # Title
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=4,
    )
    story.append(Paragraph("DMV Registration Preparation Summary", title_style))

    sub_style = ParagraphStyle(
        "Sub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#6b7280"),
    )
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(
        f"Case: {case_id} &nbsp;·&nbsp; Scenario: Private-Party Vehicle Purchase &nbsp;·&nbsp; "
        f"Generated: {generated_at}",
        sub_style,
    ))
    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 0.15 * inch))

    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=colors.HexColor("#1e3a5f"),
        spaceBefore=12,
        spaceAfter=4,
    )

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------
    sections = [
        ("Vehicle Information", draft_data.get("vehicle")),
        ("Buyer / Applicant Information", draft_data.get("buyer")),
        ("Seller Information", draft_data.get("seller")),
        ("Purchase Details", draft_data.get("purchase")),
    ]

    for label, data in sections:
        story.append(Paragraph(label, section_title_style))
        if data:
            t = _section_table(data)
            if t:
                story.append(t)
        else:
            empty_style = ParagraphStyle(
                "Empty",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#9ca3af"),
                leftIndent=6,
            )
            story.append(Paragraph("(Not yet filled in)", empty_style))
        story.append(Spacer(1, 0.05 * inch))

    # Additional notes
    notes = draft_data.get("additional_notes")
    if notes:
        story.append(Paragraph("Additional Notes", section_title_style))
        notes_style = ParagraphStyle(
            "Notes",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#374151"),
            leftIndent=6,
        )
        story.append(Paragraph(notes, notes_style))

    # ------------------------------------------------------------------
    # Footer disclaimer
    # ------------------------------------------------------------------
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 0.08 * inch))
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#9ca3af"),
        alignment=1,  # centre
    )
    story.append(Paragraph(
        "DMV Registration Assistant · IBM SkillsBuild AI Experiential Learning Lab · "
        "Not affiliated with the SCDMV · All data is simulated",
        footer_style,
    ))

    doc.build(story)
    return buf.getvalue()
