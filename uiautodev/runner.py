#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Download and run the prebuilt uiautodev server binary.

Ported from the `uiautodev` npm CLI (`run`/`download`/`path` commands).
"""

from __future__ import annotations

import logging
import os
import platform as platform_module
import re
import stat
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn

logger = logging.getLogger("uiautodev.runner")

API_BASE = "https://get.uiauto.dev"
REQUEST_HEADERS = {"user-agent": "uiautodev-cli"}
REQUEST_TIMEOUT = 30.0

OS_MAP = {"darwin": "macOS", "linux": "Linux", "windows": "Windows"}
SERVER_NAME_RE = re.compile(r"uiautodev-server", re.IGNORECASE)


def get_cache_dir(version: str) -> Path:
    base = os.environ.get("UIAUTODEV_CACHE_DIR")
    if not base:
        base = str(Path.home() / ".cache" / "uiautodev")
    return Path(base) / version


def _client() -> httpx.Client:
    return httpx.Client(
        headers=REQUEST_HEADERS,
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT,
    )


def get_version_info(version: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (version, files). Uses /api/versions/latest when version is None."""
    if version:
        url = f"{API_BASE}/api/versions/{version}"
    else:
        url = f"{API_BASE}/api/versions/latest"
    with _client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()

    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError(f"No files found for version {version or 'latest'}")
    return data.get("version") or version or "", files


def normalize_platform(system: Optional[str] = None, machine: Optional[str] = None) -> Tuple[str, str]:
    system = (system or platform_module.system()).lower()
    machine = (machine or platform_module.machine()).lower()

    if system == "darwin":
        os_name = "darwin"
    elif system == "linux":
        os_name = "linux"
    elif system in ("windows", "win32", "cygwin"):
        os_name = "windows"
    else:
        os_name = system

    if machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine in ("x86_64", "amd64", "x64"):
        arch = "x86_64"
    else:
        arch = machine
    return os_name, arch


def build_patterns(os_name: str, arch: str) -> List[re.Pattern]:
    arch64 = r"(amd64|x86_64)"
    if os_name == "darwin":
        if arch == "arm64":
            return [
                re.compile(r"uiautodev-server-darwin-arm64", re.IGNORECASE),
                re.compile(rf"uiautodev-server-darwin-{arch64}", re.IGNORECASE),
            ]
        return [
            re.compile(rf"uiautodev-server-darwin-{arch64}", re.IGNORECASE),
            # Older releases used a bare "-mac-" suffix without arch.
            re.compile(r"uiautodev-server-mac-", re.IGNORECASE),
        ]
    if os_name == "linux":
        if arch == "arm64":
            return [re.compile(r"uiautodev-server-linux-arm64", re.IGNORECASE)]
        return [re.compile(rf"uiautodev-server-linux-{arch64}", re.IGNORECASE)]
    if os_name == "windows" and arch == "x86_64":
        return [re.compile(r"uiautodev-server-windows-(amd64|x86_64).*\.exe", re.IGNORECASE)]
    return []


def resolve_binary(
    files: List[Dict[str, Any]],
    os_name: Optional[str] = None,
    arch: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if os_name is None or arch is None:
        os_name, arch = normalize_platform()

    candidates = [
        f
        for f in files
        if f
        and f.get("size", 0) > 0
        and f.get("download_url")
        and SERVER_NAME_RE.search(f.get("name", ""))
    ]
    for pattern in build_patterns(os_name, arch):
        for f in candidates:
            if pattern.search(f["name"]):
                return f
    return None


def describe_platform(os_name: str, arch: str) -> str:
    return f"{OS_MAP.get(os_name, os_name)} ({arch})"


def format_bytes(n: float) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(n)
    i = 0
    while value >= 1024 and i < len(units) - 1:
        value /= 1024
        i += 1
    digits = 0 if value >= 100 or i == 0 else 1
    return f"{value:.{digits}f} {units[i]}"


def _content_length(resp: httpx.Response) -> int:
    raw = resp.headers.get("content-length")
    try:
        return int(raw) if raw else 0
    except (TypeError, ValueError):
        return 0


def download_to(url: str, dest: Path, expected_size: Optional[int] = None) -> None:
    dest = Path(dest)
    tmp_path = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
    try:
        with _client() as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                total = expected_size or _content_length(resp) or None
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(bar_width=20),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                    console=Console(stderr=True),
                ) as progress:
                    task = progress.add_task(dest.name, total=total)
                    with open(tmp_path, "wb") as f:
                        for chunk in resp.iter_bytes():
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))

        size = tmp_path.stat().st_size
        if expected_size is not None and size != expected_size:
            raise RuntimeError(
                f"Size mismatch for {url}: expected {expected_size} bytes, got {size} bytes"
            )
        if dest.exists():
            dest.unlink()
        tmp_path.replace(dest)
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def post_download_stat(version: str, file_name: str) -> None:
    url = f"{API_BASE}/api/versions/{version}/files/{file_name}/downloads"
    try:
        with httpx.Client(
            headers=REQUEST_HEADERS, follow_redirects=True, timeout=2.0
        ) as client:
            resp = client.post(url)
            logger.debug("POST %s -> %s", url, resp.status_code)
    except Exception as e:  # best-effort only
        logger.debug("POST %s error: %s", url, e)


def ensure_binary(binary: Dict[str, Any], version: str, force: bool = False) -> Path:
    dir_path = get_cache_dir(version)
    dir_path.mkdir(parents=True, exist_ok=True)
    bin_path = dir_path / binary["name"]

    if force or not bin_path.exists():
        logger.info("Downloading %s (%s)...", binary["name"], format_bytes(binary.get("size") or 0))
        threading.Thread(
            target=post_download_stat, args=(version, binary["name"]), daemon=True
        ).start()
        download_to(binary["download_url"], bin_path, binary.get("size") or None)

    if os.name != "nt":
        bin_path.chmod(
            bin_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
    return bin_path


def resolve_target(version: Optional[str] = None) -> Tuple[str, Dict[str, Any], Path]:
    resolved_version, files = get_version_info(version)
    os_name, arch = normalize_platform()
    binary = resolve_binary(files, os_name, arch)
    if not binary:
        raise RuntimeError(
            f"No server binary available for {describe_platform(os_name, arch)} "
            f"in version {resolved_version}"
        )
    bin_path = get_cache_dir(resolved_version) / binary["name"]
    logger.debug("resolved version=%s binary=%s", resolved_version, binary["name"])
    return resolved_version, binary, bin_path


def run_binary(bin_path: Path, args: List[str]) -> int:
    bin_path = str(bin_path)
    argv = [bin_path, *[str(a) for a in args]]
    logger.debug("exec: %s", " ".join(argv))

    if os.name == "nt":
        return subprocess.call(argv)
    os.execv(bin_path, argv)
    return 0  # pragma: no cover - unreachable after execv
