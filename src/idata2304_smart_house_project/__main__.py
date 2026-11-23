import asyncio
import logging
from idata2304_smart_house_project.server import IntermediateServer
from idata2304_smart_house_project.sensor_node import SensorActuatorNode
from idata2304_smart_house_project.api import DeviceType

logging.basicConfig(level=logging.INFO)


async def run() -> None:
    server = IntermediateServer(host="127.0.0.1", port=8081)

    # Register default nodes
    server.register_node(
        SensorActuatorNode("temp_node_1", DeviceType.TEMPERATURE_SENSOR)
    )
    server.register_node(SensorActuatorNode("door_lock_1", DeviceType.DOOR_LOCK))

    print("Starting Smart House Server on 127.0.0.1:8081...")
    await server.start()


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nServer shut down.")


if __name__ == "__main__":
    main()
