import struct
from unittest.mock import MagicMock

import pytest

from uiautodev.remote.android_input import KeyeventAction, MetaState
from uiautodev.remote.keycode import KeyCode
from uiautodev.remote.touch_controller import KeyEvent, MessageType, ScrcpyTouchController


@pytest.fixture
def controller():
    # Create a mock socket for testing
    mock_socket = MagicMock()
    
    # Format string and constants used in the controller
    format_string = '>BBqiiHHHii'
    const_value = 65535
    unknown1 = 1
    unknown2 = 1
    
    # Create the controller with the mock socket
    controller = ScrcpyTouchController(
        mock_socket, 
        format_string, 
        const_value, 
        unknown1, 
        unknown2
    )
    
    # Add the mock_socket as an attribute for assertions
    controller.mock_socket = mock_socket
    
    return controller


# Screen dimensions for testing
WIDTH = 1080
HEIGHT = 1920


def test_down(controller):
    """Test the down method sends the correct data"""
    # Test coordinates
    x, y = 100, 200
    
    # Call the down method
    controller.down(x, y, WIDTH, HEIGHT)
    
    # Verify that send was called once
    controller.mock_socket.send.assert_called_once()
    
    # Get the data that was sent
    sent_data = controller.mock_socket.send.call_args[0][0]
    assert sent_data == bytes([
        0x02, # SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT
        0x00, # AKEY_EVENT_ACTION_DOWN
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, #12, 0x34, 0x56, 0x78, 0x87, 0x65, 0x43, 0x21, # pointer_id
        0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x00, 0xc8, # 100 200
        0x04, 0x38, 0x07, 0x80, # width, height
        0x00, 0x01, # pressure
        0x00, 0x00, 0x00, 0x01, # action_button
        0x00, 0x00, 0x00, 0x01, # buttons
    ])


def test_key(controller):
    controller.key(KeyeventAction.UP, KeyCode.ENTER, 5, MetaState.SHIFT_ON | MetaState.SHIFT_LEFT_ON)
    controller.mock_socket.send.assert_called_once()
    
    sent_data = controller.mock_socket.send.call_args[0][0]
    assert sent_data == bytes([
        0x00, # SC_CONTROL_MSG_TYPE_INJECT_KEYCODE
        0x01, # AKEY_EVENT_ACTION_UP
        0x00, 0x00, 0x00, 0x42, # AKEYCODE_ENTER
        0x00, 0x00, 0x00, 0X05, # repeat
        0x00, 0x00, 0x00, 0x41, # AMETA_SHIFT_ON | AMETA_SHIFT_LEFT_ON
    ])