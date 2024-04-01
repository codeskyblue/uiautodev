#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 11:10:58 by codeskyblue
"""
from __future__ import annotations

import abc

import adbutils

from uiauto_dev.driver.android import AndroidDriver
from uiauto_dev.driver.base_driver import BaseDriver
from uiauto_dev.driver.ios import IOSDriver
from uiauto_dev.driver.mock import MockDriver
from uiauto_dev.exceptions import uiauto_devException
from uiauto_dev.model import DeviceInfo
from uiauto_dev.utils.usbmux import MuxDevice, list_devices


class BaseProvider(abc.ABC):
    @abc.abstractmethod
    def list_devices(self) -> list[DeviceInfo]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_device_driver(self, serial: str) -> BaseDriver:
        raise NotImplementedError()
    
    def get_single_device_driver(self) -> BaseDriver:
        """ debug use """
        devs = self.list_devices()
        if len(devs) == 0:
            raise uiauto_devException("No device found")
        if len(devs) > 1:
            raise uiauto_devException("More than one device found")
        return self.get_device_driver(devs[0].serial)


class AndroidProvider(BaseProvider):
    def __init__(self):
        pass

    def list_devices(self) -> list[DeviceInfo]:
        adb = adbutils.AdbClient()
        ret: list[DeviceInfo] = []
        for d in adb.list():
            if d.state != "device":
                ret.append(DeviceInfo(serial=d.serial, status=d.state, enabled=False))
            else:
                dev = adb.device(d.serial)
                ret.append(DeviceInfo(serial=d.serial, model=dev.prop.model, name=dev.prop.name))
        return ret

    def get_device_driver(self, serial: str) -> AndroidDriver:
        return AndroidDriver(serial)


class IOSProvider(BaseProvider):
    def list_devices(self) -> list[DeviceInfo]:
        devs = list_devices()
        return [DeviceInfo(serial=d.serial, model="unknown", name="unknown") for d in devs]

    def get_device_driver(self, serial: str) -> BaseDriver:
        return IOSDriver(serial)
    

class MockProvider(BaseProvider):
    def list_devices(self) -> list[DeviceInfo]:
        return [DeviceInfo(serial="mock-serial", model="mock-model", name="mock-name")]

    def get_device_driver(self, serial: str) -> BaseDriver:
        return MockDriver(serial)