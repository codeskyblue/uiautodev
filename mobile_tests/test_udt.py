#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Apr 23 2024 22:28:02 by codeskyblue
"""

import pytest
import adbutils
from uiauto_dev.driver.udt.udt import UDT


@pytest.fixture(scope="module")
def udt():
    return UDT(adbutils.device())


def test_udt_screenshot(udt: UDT):
    pil_img = udt.screenshot()
    assert pil_img is not None
    assert pil_img.width > 0


def test_udt_dump_hierarchy(udt: UDT):
    page_source = udt.dump_hierarchy()
    assert page_source.startswith("<?xml")
