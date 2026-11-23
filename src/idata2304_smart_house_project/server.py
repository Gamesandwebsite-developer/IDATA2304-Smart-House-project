
import asyncio
import struct
from typing import Dict, Optional

from .api import DeviceType, Packet
from .sensor_node import SensorActuatorNode
from .request_handler import RequestHandler


MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MB


class IntermediateServer:
    """Manage TCP connections and forward requests to a handler."""

    def __init__(
        self, host: str = "127.0.0.1", port: int = 8081
    ) -> None:
        self.host = host
        self.port = port
        self.nodes: Dict[str, SensorActuatorNode] = {}
        self.clients: Dict[str, str] = {}
        self.server: Optional[asyncio.Server] = None

        # Share the registered node collection with the handler.
        self.request_handler = RequestHandler(self.nodes)

    def register_node(self, node: SensorActuatorNode) -> None:
        """Register a node with a unique identifier."""

        if node.node_id in self.nodes:
            raise ValueError(
                f"Node '{node.node_id}' is already registered"
            )

        self.nodes[node.node_id] = node

    def register_client(self, user_id: str) -> None:
        """Register a control-panel identity."""
        self.clients[user_id] = user_id

    async def start(self) -> None:
        """Start the TCP server."""

        # asyncio runs the connection handler separately for each client.
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
                # The first four bytes are the body length in network byte order.
                header = await reader.readexactly(4)
                msg_length = struct.unpack("!I", header)[0]

                # Reply and close on an invalid length because the next frame boundary is uncertain.
                if not 0 < msg_length <= MAX_MESSAGE_SIZE:
                    response = self._error_response(
                        "Invalid message size"
                    )

                    writer.write(
                        struct.pack("!I", len(response)) + response
                    )
                    await writer.drain()
                    break

                # Read the exact length because TCP can split a request across multiple reads.
                raw_bytes = await reader.readexactly(msg_length)

                # Let RequestHandler process the request.
                response = self.route_message(raw_bytes)

                # Prefix the reply with its length using the same format as the request.
                writer.write(
                    struct.pack("!I", len(response)) + response
                )
                await writer.drain()

        except asyncio.IncompleteReadError:
            print(f"[SERVER] Client disconnected: {addr}")

        except (ConnectionResetError, BrokenPipeError, OSError) as error:
            print(f"[SERVER] Connection error: {error}")

        finally:
            writer.close()

            try:
                await writer.wait_closed()
            except OSError:
                pass

    def route_message(self, raw_bytes: bytes) -> bytes:
        """Forward requests to the request handler."""

        return self.request_handler.handle(raw_bytes)

    def _error_response(self, message: str) -> bytes:
        """Create an error response for invalid message sizes."""

        return Packet(
            device_id="server",
            device_type=DeviceType.SERVER,
            payload={
                "status": "error",
                "message": message
            }
        ).encode()
