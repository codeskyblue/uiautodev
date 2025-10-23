# uiautodev
[![codecov](https://codecov.io/gh/codeskyblue/appinspector/graph/badge.svg?token=aLTg4VOyQH)](https://codecov.io/gh/codeskyblue/appinspector)
[![PyPI version](https://badge.fury.io/py/uiautodev.svg)](https://badge.fury.io/py/uiautodev)

https://uiauto.dev

> ~~In China visit: https://uiauto.devsleep.com~~

UI Inspector for Android, iOS and Harmony help inspector element properties, and auto generate XPath, script.

# Install
```bash
pip install uiautodev
```

To enable Harmony support, run the following command to install its dependencies:

```sh
uiautodev install-harmony
```

# Usage
```bash
Usage: uiauto.dev [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose  verbose mode
  -h, --help     Show this message and exit.

Commands:
  server       start uiauto.dev local server [Default]
  android      COMMAND: tap, tapElement, installApp, currentApp,...
  ios          COMMAND: tap, tapElement, installApp, currentApp,...
  self-update  Update uiautodev to latest version
  version      Print version
  shutdown     Shutdown server
```

```bash
# run local server and open browser
uiauto.dev
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
