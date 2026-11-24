import asyncio
from contextlib import AsyncExitStack

import pytest

from idata2304_smart_house_project import ControlPanel, DeviceType, IntermediateServer
from idata2304_smart_house_project import cli
from idata2304_smart_house_project.client import AsyncNetworkClient, send_request
from idata2304_smart_house_project.SimulationBuilder import create_nodes
from idata2304_smart_house_project.sensor_server import listen_for_commands


# Verify panels share state through sensor node sockets
@pytest.mark.asyncio
async def test_panels_share_state_through_sensor_node_sockets(monkeypatch):
    # A fixed random value makes the first generated reading easy to verify
    monkeypatch.setattr("idata2304_smart_house_project.sensor_node.random.uniform",
                        lambda low, high: low)
    nodes = create_nodes()
    server = IntermediateServer(port=0)

    # Use the context for the duration of the operation
    async with AsyncExitStack() as stack:
        listeners = {}
        # Process each item in the collection
        for node_id, node in nodes.items():
            listeners[node_id] = await stack.enter_async_context(
                listen_for_commands(node, "node-token")
            )
            await server.register_remote_node(
                "127.0.0.1", listeners[node_id].port, "node-token"
            )
        await server.start_listening()
        stack.push_async_callback(server.stop)

        owner = ControlPanel("owner", "owner")
        guest = ControlPanel("guest", "guest")
        clients = []
        # Process each item in the collection
        for _ in (owner, guest):
            client = AsyncNetworkClient(port=server.port, quiet=True)
            stack.push_async_callback(client.disconnect)
            await client.connect()
            clients.append(client)

        first, second = clients
        listing, reading = await asyncio.gather(
            send_request(first, owner.create_list_nodes_request()),
            send_request(second, guest.create_read_request("temp_node_1", "temperature")),
        )
        assert set(listing["nodes"]) == set(nodes)
        assert all(len(info["sensors"]) >= 2 and info["actuators"] for info in listing["nodes"].values())
        assert reading["value"] == 18.0

        denied = await send_request(second, guest.create_write_request(
            "door_lock_1", "door_lock", "UNLOCKED"
        ))
        assert denied["status"] == "error"
        assert nodes["door_lock_1"].actuators["door_lock"] == "LOCKED"

        changed = await send_request(first, owner.create_write_request(
            "door_lock_1", "door_lock", "UNLOCKED"
        ))
        observed = await send_request(second, guest.create_read_request("door_lock_1", "door_lock"))
        assert changed["new_state"] == observed["value"] == "UNLOCKED"
        assert nodes["door_lock_1"].actuators["door_lock"] == "UNLOCKED"

        await listeners["door_lock_1"].stop()
        unavailable = await send_request(second, guest.create_read_request("door_lock_1", "door_lock"))
        assert unavailable["status"] == "error"
        assert "did not respond" in unavailable["message"]
        assert (await send_request(second, guest.create_list_nodes_request()))["status"] == "success"


