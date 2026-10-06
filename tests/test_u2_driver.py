from unittest import mock

from uiautodev.driver.android.u2_driver import U2AndroidDriver


def _make_driver(port=None):
    with mock.patch("uiautodev.driver.android.adb_driver.adbutils.device"):
        return U2AndroidDriver("dummy-serial", port=port)


def test_ud_forwards_port_when_set():
    driver = _make_driver(port=9009)
    with mock.patch("uiautodev.driver.android.u2_driver.u2.connect_usb") as connect_usb:
        driver.ud
    connect_usb.assert_called_once_with("dummy-serial", port=9009)


def test_ud_omits_port_when_unset():
    driver = _make_driver(port=None)
    with mock.patch("uiautodev.driver.android.u2_driver.u2.connect_usb") as connect_usb:
        driver.ud
    connect_usb.assert_called_once_with("dummy-serial")
