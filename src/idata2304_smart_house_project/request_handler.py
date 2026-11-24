from collections.abc import Callable

from .access_control import AccessControlManager
from .api import Command, DeviceType, Packet, split_address
from .sensor_node import SensorActuatorNode


# Manage request handler
class RequestHandler:
    """Validate requests and run commands on local simulated nodes."""

    # Initialize the object and prepare it for use
    def __init__(self, nodes: dict[str, SensorActuatorNode]) -> None:
        self.nodes = nodes

    # Handle the incoming request
    def handle(self, raw_bytes: bytes) -> bytes:
        nodes_info = {node_id: node.describe() for node_id, node in self.nodes.items()}
        request = self.prepare(raw_bytes, nodes_info)
        if isinstance(request, bytes):
            return request
        if request["command"] == Command.REGISTER_NODE:
            return self.error_response("Registration requires a central server connection")
        return self.execute(request)

    # Validate and prepare the incoming request
    def prepare(
        self,
        raw_bytes: bytes,
        nodes_info: dict,
        authenticate: Callable[[Packet], str] | None = None,
    ) -> dict | bytes:
        """Check the request and resolve a command's target before routing it."""
        # Run the operation and handle possible errors
        try:
            packet = Packet.decode(raw_bytes)
        except (ValueError, TypeError, KeyError, RecursionError):
            return self.error_response("Invalid packet format")

        if not isinstance(packet.payload, dict):
            return self.error_response("Missing or invalid payload")
        payload = packet.payload
        command = payload.get("command")
        if not isinstance(command, str) or not command:
            return self.error_response("Missing or invalid command")
        if command not in Command:
            return self.error_response(f"Unknown command '{command}'")

        # Run the operation and handle possible errors
        try:
            role = authenticate(packet) if authenticate else payload.get("access_level", "guest")
        except ValueError as error:
            return self.error_response(str(error))
        if not isinstance(role, str):
            return self.error_response("Invalid access level")

        # Check the condition and choose the matching result
        if command in (Command.LIST_NODES, Command.REGISTER_NODE):
            if "address" in payload:
                return self.error_response("Address not allowed for this command")
            if not AccessControlManager.is_authorized(role, command):
                return self.error_response("Access denied")
            if command == Command.LIST_NODES:
                return self.success_response({"nodes": nodes_info})
            return {
                "command": command,
                "node_id": payload.get("node_id"),
                "components": payload.get("components"),
            }

        field = {
            Command.READ: "resource",
            Command.WRITE: "actuator",
            Command.UPDATE_SENSOR: "sensor",
        }[command]
        target_id = payload.get("target_node_id")
        component = payload.get(field)
        # Check the condition and choose the matching result
        if "address" in payload:
            # Run the operation and handle possible errors
            try:
                target_id, component = split_address(payload["address"])
            except ValueError as error:
                return self.error_response(str(error))

        if not isinstance(target_id, str) or not target_id:
            return self.error_response("Missing or invalid target node ID")
        if not isinstance(component, str) or not component:
            return self.error_response(f"Invalid {field} name")
        if target_id not in nodes_info:
            return self.error_response(f"Target node '{target_id}' not found")

        actuator_type = nodes_info[target_id]["actuator_types"].get(component)
        # Check the condition and choose the matching result
        if not AccessControlManager.is_authorized(role, command, component, actuator_type):
            return self.error_response(
                f"Access denied: role '{role}' cannot perform '{command}' on '{component}'."
            )

        request = {"command": command, "target_node_id": target_id, field: component}
        # Check the condition and choose the matching result
        if command == Command.WRITE:
            state = payload.get("state")
            if type(state) not in (int, float, str):
                return self.error_response(f"Invalid actuator or value for '{component}'")
            request["state"] = state
        # Check the condition and choose the matching result
        elif command == Command.UPDATE_SENSOR:
            value = payload.get("value")
            if type(value) not in (int, float):
                return self.error_response(f"Invalid sensor or value for '{component}'")
            request["value"] = value
        return request

    # Execute the prepared request
    def execute(self, request: dict) -> bytes:
        """Apply a validated command to the local node."""
        target_id = request["target_node_id"]
        node = self.nodes[target_id]

        # Check the condition and choose the matching result
        if request["command"] == Command.READ:
            resource = request["resource"]
            # Check the condition and choose the matching result
            if resource in node.sensors:
                value = node.sensors[resource]
            # Check the condition and choose the matching result
            elif resource in node.actuators:
                value = node.actuators[resource]
            else:
                return self.error_response(f"Unknown resource '{resource}'")
            return self.success_response(
                {"resource": resource, "value": value}, node.device_type
            )

        # Check the condition and choose the matching result
        if request["command"] == Command.WRITE:
            actuator = request["actuator"]
            if not node.execute_command(actuator, request["state"]):
                return self.error_response(f"Invalid actuator or value for '{actuator}'")
            return self.success_response(
                {"actuator": actuator, "new_state": node.actuators[actuator]},
                node.device_type,
            )

        sensor = request["sensor"]
        if not node.update_sensor(sensor, request["value"]):
            return self.error_response(f"Invalid sensor or value for '{sensor}'")
        return self.success_response({
            "target_id": target_id,
            "sensor": sensor,
            "new_value": node.sensors[sensor],
        })

    # Perform error response
    @staticmethod
    def error_response(message: str) -> bytes:
        return Packet(
            device_id="server",
            device_type=DeviceType.SERVER,
            payload={"status": "error", "message": message},
        ).encode()

    # Perform success response
    @staticmethod
    def success_response(
        payload: dict, device_type: DeviceType = DeviceType.SERVER
    ) -> bytes:
        return Packet(
            device_id="server",
            device_type=device_type,
            payload={"status": "success", **payload},
        ).encode()
