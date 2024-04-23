#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 10:43:51 by codeskyblue
"""

from __future__ import annotations

import time
import typing
from typing import Callable, Dict, Optional

from pydantic import BaseModel

from uiauto_dev.command_types import AppLaunchRequest, AppTerminateRequest, By, Command, CurrentAppResponse, \
    DumpResponse, FindElementRequest, FindElementResponse, InstallAppRequest, InstallAppResponse, TapRequest, \
    WindowSizeResponse
from uiauto_dev.driver.base_driver import BaseDriver
from uiauto_dev.exceptions import ElementNotFoundError
from uiauto_dev.model import Node
from uiauto_dev.utils.common import node_travel

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


@register(Command.APP_INSTALL)
def app_install(driver: BaseDriver, params: InstallAppRequest):
    """install app"""
    driver.app_install(params.url)
    return InstallAppResponse(success=True, id=None)


@register(Command.APP_CURRENT)
def app_current(driver: BaseDriver) -> CurrentAppResponse:
    """get current app"""
    return driver.app_current()


@register(Command.APP_LAUNCH)
def app_launch(driver: BaseDriver, params: AppLaunchRequest):
    if params.stop:
        driver.app_terminate(params.package)
    driver.app_launch(params.package)


@register(Command.APP_TERMINATE)
def app_terminate(driver: BaseDriver, params: AppTerminateRequest):
    driver.app_terminate(params.package)


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


def node_match(node: Node, by: By, value: str) -> bool:
    if by == By.ID:
        return node.properties.get("resource-id") == value
    if by == By.TEXT:
        return node.properties.get("text") == value
    if by == By.CLASS_NAME:
        return node.name == value
    raise ValueError(f"not support by {by!r}")


@register(Command.FIND_ELEMENTS)
def find_elements(driver: BaseDriver, params: FindElementRequest) -> FindElementResponse:
    _, root_node = driver.dump_hierarchy()
    # TODO: support By.XPATH
    nodes = []
    for node in node_travel(root_node):
        if node_match(node, params.by, params.value):
            nodes.append(node)
    return FindElementResponse(count=len(nodes), value=nodes)


@register(Command.CLICK_ELEMENT)
def click_element(driver: BaseDriver, params: FindElementRequest):
    node = None
    deadline = time.time() + params.timeout
    while time.time() < deadline:
        result = find_elements(driver, params)
        if result.value:
            node = result.value[0]
            break
        time.sleep(.5) # interval
    if not node:
        raise ElementNotFoundError(f"element not found by {params.by}={params.value}")
    center_x = (node.bounds[0] + node.bounds[2]) / 2
    center_y = (node.bounds[1] + node.bounds[3]) / 2
    tap(driver, TapRequest(x=center_x, y=center_y, isPercent=True))
