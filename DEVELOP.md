# For Developers
写的不是很全，请见谅。另外国外朋友，还请自行翻译一下。

目录结构

- binaries: 二进制文件
- driver: 不同类型设备的驱动
- remote: 由于这块代码较多，单独从driver中拿出来了
- router: 将驱动包括成接口透出

- app.py: 相当于FastAPI入口文件
- cli.py: 命令行相关

目前启动后的端口是固定的20242 (也就是2024年2月开始开发的意思)

## Mac or Linux环境配置

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

## Windows环境配置

```bash
# install poetry (python package manager)
pip install poetry # pipx install poetry

# install deps
poetry install

# install make, choco ref: https://community.chocolatey.org/install
# Set-ExecutionPolicy Bypass -Scope Process -Force; 
# [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; 
# iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
choco install make

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