#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Apr 21 2024 21:15:15 by codeskyblue
"""


import atexit
from base64 import b64decode
import enum
import io
import json
import logging
from pprint import pprint
import threading
import time
from pathlib import Path
from typing import Any, Optional

from PIL import Image
import adbutils
import requests
from pydantic import BaseModel

"""
shell steps:
adb push appium-uiautomator2-v5.12.4.apk /data/local/tmp/udt.jar
adb shell CLASSPATH=/data/local/tmp/udt.jar app_process / "com.wetest.uia2.Main"
adb forward tcp:6790 tcp:6790
# 创建session
echo '{"capabilities": {}}' | http POST :6790/session
# 获取当前所有session
http GET :6790/sessions
# 获取pageSource
http GET :6790/session/{session_id}/source

# TODO
# /appium/settins 中waitForIdleTimeout需要调整，其他的再看看
"""

logger = logging.getLogger(__name__)

class UDTError(Exception):
    pass


class HTTPError(UDTError):
    pass


class AppiumErrorEnum(str, enum.Enum):
    InvalidSessionID = 'invalid session id'


class AppiumError(UDTError):
    def __init__(self, error: str, message):
        self.error = error
        self.message = message


class AppiumResponseValue(BaseModel):
    error: Optional[str] = None
    message: Optional[str] = None
    stacktrace: Optional[str] = None


class AppiumResponse(BaseModel):
    sessionId: Optional[str] = None
    value: Any = None


class MockAdbProcess:
    def __init__(self, conn: adbutils.AdbConnection) -> None:
        self._conn = conn
        self._event = threading.Event()
        
        def wait_finished():
            try:
                self._conn.read_until_close()
            except:
                pass
            self._event.set()
        
        t = threading.Thread(target=wait_finished)
        t.daemon = True
        t.name = "wait_adb_conn"
        t.start()

    def wait(self) -> int:
        self._event.wait()
        return 0

    def pool(self) -> Optional[int]:
        if self._event.is_set():
            return 0
        return None

    def kill(self):
        self._conn.close()


class UDT:
    def __init__(self, device: adbutils.AdbDevice):
        self._device = device
        self._lport = None
        self._process = None
        self._lock = threading.Lock()
        self._session_id = None
        atexit.register(self.release)

    def get_session_id(self) -> str:
        if self._session_id:
            return self._session_id
        self._session_id = self._new_session()
        logger.debug("update waitForIdleTimeout to 0ms")
        self._dev_request("POST", f"/session/{self._session_id}/appium/settings", payload={
            "settings": {
                "waitForIdleTimeout": 10,
                "waitForSelectorTimeout": 10,
                "actionAcknowledgmentTimeout": 10,
                "scrollAcknowledgmentTimeout": 10,
                "trackScrollEvents": False,
            }
        })
        result = self._dev_request("GET", f"/session/{self._session_id}/appium/settings")
        return self._session_id
    
    def dev_request(self, method: str, path: str, **kwargs) -> AppiumResponse:
        """send http request to device
        :param method: GET, POST, DELETE, PUT
        :param path: url path, path start with @ means with_session=True

        :return: response json
        """
        try:
            if path.startswith("@"):
                path = path[1:]
                kwargs['with_session'] = True
            return self._dev_request(method, path, **kwargs)
        except HTTPError:
            self.launch_server()
            return self._dev_request(method, path, **kwargs)
        except AppiumError as e:
            if e.error == AppiumErrorEnum.InvalidSessionID:
                self._session_id = self._new_session()
                return self._dev_request(method, path, **kwargs)
            raise

    def _dev_request(self, method: str, path: str, payload=None, timeout: float = 10.0, with_session: bool = False) -> AppiumResponse:
        try:
            if with_session:
                sid = self.get_session_id()
                path = f"/session/{sid}{path}"
            url = f"http://localhost:{self._lport}{path}"
            logger.debug("request %s %s", method, url)
            r = requests.request(method, url, json=payload, timeout=timeout)
            response_json = r.json()
            resp = AppiumResponse.model_validate(response_json)
            if isinstance(resp.value, dict):
                value = AppiumResponseValue.model_validate(resp.value)
                if value.error:
                    raise AppiumError(value.error, value.message)
            return resp
        except requests.RequestException as e:
            raise HTTPError(f"{method} to {path!r} error", payload)
        except json.JSONDecodeError as e:
            raise HTTPError("JSON decode error", e.msg)
        
    def _new_session(self) -> str:
        resp = self._dev_request("POST", "/session", payload={"capabilities": {}})
        value = resp.value
        if not isinstance(value, dict) and 'sessionId' not in value:
            raise UDTError("session create failed", resp)
        sid = value['sessionId']
        if not sid:
            raise UDTError("session create failed", resp)
        return sid

    def post(self, path: str, payload=None) -> AppiumResponse:
        return self.dev_request("POST", path, payload=payload)

    def get(self, path: str, ) -> AppiumResponse:
        return self.dev_request("GET", path)

    def _update_process_status(self):
        if self._process:
            if self._process.pool() is not None:
                self._process = None

    def release(self):
        logger.debug("Releasing")
        with self._lock:
            if self._process is not None:
                logger.debug("Killing process")
                self._process.kill()
                self._process.wait()
                self._process = None

    def launch_server(self):
        try:
            self._launch_server()
            self._device.keyevent("WAKEUP")
        except adbutils.AdbError as e:
            raise UDTError("fail to start udt", str(e))
        self._wait_ready()

    def _launch_server(self):
        with self._lock:
            self._update_process_status()
            if self._process:
                logger.debug("Process already running")
                return
            logger.debug("Launching process")
            dex_local_path = Path(__file__).parent.joinpath("appium-uiautomator2-v5.12.4-light.apk")
            logger.debug("dex_local_path: %s", dex_local_path)
            dex_remote_path = "/data/local/tmp/udt/udt-5.12.4-light.dex"
            info = self._device.sync.stat(dex_remote_path)
            if info.size == dex_local_path.stat().st_size:
                logger.debug("%s already exists", dex_remote_path)
            else:
                logger.debug("push dex(%d) to %s", dex_local_path.stat().st_size, dex_remote_path)
                self._device.shell("mkdir -p /data/local/tmp/udt")
                self._device.sync.push(dex_local_path, dex_remote_path, 0o644)
            logger.debug("CLASSPATH=%s app_process / com.wetest.uia2.Main", dex_remote_path)
            conn = self._device.shell(f"CLASSPATH={dex_remote_path} app_process / com.wetest.uia2.Main", stream=True)
            self._process = MockAdbProcess(conn)

            self._lport = self._device.forward_port(6790)
            logger.debug("forward tcp:6790 -> tcp:%d", self._lport)

    def _wait_ready(self):
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                self._dev_request("GET", "/status", timeout=1)
                return
            except HTTPError:
                time.sleep(0.5)
        raise UDTError("Service not ready")

    def dump_hierarchy(self) -> str:
        resp = self.get(f"@/source")
        return resp.value
    
    def status(self):
        return self.get("/status")
    
    def screenshot(self) -> Image.Image:
        resp = self.get(f"@/screenshot")
        raw = b64decode(resp.value)
        return Image.open(io.BytesIO(raw))



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    r = UDT(adbutils.device())
    print(r.status())
    r.dump_hierarchy()
