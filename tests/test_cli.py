# Check what the control-panel menu and node listing print to the terminal.
from idata2304_smart_house_project.cli import print_menu, print_nodes


def test_print_menu(capsys):
    # Use pytest's captured stdout to inspect the printed menu.
    print_menu()

    output = capsys.readouterr().out
    assert '1. List nodes' in output
    assert '5. Quit' in output


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


def test_print_nodes_when_empty(capsys):
    # An empty registry should give the user a message instead of a blank listing.
    print_nodes({})

    output = capsys.readouterr().out
    assert 'No nodes found' in output
