import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, override


class DeviceType(IntEnum):
    # sensors go here
    UNKNOWN_SENSOR = 0x000
    TEMPERATURE_SENSOR = 0x001
    LIGHT_SENSOR = 0x002

    # actuators go here
    UNKNOWN_IRRIGATOR = 0x100
    IRRIGATOR = 0x101

    # others
    CONTROL_PANEL = 0x200
    PHONE = 0x201


@dataclass
class Packet:
    device_id: str
    device_type: DeviceType
    timestamp: int | None = field(default_factory=lambda: int(time.time()))
    payload: dict[str, Any] | None = None

    def encode(self) -> bytes:
        return json.dumps(asdict(self)).encode()

    @classmethod
    def decode(cls, payload: bytes) -> Packet:
        return cls(**json.loads(payload.decode()))

    @override
    def __str__(self) -> str:
        data = asdict(self)
        data["timestamp"] = datetime.fromtimestamp(float(self.timestamp)).__str__()  # ty: ignore[invalid-argument-type]
        return "Packet: " + data.__str__()


if __name__ == "__main__":
    testPacket = Packet(device_id="XDD", device_type=DeviceType.IRRIGATOR)
    print(testPacket)

    encoded = testPacket.encode()
    print(encoded)

    decoded = Packet.decode(encoded)
    print(decoded)
