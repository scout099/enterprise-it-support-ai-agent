"""Boundary-aware document chunking tests."""

from enterprise_it_support.knowledge.chunking import DocumentChunker
from enterprise_it_support.knowledge.domain import (
    DocumentContent,
    DocumentSection,
    DocumentSourceType,
    SourceLocation,
)


def test_chunk_size_and_overlap_are_applied_to_long_sections() -> None:
    content = DocumentContent(
        source_type=DocumentSourceType.TXT,
        title="Numbered words",
        sections=(
            DocumentSection(
                title="Sequence",
                content=(
                    "one two three four five six seven eight nine ten eleven twelve "
                    "thirteen fourteen fifteen sixteen"
                ),
                location=SourceLocation(start_line=3, end_line=3),
            ),
        ),
        metadata={"original_filename": "sequence.txt"},
    )

    chunks = DocumentChunker(chunk_size=8, chunk_overlap=2).split(content)

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert [chunk.token_count for chunk in chunks] == [8, 8, 4]
    assert chunks[0].content.split()[-2:] == chunks[1].content.split()[:2]
    assert chunks[1].content.split()[-2:] == chunks[2].content.split()[:2]
    assert chunks[0].section_title == "Sequence"
    assert chunks[0].metadata["source_location"] == {
        "start_line": 3,
        "end_line": 3,
        "page_number": None,
    }


def test_chunker_prefers_paragraph_boundaries_and_skips_meaningless_text() -> None:
    content = DocumentContent(
        source_type=DocumentSourceType.MARKDOWN,
        title="Boundary guide",
        sections=(
            DocumentSection(
                title="Useful section",
                content=("alpha beta gamma delta epsilon zeta\n\neta theta iota kappa lambda mu"),
                location=SourceLocation(start_line=4, end_line=7),
            ),
            DocumentSection(
                title="Empty decoration",
                content="#",
                location=SourceLocation(start_line=8, end_line=8),
            ),
        ),
        metadata={"original_filename": "boundaries.md"},
    )

    chunks = DocumentChunker(chunk_size=8, chunk_overlap=2).split(content)

    assert chunks[0].content == "alpha beta gamma delta epsilon zeta"
    assert chunks[1].content.startswith("epsilon zeta")
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert all(chunk.content.strip() for chunk in chunks)
    assert all(chunk.section_title == "Useful section" for chunk in chunks)
