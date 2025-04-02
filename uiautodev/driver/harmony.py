#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile
import time
import re
import shutil
from typing import Tuple, List, Optional

from PIL import Image

from uiautodev.command_types import CurrentAppResponse
from uiautodev.utils.common import run_command
from uiautodev.driver.base_driver import BaseDriver
from uiautodev.model import AppInfo, Node, Rect, ShellResponse, WindowSize


class HarmonyUtils:
    @staticmethod
    def list_device() -> List[str]:
        if not shutil.which("hdc"):
            return []
        command = "hdc list targets"
        result = run_command(command)
        if result and not "Empty" in result:
            devices = result.split("\n")
            return devices
        else:
            return []

    @staticmethod
    def shell(device_sn: str, command: str) -> str:
        shell_command = f"hdc -t {device_sn} shell {command}"
        return run_command(shell_command)

    @staticmethod
    def get_model(device_sn: str) -> str:
        return HarmonyUtils.shell(device_sn, "param get const.product.model")

    @staticmethod
    def screenshot(device_sn: str) -> str:
        name = "{}.jpeg".format(int(time.time() * 1000))
        remote_path = "/data/local/tmp/{}".format(name)
        HarmonyUtils.shell(device_sn, "snapshot_display -f {}".format(remote_path))
        temp_path = os.path.join(tempfile.gettempdir(), name)
        HarmonyUtils.pull(device_sn, remote_path, temp_path)
        if os.path.exists(temp_path):
            HarmonyUtils.shell(device_sn, "rm {}".format(remote_path))
            return temp_path
        else:
            return None

    @staticmethod
    def dump_layout(device_sn: str) -> str:
        name = "{}.json".format(int(time.time() * 1000))
        remote_path = "/data/local/tmp/{}".format(name)
        HarmonyUtils.shell(device_sn, "uitest dumpLayout -p {}".format(remote_path))
        temp_path = os.path.join(tempfile.gettempdir(), name)
        HarmonyUtils.pull(device_sn, remote_path, temp_path)
        if os.path.exists(temp_path):
            HarmonyUtils.shell(device_sn, "rm {}".format(remote_path))
            return temp_path
        else:
            return None

    @staticmethod
    def pull(device_sn: str, remote: str, local: str) -> str:
        command = f"hdc -t {device_sn} file recv {remote} {local}"
        return run_command(command)

    @staticmethod
    def push(device_sn: str, local: str, remote: str) -> str:
        command = f"hdc -t {device_sn} file send {local} {remote}"
        return run_command(command)


class HarmonyDriver(BaseDriver):
    def __init__(self, serial: str):
        super().__init__(serial)

    def screenshot(self, id: int = 0) -> Image.Image:
        path = HarmonyUtils.screenshot(self.serial)
        if path:
            try:
                image = Image.open(path)
                image.load()
                os.remove(path)
                return image
            except Exception as e:
                raise RuntimeError(f"can not load image or cannot delete {e}")
        else:
            raise FileNotFoundError("screenshot failed!")

    def window_size(self) -> Tuple[int, int]:
        result = HarmonyUtils.shell(self.serial, "hidumper -s 10 -a screen")
        pattern = r"activeMode:\s*(\d+x\d+)"
        match = re.search(pattern, result)
        if match:
            resolution = match.group(1).split("x")
            return int(resolution[0]), int(resolution[1])
        else:
            image = self.screenshot()
            return image.size

    def dump_hierarchy(self) -> Tuple[str, Node]:
        """returns xml string and hierarchy object"""
        layout = HarmonyUtils.dump_layout(self.serial)
        with open(layout, "r", encoding="utf-8") as f:
            json_content = json.load(f)
        return json.dumps(json_content), parse_json_element(json_content, WindowSize(width=1, height=1))

    def tap(self, x: int, y: int):
        HarmonyUtils.shell(self.serial, "uinput -T -c {} {}".format(x, y))

    def app_current(self) -> CurrentAppResponse:
        echo = HarmonyUtils.shell(self.serial, "hidumper -s WindowManagerService -a '-a'")
        focus_window = re.search(r"Focus window: (\d+)", echo)
        if focus_window:
            focus_window = focus_window.group(1)
        mission_echo = HarmonyUtils.shell(self.serial, "aa dump -a")
        pkg_names = re.findall(r"Mission ID #(\d+)\s+mission name #\[(.*?)\]", mission_echo)
        if focus_window and pkg_names:
            for mission in pkg_names:
                mission_id = mission[0]
                if focus_window == mission_id:
                    mission_name = mission[1]
                    pkg_name = mission_name.split(":")[0].replace("#", "")
                    ability_name = mission_name.split(":")[-1]
                    pid = HarmonyUtils.shell(self.serial, "pidof {}".format(pkg_name)).strip()
                    return CurrentAppResponse(package=pkg_name, activity=ability_name, pid=pid)
        else:
            return None

    def shell(self, command: str) -> ShellResponse:
        result = HarmonyUtils.shell(self.serial, command)
        return ShellResponse(output=result)

    def home(self):
        HarmonyUtils.shell(self.serial, "uinput -K -d 1 -u 1")

    def back(self):
        HarmonyUtils.shell(self.serial, "uinput -K -d 2 -u 2")

    def volume_up(self):
        HarmonyUtils.shell(self.serial, "uinput -K -d 16 -u 16")

    def volume_down(self):
        HarmonyUtils.shell(self.serial, "uinput -K -d 17 -u 17")

    def volume_mute(self):
        HarmonyUtils.shell(self.serial, "uinput -K -d 22 -u 22")

    def app_switch(self):
        HarmonyUtils.shell(self.serial, "uinput -K -d 2076 -d 2049 -u 2076 -u 2049")

    def app_list(self) -> List[AppInfo]:
        results = []
        output = HarmonyUtils.shell(self.serial, "bm dump -a")
        for i in output.split("\n"):
            if "ID" in i:
                continue
            else:
                results.append(AppInfo(packageName=i.strip()))
        return results


def parse_json_element(element, wsize: WindowSize, indexes: List[int] = [0]) -> Optional[Node]:
    """
    Recursively parse an json element into a dictionary format.
    """
    attributes = element.get("attributes", {})
    name = attributes.get("type", "")
    bounds = attributes.get("bounds", "")
    bounds = list(map(int, re.findall(r"\d+", bounds)))
    assert len(bounds) == 4
    rect = Rect(x=bounds[0], y=bounds[1], width=bounds[2] - bounds[0], height=bounds[3] - bounds[1])
    bounds = (
        bounds[0] / wsize.width,
        bounds[1] / wsize.height,
        bounds[2] / wsize.width,
        bounds[3] / wsize.height,
    )
    elem = Node(
        key="-".join(map(str, indexes)),
        name=name,
        bounds=bounds,
        rect=rect,
        properties={key: attributes[key] for key in attributes},
        children=[],
    )
    # Construct xpath for children
    for index, child in enumerate(element.get("children", [])):
        child_node = parse_json_element(child, wsize, indexes + [index])
        if child_node:
            elem.children.append(child_node)

    return elem
