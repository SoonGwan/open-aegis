"""Bound request bodies before JSON parsing, including chunked/lengthless requests."""
import asyncio
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_BODY_READERS = 16


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes=MAX_BODY_BYTES, read_timeout=30, max_readers=MAX_BODY_READERS):
        self.app = app
        self.max_bytes = max_bytes
        self.read_timeout = read_timeout
        if max_readers < 1:
            raise ValueError("max_readers must be positive")
        self.readers = asyncio.Semaphore(max_readers)

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
        if self.readers.locked():
            return await JSONResponse(
                {'detail': '요청 본문 수신이 혼잡합니다. 잠시 후 다시 시도하세요.'},
                status_code=503, headers={'Retry-After': '1'},
            )(scope, receive, send)
        await self.readers.acquire()
        try:
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
        finally:
            self.readers.release()
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
