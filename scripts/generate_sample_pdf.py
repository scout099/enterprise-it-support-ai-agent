"""Generate the fictional account FAQ PDF used by knowledge ingestion tests."""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUTPUT_PATH = Path("tests/fixtures/knowledge/account_common_questions_faq.pdf")


def _draw_page_number(canvas, document) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setFillColor(HexColor("#52606D"))
    canvas.setFont("Helvetica", 9)
    canvas.drawString(0.75 * inch, 0.5 * inch, "Northwind Demo - Fictional IT Knowledge")
    canvas.drawRightString(7.75 * inch, 0.5 * inch, f"Page {document.page}")
    canvas.restoreState()


def generate_pdf(output_path: Path = OUTPUT_PATH) -> None:
    """Create a stable two-page PDF containing fictional account guidance."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=HexColor("#173F5F"),
        spaceAfter=18,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        textColor=HexColor("#20639B"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        leading=15,
        spaceAfter=10,
    )
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.75 * inch,
        title="Enterprise Account Common Questions FAQ",
        author="Northwind Demo IT Learning Team",
    )
    story = [
        Paragraph("Enterprise Account Common Questions FAQ", title_style),
        Paragraph(
            "This fictional FAQ is for demonstration only. It contains no real company, "
            "employee, domain, or support contact information.",
            body_style,
        ),
        Paragraph("How do I reset a forgotten password?", heading_style),
        Paragraph(
            "Open the fictional Northwind Demo identity portal and choose Reset password. "
            "Complete the training verification prompt, then create a unique practice password.",
            body_style,
        ),
        Paragraph("Why is my account temporarily locked?", heading_style),
        Paragraph(
            "Five unsuccessful demonstration sign-in attempts trigger a fifteen-minute lock. "
            "Wait for the timer to finish before retrying so the training counter is not extended.",
            body_style,
        ),
        Paragraph("What should I do when verification prompts do not arrive?", heading_style),
        Paragraph(
            "Confirm that the fictional authentication app shows the Northwind Demo profile. "
            "Check the device clock and network connection, then request one new prompt.",
            body_style,
        ),
        PageBreak(),
        Paragraph("Account Access Escalation", title_style),
        Paragraph("When should I contact the local IT queue?", heading_style),
        Paragraph(
            "Escalate when the demo identity portal reports that verification methods are "
            "unavailable, or when access remains blocked after the documented waiting period.",
            body_style,
        ),
        Paragraph("What information is safe to include?", heading_style),
        Paragraph(
            "Provide the fictional employee alias, approximate failure time, device type, and "
            "the displayed training error code. Never include a password or verification code.",
            body_style,
        ),
        Spacer(1, 18),
        Paragraph(
            "Demo escalation reference: ACCOUNT-TRAINING. This value is fictional and cannot "
            "contact a real support team.",
            body_style,
        ),
    ]
    document.build(story, onFirstPage=_draw_page_number, onLaterPages=_draw_page_number)


if __name__ == "__main__":
    generate_pdf()
