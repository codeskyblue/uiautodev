from __future__ import annotations

import datetime
import json as sysjson
import platform
import re
import socket
import subprocess
import sys
import typing
import uuid
from http.client import HTTPConnection, HTTPResponse
from typing import Optional, TypeVar, Union

from pydantic import BaseModel
from pygments import formatters, highlight, lexers

from uiautodev.exceptions import RequestError
from uiautodev.model import Node


def is_output_terminal() -> bool:
    """
    Check if the standard output is attached to a terminal.
    """
    return sys.stdout.isatty()


def enable_windows_ansi_support():
    if platform.system().lower() == "windows" and is_output_terminal():
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


def default_json_encoder(obj):
    if isinstance(obj, bytes):
        return f'<{obj.hex()}>'
    if isinstance(obj, datetime.datetime):
        return str(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    raise TypeError()


def print_json(buf, colored=None, default=default_json_encoder):
    """ copy from pymobiledevice3 """
    formatted_json = sysjson.dumps(buf, sort_keys=True, indent=4, default=default)
    if colored is None:
        if is_output_terminal():
            colored = True
            enable_windows_ansi_support()
        else:
            colored = False

    if colored:
        colorful_json = highlight(formatted_json, lexers.JsonLexer(),
                                  formatters.TerminalTrueColorFormatter(style='stata-dark'))
        print(colorful_json)
    else:
        print(formatted_json)


_T = TypeVar("_T")


def convert_to_type(value: str, _type: _T) -> _T:
    """ usage example:
    convert_to_type("123", int)
    """
    if _type in (int, float, str):
        return _type(value)
    if _type == bool:
        return value.lower() in ("true", "1")
    if _type == Union[int, float]:
        return float(value) if "." in value else int(value)
    if _type == re.Pattern:
        return re.compile(value)
    raise NotImplementedError(f"convert {value} to {_type}")


def convert_params_to_model(params: list[str], model: BaseModel) -> BaseModel:
    """ used in cli.py """
    assert len(params) > 0
    if len(params) == 1:
        try:
            return model.model_validate_json(params)
        except Exception as e:
            print("module_parse_error", e)

    value = {}
    type_hints = typing.get_type_hints(model)
    for p in params:
        if "=" not in p:
            _type = type_hints.get(p)
            if _type == bool:
                value[p] = True
                continue
            elif _type is None:
                print(f"unknown key: {p}")
                continue
            raise ValueError(f"missing value for {p}")
        k, v = p.split("=", 1)
        _type = type_hints.get(k)
        if _type is None:
            print(f"unknown key: {k}")
            continue
        value[k] = convert_to_type(v, _type)
    return model.model_validate(value)


class SocketHTTPConnection(HTTPConnection):
    def __init__(self, conn: socket.socket, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self.__conn = conn

    def connect(self):
        self.sock = self.__conn

    def __enter__(self) -> HTTPConnection:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class MySocketHTTPConnection(SocketHTTPConnection):
    def connect(self):
        super().connect()
        self.sock.settimeout(self.timeout)


def fetch_through_socket(sock: socket.socket, path: str, method: str = "GET", json: Optional[dict] = None,
                         timeout: float = 60) -> bytearray:
    """ usage example:
    with socket.create_connection((host, port)) as s:
        request_through_socket(s, "GET", "/")
    """
    conn = MySocketHTTPConnection(sock, timeout)
    try:
        if json is None:
            conn.request(method, path)
        else:
            conn.request(method, path, body=sysjson.dumps(json), headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        if response.getcode() != 200:
            raise RequestError(f"request {method} {path}, status: {response.getcode()}")
        content = bytearray()
        while chunk := response.read(40960):
            content.extend(chunk)
        return content
    finally:
        conn.close()


def node_travel(node: Node, dfs: bool = True):
    """ usage example:
    for n in node_travel(node):
        print(n)
    """
    if not dfs:
        yield node
    for child in node.children:
        yield from node_travel(child, dfs)
    if dfs:
        yield node


def run_command(command: str, timeout: int = 60) -> str:
    """
    run shell command
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout,
            text=True
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output.strip()
    except subprocess.TimeoutExpired as e:
        return f"timeout {e}"
    except Exception as e:
        return f"run command error {e}"
