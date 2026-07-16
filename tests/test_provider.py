import logging
from unittest import mock

from uiautodev.driver.android.adb_driver import ADBAndroidDriver
from uiautodev.provider import AndroidProvider


def test_get_device_driver_warns_when_port_ignored(caplog):
    with mock.patch("uiautodev.driver.android.adb_driver.adbutils.device"):
        provider = AndroidProvider(driver_class=ADBAndroidDriver, port=9009)
        with caplog.at_level(logging.WARNING):
            driver = provider.get_device_driver("dummy-serial")

    assert isinstance(driver, ADBAndroidDriver)
    assert "does not support a custom port" in caplog.text
