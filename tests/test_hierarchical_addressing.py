import pytest

from idata2304_smart_house_project.api import DeviceType, Packet
from idata2304_smart_house_project.control_panel import ControlPanel
from idata2304_smart_house_project.sensor_node import SensorActuatorNode
from idata2304_smart_house_project.server import IntermediateServer


def make_home():
    """Create a simulated home for the tests."""

    server = IntermediateServer()

    node = SensorActuatorNode(
        "level_1/living_room/sensor_node_1",
        DeviceType.TEMPERATURE_SENSOR
    )

    # Two actuators are used to test individual targeting.
    node.add_actuator(
        "light_actuator_1",
        DeviceType.FAN,
        "OFF"
    )

    node.add_actuator(
        "light_actuator_2",
        DeviceType.FAN,
        "OFF"
    )

    server.register_node(node)
    panel = ControlPanel("admin_user", "admin")
    return server, node, panel


def reply(server, message):
    """Send a request and decode the server response."""

    result = Packet.decode(
        server.route_message(message)
    ).payload

    assert result is not None
    return result


def test_addressed_read():
    """Check that a sensor can be read using its full address."""

    server, _, panel = make_home()

    result = reply(
        server,
        panel.create_addressed_read_request(
            "level_1/living_room/sensor_node_1/temperature"
        )
    )

    assert result["status"] == "success"
    assert result["value"] == 20.0


def test_addressed_write_targets_one_actuator():
    """Changing one actuator must not change another."""

    server, node, panel = make_home()

    result = reply(
        server,
        panel.create_addressed_write_request(
            "level_1/living_room/sensor_node_1/light_actuator_1",
            "ON"
        )
    )

    assert result["status"] == "success"
    assert node.actuators["light_actuator_1"] == "ON"
    assert node.actuators["light_actuator_2"] == "OFF"


def test_unknown_address_is_rejected():
    """Invalid or unknown addresses are rejected."""

    server, _, panel = make_home()

    result = reply(
        server,
        panel.create_addressed_write_request(
            "level_1/kitchen/sensor_node_1/light_actuator_1",
            "ON"
        )
    )

    assert result["status"] == "error"

    with pytest.raises(ValueError):
        panel.create_addressed_read_request(
            "living_room/light_actuator_1"
        )


