#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Tue Mar 19 2024 22:23:37 by codeskyblue
"""

import sys
import httpx
from fastapi import FastAPI, Request, Response

app = FastAPI()


# Retrieve the target URL from the command line arguments
try:
    TARGET_URL = sys.argv[1]
except IndexError:
    print("Usage: python proxy_server.py <target_url>")
    sys.exit(1)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def proxy(request: Request, path: str):
    # Construct the full URL to forward the request to
    if path.endswith('/execute/sync'):
        # 旧版appium处理不好这个请求，直接返回404, unknown command
        # 目前browserstack也不支持这个请求
        return Response(content=b'{"value": {"error": "unknown command", "message": "unknown command", "stacktrace": "UnknownCommandError"}}', status_code=404)
    full_url = f"{TARGET_URL}/{path}"
    body = await request.body()
    print("Forwarding to", request.method, full_url)
    print("==> BODY <==")
    print(body)
    # Include original headers in the request
    headers = {k: v for k, v in request.headers.items() if k != 'host'}

    # Forward the request to the target server
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.request(
            method=request.method,
            url=full_url,
            headers=headers,
            data=body,
            follow_redirects=True,        
        )

    # Return the response received from the target server
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
