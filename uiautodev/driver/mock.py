#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Mon Mar 04 2024 14:10:00 by codeskyblue
"""

from PIL import Image, ImageDraw

from uiautodev.driver.base_driver import BaseDriver
from uiautodev.model import Node, ShellResponse, WindowSize


class MockDriver(BaseDriver):
    def screenshot(self, id: int):
        im = Image.new("RGB", (500, 800), "gray")
        draw = ImageDraw.Draw(im)
        draw.text((10, 10), "mock", fill="white")
        draw.rectangle([100, 100, 200, 200], outline="red", fill="blue")
        del draw
        return im

    def dump_hierarchy(self):
        return "", Node(
            key="0",
            name="root",
            bounds=(0, 0, 1, 1),
            properties={
                "class": "android.view.View",
            },
            children=[
                Node(
                    key="0-0",
                    name="mock1",
                    bounds=(0.1, 0.1, 0.5, 0.5),
                    properties={
                        "class": "android.widget.FrameLayout",
                        "text": "mock1",
                        "accessible": "true",
                    },
                ),
                Node(
                    key="0-1",
                    name="mock2",
                    bounds=(0.4, 0.4, 0.6, 0.6),
                    properties={
                        "class": "android.widget.ImageView",
                        "text": "mock2",
                        "accessible": "true",
                    },
                    children=[
                        Node(
                            key="0-1-0",
                            name="mock2-1",
                            bounds=(0.42, 0.42, 0.45, 0.45),
                            properties={
                                "class": "android.widget.ImageView",
                                "text": "mock2-1",
                                "visible": "true",
                            },
                        ),
                    ]
                ),
                Node(
                    key="0-2",
                    name="mock-should-not-show",
                    bounds=(0.4, 0.4, 0.6, 0.6),
                    properties={
                        "class": "android.widget.ImageView",
                        "text": "mock3",
                        "visible": "false",
                    },
                ),
            ],
        )
