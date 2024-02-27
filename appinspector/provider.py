#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 11:10:58 by codeskyblue
"""
from __future__ import annotations
import adbutils

from appinspector.device_driver import AndroidDriver
from appinspector.model import DeviceInfo


class BaseProvider:
    def list_devices(self) -> list[DeviceInfo]:
        raise NotImplementedError()


class AndroidProvider(BaseProvider):
    def __init__(self):
        pass

    def list_devices(self) -> list[DeviceInfo]:
        adb = adbutils.AdbClient()
        return [
            DeviceInfo(serial=d.serial, model=d.prop.model, name=d.prop.name)
            for d in adb.device_list()
        ]

    def get_device_driver(self, serial: str) -> AndroidDriver:
        return AndroidDriver(serial)
