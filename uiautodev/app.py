#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 13:48:55 by codeskyblue
"""

import logging
import os
import platform
import signal
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from uiautodev import __version__
from uiautodev.provider import AndroidProvider, IOSProvider, MockProvider
from uiautodev.router.device import make_router
from uiautodev.router.xml import router as xml_router

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

android_router = make_router(AndroidProvider())
ios_router = make_router(IOSProvider())
mock_router = make_router(MockProvider())

app.include_router(mock_router, prefix="/api/mock", tags=["mock"])

if os.environ.get("UIAUTODEV_MOCK"):
    app.include_router(mock_router, prefix="/api/android", tags=["mock"])
    app.include_router(mock_router, prefix="/api/ios", tags=["mock"])
else:
    app.include_router(android_router, prefix="/api/android", tags=["android"])
    app.include_router(ios_router, prefix="/api/ios", tags=["ios"])

app.include_router(xml_router, prefix="/api/xml", tags=["xml"])


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
        drivers=["android"],
    )


@app.get("/shutdown")
def shutdown() -> str:
    """Shutdown the server"""
    os.kill(os.getpid(), signal.SIGINT)
    return "Server shutting down..."


@app.get("/demo")
def demo() -> str:
    """Demo endpoint"""
    static_dir = Path(__file__).parent / "static"
    print(static_dir / "demo.html")
    return FileResponse(static_dir / "demo.html")


@app.get("/")
def index_redirect():
    """ redirect to official homepage """
    return RedirectResponse("https://uiauto.dev")
