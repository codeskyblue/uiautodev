# TODO
import asyncio
import socket
from typing import Optional, Protocol
from starlette.websockets import WebSocket, WebSocketDisconnect


class AsyncDuplex(Protocol):
    async def read(self, n: int = -1) -> bytes: ...
    async def write(self, data: bytes): ...
    async def close(self): ...
    

async def pipe_duplex(a: AsyncDuplex, b: AsyncDuplex, label_a="A", label_b="B"):
    """双向管道：a <-> b"""
    task_ab = asyncio.create_task(_pipe_oneway(a, b, f"{label_a}->{label_b}"))
    task_ba = asyncio.create_task(_pipe_oneway(b, a, f"{label_b}->{label_a}"))
    done, pending = await asyncio.wait(
        [task_ab, task_ba],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for t in pending:
        t.cancel()


async def _pipe_oneway(src: AsyncDuplex, dst: AsyncDuplex, name: str):
    try:
        while True:
            data = await src.read(4096)
            if not data:
                break
            await dst.write(data)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[{name}] error:", e)
    finally:
        await dst.close()
        
        
        
class SocketDuplex:
    """封装 socket.socket 为 AsyncDuplex 接口"""
    def __init__(self, sock: socket.socket, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.sock = sock
        self.loop = loop or asyncio.get_event_loop()
        self._closed = False
        self.sock.setblocking(False)

    async def read(self, n: int = 4096) -> bytes:
        try:
            return await self.loop.sock_recv(self.sock, n)
        except (ConnectionResetError, OSError):
            return b''

    async def write(self, data: bytes):
        if not data or self._closed:
            return
        try:
            await self.loop.sock_sendall(self.sock, data)
        except (ConnectionResetError, OSError):
            self._closed = True

    async def close(self):
        if not self._closed:
            self._closed = True
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()

    def fileno(self):
        return self.sock.fileno()

    def is_closed(self) -> bool:
        return self._closed


class WebSocketDuplex:
    """将 starlette.websockets.WebSocket 封装为 AsyncDuplex"""
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self._closed = False

    async def read(self, n: int = -1) -> bytes:
        """读取二进制消息，如果是文本则自动转 bytes"""
        if self._closed:
            return b''
        try:
            msg = await self.ws.receive()
        except WebSocketDisconnect:
            self._closed = True
            return b''
        except Exception:
            self._closed = True
            return b''

        if msg["type"] == "websocket.disconnect":
            self._closed = True
            return b''
        elif msg["type"] == "websocket.receive":
            data = msg.get("bytes")
            if data is not None:
                return data
            text = msg.get("text")
            return text.encode("utf-8") if text else b''
        return b''

    async def write(self, data: bytes):
        if self._closed:
            return
        try:
            await self.ws.send_bytes(data)
        except Exception:
            self._closed = True

    async def close(self):
        if not self._closed:
            self._closed = True
            try:
                await self.ws.close()
            except Exception:
                pass