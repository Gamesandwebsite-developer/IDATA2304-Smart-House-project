# Expose the public classes and entry point at the package level
from .api import DeviceType, Packet
from .sensor_node import SensorActuatorNode
from .control_panel import ControlPanel
from .server import IntermediateServer


# Start the application
def main() -> None:
    from .__main__ import main as run_server

    run_server()


__all__ = [
    "DeviceType",
    "Packet",
    "SensorActuatorNode",
    "ControlPanel",
    "IntermediateServer",
    "main",
]
