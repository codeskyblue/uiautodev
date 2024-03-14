#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 13:48:55 by codeskyblue
"""

import os
import platform
import signal
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from appinspector import __version__
from appinspector.provider import AndroidProvider, IOSProvider, MockProvider
from appinspector.router.device import make_router
from appinspector.router.xml import router as xml_router

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

if os.environ.get("APPINSPECTOR_MOCK"):
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
        description="client for appinspector.devsleep.com",
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
    """ redirect to appinspector.devsleep.com """
    return RedirectResponse("https://appinspector.devsleep.com")


def run_server():
    import argparse

    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=20242)
    parser.add_argument("--mock", action="store_true", help="Run with mock driver")
    parser.add_argument("--reload", action="store_true", help="Run with auto reload")
    args = parser.parse_args()

    if args.mock:
        os.environ["APPINSPECTOR_MOCK"] = "1"

    uvicorn.run("appinspector.app:app", host="127.0.0.1", port=args.port, reload=args.reload)