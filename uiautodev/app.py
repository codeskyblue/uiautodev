#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 13:48:55 by codeskyblue"""

import logging
import os
import platform
import signal
from pathlib import Path
from typing import Dict, List

import adbutils
import httpx
import uvicorn
from fastapi import FastAPI, File, Request, Response, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from uiautodev import __version__
from uiautodev.common import convert_bytes_to_image, get_webpage_url, ocr_image
from uiautodev.driver.android import ADBAndroidDriver, U2AndroidDriver
from uiautodev.model import Node
from uiautodev.provider import AndroidProvider, HarmonyProvider, IOSProvider, MockProvider
from uiautodev.remote.scrcpy import ScrcpyServer
from uiautodev.router.android import router as android_device_router
from uiautodev.router.device import make_router
from uiautodev.router.proxy import make_reverse_proxy
from uiautodev.router.proxy import router as proxy_router
from uiautodev.router.record import router as record_router
from uiautodev.router.xml import router as xml_router
from uiautodev.utils.envutils import Environment

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["*"],
)

android_default_driver = U2AndroidDriver
if os.getenv("UIAUTODEV_USE_ADB_DRIVER") in ("1", "true", "True"):
    android_default_driver = ADBAndroidDriver

android_router = make_router(AndroidProvider(driver_class=android_default_driver))
android_adb_router = make_router(AndroidProvider(driver_class=ADBAndroidDriver))
ios_router = make_router(IOSProvider())
harmony_router = make_router(HarmonyProvider())
mock_router = make_router(MockProvider())

app.include_router(mock_router, prefix="/api/mock", tags=["mock"])

if Environment.UIAUTODEV_MOCK:
    app.include_router(mock_router, prefix="/api/android", tags=["mock"])
    app.include_router(mock_router, prefix="/api/ios", tags=["mock"])
    app.include_router(mock_router, prefix="/api/harmony", tags=["mock"])
else:
    app.include_router(android_router, prefix="/api/android", tags=["android"])
    app.include_router(android_adb_router, prefix="/api/android_adb", tags=["android_adb"])
    app.include_router(ios_router, prefix="/api/ios", tags=["ios"])
    app.include_router(harmony_router, prefix="/api/harmony", tags=["harmony"])

app.include_router(xml_router, prefix="/api/xml", tags=["xml"])
app.include_router(android_device_router, prefix="/api/android", tags=["android"])
app.include_router(proxy_router, tags=["proxy"])
app.include_router(record_router, prefix="/api/record", tags=["record"])


@app.get("/api/{platform}/features")
def get_features(platform: str) -> Dict[str, bool]:
    """Get features supported by the specified platform"""
    features = {}
    # 获取所有带有指定平台tag的路由
    from starlette.routing import Route

    for route in app.routes:
        _route: Route = route  # type: ignore
        if hasattr(_route, "tags") and platform in _route.tags:
            if _route.path.startswith(f"/api/{platform}/{{serial}}/"):
                # 提取特性名称
                parts = _route.path.split("/")
                feature_name = parts[-1]
                if not feature_name.startswith("{"):
                    features[feature_name] = True
    return features


class InfoResponse(BaseModel):
    version: str
    description: str
    platform: str
    code_language: str
    cwd: str
    drivers: List[str]


@app.get("/api/info")
def info() -> InfoResponse:
    """Information about the application"""
    return InfoResponse(
        version=__version__,
        description="client for https://uiauto.dev",
        platform=platform.system(),  # Linux | Darwin | Windows
        code_language="Python",
        cwd=os.getcwd(),
        drivers=["android", "ios", "harmony"],
    )


@app.post("/api/ocr_image")
async def _ocr_image(file: UploadFile = File(...)) -> List[Node]:
    """OCR an image"""
    image_data = await file.read()
    image = convert_bytes_to_image(image_data)
    return ocr_image(image)


@app.get("/shutdown")
def shutdown() -> str:
    """Shutdown the server"""
    os.kill(os.getpid(), signal.SIGINT)
    return "Server shutting down..."


@app.get("/demo")
def demo():
    """Demo endpoint"""
    static_dir = Path(__file__).parent / "static"
    print(static_dir / "demo.html")
    return FileResponse(static_dir / "demo.html")


@app.get("/redirect")
def index_redirect():
    """redirect to official homepage"""
    url = get_webpage_url()
    logger.debug("redirect to %s", url)
    return RedirectResponse(url)


@app.get("/api/auth/me")
def mock_auth_me():
    # 401 {"detail":"Authentication required"}
    return JSONResponse(status_code=401, content={"detail": "Authentication required"})

@app.websocket('/ws/android/scrcpy3/{serial}')
async def handle_android_scrcpy3_ws(websocket: WebSocket, serial: str):
    await websocket.accept()
    try:
        logger.info(f"WebSocket serial: {serial}")
        device = adbutils.device(serial)
        from uiautodev.remote.scrcpy3 import ScrcpyServer3
        scrcpy = ScrcpyServer3(device)
        try:
            await scrcpy.stream_to_websocket(websocket)
        finally:
            scrcpy.close()
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client.")
    except Exception as e:
        logger.exception(f"WebSocket error for serial={serial}: {e}")
        reason = str(e).replace("\n", " ")
        await websocket.close(code=1000, reason=reason)
    finally:
        logger.info(f"WebSocket closed for serial={serial}")

@app.websocket("/ws/android/scrcpy/{serial}")
async def handle_android_ws(websocket: WebSocket, serial: str):
    """
    Args:
        serial: device serial
        websocket: WebSocket
    """
    scrcpy_version = websocket.query_params.get("version", "2.7")
    await websocket.accept()

    try:
        logger.info(f"WebSocket serial: {serial}")
        device = adbutils.device(serial)
        server = ScrcpyServer(device, version=scrcpy_version)
        await server.handle_unified_websocket(websocket, serial)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client.")
    except Exception as e:
        logger.exception(f"WebSocket error for serial={serial}: {e}")
        await websocket.close(code=1000, reason=str(e))
    finally:
        logger.info(f"WebSocket closed for serial={serial}")


def get_harmony_mjpeg_server(serial: str):
    from hypium import UiDriver

    from uiautodev.remote.harmony_mjpeg import HarmonyMjpegServer

    driver = UiDriver.connect(device_sn=serial)
    logger.info("create harmony mjpeg server for %s", serial)
    logger.info(f"device wake_up_display: {driver.wake_up_display()}")
    return HarmonyMjpegServer(driver)


@app.websocket("/ws/harmony/mjpeg/{serial}")
async def unified_harmony_ws(websocket: WebSocket, serial: str):
    """
    Args:
        serial: device serial
        websocket: WebSocket
    """
    await websocket.accept()

    try:
        logger.info(f"WebSocket serial: {serial}")

        # 获取 HarmonyScrcpyServer 实例
        server = get_harmony_mjpeg_server(serial)
        server.start()
        await server.handle_ws(websocket)
    except ImportError as e:
        logger.error(f"missing library for harmony: {e}")
        await websocket.close(
            code=1000, reason='missing library, fix by "pip install uiautodev[harmony]"'
        )
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client.")
    except Exception as e:
        logger.exception(f"WebSocket error for serial={serial}: {e}")
        await websocket.close(code=1000, reason=str(e))
    finally:
        logger.info(f"WebSocket closed for serial={serial}")


if __name__ == "__main__":
    uvicorn.run("uiautodev.app:app", port=4000, reload=True, use_colors=True)
