import asyncio
import struct
from typing import Optional


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

        if len(data) == 0 or len(data) > MAX_MESSAGE_SIZE:
            raise ValueError("Invalid message size")

        try:
            # Send the four-byte length and message.
            length_prefix = struct.pack("!I", len(data))
            self.writer.write(length_prefix + data)

            await asyncio.wait_for(
                self.writer.drain(),
                timeout=TIMEOUT
            )

            # Read the response length.
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