import asyncio
import struct
from typing import Dict, Optional

from .api import Command, DeviceType, Packet, split_address
from .sensor_node import SensorActuatorNode
from .access_control import AccessControlManager


# Central request router.
# Simulated sensor nodes are stored as local objects.
class IntermediateServer:
    """Accept TCP requests and route commands to simulated nodes."""
    def __init__(
        self, host: str = "127.0.0.1", port: int = 8081
    ) -> None:
        self.host = host
        self.port = port
        self.nodes: Dict[str, SensorActuatorNode] = {}
        self.clients: Dict[str, str] = {}
        self.server: Optional[asyncio.Server] = None

   
    def register_node(self, node: SensorActuatorNode) -> None: 
        """Store a simulated node under its unique node ID."""
        self.nodes[node.node_id] = node
        
    def register_client(self, user_id: str) -> None:
        """Register a control-panel identity."""
        self.clients[user_id] = user_id

    async def start(self) -> None:
        """Start the TCP server."""

        self.server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port
        )

        print(f"[SERVER] Listening on {self.host}:{self.port}...")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self) -> None:
        """Stop the TCP server."""

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("[SERVER] Stopped.")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Receive requests and return responses over TCP."""

        addr = writer.get_extra_info("peername")
        print(f"[SERVER] Client connected: {addr}")

        try:
            while True:
                # Read the four-byte message length.
                header = await reader.readexactly(4)
                msg_length = struct.unpack("!I", header)[0]

                # Read the complete packet.
                raw_bytes = await reader.readexactly(msg_length)

                # Process the packet.
                response_bytes = self.route_message(raw_bytes)

                # Send the response with its length prefix.
                response_length = struct.pack(
                    "!I", len(response_bytes)
                )

                writer.write(response_length + response_bytes)
                await writer.drain()

        except (asyncio.IncompleteReadError, ConnectionResetError):
            print(f"[SERVER] Client disconnected: {addr}")

        finally:
            writer.close()
            await writer.wait_closed()

    def route_message(self, raw_bytes: bytes) -> bytes:
        """Decode a request, check permissions and return a response."""

        packet = Packet.decode(raw_bytes)

        if not packet.payload:
            return self._error_response("Missing payload")

        payload = packet.payload
        command = payload.get("command") or ""

        # Resolve a hierarchical address, if provided.
        # This identifies both the node and its component.
        target_id = payload.get("target_node_id")
        component = None

        if "address" in payload:
            if command not in (
                Command.READ,
                Command.WRITE,
                Command.UPDATE_SENSOR
            ):
                return self._error_response(
                    "Address not allowed for this command"
                )

            try:
                target_id, component = split_address(
                    payload["address"]
                )
            except ValueError as exc:
                return self._error_response(str(exc))

        # Check whether the user is allowed to perform the command.
        access_level = payload.get("access_level", "guest")

        actuator = (
            component
            if command == Command.WRITE and component
            else payload.get("actuator", "")
        )

        if not AccessControlManager.is_authorized(
            access_level, command, actuator
        ):
            return self._error_response(
                f"Access denied: role '{access_level}' "
                f"cannot perform '{command}' on '{actuator}'."
            )

        # Return all registered nodes.
        if command == Command.LIST_NODES:
            nodes_info = {
                node_id: {
                    "device_type": node.device_type.name,
                    "sensors": list(node.sensors.keys()),
                    "actuators": list(node.actuators.keys()),
                }
                for node_id, node in self.nodes.items()
            }

            return self._success_response(
                payload={
                    "status": "success",
                    "nodes": nodes_info
                }
            )

        # All remaining commands require a valid target node.
        if target_id not in self.nodes:
            return self._error_response(
                f"Target node '{target_id}' not found"
            )

        target_node = self.nodes[target_id]

        # READ: Retrieve a sensor value or actuator state.
        if command == Command.READ:
            resource = (
                component
                if component is not None
                else str(payload.get("resource", ""))
            )

            if resource in target_node.sensors:
                val = target_node.sensors[resource]

            elif resource in target_node.actuators:
                val = target_node.actuators[resource]

            else:
                return self._error_response(
                    f"Unknown resource '{resource}'"
                )

            return self._success_response(
                payload={
                    "status": "success",
                    "resource": resource,
                    "value": val
                },
                device_type=target_node.device_type
            )

        # WRITE: Change a specific actuator state.
        elif command == Command.WRITE:
            actuator = (
                component
                if component is not None
                else str(payload.get("actuator", ""))
            )

            # Keep numeric values numeric for devices like thermostats.
            state = packet.payload.get("state")

            # The sensor node validates the value using device_types.json.
            success = target_node.execute_command(
                actuator, state
            )

            if not success:
                return self._error_response(
                    f"Invalid actuator or value for '{actuator}'"
                )

            return self._success_response(
                payload={
                    "status": "success" if success else "failed",
                    "actuator": actuator,
                    "new_state": target_node.actuators.get(actuator),
                },
                device_type=target_node.device_type
            )

        # UPDATE_SENSOR: Update a simulated sensor value.
        elif command == Command.UPDATE_SENSOR:
            sensor_name = (
                component
                if component is not None
                else str(payload.get("sensor", ""))
            )

            value = packet.payload.get("value")

            if not target_node.update_sensor(
                sensor_name, value
            ):
                return self._error_response(
                    f"Invalid sensor or value for '{sensor_name}'"
                )

            return self._success_response(
                payload={
                    "status": "success",
                    "target_id": target_id,
                    "sensor": sensor_name,
                    "new_value": target_node.sensors.get(
                        sensor_name
                    ),
                }
            )

        return self._error_response(
            f"Unknown command '{command}'"
        )

    def _error_response(self, message: str) -> bytes:
        """Create an error response packet."""

        return Packet(
            device_id="server",
            device_type=DeviceType.SERVER,
            payload={
                "status": "error",
                "message": message
            },
        ).encode()

    def _success_response(
        self,
        payload: dict,
        device_type: DeviceType = DeviceType.SERVER
    ) -> bytes:
        """Create a successful response packet."""

        return Packet(
            device_id="server",
            device_type=device_type,
            payload=payload,
        ).encode()