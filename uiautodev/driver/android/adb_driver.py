#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:19:29 by codeskyblue
"""

import logging
import re
import time
from typing import Iterator, List, Optional, Tuple

import adbutils
from PIL import Image

from uiautodev.command_types import CurrentAppResponse
from uiautodev.driver.android.common import parse_xml
from uiautodev.driver.base_driver import BaseDriver
from uiautodev.exceptions import AndroidDriverException
from uiautodev.model import AppInfo, Node, Rect, ShellResponse, WindowSize

logger = logging.getLogger(__name__)

class ADBAndroidDriver(BaseDriver):
    def __init__(self, serial: str):
        super().__init__(serial)
        self.adb_device = adbutils.device(serial)

    def get_current_activity(self) -> str:
        ret = self.adb_device.shell2(["dumpsys", "activity", "activities"], rstrip=True, timeout=5)
        # 使用正则查找包含前台 activity 的行
        match = re.search(r"mResumedActivity:.*? ([\w\.]+\/[\w\.]+)", ret.output)
        if match:
            return match.group(1)  # 返回包名/类名，例如 com.example/.MainActivity
        else:
            return ""
    
    def screenshot(self, id: int) -> Image.Image:
        if id > 0:
            raise AndroidDriverException("multi-display is not supported yet for uiautomator2")
        return self.adb_device.screenshot(display_id=id)

    def shell(self, command: str) -> ShellResponse:
        try:
            ret = self.adb_device.shell2(command, rstrip=True, timeout=20)
            if ret.returncode == 0:
                return ShellResponse(output=ret.output, error=None)
            else:
                return ShellResponse(
                    output="", error=f"exit:{ret.returncode}, output:{ret.output}"
                )
        except Exception as e:
            return ShellResponse(output="", error=f"adb error: {str(e)}")

    def dump_hierarchy(self, display_id: Optional[int] = 0) -> Tuple[str, Node]:
        """returns xml string and hierarchy object"""
        start = time.time()
        try:
            xml_data = self._dump_hierarchy_raw()
            logger.debug("dump_hierarchy cost: %s", time.time() - start)
        except Exception as e:
            raise AndroidDriverException(f"Failed to dump hierarchy: {str(e)}")

        wsize = self.adb_device.window_size()
        logger.debug("window size: %s", wsize)
        return xml_data, parse_xml(
            xml_data, WindowSize(width=wsize[0], height=wsize[1]), display_id
        )

    def _dump_hierarchy_raw(self) -> str:
        """
        uiautomator2 server is conflict with "uiautomator dump" command.

        uiautomator dump errors:
        - ERROR: could not get idle state.
        """
        try:
            return self.adb_device.dump_hierarchy()
        except adbutils.AdbError as e:
            if "Killed" in str(e):
                self.kill_app_process()
            return self.adb_device.dump_hierarchy()
    
    def kill_app_process(self):
        logger.debug("Killing app_process")
        pids = []
        for line in self.adb_device.shell("ps -A || ps").splitlines():
            if "app_process" in line:
                fields = line.split()
                if len(fields) >= 2:
                    pids.append(int(fields[1]))
                    logger.debug(f"App process PID: {fields[1]}")
        for pid in set(pids):
            self.adb_device.shell(f"kill {pid}")

    def tap(self, x: int, y: int):
        self.adb_device.click(x, y)

    def window_size(self) -> Tuple[int, int]:
        w, h = self.adb_device.window_size()
        return (w, h)

    def app_install(self, app_path: str):
        self.adb_device.install(app_path)

    def app_current(self) -> CurrentAppResponse:
        info = self.adb_device.app_current()
        return CurrentAppResponse(
            package=info.package, activity=info.activity, pid=info.pid
        )

    def app_launch(self, package: str, stop_first: bool = True):
        """
        Launch an app and bring it to foreground.
        
        This method:
        1. Checks if the app is installed
        2. Optionally stops the app first to ensure clean launch (default: True)
        3. Uses 'am start' command with resolved main activity to launch the app
        
        Note: By default, this method stops the app first to ensure a clean launch.
        This is more reliable than just starting an app that may already be running in background.
        
        Args:
            package: Package name of the app to launch
            stop_first: Whether to stop the app before launching (default: True)
        """
        if self.adb_device.package_info(package) is None:
            raise AndroidDriverException(f"App not installed: {package}")
        
        # Step 1: Stop the app first to ensure clean launch
        if stop_first:
            print(f"[app_launch] Stopping app {package} before launch")
            logger.info(f"Stopping app {package} before launch")
            try:
                self.app_terminate(package)
                time.sleep(0.5)  # Wait for app to fully stop
                print(f"[app_launch] App {package} stopped successfully")
                logger.info(f"App {package} stopped successfully")
            except Exception as e:
                print(f"[app_launch] Failed to stop {package}: {e}")
                logger.warning(f"Failed to stop {package} before launch: {e}")
        
        # Step 2: Use monkey command to launch the app
        print(f"[app_launch] Launching app {package} using monkey command")
        logger.info(f"Launching app {package} using monkey command")
        try:
            result = self.adb_device.shell2([
                "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"
            ], timeout=10)
            
            if result.returncode == 0:
                print(f"[app_launch] Successfully launched {package} using monkey command")
                logger.info(f"Successfully launched {package} using monkey command")
                time.sleep(0.5)  # Wait for app to appear
                return
            else:
                error_msg = f"monkey command failed for {package}, returncode={result.returncode}, output={result.output}"
                print(f"[app_launch] {error_msg}")
                logger.error(error_msg)
                raise AndroidDriverException(f"Failed to launch app {package}: {result.output}")
        except Exception as e:
            error_msg = f"Failed to launch {package} using monkey: {e}"
            print(f"[app_launch] {error_msg}")
            logger.error(error_msg)
            raise AndroidDriverException(f"Failed to launch app {package}: {e}")
        
        # Old code below (kept for reference, but should not be reached)
        # Get the main activity using 'cmd package resolve-activity'
        # This is more reliable than package_info.main_activity
        try:
            # Use 'cmd package resolve-activity' to get the launcher activity
            result = self.adb_device.shell2([
                "cmd", "package", "resolve-activity", "--brief", package
            ], rstrip=True, timeout=5)
            
            if result.returncode == 0 and result.output:
                # Parse the output to get activity name
                # Output format is:
                #   priority=0 preferredOrder=0 match=0x108000 specificIndex=-1 isDefault=false
                #   com.package/.Activity
                # The activity is usually on the last line
                lines = [line.strip() for line in result.output.strip().split('\n') if line.strip()]
                activity_line = None
                
                # Try to find activity in output (usually the last line that contains package name and '/')
                for line in reversed(lines):  # Check from last line first
                    if '/' in line and package in line and not line.startswith('priority'):
                        # Remove "name=" prefix if present
                        activity_line = line.replace('name=', '').strip()
                        break
                
                if activity_line and '/' in activity_line:
                    # Launch using the resolved activity
                    logger.info(f"Attempting to launch {package} with activity: {activity_line}")
                    launch_result = self.adb_device.shell2([
                        "am", "start", "-n", activity_line
                    ], timeout=5)
                    if launch_result.returncode == 0:
                        logger.info(f"Successfully launched {package} using activity: {activity_line}")
                        # Wait a moment for app to appear
                        time.sleep(0.3)
                        return
                    else:
                        logger.warning(f"am start failed for {activity_line}, returncode={launch_result.returncode}, output={launch_result.output}")
                else:
                    logger.warning(f"Could not parse activity from resolve-activity output. Lines: {lines}, Output: {result.output}")
            
            # Fallback: try using package_info if resolve-activity fails
            logger.warning(f"Could not resolve activity for {package}, trying package_info")
            package_info = self.adb_device.package_info(package)
            if isinstance(package_info, dict):
                main_activity = package_info.get('main_activity')
            else:
                main_activity = getattr(package_info, 'main_activity', None)
            
            if main_activity:
                activity_name = main_activity if main_activity.startswith(".") else f"{package}/{main_activity}"
                launch_result = self.adb_device.shell2([
                    "am", "start", "-n", activity_name
                ], timeout=5)
                if launch_result.returncode == 0:
                    logger.info(f"Successfully launched {package} using main activity: {activity_name}")
                    time.sleep(0.3)
                    return
                else:
                    logger.warning(f"am start failed for {activity_name}: {launch_result.output}")
        except Exception as e:
            logger.warning(f"Failed to launch using resolved activity: {e}, falling back to app_start")
        
        # Final fallback: use app_start
        logger.info(f"Using app_start as fallback for {package}")
        try:
            self.adb_device.app_start(package)
            logger.info(f"app_start completed for {package}")
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"app_start failed for {package}: {e}")
            raise AndroidDriverException(f"Failed to launch app {package}: {e}")
    
    def app_terminate(self, package: str):
        self.adb_device.app_stop(package)

    def home(self):
        self.adb_device.keyevent("HOME")
    
    def wake_up(self):
        self.adb_device.keyevent("WAKEUP")
    
    def back(self):
        self.adb_device.keyevent("BACK")
    
    def app_switch(self):
        self.adb_device.keyevent("APP_SWITCH")
    
    def volume_up(self):
        self.adb_device.keyevent("VOLUME_UP")
    
    def volume_down(self):
        self.adb_device.keyevent("VOLUME_DOWN")
    
    def volume_mute(self):
        self.adb_device.keyevent("VOLUME_MUTE")

    def get_app_version(self, package_name: str) -> dict:
        """
        Get the version information of an app, including mainVersion and subVersion.

        Args:
            package_name (str): The package name of the app.

        Returns:
            dict: A dictionary containing mainVersion and subVersion.
        """
        output = self.adb_device.shell(["dumpsys", "package", package_name])

        # versionName
        m = re.search(r"versionName=(?P<name>[^\s]+)", output)
        version_name = m.group("name") if m else ""
        if version_name == "null":  # Java dumps "null" for null values
            version_name = None

        # versionCode
        m = re.search(r"versionCode=(?P<code>\d+)", output)
        version_code = m.group("code") if m else ""
        version_code = int(version_code) if version_code.isdigit() else None

        return {
            "versionName": version_name,
            "versionCode": version_code
        }

    def app_list(self) -> List[AppInfo]:
        results = []
        output = self.adb_device.shell(["pm", "list", "packages", '-3'])
        for m in re.finditer(r"^package:([^\s]+)\r?$", output, re.M):
            packageName = m.group(1)
            # get version
            version_info = self.get_app_version(packageName)
            app_info = AppInfo(
                packageName=packageName,
                versionName=version_info.get("versionName"),
                versionCode=version_info.get("versionCode")
            )
            results.append(app_info)
        return results

    def open_app_file(self, package: str) -> Iterator[bytes]:
        line = self.adb_device.shell(f"pm path {package}")
        assert isinstance(line, str)
        if not line.startswith("package:"):
            raise AndroidDriverException(f"Failed to get package path: {line}")
        remote_path = line.split(':', 1)[1]
        yield from self.adb_device.sync.iter_content(remote_path)
    
    def send_keys(self, text: str):
        self.adb_device.send_keys(text)
    
    def clear_text(self):
        for _ in range(3):
            self.adb_device.shell2("input keyevent DEL --longpress")
