"""Document parser behavior tests."""

from pathlib import Path

import pytest

from enterprise_it_support.knowledge.domain import DocumentSourceType
from enterprise_it_support.knowledge.parsers import DocumentParseError, DocumentParserRegistry

FIXTURES = Path(__file__).parents[3] / "data" / "evaluation" / "knowledge"


def test_txt_parser_returns_normalized_sections_with_line_positions() -> None:
    path = FIXTURES / "outlook_mail_troubleshooting.txt"

    content = DocumentParserRegistry().parse(path.name, path.read_bytes())

    assert content.source_type is DocumentSourceType.TXT
    assert content.title == "Outlook Mail Delivery Troubleshooting SOP"
    assert content.sections[0].content.startswith("Outlook Mail Delivery")
    assert content.sections[0].location.start_line == 1
    assert content.sections[-1].location.end_line == 12
    assert "demo mailbox" in content.canonical_text


def test_markdown_parser_preserves_heading_boundaries() -> None:
    path = FIXTURES / "vpn_configuration_sop.md"

    content = DocumentParserRegistry().parse(path.name, path.read_bytes())

    assert content.source_type is DocumentSourceType.MARKDOWN
    assert content.title == "Northwind Demo VPN Configuration SOP"
    assert [section.title for section in content.sections] == [
        "Northwind Demo VPN Configuration SOP",
        "Before you begin",
        "Configure the client",
        "Troubleshooting",
    ]
    assert content.sections[1].location.start_line == 5
    assert content.sections[-1].location.end_line == 17
    assert "Configure the client" in content.canonical_text


def test_pdf_parser_preserves_page_positions() -> None:
    path = FIXTURES / "account_common_questions_faq.pdf"

    content = DocumentParserRegistry().parse(path.name, path.read_bytes())

    assert content.source_type is DocumentSourceType.PDF
    assert content.title == "Enterprise Account Common Questions FAQ"
    assert len(content.sections) == 2
    assert content.sections[0].location.page_number == 1
    assert content.sections[1].location.page_number == 2
    assert "ACCOUNT-TRAINING" in content.sections[1].content


def test_corrupted_pdf_returns_clear_parse_error() -> None:
    with pytest.raises(DocumentParseError, match="could not be parsed"):
        DocumentParserRegistry().parse("broken.pdf", b"not-a-pdf")
