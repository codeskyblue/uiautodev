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

logger = logging.getLogger(__name__)

class AndroidDriver(BaseDriver):
    def __init__(self, serial: str):
        super().__init__(serial)
        self.adb_device = adbutils.device(serial)

    @cached_property
    def ud(self) -> u2.Device:
        return u2.connect_usb(self.serial)
    
    def screenshot(self, id: int) -> Image.Image:
        if id > 0:
            raise AndroidDriverException("multi-display is not supported yet for uiautomator2")
        return self.ud.screenshot()

    def shell(self, command: str) -> ShellResponse:
        try:
            ret = self.adb_device.shell2(command, rstrip=True, timeout=20)
            if ret.returncode == 0:
                return ShellResponse(output=ret.output, error=None)
            else:
                return ShellResponse(
                    output="", error=f"exit:{ret.returncode}, output:{ret.output}"
                )
        except Exception as e:
            return ShellResponse(output="", error=f"adb error: {str(e)}")

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
            logger.exception("unexpected dump error: %s", e)
            raise AndroidDriverException("Failed to dump hierarchy")
    
    def tap(self, x: int, y: int):
        self.adb_device.click(x, y)

    def window_size(self) -> Tuple[int, int]:
        w, h = self.adb_device.window_size()
        return (w, h)

    def app_install(self, app_path: str):
        self.adb_device.install(app_path)

    def app_current(self) -> CurrentAppResponse:
        info = self.adb_device.app_current()
        return CurrentAppResponse(
            package=info.package, activity=info.activity, pid=info.pid
        )

    def app_launch(self, package: str):
        if self.adb_device.package_info(package) is None:
            raise AndroidDriverException(f"App not installed: {package}")
        self.adb_device.app_start(package)
    
    def app_terminate(self, package: str):
        self.adb_device.app_stop(package)

    def home(self):
        self.adb_device.keyevent("HOME")
    
    def wake_up(self):
        self.adb_device.keyevent("WAKEUP")
    
    def back(self):
        self.adb_device.keyevent("BACK")
    
    def app_switch(self):
        self.adb_device.keyevent("APP_SWITCH")
    
    def volume_up(self):
        self.adb_device.keyevent("VOLUME_UP")
    
    def volume_down(self):
        self.adb_device.keyevent("VOLUME_DOWN")
    
    def volume_mute(self):
        self.adb_device.keyevent("VOLUME_MUTE")
    
    def app_list(self) -> List[AppInfo]:
        results = []
        output = self.adb_device.shell(["pm", "list", "packages", '-3'])
        for m in re.finditer(r"^package:([^\s]+)\r?$", output, re.M):
            packageName = m.group(1)
            results.append(AppInfo(packageName=packageName))
        return results

    def open_app_file(self, package: str) -> Iterator[bytes]:
        line = self.adb_device.shell(f"pm path {package}")
        if not line.startswith("package:"):
            raise AndroidDriverException(f"Failed to get package path: {line}")
        remote_path = line.split(':', 1)[1]
        yield from self.adb_device.sync.iter_content(remote_path)



def parse_xml(xml_data: str, wsize: WindowSize, display_id: Optional[int] = None) -> Node:
    root = ElementTree.fromstring(xml_data)
    node = parse_xml_element(root, wsize, display_id)
    if node is None:
        raise AndroidDriverException("Failed to parse xml")
    return node


def parse_xml_element(element, wsize: WindowSize, display_id: Optional[int], indexes: List[int] = [0]) -> Optional[Node]:
    """
    Recursively parse an XML element into a dictionary format.
    """
    name = element.tag
    if name == "node":
        name = element.attrib.get("class", "node")
    if display_id is not None:
        elem_display_id = int(element.attrib.get("display-id", display_id))
        if elem_display_id != display_id:
            return

    bounds = None
    rect = None
    # eg: bounds="[883,2222][1008,2265]"
    if "bounds" in element.attrib:
        bounds = element.attrib["bounds"]
        bounds = list(map(int, re.findall(r"\d+", bounds)))
        assert len(bounds) == 4
        rect = Rect(x=bounds[0], y=bounds[1], width=bounds[2] - bounds[0], height=bounds[3] - bounds[1])
        bounds = (
            bounds[0] / wsize.width,
            bounds[1] / wsize.height,
            bounds[2] / wsize.width,
            bounds[3] / wsize.height,
        )
        bounds = map(partial(round, ndigits=4), bounds)
        
    elem = Node(
        key="-".join(map(str, indexes)),
        name=name,
        bounds=bounds,
        rect=rect,
        properties={key: element.attrib[key] for key in element.attrib},
        children=[],
    )

    # Construct xpath for children
    for index, child in enumerate(element):
        child_node = parse_xml_element(child, wsize, display_id, indexes + [index])
        if child_node:
            elem.children.append(child_node)

    return elem
