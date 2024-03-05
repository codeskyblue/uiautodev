#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Mon Mar 04 2024 14:10:00 by codeskyblue
"""

from PIL import Image

from appinspector.driver.base import BaseDriver
from appinspector.model import Hierarchy, ShellResponse, WindowSize


class MockDriver(BaseDriver):
    def screenshot(self, id: int):
        return Image.new("RGB", (100, 150), "gray")

    def dump_hierarchy(self):
        return "", Hierarchy(
            key="0",
            name="root",
            bounds=(0, 0, 1, 1),
            properties={
                "class": "android.view.View",
            },
            children=[
                Hierarchy(
                    key="0-0",
                    name="mock1",
                    bounds=(0.1, 0.1, 0.5, 0.5),
                    properties={
                        "class": "android.widget.FrameLayout",
                        "text": "mock1",
                    },
                ),
                Hierarchy(
                    key="0-1",
                    name="mock2",
                    bounds=(0.3, 0.3, 0.7, 0.7),
                    properties={
                        "class": "android.widget.ImageView",
                        "text": "mock2",
                    },
                ),
            ],
        )
