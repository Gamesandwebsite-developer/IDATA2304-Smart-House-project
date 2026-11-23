from typing import Any
from .api import Command, DeviceType, supports_command, validate_device_value


class SensorActuatorNode:
    # A node holds the current values and types of its simulated components.
    def __init__(self, node_id: str, device_type: DeviceType) -> None:
        self.node_id = node_id
        self.device_type = device_type
        self.sensors: dict[str, float] = {}
        self.actuators: dict[str, Any] = {}
        # Component types can differ from the node's type and determine validation.
        self.sensor_types: dict[str, DeviceType] = {}
        self.actuator_types: dict[str, DeviceType] = {}
        self._initialize_hardware()

    def add_sensor(self, name: str, device_type: DeviceType, value: float) -> None:
        # Validate the starting reading before adding the sensor to the node.
        if not supports_command(device_type, Command.READ) or not validate_device_value(device_type, value):
            raise ValueError(f"Invalid sensor definition/value: {name}")
        self.sensors[name] = value
        self.sensor_types[name] = device_type

    def add_actuator(self, name: str, device_type: DeviceType, state: Any) -> None:
        # Check write support and the starting state before adding the actuator.
        if not supports_command(device_type, Command.WRITE) or not validate_device_value(device_type, state):
            raise ValueError(f"Invalid actuator definition/value: {name}")
        self.actuators[name] = state
        self.actuator_types[name] = device_type

    def _initialize_hardware(self) -> None:
        # Populate the built-in components for the supported default node types.
        if self.device_type == DeviceType.TEMPERATURE_SENSOR:
            self.add_sensor("temperature", DeviceType.TEMPERATURE_SENSOR, 20.0)
        elif self.device_type == DeviceType.DOOR_LOCK:
            self.add_actuator("door_lock", DeviceType.DOOR_LOCK, "LOCKED")
        elif self.device_type == DeviceType.IRRIGATOR:
            self.add_actuator("irrigator_valve", DeviceType.IRRIGATOR, "OFF")

    def update_sensor(self, sensor_name: str, value: Any) -> bool:
        """Update a sensor if it exists and the new value is valid."""

        device_type = self.sensor_types.get(sensor_name)

        # Check that the sensor exists.
        if device_type is None:
            return False

        # Check the value against the rules in device_types.json.
        if not validate_device_value(device_type, value):
            return False

        # Store the new reading.
        self.sensors[sensor_name] = value
        return True

    def execute_command(self, actuator_name: str, state: Any) -> bool:
        # Apply a state change only after validating the actuator and its new state.
        device_type = self.actuator_types.get(actuator_name)
        if (device_type is None
                or not supports_command(device_type, Command.WRITE)
                or not validate_device_value(device_type, state)):
            return False
        self.actuators[actuator_name] = state
        return True
