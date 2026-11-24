from typing import Any
from .api import Command, DeviceType, Packet


# Manage control panel
class ControlPanel:
    """Build protocol requests; network transport is handled by the client."""

    # Initialize the object and prepare it for use
    def __init__(
        self,
        user_id: str,
        access_level: str,
        device_type: DeviceType = DeviceType.CONTROL_PANEL,
    ) -> None:

        # Identity and access level are included in every request
        self.user_id = user_id
        self.access_level = access_level
        self.device_type = DeviceType(device_type)

    # Create a read request
    def create_read_request(
        self, target_node_id: str, resource: str
    ) -> bytes:
        """Ask for a named sensor reading or actuator status."""

        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "command": Command.READ.value,
                "target_node_id": target_node_id,
                "resource": resource,
                "access_level": self.access_level,
            },
        )

        return packet.encode()

    # Create a write request
    def create_write_request(
        self, target_node_id: str, actuator: str, state: Any
    ) -> bytes:
        """Request an actuator state change."""

        # Preserve the original state type because thermostats require numeric values
        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "command": Command.WRITE.value,
                "target_node_id": target_node_id,
                "actuator": actuator,
                "state": state,
                "access_level": self.access_level,
            },
        )

        return packet.encode()

    # Create a list nodes request
    def create_list_nodes_request(self) -> bytes:
        """Request the server's registered nodes."""

        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "command": Command.LIST_NODES.value,
                "access_level": self.access_level,
            },
        )

        return packet.encode()

    # Create a sensor update request
    def create_sensor_update_request(
        self, target_node_id: str, sensor: str, value: float
    ) -> bytes:
        """Create a request to update a simulated sensor reading."""

        packet = Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "command": Command.UPDATE_SENSOR.value,
                "target_node_id": target_node_id,
                "sensor": sensor,
                "value": value,
                "access_level": self.access_level,
            },
        )

        return packet.encode()

    # Create a register node request
    def create_register_node_request(self, node_id: str, components: list[dict]) -> bytes:
        return Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "command": Command.REGISTER_NODE,
                "node_id": node_id,
                "components": components,
                "access_level": self.access_level,
            },
        ).encode()

    # Create a addressed read request
    def create_addressed_read_request(self, address: str) -> bytes:
        """READ one component using its full hierarchical address."""

        from .api import split_address

        # Validate locally while leaving target resolution to the server
        split_address(address)

        return Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "command": Command.READ.value,
                "address": address,
                "access_level": self.access_level,
            },
        ).encode()

    # Create a addressed write request
    def create_addressed_write_request(
        self, address: str, state: Any
    ) -> bytes:
        """WRITE one actuator using its full hierarchical address."""

        from .api import split_address

        # Validate the hierarchical address
        split_address(address)

        return Packet(
            device_id=self.user_id,
            device_type=self.device_type,
            payload={
                "command": Command.WRITE.value,
                "address": address,
                "state": state,
                "access_level": self.access_level,
            },
        ).encode()