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
        self.scrcpy_jar_path = scrcpy_jar_path or os.path.join(os.path.dirname(__file__), '../binaries/scrcpy_server.jar')
        self.device = device
        self.resolution_width = 0  # scrcpy 投屏转换宽度
        self.resolution_height = 0  # scrcpy 投屏转换高度
        self.device_width = 0  # 设备真实宽度
        self.device_height = 0  # 设备真实高度
        
        self._shell_conn: AdbConnection
        self._video_conn: socket.socket
        self._control_conn: socket.socket

        self._setup_connection()
    
    def _setup_connection(self):
        self._shell_conn = self.start_scrcpy_server(control=True)
        self._video_conn = self._connect_scrcpy(self.device)
        self._control_conn = self._connect_scrcpy(self.device)
        self._parse_scrcpy_info(self._video_conn)
        self.device_width, self.device_height = self.device.window_size()
        logger.debug(f"Device size: {self.device_width}x{self.device_height}")

        format_string = '>BBqiiHHHii'
        const_value = 65535
        unknown1 = 1
        unknown2 = 1
        self.controller = ScrcpyTouchController(self._control_conn, format_string, const_value, unknown1, unknown2)
        
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
    
    @staticmethod
    def is_scrcpy_running(serial: str) -> bool:
        """
        检查 scrcpy 服务器是否正在运行。

        Args:
            serial (str): Android 设备的序列号。

        Returns:
            bool: 如果 scrcpy 服务器正在运行，返回 True；否则返回 False。
        """
        try:
            # 使用 adbutils 获取设备
            device = adb.device(serial=serial)

            # 执行 shell 命令
            ret = device.shell2("ps")
            # 检查 scrcpy 服务是否存在
            # COMMENT(ssx): ps未必在每个设备上都好使
            return 'com.genymobile.scrcpy.Server' in ret.output # type: ignore
        except Exception as e:
            logger.warning(f"Failed to check scrcpy server process: {e}")
            return False

    def start_scrcpy_server(self, control: bool = True) -> AdbConnection:
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
        print(conn.conn.recv(100))
        return conn # type: ignore

    async def stream_video_to_websocket(self, conn: socket.socket, ws: WebSocket):
        # Set socket to non-blocking mode
        conn.setblocking(False)
        
        while True:
            # check if ws closed
            if ws.client_state.name != "CONNECTED":
                logger.info('WebSocket no longer connected. Exiting video stream.')
                break
                
            try:
                # Use asyncio to read data asynchronously
                data = await asyncio.get_event_loop().sock_recv(conn, 1024*1024)
                if not data:
                    logger.warning('No data received, breaking the loop.')
                    break
                # send data to ws
                await ws.send_bytes(data)
            except (ConnectionError, BrokenPipeError) as e:
                logger.error(f'Socket error: {e}')
                break
            


    @retry.retry(exceptions=AdbError, tries=20, delay=0.1)
    def _connect_scrcpy(self, device: AdbDevice) -> socket.socket:
        return device.create_connection(Network.LOCAL_ABSTRACT, 'scrcpy')
    

    async def handle_control_websocket(self, websocket, serial):
        """
        Handles control WebSocket connections, allowing clients to send touch and key events.

        Args:
            websocket (WebSocket): WebSocket connection to the client.
            serial (str): Serial number of the Android device.
        """
        logger.info(f'Control New control connection from {websocket} for serial: {serial}')
        try:
            while True:
                try:
                    message = await websocket.receive_text()
                    logger.info(f'Received message: {message}')
                    message = json.loads(message)

                    message_type = message.get('type', None)
                    # if message_type is None:
                    #     continue
                    if message_type == 'touch':
                        action_type = message.get('actionType')
                        width, height = self.resolution_width, self.resolution_height
                        x = int(message['x'] * width)
                        y = int(message['y'] * height)
                        if action_type == 0:
                            self.controller.down(x, y, width, height)
                        elif action_type == 1:
                            self.controller.up(x, y, width, height)
                        elif action_type == 2:
                            self.controller.move(x, y, width, height)
                        else:
                            raise Exception(f'not support action_type: {action_type}')

                    elif message_type == 'keyEvent':
                        event_number = message['data']['eventNumber']
                        self.device.shell(f'input keyevent {event_number}')

                    elif message_type == 'text':
                        text = message['detail']
                        self.device.shell(f'am broadcast -a SONIC_KEYBOARD --es msg \'{text}\'')

                except WebSocketDisconnect:
                    logger.info('Control WebSocket disconnected by client.')
                    break  # 正确退出循环
        finally:

            logger.info(f"Control WebSocket closed for serial {serial}")

            if websocket.client_state.name != "DISCONNECTED":
                logger.info(f"control/{serial}: {websocket.client_state.name}")
                await websocket.close()
            logger.info(f"WebSocket closed for control/{serial}")

    async def handle_video_websocket(self, websocket: WebSocket, serial=''):
        if websocket:
            logger.info(f'Video New video connection from {websocket} for serial: {serial}')

        video_task = asyncio.create_task(self.stream_video_to_websocket(self._video_conn, websocket))

        try:
            while True:
                try:
                    message = await websocket.receive_text()
                    logger.info(f"Received message: {message}")
                    data = json.loads(message)
                    if 'udid' in data:
                        response = json.dumps({
                            'messageType': 'sizeInfo',
                            'sizeInfo': {
                                'width': self.resolution_width,
                                'height': self.resolution_height,
                                'device_width': self.device_width,
                                'device_height': self.device_height,
                                'rotation': 0,
                            }
                        })
                        await websocket.send_text(response)
                        logger.info(f'Sent resolution: {response}')
                except json.JSONDecodeError:
                    logger.error('Failed to decode JSON message')
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected by client.")
                    break
                except Exception as e:
                    logger.error(f'Error handling message: {e}')
                    break

        except Exception as e:
            logger.error(f'Video connection handler error: {e}')
        finally:
            video_task.cancel()

            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close()
            logger.info(f"WebSocket closed for screen/{serial}")

    async def handle_unified_websocket(self, websocket: WebSocket, serial=''):
        logger.info(f"[Unified] WebSocket connection from {websocket} for serial: {serial}")

        # 启动视频流任务
        video_task = asyncio.create_task(self.stream_video_to_websocket(self._video_conn, websocket))

        try:
            while True:
                try:
                    message = await websocket.receive_text()
                    logger.debug(f"[Unified] Received message: {message}")
                    message = json.loads(message)

                    message_type = message.get('type')

                    if message_type == 'touch':
                        action_type = message.get('actionType')
                        width, height = self.resolution_width, self.resolution_height
                        x = int(message['x'] * width)
                        y = int(message['y'] * height)
                        if action_type == 0:
                            self.controller.down(x, y, width, height)
                        elif action_type == 1:
                            self.controller.up(x, y, width, height)
                        elif action_type == 2:
                            self.controller.move(x, y, width, height)
                        else:
                            logger.warning(f"[Unified] Unknown actionType: {action_type}")

                    elif message_type == 'keyEvent':
                        event_number = message['data']['eventNumber']
                        self.device.shell(f'input keyevent {event_number}')

                    elif message_type == 'text':
                        text = message['detail']
                        self.device.shell(f'am broadcast -a SONIC_KEYBOARD --es msg \'{text}\'')

                    elif message_type == 'ping':
                        await websocket.send_text(json.dumps({"type": "pong"}))

                except WebSocketDisconnect:
                    logger.info('[Unified] WebSocket disconnected by client.')
                    break
                except Exception as e:
                    logger.exception(f'[Unified] Exception while handling message: {e}')
                    break
        finally:
            video_task.cancel()
            try:
                await video_task
            except asyncio.CancelledError:
                logger.info('[Unified] Video task cancelled.')

            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close()
            logger.info(f"[Unified] WebSocket closed for serial={serial}")

