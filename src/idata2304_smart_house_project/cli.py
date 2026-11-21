# this file creates a control panel and uses a command line interface to interact with it
import asyncio     # runs the asynchronous server

from .api import Packet
from .client import AsyncNetworkClient
from .control_panel import ControlPanel


def print_menu() -> None:
    print('\n\n\n1. List nodes')
    print('2. Read sensor')
    print('3. Write actuator')
    print('4. Update sensor')
    print('5. Quit')


def print_nodes(nodes: dict) -> None:
    if not nodes:
        print('\nNo nodes found')
        return

    print('\nAvilable nodes:')
    for node_id, node_info in nodes.items():
        print(f'\n{node_id}')
        print(f'    Device type: {node_info['device_type']}')

        for sensor in node_info['sensors']:
            print(f'    READ sensor: {sensor}')

        for actuator in node_info['actuators']:
            print(f'    WRITE actuator: {actuator}')


async def refresh_nodes(
        client: AsyncNetworkClient,
        panel: ControlPanel,
) -> dict:
    packet = panel.create_list_nodes_request()
    response_bytes = await client.send_packet(packet)
    response = Packet.decode(response_bytes)

    if not response.payload:
        print('Empty response received from server')
        return {}

    if response.payload['status'] == 'error':
        print(response.payload['message'])
        return {}

    return response.payload['nodes']


async def send_request(
    client: AsyncNetworkClient,
    packet: bytes,
) -> dict | None:
    response_bytes = await client.send_packet(packet)
    response = Packet.decode(response_bytes)

    if not response.payload:
        print('Empty response received from server')
        return None

    if response.payload['status'] == 'error':
        print(f"Error: {response.payload['message']}")
        return None

    return response.payload


async def main() -> None:
    print('\n-----------------------------')
    print('Smart House Control Panel CLI')
    print('-----------------------------\n')

    # ask for connection settings, providing a default value if skipped
    host = input('Server host [127.0.0.1]: ').strip() or '127.0.0.1'
    port = int(input('Server port [8081]: ').strip() or '8081')
    user_id = input('User ID [admin_user]: ').strip() or 'admin_user'
    access_level = input('Access level [admin]:').strip() or 'admin'

    # create a control panel object and a network client to let it communicate with the server
    panel = ControlPanel(user_id, access_level)
    client = AsyncNetworkClient(host, port)

    # connect client to server
    await client.connect()

    # creating a list to keep track of avilable nodes
    nodes = await refresh_nodes(client, panel)

    # menu loop
    while True:
        print_menu()
        choice = input('\nChoose option: ').strip()

        if choice == '1':
            # list nodes
            nodes = await refresh_nodes(client, panel)
            print_nodes(nodes)

        elif choice == '2':
            # read sensor
            sensors = []

            for node_id, node_info in nodes.items():
                for sensor in node_info['sensors']:
                    sensors.append((node_id, sensor))

            if not sensors:
                print('No sensors found')
                continue

            print('\nAvailable sensors:')

            for i, (node_id, sensor) in enumerate(
                sensors,
                start=1,
            ):
                print(f'{i}. {node_id} / {sensor}')

            sensor_choice = input('\nChoose sensor option: ').strip()

            try:
                choice = int(sensor_choice)
                target_node_id, resource = sensors[choice - 1]
            except (ValueError, IndexError):
                print('Invalid sensor option')
                continue

            packet = panel.create_read_request(target_node_id, resource)
            result = await send_request(client, packet)

            if result:
                print(
                    f'{result['resource']}' f' at {target_node_id}: ' f'{result['value']}')

        elif choice == '3':
            # write actuator

            # ask for target_node_id, actuator, and state
            # create a WRITRE packet
            # send it to server
            # print the decoded response
            pass

        elif choice == '4':
            # update sensor

            # ask fir target_node_id, sensor, and value
            # create an UPDATE_SENSOR packet
            # send it to server
            # print the decoded response
            pass

        elif choice == '5':
            print('Shutting down control panel...')
            break

        else:
            print('Invalid command. Please enter a valid menu option number.')

    # disconnect
    await client.disconnect()


# required because file has async code :P
if __name__ == '__main__':
    asyncio.run(main())
