# coding: utf-8
#
# 参考：https://github.com/codematrixer/awesome-hdc

import pytest

from uiautodev.driver.harmony import HDC


@pytest.fixture
def hdc() -> HDC:
    return HDC()

@pytest.fixture
def serial(hdc: HDC) -> str:
    devices = hdc.list_device()
    assert len(devices) == 1
    return devices[0]


def test_list_device(hdc: HDC):
    devices = hdc.list_device()
    assert len(devices) == 1


def test_shell(hdc: HDC, serial: str):
    assert hdc.shell(serial, 'pwd') == '/'

def test_get_model(hdc: HDC, serial: str):
    assert hdc.get_model(serial) == 'ohos'


def test_screenshot(hdc: HDC, serial: str):
    image = hdc.screenshot(serial)
    assert image is not None
    assert image.size is not None


def test_dump_layout(hdc: HDC, serial: str):
    layout = hdc.dump_layout(serial)
    assert layout is not None
    assert isinstance(layout, dict)


from uiautodev.driver.harmony import HarmonyDriver


@pytest.fixture
def driver(hdc: HDC, serial: str) -> HarmonyDriver:
    return HarmonyDriver(hdc, serial)


def test_window_size(driver: HarmonyDriver):
    size = driver.window_size()
    assert size.width > 0
    assert size.height > 0
    

def test_dump_hierarchy(driver: HarmonyDriver):
    xml, hierarchy = driver.dump_hierarchy()
    assert xml is not None
    assert hierarchy is not None