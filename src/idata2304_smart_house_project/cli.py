import asyncio
from os import getpid

from .access_control import AccessControlManager, AccessLevel
from .anomaly_detector import AnomalyDetector
from .api import Command, DEVICE_DEFINITIONS, DeviceType, validate_device_value
from .client import AsyncNetworkClient, send_request
from .control_panel import ControlPanel
from .SimulationBuilder import valid_name, valid_node_id

# Move entries here to change both the displayed order and their shortcut numbers
MENU = {
    "list_nodes": "List nodes",
    "show_readings": "Show sensor readings",
    "read": "Read a specific sensor or actuator",
    "write_actuator": "Change an actuator",
    "set_sensor": "Set a simulated sensor reading",
    "switch_role": "Switch role",
    "register_node": "Create and register a node",
    "quit": "Quit",
}


# Print menu
def print_menu(role: str = "guest") -> None:
    print("\nSmart House Control Panel")
    print(f"\nCurrent role: {role}")
    for number, label in enumerate(MENU.values(), start=1):
        print(f"{number}. {label}")


# Perform switch role
def switch_role(panel: ControlPanel) -> None:
    roles = list(AccessLevel)
    print("\nChoose a role for this demo:")
    print("1. Admin - full access")
    print("2. Owner - full access")
    print("3. Technician - can set sensor readings, cannot change door locks")
    print("4. Guest - can read and use actuators except door locks")
    choice = input(
        f"Choose a role (1–{len(roles)}) or press Enter to keep the current role: "
    ).strip()
    # Check the condition and choose the matching result
    if choice in ("1", "2", "3", "4"):
        panel.access_level = roles[int(choice) - 1].value
    elif choice:
        print("Invalid role number.")


# Print nodes
def print_nodes(nodes: dict) -> None:
    # Check the condition and choose the matching result
    if not nodes:
        print("\nNo nodes found")
        return

    print("\nAvailable nodes:")
    # Process each item in the collection
    for node_id, node in nodes.items():
        print(f"\n{node_id}")
        print(f"    Device type: {node['device_type']}")
        for sensor in node["sensors"]:
            print(f"    READ sensor: {sensor}")
        for actuator in node["actuators"]:
            print(f"    READ / WRITE actuator: {actuator}")


# Perform request
async def request(client: AsyncNetworkClient, packet: bytes) -> dict | None:
    payload = await send_request(client, packet)
    # Check the condition and choose the matching result
    if payload["status"] == "error":
        print(f"Error: {payload.get('message', 'Request failed')}")
        return None
    return payload


# Perform refresh nodes
async def refresh_nodes(client: AsyncNetworkClient, panel: ControlPanel) -> dict:
    result = await request(client, panel.create_list_nodes_request())
    return result["nodes"] if result else {}


# Choose component
def choose_component(
    nodes: dict, categories: tuple[str, ...]
) -> tuple[str, str, str] | None:
    available = [
        (node_id, name, category)
        for node_id, node in nodes.items()
        for category in categories
        for name in node[category]
    ]
    # Check the condition and choose the matching result
    if not available:
        print("No matching components are available.")
        return None

    print("\nAvailable components:")
    for index, (node_id, name, category) in enumerate(available, start=1):
        print(f"{index}. {node_id} / {name} ({category[:-1]})")

    # Run the operation and handle possible errors
    try:
        choices = f"1–{len(available)}" if len(available) > 1 else "1"
        selection = int(input(f"Choose a component ({choices}): ").strip())
        if 1 <= selection <= len(available):
            return available[selection - 1]
    except ValueError:
        pass
    print("Invalid selection")
    return None


# Perform anomaly sensor name
def anomaly_sensor_name(detector: AnomalyDetector, name: str, kind: str | None) -> str:
    if kind and name not in detector.limits:
        return kind.removesuffix("_SENSOR").lower()
    return name


# Print anomaly
def print_anomaly(
    detector: AnomalyDetector, name: str, kind: str | None, value: float
) -> None:
    warning = detector.check(anomaly_sensor_name(detector, name, kind), value)
    if warning:
        print(warning)


