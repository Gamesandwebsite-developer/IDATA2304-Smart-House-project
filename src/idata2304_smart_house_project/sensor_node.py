import random
from typing import Any
from .api import Command, DEVICE_DEFINITIONS, DeviceType, supports_command, validate_device_value


# Manage sensor actuator node
class SensorActuatorNode:
    # A node holds the current values and types of its simulated components
    def __init__(self, node_id: str, device_type: DeviceType) -> None:
        self.node_id = node_id
        self.device_type = device_type
        self.sensors: dict[str, float] = {}
        self.actuators: dict[str, Any] = {}
        # Component types can differ from the node s type and determine validation
        self.sensor_types: dict[str, DeviceType] = {}
        self.actuator_types: dict[str, DeviceType] = {}
        self.manual_readings: set[str] = set()
        self._initialize_hardware()

    # Perform add sensor
    def add_sensor(self, name: str, device_type: DeviceType, value: float) -> None:
        # Validate the starting reading before adding the sensor to the node
        if (not 0 <= device_type < 0x100
                or not supports_command(device_type, Command.READ)
                or not validate_device_value(device_type, value)):
            raise ValueError(f"Invalid sensor definition/value: {name}")
        self.sensors[name] = value
        self.sensor_types[name] = device_type
        self.manual_readings.discard(name)

    # Perform add actuator
    def add_actuator(self, name: str, device_type: DeviceType, state: Any) -> None:
        # Check write support and the starting state before adding the actuator
        if (not 0x100 <= device_type < 0x200
                or not supports_command(device_type, Command.WRITE)
                or not validate_device_value(device_type, state)):
            raise ValueError(f"Invalid actuator definition/value: {name}")
        self.actuators[name] = state
        self.actuator_types[name] = device_type

    # Perform initialize hardware
    def _initialize_hardware(self) -> None:
        # Populate the built in components for the supported default node types
        if self.device_type == DeviceType.TEMPERATURE_SENSOR:
            self.add_sensor("temperature", DeviceType.TEMPERATURE_SENSOR, 20.0)
        # Check the condition and choose the matching result
        elif self.device_type == DeviceType.DOOR_LOCK:
            self.add_actuator("door_lock", DeviceType.DOOR_LOCK, "LOCKED")
        elif self.device_type == DeviceType.IRRIGATOR:
            self.add_actuator("irrigator_valve", DeviceType.IRRIGATOR, "OFF")

    # Perform update sensor
    def update_sensor(self, sensor_name: str, value: Any) -> bool:
        """Update a sensor if it exists and the new value is valid."""

        device_type = self.sensor_types.get(sensor_name)

        # Check that the sensor exists
        if device_type is None:
            return False

        # Check the value against the rules in device_types json
        if not validate_device_value(device_type, value):
            return False

        # Store the new reading
        self.sensors[sensor_name] = value
        self.manual_readings.add(sensor_name)
        return True

    # Perform generate readings
    def generate_readings(self) -> None:
        """Refresh simulated readings while preserving manual overrides."""
        ranges = {
            DeviceType.TEMPERATURE_SENSOR: (18.0, 25.0),
            DeviceType.HUMIDITY_SENSOR: (35.0, 65.0),
            DeviceType.LIGHT_SENSOR: (100.0, 800.0),
        }
        # Process each item in the collection
        for name, device_type in self.sensor_types.items():
            if name in self.manual_readings:
                continue
            # Check the condition and choose the matching result
            if device_type == DeviceType.MOTION_SENSOR:
                self.sensors[name] = float(random.randrange(2))
            else:
                bounds = DEVICE_DEFINITIONS[device_type.name]["value_range"]
                low, high = ranges.get(device_type, bounds)
                low, high = max(low, bounds[0]), min(high, bounds[1])
                if low > high:
                    low, high = bounds
                value = random.uniform(low, high)
                if device_type in ranges:
                    value = round(value, 1)
                self.sensors[name] = max(low, min(high, value))

    # Perform describe
    def describe(self) -> dict:
        """List the components and their device types for discovery."""
        return {
            "device_type": self.device_type.name,
            "sensors": list(self.sensors),
            "actuators": list(self.actuators),
            "sensor_types": {name: kind.name for name, kind in self.sensor_types.items()},
            "actuator_types": {name: kind.name for name, kind in self.actuator_types.items()},
        }

    # Perform execute command
    def execute_command(self, actuator_name: str, state: Any) -> bool:
        # Apply a state change only after validating the actuator and its new state
        device_type = self.actuator_types.get(actuator_name)
        # Check the condition and choose the matching result
        if (device_type is None
                or not supports_command(device_type, Command.WRITE)
                or not validate_device_value(device_type, state)):
            return False
        self.actuators[actuator_name] = state
        return True
