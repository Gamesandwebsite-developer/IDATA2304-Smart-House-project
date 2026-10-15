import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, override


class DeviceType(IntEnum):
    # Sensors (0x000 - 0x0FF)
    UNKNOWN_SENSOR = 0x000
    TEMPERATURE_SENSOR = 0x001
    LIGHT_SENSOR = 0x002
    HUMIDITY_SENSOR = 0x003
    MOTION_SENSOR = 0x004
    SMOKE_FLAME_DETECTOR = 0x005

    # Actuators (0x100 - 0x1FF)
    UNKNOWN_ACTUATOR = 0x100
    IRRIGATOR = 0x101
    FAN = 0x102
    HEATER = 0x103
    DOOR_LOCK = 0x104

    # Control / System Nodes (0x200+)
    CONTROL_PANEL = 0x200
    PHONE = 0x201
    SERVER = 0x202


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
    