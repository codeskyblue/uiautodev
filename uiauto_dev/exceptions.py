#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 05 2024 11:16:29 by codeskyblue
"""

class uiauto_devException(Exception):
    pass


class IOSDriverException(uiauto_devException):
    pass


class AndroidDriverException(uiauto_devException):
    pass


class AppiumDriverException(uiauto_devException):
    pass
