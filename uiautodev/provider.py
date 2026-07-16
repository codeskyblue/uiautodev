#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Feb 18 2024 11:10:58 by codeskyblue
"""
from __future__ import annotations

import abc
import logging
from functools import lru_cache
from typing import Optional, Type

import adbutils

from uiautodev.driver.android import ADBAndroidDriver, U2AndroidDriver
from uiautodev.driver.base_driver import BaseDriver
from uiautodev.driver.harmony import HDC, HarmonyDriver
from uiautodev.driver.ios import IOSDriver
from uiautodev.driver.mock import MockDriver
from uiautodev.exceptions import UiautoException
from uiautodev.model import DeviceInfo
from uiautodev.utils.usbmux import MuxDevice, list_devices

logger = logging.getLogger(__name__)


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
    def __init__(self, driver_class: Type[BaseDriver] = U2AndroidDriver, port: Optional[int] = None):
        self.driver_class = driver_class
        self.port = port

    def list_devices(self) -> list[DeviceInfo]:
        adb = adbutils.AdbClient()
        ret: list[DeviceInfo] = []
        for d in adb.list(extended=True):
            if d.state != "device":
                ret.append(DeviceInfo(serial=d.serial, status=d.state, enabled=False))
            else:
                ret.append(DeviceInfo(
                    serial=d.serial,
                    status=d.state,
                    name=d.tags.get('device', ''),
                    model=d.tags.get('model', ''),
                    product=d.tags.get('product', ''),
                    enabled=True
                ))
        return ret

    @lru_cache
    def get_device_driver(self, serial: str) -> BaseDriver:
        if self.port is not None:
            if issubclass(self.driver_class, U2AndroidDriver):
                return self.driver_class(serial, port=self.port)
            logger.warning(
                "A custom uiautomator2 port (%s) was provided but %s does not support a custom port; ignoring",
                self.port,
                self.driver_class.__name__,
            )
        return self.driver_class(serial)



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
        return [DeviceInfo(serial=d, model=self.hdc.get_model(d), name=self.hdc.get_name(d)) for d in devices]

    @lru_cache
    def get_device_driver(self, serial: str) -> HarmonyDriver:
        return HarmonyDriver(self.hdc, serial)


class MockProvider(BaseProvider):
    def list_devices(self) -> list[DeviceInfo]:
        return [DeviceInfo(serial="mock-serial", model="mock-model", name="mock-name")]

    def get_device_driver(self, serial: str) -> BaseDriver:
        return MockDriver(serial)
