import asyncio
from contextlib import asynccontextmanager, suppress

from .sensor_node import SensorActuatorNode
from .server import IntermediateServer


# Perform simulate
async def simulate(node: SensorActuatorNode) -> None:
    # Repeat while the condition remains true
    while True:
        node.generate_readings()
        await asyncio.sleep(3)


# Perform listen for commands
@asynccontextmanager
async def listen_for_commands(node: SensorActuatorNode, token: str):
    """Start a simulated node on its own loopback port."""
    server = IntermediateServer(port=0, node_token=token)
    server.register_node(node)
    await server.start_listening()
    simulation = asyncio.create_task(simulate(node))
    # Run the operation and handle possible errors
    try:
        yield server
    finally:
        simulation.cancel()
        with suppress(asyncio.CancelledError):
            await simulation
        await server.stop()
