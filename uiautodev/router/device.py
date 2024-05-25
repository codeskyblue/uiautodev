#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:00:10 by codeskyblue
"""

import io
import logging
from typing import Any, List

from fastapi import APIRouter, Response
from pydantic import BaseModel

from uiautodev import command_proxy
from uiautodev.command_types import Command, CurrentAppResponse, InstallAppRequest, InstallAppResponse, TapRequest
from uiautodev.model import DeviceInfo, Node, ShellResponse
from uiautodev.provider import BaseProvider

logger = logging.getLogger(__name__)

class AndroidShellPayload(BaseModel):
    command: str


def make_router(provider: BaseProvider) -> APIRouter:
    router = APIRouter()

    @router.get("/list")
    def _list() -> List[DeviceInfo]:
        """List of Android devices"""
        try:
            return provider.list_devices()
        except NotImplementedError as e:
            return Response(content="list_devices not implemented", media_type="text/plain", status_code=501)
        except Exception as e:
            logger.exception("list_devices failed")
            return Response(content=str(e), media_type="text/plain", status_code=500)

    @router.post("/{serial}/shell")
    def android_shell(serial: str, payload: AndroidShellPayload) -> ShellResponse:
        """Run a shell command on an Android device"""
        try:
            driver = provider.get_device_driver(serial)
            return driver.shell(payload.command)
        except NotImplementedError as e:
            return Response(content="shell not implemented", media_type="text/plain", status_code=501)
        except Exception as e:
            logger.exception("shell failed")
            return ShellResponse(output="", error=str(e))

    @router.get(
        "/{serial}/screenshot/{id}",
        responses={200: {"content": {"image/jpeg": {}}}},
        response_class=Response,
    )
    def _screenshot(serial: str, id: int) -> Response:
        """Take a screenshot of device"""
        try:
            driver = provider.get_device_driver(serial)
            pil_img = driver.screenshot(id).convert("RGB")
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG")
            image_bytes = buf.getvalue()
            return Response(content=image_bytes, media_type="image/jpeg")
        except Exception as e:
            logger.exception("screenshot failed")
            return Response(content=str(e), media_type="text/plain", status_code=500)

    @router.get("/{serial}/hierarchy")
    def dump_hierarchy(serial: str, format: str = "json") -> Node:
        """Dump the view hierarchy of an Android device"""
        try:
            driver = provider.get_device_driver(serial)
            xml_data, hierarchy = driver.dump_hierarchy()
            if format == "xml":
                return Response(content=xml_data, media_type="text/xml")
            elif format == "json":
                return hierarchy
            else:
                return Response(content=f"Invalid format: {format}", media_type="text/plain", status_code=400)
        except Exception as e:
            logger.exception("dump_hierarchy failed")
            return Response(content=str(e), media_type="text/plain", status_code=500)
    
    @router.post('/{serial}/command/tap')
    def command_tap(serial: str, params: TapRequest):
        """Run a command on the device"""
        driver = provider.get_device_driver(serial)
        command_proxy.tap(driver, params)
        return {"status": "ok"}
    
    @router.post('/{serial}/command/installApp')
    def install_app(serial: str, params: InstallAppRequest) -> InstallAppResponse:
        """Install app"""
        driver = provider.get_device_driver(serial)
        return command_proxy.app_install(driver, params)

    @router.get('/{serial}/command/currentApp')
    def current_app(serial: str) -> CurrentAppResponse:
        """Get current app"""
        driver = provider.get_device_driver(serial)
        return command_proxy.app_current(driver)

    @router.post('/{serial}/command/{command}')
    def _command_proxy_other(serial: str, command: Command, params: Any = None):
        """Run a command on the device"""
        driver = provider.get_device_driver(serial)
        func = command_proxy.COMMANDS[command]
        if params is None:
            response = func(driver)
        else:
            response = func(driver, params)
        return response

    return router
