from __future__ import annotations

import json
import re
import sys
import platform
from typing import TypeVar, Union
import typing
from pydantic import BaseModel


class ColorizedJsonEncoder(json.JSONEncoder):
    KEY_COLOR = "\033[1;34m"  # Bright Blue for keys
    VALUE_COLOR = "\033[0;32m"  # Green for values
    STRING_COLOR = "\033[0;33m"  # Yellow for strings
    RESET = "\033[0m"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.colorize_output = is_output_terminal()

    def encode(self, o):
        if not self.colorize_output:
            return super().encode(o)

        uncolored_json = super().encode(o)

        def colorize_key(match):
            key = match.group(1)
            return f"{self.KEY_COLOR}{key}{self.RESET}: "

        def colorize_value(match):
            value = match.group(0)
            if value.startswith('"'):
                return f"{self.STRING_COLOR}{value}{self.RESET}"
            return f"{self.VALUE_COLOR}{value}{self.RESET}"

        import re

        # First, colorize keys
        pattern_keys = r'(".*?")(\s*:\s*)'
        colored_json = re.sub(pattern_keys, colorize_key, uncolored_json)

        # Then, selectively colorize values
        pattern_values = r':\s*(".*?"|\b(?:true|false|null)\b|\d+|\[.*?\]|\{.*?\})'
        colored_json = re.sub(
            pattern_values, colorize_value, colored_json, flags=re.DOTALL
        )

        return colored_json


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


def print_json_with_color(data: BaseModel | None):
    enable_windows_ansi_support()
    json_data = data.model_dump() if data else None
    print(json.dumps(json_data, indent=4, cls=ColorizedJsonEncoder))


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