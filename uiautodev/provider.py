#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 11:10:58 by codeskyblue
"""
from __future__ import annotations

import abc
from functools import lru_cache

import adbutils

from uiautodev.driver.android import AndroidDriver
from uiautodev.driver.base_driver import BaseDriver
from uiautodev.driver.harmony import HarmonyDriver, HDC
from uiautodev.driver.ios import IOSDriver
from uiautodev.driver.mock import MockDriver
from uiautodev.exceptions import UiautoException
from uiautodev.model import DeviceInfo
from uiautodev.utils.usbmux import MuxDevice, list_devices


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
            raise UiautoException("No device found")
        if len(devs) > 1:
            raise UiautoException("More than one device found")
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

    @lru_cache
    def get_device_driver(self, serial: str) -> AndroidDriver:
        return AndroidDriver(serial)


class IOSProvider(BaseProvider):
    def list_devices(self) -> list[DeviceInfo]:
        devs = list_devices()
        return [DeviceInfo(serial=d.serial, model="unknown", name="unknown") for d in devs]

    @lru_cache
    def get_device_driver(self, serial: str) -> BaseDriver:
        return IOSDriver(serial)


class HarmonyProvider(BaseProvider):
    def __init__(self):
        super().__init__()
        self.hdc = HDC()

    def list_devices(self) -> list[DeviceInfo]:
        devices = self.hdc.list_device()
        return [DeviceInfo(serial=d, model=self.hdc.get_model(d), name=self.hdc.get_model(d)) for d in devices]

    @lru_cache
    def get_device_driver(self, serial: str) -> HarmonyDriver:
        return HarmonyDriver(self.hdc, serial)


class MockProvider(BaseProvider):
    def list_devices(self) -> list[DeviceInfo]:
        return [DeviceInfo(serial="mock-serial", model="mock-model", name="mock-name")]

    def get_device_driver(self, serial: str) -> BaseDriver:
        return MockDriver(serial)
