#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Mon Mar 04 2024 14:10:00 by codeskyblue
"""

from PIL import Image

from appinspector.driver.base import BaseDriver
from appinspector.model import Hierarchy, ShellResponse, WindowSize


class MockDriver(BaseDriver):
    def screenshot(self, id: int):
        return Image.new("RGB", (100, 100), "gray")

    def dump_hierarchy(self) -> Hierarchy:
        return Hierarchy(key="root", name="root")
