#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:35:46 by codeskyblue
"""


from appinspector.driver.base import BaseDriver


class AndroidDriver(BaseDriver):
    def __init__(self, serial: str):
        super().__init__(serial)
    
    