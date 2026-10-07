#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import pytest

from uiautodev import runner

FILES = [
    {"name": "0.10.5", "size": 0, "download_url": "https://dl.uiauto.dev/0.10.5/0.10.5"},
    {
        "name": "uiautodev-server-darwin-arm64-0.10.5",
        "size": 100,
        "download_url": "https://dl.uiauto.dev/0.10.5/uiautodev-server-darwin-arm64-0.10.5",
    },
    {
        "name": "uiautodev-server-darwin-x86_64-0.10.5",
        "size": 100,
        "download_url": "https://dl.uiauto.dev/0.10.5/uiautodev-server-darwin-x86_64-0.10.5",
    },
    {
        "name": "uiautodev-server-linux-x86_64-0.10.5",
        "size": 100,
        "download_url": "https://dl.uiauto.dev/0.10.5/uiautodev-server-linux-x86_64-0.10.5",
    },
    {
        "name": "uiautodev-server-linux-arm64-0.10.5",
        "size": 100,
        "download_url": "https://dl.uiauto.dev/0.10.5/uiautodev-server-linux-arm64-0.10.5",
    },
    {
        "name": "uiautodev-server-windows-amd64-0.10.5.exe",
        "size": 100,
        "download_url": "https://dl.uiauto.dev/0.10.5/uiautodev-server-windows-amd64-0.10.5.exe",
    },
]


def test_normalize_platform():
    assert runner.normalize_platform("Darwin", "arm64") == ("darwin", "arm64")
    assert runner.normalize_platform("Linux", "AMD64") == ("linux", "x86_64")
    assert runner.normalize_platform("Windows", "AMD64") == ("windows", "x86_64")
    assert runner.normalize_platform("Linux", "aarch64") == ("linux", "arm64")
    assert runner.normalize_platform("FreeBSD", "riscv64") == ("freebsd", "riscv64")


def test_resolve_binary_per_platform():
    assert runner.resolve_binary(FILES, "darwin", "arm64")["name"] == "uiautodev-server-darwin-arm64-0.10.5"
    assert runner.resolve_binary(FILES, "darwin", "x86_64")["name"] == "uiautodev-server-darwin-x86_64-0.10.5"
    assert runner.resolve_binary(FILES, "linux", "arm64")["name"] == "uiautodev-server-linux-arm64-0.10.5"
    assert runner.resolve_binary(FILES, "linux", "x86_64")["name"] == "uiautodev-server-linux-x86_64-0.10.5"
    assert runner.resolve_binary(FILES, "windows", "x86_64")["name"].endswith(".exe")


def test_resolve_binary_skips_zero_size_and_non_server():
    files = [
        {"name": "uiautodev-server-linux-x86_64-0.3.2", "size": 0, "download_url": "u"},
        {"name": "UiautodevDesktop-mac-0.3.2.dmg", "size": 10, "download_url": "u"},
        {"name": "uiautodev-server-linux-x86_64-0.3.2", "size": 10, "download_url": "u"},
    ]
    assert runner.resolve_binary(files, "linux", "x86_64")["size"] == 10


def test_resolve_binary_old_mac_fallback():
    files = [{"name": "uiautodev-server-mac-0.3.2", "size": 10, "download_url": "u"}]
    assert runner.resolve_binary(files, "darwin", "x86_64")["name"] == "uiautodev-server-mac-0.3.2"


def test_resolve_binary_unsupported_platform():
    assert runner.resolve_binary(FILES, "windows", "arm64") is None
    assert runner.resolve_binary(FILES, "freebsd", "x86_64") is None


def test_cache_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("UIAUTODEV_CACHE_DIR", str(tmp_path))
    assert runner.get_cache_dir("1.2.3") == tmp_path / "1.2.3"


def test_format_bytes():
    assert runner.format_bytes(0) == "0 B"
    assert runner.format_bytes(1024) == "1.0 KB"
    assert runner.format_bytes(1024 * 1024) == "1.0 MB"


def _make_client(data, captured):
    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return data

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            captured.append(url)
            return _Response()

    return _Client()


def test_get_version_info_latest(monkeypatch):
    captured = []
    data = {"version": "0.10.5", "files": [{"name": "x", "size": 1, "download_url": "u"}]}
    monkeypatch.setattr(runner, "_client", lambda: _make_client(data, captured))
    version, files = runner.get_version_info()
    assert version == "0.10.5"
    assert files == data["files"]
    assert captured[0] == "https://get.uiauto.dev/api/versions/latest"


def test_get_version_info_specific(monkeypatch):
    captured = []
    data = {"version": "0.9.0", "files": [{"name": "x", "size": 1, "download_url": "u"}]}
    monkeypatch.setattr(runner, "_client", lambda: _make_client(data, captured))
    version, _ = runner.get_version_info("0.9.0")
    assert version == "0.9.0"
    assert captured[0] == "https://get.uiauto.dev/api/versions/0.9.0"


def test_get_version_info_no_files(monkeypatch):
    monkeypatch.setattr(runner, "_client", lambda: _make_client({"version": "0.10.5", "files": []}, []))
    with pytest.raises(RuntimeError):
        runner.get_version_info()
