from typing import Dict
from .api import DeviceType, Packet
from .sensor_node import SensorActuatorNode
from .control_panel import ControlPanel

class IntermediateServer:
    def __init__(self):
        self.nodes: Dict[str, SensorActuatorNode] = {}
        self.clients: Dict[str, ControlPanel] = {}

    def register_node(self, node: SensorActuatorNode) -> None:
        self.nodes[node.node_id] = node

    def register_client(self, client: ControlPanel) -> None:
        self.clients[client.user_id] = client

    def route_message(self, raw_bytes: bytes) -> bytes:
        packet = Packet.decode(raw_bytes)

        if not packet.payload:
            res = Packet(
                device_id="server",
                device_type=DeviceType.SERVER,
                payload={"status": "error", "message": "Missing payload"}
            )
            return res.encode()

        action = packet.payload.get("action")
        target_id = packet.payload.get("target_id")

        if target_id not in self.nodes:
            res = Packet(
                device_id="server",
                device_type=DeviceType.SERVER,
                payload={"status": "error", "message": f"Target node '{target_id}' not found"}
            )
            return res.encode()

        target_node = self.nodes[target_id]

        if action == "READ":
            resource = packet.payload.get("resource")
            val = target_node.sensors.get(resource)
            res = Packet(
                device_id="server",
                device_type=target_node.device_type,
                payload={"status": "success", "resource": resource, "value": val}
            )
            return res.encode()

        elif action == "WRITE":
            # Cast the fetched values to string so they match the target_node method signatures
            actuator = str(packet.payload.get("actuator", ""))
            state = str(packet.payload.get("state", ""))
            
            success = target_node.execute_command(actuator, state)
            res = Packet(
                device_id="server",
                device_type=target_node.device_type,
                payload={
                    "status": "success" if success else "failed",
                    "actuator": actuator,
                    "new_state": target_node.actuators.get(actuator)
                }
            )
            return res.encode()

        res = Packet(
            device_id="server",
            device_type=DeviceType.SERVER,
            payload={"status": "error", "message": f"Unknown action '{action}'"}
        )
        return res.encode()