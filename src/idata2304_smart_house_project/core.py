from .api import DeviceType, Packet
from .sensor_node import SensorActuatorNode
from .control_panel import ControlPanel
from .server import IntermediateServer

def main() -> None:
    print("-----------------------------------------")
    print(" Smart House Communication MVP Simulation")
    print("-----------------------------------------")

    # Starting the IntermediateServer
    server = IntermediateServer()

    # Instantiate and register nodes
    temp_sensor = SensorActuatorNode("temp_node_01", DeviceType.TEMPERATURE_SENSOR)
    temp_sensor.update_sensor("temperature", 23.4)
    server.register_node(temp_sensor)

    irrigator_node = SensorActuatorNode("irrigator_node_01", DeviceType.IRRIGATOR)
    server.register_node(irrigator_node)

    # Instantiate controlpanel client
    admin_panel = ControlPanel("admin_user", access_level="admin")
    server.register_client(admin_panel.user_id)

    # Test READ execution over packet bytes
    print("\n[READ Request] Querying temperature sensor...")
    read_bytes = admin_panel.create_read_request("temp_node_01", "temperature")
    print(f"Sent Bytes:     {read_bytes}")

    read_response_bytes = server.route_message(read_bytes)
    read_packet = Packet.decode(read_response_bytes)
    print(f"Decoded Packet: {read_packet}")

    # Test WRITE execution over packet bytes
    print("\n[WRITE Request] Activating irrigator valve...")
    write_bytes = admin_panel.create_write_request("irrigator_node_01", "irrigator_valve", "ON")
    print(f"Sent Bytes:     {write_bytes}")

    write_response_bytes = server.route_message(write_bytes)
    write_packet = Packet.decode(write_response_bytes)
    print(f"Decoded Packet: {write_packet}")

if __name__ == "__main__":
    main()