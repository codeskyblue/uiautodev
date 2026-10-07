# uiautodev
[![codecov](https://codecov.io/gh/codeskyblue/appinspector/graph/badge.svg?token=aLTg4VOyQH)](https://codecov.io/gh/codeskyblue/appinspector)
[![PyPI version](https://badge.fury.io/py/uiautodev.svg)](https://badge.fury.io/py/uiautodev)

https://web.uiauto.dev

> ~~In China visit: https://uiauto.devsleep.com~~

UI Inspector for Android, iOS and Harmony help inspector element properties, and auto generate XPath, script.

# Install
```bash
pip install uiautodev

# or with Harmony support
pip install "uiautodev[harmony]"
# ref
# https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines
```

# Usage
```bash
Usage: uiauto.dev [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose  verbose mode
  --debug        enable debug output
  --version TEXT server binary version (default: latest)
  -f, --force    force re-download even if cached
  -h, --help     Show this message and exit.

Commands:
  run          download (if needed) and run the server binary [Default]
  download     download the server binary only and print its path
  path         print the path to the server binary without downloading
  server       start uiauto.dev local server (deprecated)
  self-update  Update uiautodev to latest version
  version      Print version
  shutdown     Shutdown server (deprecated)
```

```bash
# download the latest server binary and run it (opens the browser)
uiauto.dev

# start the local Python server instead (deprecated, old default)
uiauto.dev server
```

# Run prebuilt server binary

Running `uiauto.dev` without a command downloads the prebuilt server binary for
the current platform and executes it as `run -open`. The binary is cached at
`~/.cache/uiautodev/<version>/` (override with `UIAUTODEV_CACHE_DIR`), and
everything after `run` is passed through to the binary as-is.

> Note: the old local-server default is now the explicit `uiauto.dev server` command.

```bash
uiauto.dev                          # download latest binary and run it (open browser)
uiauto.dev run                      # same as above, without opening the browser
uiauto.dev run -addr :8000          # pass args through to the binary
uiauto.dev --version 0.10.5 run     # use a specific version
uiauto.dev download                 # only download, print the binary path
uiauto.dev download --force         # force re-download
uiauto.dev path                     # only print the binary path, no download
uiauto.dev --debug download         # debug logging (request/redirect info)
```

# Environment

```sh
# Default driver is uiautomator2
# Set the environment variable below to switch to adb driver
export UIAUTODEV_USE_ADB_DRIVER=1
```

# Offline mode

Start with

```sh
uiautodev server --offline

# Specify server url (optional)
uiautodev server --offline --server-url https://web.uiauto.dev
```

Visit <http://localhost:20242> once, and then disconnecting from the internet will not affect usage.

> All frontend resources will be saved to cache/ dir.

# DEVELOP

see [DEVELOP.md](DEVELOP.md)

# Links
- https://app.tangoapp.dev/ 基于webadb的手机远程控制项目
- https://docs.tangoapp.dev/scrcpy/video/web-codecs/ H264解码器

# LICENSE
[MIT](LICENSE)
