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
from rich.logging import RichHandler

from uiautodev import __version__, command_proxy, runner
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


def enable_logger_to_console(level):
    _logger = logging.getLogger("uiautodev")
    _logger.setLevel(level)
    _logger.addHandler(RichHandler(enable_link_path=False))


RUN_OPTIONS = [
    click.option("--version", "binary_version", default=None, help="server binary version (default: latest)"),
    click.option("-f", "--force", is_flag=True, default=False, help="force re-download even if cached"),
]


def add_run_options(func):
    for option in reversed(RUN_OPTIONS):
        func = option(func)
    return func


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option("--verbose", "-v", is_flag=True, default=False, help="verbose mode")
@click.option("--debug", is_flag=True, default=False, help="enable debug output")
@add_run_options
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool, binary_version: str, force: bool):
    if verbose or debug:
        enable_logger_to_console(level=logging.DEBUG)
        logger.debug("Verbose mode enabled")
    else:
        enable_logger_to_console(level=logging.INFO)
    ctx.obj = {"version": binary_version, "force": force}


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


@cli.command(hidden=True, help="(deprecated) COMMAND: " + ", ".join(c.value for c in Command))
@click.argument("command", type=Command, required=True)
@click.argument("params", required=False, nargs=-1)
def android(command: Command, params: list[str] = None):
    click.echo("Warning: `uiauto.dev android` is deprecated.", err=True)
    provider = AndroidProvider()
    run_driver_command(provider, command, params)


@cli.command(hidden=True, help="(deprecated) COMMAND: " + ", ".join(c.value for c in Command))
@click.argument("command", type=Command, required=True)
@click.argument("params", required=False, nargs=-1)
def ios(command: Command, params: list[str] = None):
    click.echo("Warning: `uiauto.dev ios` is deprecated.", err=True)
    provider = IOSProvider()
    run_driver_command(provider, command, params)


@cli.command(help="run case (beta)")
def case():
    from uiautodev.case import run
    run()


@cli.command(hidden=True, help="COMMAND: " + ", ".join(c.value for c in Command))
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
    pip_install("hypium")

@retry(tries=2, delay=3, backoff=2)
def pip_install(package: str):
    """Install a package using pip."""
    subprocess.run([sys.executable, '-m', "pip", "install", package], check=True)
    click.echo(f"Successfully installed {package}")


def _resolve_and_download(version: str, force: bool):
    resolved_version, binary, _ = runner.resolve_target(version)
    bin_path = runner.ensure_binary(binary, resolved_version, force)
    return resolved_version, binary, bin_path


@cli.command(
    "run",
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
        help_option_names=[],
    ),
    add_help_option=False,
    help="download (if needed) and run the server binary (default); extra args are passed through",
)
@click.argument("binary_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def run(ctx: click.Context, binary_args: tuple):
    version = ctx.obj.get("version")
    force = ctx.obj.get("force")
    _, _, bin_path = _resolve_and_download(version, force)
    runner.run_binary(bin_path, list(binary_args))


@cli.command("download", help="download the server binary only and print its path")
@add_run_options
@click.pass_context
def download(ctx: click.Context, binary_version: str, force: bool):
    version = binary_version or ctx.obj.get("version")
    force = force or ctx.obj.get("force")
    _, _, bin_path = _resolve_and_download(version, force)
    click.echo(str(bin_path))


@cli.command("path", help="print the path to the server binary without downloading")
@click.pass_context
def path(ctx: click.Context):
    version = ctx.obj.get("version")
    _, _, bin_path = runner.resolve_target(version)
    click.echo(str(bin_path))


@cli.command(help="start uiauto.dev local server (deprecated)")
@click.option("--port", default=20242, help="port number", show_default=True)
@click.option("--host", default="127.0.0.1", help="host", show_default=True)
@click.option("--reload", is_flag=True, default=False, help="auto reload, dev only")
@click.option("-f", "--force", is_flag=True, default=False, help="shutdown already running server")
@click.option("-s", "--no-browser", is_flag=True, default=False, help="silent mode, do not open browser")
@click.option("--offline", is_flag=True, default=False, help="offline mode, do not use internet")
@click.option("--server-url", default="https://web.uiauto.dev", help="uiauto.dev server url", show_default=True)
def server(port: int, host: str, reload: bool, force: bool, no_browser: bool, offline: bool, server_url: str):
    click.echo(
        "Warning: `uiauto.dev server` is deprecated, use `uiauto.dev` instead.",
        err=True,
    )
    click.echo(f"uiautodev version: {__version__}")
    if force:
        try:
            httpx.get(f"http://{host}:{port}/shutdown", timeout=3)
        except httpx.HTTPError:
            pass

    use_color = True
    if platform.system() == 'Windows':
        use_color = False

    server_url = server_url.rstrip('/')
    from uiautodev.router import proxy
    proxy.base_url = server_url

    if offline:
        proxy.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("offline mode enabled, cache dir: %s, server url: %s", proxy.cache_dir, proxy.base_url)

    if not no_browser:
        th = threading.Thread(target=open_browser_when_server_start, args=(f"http://{host}:{port}", offline))
        th.daemon = True
        th.start()
    uvicorn.run("uiautodev.app:app", host=host, port=port, reload=reload, use_colors=use_color)

@cli.command(help="shutdown uiauto.dev local server (deprecated)")
@click.option("--port", default=20242, help="port number", show_default=True)
def shutdown(port: int):
    click.echo("Warning: `uiauto.dev shutdown` is deprecated.", err=True)
    try:
        httpx.get(f"http://127.0.0.1:{port}/shutdown", timeout=3)
    except httpx.HTTPError:
        pass


def open_browser_when_server_start(local_server_url: str, offline: bool = False):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{local_server_url}/api/info", timeout=1)
            break
        except Exception as e:
            time.sleep(0.5)
    import webbrowser
    web_url = get_webpage_url(local_server_url if offline else None)
    logger.info("open browser: %s", web_url)
    webbrowser.open(web_url)


def main():
    args = sys.argv[1:]
    has_command = any(name in cli.commands for name in args)
    wants_help = any(name in ("-h", "--help") for name in args)

    if has_command or wants_help:
        cli()
    else:
        click.echo(
            "Tip: `uiauto.dev` now downloads and runs the server binary. "
            "The old local-server usage is `uiauto.dev server`.",
            err=True,
        )
        cli.main(args=args + ["run", "-open"], prog_name="uiauto.dev")


if __name__ == "__main__":
    main()
