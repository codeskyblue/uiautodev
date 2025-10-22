#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:19:29 by codeskyblue
"""

import logging
import re
import time
from functools import cached_property, partial
from typing import Iterator, List, Optional, Tuple
from xml.etree import ElementTree

import adbutils
import uiautomator2 as u2
from PIL import Image

from uiautodev.command_types import CurrentAppResponse
from uiautodev.driver.base_driver import BaseDriver
from uiautodev.exceptions import AndroidDriverException, RequestError
from uiautodev.model import AppInfo, Node, Rect, ShellResponse, WindowSize
from uiautodev.utils.common import fetch_through_socket
from uiautodev.driver.android.adb_driver import ADBAndroidDriver, parse_xml


logger = logging.getLogger(__name__)

class U2AndroidDriver(ADBAndroidDriver):
    def __init__(self, serial: str):
        super().__init__(serial)

    @cached_property
    def ud(self) -> u2.Device:
        return u2.connect_usb(self.serial)
    
    def screenshot(self, id: int) -> Image.Image:
        if id > 0:
            # u2 is not support multi-display yet
            return super().screenshot(id)
        return self.ud.screenshot()

    def dump_hierarchy(self, display_id: Optional[int] = 0) -> Tuple[str, Node]:
        """returns xml string and hierarchy object"""
        start = time.time()
        xml_data = self._dump_hierarchy_raw()
        logger.debug("dump_hierarchy cost: %s", time.time() - start)

        wsize = self.adb_device.window_size()
        logger.debug("window size: %s", wsize)
        return xml_data, parse_xml(
            xml_data, WindowSize(width=wsize[0], height=wsize[1]), display_id
        )

    def _dump_hierarchy_raw(self) -> str:
        """
        uiautomator2 server is conflict with "uiautomator dump" command.

        uiautomator dump errors:
        - ERROR: could not get idle state.
        """
        try:
            return self.ud.dump_hierarchy()
        except Exception as e:
            raise AndroidDriverException(f"Failed to dump hierarchy: {str(e)}")
    
    def tap(self, x: int, y: int):
        self.ud.click(x, y)
    
    def send_keys(self, text: str):
        self.ud.send_keys(text)
    
    def clear_text(self):
        self.ud.clear_text()