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

## 环境配置

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

## 代理转发

由于服务端是写在https外部网站上的，访问非localhost的http服务时会由于安全问题，禁止访问。
比如A机器访问B机器的服务，就不行。
所以需要本地转发，才能连接到其他的uiautodev客户端上。

测试WebSocket转发

```sh
wscat -c "ws://localhost:20242/proxy/ws/wss://echo.websocket.events"
```

> npm i -g wscat

测试HTTP转发

```sh
curl http://localhost:20242/proxy/http/https://httpbin.org/get
```
