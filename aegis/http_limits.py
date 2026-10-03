"""Bound request bodies before JSON parsing, including chunked/lengthless requests."""
import asyncio
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 2 * 1024 * 1024


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes=MAX_BODY_BYTES, read_timeout=30):
        self.app = app
        self.max_bytes = max_bytes
        self.read_timeout = read_timeout

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        length = dict(scope.get('headers', [])).get(b'content-length')
        if length is not None:
            try:
                size = int(length)
            except ValueError:
                return await JSONResponse({'detail': 'Content-Length가 올바르지 않습니다.'}, status_code=400)(scope, receive, send)
            if size < 0:
                return await JSONResponse({'detail': 'Content-Length가 올바르지 않습니다.'}, status_code=400)(scope, receive, send)
            if size > self.max_bytes:
                return await self.reject(scope, receive, send)
        body = bytearray()
        deadline = asyncio.get_running_loop().time() + self.read_timeout
        while True:
            try:
                message = await asyncio.wait_for(receive(), timeout=max(0, deadline - asyncio.get_running_loop().time()))
            except asyncio.TimeoutError:
                return await JSONResponse({'detail': '요청 본문을 받는 시간이 초과되었습니다.'}, status_code=408)(scope, receive, send)
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            if len(body) + len(chunk) > self.max_bytes:
                return await self.reject(scope, receive, send)
            body.extend(chunk)
            if not message.get('more_body', False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)

    async def reject(self, scope, receive, send):
        await JSONResponse({'detail': '요청은 2 MiB 이하로 보내세요. 대량 가져오기는 나누어 진행하세요.'}, status_code=413)(scope, receive, send)
