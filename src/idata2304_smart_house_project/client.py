import asyncio
import struct
from typing import Optional
from .api import Packet
from .control_panel import ControlPanel


MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MB
TIMEOUT = 10  # Seconds


class AsyncNetworkClient:
    """Manage TCP communication with the Smart Home server."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8081
    ) -> None:
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        """Connect to the server and handle connection errors."""

        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=TIMEOUT
            )

            print(
                f"[CLIENT] Connected to server "
                f"at {self.host}:{self.port}"
            )

        except (OSError, asyncio.TimeoutError) as error:
            raise ConnectionError(
                f"Could not connect to server: {error}"
            ) from error

    async def send_packet(self, data: bytes) -> bytes:
        """Send a packet and receive the server response."""

        if self.writer is None or self.reader is None:
            raise ConnectionError("Client is not connected")

        if not 0 < len(data) <= MAX_MESSAGE_SIZE:
            raise ValueError("Invalid message size")

        try:
            # Send the four-byte length and packet.
            length_prefix = struct.pack("!I", len(data))
            self.writer.write(length_prefix + data)

            await asyncio.wait_for(
                self.writer.drain(),
                timeout=TIMEOUT
            )

            # Read the four-byte response length.
            header = await asyncio.wait_for(
                self.reader.readexactly(4),
                timeout=TIMEOUT
            )

            msg_length = struct.unpack("!I", header)[0]

            if not 0 < msg_length <= MAX_MESSAGE_SIZE:
                raise ValueError("Invalid response size")

            # Read the complete response.
            return await asyncio.wait_for(
                self.reader.readexactly(msg_length),
                timeout=TIMEOUT
            )

        except asyncio.IncompleteReadError as error:
            raise ConnectionError(
                "Server disconnected unexpectedly"
            ) from error

        except (OSError, asyncio.TimeoutError) as error:
            raise ConnectionError(
                f"Communication with server failed: {error}"
            ) from error

    async def disconnect(self) -> None:
        """Close the connection safely."""

        if self.writer is not None:
            self.writer.close()

            try:
                await self.writer.wait_closed()
            except OSError:
                pass

            self.reader = None
            self.writer = None

            print("[CLIENT] Disconnected from server.")


async def send_request(
    client: AsyncNetworkClient,
    request: bytes
) -> dict:
    """Send an encoded request and return its response payload."""

    response = await client.send_packet(request)
    packet = Packet.decode(response)

    if not isinstance(packet.payload, dict):
        raise ValueError("Invalid server response")

    return packet.payload


async def read_and_display_sensor(
    client: AsyncNetworkClient,
    panel: ControlPanel,
    node_id: str,
    sensor: str
) -> None:
    """Read a sensor and display anomaly warnings."""

    request = panel.create_read_request(node_id, sensor)
    payload = await send_request(client, request)

    if payload.get("status") != "success":
        print("[ERROR]", payload.get("message", "Read failed"))
        return

    value = payload.get("value")

    print(f"\nNode: {node_id}")
    print(f"Sensor: {sensor}")
    print(f"Value: {value}")

    # Only check numeric sensor readings for anomalies.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # warning = panel.check_sensor_anomaly(sensor, value)
        warning = "" #TODO fix this

        if warning:
            print(warning)
        else:
            print("Status: Normal")
    else:
        print("Anomaly detection not applicable")


async def list_nodes(
    client: AsyncNetworkClient,
    panel: ControlPanel
) -> None:
    """Display registered sensor-actuator nodes."""

    request = panel.create_list_nodes_request()
    payload = await send_request(client, request)

    if payload.get("status") != "success":
        print("[ERROR]", payload.get("message", "Request failed"))
        return

    nodes = payload.get("nodes", {})

    if not nodes:
        print("No nodes registered")
        return

    print("\n===== REGISTERED NODES =====")

    for node_id, information in nodes.items():
        print(f"\nNode: {node_id}")
        print(f"Type: {information.get('device_type')}")
        print(f"Sensors: {information.get('sensors')}")
        print(f"Actuators: {information.get('actuators')}")


async def write_actuator(
    client: AsyncNetworkClient,
    panel: ControlPanel,
    node_id: str,
    actuator: str,
    state: str
) -> None:
    """Send a WRITE command to a specific actuator."""

    request = panel.create_write_request(
        node_id, actuator, state
    )

    payload = await send_request(client, request)

    if payload.get("status") != "success":
        print("[ERROR]", payload.get("message", "Write failed"))
        return

    print(
        f"Actuator '{actuator}' updated to "
        f"{payload.get('new_state')}"
    )


async def main() -> None:
    """Run the Smart Home terminal control panel."""

    client = AsyncNetworkClient()
    panel = ControlPanel("admin_user", "admin")

    try:
        await client.connect()

        while True:
            print("\n===== SMART HOME CONTROL PANEL =====")
            print("1. List nodes")
            print("2. Read sensor")
            print("3. Control actuator")
            print("4. Quit")

            choice = (
                await asyncio.to_thread(input, "Choose option: ")
            ).strip()

            if choice == "4":
                break

            try:
                if choice == "1":
                    await list_nodes(client, panel)

                elif choice == "2":
                    node_id = (
                        await asyncio.to_thread(input, "Node ID: ")
                    ).strip()

                    sensor = (
                        await asyncio.to_thread(input, "Sensor: ")
                    ).strip()

                    await read_and_display_sensor(
                        client, panel, node_id, sensor
                    )

                elif choice == "3":
                    node_id = (
                        await asyncio.to_thread(input, "Node ID: ")
                    ).strip()

                    actuator = (
                        await asyncio.to_thread(input, "Actuator: ")
                    ).strip()

                    state = (
                        await asyncio.to_thread(input, "New state: ")
                    ).strip()

                    await write_actuator(
                        client, panel, node_id, actuator, state
                    )

                else:
                    print("Invalid option")

            except (ConnectionError, OSError, ValueError) as error:
                print(f"[ERROR] {error}")

                # A broken TCP connection cannot be reused.
                if isinstance(error, ConnectionError):
                    break

    except (ConnectionError, OSError) as error:
        print(f"[ERROR] {error}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
