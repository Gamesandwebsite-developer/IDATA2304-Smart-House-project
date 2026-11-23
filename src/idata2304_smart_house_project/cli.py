# this file creates a control panel and uses a command line interface to interact with it

# to run this file, a server must be running first, using the command:
# python -m idata2304_smart_house_project.__main__
# then run this file in a separate terminal to start the control panel CLI, using the command:
# python -m idata2304_smart_house_project.cli

import asyncio     # runs the asynchronous client menu

from idata2304_smart_house_project.api import Packet
from idata2304_smart_house_project.client import AsyncNetworkClient
from idata2304_smart_house_project.control_panel import ControlPanel


def print_menu() -> None:
    print('\n\n\n1. List nodes')
    print('2. Read sensor')
    print('3. Write actuator')
    print('4. Update sensor')
    print('5. Quit')


def print_nodes(nodes: dict) -> None:
    # Display each node alongside the operations its components offer.
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
    # Refresh the menu's node lookup from the server's current registry.
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
    # Print server errors here so the menu can display successful results only.
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
    # Discover nodes, dispatch menu actions, and close the client when the user quits.
    print('\n-----------------------------')
    print('Smart House Control Panel CLI')
    print('-----------------------------\n')

    # ask for connection settings, providing a default value if skipped
    host = input('Server host [127.0.0.1]: ').strip() or '127.0.0.1'
    port = int(input('Server port [8081]: ').strip() or '8081')
    user_id = input('User ID [admin_user]: ').strip() or 'admin_user'
    access_level = input('Access level [admin]: ').strip() or 'admin'

    # create a control panel object and a network client to let it communicate with the server
    panel = ControlPanel(user_id, access_level)
    client = AsyncNetworkClient(host, port)

    # connect client to server
    await client.connect()

    # Cache nodes by ID for the sensor and actuator menus.
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
            # Pair each sensor name with its node ID because names can repeat across nodes.
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

            selection_text = input('\nChoose sensor option: ').strip()

            try:
                selection = int(selection_text)
                # The displayed menu starts at 1 and Python list indices start at 0.
                target_node_id, resource = sensors[selection - 1]
            except (ValueError, IndexError):
                print('Invalid sensor option')
                continue

            packet = panel.create_read_request(target_node_id, resource)
            result = await send_request(client, packet)

            if result:
                print(
                    f'{result['resource']}' f' at {target_node_id}: ' f'{result['value']}')

        elif choice == '3':
            # Keep the node ID with each actuator so a menu choice identifies its target.
            actuators = []

            for node_id, node_info in nodes.items():
                for actuator in node_info['actuators']:
                    actuators.append((node_id, actuator))

            if not actuators:
                print('No actuators are available')
                continue

            print('\nAvailable actuators:')

            for i, (node_id, actuator) in enumerate(
                actuators,
                start=1,
            ):
                print(f'{i}. {node_id} / {actuator}')

            selection_text = input('\nChoose actuator option: ').strip()

            try:
                selection = int(selection_text)
                target_node_id, actuator = actuators[selection - 1]
            except (ValueError, IndexError):
                print('Invalid actuator selection')
                continue

            state = input('Enter state: ').strip()

            packet = panel.create_write_request(
                target_node_id,
                actuator,
                state,
            )
            result = await send_request(client, packet)

            if result:
                print(
                    f'{result['actuator']} ' f'at {target_node_id}: ' f'{result['new_state']}')

        elif choice == '4':
            # Build the choices from simulated sensors in the cached registry.
            sensors = []

            for node_id, node_info in nodes.items():
                for sensor in node_info['sensors']:
                    sensors.append((node_id, sensor))

            if not sensors:
                print('No sensors are available')
                continue

            print('\nAvailable sensors:')

            for i, (node_id, sensor) in enumerate(
                sensors,
                start=1,
            ):
                print(f'{i}. {node_id} / {sensor}')

            selection_text = input('\nChoose sensor option: ').strip()

            try:
                selection = int(selection_text)
                target_node_id, sensor = sensors[selection - 1]
            except (ValueError, IndexError):
                print('Invalid sensor selection')
                continue

            value_text = input('\nEnter new sensor value: ').strip()

            try:
                value = float(value_text)
            except ValueError:
                print('Sensor value must be a number')
                continue

            packet = panel.create_sensor_update_request(
                target_node_id,
                sensor,
                value,
            )
            result = await send_request(client, packet)

            if result:
                print(
                    f'{result['sensor']} ' f'at {target_node_id}: ' f'{result['new_value']}')

        elif choice == '5':
            print('Shutting down control panel...')
            break

        else:
            print('Invalid command. Please enter a valid menu option number.')

    # disconnect
    await client.disconnect()


# Start the client menu when this module is run directly.
if __name__ == '__main__':
    asyncio.run(main())
