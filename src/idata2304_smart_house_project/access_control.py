from enum import Enum
from .api import Command, DeviceType

# Manage access level
class AccessLevel(Enum):
    # These strings are the role names accepted in request payloads
    ADMIN = "admin"
    OWNER = "owner"
    TECHNICIAN = "technician"
    GUEST = "guest"


# Manage access control manager
class AccessControlManager:

    # Check if authorized
    @staticmethod
    def is_authorized(
        access_level_str: str,
        command: str,
        actuator: str = "",
        actuator_type: str | None = None,
    ) -> bool:
        # Match the requested role and command against the project s permission rules
        try:
            role = AccessLevel(access_level_str.lower())
        except ValueError:
            return False  # Default deny for invalid unknown roles

        # Admins and owners have unrestricted access
        if role in (AccessLevel.ADMIN, AccessLevel.OWNER):
            return True

        if command in (Command.READ, Command.LIST_NODES):
            return True
        if command == Command.UPDATE_SENSOR:
            return role == AccessLevel.TECHNICIAN

        # WRITE permissions based on role
        if command == Command.WRITE:
            if actuator == "door_lock" or actuator_type == DeviceType.DOOR_LOCK.name:
                return False
            return True

        return False
