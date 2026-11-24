from .api import DeviceType
from .sensor_node import SensorActuatorNode


# Perform valid name
def valid_name(name: str) -> bool:
    return name.replace("_", "").replace("-", "").isalnum()


# Perform valid node id
def valid_node_id(node_id: str) -> bool:
    parts = node_id.split("/")
    return len(parts) in (1, 3) and all(map(valid_name, parts))


# Perform build node
def build_node(node_id: str, components: list) -> SensorActuatorNode:
    """Build a node from the components selected by the control panel."""
    if not isinstance(node_id, str) or not valid_node_id(node_id):
        raise ValueError("Use a node name or level/room/node")
    if not isinstance(components, list) or not components:
        raise ValueError("Add at least one sensor or actuator")

    node = SensorActuatorNode(node_id, DeviceType.SIMULATED_NODE)
    # Process each item in the collection
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("Invalid component")
        name, kind = component.get("name"), component.get("type")
        if not isinstance(name, str) or not valid_name(name):
            raise ValueError("Invalid component name")
        if name in node.sensors or name in node.actuators:
            raise ValueError(f"Duplicate component name: {name}")
        if not isinstance(kind, str) or kind not in DeviceType.__members__:
            raise ValueError(f"Unknown type for '{name}'")
        device_type = DeviceType[kind]
        # Check the condition and choose the matching result
        if device_type < 0x100:
            node.add_sensor(name, device_type, component.get("value"))
        else:
            node.add_actuator(name, device_type, component.get("value"))
    return node


# Create a nodes
def create_nodes() -> dict[str, SensorActuatorNode]:
    """Build the simulated nodes used by the default house."""
    living_room = SensorActuatorNode("temp_node_1", DeviceType.TEMPERATURE_SENSOR)
    living_room.add_sensor("humidity", DeviceType.HUMIDITY_SENSOR, 45.0)
    living_room.add_actuator("fan", DeviceType.FAN, "OFF")
    living_room.add_actuator("thermostat", DeviceType.THERMOSTAT_ACTUATOR, 21.0)

    entrance = SensorActuatorNode("door_lock_1", DeviceType.DOOR_LOCK)
    entrance.add_sensor("light", DeviceType.LIGHT_SENSOR, 350.0)
    entrance.add_sensor("motion", DeviceType.MOTION_SENSOR, 0.0)
    entrance.add_actuator("heater", DeviceType.HEATER, "OFF")

    return {node.node_id: node for node in (living_room, entrance)}
