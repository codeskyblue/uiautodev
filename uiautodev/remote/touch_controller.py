import socket
import struct


class ScrcpyTouchController:
    """scrcpy控制类，支持scrcpy版本>=2.2"""

    def __init__(self, control_socket: socket.socket, format_string: str, unknown1: int,
                 unknown2: int, const_value: int):
        self.control_socket = control_socket
        self.format_string = format_string
        self.unknown1 = unknown1
        self.unknown2 = unknown2
        self.const_value = const_value

    def down(self, x: int, y: int, width: int, height: int):
        """发送down操作"""
        values = struct.pack(self.format_string, 2, 0, 1, x, y, width, height, self.const_value,
                             self.unknown1, self.unknown2)
        self.control_socket.send(values)

    def up(self, x: int, y: int, width: int, height: int):
        """发送up操作"""
        values = struct.pack(self.format_string, 2, 1, 1, x, y, width, height, self.const_value,
                             self.unknown1, self.unknown2)
        self.control_socket.send(values)

    def move(self, x: int, y: int, width: int, height: int):
        """发送move操作"""
        values = struct.pack(self.format_string, 2, 2, 1, x, y, width, height, self.const_value,
                             self.unknown1, self.unknown2)
        self.control_socket.send(values)

    def text(self, text: str):
        """发送文本操作"""
        # buffer = text.encode("utf-8")
        # values = struct.pack(self.format_string, 2, 3, 1, len(buffer), 0, 0, 0, self.const_value,
        #                      self.unknown1, self.unknown2) + buffer
        # self.control_socket.send(values)
        pass
