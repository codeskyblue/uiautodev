#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 10:19:27 by codeskyblue
"""


# Request and Response
import enum
from typing import Optional, Union
from pydantic import BaseModel


# POST /api/v1/device/{serial}/command/{command}
class Command(str, enum.Enum):
    TAP = "tap"
    TAP_ELEMENT = "tapElement"
    INSTALL_APP = "installApp"
    CURRENT_APP = "currentApp"
    GET_WINDOW_SIZE = "getWindowSize"
    HOME = "home"
    DUMP = "dump"

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


class WindowSizeResponse(BaseModel):
    width: int
    height: int


class DumpResponse(BaseModel):
    value: str