#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 10:53:03 by codeskyblue
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import threading
import time
from pprint import pprint

import click
import httpx
import pydantic
import uvicorn
from retry import retry

from uiautodev import __version__, command_proxy
from uiautodev.command_types import Command
from uiautodev.common import get_webpage_url
from uiautodev.provider import AndroidProvider, BaseProvider, IOSProvider
from uiautodev.utils.common import convert_params_to_model, print_json

logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
HARMONY_PACKAGES = [
    "setuptools",
    "https://public.uiauto.devsleep.com/harmony/xdevice-5.0.7.200.tar.gz",
    "https://public.uiauto.devsleep.com/harmony/xdevice-devicetest-5.0.7.200.tar.gz",
    "https://public.uiauto.devsleep.com/harmony/xdevice-ohos-5.0.7.200.tar.gz",
    "https://public.uiauto.devsleep.com/harmony/hypium-5.0.7.200.tar.gz",
]

@click.group(context_settings=CONTEXT_SETTINGS)
@click.option("--verbose", "-v", is_flag=True, default=False, help="verbose mode")
def cli(verbose: bool):
    if verbose:
        os.environ['UIAUTODEV_DEBUG'] = '1'
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
    from uiautodev.case import run
    run()


@cli.command(help="COMMAND: " + ", ".join(c.value for c in Command))
@click.argument("command", type=Command, required=True)
@click.argument("params", required=False, nargs=-1)
def appium(command: Command, params: list[str] = None):
    from uiautodev.driver.appium import AppiumProvider
    from uiautodev.exceptions import AppiumDriverException

    provider = AppiumProvider()
    try:
        run_driver_command(provider, command, params)
    except AppiumDriverException as e:
        print(f"Error: {e}")


@cli.command('version')
def print_version():
    """ Print version """
    print(__version__)


@cli.command('self-update')
def self_update():
    """ Update uiautodev to latest version """
    subprocess.run([sys.executable, '-m', "pip", "install", "--upgrade", "uiautodev"])


@cli.command('install-harmony')
def install_harmony():
    for lib_url in HARMONY_PACKAGES:
        click.echo(f"Installing {lib_url} ...")
        pip_install(lib_url)

@retry(tries=2, delay=3, backoff=2)
def pip_install(package: str):
    """Install a package using pip."""
    subprocess.run([sys.executable, '-m', "pip", "install", package], check=True)
    click.echo(f"Successfully installed {package}")


@cli.command(help="start uiauto.dev local server [Default]")
@click.option("--port", default=20242, help="port number", show_default=True)
@click.option("--host", default="127.0.0.1", help="host", show_default=True)
@click.option("--reload", is_flag=True, default=False, help="auto reload, dev only")
@click.option("-f", "--force", is_flag=True, default=False, help="shutdown alrealy runningserver")
@click.option("-s", "--no-browser", is_flag=True, default=False, help="silent mode, do not open browser")
def server(port: int, host: str, reload: bool, force: bool, no_browser: bool):
    click.echo(f"uiautodev version: {__version__}")
    if force:
        try:
            httpx.get(f"http://{host}:{port}/shutdown", timeout=3)
        except httpx.HTTPError:
            pass

    use_color = True
    if platform.system() == 'Windows':
        use_color = False

    if not no_browser:
        th = threading.Thread(target=open_browser_when_server_start, args=(f"http://{host}:{port}",))
        th.daemon = True
        th.start()
    uvicorn.run("uiautodev.app:app", host=host, port=port, reload=reload, use_colors=use_color)

@cli.command(help="shutdown uiauto.dev local server")
@click.option("--port", default=20242, help="port number", show_default=True)
def shutdown(port: int):
    try:
        httpx.get(f"http://127.0.0.1:{port}/shutdown", timeout=3)
    except httpx.HTTPError:
        pass


def open_browser_when_server_start(server_url: str):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{server_url}/api/info", timeout=1)
            break
        except Exception as e:
            time.sleep(0.5)
    import webbrowser
    web_url = get_webpage_url()
    logger.info("open browser: %s", web_url)
    webbrowser.open(web_url)


def main():
    has_command = False
    for name in sys.argv[1:]:
        if not name.startswith("-"):
            has_command = True

    if not has_command:
        cli.main(args=sys.argv[1:] + ["server"], prog_name="uiauto.dev")
    else:
        cli()


if __name__ == "__main__":
    main()
