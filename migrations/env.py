"""Alembic migration environment."""

from alembic import context
from sqlalchemy import create_engine, pool

from enterprise_it_support.agent_runtime import models as agent_models  # noqa: F401
from enterprise_it_support.analytics import models as analytics_models  # noqa: F401
from enterprise_it_support.conversation import models as conversation_models  # noqa: F401
from enterprise_it_support.governance import models as governance_models  # noqa: F401
from enterprise_it_support.knowledge import models as knowledge_models  # noqa: F401
from enterprise_it_support.platform.config import get_settings
from enterprise_it_support.platform.database import Base
from enterprise_it_support.service_desk import models as service_desk_models  # noqa: F401
from enterprise_it_support.tools import models as tool_models  # noqa: F401

config = context.config
target_metadata = Base.metadata

_LANGGRAPH_CHECKPOINT_TABLES = frozenset(
    {
        "checkpoint_blobs",
        "checkpoint_migrations",
        "checkpoint_writes",
        "checkpoints",
    }
)
# SQLAlchemy/Alembic cannot reliably round-trip this PostgreSQL expression index.
# It remains migration-owned and is verified explicitly by scripts.run_migrations.
_EXPLICITLY_VERIFIED_INDEXES = frozenset({"ix_document_chunks_fts"})


def include_managed_object(
    _object: object,
    name: str | None,
    type_: str,
    _reflected: bool,
    _compare_to: object | None,
) -> bool:
    """Limit autogenerate checks to schema objects owned by project metadata."""
    if type_ == "table" and name in _LANGGRAPH_CHECKPOINT_TABLES:
        return False
    if type_ == "index" and name in _EXPLICITLY_VERIFIED_INDEXES:
        return False
    return True


def run_migrations_offline() -> None:
    """Generate SQL without opening a database connection."""
    context.configure(
        url=get_settings().active_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_managed_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations through a short-lived synchronous engine."""
    engine = create_engine(
        get_settings().active_database_url,
        poolclass=pool.NullPool,
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_managed_object,
        )

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
