#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 11:12:33 by codeskyblue
"""
from __future__ import annotations

import typing
from typing import Dict, List, Optional, Tuple, Union

from pydantic import BaseModel


class DeviceInfo(BaseModel):
    serial: str
    model: str = ""
    product: str = ""
    name: str = ""
    status: str = ""
    enabled: bool = True


class ShellResponse(BaseModel):
    output: str
    error: Optional[str] = ""


class Rect(BaseModel):
    x: int
    y: int
    width: int
    height: int


class Node(BaseModel):
    key: str
    name: str  # can be seen as description
    bounds: Optional[Tuple[float, float, float, float]] = None
    rect: Optional[Rect] = None
    properties: Dict[str, Union[str, bool]] = {}
    children: List[Node] = []


class OCRNode(Node):
    confidence: float


class WindowSize(typing.NamedTuple):
    width: int
    height: int


class AppInfo(BaseModel):
    packageName: str
    versionName: Optional[str] = None  # Allow None values
    versionCode: Optional[int] = None
