#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:35:46 by codeskyblue
"""


import json
from functools import partial
from typing import List, Optional, Tuple
from xml.etree import ElementTree

import wdapy
from PIL import Image

from uiautodev.command_types import CurrentAppResponse
from uiautodev.driver.base_driver import BaseDriver
from uiautodev.exceptions import IOSDriverException
from uiautodev.model import Node, WindowSize
from uiautodev.utils.usbmux import select_device


class IOSDriver(BaseDriver):
    def __init__(self, serial: str):
        """ serial is the udid of the ios device """
        super().__init__(serial)
        self.device = select_device(serial)
        self.wda = wdapy.AppiumUSBClient(self.device.serial)
    
    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> bytes:
        conn = self.device.make_http_connection(port=8100)
        try:
            if payload is None:
                conn.request(method, path)
            else:
                conn.request(method, path, body=json.dumps(payload), headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            if response.getcode() != 200:
                raise IOSDriverException(f"Failed request to device, status: {response.getcode()}")
            content = bytearray()
            while chunk := response.read(4096):
                content.extend(chunk)
            return content
        finally:
            conn.close()
    
    def _request_json(self, method: str, path: str) -> dict:
        content = self._request(method, path)
        return json.loads(content)

    def _request_json_value(self, method: str, path: str) -> dict:
        return self._request_json(method, path)["value"]
    
    def status(self):
        return self._request_json("GET", "/status")
    
    def screenshot(self, id: int = 0) -> Image.Image:
        return self.wda.screenshot()
    
    def window_size(self):
        return self.wda.window_size()
    
    def dump_hierarchy(self) -> Tuple[str, Node]:
        """returns xml string and hierarchy object"""
        t = self.wda.sourcetree()
        xml_data = t.value
        root = ElementTree.fromstring(xml_data)
        return xml_data, parse_xml_element(root, WindowSize(width=1, height=1))
    
    def tap(self, x: int, y: int):
        self.wda.tap(x, y)
    
    def app_current(self) -> CurrentAppResponse:
        info = self.wda.app_current()
        return CurrentAppResponse(package=info.bundle_id, pid=info.pid)

    def home(self):
        self.wda.homescreen()
    
    def app_switch(self):
        raise NotImplementedError()

    def volume_up(self):
        self.wda.volume_up()
    
    def volume_down(self):
        self.wda.volume_down()
        

def parse_xml_element(element, wsize: WindowSize, indexes: List[int]=[0]) -> Node:
    """
    Recursively parse an XML element into a dictionary format.
    # <XCUIElementTypeApplication type="XCUIElementTypeApplication" name="设置" label="设置" enabled="true" visible="true" accessible="false" x="0" y="0" width="414" height="896" index="0">
    """
    if element.attrib.get("visible") == "false":
        return None
    if element.tag == "XCUIElementTypeApplication":
        wsize = WindowSize(width=int(element.attrib["width"]), height=int(element.attrib["height"]))
    x = int(element.attrib.get("x", 0))
    y = int(element.attrib.get("y", 0))
    width = int(element.attrib.get("width", 0))
    height = int(element.attrib.get("height", 0))
    bounds = (x / wsize.width, y / wsize.height, (x + width) / wsize.width, (y + height) / wsize.height)
    bounds = list(map(partial(round, ndigits=4), bounds))
    name = element.attrib.get("type", "XCUIElementTypeUnknown")
    
    elem = Node(
        key='-'.join(map(str, indexes)),
        name=name,
        bounds=bounds,
        properties={key: element.attrib[key] for key in element.attrib},
        children=[],
    )
    for index, child in enumerate(element):
        child_elem = parse_xml_element(child, wsize, indexes+[index])
        if child_elem:
            elem.children.append(child_elem)
    return elem

    