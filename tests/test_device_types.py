
"""Tests for device definitions stored in JSON."""

from idata2304_smart_house_project.api import (
    Command,
    DEVICE_DEFINITIONS,
    DeviceType,
    supports_command,
    validate_device_value,
)


# Verify device commands
def test_device_commands():
    # Check that device IDs and commands match the JSON configuration
    assert DeviceType.DOOR_LOCK.value == DEVICE_DEFINITIONS["DOOR_LOCK"]["id"]
    assert supports_command(DeviceType.DOOR_LOCK, Command.WRITE)
    assert not supports_command(DeviceType.TEMPERATURE_SENSOR, Command.WRITE)


# Verify door lock
def test_door_lock():
    # A door lock accepts LOCKED UNLOCKED but not ON
    assert validate_device_value(DeviceType.DOOR_LOCK, "LOCKED")
    assert validate_device_value(DeviceType.DOOR_LOCK, "UNLOCKED")
    assert not validate_device_value(DeviceType.DOOR_LOCK, "ON")


# Verify temperature
def test_temperature():
    # Temperature must be a number within the configured range
    assert validate_device_value(DeviceType.TEMPERATURE_SENSOR, 35.5)
    assert not validate_device_value(DeviceType.TEMPERATURE_SENSOR, 200)
    assert not validate_device_value(DeviceType.TEMPERATURE_SENSOR, True)


# Verify thermostat
def test_thermostat():
    # Thermostat accepts valid numbers but rejects strings and out of range values
    assert validate_device_value(DeviceType.THERMOSTAT_ACTUATOR, 22.5)
    assert not validate_device_value(DeviceType.THERMOSTAT_ACTUATOR, "ON")
    assert not validate_device_value(DeviceType.THERMOSTAT_ACTUATOR, 200)
