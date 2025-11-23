#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Recording API router for mobile UI automation recorder
Created based on record.md requirements
"""

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from uiautodev.model import RecordEvent, RecordScript, SaveScriptRequest, SaveScriptResponse
from uiautodev.provider import AndroidProvider
from uiautodev.command_proxy import send_command
from uiautodev.command_types import Command, TapRequest, SendKeysRequest, By, FindElementRequest
from uiautodev.utils.common import node_travel

logger = logging.getLogger(__name__)

router = APIRouter()

# Storage directory for recorded scripts
STORAGE_DIR = Path.home() / ".uiautodev" / "records"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Timing constants for script execution
ACTION_DELAY = 0.5  # Delay between actions (seconds)
KEYBOARD_WAIT = 0.3  # Wait time for keyboard to appear (seconds)
APP_LAUNCH_WAIT = 2.0  # Wait time for app to fully launch (seconds)


class RecordListResponse(BaseModel):
    """Response model for listing scripts"""
    scripts: List[RecordScript]
    total: int


class ScriptGenerator:
    """Generate scripts in different formats"""
    
    @staticmethod
    def escape_python_string(s: str) -> str:
        """Escape special characters for Python string literals"""
        if s is None:
            return ""
        # Escape backslashes first, then quotes
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    
    @staticmethod
    def escape_js_string(s: str) -> str:
        """Escape special characters for JavaScript string literals"""
        if s is None:
            return ""
        # Escape backslashes first, then quotes
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    
    @staticmethod
    def escape_java_string(s: str) -> str:
        """Escape special characters for Java string literals"""
        if s is None:
            return ""
        # Escape backslashes first, then quotes
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    
    @staticmethod
    def escape_swift_string(s: str) -> str:
        """Escape special characters for Swift string literals"""
        if s is None:
            return ""
        # Escape backslashes first, then quotes
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    
    @staticmethod
    def generate_appium_python(script: RecordScript) -> str:
        """Generate Appium Python script"""
        lines = [
            "from appium import webdriver",
            "",
            f'driver = webdriver.Remote("http://localhost:4723/wd/hub", {{',
            f'    "platformName": "{script.platform.capitalize()}",',
        ]
        
        if script.deviceSerial:
            escaped_serial = ScriptGenerator.escape_python_string(script.deviceSerial)
            lines.append(f'    "deviceName": "{escaped_serial}",')
        if script.appPackage:
            escaped_package = ScriptGenerator.escape_python_string(script.appPackage)
            lines.append(f'    "appPackage": "{escaped_package}",')
        if script.appActivity:
            escaped_activity = ScriptGenerator.escape_python_string(script.appActivity)
            lines.append(f'    "appActivity": "{escaped_activity}"')
        
        lines.append("})")
        lines.append("")
        
        for event in script.events:
            if event.action == "tap":
                if event.selector and event.selector.id:
                    escaped_id = ScriptGenerator.escape_python_string(event.selector.id)
                    lines.append(f'driver.find_element("id", "{escaped_id}").click()')
                elif event.selector and event.selector.text:
                    escaped_text = ScriptGenerator.escape_python_string(event.selector.text)
                    lines.append(f'driver.find_element("xpath", "//*[@text=\'{escaped_text}\']").click()')
                elif event.x is not None and event.y is not None:
                    lines.append(f'driver.tap([({event.x}, {event.y})])')
            elif event.action == "input":
                if event.selector and event.selector.id:
                    escaped_id = ScriptGenerator.escape_python_string(event.selector.id)
                    escaped_value = ScriptGenerator.escape_python_string(event.value or "")
                    lines.append(f'driver.find_element("id", "{escaped_id}").send_keys("{escaped_value}")')
                elif event.selector and event.selector.text:
                    escaped_text = ScriptGenerator.escape_python_string(event.selector.text)
                    escaped_value = ScriptGenerator.escape_python_string(event.value or "")
                    lines.append(f'driver.find_element("xpath", "//*[@text=\'{escaped_text}\']").send_keys("{escaped_value}")')
            elif event.action == "swipe":
                if event.x1 is not None and event.y1 is not None and event.x2 is not None and event.y2 is not None:
                    lines.append(f'driver.swipe({event.x1}, {event.y1}, {event.x2}, {event.y2}, {event.duration or 1000})')
            elif event.action == "back":
                lines.append('driver.back()')
            elif event.action == "home":
                lines.append('driver.press_keycode(3)  # HOME key')
        
        lines.append("")
        lines.append("driver.quit()")
        return "\n".join(lines)
    
    @staticmethod
    def generate_appium_js(script: RecordScript) -> str:
        """Generate Appium JavaScript script (WebDriverIO)"""
        lines = [
            "const { remote } = require('webdriverio');",
            "",
            "(async () => {",
            "    const driver = await remote({",
            f'        platformName: "{script.platform.capitalize()}",',
        ]
        
        if script.deviceSerial:
            escaped_serial = ScriptGenerator.escape_js_string(script.deviceSerial)
            lines.append(f'        deviceName: "{escaped_serial}",')
        if script.appPackage:
            escaped_package = ScriptGenerator.escape_js_string(script.appPackage)
            lines.append(f'        appPackage: "{escaped_package}",')
        if script.appActivity:
            escaped_activity = ScriptGenerator.escape_js_string(script.appActivity)
            lines.append(f'        appActivity: "{escaped_activity}"')
        
        lines.append("    });")
        lines.append("")
        
        for event in script.events:
            if event.action == "tap":
                if event.selector and event.selector.id:
                    escaped_id = ScriptGenerator.escape_js_string(event.selector.id)
                    lines.append(f'    await driver.$("#{escaped_id}").click();')
                elif event.selector and event.selector.text:
                    escaped_text = ScriptGenerator.escape_js_string(event.selector.text)
                    lines.append(f'    await driver.$("//*[@text=\'{escaped_text}\']").click();')
            elif event.action == "input":
                if event.selector and event.selector.id:
                    escaped_id = ScriptGenerator.escape_js_string(event.selector.id)
                    escaped_value = ScriptGenerator.escape_js_string(event.value or "")
                    lines.append(f'    await driver.$("#{escaped_id}").setValue("{escaped_value}");')
            elif event.action == "back":
                lines.append('    await driver.back();')
        
        lines.append("")
        lines.append("    await driver.deleteSession();")
        lines.append("})();")
        return "\n".join(lines)
    
    @staticmethod
    def generate_uiautomator2(script: RecordScript) -> str:
        """Generate UIAutomator2 Java/Kotlin script"""
        lines = [
            "import androidx.test.uiautomator.UiDevice;",
            "import androidx.test.uiautomator.UiObject;",
            "import androidx.test.uiautomator.UiSelector;",
            "",
            "UiDevice device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation());",
            "",
        ]
        
        for event in script.events:
            if event.action == "tap":
                if event.selector and event.selector.id:
                    escaped_id = ScriptGenerator.escape_java_string(event.selector.id)
                    lines.append(f'UiObject element = device.findObject(new UiSelector().resourceId("{escaped_id}"));')
                    lines.append("element.click();")
                elif event.selector and event.selector.text:
                    escaped_text = ScriptGenerator.escape_java_string(event.selector.text)
                    lines.append(f'UiObject element = device.findObject(new UiSelector().text("{escaped_text}"));')
                    lines.append("element.click();")
            elif event.action == "input":
                if event.selector and event.selector.id:
                    escaped_id = ScriptGenerator.escape_java_string(event.selector.id)
                    escaped_value = ScriptGenerator.escape_java_string(event.value or "")
                    lines.append(f'UiObject element = device.findObject(new UiSelector().resourceId("{escaped_id}"));')
                    lines.append(f'element.setText("{escaped_value}");')
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_xcuitest(script: RecordScript) -> str:
        """Generate XCUITest Swift script"""
        lines = [
            "import XCTest",
            "",
            "class RecordedTest: XCTestCase {",
            "    var app: XCUIApplication!",
            "",
            "    override func setUp() {",
            "        super.setUp()",
            "        app = XCUIApplication()",
            "        app.launch()",
            "    }",
            "",
            "    func testRecorded() {",
        ]
        
        for event in script.events:
            if event.action == "tap":
                if event.selector and event.selector.id:
                    escaped_id = ScriptGenerator.escape_swift_string(event.selector.id)
                    lines.append(f'        app.buttons["{escaped_id}"].tap()')
                elif event.selector and event.selector.text:
                    escaped_text = ScriptGenerator.escape_swift_string(event.selector.text)
                    lines.append(f'        app.staticTexts["{escaped_text}"].tap()')
            elif event.action == "input":
                if event.selector and event.selector.id:
                    escaped_id = ScriptGenerator.escape_swift_string(event.selector.id)
                    escaped_value = ScriptGenerator.escape_swift_string(event.value or "")
                    lines.append(f'        app.textFields["{escaped_id}"].typeText("{escaped_value}")')
        
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)
    
    @staticmethod
    def generate(script: RecordScript, script_type: str) -> str:
        """Generate script based on type"""
        generators = {
            "appium_python": ScriptGenerator.generate_appium_python,
            "appium_js": ScriptGenerator.generate_appium_js,
            "uiautomator2": ScriptGenerator.generate_uiautomator2,
            "xcuitest": ScriptGenerator.generate_xcuitest,
        }
        
        generator = generators.get(script_type)
        if not generator:
            raise ValueError(f"Unsupported script type: {script_type}")
        
        return generator(script)


def save_script_to_file(script: RecordScript) -> Path:
    """Save script to file system"""
    script_id = script.id or str(uuid.uuid4())
    script_file = STORAGE_DIR / f"{script_id}.json"
    
    script_dict = script.model_dump()
    script_dict["id"] = script_id
    
    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(script_dict, f, ensure_ascii=False, indent=2)
    
    return script_file


def load_script_from_file(script_id: str) -> Optional[RecordScript]:
    """Load script from file system"""
    script_file = STORAGE_DIR / f"{script_id}.json"
    if not script_file.exists():
        return None
    
    with open(script_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return RecordScript(**data)


def list_scripts() -> List[RecordScript]:
    """List all saved scripts"""
    scripts = []
    for script_file in STORAGE_DIR.glob("*.json"):
        try:
            with open(script_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                scripts.append(RecordScript(**data))
        except Exception as e:
            logger.error(f"Failed to load script {script_file}: {e}")
    
    # Sort by updatedAt descending
    scripts.sort(key=lambda x: x.updatedAt or 0, reverse=True)
    return scripts


@router.post("/save", response_model=SaveScriptResponse)
def save_script(request: SaveScriptRequest) -> SaveScriptResponse:
    """Save recorded script"""
    try:
        script_id = str(uuid.uuid4())
        current_time = time.time()
        
        script = RecordScript(
            id=script_id,
            name=request.name,
            platform=request.platform,
            deviceSerial=request.deviceSerial,
            appPackage=request.appPackage,
            appActivity=request.appActivity,
            events=request.events,
            createdAt=current_time,
            updatedAt=current_time,
            scriptType=request.scriptType,
        )
        
        save_script_to_file(script)
        
        return SaveScriptResponse(
            id=script_id,
            success=True,
            message="Script saved successfully",
        )
    except Exception as e:
        logger.exception("Failed to save script")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=RecordListResponse)
def list_recorded_scripts() -> RecordListResponse:
    """List all recorded scripts"""
    try:
        scripts = list_scripts()
        return RecordListResponse(scripts=scripts, total=len(scripts))
    except Exception as e:
        logger.exception("Failed to list scripts")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{script_id}", response_model=RecordScript)
def get_script(script_id: str) -> RecordScript:
    """Get script by ID"""
    script = load_script_from_file(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.delete("/{script_id}")
def delete_script(script_id: str) -> Dict[str, bool]:
    """Delete script by ID"""
    script_file = STORAGE_DIR / f"{script_id}.json"
    if not script_file.exists():
        raise HTTPException(status_code=404, detail="Script not found")
    
    try:
        script_file.unlink()
        return {"success": True}
    except Exception as e:
        logger.exception("Failed to delete script")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{script_id}/generate")
def generate_script(
    script_id: str,
    script_type: str = Query(default="appium_python", description="Script type: appium_python, appium_js, uiautomator2, xcuitest"),
) -> Dict[str, str]:
    """Generate script in specified format"""
    script = load_script_from_file(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    try:
        generated_code = ScriptGenerator.generate(script, script_type)
        return {
            "script": generated_code,
            "type": script_type,
            "id": script_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate script")
        raise HTTPException(status_code=500, detail=str(e))



class ScriptExecutionResult(BaseModel):
    """Result of script execution"""
    step: int
    action: str
    success: bool
    message: str
    error: Optional[str] = None


class ExecuteScriptResponse(BaseModel):
    """Response model for script execution"""
    script_id: Optional[str] = None  # May be None for frontend scripts
    total_steps: int
    executed_steps: int
    success: bool
    results: List[ScriptExecutionResult]
    error: Optional[str] = None


def find_element_by_selector(driver, selector):
    """Find element by selector using hierarchy dump"""
    print(f"[execute_script] Finding element with selector: {selector}")
    logger.info(f"Finding element with selector: {selector}")
    
    try:
        _, root_node = driver.dump_hierarchy()
        
        # Try different selector strategies
        if selector.id:
            print(f"[execute_script] Searching by resource-id: {selector.id}")
            logger.info(f"Searching by resource-id: {selector.id}")
            for node in node_travel(root_node):
                if node.properties.get("resource-id") == selector.id:
                    print(f"[execute_script] Found element by id: {selector.id}")
                    logger.info(f"Found element by id: {selector.id}")
                    return node
        
        if selector.text:
            print(f"[execute_script] Searching by text: {selector.text}")
            logger.info(f"Searching by text: {selector.text}")
            for node in node_travel(root_node):
                if node.properties.get("text") == selector.text:
                    print(f"[execute_script] Found element by text: {selector.text}")
                    logger.info(f"Found element by text: {selector.text}")
                    return node
        
        if selector.contentDesc:
            print(f"[execute_script] Searching by content-desc: {selector.contentDesc}")
            logger.info(f"Searching by content-desc: {selector.contentDesc}")
            for node in node_travel(root_node):
                if node.properties.get("content-desc") == selector.contentDesc:
                    print(f"[execute_script] Found element by content-desc: {selector.contentDesc}")
                    logger.info(f"Found element by content-desc: {selector.contentDesc}")
                    return node
        
        print(f"[execute_script] Element not found with selector: {selector}")
        logger.warning(f"Element not found with selector: {selector}")
        return None
    except Exception as e:
        print(f"[execute_script] Error finding element: {e}")
        logger.error(f"Error finding element: {e}")
        return None


def execute_event(driver, event: RecordEvent, step_index: int) -> ScriptExecutionResult:
    """Execute a single recorded event"""
    print(f"[execute_script] Step {step_index + 1}: Executing action '{event.action}'")
    logger.info(f"Step {step_index + 1}: Executing action '{event.action}'")
    
    try:
        if event.action == "tap":
            if event.selector:
                # Try to use direct element operation if driver supports it (UIAutomator2)
                # Check if driver has 'ud' attribute (U2AndroidDriver)
                if hasattr(driver, 'ud'):
                    # U2AndroidDriver supports direct element operation
                    print(f"[execute_script] Using UIAutomator2 direct element operation (U2)")
                    logger.info("Using UIAutomator2 direct element operation (U2)")
                    try:
                        ud = driver.ud
                        if event.selector.id:
                            print(f"[execute_script] [U2] Clicking element by resource-id: {event.selector.id}")
                            logger.info(f"[U2] Clicking element by resource-id: {event.selector.id}")
                            ud(resourceId=event.selector.id).click()
                            # U2 click successful, return immediately
                            print(f"[execute_script] [U2] Direct element click successful")
                            logger.info("[U2] Direct element click successful")
                            # Wait a bit between actions
                            time.sleep(ACTION_DELAY)
                            return ScriptExecutionResult(
                                step=step_index + 1,
                                action=event.action,
                                success=True,
                                message=f"Action '{event.action}' executed successfully via U2 direct click"
                            )
                        elif event.selector.text:
                            print(f"[execute_script] [U2] Clicking element by text: {event.selector.text}")
                            logger.info(f"[U2] Clicking element by text: {event.selector.text}")
                            ud(text=event.selector.text).click()
                            # U2 click successful, return immediately
                            print(f"[execute_script] [U2] Direct element click successful")
                            logger.info("[U2] Direct element click successful")
                            # Wait a bit between actions
                            time.sleep(ACTION_DELAY)
                            return ScriptExecutionResult(
                                step=step_index + 1,
                                action=event.action,
                                success=True,
                                message=f"Action '{event.action}' executed successfully via U2 direct click"
                            )
                        elif event.selector.contentDesc:
                            print(f"[execute_script] [U2] Clicking element by description: {event.selector.contentDesc}")
                            logger.info(f"[U2] Clicking element by description: {event.selector.contentDesc}")
                            ud(description=event.selector.contentDesc).click()
                            # U2 click successful, return immediately
                            print(f"[execute_script] [U2] Direct element click successful")
                            logger.info("[U2] Direct element click successful")
                            # Wait a bit between actions
                            time.sleep(ACTION_DELAY)
                            return ScriptExecutionResult(
                                step=step_index + 1,
                                action=event.action,
                                success=True,
                                message=f"Action '{event.action}' executed successfully via U2 direct click"
                            )
                        else:
                            # Fallback to coordinate-based approach
                            raise ValueError("No valid selector found")
                    except Exception as e:
                        print(f"[execute_script] [U2] Direct element operation failed: {e}, falling back to coordinate-based")
                        logger.warning(f"[U2] Direct element operation failed: {e}, falling back to coordinate-based")
                        print(f"[execute_script] Switching to coordinate-based execution method")
                        logger.info("Switching to coordinate-based execution method")
                        # Fallback to coordinate-based approach
                        print(f"[execute_script] [COORDINATE] Calculating coordinates from element bounds")
                        logger.info("[COORDINATE] Calculating coordinates from element bounds")
                        node = find_element_by_selector(driver, event.selector)
                        if node:
                            # Use rect if available (pixel coordinates), otherwise convert bounds (normalized) to pixels
                            if node.rect:
                                # rect contains actual pixel coordinates
                                center_x = node.rect.x + node.rect.width // 2
                                center_y = node.rect.y + node.rect.height // 2
                                print(f"[execute_script] [COORDINATE] Tapping element at ({center_x}, {center_y}) using rect")
                                logger.info(f"[COORDINATE] Tapping element at ({center_x}, {center_y}) using rect")
                            elif node.bounds:
                                # bounds are normalized (0-1), need to convert to pixels
                                wsize = driver.window_size()
                                center_x = int((node.bounds[0] + node.bounds[2]) / 2 * wsize[0])
                                center_y = int((node.bounds[1] + node.bounds[3]) / 2 * wsize[1])
                                print(f"[execute_script] [COORDINATE] Tapping element at ({center_x}, {center_y}) using bounds (window size: {wsize})")
                                logger.info(f"[COORDINATE] Tapping element at ({center_x}, {center_y}) using bounds (window size: {wsize})")
                            else:
                                # No bounds or rect available
                                center_x = None
                                center_y = None
                            
                            if center_x is not None and center_y is not None:
                                driver.tap(center_x, center_y)
                            else:
                                error_msg = f"Could not find element bounds/rect for tap action"
                                print(f"[execute_script] {error_msg}")
                                logger.error(error_msg)
                                return ScriptExecutionResult(
                                    step=step_index + 1,
                                    action=event.action,
                                    success=False,
                                    message=error_msg,
                                    error=error_msg
                                )
                        else:
                            error_msg = f"Could not find element with selector: {event.selector}"
                            print(f"[execute_script] {error_msg}")
                            logger.error(error_msg)
                            return ScriptExecutionResult(
                                step=step_index + 1,
                                action=event.action,
                                success=False,
                                message=error_msg,
                                error=error_msg
                            )
                else:
                    # For other drivers, use coordinate-based approach
                    print(f"[execute_script] Using coordinate-based execution method (no U2 support)")
                    logger.info("Using coordinate-based execution method (no U2 support)")
                    node = find_element_by_selector(driver, event.selector)
                    if node:
                        # Use rect if available (pixel coordinates), otherwise convert bounds (normalized) to pixels
                        if node.rect:
                            # rect contains actual pixel coordinates
                            center_x = node.rect.x + node.rect.width // 2
                            center_y = node.rect.y + node.rect.height // 2
                            print(f"[execute_script] [COORDINATE] Tapping element at ({center_x}, {center_y}) using rect")
                            logger.info(f"[COORDINATE] Tapping element at ({center_x}, {center_y}) using rect")
                        elif node.bounds:
                            # bounds are normalized (0-1), need to convert to pixels
                            wsize = driver.window_size()
                            center_x = int((node.bounds[0] + node.bounds[2]) / 2 * wsize[0])
                            center_y = int((node.bounds[1] + node.bounds[3]) / 2 * wsize[1])
                            print(f"[execute_script] [COORDINATE] Tapping element at ({center_x}, {center_y}) using bounds (window size: {wsize})")
                            logger.info(f"[COORDINATE] Tapping element at ({center_x}, {center_y}) using bounds (window size: {wsize})")
                        else:
                            # No bounds or rect available
                            center_x = None
                            center_y = None
                        
                        if center_x is not None and center_y is not None:
                            driver.tap(center_x, center_y)
                    else:
                        # Fallback to coordinates if available
                        if event.x is not None and event.y is not None:
                            print(f"[execute_script] No bounds/rect, tapping at coordinates ({event.x}, {event.y})")
                            logger.info(f"No bounds/rect, tapping at coordinates ({event.x}, {event.y})")
                            driver.tap(int(event.x), int(event.y))
                        else:
                            error_msg = f"Could not find element bounds/rect or coordinates for tap action"
                            print(f"[execute_script] {error_msg}")
                            logger.error(error_msg)
                            return ScriptExecutionResult(
                                step=step_index + 1,
                                action=event.action,
                                success=False,
                                message=error_msg,
                                error=error_msg
                            )
            else:
                # No selector, fallback to coordinates if available
                if event.x is not None and event.y is not None:
                    print(f"[execute_script] [COORDINATE] Tapping at recorded coordinates ({event.x}, {event.y})")
                    logger.info(f"[COORDINATE] Tapping at recorded coordinates ({event.x}, {event.y})")
                    driver.tap(int(event.x), int(event.y))
                else:
                    error_msg = "No selector or coordinates provided for tap action"
                    print(f"[execute_script] {error_msg}")
                    logger.error(error_msg)
                    return ScriptExecutionResult(
                        step=step_index + 1,
                        action=event.action,
                        success=False,
                        message=error_msg,
                        error=error_msg
                    )
        
        elif event.action == "input":
            if not event.selector:
                error_msg = "No selector provided for input action"
                print(f"[execute_script] {error_msg}")
                logger.error(error_msg)
                return ScriptExecutionResult(
                    step=step_index + 1,
                    action=event.action,
                    success=False,
                    message=error_msg,
                    error=error_msg
                )
            
            # Check if using U2 or coordinate-based
            if hasattr(driver, 'ud'):
                print(f"[execute_script] [U2] Using UIAutomator2 for input operation")
                logger.info("[U2] Using UIAutomator2 for input operation")
            else:
                print(f"[execute_script] [COORDINATE] Using coordinate-based method for input operation")
                logger.info("[COORDINATE] Using coordinate-based method for input operation")
            
            node = find_element_by_selector(driver, event.selector)
            if node:
                # Use rect if available (pixel coordinates), otherwise convert bounds (normalized) to pixels
                if node.rect:
                    # rect contains actual pixel coordinates
                    center_x = node.rect.x + node.rect.width // 2
                    center_y = node.rect.y + node.rect.height // 2
                    print(f"[execute_script] [COORDINATE] Focusing input field at ({center_x}, {center_y}) using rect")
                    logger.info(f"[COORDINATE] Focusing input field at ({center_x}, {center_y}) using rect")
                elif node.bounds:
                    # bounds are normalized (0-1), need to convert to pixels
                    wsize = driver.window_size()
                    center_x = int((node.bounds[0] + node.bounds[2]) / 2 * wsize[0])
                    center_y = int((node.bounds[1] + node.bounds[3]) / 2 * wsize[1])
                    print(f"[execute_script] [COORDINATE] Focusing input field at ({center_x}, {center_y}) using bounds (window size: {wsize})")
                    logger.info(f"[COORDINATE] Focusing input field at ({center_x}, {center_y}) using bounds (window size: {wsize})")
                else:
                    error_msg = f"Could not find input element bounds/rect with selector: {event.selector}"
                    print(f"[execute_script] {error_msg}")
                    logger.error(error_msg)
                    return ScriptExecutionResult(
                        step=step_index + 1,
                        action=event.action,
                        success=False,
                        message=error_msg,
                        error=error_msg
                    )
                
                if center_x is not None and center_y is not None:
                    driver.tap(center_x, center_y)
                time.sleep(KEYBOARD_WAIT)  # Wait for keyboard
                
                # Clear existing text and input new text
                print(f"[execute_script] Inputting text: {event.value}")
                logger.info(f"Inputting text: {event.value}")
                driver.clear_text()
                if event.value:
                    driver.send_keys(event.value)
            else:
                error_msg = f"Could not find input element with selector: {event.selector}"
                print(f"[execute_script] {error_msg}")
                logger.error(error_msg)
                return ScriptExecutionResult(
                    step=step_index + 1,
                    action=event.action,
                    success=False,
                    message=error_msg,
                    error=error_msg
                )
        
        elif event.action == "swipe":
            if event.x1 is not None and event.y1 is not None and event.x2 is not None and event.y2 is not None:
                print(f"[execute_script] [COORDINATE] Swiping from ({event.x1}, {event.y1}) to ({event.x2}, {event.y2})")
                logger.info(f"[COORDINATE] Swiping from ({event.x1}, {event.y1}) to ({event.x2}, {event.y2})")
                # Use adb shell input swipe
                if hasattr(driver, 'adb_device'):
                    duration = int(event.duration or 1000) if event.duration else 1000
                    driver.adb_device.shell(f"input swipe {int(event.x1)} {int(event.y1)} {int(event.x2)} {int(event.y2)} {duration}")
            else:
                error_msg = "Missing coordinates for swipe action"
                print(f"[execute_script] {error_msg}")
                logger.error(error_msg)
                return ScriptExecutionResult(
                    step=step_index + 1,
                    action=event.action,
                    success=False,
                    message=error_msg,
                    error=error_msg
                )
        
        elif event.action == "back":
            print(f"[execute_script] Pressing back button")
            logger.info("Pressing back button")
            driver.back()
        
        elif event.action == "home":
            print(f"[execute_script] Pressing home button")
            logger.info("Pressing home button")
            driver.home()
        
        else:
            error_msg = f"Unsupported action: {event.action}"
            print(f"[execute_script] {error_msg}")
            logger.warning(error_msg)
            return ScriptExecutionResult(
                step=step_index + 1,
                action=event.action,
                success=False,
                message=error_msg,
                error=error_msg
            )
        
        # Wait a bit between actions
        time.sleep(ACTION_DELAY)
        
        print(f"[execute_script] Step {step_index + 1} completed successfully")
        logger.info(f"Step {step_index + 1} completed successfully")
        return ScriptExecutionResult(
            step=step_index + 1,
            action=event.action,
            success=True,
            message=f"Action '{event.action}' executed successfully"
        )
    
    except Exception as e:
        error_msg = f"Error executing action '{event.action}': {e}"
        print(f"[execute_script] {error_msg}")
        logger.exception(error_msg)
        return ScriptExecutionResult(
            step=step_index + 1,
            action=event.action,
            success=False,
            message=error_msg,
            error=str(e)
        )


class ExecuteScriptRequest(BaseModel):
    """Request model for executing script"""
    script: Optional[RecordScript] = None  # Script data from frontend
    script_id: Optional[str] = None  # Script ID to load from file system
    device_serial: Optional[str] = None  # Override device serial


@router.post("/execute", response_model=ExecuteScriptResponse)
def execute_script(request: ExecuteScriptRequest):
    """Execute a recorded script
    
    Supports two modes:
    1. Execute script from frontend: provide 'script' in request body
    2. Execute script from file: provide 'script_id' in request body
    """
    script = None
    
    # Mode 1: Script data from frontend
    if request.script:
        print(f"[execute_script] Starting execution of script from frontend (name: {request.script.name})")
        logger.info(f"Starting execution of script from frontend (name: {request.script.name})")
        script = request.script
    
    # Mode 2: Load script from file system
    elif request.script_id:
        print(f"[execute_script] Starting execution of script {request.script_id}")
        logger.info(f"Starting execution of script {request.script_id}")
        script = load_script_from_file(request.script_id)
        if not script:
            error_msg = f"Script {request.script_id} not found"
            print(f"[execute_script] {error_msg}")
            logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)
    
    else:
        error_msg = "Either 'script' or 'script_id' must be provided"
        print(f"[execute_script] {error_msg}")
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    if not script:
        error_msg = "Script data is required"
        print(f"[execute_script] {error_msg}")
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Get device serial (from request, script, or error)
        serial = request.device_serial or script.deviceSerial
        if not serial:
            error_msg = "Device serial is required for script execution"
            print(f"[execute_script] {error_msg}")
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        print(f"[execute_script] Using device: {serial}")
        logger.info(f"Using device: {serial}")
        
        # Get driver based on platform
        if script.platform == "android":
            provider = AndroidProvider()
            driver = provider.get_device_driver(serial)
            # Log driver type
            if hasattr(driver, 'ud'):
                print(f"[execute_script] Driver type: UIAutomator2 (U2) - supports direct element operation")
                logger.info("Driver type: UIAutomator2 (U2) - supports direct element operation")
            else:
                print(f"[execute_script] Driver type: ADB - using coordinate-based execution")
                logger.info("Driver type: ADB - using coordinate-based execution")
        else:
            error_msg = f"Unsupported platform: {script.platform}"
            print(f"[execute_script] {error_msg}")
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Launch app if appPackage is specified
        if script.appPackage:
            print(f"[execute_script] Launching app: {script.appPackage}")
            logger.info(f"Launching app: {script.appPackage}")
            from uiautodev.command_proxy import app_launch
            from uiautodev.command_types import AppLaunchRequest
            app_launch(driver, AppLaunchRequest(package=script.appPackage, stop=True))
            time.sleep(APP_LAUNCH_WAIT)  # Wait for app to fully launch
        
        # Execute events
        results = []
        executed_count = 0
        
        print(f"[execute_script] Executing {len(script.events)} events")
        logger.info(f"Executing {len(script.events)} events")
        
        for i, event in enumerate(script.events):
            result = execute_event(driver, event, i)
            results.append(result)
            if result.success:
                executed_count += 1
            else:
                print(f"[execute_script] Step {i + 1} failed: {result.error}")
                logger.warning(f"Step {i + 1} failed: {result.error}")
                # Continue execution even if one step fails
        
        success = executed_count == len(script.events)
        print(f"[execute_script] Script execution completed: {executed_count}/{len(script.events)} steps successful")
        logger.info(f"Script execution completed: {executed_count}/{len(script.events)} steps successful")
        
        return ExecuteScriptResponse(
            script_id=script.id or request.script_id or "frontend_script",
            total_steps=len(script.events),
            executed_steps=executed_count,
            success=success,
            results=results
        )
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to execute script: {e}"
        print(f"[execute_script] {error_msg}")
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=str(e))
