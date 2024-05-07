#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 05 2024 11:16:29 by codeskyblue
"""

class UiautoException(Exception):
    pass


class IOSDriverException(UiautoException):
    pass


class AndroidDriverException(UiautoException):
    pass


class AppiumDriverException(UiautoException):
    pass


class MethodError(UiautoException):
    pass


class ElementNotFoundError(MethodError):
    pass


class RequestError(UiautoException):
    pass