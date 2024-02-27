#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 13:48:55 by codeskyblue
"""

import os
from pathlib import Path
import platform

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from appinspector.router.android import router as android_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(android_router, prefix="/api/android", tags=["android"])


class InfoResponse(BaseModel):
    version: str
    description: str
    platform: str
    code_language: str


@app.get("/info")
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
