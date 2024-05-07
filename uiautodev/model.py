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
    name: str = ""
    status: str = ""
    enabled: bool = True


class ShellResponse(BaseModel):
    output: str
    error: Optional[str] = ""


class Node(BaseModel):
    key: str
    name: str
    bounds: Optional[Tuple[float, float, float, float]] = None
    properties: Dict[str, Union[str, bool]] = []
    children: List[Node] = []


class WindowSize(typing.NamedTuple):
    width: int
    height: int