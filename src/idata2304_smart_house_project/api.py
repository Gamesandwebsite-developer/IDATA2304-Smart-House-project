import json
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any, override


class Command(StrEnum):
    LIST_NODES = "LIST_NODES"
    READ = "READ"
    WRITE = "WRITE"
    UPDATE_SENSOR = "UPDATE_SENSOR"


def _load_device_definitions() -> dict[str, dict[str, Any]]:
    """Load schemas and validate the configuration at startup."""
    path = Path(__file__).with_name("device_types.json")
    with path.open("r", encoding="utf-8") as file:
        definitions = json.load(file)
    if not isinstance(definitions, dict) or not definitions:
        raise ValueError("device_types.json must contain device definitions")

    ids = []
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
        if not isinstance(commands, list) or any(command not in Command._value2member_map_ for command in commands):
            raise ValueError(f"Invalid commands for {name}")
        kind = spec.get("value_type")
        if kind not in ("float", "string", "none"):
            raise ValueError(f"Invalid value type for {name}")
        if kind == "float":
            bounds = spec.get("value_range")
            if (not isinstance(bounds, list) or len(bounds) != 2
                    or any(type(n) not in (int, float) for n in bounds)
                    or bounds[0] > bounds[1]):
                raise ValueError(f"Invalid value range for {name}")
        if kind == "string":
            choices = spec.get("allowed_values")
            if not isinstance(choices, list) or not choices or any(not isinstance(s, str) for s in choices):
                raise ValueError(f"Invalid allowed values for {name}")
    if len(ids) != len(set(ids)):
        raise ValueError("Device type IDs must be unique")
    return definitions


DEVICE_DEFINITIONS = _load_device_definitions()
# Keep integer identifiers compatible with the original Packet format.
DeviceType = IntEnum(
    "DeviceType",
    {name: spec["id"] for name, spec in DEVICE_DEFINITIONS.items()},
    module=__name__,
)


def supports_command(device_type: DeviceType, command: Command) -> bool:
    return command.value in DEVICE_DEFINITIONS[device_type.name]["supported_commands"]


def validate_device_value(device_type: DeviceType, value: Any) -> bool:
    """Enforce the JSON schema without silently converting incorrect types."""
    spec = DEVICE_DEFINITIONS[device_type.name]
    if spec["value_type"] == "float":
        return (type(value) in (int, float)
                and not isinstance(value, bool)
                and math.isfinite(value)
                and spec["value_range"][0] <= value <= spec["value_range"][1])
    if spec["value_type"] == "string":
        return isinstance(value, str) and value in spec["allowed_values"]
    return value is None


@dataclass
class Packet:
    device_id: str
    device_type: DeviceType
    timestamp: int | None = field(default_factory=lambda: int(time.time()))
    payload: dict[str, Any] | None = None

    def encode(self) -> bytes:
        # Appending \n ensures clean stream socket message framing
        return (json.dumps(asdict(self)) + "\n").encode()

    @classmethod
    def decode(cls, payload: bytes) -> "Packet":
        data = json.loads(payload.decode().strip())
        # Safely convert raw integer back into a DeviceType IntEnum
        data["device_type"] = DeviceType(data["device_type"])
        return cls(**data)


    @override
    def __str__(self) -> str:
        data = asdict(self)
        # Add "or 0" to handle the None case safely for the type checker
        data["timestamp"] = datetime.fromtimestamp(float(self.timestamp or 0)).__str__()
        return "Packet: " + str(data)


if __name__ == "__main__":
    testPacket = Packet(device_id="XDD", device_type=DeviceType.IRRIGATOR)
    print(testPacket)

    encoded = testPacket.encode()
    print("Encoded bytes:", encoded)

    decoded = Packet.decode(encoded)
    print("Decoded packet object:", decoded)
    print("Is DeviceType enum restored:", isinstance(decoded.device_type, DeviceType))
    