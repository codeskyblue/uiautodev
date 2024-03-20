#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 15:51:59 by codeskyblue
"""

from __future__ import annotations

import io
import json
import logging
from pprint import pprint
from typing import Tuple

import httpretty
import httpx
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy as By
from PIL import Image
from selenium.webdriver.common.proxy import Proxy, ProxyType

from appinspector.command_types import CurrentAppResponse
from appinspector.driver.android import parse_xml
from appinspector.driver.base import BaseDriver
from appinspector.exceptions import AppiumDriverException
from appinspector.model import DeviceInfo, Hierarchy, ShellResponse, WindowSize
from appinspector.provider import BaseProvider

logger = logging.getLogger(__name__)

class AppiumProvider(BaseProvider):
    sessions = []

    def __init__(self, command_executor: str = "http://localhost:4723/wd/hub"):
        # command_executor = "http://localhost:4700"
        # command_executor = "http://localhost:4720/wd/hub"
        self.command_executor = command_executor.rstrip('/')
        self.sessions.clear()

    def list_devices(self) -> list[DeviceInfo]:
        """ appium just return all session_ids """
        response = httpx.get(f"{self.command_executor}/sessions", verify=False)
        if response.status_code >= 400:
            raise AppiumDriverException(f"Failed request to appium server: {self.command_executor} status: {response.status_code}")
        ret = []
        self.sessions = response.json()['value']
        for item in self.sessions:
            item['sessionId'] = item.pop('id')
            print("Active sessionId", item['sessionId'])
            serial = item['capabilities']['platformName'] + ':' + item['sessionId']
            ret.append(DeviceInfo(
                serial=serial,
                model=item['capabilities']['deviceModel'],
                name=item['capabilities']['deviceName'],
            ))
        return ret
    
    def get_device_driver(self, serial: str, session_id: str = None) -> BaseDriver:
        """ TODO: attach to the existing session """
        platform_name, session_id = serial.split(':', 1)
        filtered_sessions = [session for session in self.sessions if session['sessionId'] == session_id]
        if len(filtered_sessions) == 1:
            session = filtered_sessions[0]
            driver = self.attach_session(session)
            return AppiumDriver(driver, is_attached=True)
        else:
            options = UiAutomator2Options() if platform_name == "Android" else XCUITestOptions()
            driver = webdriver.Remote(self.command_executor, options=options)
            return AppiumDriver(driver)
        
    @httpretty.activate(allow_net_connect=False)
    def attach_session(self, session: dict) -> webdriver.Remote:
        """
        https://github.com/appium/python-client/issues/212
        the author say it can't
        """
        body = json.dumps({'value': session}, indent=4)
        logger.debug("Mock response: POST /wd/hub/session", body)
        httpretty.register_uri(httpretty.POST,
                               self.command_executor + '/session',
                               body=body,
                               headers={'Content-Type': 'application/json'})
        options = UiAutomator2Options()# if platform_name == "Android" else XCUITestOptions()
        driver = webdriver.Remote(command_executor=self.command_executor, strict_ssl=False, options=options)
        return driver

    def get_single_device_driver(self) -> BaseDriver:
        devices = self.list_devices()
        if len(devices) == 0:
            return self.get_device_driver("Android:12345")
        #     raise AppiumDriverException("No device found")
        return self.get_device_driver(devices[0].serial)


class AppiumDriver(BaseDriver):
    def __init__(self, driver: webdriver.Remote, is_attached: bool = False):
        self.driver = driver
        self.is_attached = is_attached
    
    # def __del__(self):
    #     if not self.is_attached:
    #         self.driver.quit()

    def screenshot(self, id: int) -> Image:
        png_data = self.driver.get_screenshot_as_png()
        return Image.open(io.BytesIO(png_data))

    def window_size(self) -> WindowSize:
        size = self.driver.get_window_size()
        return WindowSize(width=size["width"], height=size["height"])
        
    def dump_hierarchy(self) -> Tuple[str, Hierarchy]:
        source = self.driver.page_source
        wsize = self.window_size()
        return source, parse_xml(source, wsize)
    
    def shell(self, command: str) -> ShellResponse:
        # self.driver.execute_script(command)
        raise NotImplementedError()

    def tap(self, x: int, y: int):
        self.driver.tap([(x, y)], 100)
        print("Finished")
    
    def app_install(self, app_path: str):
        self.driver.install_app(app_path)
    
    def app_current(self) -> CurrentAppResponse:
        package = self.driver.current_package
        activity = self.driver.current_activity
        return CurrentAppResponse(package=package, activity=activity)

    def home(self):
        self.driver.press_keycode(3)