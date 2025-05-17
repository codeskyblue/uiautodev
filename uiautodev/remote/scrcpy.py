import asyncio
import json
import logging
import os
import struct
import subprocess
import time

from adbutils import AdbError, Network, adb
from starlette.websockets import WebSocketDisconnect

from uiautodev.remote.touch_controller import ScrcpyTouchController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logging.getLogger().setLevel(logging.INFO)


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

    def start_scrcpy_server(self, serial: str, control: bool = True):
        """
        Pushes the scrcpy server JAR file to the Android device and starts the scrcpy server.

        Args:
            serial (str): Serial number of the Android device.
            control (bool, optional): Whether to enable touch control. Defaults to True.

        Returns:
            subprocess.Popen: Process object representing the scrcpy server.
        """
        logging.info(f'start_scrcpy_server: {serial}')
        # 推送scrcpy服务器到设备
        subprocess.run(['adb', '-s', serial, 'push', self.scrcpy_jar_path, '/data/local/tmp/scrcpy_server.jar'])

        # 启动scrcpy服务器
        start_command = [
            'adb', '-s', serial, 'shell', 'CLASSPATH=/data/local/tmp/scrcpy_server.jar',
            'app_process', '/',  # 用于启动 Android 应用程序的工具
            'com.genymobile.scrcpy.Server',  # scrcpy 服务器的入口点，负责处理和管理 scrcpy 的所有功能
            '2.7',  # 当前采用的2.7版本，经测试稳定，兼容安卓15系统
            'log_level=info',
            'max_size=1024',  # 0 表示不限制分辨率，保持原始设备分辨率,这里需要设置最大1024,因为某些oppo手机无法使用1920去解码
            'max_fps=30',  # 15 表示最大帧率为 15 帧每秒。可以调整以减少带宽消耗或提高性能
            'video_bit_rate=8000000',  # 视频的比特率, 默认 8000000 即 8 Mbps 1000000000 1Gbps
            'tunnel_forward=true',  # 启用或禁用 adb 的隧道转发
            'send_frame_meta=false',  # 是否发送每帧的元数据。元数据包括帧的时间戳、序列号等信息，通常用于同步
            'control=true' if control else 'control=false',
            'audio=false',
            'show_touches=false',  # 是否显示触摸操作的指示器
            'stay_awake=false',  # 是否保持设备唤醒状态
            'power_off_on_close=false',  # 是否在关闭 scrcpy 时关闭设备屏幕
            'clipboard_autosync=false'  # 是否自动同步剪贴板
        ]

        process = subprocess.Popen(start_command)
        logging.info('scrcpy server started')
        return process

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
        output = device.shell("wm size")
        if "Physical size" in output:
            size_str = output.strip().split(":")[1].strip()
            self.device_width, self.device_height = map(int, size_str.split("x"))
        else:
            raise RuntimeError("Failed to get device resolution")

        video_socket = None
        for _ in range(100):
            try:
                video_socket = device.create_connection(Network.LOCAL_ABSTRACT, 'scrcpy')
                logging.info(f'video_socket = {video_socket}')
                break
            except AdbError:
                time.sleep(0.1)

        dummy_byte = video_socket.recv(1)
        if not dummy_byte or dummy_byte != b"\x00":
            raise ConnectionError("Did not receive Dummy Byte!")
        logging.info('Received Dummy Byte!')

        if not control:
            return video_socket
        else:
            control_socket = None
            for _ in range(100):
                try:
                    control_socket = device.create_connection(Network.LOCAL_ABSTRACT, 'scrcpy')
                    logging.info(f'control_socket = {control_socket}')
                    break
                except AdbError:
                    time.sleep(0.1)
            # Protocol docking reference: https://github.com/Genymobile/scrcpy/blob/master/doc/develop.md
            device_name = video_socket.recv(64).decode('utf-8').rstrip('\x00')
            logging.info(f'Device name: {device_name}')

            codec = video_socket.recv(4)
            logging.info(f'resolution_data: {codec}')

            resolution_data = video_socket.recv(8)
            logging.info(f'resolution_data: {resolution_data}')

            screen_width, screen_height = struct.unpack(">II", resolution_data)
            logging.info(f'Resolution: {screen_width}x{screen_height}')

            format_string = '>BBqiiHHHii'
            const_value = 65535
            unknown1 = 1
            unknown2 = 1

            touch_controller = ScrcpyTouchController(control_socket, format_string, const_value, unknown1, unknown2)
            return touch_controller, video_socket, device, screen_width, screen_height

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
