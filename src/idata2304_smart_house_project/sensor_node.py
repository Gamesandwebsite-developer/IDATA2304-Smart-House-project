from typing import Any, Dict
from .api import DeviceType


class SensorActuatorNode:
    """Represents an edge hardware node holding local sensor telemetry and actuator states."""

    def __init__(self, node_id: str, device_type: DeviceType) -> None:
        self.node_id = node_id
        self.device_type = device_type
        self.sensors: Dict[str, float] = {}
        self.actuators: Dict[str, str] = {}
        
        # Self-initialize default components based on node role
        self._initialize_hardware()

    def _initialize_hardware(self) -> None:
        """Helper method to isolate component initialization and keep __init__ clean."""
        if self.device_type == DeviceType.TEMPERATURE_SENSOR:
            self.sensors["temperature"] = 20.0
        elif self.device_type == DeviceType.DOOR_LOCK:
            self.actuators["door_lock"] = "LOCKED"
        elif self.device_type == DeviceType.IRRIGATOR:
            self.actuators["irrigator_valve"] = "OFF"

    def update_sensor(self, sensor_name: str, value: float) -> None:
        """Updates or registers a live sensor reading."""
        self.sensors[sensor_name] = value

    def execute_command(self, actuator_name: str, state: str) -> bool:
        """Executes a state change command on a target actuator if present on this node."""
        if actuator_name in self.actuators:
            self.actuators[actuator_name] = state
            return True
        return False