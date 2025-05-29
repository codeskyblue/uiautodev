#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 13:48:55 by codeskyblue
"""

import logging
import os
import platform
import signal
from pathlib import Path
from typing import Dict, List

import adbutils
import uvicorn
from fastapi import FastAPI, File, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from rich.logging import RichHandler
from starlette.websockets import WebSocketDisconnect

from uiautodev import __version__
from uiautodev.common import convert_bytes_to_image, get_webpage_url, ocr_image
from uiautodev.model import Node
from uiautodev.provider import AndroidProvider, HarmonyProvider, IOSProvider, MockProvider
from uiautodev.remote.scrcpy import ScrcpyServer
from uiautodev.router.android import router as android_device_router
from uiautodev.router.device import make_router
from uiautodev.router.xml import router as xml_router
from uiautodev.utils.envutils import Environment

logger = logging.getLogger(__name__)

app = FastAPI()


def enable_logger_to_console():
    _logger = logging.getLogger("uiautodev")
    _logger.setLevel(logging.DEBUG)
    _logger.addHandler(RichHandler(enable_link_path=False))


if os.getenv("UIAUTODEV_DEBUG"):
    enable_logger_to_console()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

android_router = make_router(AndroidProvider())
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
    app.include_router(ios_router, prefix="/api/ios", tags=["ios"])
    app.include_router(harmony_router, prefix="/api/harmony", tags=["harmony"])

app.include_router(xml_router, prefix="/api/xml", tags=["xml"])
app.include_router(android_device_router, prefix="/api/android", tags=["android"])


@app.get('/api/{platform}/features')
def get_features(platform: str) -> Dict[str, bool]:
    """Get features supported by the specified platform"""
    features = {}
    # 获取所有带有指定平台tag的路由
    for route in app.routes:
        if hasattr(route, 'tags') and platform in route.tags:
            if route.path.startswith(f"/api/{platform}/{{serial}}/"):
                # 提取特性名称
                parts = route.path.split('/')
                feature_name = parts[-1]
                if not feature_name.startswith('{'):
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


@app.post('/api/ocr_image')
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


@app.get("/")
def index_redirect():
    """ redirect to official homepage """
    url = get_webpage_url()
    logger.debug("redirect to %s", url)
    return RedirectResponse(url)


def get_scrcpy_server(serial: str):
    # 这里主要是为了避免两次websocket建立建立，启动两个scrcpy进程
    logger.info("create scrcpy server for %s", serial)
    device = adbutils.device(serial)
    return ScrcpyServer(device)


@app.websocket("/ws/android/scrcpy/{serial}")
async def unified_ws(websocket: WebSocket, serial: str):
    """
    Args:
        serial: device serial
        websocket: WebSocket
    """
    await websocket.accept()

    try:
        logger.info(f"WebSocket serial: {serial}")

        # 获取 ScrcpyServer 实例
        server = get_scrcpy_server(serial)
        await server.handle_unified_websocket(websocket, serial)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client.")
    except Exception as e:
        logger.exception(f"WebSocket error for serial={serial}: {e}")
        await websocket.close(code=1000, reason=str(e))
    finally:
        logger.info(f"WebSocket closed for serial={serial}")


if __name__ == '__main__':
    uvicorn.run("uiautodev.app:app", port=4000, reload=True, use_colors=True)
