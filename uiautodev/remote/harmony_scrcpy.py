import asyncio
import json
import logging
import socket
from datetime import datetime
from threading import Thread

from fastapi import WebSocket
from hypium import KeyCode

logger = logging.getLogger(__name__)


class HarmonyScrcpyServer:
    """
    HarmonyScrcpyServer is responsible for handling screen streaming functionality
    for HarmonyOS devices that support ABC proxy (a communication interface).

    It manages WebSocket clients, communicates with the ABC server over gRPC, and streams
    the device's screen data in real-time to connected clients.

    This server is specifically designed for devices running in 'abc mode' and requires that
    the target device expose an `abc_proxy` attribute for communication.

    Attributes:
        device: The HarmonyOS device object.
        driver: The controlling driver which may wrap the device.
        abc_rpc_addr: Tuple containing the IP and port used to communicate with abc_proxy.
        channel: The gRPC communication channel (initialized later).
        clients: A set of connected WebSocket clients.
        loop: Asyncio event loop used to run asynchronous tasks.
        is_running: Boolean flag indicating if the streaming service is active.

    Raises:
        RuntimeError: If the connected device does not support abc_proxy.

    References:
        - Huawei HarmonyOS Python Guidelines:
          https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines
    """

    def __init__(self, driver):
        if hasattr(driver, "_device"):
            device = driver._device
        else:
            device = driver
        logger.info(f'device: {device}')
        if not hasattr(device, "abc_proxy") or device.abc_proxy is None:
            raise RuntimeError("Only abc mode can support screen recorder")
        self.device = device
        self.driver = driver
        self.abc_rpc_addr = ("127.0.0.1", device.abc_proxy.port)
        self.channel = None
        self.clients = set()
        self.loop = asyncio.get_event_loop()
        self.is_running = False

    def connect(self):
        self.channel = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.channel.connect(self.abc_rpc_addr)

    def start(self, timeout=3600):
        if self.channel is None:
            self.connect()
        self.is_running = True
        self.timeout = timeout
        self.stop_capture_if_running()
        msg_json = {'api': "startCaptureScreen", 'args': []}
        full_msg = {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "Captures", 
            "params": msg_json,
            "request_id": datetime.now().strftime("%Y%m%d%H%M%S%f")
        }
        full_msg_str = json.dumps(full_msg, ensure_ascii=False, separators=(',', ':'))
        self.channel.sendall(full_msg_str.encode("utf-8") + b'\n')
        reply = self.channel.recv(1024)
        logger.info(f'reply: {reply}')
        if b"true" in reply:
            thread_record = Thread(target=self._record_worker)
            thread_record.start()
        else:
            raise RuntimeError("Fail to start screen capture")

    def stop_capture_if_running(self):
        msg_json = {'api': "stopCaptureScreen", 'args': []}
        full_msg = {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "Captures", 
            "params": msg_json,
            "request_id": datetime.now().strftime("%Y%m%d%H%M%S%f")
        }
        full_msg_str = json.dumps(full_msg, ensure_ascii=False, separators=(',', ':'))
        self.channel.sendall(full_msg_str.encode("utf-8") + b'\n')
        reply = self.channel.recv(1024)
        logger.info(f'stop reply: {reply}')

    async def handle_ws(self, websocket: WebSocket):
        self.clients.add(websocket)
        serial = getattr(self.device, "device_sn", "unknown")
        logger.info(f"[{serial}] WebSocket connected")

        try:
            while True:
                message = await websocket.receive_text()
                logger.info(f"Received message: {message}")
                try:
                    data = json.loads(message)
                    if data.get('type') == 'touch':
                        action = data.get('action')
                        x, y = data.get('x'), data.get('y')
                        if action == 'normal':
                            self.driver.touch((x, y))
                        elif action == 'long':
                            self.driver.touch(target=(x, y), mode='long')
                        elif action == 'double':
                            self.driver.touch(target=(x, y), mode='double')
                        elif action == 'move':
                            self.driver.slide(
                                start=(data.get('x1'), data.get('y1')),
                                end=(data.get('x2'), data.get('y2')),
                                slide_time=0.1
                            )
                    elif data.get('type') == 'keyEvent':
                        event_number = data['eventNumber']
                        if event_number == 187:
                            self.driver.swipe_to_recent_task()
                        elif event_number == 3:
                            self.driver.go_home()
                        elif event_number == 4:
                            self.driver.go_back()
                        elif event_number == 224:
                            self.driver.wake_up_display()
                    elif data.get('type') == 'text':
                        detail = data.get('detail')
                        if detail == 'CODE_AC_BACK':
                            self.driver.press_key(KeyCode.DEL)
                        elif detail == 'CODE_AC_ENTER':
                            self.driver.press_key(KeyCode.ENTER)
                        else:
                            self.driver.shell(
                                f"uitest uiInput inputText {data.get('x')} {data.get('y')} {detail}")
                except Exception as e:
                    logger.warning(f"Failed to handle message: {e}")
        except Exception as e:
            logger.info(f"WebSocket closed: {e}")
        finally:
            self.clients.discard(websocket)

    def _record_worker(self):
        tmp_data = b''
        start_flag = b'\xff\xd8'
        end_flag = b'\xff\xd9'
        while self.is_running:
            try:
                result = self.channel.recv(4096 * 1024)
                tmp_data += result
                while start_flag in tmp_data and end_flag in tmp_data:
                    start_index = tmp_data.index(start_flag)
                    end_index = tmp_data.index(end_flag) + 2
                    frame = tmp_data[start_index:end_index]
                    tmp_data = tmp_data[end_index:]
                    asyncio.run_coroutine_threadsafe(self._broadcast(frame), self.loop)
            except Exception as e:
                logger.warning(f"Record worker error: {e}")
                self.is_running = False
                self.channel = None
                break

    async def _broadcast(self, data):
        for client in self.clients.copy():
            try:
                await client.send_bytes(data)
            except Exception as e:
                logger.info(f"Send error, removing client: {e}")
                self.clients.discard(client)

    def stop(self):
        self.is_running = False
        if self.channel is None:
            return
        msg_json = {'api': "stopCaptureScreen", 'args': []}
        full_msg = {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "Captures",
            "params": msg_json,
            "request_id": datetime.now().strftime("%Y%m%d%H%M%S%f")
        }
        full_msg_str = json.dumps(full_msg, ensure_ascii=False, separators=(',', ':'))
        self.channel.sendall(full_msg_str.encode("utf-8") + b'\n')
        reply = self.channel.recv(1024)
        if b"true" not in reply:
            logger.info("Fail to stop capture")
        self.channel.close()
        self.channel = None
        for client in self.clients:
            asyncio.run_coroutine_threadsafe(client.close(), self.loop)
