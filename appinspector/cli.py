#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 10:53:03 by codeskyblue
"""

from __future__ import annotations

import logging
import platform
from pprint import pprint
import sys
import click
import pydantic
import uvicorn
from appinspector import __version__, command_proxy
from appinspector.command_types import Command
from appinspector.driver.appium import AppiumProvider
from appinspector.exceptions import AppiumDriverException
from appinspector.provider import AndroidProvider, BaseProvider, IOSProvider
from appinspector.utils.common import convert_params_to_model, print_json_with_color

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


def run_driver_command(provider: BaseProvider, command: Command, params: list[str] = None):
    if command == Command.LIST:
        devices = provider.list_devices()
        print("==> Devices <==")
        pprint(devices)
        return
    driver = provider.get_single_device_driver()
    params_obj = None
    model = command_proxy.get_command_params_type(command)
    if model:
        if not params:
            print(f"params is required for {command}")
            pprint(model.model_json_schema())
            return
        params_obj = convert_params_to_model(params, model)

    try:
        print("Command:", command.value)
        print("Params ↓")
        print_json_with_color(params_obj)
        result = command_proxy.send_command(driver, command, params_obj)
        print("Result ↓")
        print_json_with_color(result)
    except pydantic.ValidationError as e:
        print(f"params error: {e}")
        print(f"\n--- params should be match schema ---")
        pprint(model.model_json_schema()["properties"])


@cli.command(help="COMMAND: " + ", ".join(c.value for c in Command))
@click.argument("command", type=Command, required=True)
@click.argument("params", required=False, nargs=-1)
def android(command: Command, params: list[str] = None):
    provider = AndroidProvider()
    run_driver_command(provider, command, params)


@cli.command(help="COMMAND: " + ", ".join(c.value for c in Command))
@click.argument("command", type=Command, required=True)
@click.argument("params", required=False, nargs=-1)
def ios(command: Command, params: list[str] = None):
    provider = IOSProvider()
    run_driver_command(provider, command, params)


@cli.command(help="COMMAND: " + ", ".join(c.value for c in Command))
@click.argument("command", type=Command, required=True)
@click.argument("params", required=False, nargs=-1)
def appium(command: Command, params: list[str] = None):
    provider = AppiumProvider()
    try:
        run_driver_command(provider, command, params)
    except AppiumDriverException as e:
        print(f"Error: {e}")


@cli.command('version')
def print_version():
    print(__version__)


@cli.command()
@click.option("--port", default=20242, help="port number")
@click.option("--host", default="127.0.0.1", help="host")
@click.option("--reload", default=False, help="auto reload, dev only")
def server(port: int, host: str, reload: bool):
    logger.info("version: %s", __version__)
    # if args.mock:
    #     os.environ["APPINSPECTOR_MOCK"] = "1"
    use_color = True
    if platform.system() == 'Windows':
        use_color = False
    uvicorn.run("appinspector.app:app", host=host, port=port, reload=reload, use_colors=use_color)


def main():
    # set logger level to INFO
    # logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)
    if len(sys.argv) == 1:
        cli.main(args=["server"], prog_name="appinspector")
    else:
        cli()


if __name__ == "__main__":
    main()