import pytest
from idata2304_smart_house_project import (
    SensorActuatorNode,
    ControlPanel,
    IntermediateServer,
    DeviceType,
    Packet,
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
    
    # Tell Pylance to guarantee payload is not None before subscripting
    assert res_packet.payload is not None
    assert res_packet.payload["status"] == "success"
    assert res_packet.payload["value"] == 19.8

def test_write_routing():
    server = IntermediateServer()
    node = SensorActuatorNode("irr_01", DeviceType.IRRIGATOR)
    server.register_node(node)

    panel = ControlPanel("user_1", "admin")
    req = panel.create_write_request("irr_01", "irrigator_valve", "ON")

    res_bytes = server.route_message(req)
    res_packet = Packet.decode(res_bytes)

    # Tell Pylance to guarantee payload is not None before subscripting
    assert res_packet.payload is not None
    assert res_packet.payload["status"] == "success"
    assert node.actuators["irrigator_valve"] == "ON"

def test_guest_permission_restriction():
    panel = ControlPanel("guest_1", "guest")
    with pytest.raises(PermissionError):
        panel.create_write_request("door_node", "door_lock", "UNLOCK")