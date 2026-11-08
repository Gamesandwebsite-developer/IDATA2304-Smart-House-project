import socket
import struct
from .api import Packet
from .control_panel import ControlPanel

HOST = '127.0.0.1'
PORT = 8081


def ask_server(connection, message: bytes) -> Packet:
    """Sends one message to the server and returns its answer"""
    # Send: 4 bytes saying how many bytes are in the message, then the message
    connection.write(struct.pack("!I", len(message)) + message)
    connection.flush()

    # Receive: 4 bytes with the length, then the answer message
    length = struct.unpack("!I", connection.read(4))[0]
    return Packet.decode(connection.read(length))


def main() -> None:
    # control panel is only used for message writing in correct packet format
    panel = ControlPanel("admin_user", access_level="admin")

    # connects to the server
    sock = socket.create_connection((HOST, PORT))
    connection = sock.makefile("rwb")
    print("Connected to the server")

    # show what is in the house
    reply = ask_server(connection, panel.create_list_nodes_request())
    nodes = reply.payload.get("nodes", {})
    print("\nNodes in the house:")
    for node_id, info in nodes.items():
        print(f"  {node_id} -> actuators: {info['actuators']}")

    # let the user switch actuators until they quit
    while True:
        node_id = input("\nNode id (or q to quit): ").strip()
        if node_id == "q":
            break
        actuator = input("Actuator name: ").strip()
        state = input("New state (for example ON or OFF): ").strip().upper()

        message = panel.create_write_request(node_id, actuator, state)
        reply = ask_server(connection, message)
        print("Server says:", reply.payload)

    sock.close()


if __name__ == "__main__":
    main()
