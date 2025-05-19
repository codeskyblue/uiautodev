import asyncio
import json
import logging
import os
import struct
import threading
import time

from adbutils import AdbError, Network, adb
from starlette.websockets import WebSocketDisconnect

from uiautodev.remote.touch_controller import ScrcpyTouchController


class ScrcpyServer:
    """
    ScrcpyServer class is responsible for managing the scrcpy server on Android devices.
    It handles the initialization, communication, and control of the scrcpy server,
    including video streaming and touch control.

    Attributes:
        scrcpy_jar_path (str): Path to the scrcpy server JAR file.
        need_run_scrcpy (bool): Flag indicating whether the scrcpy server needs to be started.
        controller (ScrcpyTouchController): Controller for handling touch events.
        video_socket (socket): Socket for receiving video stream data.
        device (adb.Device): ADB device object representing the connected Android device.
        resolution_width (int): Width of the device screen resolution.
        resolution_height (int): Height of the device screen resolution.
    """

    def __init__(self, scrcpy_jar_path: str = None):
        """
        Initializes the ScrcpyServer instance.

        Args:
            scrcpy_jar_path (str, optional): Path to the scrcpy server JAR file. Defaults to None.
        """
        self.scrcpy_jar_path = scrcpy_jar_path or os.path.join(os.path.dirname(__file__), '../binaries/scrcpy_server.jar')
        self.need_run_scrcpy = True
        self.controller = None
        self.video_socket = None
        self.device = None
        self.resolution_width = 0  # scrcpy 投屏转换宽度
        self.resolution_height = 0  # scrcpy 投屏转换高度
        self.device_width = 0  # 设备真实宽度
        self.device_height = 0  # 设备真实高度

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
            result = device.shell("ps")

            # 检查 scrcpy 服务是否存在
            return 'com.genymobile.scrcpy.Server' in result
        except Exception as e:
            logging.warning(f"Failed to check scrcpy server process: {e}")
            return False

    def start_scrcpy_server(self, serial: str, control: bool = True):
        """
        Pushes the scrcpy server JAR file to the Android device and starts the scrcpy server.

        Args:
            serial (str): Serial number of the Android device.
            control (bool, optional): Whether to enable touch control. Defaults to True.

        Returns:
            threading.Thread: Thread object representing the scrcpy server execution.
        """
        logging.info(f'start_scrcpy_server: {serial}')

        # 检查 scrcpy 是否已经运行
        if self.is_scrcpy_running(serial):
            logging.info(f"scrcpy server already running on {serial}, skipping start")
            return

        # 获取设备对象
        device = adb.device(serial=serial)

        # 推送 scrcpy 服务器到设备
        device.push(self.scrcpy_jar_path, '/data/local/tmp/scrcpy_server.jar')
        logging.info('scrcpy server JAR pushed to device')

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

        # 定义一个线程来执行命令
        def run_scrcpy():
            device.shell(start_command)
            logging.info('scrcpy server started')

        thread = threading.Thread(target=run_scrcpy)
        thread.start()
        return thread

    async def read_video_stream(self, video_socket, websocket):
        """
        Handles video WebSocket connections, streaming video data to the client.

        Args:
            websocket (WebSocket, optional): WebSocket connection to the client. Defaults to None.
            serial (str, optional): Serial number of the Android device. Defaults to ''.
        """
        try:
            while True:
                if video_socket._closed:
                    logging.warning('Video socket is closed.')
                    break

                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, video_socket.recv, 1024 * 1024 * 10)

                if not data:
                    logging.warning('No data received, breaking the loop.')
                    break

                if websocket.client_state.name != "CONNECTED":
                    logging.info('WebSocket no longer connected. Exiting video stream.')
                    break

                # logging.info(f"Data type: {type(data)}, length: {len(data)}")
                if websocket:
                    await websocket.send_bytes(data)

        except Exception as e:
            logging.error(f'Error reading video stream: {e}')

        finally:
            logging.info('enter finally ...')

    def setup_connection(self, serial: str, control: bool = True):
        """
        Sets up the connection to the scrcpy server, including video and control sockets.

        Args:
            serial (str): Serial number of the Android device.
            control (bool, optional): Whether to enable touch control. Defaults to True.

        Returns:
            tuple: Contains the touch controller, video socket, device object, screen width, and screen height.
        """
        device = adb.device(serial=serial)
        # 获取设备真实长宽
        try:
            self.device_width, self.device_height = device.window_size()
            logging.info(f"Device resolution: {self.device_width}x{self.device_height}")
        except Exception as e:
            raise RuntimeError(f"Failed to get device resolution: {e}")

        self.video_socket = None
        for _ in range(100):
            try:
                self.video_socket = device.create_connection(Network.LOCAL_ABSTRACT, 'scrcpy')
                logging.info(f'video_socket = {self.video_socket}')
                break
            except AdbError:
                time.sleep(0.1)

        dummy_byte = self.video_socket.recv(1)
        if not dummy_byte or dummy_byte != b"\x00":
            raise ConnectionError("Did not receive Dummy Byte!")
        logging.info('Received Dummy Byte!')

        if not control:
            return
        else:
            self.controller = None
            for _ in range(100):
                try:
                    self.controller = device.create_connection(Network.LOCAL_ABSTRACT, 'scrcpy')
                    logging.info(f'control_socket = {self.controller}')
                    break
                except AdbError:
                    time.sleep(0.1)
            # Protocol docking reference: https://github.com/Genymobile/scrcpy/blob/master/doc/develop.md
            device_name = self.video_socket.recv(64).decode('utf-8').rstrip('\x00')
            logging.info(f'Device name: {device_name}')

            codec = self.video_socket.recv(4)
            logging.info(f'resolution_data: {codec}')

            resolution_data = self.video_socket.recv(8)
            logging.info(f'resolution_data: {resolution_data}')

            self.resolution_width, self.resolution_height = struct.unpack(">II", resolution_data)
            logging.info(f'Resolution: {self.resolution_width}x{self.resolution_height}')

            format_string = '>BBqiiHHHii'
            const_value = 65535
            unknown1 = 1
            unknown2 = 1

            self.controller = ScrcpyTouchController(self.controller, format_string, const_value, unknown1, unknown2)

    async def handle_control_websocket(self, websocket, serial):
        """
        Handles control WebSocket connections, allowing clients to send touch and key events.

        Args:
            websocket (WebSocket): WebSocket connection to the client.
            serial (str): Serial number of the Android device.
        """
        logging.info(f'Control New control connection from {websocket} for serial: {serial}')
        try:
            while True:
                try:
                    message = await websocket.receive_text()
                    logging.info(f'Received message: {message}')
                    message = json.loads(message)

                    message_type = message.get('messageType', None)
                    # if message_type is None:
                    #     continue
                    if message_type == 'touch':
                        action_type = message['data']['actionType']
                        x, y, width, height = (message['data']['x'], message['data']['y'],
                                               message['data']['width'], message['data']['height'])
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
                    logging.info('Control WebSocket disconnected by client.')
                    break  # 正确退出循环
                except Exception as e:
                    logging.error(f'Error handling message: {e}')
                    break  # 出现错误也应中断，不然会继续尝试 receive
        except Exception as e:
            logging.error(f'Control connection handler error: {e}')
        finally:

            logging.info(f"Control WebSocket closed for serial {serial}")

            if websocket.client_state.name != "DISCONNECTED":
                logging.info(f"control/{serial}: {websocket.client_state.name}")
                await websocket.close()
            logging.info(f"WebSocket closed for control/{serial}")

    async def handle_video_websocket(self, websocket=None, serial=''):
        if websocket:
            logging.info(f'Video New video connection from {websocket} for serial: {serial}')

        video_task = asyncio.create_task(self.read_video_stream(self.video_socket, websocket))

        try:
            while True:
                try:
                    message = await websocket.receive_text()
                    logging.info(f"Received message: {message}")
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
                        logging.info(f'Sent resolution: {response}')
                except json.JSONDecodeError:
                    logging.error('Failed to decode JSON message')
                except WebSocketDisconnect:
                    logging.info("WebSocket disconnected by client.")
                    break
                except Exception as e:
                    logging.error(f'Error handling message: {e}')
                    break

        except Exception as e:
            logging.error(f'Video connection handler error: {e}')
        finally:
            video_task.cancel()

            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close()
            logging.info(f"WebSocket closed for screen/{serial}")
