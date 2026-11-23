import json
import math
from pathlib import Path


class AnomalyDetector:
    """Detect sensor readings outside configured limits."""

    def __init__(self) -> None:
        """Load and validate anomaly limits from JSON."""

        # Resolve the settings relative to this module so startup works from any directory.
        path = Path(__file__).with_name("anomaly_limits.json")

        with path.open("r", encoding="utf-8") as file:
            self.limits = json.load(file)

        if not isinstance(self.limits, dict):
            raise ValueError("Invalid anomaly configuration")

        for sensor, limits in self.limits.items():
            if not isinstance(limits, dict):
                raise ValueError(f"Invalid limits for {sensor}")

            minimum = limits.get("min")
            maximum = limits.get("max")

            if not isinstance(minimum, (int, float)):
                raise ValueError(f"Invalid minimum for {sensor}")

            if not isinstance(maximum, (int, float)):
                raise ValueError(f"Invalid maximum for {sensor}")

            if (
                isinstance(minimum, bool)
                or isinstance(maximum, bool)
                or not math.isfinite(minimum)
                or not math.isfinite(maximum)
                or minimum > maximum
            ):
                raise ValueError(f"Invalid limits for {sensor}")

    def check(self, sensor: str, value: float) -> str | None:
        """Return a warning if the reading is abnormal."""

        # Ignore sensors without configured limits.
        if sensor not in self.limits:
            return None

        # Reject invalid sensor values.
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"WARNING: Invalid value for {sensor}!"

        if not math.isfinite(value):
            return f"WARNING: Invalid value for {sensor}!"

        minimum = self.limits[sensor]["min"]
        maximum = self.limits[sensor]["max"]

        # The minimum and maximum themselves are both normal readings.
        if value < minimum:
            return f"WARNING: Low {sensor}!"

        if value > maximum:
            return f"WARNING: High {sensor}!"

        return None
