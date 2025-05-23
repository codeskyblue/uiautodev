import socket
import struct

from construct import Byte, Int16ub, Int32ub, Int64ub, Struct

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


class ScrcpyTouchController:
    """scrcpy控制类，支持scrcpy版本>=2.2"""

    def __init__(self, control_socket: socket.socket, format_string: str, unknown1: int,
                 unknown2: int, const_value: int):
        self.control_socket = control_socket
        self.format_string = format_string # '>BBqiiHHHii'
        self.unknown1 = unknown1
        self.unknown2 = unknown2
        self.const_value = const_value

    def _build(self, action: int, x: int, y: int, width: int, height: int):
        x = max(0, min(x, width))
        y = max(0, min(y, height))
        return TouchEvent.build(dict(
            type=2,
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
        data = self._build(0, x, y, width, height)
        self.control_socket.send(data)

    def up(self, x: int, y: int, width: int, height: int):
        """发送up操作"""
        data = self._build(1, x, y, width, height)
        self.control_socket.send(data)

    def move(self, x: int, y: int, width: int, height: int):
        """发送move操作"""
        data = self._build(2, x, y, width, height)
        self.control_socket.send(data)

    def text(self, text: str):
        """发送文本操作"""
        # buffer = text.encode("utf-8")
        # values = struct.pack(self.format_string, 2, 3, 1, len(buffer), 0, 0, 0, self.const_value,
        #                      self.unknown1, self.unknown2) + buffer
        # self.control_socket.send(values)
        pass
