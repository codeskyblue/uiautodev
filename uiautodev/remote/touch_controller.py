import enum
import socket
import struct

from construct import Byte, Int16ub, Int32ub, Int64ub, Struct

from uiautodev.remote.android_input import KeyeventAction, MetaState
from uiautodev.remote.keycode import KeyCode


# https://github.com/Genymobile/scrcpy/blob/master/app/src/control_msg.h#L29
class MessageType(enum.IntEnum):
    INJECT_KEYCODE = 0
    INJECT_TEXT = 1
    INJECT_TOUCH_EVENT = 2
    INJECT_SCROLL_EVENT = 3
    BACK_OR_SCREEN_ON = 4
    EXPAND_NOTIFICATION_PANEL = 5
    EXPAND_SETTINGS_PANEL = 6
    COLLAPSE_PANELS = 7
    GET_CLIPBOARD = 8
    SET_CLIPBOARD = 9
    SET_DISPLAY_POWER = 10
    ROTATE_DEVICE = 11
    UHID_CREATE = 12
    UHID_INPUT = 13
    UHID_DESTROY = 14
    OPEN_HARD_KEYBOARD_SETTINGS = 15
    START_APP = 16
    RESET_VIDEO = 17


TouchEvent = Struct(
    "type" / Byte,               # SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT
    "action" / Byte,             # AKEY_EVENT_ACTION_DOWN
    "pointer_id" / Int64ub,      # 8-byte pointer ID
    "x" / Int32ub,               # X coordinate
    "y" / Int32ub,               # Y coordinate
    "width" / Int16ub,           # width
    "height" / Int16ub,          # height
    "pressure" / Int16ub,        # pressure
    "action_button" / Int32ub,   # action button
    "buttons" / Int32ub          # buttons
)


# Define the structure for key events
KeyEvent = Struct(
    "type" / Byte,               # SC_CONTROL_MSG_TYPE_INJECT_KEYCODE
    "action" / Byte,             # AKEY_EVENT_ACTION (DOWN, UP, MULTIPLE)
    "keycode" / Int32ub,         # Android keycode
    "repeat" / Int32ub,          # Repeat count
    "metastate" / Int32ub        # Meta state flags (SHIFT, ALT, etc.)
)


class ScrcpyTouchController:
    """scrcpy控制类，支持scrcpy版本>=2.2"""

    def __init__(self, control_socket: socket.socket):
        self.control_socket = control_socket

    def _build_touch_event(self, action: int, x: int, y: int, width: int, height: int):
        x = max(0, min(x, width))
        y = max(0, min(y, height))
        return TouchEvent.build(dict(
            type=MessageType.INJECT_TOUCH_EVENT,
            action=action,
            pointer_id=1,
            x=x,
            y=y,
            width=width,
            height=height,
            pressure=1,
            action_button=1, # AMOTION_EVENT_BUTTON_PRIMARY (action button)
            buttons=1, # AMOTION_EVENT_BUTTON_PRIMARY (buttons)
        ))

    def down(self, x: int, y: int, width: int, height: int):
        """发送down操作"""
        data = self._build_touch_event(0, x, y, width, height)
        self.control_socket.send(data)

    def up(self, x: int, y: int, width: int, height: int):
        """发送up操作"""
        data = self._build_touch_event(1, x, y, width, height)
        self.control_socket.send(data)

    def move(self, x: int, y: int, width: int, height: int):
        """发送move操作"""
        data = self._build_touch_event(2, x, y, width, height)
        self.control_socket.send(data)

    def text(self, text: str):
        """发送文本操作"""

        # buffer = text.encode("utf-8")
        # values = struct.pack(self.format_string, 2, 3, 1, len(buffer), 0, 0, 0, self.const_value,
        #                      self.unknown1, self.unknown2) + buffer
        # self.control_socket.send(values)
        pass

    def key(self, action: KeyeventAction, keycode: KeyCode, repeat: int, metastate: MetaState):
        """
        Send a keycode event to the Android device
        
        Args:
            action: Key action (DOWN, UP, or MULTIPLE)
            keycode: Android key code to send
            repeat: Number of times the key is repeated
            metastate: Meta state flags (SHIFT, ALT, etc.)
        """
        # Build the data using the KeyEvent structure
        data = KeyEvent.build(dict(
            type=MessageType.INJECT_KEYCODE,  # Type byte
            action=action,                   # Action byte
            keycode=keycode,                   # Keycode (4 bytes)
            repeat=repeat,                   # Repeat count (4 bytes)
            metastate=metastate,        # Meta state (4 bytes)
        ))
        
        # Send the data to the control socket
        self.control_socket.send(data)
