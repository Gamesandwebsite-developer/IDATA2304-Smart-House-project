import asyncio
import struct
from typing import Dict, Optional
from .api import DeviceType, Packet
from .sensor_node import SensorActuatorNode
from .access_control import AccessControlManager

#Central message broker router responsible for handling network node registry and packet routing.
class IntermediateServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8081) -> None:
        self.host = host
        self.port = port
        self.nodes: Dict[str, SensorActuatorNode] = {}
        self.clients: Dict[str, str] = {}  
        self.server: Optional[asyncio.Server] = None

    def register_node(self, node: SensorActuatorNode) -> None:
        self.nodes[node.node_id] = node

    # Registers a client user identity.
    def register_client(self, user_id: str) -> None:
        self.clients[user_id] = user_id

    # Starts the TCP server
    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._handle_connection, self.host, self.port
        )
        print(f"[SERVER] Listening on {self.host}:{self.port}...")
        async with self.server:
            await self.server.serve_forever()

    # Shuts down the TCP server.
    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("[SERVER] Stopped.")

    #Handles framed socket communication for a connected client.
    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        
        addr = writer.get_extra_info("peername")
        print(f"[SERVER] Client connected: {addr}")

        try:
            while True:
                header = await reader.readexactly(4)
                msg_length = struct.unpack("!I", header)[0]
                raw_bytes = await reader.readexactly(msg_length)

                response_bytes = self.route_message(raw_bytes)

                # Send length header + payload back to client
                response_length = struct.pack("!I", len(response_bytes))
                writer.write(response_length + response_bytes)
                await writer.drain()

        except (asyncio.IncompleteReadError, ConnectionResetError):
            print(f"[SERVER] Client disconnected: {addr}")
        finally:
            writer.close()
            await writer.wait_closed()
    

    def route_message(self, raw_bytes: bytes) -> bytes:
        packet = Packet.decode(raw_bytes)

        if not packet.payload:
            return self._error_response("Missing payload")
        
        payload = packet.payload
        action = payload.get("action") or ""

        access_level = payload.get("access_level", "guest")
        actuator = payload.get("actuator", "")

        if not AccessControlManager.is_authorized(access_level, action, actuator):
            return self._error_response(
                f"Access denied: role '{access_level}' cannot perform '{action}' on '{actuator}'."
            )
        # Action: LIST_NODES 
        if action == "LIST_NODES":
            nodes_info = {
                node_id: {
                    "device_type": node.device_type.name,
                    "sensors": list(node.sensors.keys()),
                    "actuators": list(node.actuators.keys()),
                }
                for node_id, node in self.nodes.items()
            }
            return self._success_response(payload={"status": "success", "nodes": nodes_info})

        # Target validation for node-specific actions (READ, WRITE, UPDATE_SENSOR)
        target_node_id = packet.payload.get("target_node_id")
        if target_node_id not in self.nodes:
            return self._error_response(f"Target node '{target_node_id}' not found")

        target_node = self.nodes[target_node_id]

        # Action routing
        if action == "READ":
            resource = str(packet.payload.get("resource", ""))
            val = target_node.sensors.get(resource)
            return self._success_response(
                payload={"status": "success", "resource": resource, "value": val},
                device_type=target_node.device_type,
            )

        elif action == "WRITE":
            actuator = str(packet.payload.get("actuator", ""))
            state = str(packet.payload.get("state", ""))
            success = target_node.execute_command(actuator, state)
            return self._success_response(
                payload={
                    "status": "success" if success else "failed",
                    "actuator": actuator,
                    "new_state": target_node.actuators.get(actuator),
                },
                device_type=target_node.device_type,
            )

        elif action == "UPDATE_SENSOR":
            sensor_name = str(packet.payload.get("sensor", ""))
            value = float(packet.payload.get("value", 0.0))
            target_node.update_sensor(sensor_name, value)
            return self._success_response(
                payload={
                    "status": "success",
                    "target_node_id": target_node_id,
                    "sensor": sensor_name,
                    "new_value": target_node.sensors.get(sensor_name),
                }
            )

        return self._error_response(f"Unknown action '{action}'")

    def _error_response(self, message: str) -> bytes:
        return Packet(
            device_id="server",
            device_type=DeviceType.SERVER,
            payload={"status": "error", "message": message},
        ).encode()
    
    def _success_response(
        self, payload: dict, device_type: DeviceType = DeviceType.SERVER
    ) -> bytes:
        return Packet(
            device_id="server",
            device_type=device_type,
            payload=payload,
        ).encode()