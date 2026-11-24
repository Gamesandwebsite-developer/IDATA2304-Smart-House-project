import json
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any, override


# Manage command
class Command(StrEnum):
    # The command strings are sent verbatim in JSON payloads
    LIST_NODES = "LIST_NODES"
    READ = "READ"
    WRITE = "WRITE"
    UPDATE_SENSOR = "UPDATE_SENSOR"
    REGISTER_NODE = "REGISTER_NODE"


MAX_MESSAGE_SIZE = 1024 * 1024
TIMEOUT = 10


# Perform load device definitions
def _load_device_definitions() -> dict[str, dict[str, Any]]:
    """Load schemas and validate the configuration at startup."""
    path = Path(__file__).with_name("device_types.json")
    with path.open("r", encoding="utf-8") as file:
        definitions = json.load(file)
    if not isinstance(definitions, dict) or not definitions:
        raise ValueError("device_types.json must contain device definitions")

    ids = []
    # Process each item in the collection
    for name, spec in definitions.items():
        if not isinstance(name, str) or not name.isidentifier() or not name.isupper():
            raise ValueError(f"Invalid device name: {name!r}")
        if not isinstance(spec, dict):
            raise ValueError(f"Invalid schema for {name}")
        identifier = spec.get("id")
        if type(identifier) is not int or not 0 <= identifier <= 65535:
            raise ValueError(f"Invalid device ID for {name}")
        ids.append(identifier)
        commands = spec.get("supported_commands")
        # Check the condition and choose the matching result
        if not isinstance(commands, list) or any(
            not isinstance(command, str) or command not in Command for command in commands
        ):
            raise ValueError(f"Invalid commands for {name}")
        kind = spec.get("value_type")
        if kind not in ("float", "string", "none"):
            raise ValueError(f"Invalid value type for {name}")
        if identifier < 0x100 and (kind != "float" or commands != [Command.READ]):
            raise ValueError(f"Sensor {name} needs a numeric range and READ support")
        # Check the condition and choose the matching result
        if 0x100 <= identifier < 0x200 and (
            kind == "none" or set(commands) != {Command.READ, Command.WRITE}
        ):
            raise ValueError(f"Actuator {name} needs a value rule and READ and WRITE support")
        # Check the condition and choose the matching result
        if kind == "float":
            bounds = spec.get("value_range")
            # Check the condition and choose the matching result
            if (not isinstance(bounds, list) or len(bounds) != 2
                    or any(type(n) not in (int, float) for n in bounds)
                    or bounds[0] > bounds[1]):
                raise ValueError(f"Invalid value range for {name}")
            # Run the operation and handle possible errors
            try:
                if not math.isfinite(bounds[1] - bounds[0]) or not all(map(math.isfinite, bounds)):
                    raise ValueError(f"Invalid value range for {name}")
            except OverflowError as error:
                raise ValueError(f"Invalid value range for {name}") from error
        # Check the condition and choose the matching result
        if kind == "string":
            choices = spec.get("allowed_values")
            if not isinstance(choices, list) or not choices or any(not isinstance(s, str) for s in choices):
                raise ValueError(f"Invalid allowed values for {name}")
    if len(ids) != len(set(ids)):
        raise ValueError("Device type IDs must be unique")
    return definitions


DEVICE_DEFINITIONS = _load_device_definitions()
# Read type names and their wire IDs from the same configuration
DeviceType = IntEnum(
    "DeviceType", {name: spec["id"] for name, spec in DEVICE_DEFINITIONS.items()}
)


# Perform supports command
def supports_command(device_type: DeviceType, command: Command) -> bool:
    # Look up the operations declared for this device in the JSON configuration
    return command.value in DEVICE_DEFINITIONS[device_type.name]["supported_commands"]


# Validate device value
def validate_device_value(device_type: DeviceType, value: Any) -> bool:
    """Enforce the JSON schema without silently converting incorrect types."""
    spec = DEVICE_DEFINITIONS[device_type.name]
    # Check the condition and choose the matching result
    if spec["value_type"] == "float":
        return (type(value) in (int, float)
                and not isinstance(value, bool)
                and spec["value_range"][0] <= value <= spec["value_range"][1]
                and math.isfinite(value))
    if spec["value_type"] == "string":
        return isinstance(value, str) and value in spec["allowed_values"]
    return value is None


# Manage packet
@dataclass
class Packet:
    # The envelope identifies the sender and carries command or response data
    device_id: str
    device_type: DeviceType
    timestamp: int | None = field(default_factory=lambda: int(time.time()))
    payload: dict[str, Any] | None = None

    # Convert the object into bytes for sending
    def encode(self) -> bytes:
        # Keep the trailing newline in the JSON body TCP framing uses a separate length prefix
        return (json.dumps(asdict(self)) + "\n").encode()

    # Convert received bytes back into an object
    @classmethod
    def decode(cls, payload: bytes) -> "Packet":
        data = json.loads(payload.decode().strip())
        # Check the condition and choose the matching result
        if (not isinstance(data, dict)
                or not isinstance(data.get("device_id"), str)
                or not data["device_id"]
                or type(data.get("device_type")) is not int
                or (data.get("timestamp") is not None
                    and type(data["timestamp"]) is not int)):
            raise ValueError("Invalid packet envelope")
        data["device_type"] = DeviceType(data["device_type"])
        return cls(**data)


    # Convert the object into a readable text value
    @override
    def __str__(self) -> str:
        data = asdict(self)
        # Display a missing timestamp as the Unix epoch
        data["timestamp"] = datetime.fromtimestamp(float(self.timestamp or 0)).__str__()
        return "Packet: " + str(data)


# Check the condition and choose the matching result
if __name__ == "__main__":
    testPacket = Packet(device_id="XDD", device_type=DeviceType.IRRIGATOR)
    print(testPacket)

    encoded = testPacket.encode()
    print("Encoded bytes:", encoded)

    decoded = Packet.decode(encoded)
    print("Decoded packet object:", decoded)
    print("Is DeviceType enum restored:", isinstance(decoded.device_type, DeviceType))

# Perform split address
def split_address(address: str) -> tuple[str, str]:
    # Return the first three path segments as the node ID and the last as the component
    if not isinstance(address, str):
        raise ValueError("Address must be a string")

    parts = address.split("/")

    # Check the condition and choose the matching result
    if len(parts) != 4 or any(
        not part
        or part in (".", "..")
        or part.strip() != part
        for part in parts
    ):
        raise ValueError(
            "Address must be 'level/room/node/component'"
        )

    return "/".join(parts[:3]), parts[3]
