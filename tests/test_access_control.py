# Cover protocol role values and the authorization rules applied by the server
import pytest
from idata2304_smart_house_project.access_control import AccessControlManager, AccessLevel

# Verify access level enum
def test_access_level_enum():
    assert AccessLevel.ADMIN.value == "admin"
    assert AccessLevel.GUEST.value == "guest"

# Verify is authorized admin unrestricted
def test_is_authorized_admin_unrestricted():
    # Admins have unrestricted access to everything including door locks
    assert AccessControlManager.is_authorized("admin", "WRITE", "door_lock") is True

# Verify is authorized guest restrictions
def test_is_authorized_guest_restrictions():
    # Guests can read data
    assert AccessControlManager.is_authorized("guest", "READ") is True
    # But guests cannot toggle door locks
    assert AccessControlManager.is_authorized("guest", "WRITE", "door_lock") is False

# Verify is authorized invalid role
def test_is_authorized_invalid_role():
    # An unrecognized role is denied even for a read request
    assert AccessControlManager.is_authorized("invalid_role", "READ") is False