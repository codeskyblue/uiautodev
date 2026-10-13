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


# Recording related models
class Selector(BaseModel):
    """Element selector for recording"""
    id: Optional[str] = None  # resource-id
    text: Optional[str] = None
    className: Optional[str] = None
    xpath: Optional[str] = None
    contentDesc: Optional[str] = None  # content-desc / accessibilityLabel


class RecordEvent(BaseModel):
    """Recording event model"""
    action: str  # tap, long_press, input, swipe, scroll, back, home, etc.
    selector: Optional[Selector] = None
    value: Optional[str] = None  # for input action
    timestamp: Optional[float] = None
    x: Optional[float] = None  # for coordinate-based actions
    y: Optional[float] = None
    x1: Optional[float] = None  # for swipe actions
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    duration: Optional[float] = None  # for long_press, swipe duration


class RecordScript(BaseModel):
    """Recorded script model"""
    id: Optional[str] = None
    name: str
    platform: str  # android, ios, harmony
    deviceSerial: Optional[str] = None
    appPackage: Optional[str] = None
    appActivity: Optional[str] = None
    events: List[RecordEvent] = []
    createdAt: Optional[float] = None
    updatedAt: Optional[float] = None
    scriptType: str = "appium_python"  # appium_python, appium_js, uiautomator2, xcuitest


class SaveScriptRequest(BaseModel):
    """Request model for saving script"""
    name: str
    platform: str
    deviceSerial: Optional[str] = None
    appPackage: Optional[str] = None
    appActivity: Optional[str] = None
    events: List[RecordEvent]
    scriptType: str = "appium_python"


class SaveScriptResponse(BaseModel):
    """Response model for saving script"""
    id: str
    success: bool
    message: str