# Perform sensor value prompt
def sensor_value_prompt(detector: AnomalyDetector, name: str, kind: str | None) -> str:
    limits = detector.limits.get(anomaly_sensor_name(detector, name, kind))
    value_range = DEVICE_DEFINITIONS.get(kind, {}).get("value_range")
    # Check the condition and choose the matching result
    if limits:
        low, high = limits["min"], limits["max"]
        if value_range:
            low, high = max(low, value_range[0]), min(high, value_range[1])
        if low <= high:
            return f"Enter new {name} reading (safe range: {low} to {high}): "
        return f"Enter new {name} reading (no valid reading avoids a warning): "
    # Check the condition and choose the matching result
    if value_range:
        low, high = value_range
        return f"Enter new {name} reading ({low} to {high}, no anomaly limits configured): "
    return f"Enter new {name} reading (number, no anomaly limits configured): "


# Perform show sensor readings
async def show_sensor_readings(
    client: AsyncNetworkClient, panel: ControlPanel, detector: AnomalyDetector
) -> None:
    nodes = await refresh_nodes(client, panel)
    # Check the condition and choose the matching result
    if not any(node["sensors"] for node in nodes.values()):
        print("No sensors available.")
        return
    print("\nSensor readings (bars use each sensor's allowed range)")
    # Process each item in the collection
    for node_id, node in nodes.items():
        if not node["sensors"]:
            continue
        print(f"\n{node_id}")
        # Process each item in the collection
        for name in node["sensors"]:
            result = await request(client, panel.create_read_request(node_id, name))
            if not result:
                continue
            value = result["value"]
            kind = node.get("sensor_types", {}).get(name)
            bounds = DEVICE_DEFINITIONS.get(kind, {}).get("value_range")
            bar = ""
            # Check the condition and choose the matching result
            if bounds:
                low, high = bounds
                fraction = (float(value) - low) / (high - low) if high != low else 1
                filled = round(max(0, min(1, fraction)) * 16)
                bar = f"  [{'#' * filled}{'-' * (16 - filled)}]"
            print(f"  {name:<18} {value:>8.4g}{bar}")
            print_anomaly(detector, name, kind, value)


# Read device value
def read_device_value(label: str, rule: dict) -> float | str:
    # Check the condition and choose the matching result
    if rule.get("value_type") == "float":
        low, high = rule["value_range"]
        return float(input(f"{label} (number from {low} to {high}): ").strip())

    allowed = rule.get("allowed_values", ())
    choices = " / ".join(allowed) or "text"
    value = input(f"{label} ({choices}): ").strip()
    if value in allowed:
        return value
    return next(
        (state for state in allowed if state.casefold() == value.casefold()), value
    )


# Choose device type
def choose_device_type(sensor: bool) -> DeviceType | None:
    first_id, last_id = (0, 0x100) if sensor else (0x100, 0x200)
    types = [kind for kind in DeviceType if first_id <= kind < last_id]
    for number, kind in enumerate(types, start=1):
        print(f"{number}. {kind.name}")
    print("0. Back")
    # Run the operation and handle possible errors
    try:
        index = int(input(f"Choose a device type (0–{len(types)}): ").strip())
    except ValueError:
        index = -1
    if 1 <= index <= len(types):
        return types[index - 1]
    if index != 0:
        print("Invalid device type")
    return None


# Register node
async def register_node(
    client: AsyncNetworkClient, panel: ControlPanel, detector: AnomalyDetector
) -> bool:
    # Check the condition and choose the matching result
    if not AccessControlManager.is_authorized(
        panel.access_level, Command.REGISTER_NODE
    ):
        print("Switch to Admin or Owner to register a node.")
        return False

    node_id = input("New node ID (name or level/room/node, Enter to cancel): ").strip()
    if not node_id:
        return False
    # Check the condition and choose the matching result
    if not valid_node_id(node_id):
        print(
            "Use letters, numbers, hyphens or underscores in each part of the node ID."
        )
        return False

    components = []
    # Repeat while the condition remains true
    while True:
        print(f"\n{node_id} has {len(components)} selected component(s)")
        print("1. Add sensor\n2. Add actuator\n3. Register node\n0. Cancel")
        choice = input("Choose an option (0–3): ").strip()
        if choice == "0":
            return False
        # Check the condition and choose the matching result
        if choice == "3":
            # Check the condition and choose the matching result
            if not components:
                print("Add at least one sensor or actuator first.")
                continue
            result = await request(
                client, panel.create_register_node_request(node_id, components)
            )
            # Check the condition and choose the matching result
            if result:
                print(f"Registered node: {result['node_id']}")
                return True
            return False
        # Check the condition and choose the matching result
        if choice not in ("1", "2"):
            print("Invalid selection")
            continue

        kind = choose_device_type(sensor=choice == "1")
        if kind is None:
            continue
        name = input(
            "Component name (letters, numbers, underscores or hyphens): "
        ).strip()
        # Check the condition and choose the matching result
        if not valid_name(name) or any(
            component["name"] == name for component in components
        ):
            print("Use a valid name that is unique on this node.")
            continue

        # Run the operation and handle possible errors
        try:
            # Check the condition and choose the matching result
            if choice == "1":
                value = float(
                    input(sensor_value_prompt(detector, name, kind.name)).strip()
                )
            else:
                value = read_device_value(
                    f"Initial value for {name}", DEVICE_DEFINITIONS[kind.name]
                )
        except ValueError:
            print("The initial value must be a number.")
            continue
        # Check the condition and choose the matching result
        if not validate_device_value(kind, value):
            print("The initial value is outside the allowed choices.")
            continue
        components.append({"name": name, "type": kind.name, "value": value})


