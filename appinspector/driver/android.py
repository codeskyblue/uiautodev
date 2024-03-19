#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:19:29 by codeskyblue
"""

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
        xml_data = self._dump_hierarchy_raw()
        return xml_data, parse_xml(xml_data, WindowSize(width=wsize[0], height=wsize[1]))
    
    def _dump_hierarchy_raw(self) -> str:
        """ 
        appium.uiautomator2.server.test is conflict with "uiautomator dump" command.
        """
        try:
            return self._get_appium_hierarchy()
        except (requests.RequestException, AndroidDriverException):
            # no appium server started, use uiautomator dump
            return self.device.dump_hierarchy()
    
    def _get_appium_hierarchy(self) -> str:
        
        local_port = None
        for f in self.device.forward_list():
            if f.local.startswith("tcp:") and f.remote == "tcp:6790":
                local_port = int(f.local.split(":")[-1])
        if local_port is None:
            raise AndroidDriverException("appium server not started")
        
        r = requests.get(f"http://127.0.0.1:{local_port}/wd/hub/session/0/source")
        r.raise_for_status()
        return r.json()['value']
    
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
