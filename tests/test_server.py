from idata2304_smart_house_project.api import Packet, DeviceType, Command
from idata2304_smart_house_project.server import IntermediateServer

def test_server_route_message():
    # Create server
    server = IntermediateServer()

    # Create a valid protocol request
    packet = Packet(
        device_id="guest_user",
        device_type=DeviceType.CONTROL_PANEL,
        payload={
            "command": Command.LIST_NODES.value,
            "access_level": "guest"
        }
    )

    # Send packet directly to server and decode response
    response = Packet.decode(server.route_message(packet.encode()))
    print("Server response:", response.payload)
    assert response.payload is not None
    assert response.payload["status"] == "success"
