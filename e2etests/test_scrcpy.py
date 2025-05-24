import logging

import adbutils
import pytest

from uiautodev.remote.scrcpy import ScrcpyServer

logger = logging.getLogger(__name__)
from adbutils._device import AdbDevice


@pytest.fixture
def device() -> AdbDevice:
    dev = adbutils.adb.device()
    return dev


def test_scrcpy_video(device: AdbDevice):
    server = ScrcpyServer(device)
    assert server.device_width > 0
    assert server.device_height > 0
    assert server.resolution_width > 0
    assert server.resolution_height > 0
    server.close()