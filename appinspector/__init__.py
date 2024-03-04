#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Mon Mar 04 2024 14:28:53 by codeskyblue
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("appinspector")
except PackageNotFoundError:
    __version__ = "0.0.0"