import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

import httpx
import websockets
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from starlette.background import BackgroundTask

logger = logging.getLogger(__name__)
router = APIRouter()
cache_dir = Path("./cache")
base_url = 'https://uiauto.dev'

@router.get("/")
@router.get("/android/{path:path}")
@router.get("/ios/{path:path}")
@router.get("/demo/{path:path}")
@router.get("/harmony/{path:path}")
async def proxy_html(request: Request):
    cache = HTTPCache(cache_dir, base_url, key='homepage')
    response = await cache.proxy_request(request, update_cache=True)
    return response
    # update

@router.get("/assets/{path:path}")
@router.get('/favicon.ico')
async def proxy_assets(request: Request, path: str = ""):
    target_url = f"{base_url}{request.url.path}"
    cache = HTTPCache(cache_dir, target_url)
    return await cache.proxy_request(request)


class HTTPCache:
    def __init__(self, cache_dir: Path, target_url: str, key: Optional[str] = None):
        self.cache_dir = cache_dir
        self.target_url = target_url
        self.key = key or hashlib.md5(target_url.encode()).hexdigest()
        self.file_body = self.cache_dir / 'http' / (self.key + ".body")
        self.file_headers = self.file_body.with_suffix(".headers")

    async def proxy_request(self, request: Request, update_cache: bool = False):
        response = await self.get_cached_response(request)
        if not response:
            response = await self.proxy_and_save_response(request)
            return response
        if update_cache:
            # async update cache in background
            asyncio.create_task(self.update_cache(request))
        return response

    async def get_cached_response(self, request: Request):
        if request.method == 'GET' and self.file_body.exists():
            logger.info(f"Cache hit: {self.file_body}")
            headers = {}
            if self.file_headers.exists():
                with self.file_headers.open('rb') as f:
                    headers = json.load(f)
            body_fd = self.file_body.open("rb")
            return StreamingResponse(
                content=body_fd,
                status_code=200,
                headers=headers,
                background=BackgroundTask(body_fd.close)
            )
        return None

    async def update_cache(self, request: Request):
        try:
            await self.proxy_and_save_response(request)
        except Exception as e:
            logger.error("Update cache failed")

    async def proxy_and_save_response(self, request: Request) -> Response:
        logger.debug(f"Proxying request... {request.url.path}")
        response = await proxy_http(request, self.target_url)
        # save response to cache
        if request.method == "GET" and response.status_code == 200 and self.cache_dir.exists():
            self.file_body.parent.mkdir(parents=True, exist_ok=True)
            with self.file_body.open("wb") as f:
                f.write(response.body)
            with self.file_headers.open("w", encoding="utf-8") as f:
                headers = response.headers
                headers['cache-status'] = 'HIT'
                json.dump(dict(headers), f, indent=2, ensure_ascii=False)
        return response


# WebSocket 转发
@router.websocket("/proxy/ws/{target_url:path}")
async def proxy_ws(websocket: WebSocket, target_url: str):
    await websocket.accept()
    logger.info(f"WebSocket target_url: {target_url}")

    try:
        async with websockets.connect(target_url) as target_ws:
            async def from_client():
                while True:
                    msg = await websocket.receive_text()
                    await target_ws.send(msg)

            async def from_server():
                while True:
                    msg = await target_ws.recv()
                    if isinstance(msg, bytes):
                        await websocket.send_bytes(msg)
                    elif isinstance(msg, str):
                        await websocket.send_text(msg)
                    else:
                        raise RuntimeError("Unknown message type", msg)

            await asyncio.gather(from_client(), from_server())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS Error: {e}")
        await websocket.close()

# ref: https://stackoverflow.com/questions/74555102/how-to-forward-fastapi-requests-to-another-server
def make_reverse_proxy(base_url: str, strip_prefix: str = ""):
    async def _reverse_proxy(request: Request):
        client = httpx.AsyncClient(base_url=base_url)
        client.timeout = httpx.Timeout(30.0, read=300.0)
        path = request.url.path
        if strip_prefix and path.startswith(strip_prefix):
            path = path[len(strip_prefix):]
        target_url = httpx.URL(
            path=path, query=request.url.query.encode("utf-8")
        )
        exclude_headers = [b"host", b"connection", b"accept-encoding"]
        headers = [(k, v) for k, v in request.headers.raw if k not in exclude_headers]
        headers.append((b'accept-encoding', b''))
        
        req = client.build_request(
            request.method, target_url, headers=headers, content=request.stream()
        )
        r = await client.send(req, stream=True)#, follow_redirects=True)
        
        response_headers = {
            k: v for k, v in r.headers.items()
            if k.lower() not in {"transfer-encoding", "connection", "content-length"}
        }
        async def gen_content():
            async for chunk in r.aiter_bytes(chunk_size=40960):
                yield chunk
        
        async def aclose():
            await client.aclose()
        
        return StreamingResponse(
            content=gen_content(),
            status_code=r.status_code,
            headers=response_headers,
            background=BackgroundTask(aclose),
        )

    return _reverse_proxy
