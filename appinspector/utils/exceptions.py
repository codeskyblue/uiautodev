#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 05 2024 10:18:09 by codeskyblue

Copy from https://github.com/doronz88/pymobiledevice3
"""


class PyMobileDevice3Exception(Exception):
    pass


class NotPairedError(PyMobileDevice3Exception):
    pass



class MuxException(PyMobileDevice3Exception):
    pass


class MuxVersionError(MuxException):
    pass


class BadCommandError(MuxException):
    pass


class BadDevError(MuxException):
    pass


class ConnectionFailedError(MuxException):
    pass


class ConnectionFailedToUsbmuxdError(ConnectionFailedError):
    pass


class ArgumentError(PyMobileDevice3Exception):
    pass