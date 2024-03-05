#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:00:10 by codeskyblue
"""

import io
from typing import List

from fastapi import APIRouter, Response
from pydantic import BaseModel

from appinspector.model import DeviceInfo, Hierarchy, ShellResponse
from appinspector.provider import BaseProvider


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
            pil_img = driver.screenshot(id)
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG")
            image_bytes = buf.getvalue()
            return Response(content=image_bytes, media_type="image/jpeg")
        except Exception as e:
            return Response(content=str(e), media_type="text/plain", status_code=500)

    @router.get("/{serial}/hierarchy")
    def dump_hierarchy(serial: str) -> Hierarchy:
        """Dump the view hierarchy of an Android device"""
        try:
            driver = provider.get_device_driver(serial)
            xml_data, hierarchy = driver.dump_hierarchy()
            return hierarchy
        except Exception as e:
            return Response(content=str(e), media_type="text/plain", status_code=500)

    return router
