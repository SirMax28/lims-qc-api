import pytest
from core.database import MongoDB
from core.config import settings


@pytest.mark.asyncio
async def test_mongodb_connect_and_disconnect(monkeypatch):
    """Probar conexión simulada a MongoDB."""

    # Fake AsyncIOMotorClient
    class DummyClient:
        def __init__(self, uri):
            self.uri = uri
            self.admin = self
            self.closed = False

        async def command(self, cmd):
            assert cmd == "ping"
            return {"ok": 1}

        def close(self):
            self.closed = True

        def __getitem__(self, name):
            return {"_name": name}

    # parcheamos motor
    monkeypatch.setattr("core.database.AsyncIOMotorClient", DummyClient)

    mdb = MongoDB()
    assert not mdb.is_connected

    await mdb.connect()
    assert mdb.is_connected
    assert mdb.db["_name"] == settings.MONGODB_NAME

    await mdb.disconnect()
    assert not mdb.is_connected
    assert mdb.client.closed
