"""Unit tests for migration-owned schema contract validation."""

import pytest
from scripts.run_migrations import _validate_fts_index_contract


def test_fts_index_contract_accepts_expected_index() -> None:
    _validate_fts_index_contract(
        {
            "table_name": "document_chunks",
            "access_method": "gin",
            "expression": (
                "to_tsvector('simple'::regconfig, "
                "((COALESCE(section_title, ''::character varying)::text || ' '::text) "
                "|| content))"
            ),
        }
    )


@pytest.mark.parametrize(
    "index",
    [
        None,
        {
            "table_name": "document_chunks",
            "access_method": "btree",
            "expression": "content",
        },
    ],
)
def test_fts_index_contract_rejects_missing_or_changed_index(
    index: dict[str, object] | None,
) -> None:
    with pytest.raises(RuntimeError, match=r"[Ee]xplicit index"):
        _validate_fts_index_contract(index)