# Run the application process
async def run(host: str = "127.0.0.1", port: int = 8081) -> None:

    client = AsyncNetworkClient(host, port)
    panel = ControlPanel(f"control_panel_{getpid()}", "guest")
    # Run the operation and handle possible errors
    try:
        detector = AnomalyDetector()
        await client.connect()
        nodes = await refresh_nodes(client, panel)

        # Repeat while the condition remains true
        while True:
            print_menu(panel.access_level)
            # Run the operation and handle possible errors
            try:
                selection = int(
                    input(f"\nChoose a menu option (1–{len(MENU)}): ").strip()
                )
            except ValueError:
                selection = 0
            # Check the condition and choose the matching result
            if not 1 <= selection <= len(MENU):
                print("Invalid command")
                continue

            choice = tuple(MENU)[selection - 1]
            if choice == "quit":
                break
            # Check the condition and choose the matching result
            if choice == "switch_role":
                switch_role(panel)
                continue
            # Check the condition and choose the matching result
            if choice == "list_nodes":
                nodes = await refresh_nodes(client, panel)
                print_nodes(nodes)
                continue
            # Check the condition and choose the matching result
            if choice == "show_readings":
                await show_sensor_readings(client, panel, detector)
                continue
            # Check the condition and choose the matching result
            if choice == "register_node":
                if await register_node(client, panel, detector):
                    nodes = await refresh_nodes(client, panel)
                continue

            categories = {
                "read": ("sensors", "actuators"),
                "write_actuator": ("actuators",),
                "set_sensor": ("sensors",),
            }
            selection = choose_component(nodes, categories[choice])
            if selection is None:
                continue
            node_id, name, category = selection

            # Check the condition and choose the matching result
            if choice == "read":
                result = await request(client, panel.create_read_request(node_id, name))
                # Check the condition and choose the matching result
                if result:
                    value = result["value"]
                    print(f"{name} at {node_id}: {value}")
                    # Check the condition and choose the matching result
                    if category == "sensors":
                        kind = nodes[node_id].get("sensor_types", {}).get(name)
                        print_anomaly(detector, name, kind, value)
            # Check the condition and choose the matching result
            elif choice == "write_actuator":
                kind = nodes[node_id].get("actuator_types", {}).get(name)
                rule = DEVICE_DEFINITIONS.get(kind, {})
                # Run the operation and handle possible errors
                try:
                    state = read_device_value(f"Enter new {name} state", rule)
                except ValueError:
                    print("Actuator state must be a number")
                    continue
                result = await request(
                    client, panel.create_write_request(node_id, name, state)
                )
                if result:
                    print(f"{name} at {node_id}: {result['new_state']}")
            # Check the condition and choose the matching result
            elif choice == "set_sensor":
                kind = nodes[node_id].get("sensor_types", {}).get(name)
                # Run the operation and handle possible errors
                try:
                    value = float(
                        input(sensor_value_prompt(detector, name, kind)).strip()
                    )
                except ValueError:
                    print("Sensor value must be a number")
                    continue
                result = await request(
                    client, panel.create_sensor_update_request(node_id, name, value)
                )
                # Check the condition and choose the matching result
                if result:
                    new_value = result["new_value"]
                    print(f"{name} at {node_id}: {new_value}")
                    print_anomaly(detector, name, kind, new_value)

    except (ConnectionError, ValueError, KeyError, TypeError) as error:
        print(f"Error: {error}")
        if client.writer is None and isinstance(error, ConnectionError):
            print("Start the server in another terminal with uv run server.")
    except (EOFError, KeyboardInterrupt):
        print("\nShutting down control panel.")
    finally:
        await client.disconnect()


# Start the application
def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
