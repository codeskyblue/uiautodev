#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 13:48:55 by codeskyblue
"""

import os
import platform
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from appinspector.provider import AndroidProvider, IOSProvider
from appinspector.router.device import make_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

android_router = make_router(AndroidProvider())
app.include_router(android_router, prefix="/api/android", tags=["android"])

ios_router = make_router(IOSProvider())
app.include_router(ios_router, prefix="/api/ios", tags=["ios"])

class InfoResponse(BaseModel):
    version: str
    description: str
    platform: str
    code_language: str


@app.get("/api/info")
def info() -> InfoResponse:
    """Information about the application"""
    return InfoResponse(
        version="0.0.1",
        description="This is a simple FastAPI application",
        platform=platform.system(),  # Linux | Darwin | Windows
        code_language="Python",
        cwd=os.getcwd(),
    )


@app.get("/demo")
def demo() -> str:
    """Demo endpoint"""
    static_dir = Path(__file__).parent / "static"
    print(static_dir / "demo.html")
    return FileResponse(static_dir / "demo.html")


def run_server():
    import uvicorn
    uvicorn.run("appinspector.app:app", host="0.0.0.0", port=20242)