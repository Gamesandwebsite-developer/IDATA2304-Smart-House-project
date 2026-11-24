import asyncio
import secrets
import struct
from contextlib import AsyncExitStack
from hmac import compare_digest

from .api import Command, DeviceType, MAX_MESSAGE_SIZE, Packet, TIMEOUT
from .request_handler import RequestHandler
from .sensor_node import SensorActuatorNode
from .SimulationBuilder import build_node


# Manage intermediate server
class IntermediateServer:
    """Manage TCP connections and forward commands to registered nodes."""

    # Initialize the object and prepare it for use
    def __init__(
        self, host: str = "127.0.0.1", port: int = 8081,
        node_token: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.node_token = node_token
        self.nodes: dict[str, SensorActuatorNode] = {}
        self.remote_nodes: dict[str, dict] = {}
        self.node_endpoints: dict[str, tuple[str, int, str]] = {}
        self.clients: dict[str, str] = {}
        self.server: asyncio.Server | None = None
        self.request_handler = RequestHandler(self.nodes)
        self._node_listeners = AsyncExitStack()
        self._registration_lock = asyncio.Lock()
        self._stopping = False

    # Register node
    def register_node(self, node: SensorActuatorNode) -> None:
        """Register a simulated node hosted by this listener."""
        self._check_node_id(node.node_id)
        self.nodes[node.node_id] = node

    # Perform check node id
    def _check_node_id(self, node_id: str) -> None:
        if not node_id or node_id in self.nodes or node_id in self.remote_nodes:
            raise ValueError(f"Invalid or duplicate node ID: '{node_id}'")

    # Perform add simulated node
    async def add_simulated_node(self, node: SensorActuatorNode) -> None:
        """Start a node listener and keep it running once discovery succeeds."""
        from .sensor_server import listen_for_commands

        # Use the context for the duration of the operation
        async with self._registration_lock:
            if self._stopping:
                raise ValueError("The server is stopping")
            self._check_node_id(node.node_id)
            token = secrets.token_urlsafe(24)
            # Use the context for the duration of the operation
            async with AsyncExitStack() as stack:
                listener = await stack.enter_async_context(listen_for_commands(node, token))
                await self.register_remote_node(listener.host, listener.port, token)
                self._node_listeners.push_async_callback(stack.pop_all().aclose)

    # Register remote node
    async def register_remote_node(self, host: str, port: int, token: str) -> None:
        """Discover the components on a sensor-node TCP listener."""
        from .client import AsyncNetworkClient, send_request

        client = AsyncNetworkClient(host, port, quiet=True)
        request = Packet(
            device_id="server", device_type=DeviceType.SERVER,
            payload={"command": Command.LIST_NODES, "token": token},
        )
        # Run the operation and handle possible errors
        try:
            await client.connect()
            reply = await send_request(client, request.encode())
        finally:
            await client.disconnect()

        nodes = reply.get("nodes")
        if reply.get("status") != "success" or not isinstance(nodes, dict) or len(nodes) != 1:
            raise ValueError(f"Could not discover a sensor node at {host}:{port}")
        node_id, info = next(iter(nodes.items()))
        self._check_node_id(node_id)
        # Check the condition and choose the matching result
        if (not isinstance(info, dict)
                or not isinstance(info.get("device_type"), str)
                or info["device_type"] not in DeviceType.__members__):
            raise ValueError(f"Invalid description for node '{node_id}'")
        # Process each item in the collection
        for components, types in (("sensors", "sensor_types"), ("actuators", "actuator_types")):
            names = info.get(components)
            type_map = info.get(types)
            # Check the condition and choose the matching result
            if (not isinstance(names, list) or not all(isinstance(name, str) for name in names)
                    or not isinstance(type_map, dict) or set(names) != type_map.keys()
                    or not all(isinstance(kind, str) and kind in DeviceType.__members__
                               for kind in type_map.values())):
                raise ValueError(f"Invalid {components} for node '{node_id}'")
        self.remote_nodes[node_id] = info
        self.node_endpoints[node_id] = (host, port, token)

    # Register client
    def register_client(self, user_id: str) -> None:
        """Register a control-panel identity."""
        self.clients[user_id] = user_id

    # Start listening
    async def start_listening(self) -> None:
        # asyncio runs the connection handler separately for each client
        self.server = await asyncio.start_server(self._handle_connection, self.host, self.port)
        if self.port == 0:
            self.port = self.server.sockets[0].getsockname()[1]

    # Perform start
    async def start(self) -> None:
        """Start the TCP server and wait for connections."""
        await self.start_listening()
        print(f"[SERVER] Listening on {self.host}:{self.port}...")
        print("Open a control panel in another terminal with uv run client.")
        # Run the operation and handle possible errors
        try:
            await self.server.serve_forever()
        finally:
            await self.stop()

    # Perform stop
    async def stop(self) -> None:
        """Stop the TCP server and close active connections."""
        self._stopping = True
        # Check the condition and choose the matching result
        if self.server:
            self.server.close()
            self.server.close_clients()
            await self.server.wait_closed()
        async with self._registration_lock:
            await self._node_listeners.aclose()

    # Perform handle connection
    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Receive requests and return responses over TCP."""
        addr = writer.get_extra_info("peername")
        # Run the operation and handle possible errors
        try:
            # Repeat while the condition remains true
            while True:
                # The first four bytes are the body length in network byte order
                header = await reader.readexactly(4)
                msg_length = struct.unpack("!I", header)[0]
                # Check the condition and choose the matching result
                if not 0 < msg_length <= MAX_MESSAGE_SIZE:
                    await self._send_response(writer, self.request_handler.error_response(
                        "Invalid message size"
                    ))
                    break

                body = await asyncio.wait_for(reader.readexactly(msg_length), timeout=TIMEOUT)
                await self._send_response(writer, await self.route_network_message(body))

        except asyncio.IncompleteReadError:
            pass
        except OSError as error:
            print(f"[SERVER] Connection error from {addr}: {error}")
        finally:
            writer.close()
            # Run the operation and handle possible errors
            try:
                await writer.wait_closed()
            except OSError:
                pass

    # Perform send response
    async def _send_response(self, writer: asyncio.StreamWriter, response: bytes) -> None:
        if len(response) > MAX_MESSAGE_SIZE:
            response = self.request_handler.error_response("Response too large")
        writer.write(struct.pack("!I", len(response)) + response)
        await asyncio.wait_for(writer.drain(), timeout=TIMEOUT)

    # Perform route message
    def route_message(self, raw_bytes: bytes) -> bytes:
        """Run a request directly against locally registered nodes."""
        return self.request_handler.handle(raw_bytes)

    # Perform server role
    def _server_role(self, packet: Packet) -> str:
        # The node listener accepts only requests from the central server
        token = (packet.payload or {}).get("token")
        # Check the condition and choose the matching result
        if (packet.device_type != DeviceType.SERVER or packet.device_id != "server"
                or self.node_token is None or not isinstance(token, str)
                or not compare_digest(token.encode(), self.node_token.encode())):
            raise ValueError("Invalid server credentials")
        return "admin"

    # Perform route network message
    async def route_network_message(self, raw_bytes: bytes) -> bytes:
        from .client import AsyncNetworkClient

        nodes_info = {node_id: node.describe() for node_id, node in self.nodes.items()}
        nodes_info.update(self.remote_nodes)
        resolve_role = self._server_role if self.node_token is not None else None
        request = self.request_handler.prepare(raw_bytes, nodes_info, resolve_role)
        if isinstance(request, bytes):
            return request

        # Check the condition and choose the matching result
        if request["command"] == Command.REGISTER_NODE:
            if self.node_token is not None:
                return self.request_handler.error_response("Register with the central server")
            # Run the operation and handle possible errors
            try:
                node = build_node(request["node_id"], request["components"])
                await self.add_simulated_node(node)
            except ValueError as error:
                return self.request_handler.error_response(str(error))
            except OSError:
                return self.request_handler.error_response("Could not start the new node")
            return self.request_handler.success_response({"node_id": node.node_id})

        node_id = request["target_node_id"]
        if node_id in self.nodes:
            return self.request_handler.execute(request)

        host, port, token = self.node_endpoints[node_id]
        forwarded = Packet(
            device_id="server",
            device_type=DeviceType.SERVER,
            payload={**request, "token": token},
        ).encode()
        client = AsyncNetworkClient(host, port, quiet=True)
        # Run the operation and handle possible errors
        try:
            # Leave time for the server to return an error to the control panel
            async with asyncio.timeout(TIMEOUT - 2):
                await client.connect()
                response = await client.send_packet(forwarded)
            packet = Packet.decode(response)
            # Check the condition and choose the matching result
            if not isinstance(packet.payload, dict) or packet.payload.get("status") not in (
                "success", "error"
            ):
                raise ValueError("Invalid node response")
            return response
        except (ConnectionError, TimeoutError, ValueError, TypeError, KeyError, RecursionError):
            return self.request_handler.error_response(f"Sensor node '{node_id}' did not respond")
        finally:
            await client.disconnect()
