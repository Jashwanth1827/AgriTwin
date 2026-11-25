"""Alembic environment for AgriTwin.

The URL comes from :mod:`app.core.config` (``DATABASE_URL``) so that the CLI,
the API and the test suite can never drift onto different databases.  SQLite
uses batch mode so that future ALTER operations work on older SQLite builds.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Make ``backend/`` importable when Alembic is invoked from the repo root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  (registers every table on Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    # Escape percent signs for ConfigParser interpolation.
    return settings.DATABASE_URL.replace("%", "%%")


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=settings.is_sqlite,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Emit SQL without connecting to a database."""
    _configure(
        url=_database_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the configured database and apply migrations."""
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
