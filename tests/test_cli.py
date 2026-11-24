# Check what the control panel menu and node listing print to the terminal
from idata2304_smart_house_project.cli import print_menu, print_nodes


# Verify print menu
def test_print_menu(capsys):
    # Use pytest s captured stdout to inspect the printed menu
    print_menu()

    output = capsys.readouterr().out
    assert '1. List nodes' in output
    assert '2. Show sensor readings' in output
    assert '3. Read a specific sensor or actuator' in output
    assert '6. Switch role' in output
    assert '8. Quit' in output


# Verify print nodes shows sensor
def test_print_nodes_shows_sensor(capsys):
    nodes = {
        'temp_node_1': {
            'device_type': 'TEMPERATURE_SENSOR',
            'sensors': ['temperature'],
            'actuators': [],
        }
    }

    print_nodes(nodes)

    output = capsys.readouterr().out
    assert 'temp_node_1' in output
    assert 'READ sensor: temperature' in output


# Verify print nodes shows actuator
def test_print_nodes_shows_actuator(capsys):
    nodes = {
        'door_lock_1': {
            'device_type': 'DOOR_LOCK',
            'sensors': [],
            'actuators': ['door_lock'],
        }
    }

    print_nodes(nodes)

    output = capsys.readouterr().out
    assert 'door_lock_1' in output
    assert 'WRITE actuator: door_lock' in output


# Verify print nodes when empty
def test_print_nodes_when_empty(capsys):
    # An empty registry should give the user a message instead of a blank listing
    print_nodes({})

    output = capsys.readouterr().out
    assert 'No nodes found' in output
