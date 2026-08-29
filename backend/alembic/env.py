from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import every model so Base.metadata is fully populated before autogenerate
# runs — app.models.__init__ already does this import-everything step (see
# its docstring), so importing that package is sufficient.
from app.config import settings
from app.models import Base

config = context.config

# Overwrite whatever `sqlalchemy.url` is in alembic.ini with the app's own
# Settings-derived URL, so DATABASE_URL/.env stays the single source of
# truth for the connection string instead of being duplicated into the ini
# file. alembic.ini's sqlalchemy.url is intentionally left blank.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit migrations as SQL text without a live DB connection (`alembic
    upgrade head --sql`) -- useful for generating a script a DBA reviews
    and applies manually in a locked-down production environment."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detect column type changes (e.g. String -> Text) during
            # autogenerate, not just added/removed tables and columns.
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
