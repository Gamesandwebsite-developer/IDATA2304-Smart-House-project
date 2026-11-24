import asyncio
import struct
from typing import Optional
from .anomaly_detector import AnomalyDetector
from idata2304_smart_house_project.api import MAX_MESSAGE_SIZE, TIMEOUT, Packet
from idata2304_smart_house_project.control_panel import ControlPanel

# The network client handles TCP framing The control panel builds requests
# for the terminal menu which decodes the server s responses through send_request
class AsyncNetworkClient:
    """Manage TCP communication with the Smart Home server."""

    # Initialize the object and prepare it for use
    def __init__(
        self, host: str = "127.0.0.1", port: int = 8081, quiet: bool = False
    ) -> None:
        self.host = host
        self.port = port
        self.quiet = quiet
        # Connecting sets these streams Disconnecting clears them
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    # Perform connect
    async def connect(self) -> None:
        """Connect to the server and handle connection errors."""

        # Run the operation and handle possible errors
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=TIMEOUT
            )

            if not self.quiet:
                print(f"[CLIENT] Connected to server at {self.host}:{self.port}")

        except (OSError, asyncio.TimeoutError) as error:
            raise ConnectionError(f"Could not connect to server: {error}") from error

    # Send packet
    async def send_packet(self, data: bytes) -> bytes:
        """Send a packet and receive the server response."""

        if self.writer is None or self.reader is None:
            raise ConnectionError("Client is not connected")

        if not 0 < len(data) <= MAX_MESSAGE_SIZE:
            raise ValueError("Invalid message size")

        # Run the operation and handle possible errors
        try:
            # TCP delivers a byte stream so prefix each packet with its size
            # The server expects a four byte unsigned integer in network byte order
            length_prefix = struct.pack("!I", len(data))
            self.writer.write(length_prefix + data)

            # Pause if the transport needs time to clear its write buffer
            await asyncio.wait_for(self.writer.drain(), timeout=TIMEOUT)

            # Read and validate the server s length prefix before reading the body
            header = await asyncio.wait_for(self.reader.readexactly(4), timeout=TIMEOUT)

            msg_length = struct.unpack("!I", header)[0]

            if not 0 < msg_length <= MAX_MESSAGE_SIZE:
                raise ConnectionError("Invalid response size")

            # The body can arrive in several chunks so wait for every byte
            return await asyncio.wait_for(
                self.reader.readexactly(msg_length), timeout=TIMEOUT
            )

        except asyncio.IncompleteReadError as error:
            # The peer closed the stream before the full header or body arrived
            raise ConnectionError("Server disconnected unexpectedly") from error

        except (OSError, asyncio.TimeoutError) as error:
            raise ConnectionError(
                f"Communication with server failed: {error}"
            ) from error

    # Perform disconnect
    async def disconnect(self) -> None:
        """Close the connection safely."""

        # Check the condition and choose the matching result
        if self.writer is not None:
            self.writer.close()

            # Run the operation and handle possible errors
            try:
                await self.writer.wait_closed()
            except OSError:
                # Clear the local stream references even if closing the socket fails
                pass

            self.reader = None
            self.writer = None

            if not self.quiet:
                print("[CLIENT] Disconnected from server.")


# Send request
async def send_request(client: AsyncNetworkClient, request: bytes) -> dict:
    """Send an encoded request and return its response payload."""

    response = await client.send_packet(request)
    # Decode the application packet after the network client reads the frame
    packet = Packet.decode(response)

    if not isinstance(packet.payload, dict):
        raise ValueError("Invalid server response")

    return packet.payload


# Read and display sensor
async def read_and_display_sensor(
    client: AsyncNetworkClient, panel: ControlPanel, node_id: str, sensor: str
) -> None:
    """Read a sensor and display anomaly warnings."""

    request = panel.create_read_request(node_id, sensor)
    payload = await send_request(client, request)

    # Check the condition and choose the matching result
    if payload.get("status") != "success":
        print("[ERROR]", payload.get("message", "Read failed"))
        return

    value = payload.get("value")

    print(f"\nNode: {node_id}")
    print(f"Sensor: {sensor}")
    print(f"Value: {value}")

    # Python treats bool as a subclass of int so exclude on off readings explicitly
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        warning = AnomalyDetector().check(sensor, value)

        # Check the condition and choose the matching result
        if warning:
            print(warning)
        else:
            print("Status: Normal")
    else:
        print("Anomaly detection not applicable")


# Perform list nodes
async def list_nodes(client: AsyncNetworkClient, panel: ControlPanel) -> None:
    """Display registered sensor-actuator nodes."""

    request = panel.create_list_nodes_request()
    payload = await send_request(client, request)

    # Check the condition and choose the matching result
    if payload.get("status") != "success":
        print("[ERROR]", payload.get("message", "Request failed"))
        return

    nodes = payload.get("nodes", {})

    # Check the condition and choose the matching result
    if not nodes:
        print("No nodes registered")
        return

    print("\n===== REGISTERED NODES =====")

    # Process each item in the collection
    for node_id, information in nodes.items():
        print(f"\nNode: {node_id}")
        print(f"Type: {information.get('device_type')}")
        print(f"Sensors: {information.get('sensors')}")
        print(f"Actuators: {information.get('actuators')}")


# Write actuator
async def write_actuator(
    client: AsyncNetworkClient,
    panel: ControlPanel,
    node_id: str,
    actuator: str,
    state: str,
) -> None:
    """Send a WRITE command to a specific actuator."""

    request = panel.create_write_request(node_id, actuator, state)

    payload = await send_request(client, request)

    # Check the condition and choose the matching result
    if payload.get("status") != "success":
        print("[ERROR]", payload.get("message", "Write failed"))
        return

    # Show the state confirmed by the server
    print(f"Actuator '{actuator}' updated to " f"{payload.get('new_state')}")


# Start the application
async def main() -> None:
    from .cli import run as run_control_panel

    await run_control_panel()


if __name__ == "__main__":
    asyncio.run(main())
