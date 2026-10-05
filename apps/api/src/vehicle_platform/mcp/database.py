"""Read-only connection defaults also bound queries before a transaction begins."""

from typing import Protocol, cast

from sqlalchemy import event
from sqlalchemy.engine.interfaces import AdaptedConnection
from sqlalchemy.pool import ConnectionPoolEntry

from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database


class Terminable(Protocol):
    def terminate(self) -> None: ...


class ReadOnlyDatabase(Database):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings,
            command_timeout=5,
            server_settings={
                "default_transaction_read_only": "on",
                "statement_timeout": "5000",
                "lock_timeout": "1000",
            },
        )
        self.engine = self.engine.execution_options(postgresql_readonly=True)
        self.sessions.configure(bind=self.engine)

        event.listen(self.engine.sync_engine.pool, "invalidate", self._abort_invalidated)

    @staticmethod
    def _abort_invalidated(
        connection: "AdaptedConnection | None",
        record: "ConnectionPoolEntry",
        exception: BaseException | None,
    ) -> None:
        # A paused backend cannot acknowledge asyncpg cancellation. Aborting an
        # invalidated read connection avoids waiting for a graceful cancel handshake.
        if connection is not None:
            cast(Terminable, connection.driver_connection).terminate()
