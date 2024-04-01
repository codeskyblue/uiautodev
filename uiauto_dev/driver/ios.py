#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:35:46 by codeskyblue
"""


import base64
import io
import json
import re
from functools import partial
from typing import List, Optional, Tuple
from xml.etree import ElementTree

from PIL import Image

from uiauto_dev.command_types import CurrentAppResponse
from uiauto_dev.driver.base_driver import BaseDriver
from uiauto_dev.exceptions import IOSDriverException
from uiauto_dev.model import Hierarchy, WindowSize
from uiauto_dev.utils.usbmux import MuxDevice, select_device


class IOSDriver(BaseDriver):
    def __init__(self, serial: str):
        """ serial is the udid of the ios device """
        super().__init__(serial)
        self.device = select_device(serial)
    
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
        png_base64 = self._request_json_value("GET", "/screenshot")
        png_data = base64.b64decode(png_base64)
        return Image.open(io.BytesIO(png_data))
    
    def window_size(self):
        return self._request_json_value("GET", "/window/size")
    
    def dump_hierarchy(self) -> Tuple[str, Hierarchy]:
        """returns xml string and hierarchy object"""
        xml_data = self._request_json_value("GET", "/source")
        root = ElementTree.fromstring(xml_data)
        return xml_data, parse_xml_element(root, WindowSize(width=1, height=1))
    
    def tap(self, x: int, y: int):
        self._request("POST", f"/wda/tap/0", {"x": x, "y": y})
    
    def app_current(self) -> CurrentAppResponse:
        # {'processArguments': {'env': {}, 'args': []}, 'name': '', 'pid': 32, 'bundleId': 'com.apple.springboard'}
        value = self._request_json_value("GET", "/wda/activeAppInfo")
        return CurrentAppResponse(package=value["bundleId"], pid=value["pid"])

    def home(self):
        self._request("POST", "/wda/homescreen")
        

def parse_xml_element(element, wsize: WindowSize, indexes: List[int]=[0]) -> Hierarchy:
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
    
    elem = Hierarchy(
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

    