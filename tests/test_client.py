import pytest

from idata2304_smart_house_project.client import AsyncNetworkClient


@pytest.mark.asyncio
async def test_client_connection_error_handling():
    """Check that the client handles a failed server connection."""

    client = AsyncNetworkClient(
        host="127.0.0.1",
        port=19999
    )

    with pytest.raises(ConnectionError):
        await client.connect()


def test_client_initialization():
    """Check that client settings are initialized correctly."""

    client = AsyncNetworkClient(
        host="127.0.0.1",
        port=8081
    )

    assert client.host == "127.0.0.1"
    assert client.port == 8081
    assert client.reader is None
    assert client.writer is None