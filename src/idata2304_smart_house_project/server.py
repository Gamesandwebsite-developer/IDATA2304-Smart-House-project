
import asyncio
import struct
from typing import Any, Dict, Optional

from .api import Command, DeviceType, Packet, split_address
from .sensor_node import SensorActuatorNode
from .access_control import AccessControlManager


MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MB


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
        """Receive packets and handle connection or messaging errors."""

        addr = writer.get_extra_info("peername")
        print(f"[SERVER] Client connected: {addr}")

        try:
            while True:
                # Read the four-byte message length.
                header = await reader.readexactly(4)
                msg_length = struct.unpack("!I", header)[0]

                # Reject empty or oversized messages.
                if not 0 < msg_length <= MAX_MESSAGE_SIZE:
                    response = self._error_response(
                        "Invalid message size"
                    )

                    writer.write(
                        struct.pack("!I", len(response)) + response
                    )
                    await writer.drain()

                    # Close the connection because the remaining
                    # message body may be unread.
                    break

                # Read the complete message.
                raw_bytes = await reader.readexactly(msg_length)

                # Decode, validate and process the request.
                response = self.route_message(raw_bytes)

                # Send the response with its four-byte length prefix.
                writer.write(
                    struct.pack("!I", len(response)) + response
                )
                await writer.drain()

        except asyncio.IncompleteReadError:
            print(f"[SERVER] Client disconnected: {addr}")

        except (
            ConnectionResetError,
            BrokenPipeError,
            OSError
        ) as error:
            print(f"[SERVER] Connection error: {error}")

        finally:
            # Always close the client's connection.
            writer.close()

            try:
                await writer.wait_closed()
            except OSError:
                pass

    def route_message(self, raw_bytes: bytes) -> bytes:
        """Validate and route incoming protocol messages."""

        # Handle invalid JSON and malformed packets.
        try:
            packet = Packet.decode(raw_bytes)

        except (
            ValueError,
            TypeError,
            KeyError,
            UnicodeDecodeError
        ):
            return self._error_response("Invalid packet format")

        # Every request must have a dictionary payload.
        if not isinstance(packet.payload, dict):
            return self._error_response(
                "Missing or invalid payload"
            )

        payload = packet.payload
        command = payload.get("command")

        # Check that the packet contains a valid command field.
        if not isinstance(command, str) or not command:
            return self._error_response(
                "Missing or invalid command"
            )

        # Resolve the target node and component.
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
            except ValueError as error:
                return self._error_response(str(error))

        # Check whether the control panel has permission.
        access_level = payload.get("access_level", "guest")

        if not isinstance(access_level, str):
            return self._error_response(
                "Invalid access level"
            )

        actuator = (
            component
            if command == Command.WRITE and component
            else payload.get("actuator", "")
        )

        if not isinstance(actuator, str):
            return self._error_response(
                "Invalid actuator name"
            )

        if not AccessControlManager.is_authorized(
            access_level, command, actuator
        ):
            return self._error_response(
                f"Access denied: role '{access_level}' "
                f"cannot perform '{command}' on '{actuator}'."
            )

        # LIST_NODES: Return all registered sensor-actuator nodes.
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

        # Commands other than LIST_NODES need a valid node.
        if not isinstance(target_id, str):
            return self._error_response(
                "Missing or invalid target node ID"
            )

        if target_id not in self.nodes:
            return self._error_response(
                f"Target node '{target_id}' not found"
            )

        target_node = self.nodes[target_id]

        # READ: Retrieve a sensor reading or actuator status.
        if command == Command.READ:
            resource = (
                component
                if component is not None
                else payload.get("resource", "")
            )

            if not isinstance(resource, str):
                return self._error_response(
                    "Invalid resource name"
                )

            if resource in target_node.sensors:
                value = target_node.sensors[resource]

            elif resource in target_node.actuators:
                value = target_node.actuators[resource]

            else:
                return self._error_response(
                    f"Unknown resource '{resource}'"
                )

            return self._success_response(
                payload={
                    "status": "success",
                    "resource": resource,
                    "value": value
                },
                device_type=target_node.device_type
            )

        # WRITE: Change the state of a specific actuator.
        elif command == Command.WRITE:
            actuator = (
                component
                if component is not None
                else payload.get("actuator", "")
            )

            if not isinstance(actuator, str):
                return self._error_response(
                    "Invalid actuator name"
                )

            # Keep the original type of the value.
            # For example, a thermostat expects a number.
            state = payload.get("state")

            # The node validates the value using device_types.json.
            success = target_node.execute_command(
                actuator, state
            )

            if not success:
                return self._error_response(
                    f"Invalid actuator or value for '{actuator}'"
                )

            return self._success_response(
                payload={
                    "status": "success",
                    "actuator": actuator,
                    "new_state": target_node.actuators.get(actuator),
                },
                device_type=target_node.device_type
            )

        # UPDATE_SENSOR: Update a simulated sensor reading.
        elif command == Command.UPDATE_SENSOR:
            sensor_name = (
                component
                if component is not None
                else payload.get("sensor", "")
            )

            if not isinstance(sensor_name, str):
                return self._error_response(
                    "Invalid sensor name"
                )

            value = payload.get("value")

            # Check that the sensor exists and the value is valid.
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

        # Reject commands that are not supported.
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
        payload: dict[str, Any],
        device_type: DeviceType = DeviceType.SERVER
    ) -> bytes:
        """Create a successful response packet."""

        return Packet(
            device_id="server",
            device_type=device_type,
            payload=payload,
        ).encode()
