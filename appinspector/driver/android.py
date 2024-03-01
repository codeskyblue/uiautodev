#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:19:29 by codeskyblue
"""

import re
from functools import partial
from xml.etree import ElementTree

import adbutils
from PIL import Image

from appinspector.driver.base import BaseDriver
from appinspector.model import Hierarchy, ShellResponse, WindowSize


def parse_xml_element(element, wsize: WindowSize) -> Hierarchy:
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
        name=name,
        bounds=bounds,
        properties={key: element.attrib[key] for key in element.attrib},
        children=[],
    )

    # Construct xpath for children
    for child in element:
        elem.children.append(parse_xml_element(child, wsize))

    return elem


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

    def dump_hierarchy(self) -> Hierarchy:
        wsize = self.device.window_size()
        xml_data = self.device.dump_hierarchy()
        root = ElementTree.fromstring(xml_data)
        return parse_xml_element(root, WindowSize(width=wsize[0], height=wsize[1]))
