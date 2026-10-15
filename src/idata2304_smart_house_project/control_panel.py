from .api import DeviceType, Packet

class ControlPanel:
    def __init__(self, user_id: str, access_level: str, device_type: DeviceType = DeviceType.CONTROL_PANEL):
        self.user_id = user_id
        self.access_level = access_level
        self.device_type = DeviceType(device_type)

    def create_read_request(self, target_node_id: str, resource: str) -> bytes:
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={"action": "READ", "target_id": target_node_id, "resource": resource}
        )
        return packet.encode()

    def create_write_request(self, target_node_id: str, actuator: str, state: str) -> bytes:
        if self.access_level == "guest" and actuator in ("door_lock", "main_valve"):
            raise PermissionError(f"Access level '{self.access_level}' cannot modify restricted actuator '{actuator}'.")

        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={"action": "WRITE", "target_id": target_node_id, "actuator": actuator, "state": state}
        )
        return packet.encode()