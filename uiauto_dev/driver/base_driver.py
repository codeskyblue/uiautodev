#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:18:30 by codeskyblue
"""
import abc
import enum
from typing import Tuple

from PIL import Image
from pydantic import BaseModel

from uiauto_dev.command_types import CurrentAppResponse
from uiauto_dev.model import Node, ShellResponse, WindowSize


class BaseDriver(abc.ABC):
    def __init__(self, serial: str):
        self.serial = serial

    @abc.abstractmethod
    def screenshot(self, id: int) -> Image.Image:
        """Take a screenshot of the device
        :param id: physical display ID to capture (normally: 0)
        :return: PIL.Image.Image
        """
        raise NotImplementedError()
    
    @abc.abstractmethod
    def dump_hierarchy(self) -> Tuple[str, Node]:
        """Dump the view hierarchy of the device
        :return: xml_source, Hierarchy
        """
        raise NotImplementedError()
    
    def shell(self, command: str) -> ShellResponse:
        """Run a shell command on the device
        :param command: shell command
        :return: ShellResponse
        """
        raise NotImplementedError()
    
    def tap(self, x: int, y: int):
        """Tap on the screen
        :param x: x coordinate
        :param y: y coordinate
        """
        raise NotImplementedError()

    def window_size(self) -> WindowSize:
        """ get window UI size """
        raise NotImplementedError()

    def app_install(self, app_path: str):
        """ install app """
        raise NotImplementedError()
    
    def app_current(self) -> CurrentAppResponse:
        """ get current app """
        raise NotImplementedError()
    
    def app_launch(self, package: str):
        """ launch app """
        raise NotImplementedError()
    
    def app_terminate(self, package: str):
        """ terminate app """
        raise NotImplementedError()
    
    def home(self):
        """ press home button """
        raise NotImplementedError()

    def wake_up(self):
        """ wake up the device """
        raise NotImplementedError()