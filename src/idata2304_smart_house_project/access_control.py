from enum import Enum

class AccessLevel(Enum):
    ADMIN = "admin"
    OWNER = "owner"
    TECHNICIAN = "technician"
    GUEST = "guest"


class AccessControlManager:

    @staticmethod
    def is_authorized(access_level_str: str, action: str, actuator: str = "") -> bool:
        try:
            role = AccessLevel(access_level_str.lower())
        except ValueError:
            return False  # Default deny for invalid/unknown roles

        # Admins and owners have unrestricted access
        if role in (AccessLevel.ADMIN, AccessLevel.OWNER):
            return True

        # All authenticated roles can read data and list nodes
        if action in ("READ", "LIST_NODES","UPDATE_SENSOR"):
            return True

        # WRITE permissions based on role
        if action == "WRITE":
            # Restricted security hardware: only Admin/Owner can toggle door locks
            if actuator == "door_lock" and role not in (AccessLevel.ADMIN, AccessLevel.OWNER):
                return False
            return True

        return False