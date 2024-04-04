#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 10:43:51 by codeskyblue
"""

from __future__ import annotations

import typing
from typing import Callable, Dict, Optional

from pydantic import BaseModel

from uiauto_dev.command_types import Command, CurrentAppResponse, DumpResponse, InstallAppRequest, InstallAppResponse, \
    TapRequest, WindowSizeResponse
from uiauto_dev.driver.base_driver import BaseDriver

COMMANDS: Dict[Command, Callable] = {}


def register(command: Command):
    def wrapper(func):
        COMMANDS[command] = func
        return func

    return wrapper


def get_command_params_type(command: Command) -> Optional[BaseModel]:
    func = COMMANDS.get(command)
    if func is None:
        return None
    type_hints = typing.get_type_hints(func)
    return type_hints.get("params")


def send_command(driver: BaseDriver, command: Command, params=None):
    if command not in COMMANDS:
        raise NotImplementedError(f"command {command} not implemented")
    func = COMMANDS[command]
    type_hints = typing.get_type_hints(func)
    if type_hints.get("params"):
        if params is None:
            raise ValueError(f"params is required for {command}")
        if not isinstance(params, type_hints["params"]):
            raise TypeError(f"params should be {type_hints['params']}")
    if params is None:
        return func(driver)
    return func(driver, params)


@register(Command.TAP)
def tap(driver: BaseDriver, params: TapRequest):
    """Tap on the screen
    :param x: x coordinate
    :param y: y coordinate
    """
    x = params.x
    y = params.y
    if params.isPercent:
        wsize = driver.window_size()
        x = int(wsize[0] * params.x)
        y = int(wsize[1] * params.y)
    driver.tap(x, y)


@register(Command.INSTALL_APP)
def install_app(driver: BaseDriver, params: InstallAppRequest):
    """install app"""
    driver.app_install(params.url)
    return InstallAppResponse(success=True, id=None)


@register(Command.CURRENT_APP)
def current_app(driver: BaseDriver) -> CurrentAppResponse:
    """get current app"""
    return driver.app_current()


@register(Command.GET_WINDOW_SIZE)
def window_size(driver: BaseDriver) -> WindowSizeResponse:
    wsize = driver.window_size()
    return WindowSizeResponse(width=wsize[0], height=wsize[1])


@register(Command.HOME)
def home(driver: BaseDriver):
    driver.home()


@register(Command.DUMP)
def dump(driver: BaseDriver) -> DumpResponse:
    source, _ = driver.dump_hierarchy()
    return DumpResponse(value=source)


@register(Command.WAKE_UP)
def wake_up(driver: BaseDriver):
    driver.wake_up()