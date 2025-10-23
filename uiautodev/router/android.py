# prefix for /api/android/{serial}/shell

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from uiautodev.driver.android import ADBAndroidDriver, U2AndroidDriver
from uiautodev.model import ShellResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class AndroidShellPayload(BaseModel):
    command: str
    
@router.post("/{serial}/shell")
def shell(serial: str, payload: AndroidShellPayload) -> ShellResponse:
    """Run a shell command on an Android device"""
    try:
        driver = ADBAndroidDriver(serial)
        return driver.shell(payload.command)
    except NotImplementedError as e:
        return Response(content="shell not implemented", media_type="text/plain", status_code=501)
    except Exception as e:
        logger.exception("shell failed")
        return ShellResponse(output="", error=str(e))


@router.get("/{serial}/current_activity")
async def get_current_activity(serial: str) -> Response:
    """Get the current activity of the Android device"""
    try:
        driver = ADBAndroidDriver(serial)
        activity = driver.get_current_activity()
        return Response(content=activity, media_type="text/plain")
    except Exception as e:
        logger.exception("get_current_activity failed")
        return Response(content="", media_type="text/plain")