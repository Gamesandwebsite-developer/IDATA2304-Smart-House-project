import pytest
import asyncio
from idata2304_smart_house_project.client import AsyncNetworkClient

@pytest.mark.asyncio
async def test_client_connection_error_handling():
    client = AsyncNetworkClient(host="127.0.0.1", port=19999) # Non-existent port
    with pytest.raises(ConnectionRefusedError):
        await client.connect()

def test_client_initialization():
    client = AsyncNetworkClient(host="127.0.0.1", port=8081)
    assert client.host == "127.0.0.1"
    assert client.port == 8081
    assert client.reader is None
    assert client.writer is None