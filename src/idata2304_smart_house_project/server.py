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
                payload={"status": "error", "message": "Missing payload"},
            )
            return res.encode()

        action = packet.payload.get("action")

         #Action: LIST_NODES (Does not target a single node)
        if action == "LIST_NODES":
            nodes_info = {
                node_id: {
                    "device_type": node.device_type.name,
                    "sensors": list(node.sensors.keys()),
                    "actuators": list(node.actuators.keys()),
                }
                for node_id, node in self.nodes.items()
            }
            res = Packet(
                device_id="server",
                device_type=DeviceType.SERVER,
                payload={"status": "success", "nodes": nodes_info},
            )
            return res.encode()

        #For READ, WRITE, and UPDATE_SENSOR, validate target_id presence
        target_id = packet.payload.get("target_id")

        if target_id not in self.nodes:
            res = Packet(
                device_id="server",
                device_type=DeviceType.SERVER,
                payload={"status": "error", "message": f"Target node '{target_id}' not found"},
            )
            return res.encode()

        target_node = self.nodes[target_id]

        # Action: READ
        if action == "READ":
            resource = packet.payload.get("resource")
            val = target_node.sensors.get(resource)
            res = Packet(
                device_id="server",
                device_type=target_node.device_type,
                payload={"status": "success", "resource": resource, "value": val},
            )
            return res.encode()

        # Action: WRITE
        elif action == "WRITE":
            actuator = str(packet.payload.get("actuator", ""))
            state = str(packet.payload.get("state", ""))

            success = target_node.execute_command(actuator, state)
            res = Packet(
                device_id="server",
                device_type=target_node.device_type,
                payload={
                    "status": "success" if success else "failed",
                    "actuator": actuator,
                    "new_state": target_node.actuators.get(actuator),
                },
            )
            return res.encode()

        # Action: UPDATE_SENSOR
        elif action == "UPDATE_SENSOR":
            sensor_name = str(packet.payload.get("sensor", ""))
            value = float(packet.payload.get("value", 0.0))

            target_node.update_sensor(sensor_name, value)

            res = Packet(
                device_id="server",
                device_type=DeviceType.SERVER,
                payload={
                    "status": "success",
                    "target_id": target_id,
                    "sensor": sensor_name,
                    "new_value": target_node.sensors.get(sensor_name),
                },
            )
            return res.encode()

        # If the requested action isn't supported, send back an error
        res = Packet(
            device_id="server",
            device_type=DeviceType.SERVER,
            payload={"status": "error", "message": f"Unknown action '{action}'"},
        )
        return res.encode()