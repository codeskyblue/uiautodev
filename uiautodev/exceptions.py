#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 05 2024 11:16:29 by codeskyblue
"""

class UiautoException(Exception):
    pass


class DriverException(UiautoException):
    """Base class for all driver-related exceptions."""
    pass

class IOSDriverException(DriverException): ...
class AndroidDriverException(DriverException): ...
class HarmonyDriverException(DriverException): ...
class AppiumDriverException(DriverException): ...


class MethodError(UiautoException):
    pass


class ElementNotFoundError(MethodError): ...
class RequestError(UiautoException): ...