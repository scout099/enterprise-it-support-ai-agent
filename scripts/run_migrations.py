"""Safely move one database to the repository's single Alembic head."""

from __future__ import annotations

import sys

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, pool

from enterprise_it_support.platform.config import get_settings


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
