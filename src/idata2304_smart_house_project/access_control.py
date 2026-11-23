from enum import Enum
from .api import Command

class AccessLevel(Enum):
    ADMIN = "admin"
    OWNER = "owner"
    TECHNICIAN = "technician"
    GUEST = "guest"


class AccessControlManager:

    @staticmethod
    def is_authorized(access_level_str: str, command: str, actuator: str = "") -> bool:
        try:
            role = AccessLevel(access_level_str.lower())
        except ValueError:
            return False  # Default deny for invalid/unknown roles

        # Admins and owners have unrestricted access
        if role in (AccessLevel.ADMIN, AccessLevel.OWNER):
            return True

        # All authenticated roles can read data and list nodes
        if command in (Command.READ, Command.LIST_NODES, Command.UPDATE_SENSOR):
            return True

        # WRITE permissions based on role
        if command == Command.WRITE:
            # Restricted security hardware: only Admin/Owner can toggle door locks
            if actuator == "door_lock" and role not in (AccessLevel.ADMIN, AccessLevel.OWNER):
                return False
            return True

        return False