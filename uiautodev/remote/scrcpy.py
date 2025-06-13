import asyncio
import json
import logging
import os
import socket
import struct
from typing import Optional

import retry
from adbutils import AdbError, Network, adb
from adbutils._adb import AdbConnection
from adbutils._device import AdbDevice
from starlette.websockets import WebSocket, WebSocketDisconnect

from uiautodev.remote.touch_controller import ScrcpyTouchController

logger = logging.getLogger(__name__)


class ScrcpyServer:
    """
    ScrcpyServer class is responsible for managing the scrcpy server on Android devices.
    It handles the initialization, communication, and control of the scrcpy server,
    including video streaming and touch control.
    """

    def __init__(self, device: AdbDevice, scrcpy_jar_path: Optional[str] = None):
        """
        Initializes the ScrcpyServer instance.

        Args:
            scrcpy_jar_path (str, optional): Path to the scrcpy server JAR file. Defaults to None.
        """
        self.scrcpy_jar_path = scrcpy_jar_path or os.path.join(os.path.dirname(__file__),
                                                               '../binaries/scrcpy_server.jar')
        self.device = device
        self.resolution_width = 0  # scrcpy 投屏转换宽度
        self.resolution_height = 0  # scrcpy 投屏转换高度

        self._shell_conn: AdbConnection
        self._video_conn: socket.socket
        self._control_conn: socket.socket

        self._setup_connection()

    def _setup_connection(self):
        self._shell_conn = self._start_scrcpy_server(control=True)
        self._video_conn = self._connect_scrcpy(self.device)
        self._control_conn = self._connect_scrcpy(self.device)
        self._parse_scrcpy_info(self._video_conn)
        self.controller = ScrcpyTouchController(self._control_conn)

    @retry.retry(exceptions=AdbError, tries=20, delay=0.1)
    def _connect_scrcpy(self, device: AdbDevice) -> socket.socket:
        return device.create_connection(Network.LOCAL_ABSTRACT, 'scrcpy')

    def _parse_scrcpy_info(self, conn: socket.socket):
        dummy_byte = conn.recv(1)
        if not dummy_byte or dummy_byte != b"\x00":
            raise ConnectionError("Did not receive Dummy Byte!")
        logger.debug('Received Dummy Byte!')
        device_name = conn.recv(64).decode('utf-8').rstrip('\x00')
        logger.debug(f'Device name: {device_name}')
        codec = conn.recv(4)
        logger.debug(f'resolution_data: {codec}')
        resolution_data = conn.recv(8)
        logger.debug(f'resolution_data: {resolution_data}')
        self.resolution_width, self.resolution_height = struct.unpack(">II", resolution_data)
        logger.debug(f'Resolution: {self.resolution_width}x{self.resolution_height}')

    def close(self):
        try:
            self._control_conn.close()
            self._video_conn.close()
            self._shell_conn.close()
        except:
            pass

    def __del__(self):
        self.close()

    def _start_scrcpy_server(self, control: bool = True) -> AdbConnection:
        """
        Pushes the scrcpy server JAR file to the Android device and starts the scrcpy server.

        Args:
            control (bool, optional): Whether to enable touch control. Defaults to True.

        Returns:
            AdbConnection
        """
        # 获取设备对象
        device = self.device

        # 推送 scrcpy 服务器到设备
        device.sync.push(self.scrcpy_jar_path, '/data/local/tmp/scrcpy_server.jar', check=True)
        logger.info('scrcpy server JAR pushed to device')

        # 构建启动 scrcpy 服务器的命令
        start_command = (
            'CLASSPATH=/data/local/tmp/scrcpy_server.jar '
            'app_process / '
            'com.genymobile.scrcpy.Server 2.7 '
            'log_level=info max_size=1024 max_fps=30 '
            'video_bit_rate=8000000 tunnel_forward=true '
            'send_frame_meta=false '
            f'control={"true" if control else "false"} '
            'audio=false show_touches=false stay_awake=false '
            'power_off_on_close=false clipboard_autosync=false'
        )
        conn = device.shell(start_command, stream=True)
        logger.debug("scrcpy output: %s", conn.conn.recv(100))
        return conn  # type: ignore

    async def handle_unified_websocket(self, websocket: WebSocket, serial=''):
        logger.info(f"[Unified] WebSocket connection from {websocket} for serial: {serial}")

        video_task = asyncio.create_task(self._stream_video_to_websocket(self._video_conn, websocket))
        control_task = asyncio.create_task(self._handle_control_websocket(websocket))

        try:
            # 不使用 return_exceptions=True，让异常能够正确传播
            await asyncio.gather(video_task, control_task)
        finally:
            # 取消任务
            for task in (video_task, control_task):
                if not task.done():
                    task.cancel()
            logger.info(f"[Unified] WebSocket closed for serial={serial}")

    async def _stream_video_to_websocket(self, conn: socket.socket, ws: WebSocket):
        # Set socket to non-blocking mode
        conn.setblocking(False)

        while True:
            # check if ws closed
            if ws.client_state.name != "CONNECTED":
                logger.info('WebSocket no longer connected. Exiting video stream.')
                break
            # Use asyncio to read data asynchronously
            data = await asyncio.get_event_loop().sock_recv(conn, 1024 * 1024)
            if not data:
                logger.warning('No data received, connection may be closed.')
                raise ConnectionError("Video stream ended unexpectedly")
            # send data to ws
            await ws.send_bytes(data)

    async def _handle_control_websocket(self, ws: WebSocket):
        while True:
            try:
                message = await ws.receive_text()
                logger.debug(f"[Unified] Received message: {message}")
                message = json.loads(message)

                width, height = self.resolution_width, self.resolution_height
                message_type = message.get('type')
                if message_type == 'touchMove':
                    xP = message['xP']
                    yP = message['yP']
                    self.controller.move(int(xP * width), int(yP * height), width, height)
                elif message_type == 'touchDown':
                    xP = message['xP']
                    yP = message['yP']
                    self.controller.down(int(xP * width), int(yP * height), width, height)
                elif message_type == 'touchUp':
                    xP = message['xP']
                    yP = message['yP']
                    self.controller.up(int(xP * width), int(yP * height), width, height)
                elif message_type == 'keyEvent':
                    event_number = message['data']['eventNumber']
                    self.device.shell(f'input keyevent {event_number}')
                elif message_type == 'text':
                    text = message['detail']
                    self.device.shell(f'am broadcast -a SONIC_KEYBOARD --es msg \'{text}\'')
                elif message_type == 'ping':
                    await ws.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message: {e}")
                continue
