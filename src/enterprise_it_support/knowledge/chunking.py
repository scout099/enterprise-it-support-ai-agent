"""Deterministic, boundary-aware chunking for normalized document content."""

import re
from dataclasses import asdict, dataclass
from typing import Any

from enterprise_it_support.knowledge.domain import DocumentContent, DocumentSection

_token_pattern = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)*|[^\w\s]")
_paragraph_break = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class DocumentChunkDraft:
    """A persistence-ready chunk produced before database identifiers exist."""

    chunk_index: int
    content: str
    token_count: int
    section_title: str | None
    metadata: dict[str, Any]


class DocumentChunker:
    """Split sections into overlapping chunks while preferring paragraph ends."""

    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size < 2:
            raise ValueError("chunk_size must be at least 2")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(self, document: DocumentContent) -> tuple[DocumentChunkDraft, ...]:
        """Return ordered, non-empty chunks with source trace metadata."""
        chunks: list[DocumentChunkDraft] = []
        for section_index, section in enumerate(document.sections):
            for chunk_text, token_start, token_end in self._split_section(section):
                token_count = token_end - token_start
                if token_count < 2 or not any(character.isalnum() for character in chunk_text):
                    continue
                chunks.append(
                    DocumentChunkDraft(
                        chunk_index=len(chunks),
                        content=chunk_text,
                        token_count=token_count,
                        section_title=section.title,
                        metadata={
                            "source_type": document.source_type.value,
                            "original_filename": document.metadata.get("original_filename"),
                            "section_index": section_index,
                            "source_location": asdict(section.location),
                            "token_start": token_start,
                            "token_end": token_end,
                        },
                    )
                )
        return tuple(chunks)

    def _split_section(self, section: DocumentSection) -> list[tuple[str, int, int]]:
        text = section.content.strip()
        tokens = list(_token_pattern.finditer(text))
        if not tokens:
            return []

        paragraph_ends = self._paragraph_token_ends(text, tokens)
        chunks: list[tuple[str, int, int]] = []
        start = 0
        while start < len(tokens):
            target_end = min(start + self._chunk_size, len(tokens))
            end = self._preferred_end(start, target_end, paragraph_ends)
            chunk_text = text[tokens[start].start() : tokens[end - 1].end()].strip()
            chunks.append((chunk_text, start, end))
            if end == len(tokens):
                break
            start = end - self._chunk_overlap
        return chunks

    def _preferred_end(self, start: int, target_end: int, paragraph_ends: set[int]) -> int:
        minimum_size = max(2, self._chunk_size // 2)
        candidates = [
            boundary
            for boundary in paragraph_ends
            if start + minimum_size <= boundary <= target_end
        ]
        return max(candidates, default=target_end)

    @staticmethod
    def _paragraph_token_ends(text: str, tokens: list[re.Match[str]]) -> set[int]:
        boundaries = set()
        for paragraph_break in _paragraph_break.finditer(text):
            tokens_before_break = sum(token.end() <= paragraph_break.start() for token in tokens)
            if tokens_before_break:
                boundaries.add(tokens_before_break)
        return boundaries
