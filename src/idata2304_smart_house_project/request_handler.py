
from typing import Any, Dict

from .api import Command, DeviceType, Packet, split_address
from .sensor_node import SensorActuatorNode
from .access_control import AccessControlManager


class RequestHandler:
    """Validate and route requests to simulated sensor nodes."""

    def __init__(
        self,
        nodes: Dict[str, SensorActuatorNode]
    ) -> None:
        self.nodes = nodes

    def handle(self, raw_bytes: bytes) -> bytes:
        """Decode a request and return an encoded response."""

        try:
            packet = Packet.decode(raw_bytes)
        except (ValueError, TypeError, KeyError, UnicodeDecodeError):
            return self._error_response("Invalid packet format")

        if not isinstance(packet.payload, dict):
            return self._error_response("Missing or invalid payload")

        payload = packet.payload
        command = payload.get("command")

        if not isinstance(command, str) or not command:
            return self._error_response("Missing or invalid command")

        target_id = payload.get("target_node_id")
        component = None

        # Resolve hierarchical device addresses.
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

        # Check access permissions.
        access_level = payload.get("access_level", "guest")

        if not isinstance(access_level, str):
            return self._error_response("Invalid access level")

        actuator = (
            component
            if command == Command.WRITE and component
            else payload.get("actuator", "")
        )

        if not isinstance(actuator, str):
            return self._error_response("Invalid actuator name")

        if not AccessControlManager.is_authorized(
            access_level, command, actuator
        ):
            return self._error_response(
                f"Access denied: role '{access_level}' "
                f"cannot perform '{command}' on '{actuator}'."
            )

        # LIST_NODES: Return registered nodes.
        if command == Command.LIST_NODES:
            nodes_info = {
                node_id: {
                    "device_type": node.device_type.name,
                    "sensors": list(node.sensors.keys()),
                    "actuators": list(node.actuators.keys()),
                }
                for node_id, node in self.nodes.items()
            }

            return self._success_response({
                "status": "success",
                "nodes": nodes_info
            })

        # Other commands require a valid node.
        if not isinstance(target_id, str):
            return self._error_response(
                "Missing or invalid target node ID"
            )

        if target_id not in self.nodes:
            return self._error_response(
                f"Target node '{target_id}' not found"
            )

        node = self.nodes[target_id]

        # READ: Get a sensor reading or actuator state.
        if command == Command.READ:
            resource = (
                component
                if component is not None
                else payload.get("resource", "")
            )

            if not isinstance(resource, str):
                return self._error_response("Invalid resource name")

            if resource in node.sensors:
                value = node.sensors[resource]
            elif resource in node.actuators:
                value = node.actuators[resource]
            else:
                return self._error_response(
                    f"Unknown resource '{resource}'"
                )

            return self._success_response(
                {
                    "status": "success",
                    "resource": resource,
                    "value": value
                },
                device_type=node.device_type
            )

        # WRITE: Change an actuator state.
        elif command == Command.WRITE:
            actuator = (
                component
                if component is not None
                else payload.get("actuator", "")
            )

            if not isinstance(actuator, str):
                return self._error_response("Invalid actuator name")

            state = payload.get("state")

            if not node.execute_command(actuator, state):
                return self._error_response(
                    f"Invalid actuator or value for '{actuator}'"
                )

            return self._success_response(
                {
                    "status": "success",
                    "actuator": actuator,
                    "new_state": node.actuators.get(actuator)
                },
                device_type=node.device_type
            )

        # UPDATE_SENSOR: Update a simulated sensor reading.
        elif command == Command.UPDATE_SENSOR:
            sensor = (
                component
                if component is not None
                else payload.get("sensor", "")
            )

            if not isinstance(sensor, str):
                return self._error_response("Invalid sensor name")

            value = payload.get("value")

            if not node.update_sensor(sensor, value):
                return self._error_response(
                    f"Invalid sensor or value for '{sensor}'"
                )

            return self._success_response({
                "status": "success",
                "target_id": target_id,
                "sensor": sensor,
                "new_value": node.sensors.get(sensor)
            })

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
            }
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
            payload=payload
        ).encode()
