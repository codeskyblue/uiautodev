#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 11:10:58 by codeskyblue
"""
from __future__ import annotations

import abc

import adbutils

from appinspector.driver.android import AndroidDriver
from appinspector.driver.base import BaseDriver
from appinspector.driver.mock import MockDriver
from appinspector.model import DeviceInfo


class BaseProvider(abc.ABC):
    @abc.abstractmethod
    def list_devices(self) -> list[DeviceInfo]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_device_driver(self, serial: str) -> BaseDriver:
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


class IOSProvider(BaseProvider):
    def list_devices(self) -> list[DeviceInfo]:
        # from tidevice3.api import list_devices
        raise NotImplementedError()

    def get_device_driver(self, serial: str) -> BaseDriver:
        raise NotImplementedError()
    

class MockProvider(BaseProvider):
    def list_devices(self) -> list[DeviceInfo]:
        return [DeviceInfo(serial="mock-serial", model="mock-model", name="mock-name")]

    def get_device_driver(self, serial: str) -> BaseDriver:
        return MockDriver(serial)