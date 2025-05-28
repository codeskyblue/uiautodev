# uiautodev
[![codecov](https://codecov.io/gh/codeskyblue/appinspector/graph/badge.svg?token=aLTg4VOyQH)](https://codecov.io/gh/codeskyblue/appinspector)
[![PyPI version](https://badge.fury.io/py/uiautodev.svg)](https://badge.fury.io/py/uiautodev)

https://uiauto.dev

> backup site: https://uiauto.devsleep.com

UI Inspector for Android and iOS, help inspector element properties, and auto generate XPath, script.

# Install
```bash
pip install uiautodev
```

# Usage
```bash
Usage: uiauto.dev [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose  verbose mode
  -h, --help     Show this message and exit.

Commands:
  android      COMMAND: tap, tapElement, installApp, currentApp,...
  appium       COMMAND: tap, tapElement, installApp, currentApp,...
  ios          COMMAND: tap, tapElement, installApp, currentApp,...
  self-update  Update uiautodev to latest version
  server       start uiauto.dev local server [Default]
  version      Print version
```

```bash
# run local server and open browser
uiauto.dev
```

# DEVELOP
```bash
# install poetry (python package manager)
pip install poetry # pipx install poetry

# install deps
poetry install

# format import
make format

# run server
make dev

# If you encounter the error NameError: name 'int2byte' is not defined,
# try installing a stable version of the construct package to resolve it:
# and restart: make dev
pip install construct==2.9.45

```

运行测试

```sh
make test
```

# Links
- https://app.tangoapp.dev/ 基于webadb的手机远程控制项目
- https://docs.tangoapp.dev/scrcpy/video/web-codecs/ H264解码器

# LICENSE
[MIT](LICENSE)