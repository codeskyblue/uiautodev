#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sat Apr 13 2024 22:35:03 by codeskyblue
"""

import enum
import logging
from typing import Dict, Union

from pydantic import BaseModel

from uiautodev import command_proxy
from uiautodev.command_types import Command
from uiautodev.driver.base_driver import BaseDriver
from uiautodev.provider import AndroidProvider

logger = logging.getLogger(__name__)

class CommandStep(BaseModel):
    method: Union[str, Command]
    params: Dict[str, str]
    skip: bool = False
    ignore_error: bool = False


class CompareEnum(str, enum.Enum):
    EQUAL = "equal"
    CONTAINS = "contains"
    NOT_EQUAL = "not_equal"
    NOT_CONTAINS = "not_contains"


class CompareCheckStep(BaseModel):
    method: CompareEnum
    value_a: str
    value_b: str
    skip: bool = False


def run_driver_command(driver: BaseDriver, command: Command, params: dict):
    model = command_proxy.get_command_params_type(command)
    params_obj = model.model_validate(params) if params else None
    # print("Params:", params, params_obj)
    result = command_proxy.send_command(driver, command, params_obj)
    return result

def run():
    # all params key and value should be string
    # Step中
    # 入参类型在为前端保存一份，后端需要同步兼容
    # params所有的key和value都是string类型
    # 出参类型支持重命名 result
    # - key: string, old_key: string, desc: string
    # eg. "WIDTH", "width", "屏幕宽度"
    steps = [
        CommandStep(
            method=Command.APP_LAUNCH,
            params= {
                "package": "com.saucelabs.mydemoapp.android",
                "stop": "true" # bool
            }
        ),
        CommandStep(
            method=Command.GET_WINDOW_SIZE,
            result_trans=[
                dict(key="WIDTH", result_key="width", desc="屏幕宽度"),
            ]
        ),
        CommandStep(
            method=Command.ECHO,
            params={
                "message": "WindowWidth is {{WIDTH}}", 
            }
        ),
        CommandStep(
            method=Command.CLICK_ELEMENT,
            params={
                "by": "id",
                "value": "com.saucelabs.mydemoapp.android:id/productIV",
            }
        ),
        CommandStep(
            method=Command.CLICK_ELEMENT,
            params={
                "by": "id",
                "value": "com.saucelabs.mydemoapp.android:id/plusIV",
            }
        ),
        CommandStep(
            method=Command.CLICK_ELEMENT,
            params={
                "by": "id",
                "value": "com.saucelabs.mydemoapp.android:id/cartBt",
            }
        ),
        CommandStep(
            method=Command.CLICK_ELEMENT,
            params={
                "by": "id",
                "value": "com.saucelabs.mydemoapp.android:id/cartIV",
            }
        ),
        CommandStep(
            method=Command.FIND_ELEMENT,
            params={
                "by": "text",
                "value": "Proceed To Checkout",
            },
            skip=True,
        ),
        CompareCheckStep(
            method=CompareEnum.EQUAL,
            value_a="$.name",
            value_b="com.saucelabs.mydemoapp.android:id/cartIV",
        ),
        CommandStep(
            method=Command.CLICK_ELEMENT,
            params={
                "by": "text",
                "value": "Proceed To Checkout",
            }
        ),
    ]
    provider = AndroidProvider()
    driver = provider.get_single_device_driver()
    local_vars: Dict[str, str] = {}
    for step in steps:
        if not isinstance(step, CommandStep):
            continue
        command = Command(step.method)
        params = step.params
        print(step.method, params)
        if step.skip:
            logger.debug("Skip step: %s", step.method)
            continue
        run_driver_command(driver, command, params)