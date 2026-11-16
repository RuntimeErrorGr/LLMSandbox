from logging.config import fileConfig

from alembic import context

from app.db import models
from app.db.session import engine

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

target_metadata = models.Base.metadata


def run_migrations() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
