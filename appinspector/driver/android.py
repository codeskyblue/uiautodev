#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:19:29 by codeskyblue
"""

import json
import re
from functools import partial
from typing import List, Tuple
from xml.etree import ElementTree

import adbutils
import requests
from PIL import Image

from appinspector.command_types import CurrentAppResponse
from appinspector.driver.base import BaseDriver
from appinspector.exceptions import AndroidDriverException
from appinspector.model import Hierarchy, ShellResponse, WindowSize
from appinspector.utils.common import fetch_through_socket


class AndroidDriver(BaseDriver):
    def __init__(self, serial: str):
        super().__init__(serial)
        self.device = adbutils.device(serial)

    def screenshot(self, id: int) -> Image.Image:
        # TODO: support multi-display
        if id > 0:
            raise ValueError("multi-display is not supported yet")
        img = self.device.screenshot()
        return img.convert("RGB")
        # return Image.new("RGB", (100, 100), "gray")

    def shell(self, command: str) -> ShellResponse:
        try:
            ret = self.device.shell2(command, rstrip=True, timeout=20)
            if ret.returncode == 0:
                return ShellResponse(output=ret.output, error=None)
            else:
                return ShellResponse(
                    output="", error=f"exit:{ret.returncode}, output:{ret.output}"
                )
        except Exception as e:
            return ShellResponse(output="", error=f"adb error: {str(e)}")

    def dump_hierarchy(self) -> Tuple[str, Hierarchy]:
        """returns xml string and hierarchy object"""
        wsize = self.device.window_size()
        self.shell("rm -f /sdcard/window_dump.xml")
        xml_data = self._dump_hierarchy_raw()
        return xml_data, parse_xml(xml_data, WindowSize(width=wsize[0], height=wsize[1]))
    
    def _dump_hierarchy_raw(self) -> str:
        """ 
        uiautomator2 server is conflict with "uiautomator dump" command.
        """
        for dump_func in (self._get_u2_hierarchy, self.device.dump_hierarchy, self._get_appium_hierarchy):
            try:
                return dump_func()
            except (requests.RequestException, AndroidDriverException, adbutils.AdbError):
                continue
    
    def _get_appium_hierarchy(self) -> str:
        c = self.device.create_connection(adbutils.Network.TCP, 6790)
        try:
            content = fetch_through_socket(c, "/wd/hub/session/0/source", timeout=10)
            return json.loads(content)['value']
        except adbutils.AdbError as e:
            raise AndroidDriverException(f"Failed to get hierarchy from appium server: {str(e)}")
        finally:
            c.close()
    
    def _get_u2_hierarchy(self) -> str:
        c = self.device.create_connection(adbutils.Network.TCP, 9008)
        try:
            compressed = False
            payload = {"jsonrpc": "2.0", "method": "dumpWindowHierarchy", "params": [compressed], "id": 1}
            content = fetch_through_socket(c, "/jsonrpc/0", method="POST", json=payload, timeout=10)
            return json.loads(content)['result']
        except adbutils.AdbError as e:
            raise AndroidDriverException(f"Failed to get hierarchy from appium server: {str(e)}")
        finally:
            c.close()
    
    def tap(self, x: int, y: int):
        self.device.click(x, y)

    def window_size(self) -> Tuple[int, int]:
        w, h = self.device.window_size()
        return (w, h)

    def app_install(self, app_path: str):
        self.device.install(app_path)
    
    def app_current(self) -> CurrentAppResponse:
        info = self.device.app_current()
        return CurrentAppResponse(
            package=info.package,
            activity=info.activity,
            pid=info.pid)

    def home(self):
        self.device.keyevent("HOME")
        

def parse_xml(xml_data: str, wsize: WindowSize) -> Hierarchy:
    root = ElementTree.fromstring(xml_data)
    return parse_xml_element(root, wsize)


def parse_xml_element(element, wsize: WindowSize, indexes: List[int]=[0]) -> Hierarchy:
    """
    Recursively parse an XML element into a dictionary format.
    """
    name = element.tag
    if name == "node":
        name = element.attrib.get("class", "node")
    bounds = None
    # bounds="[883,2222][1008,2265]"
    if "bounds" in element.attrib:
        bounds = element.attrib["bounds"]
        bounds = list(map(int, re.findall(r"\d+", bounds)))
        assert len(bounds) == 4
        bounds = (
            bounds[0] / wsize.width,
            bounds[1] / wsize.height,
            bounds[2] / wsize.width,
            bounds[3] / wsize.height,
        )
        bounds = map(partial(round, ndigits=4), bounds)
    elem = Hierarchy(
        key='-'.join(map(str, indexes)),
        name=name,
        bounds=bounds,
        properties={key: element.attrib[key] for key in element.attrib},
        children=[],
    )

    # Construct xpath for children
    for index, child in enumerate(element):
        elem.children.append(parse_xml_element(child, wsize, indexes+[index]))

    return elem
