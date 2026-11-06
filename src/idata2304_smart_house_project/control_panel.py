from .api import DeviceType, Packet

class ControlPanel:
    # Creates and stores session data (user identity & permission role)
    def __init__(self, user_id: str, access_level: str, device_type: DeviceType = DeviceType.CONTROL_PANEL):
        self.user_id = user_id
        self.access_level = access_level
        self.device_type = DeviceType(device_type)

    def create_read_request(self, target_node_id: str, resource: str) -> bytes:
        """Creates a packet to request sensor telemetry from a target node."""
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={"action": "READ", "target_id": target_node_id, "resource": resource}
        )
        return packet.encode()

    def create_write_request(self, target_node_id: str, actuator: str, state: str) -> bytes:
        """Creates a packet to change an actuator state, enforcing role-based permissions."""
        if self.access_level == "guest" and actuator in ("door_lock", "main_valve"):
            raise PermissionError(f"Access level '{self.access_level}' cannot modify restricted actuator '{actuator}'.")

        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={"action": "WRITE", "target_id": target_node_id, "actuator": actuator, "state": state}
        )
        return packet.encode()  # <--- Added missing return statement here

    def create_list_nodes_request(self) -> bytes:
        """Creates a request packet to list all connected/registered nodes."""
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={"action": "LIST_NODES"}
        )
        return packet.encode()

    def create_sensor_update_request(self, target_node_id: str, sensor: str, value: float) -> bytes:
        """Creates a request packet to update/simulate a sensor reading on a node."""
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "action": "UPDATE_SENSOR",
                "target_id": target_node_id,
                "sensor": sensor,
                "value": value
            }
        )
        return packet.encode()