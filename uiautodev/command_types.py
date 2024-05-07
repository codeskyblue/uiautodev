#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 10:19:27 by codeskyblue
"""


# Request and Response
import enum
from typing import List, Optional, Union

from pydantic import BaseModel

from uiautodev.model import Node


# POST /api/v1/device/{serial}/command/{command}
class Command(str, enum.Enum):
    TAP = "tap"
    TAP_ELEMENT = "tapElement"
    APP_INSTALL = "installApp"
    APP_CURRENT = "currentApp"
    APP_LAUNCH = "appLaunch"
    APP_TERMINATE = "appTerminate"

    GET_WINDOW_SIZE = "getWindowSize"
    HOME = "home"
    DUMP = "dump"
    WAKE_UP = "wakeUp"
    FIND_ELEMENTS = "findElements"
    CLICK_ELEMENT = "clickElement"

    LIST = "list"


class TapRequest(BaseModel):
    x: Union[int, float]
    y: Union[int, float]
    isPercent: bool = False


class InstallAppRequest(BaseModel):
    url: str


class InstallAppResponse(BaseModel):
    success: bool
    id: Optional[str] = None


class CurrentAppResponse(BaseModel):
    package: str
    activity: Optional[str] = None
    pid: Optional[int] = None


class AppLaunchRequest(BaseModel):
    package: str
    stop: bool = False


class AppTerminateRequest(BaseModel):
    package: str


class WindowSizeResponse(BaseModel):
    width: int
    height: int


class DumpResponse(BaseModel):
    value: str


class By(str, enum.Enum):
    ID = "id"
    TEXT = "text"
    XPATH = "xpath"
    CLASS_NAME = "className"

class FindElementRequest(BaseModel):
    by: str
    value: str
    timeout: float = 10.0


class FindElementResponse(BaseModel):
    count: int
    value: List[Node]