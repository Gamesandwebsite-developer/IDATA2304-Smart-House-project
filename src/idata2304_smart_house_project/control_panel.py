from .api import DeviceType, Packet

class ControlPanel:
    def __init__(
        self,
        user_id: str,
        access_level: str,
        device_type: DeviceType = DeviceType.CONTROL_PANEL,
    ) -> None:
        
        self.user_id = user_id
        self.access_level = access_level
        self.device_type = DeviceType(device_type)

    def create_read_request(self, target_node_id: str, resource: str) -> bytes:
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "action": "READ",
                "target_node_id": target_node_id,
                "resource": resource,
                "access_level": self.access_level,
            },
        )
        return packet.encode()

    def create_write_request(
        self, target_node_id: str, actuator: str, state: str
    ) -> bytes:
    
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "action": "WRITE",
                "target_node_id": target_node_id,
                "actuator": actuator,
                "state": state,
                "access_level": self.access_level,
            },
        )
        return packet.encode()

    def create_list_nodes_request(self) -> bytes:
        
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "action": "LIST_NODES",
                "access_level": self.access_level,
            },
        )
        return packet.encode()

    def create_sensor_update_request(
        self, target_node_id: str, sensor: str, value: float
    ) -> bytes:
    
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "action": "UPDATE_SENSOR",
                "target_node_id": target_node_id,
                "sensor": sensor,
                "value": value,
                "access_level": self.access_level,
            },
        )
        return packet.encode()