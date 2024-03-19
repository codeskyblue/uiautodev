#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 05 2024 11:16:29 by codeskyblue
"""

class AppInspectorException(Exception):
    pass


class IOSDriverException(AppInspectorException):
    pass


class AndroidDriverException(AppInspectorException):
    pass


class AppiumDriverException(AppInspectorException):
    pass
