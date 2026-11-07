import asyncio
import logging
from idata2304_smart_house_project.server import IntermediateServer
from idata2304_smart_house_project.sensor_node import SensorActuatorNode
from idata2304_smart_house_project.api import DeviceType

logging.basicConfig(level=logging.INFO)

async def main() -> None:
    server = IntermediateServer(host="127.0.0.1", port=8081)

    # Register default nodes
    server.register_node(SensorActuatorNode("temp_node_1", DeviceType.TEMPERATURE_SENSOR))
    server.register_node(SensorActuatorNode("door_lock_1", DeviceType.DOOR_LOCK))

    print("Starting Smart House Server on 127.0.0.1:5555...")
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shut down.")