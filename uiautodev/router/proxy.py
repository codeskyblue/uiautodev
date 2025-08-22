import asyncio
from urllib.parse import unquote

import httpx
import websockets
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
import logging


logger = logging.getLogger(__name__)
router = APIRouter()


# HTTP 转发
@router.api_route("/http/{target_url:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_http(request: Request, target_url: str):
    logger.info(f"HTTP target_url: {target_url}")

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        body = await request.body()
        resp = await client.request(
            request.method,
            target_url,
            content=body,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host" and k.lower() != "x-target-url"}
        )
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

# WebSocket 转发
@router.websocket("/ws/{target_url:path}")
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
        print(f"WS Error: {e}")
        await websocket.close()