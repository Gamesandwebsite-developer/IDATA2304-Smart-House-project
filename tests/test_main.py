import pytest
from idata2304_smart_house_project import (
    ControlPanel,
    DeviceType,
    IntermediateServer,
    Packet,
    SensorActuatorNode,
)


def test_packet_decode_enum_preservation():
    packet = Packet(device_id="sensor_1", device_type=DeviceType.TEMPERATURE_SENSOR)
    encoded = packet.encode()
    decoded = Packet.decode(encoded)
    assert isinstance(decoded.device_type, DeviceType)
    assert decoded.device_type == DeviceType.TEMPERATURE_SENSOR


def test_sensor_update():
    node = SensorActuatorNode("temp_01", DeviceType.TEMPERATURE_SENSOR)
    node.update_sensor("temperature", 24.5)
    assert node.sensors["temperature"] == 24.5


def test_read_routing():
    server = IntermediateServer()
    node = SensorActuatorNode("temp_01", DeviceType.TEMPERATURE_SENSOR)
    node.update_sensor("temperature", 19.8)
    server.register_node(node)

    panel = ControlPanel("user_1", "admin")
    req = panel.create_read_request("temp_01", "temperature")

    res_bytes = server.route_message(req)
    res_packet = Packet.decode(res_bytes)
    
    print("Server response:", res_packet.payload)

    assert res_packet.payload is not None
    assert res_packet.payload["status"] == "success", res_packet.payload
    assert res_packet.payload["value"] == 19.8


def test_write_routing():
    server = IntermediateServer()
    node = SensorActuatorNode("irr_01", DeviceType.IRRIGATOR)
    server.register_node(node)

    panel = ControlPanel("user_1", "admin")
    req = panel.create_write_request("irr_01", "irrigator_valve", "ON")

    res_bytes = server.route_message(req)
    res_packet = Packet.decode(res_bytes)


    assert res_packet.payload is not None
    assert res_packet.payload["status"] == "success", res_packet.payload
    assert node.actuators["irrigator_valve"] == "ON"


def test_list_nodes_routing():
    server = IntermediateServer()
    node_a = SensorActuatorNode("temp_01", DeviceType.TEMPERATURE_SENSOR)
    node_b = SensorActuatorNode("door_01", DeviceType.DOOR_LOCK)
    server.register_node(node_a)
    server.register_node(node_b)

    panel = ControlPanel("user_1", "admin")
    req = panel.create_list_nodes_request()

    res_bytes = server.route_message(req)
    res_packet = Packet.decode(res_bytes)

    assert res_packet.payload is not None
    assert res_packet.payload["status"] == "success", res_packet.payload
    nodes = res_packet.payload["nodes"]
    assert "temp_01" in nodes
    assert "door_01" in nodes


def test_sensor_update_routing():
    server = IntermediateServer()
    node = SensorActuatorNode("temp_01", DeviceType.TEMPERATURE_SENSOR)
    server.register_node(node)

    panel = ControlPanel("user_1", "admin")
    req = panel.create_sensor_update_request("temp_01", "temperature", 25.5)

    res_bytes = server.route_message(req)
    res_packet = Packet.decode(res_bytes)

    assert res_packet.payload is not None
    assert res_packet.payload["status"] == "success", res_packet.payload
    assert res_packet.payload["new_value"] == 25.5
    assert node.sensors["temperature"] == 25.5


def test_guest_permission_restriction():
    server = IntermediateServer()
    node = SensorActuatorNode("door_node", DeviceType.DOOR_LOCK)
    server.register_node(node)

    panel = ControlPanel("guest_1", "guest")

    request = panel.create_write_request(
        "door_node", "door_lock", "UNLOCKED"
    )

    response = Packet.decode(server.route_message(request))

    assert response.payload is not None
    assert response.payload["status"] == "error"