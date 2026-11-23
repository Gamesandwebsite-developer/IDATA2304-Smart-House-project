"""Tests for messaging errors."""
from idata2304_smart_house_project.api import DeviceType, Packet
from idata2304_smart_house_project.server import IntermediateServer


def test_invalid_json():
    server = IntermediateServer()

    response = Packet.decode(
        server.route_message(b"invalid json")
    )

    assert response.payload is not None
    assert response.payload["status"] == "error"


def test_missing_command():
    server = IntermediateServer()

    request = Packet(
        device_id="user_1",
        device_type=DeviceType.CONTROL_PANEL,
        payload={"access_level": "admin"}
    )

    response = Packet.decode(
        server.route_message(request.encode())
    )

    assert response.payload is not None
    assert response.payload["status"] == "error"