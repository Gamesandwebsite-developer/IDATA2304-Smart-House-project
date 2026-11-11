import asyncio
import struct
from typing import Optional

class AsyncNetworkClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8081) -> None:
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )
        print(f"[CLIENT] Connected to server at {self.host}:{self.port}")

    async def send_packet(self, data: bytes) -> bytes:
        if not self.writer or not self.reader:
            raise RuntimeError("Client is not connected. Call connect() first.")

        length_prefix = struct.pack("!I", len(data))
        self.writer.write(length_prefix + data)
        await self.writer.drain()
    
        header = await self.reader.readexactly(4)
        msg_length = struct.unpack("!I", header)[0]

        response_bytes = await self.reader.readexactly(msg_length)
        return response_bytes

    async def disconnect(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            print("[CLIENT] Disconnected from server.")