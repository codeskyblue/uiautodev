#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 10:53:03 by codeskyblue
"""

from __future__ import annotations

import logging
import platform
import sys
import threading
import time
from pprint import pprint

import click
import httpx
import pydantic
import uvicorn

from uiauto_dev import __version__, command_proxy
from uiauto_dev.command_types import Command
from uiauto_dev.provider import AndroidProvider, BaseProvider, IOSProvider
from uiauto_dev.utils.common import convert_params_to_model, print_json

logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, default=False, help="verbose mode")
def cli(verbose: bool):
    if verbose:
        root_logger = logging.getLogger(__name__.split(".")[0])
        root_logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        root_logger.addHandler(console_handler)
        logger.debug("Verbose mode enabled")


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
        print_json(params_obj)
        result = command_proxy.send_command(driver, command, params_obj)
        print("Result ↓")
        print_json(result)
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


@cli.command(help="run case (beta)")
def case():
    from uiauto_dev.case import run
    run()


@cli.command(help="COMMAND: " + ", ".join(c.value for c in Command))
@click.argument("command", type=Command, required=True)
@click.argument("params", required=False, nargs=-1)
def appium(command: Command, params: list[str] = None):
    from uiauto_dev.driver.appium import AppiumProvider
    from uiauto_dev.exceptions import AppiumDriverException
    
    provider = AppiumProvider()
    try:
        run_driver_command(provider, command, params)
    except AppiumDriverException as e:
        print(f"Error: {e}")


@cli.command('version')
def print_version():
    print(__version__)


@cli.command(help="start uiauto.dev local server [default]")
@click.option("--port", default=20242, help="port number", show_default=True)
@click.option("--host", default="127.0.0.1", help="host", show_default=True)
@click.option("--reload", is_flag=True, default=False, help="auto reload, dev only")
@click.option("-f", "--force", is_flag=True, default=False, help="shutdown alrealy runningserver")
@click.option("--no-browser", is_flag=True, default=False, help="do not open browser")
def server(port: int, host: str, reload: bool, force: bool, no_browser: bool):
    logger.info("version: %s", __version__)
    if force:
        try:
            httpx.get(f"http://{host}:{port}/shutdown", timeout=3)
        except httpx.HTTPError:
            pass

    # if args.mock:
    #     os.environ["uiauto_dev_MOCK"] = "1"
    use_color = True
    if platform.system() == 'Windows':
        use_color = False
    
    if not no_browser:
        th = threading.Thread(target=open_browser_when_server_start, args=(f"http://{host}:{port}",))
        th.daemon = True
        th.start()
    uvicorn.run("uiauto_dev.app:app", host=host, port=port, reload=reload, use_colors=use_color)


def open_browser_when_server_start(server_url: str):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{server_url}/api/info", timeout=1)
            break
        except Exception as e:
            time.sleep(0.5)
    import webbrowser
    web_url = "https://uiauto.dev"
    logger.info("open browser: %s", web_url)
    webbrowser.open(web_url)

def main():
    # set logger level to INFO
    # logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)
    if len(sys.argv) == 1:
        cli.main(args=["server"], prog_name="uiauto.dev")
    else:
        cli()


if __name__ == "__main__":
    main()
