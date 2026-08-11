"""Parsers that normalize supported files into DocumentContent."""

import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from enterprise_it_support.knowledge.domain import (
    DocumentContent,
    DocumentSection,
    DocumentSourceType,
    SourceLocation,
)

_markdown_heading = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


class UnsupportedDocumentTypeError(ValueError):
    """Raised when no parser is registered for a file suffix."""


class DocumentParseError(ValueError):
    """Raised when a supported file cannot produce meaningful text."""


def _decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exception:
        raise DocumentParseError("Text documents must use UTF-8 encoding") from exception


def _paragraph_sections(text: str) -> tuple[DocumentSection, ...]:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    sections: list[DocumentSection] = []
    paragraph: list[str] = []
    start_line = 1

    def append_paragraph(end_line: int) -> None:
        if not paragraph:
            return
        content = "\n".join(paragraph).strip()
        if content:
            sections.append(
                DocumentSection(
                    content=content,
                    location=SourceLocation(start_line=start_line, end_line=end_line),
                )
            )
        paragraph.clear()

    for line_number, line in enumerate(lines, start=1):
        if line.strip():
            if not paragraph:
                start_line = line_number
            paragraph.append(line.strip())
        else:
            append_paragraph(line_number - 1)
    append_paragraph(len(lines))
    return tuple(sections)


def _markdown_sections(text: str) -> tuple[DocumentSection, ...]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    sections: list[DocumentSection] = []
    body: list[str] = []
    section_title: str | None = None
    section_start = 1
    in_code_fence = False

    def append_section(end_line: int) -> None:
        while body and not body[-1].strip():
            body.pop()
            end_line -= 1
        content = "\n".join(body).strip()
        if content:
            sections.append(
                DocumentSection(
                    title=section_title,
                    content=content,
                    location=SourceLocation(start_line=section_start, end_line=end_line),
                )
            )
        body.clear()

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
        heading = None if in_code_fence else _markdown_heading.match(stripped)
        if heading:
            append_section(line_number - 1)
            section_title = heading.group(2).strip()
            section_start = line_number
            continue
        body.append(line.rstrip())

    append_section(len(lines))
    return tuple(sections)


class DocumentParserRegistry:
    """Select a deterministic parser from the uploaded filename."""

    def parse(self, filename: str, data: bytes) -> DocumentContent:
        suffix = Path(filename).suffix.lower()
        if suffix == ".txt":
            return self._parse_txt(filename, data)
        if suffix in {".md", ".markdown"}:
            return self._parse_markdown(filename, data)
        if suffix == ".pdf":
            return self._parse_pdf(filename, data)
        raise UnsupportedDocumentTypeError(f"Unsupported document type: {suffix or 'none'}")

    def _parse_txt(self, filename: str, data: bytes) -> DocumentContent:
        sections = _paragraph_sections(_decode_text(data))
        if not sections:
            raise DocumentParseError("Document does not contain readable text")
        title = sections[0].content.splitlines()[0].strip() or Path(filename).stem
        return DocumentContent(
            source_type=DocumentSourceType.TXT,
            title=title,
            sections=sections,
            metadata={"original_filename": filename},
        )

    def _parse_pdf(self, filename: str, data: bytes) -> DocumentContent:
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise DocumentParseError("Encrypted PDF documents are not supported")
            parsed_pages = []
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = _normalize_pdf_text(page.extract_text() or "")
                if page_text:
                    parsed_pages.append(
                        DocumentSection(
                            content=page_text,
                            location=SourceLocation(page_number=page_number),
                        )
                    )
            sections = tuple(parsed_pages)
        except DocumentParseError:
            raise
        except (PdfReadError, OSError, ValueError) as exception:
            raise DocumentParseError("PDF document could not be parsed") from exception

        if not sections:
            raise DocumentParseError("PDF document does not contain extractable text")
        metadata_title = reader.metadata.title if reader.metadata else None
        title = (metadata_title or sections[0].content.splitlines()[0]).strip()
        return DocumentContent(
            source_type=DocumentSourceType.PDF,
            title=title or Path(filename).stem,
            sections=sections,
            metadata={"original_filename": filename, "page_count": len(reader.pages)},
        )

    def _parse_markdown(self, filename: str, data: bytes) -> DocumentContent:
        sections = _markdown_sections(_decode_text(data))
        if not sections:
            raise DocumentParseError("Document does not contain readable text")
        title = next(
            (section.title for section in sections if section.title),
            Path(filename).stem,
        )
        return DocumentContent(
            source_type=DocumentSourceType.MARKDOWN,
            title=title,
            sections=sections,
            metadata={"original_filename": filename},
        )


def _normalize_pdf_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()
