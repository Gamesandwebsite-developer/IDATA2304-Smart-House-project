import json
import pytest
from idata2304_smart_house_project.control_panel import ControlPanel
from idata2304_smart_house_project.access_control import AccessLevel

def test_control_panel_read_request():
    # Initialize with user_id and access_level string value
    panel = ControlPanel(user_id="user_123", access_level=AccessLevel.ADMIN.value)
    
    # The encoded request is ready to pass to the network client.
    encoded_packet = panel.create_read_request(target_node_id="sensor_42", resource="temperature")
    
    assert isinstance(encoded_packet, bytes)
   