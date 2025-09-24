import pytest
from core.database import PostgresDB

@pytest.mark.asyncio
async def test_postgres_connect_and_disconnect(monkeypatch):
    """Probar conexión simulada a Postgres."""

    class DummyConnection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, stmt):
            # Debe recibir un SELECT 1
            assert "1" in str(stmt)
            return True

    class DummyEngine:
        def __init__(self):
            self.disposed = False

        def begin(self):
            return DummyConnection()

        async def dispose(self):
            self.disposed = True

    # Parcheamos create_async_engine para devolver DummyEngine
    monkeypatch.setattr("core.database.create_async_engine", lambda *a, **kw: DummyEngine())

    pg = PostgresDB()
    assert not pg.is_connected

    await pg.connect()
    assert pg.is_connected
    # async_session debería ser un sessionmaker invocable
    assert callable(pg.async_session)

    await pg.disconnect()
    assert not pg.is_connected
    assert pg.engine.disposed
