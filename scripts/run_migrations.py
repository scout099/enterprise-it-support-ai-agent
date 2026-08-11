"""Safely move one database to the repository's single Alembic head."""

from __future__ import annotations

import sys
from collections.abc import Mapping

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Engine

from enterprise_it_support.platform.config import get_settings

_FTS_INDEX_NAME = "ix_document_chunks_fts"


def _validate_fts_index_contract(index: Mapping[str, object] | None) -> None:
    """Reject a missing or materially different migration-owned FTS index."""
    if index is None:
        raise RuntimeError(f"Required explicit index {_FTS_INDEX_NAME!r} is missing")

    table_name = str(index.get("table_name", ""))
    access_method = str(index.get("access_method", ""))
    expression = str(index.get("expression", "")).lower()
    required_expression_tokens = (
        "to_tsvector",
        "'simple'",
        "coalesce",
        "section_title",
        "content",
    )
    missing_tokens = [token for token in required_expression_tokens if token not in expression]
    if table_name != "document_chunks" or access_method != "gin" or missing_tokens:
        raise RuntimeError(
            f"Explicit index {_FTS_INDEX_NAME!r} does not match the required contract: "
            f"table={table_name!r}, method={access_method!r}, "
            f"missing_expression_tokens={missing_tokens}"
        )


def _verify_explicit_schema_contracts(engine: Engine) -> None:
    """Verify schema objects intentionally excluded from Alembic autogenerate."""
    with engine.connect() as connection:
        index = (
            connection.execute(
                text(
                    """
                    SELECT
                        table_class.relname AS table_name,
                        access_method.amname AS access_method,
                        pg_get_expr(index_catalog.indexprs, index_catalog.indrelid)
                            AS expression
                    FROM pg_index AS index_catalog
                    JOIN pg_class AS index_class
                        ON index_class.oid = index_catalog.indexrelid
                    JOIN pg_class AS table_class
                        ON table_class.oid = index_catalog.indrelid
                    JOIN pg_am AS access_method
                        ON access_method.oid = index_class.relam
                    JOIN pg_namespace AS namespace
                        ON namespace.oid = index_class.relnamespace
                    WHERE namespace.nspname = current_schema()
                        AND index_class.relname = :index_name
                    """
                ),
                {"index_name": _FTS_INDEX_NAME},
            )
            .mappings()
            .one_or_none()
        )
    _validate_fts_index_contract(index)


def migrate_to_head(config_path: str = "alembic.ini") -> int:
    """Apply forward-only migrations once, or return successfully when already current."""
    config = Config(config_path)
    script = ScriptDirectory.from_config(config)
    target_heads = tuple(script.get_heads())
    if len(target_heads) != 1:
        raise RuntimeError(
            f"Refusing automatic migration: expected one Alembic head, found {target_heads}"
        )

    engine = create_engine(
        get_settings().active_database_url,
        poolclass=pool.NullPool,
    )
    try:
        with engine.connect() as connection:
            current_heads = tuple(MigrationContext.configure(connection).get_current_heads())
        if current_heads == target_heads:
            _verify_explicit_schema_contracts(engine)
            print(f"database already at Alembic head {target_heads[0]}")
            return 0

        command.upgrade(config, "head")

        with engine.connect() as connection:
            migrated_heads = tuple(MigrationContext.configure(connection).get_current_heads())
        if migrated_heads != target_heads:
            raise RuntimeError(
                "Automatic migration did not reach the expected head: "
                f"expected {target_heads}, found {migrated_heads}"
            )
        _verify_explicit_schema_contracts(engine)
        print(f"database migrated to Alembic head {target_heads[0]}")
        return 0
    finally:
        engine.dispose()


def main() -> int:
    try:
        return migrate_to_head()
    except Exception as exception:
        print(f"migration_failed: {exception}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