# Verify control panel reports anomaly and reads numeric actuator
@pytest.mark.asyncio
async def test_control_panel_reports_anomaly_and_reads_numeric_actuator(monkeypatch, capsys):
    node = create_nodes()["temp_node_1"]
    node.add_sensor("light", DeviceType.LIGHT_SENSOR, 350.0)
    server = IntermediateServer(port=0)
    # Use the context for the duration of the operation
    async with listen_for_commands(node, "node-token") as listener:
        await server.register_remote_node("127.0.0.1", listener.port, "node-token")
        await server.start_listening()
        # Run the operation and handle possible errors
        try:
            inputs = iter((
                "5", "1", "40",    # Guests cannot override readings
                "6", "3",          # Switch to technician on the same connection
                "5", "1", "40",    # Override temperature
                "5", "2", "50",    # Set humidity inside its safe range
                "5", "3", "500",   # Set a sensor without anomaly limits
                "3", "0",          # Reject the invalid component selection
                "3", "1",          # Read temperature and show a warning
                "4", "2", "22.5",  # Set the thermostat
                "4", "1", "ON",    # Set an actuator with named states
                "6", "4",          # Switch back to guest
                "3", "5",          # Read the thermostat
                "8",
            ))
            prompts = []

            # Perform enter value
            def enter_value(prompt):
                prompts.append(prompt)
                return next(inputs)

            monkeypatch.setattr("builtins.input", enter_value)
            await cli.run(port=server.port)
        finally:
            await server.stop()

    output = capsys.readouterr().out
    assert "Invalid selection" in output
    assert "Access denied" in output
    assert "Current role: technician" in output
    assert "Current role: guest" in output
    # Both the successful update and the later read should warn immediately
    assert output.count("temperature at temp_node_1: 40.0\nWARNING: High temperature!") == 2
    assert output.count("WARNING:") == 2
    assert any("menu option (1–8)" in prompt for prompt in prompts)
    assert any("role (1–4)" in prompt for prompt in prompts)
    assert any("component (1–5)" in prompt for prompt in prompts)
    assert "Enter new temperature reading (safe range: 5 to 30): " in prompts
    assert "Enter new humidity reading (safe range: 30 to 70): " in prompts
    assert "Enter new light reading (0 to 100000, no anomaly limits configured): " in prompts
    assert "Enter new thermostat state (number from -100 to 150): " in prompts
    assert "Enter new fan state (ON / OFF): " in prompts
    assert output.count("thermostat at temp_node_1: 22.5") == 2
    assert node.actuators["thermostat"] == 22.5


# Verify create node in cli and read it from another panel
@pytest.mark.asyncio
async def test_create_node_in_cli_and_read_it_from_another_panel(monkeypatch, capsys):
    # Move registration to the top and check that the displayed numbers still work
    menu = cli.MENU.copy()
    monkeypatch.setattr(cli, "MENU", {"register_node": menu.pop("register_node"), **menu})
    server = IntermediateServer(port=0)
    await server.start_listening()
    node_id = "ground/kitchen/kitchen_node"
    # Run the operation and handle possible errors
    try:
        inputs = iter((
            "1",                    # Guest cannot create nodes
            "7", "2",               # Switch to Owner
            "1", node_id,
            "1", "1", "room_temp", "22",
            "2", "3", "vent", "off",
            "3",                    # Register
            "3",                    # Show a bar for the new sensor
            "5", "1", "ON",
            "8",
        ))
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        await cli.run(port=server.port)

        output = capsys.readouterr().out
        assert "1. Create and register a node" in output
        assert "1. TEMPERATURE_SENSOR" in output
        assert "UNKNOWN_SENSOR" not in output
        assert "Switch to Admin or Owner" in output
        assert f"Registered node: {node_id}" in output
        overview = output.split("Sensor readings", 1)[1]
        assert "room_temp" in overview and "[" in overview and "#" in overview
        assert node_id in server.node_endpoints

        panel = ControlPanel("second_panel", "owner")
        client = AsyncNetworkClient(port=server.port, quiet=True)
        await client.connect()
        # Run the operation and handle possible errors
        try:
            listing = await send_request(client, panel.create_list_nodes_request())
            assert listing["nodes"][node_id]["device_type"] == "SIMULATED_NODE"
            assert listing["nodes"][node_id]["sensors"] == ["room_temp"]
            assert listing["nodes"][node_id]["actuators"] == ["vent"]
            reading = await send_request(client, panel.create_addressed_read_request(f"{node_id}/vent"))
            assert reading["value"] == "ON"

            component = {"name": "room_temp", "type": "TEMPERATURE_SENSOR", "value": 22}
            duplicate = await send_request(client, panel.create_register_node_request(node_id, [component]))
            assert duplicate["status"] == "error"
            invalid = await send_request(client, panel.create_register_node_request(
                "invalid_node", [component, component]
            ))
            assert invalid["status"] == "error"
            assert "invalid_node" not in server.remote_nodes
            panel.access_level = "guest"
            denied = await send_request(client, panel.create_register_node_request("guest_node", [component]))
            assert denied["status"] == "error"
            assert "guest_node" not in server.remote_nodes
        finally:
            await client.disconnect()
    finally:
        await server.stop()
