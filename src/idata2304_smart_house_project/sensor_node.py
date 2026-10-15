from .api import DeviceType

class SensorActuatorNode:
    def __init__(self, node_id: str, device_type: DeviceType):
        self.node_id = node_id
        self.device_type = DeviceType(device_type)
        self.sensors = {}
        self.actuators = {}

        # Initialize hardware state based on device capability
        if self.device_type == DeviceType.TEMPERATURE_SENSOR:
            self.sensors["temperature"] = 0.0
        elif self.device_type == DeviceType.LIGHT_SENSOR:
            self.sensors["light_level"] = 0.0
        elif self.device_type == DeviceType.SMOKE_FLAME_DETECTOR:
            self.sensors["smoke_level"] = 0.0
            self.actuators["alarm_siren"] = "OFF"
        elif self.device_type == DeviceType.IRRIGATOR:
            self.actuators["irrigator_valve"] = "OFF"
        elif self.device_type == DeviceType.FAN:
            self.actuators["fan_power"] = "OFF"

    def update_sensor(self, sensor_name: str, value: float) -> None:
        if sensor_name in self.sensors:
            self.sensors[sensor_name] = value

    def execute_command(self, actuator_name: str, state: str) -> bool:
        if actuator_name in self.actuators:
            self.actuators[actuator_name] = state
            return True
        return False

    def get_status(self) -> dict:
        return {
            "node_id": self.node_id,
            "device_type": int(self.device_type),
            "sensors": self.sensors,
            "actuators": self.actuators,
        }