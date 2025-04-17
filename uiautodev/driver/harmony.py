#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import List, Optional, Tuple, Union, final

from PIL import Image

from uiautodev.command_types import CurrentAppResponse
from uiautodev.driver.base_driver import BaseDriver
from uiautodev.model import AppInfo, Node, Rect, ShellResponse, WindowSize

logger = logging.getLogger(__name__)

StrOrPath = Union[str, Path]


def run_command(command: str, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout,
            text=True,
            input='' # this avoid stdout: "FreeChannelContinue handle->data is nullptr"
        )
        # the hdc shell stderr is (不仅没啥用，还没办法去掉)
        # Remote PTY will not be allocated because stdin is not a terminal.
        # Use multiple -t options to force remote PTY allocation.
        output = result.stdout.strip()
        return output
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"{command:r} timeout {e}")


class HDCError(Exception):
    pass


class HDC:
    def __init__(self):
        self.hdc = 'hdc'
        self.tmpdir = tempfile.TemporaryDirectory()
    
    def __del__(self):
        self.tmpdir.cleanup()
    
    def list_device(self) -> List[str]:
        command = f"{self.hdc} list targets"
        result = run_command(command)
        if result and not "Empty" in result:
            devices = []
            for line in result.strip().split("\n"):
                serial = line.strip().split('\t', 1)[0]
                devices.append(serial)
            return devices
        else:
            return []
    
    def shell(self, serial: str, command: str) -> str:
        command = f"{self.hdc} -t {serial} shell \"{command}\""
        result = run_command(command)
        return result.strip()
    
    def get_model(self, serial: str) -> str:
        return self.shell(serial, "param get const.product.model")
    
    def pull(self, serial: str, remote: StrOrPath, local: StrOrPath):
        if isinstance(remote, Path):
            remote = remote.as_posix()
        command = f"{self.hdc} -t {serial} file recv {remote} {local}"
        output = run_command(command)
        if not os.path.exists(local):
            raise HDCError(f"device file: {remote} not found", output)
    
    def push(self, serial: str, local: StrOrPath, remote: StrOrPath) -> str:
        if isinstance(remote, Path):
            remote = remote.as_posix()
        command = f"{self.hdc} -t {serial} file send {local} {remote}"
        return run_command(command)
    
    def screenshot(self, serial: str) -> Image.Image:
        device_path = f'/data/local/tmp/screenshot-{int(time.time()*1000)}.png'
        self.shell(serial, f"uitest screenCap -p {device_path}")
        try:
            local_path = os.path.join(self.tmpdir.name, f"{uuid.uuid4()}.png")
            self.pull(serial, device_path, local_path)
            with Image.open(local_path) as image:
                image.load()
                return image
        finally:
            self.shell(serial, f"rm {device_path}")

    def dump_layout(self, serial: str) -> dict:
        name = "{}.json".format(int(time.time() * 1000))
        remote_path = f"/data/local/tmp/layout-{name}.json"
        temp_path = os.path.join(self.tmpdir.name, f"layout-{name}.json")
        output = self.shell(serial, f"uitest dumpLayout -p {remote_path}")
        self.pull(serial, remote_path, temp_path)
        # mock
        # temp_path = Path(__file__).parent / 'testdata/layout.json'
        try:
            with open(temp_path, "rb") as f:
                json_content = json.load(f)
            return json_content
        except json.JSONDecodeError:
            raise HDCError(f"failed to dump layout: {output}")
        finally:
            self.shell(serial, f"rm {remote_path}")
    

class HarmonyDriver(BaseDriver):
    def __init__(self, hdc: HDC, serial: str):
        super().__init__(serial)
        self.hdc = hdc

    def screenshot(self, id: int = 0) -> Image.Image:
        return self.hdc.screenshot(self.serial)

    def window_size(self) -> WindowSize:
        result = self.hdc.shell(self.serial, "hidumper -s 10 -a screen")
        pattern = r"activeMode:\s*(\d+x\d+)"
        match = re.search(pattern, result)
        if match:
            resolution = match.group(1).split("x")
            return WindowSize(width=int(resolution[0]), height=int(resolution[1]))
        else:
            image = self.screenshot()
            return WindowSize(width=image.width, height=image.height)

    def dump_hierarchy(self) -> Tuple[str, Node]:
        """returns xml string and hierarchy object"""
        layout = self.hdc.dump_layout(self.serial)
        return json.dumps(layout), parse_json_element(layout)

    def tap(self, x: int, y: int):
        self.hdc.shell(self.serial, f"uinput -T -c {x} {y}")

    def app_current(self) -> Optional[CurrentAppResponse]:
        echo = self.hdc.shell(self.serial, "hidumper -s WindowManagerService -a '-a'")
        focus_window = re.search(r"Focus window: (\d+)", echo)
        if focus_window:
            focus_window = focus_window.group(1)
        mission_echo = self.hdc.shell(self.serial, "aa dump -a")
        pkg_names = re.findall(r"Mission ID #(\d+)\s+mission name #\[(.*?)\]", mission_echo)
        if focus_window and pkg_names:
            for mission in pkg_names:
                mission_id = mission[0]
                if focus_window == mission_id:
                    mission_name = mission[1]
                    pkg_name = mission_name.split(":")[0].replace("#", "")
                    ability_name = mission_name.split(":")[-1]
                    pid = self.hdc.shell(self.serial, f"pidof {pkg_name}").strip()
                    return CurrentAppResponse(package=pkg_name, activity=ability_name, pid=int(pid))
        else:
            return None

    def shell(self, command: str) -> ShellResponse:
        result = self.hdc.shell(self.serial, command)
        return ShellResponse(output=result)

    def home(self):
        self.hdc.shell(self.serial, "uinput -K -d 1 -u 1")

    def back(self):
        self.hdc.shell(self.serial, "uinput -K -d 2 -u 2")

    def volume_up(self):
        self.hdc.shell(self.serial, "uinput -K -d 16 -u 16")

    def volume_down(self):
        self.hdc.shell(self.serial, "uinput -K -d 17 -u 17")

    def volume_mute(self):
        self.hdc.shell(self.serial, "uinput -K -d 22 -u 22")

    def app_switch(self):
        self.hdc.shell(self.serial, "uinput -K -d 2076 -d 2049 -u 2076 -u 2049")

    def app_list(self) -> List[AppInfo]:
        results = []
        output = self.hdc.shell(self.serial, "bm dump -a")
        for i in output.split("\n"):
            if "ID" in i:
                continue
            else:
                results.append(AppInfo(packageName=i.strip()))
        return results


def parse_json_element(element, indexes: List[int] = [0]) -> Node:
    """
    Recursively parse an json element into a dictionary format.
    """
    attributes = element.get("attributes", {})
    name = attributes.get("type", "")
    bounds = attributes.get("bounds", "")
    bounds = list(map(int, re.findall(r"\d+", bounds)))
    assert len(bounds) == 4
    rect = Rect(x=bounds[0], y=bounds[1], width=bounds[2] - bounds[0], height=bounds[3] - bounds[1])
    elem = Node(
        key="-".join(map(str, indexes)),
        name=name,
        bounds=None,
        rect=rect,
        properties={key: attributes[key] for key in attributes},
        children=[],
    )
    # Construct xpath for children
    for index, child in enumerate(element.get("children", [])):
        child_node = parse_json_element(child, indexes + [index])
        if child_node:
            elem.children.append(child_node)

    return elem
