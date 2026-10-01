import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from vehicle_platform.core.config import Settings


def run_sync(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


async def run() -> None:
    engine = create_async_engine(
        Settings().database_url.get_secret_value(), poolclass=pool.NullPool
    )
    async with engine.connect() as connection:
        await connection.run_sync(run_sync)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=Settings().database_url.get_secret_value(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run())
