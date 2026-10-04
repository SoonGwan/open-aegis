import asyncio
from aegis.http_limits import BodyLimitMiddleware
from tests.test_validation import client


def test_large_json_rejected_before_validation_and_no_mutation(client):
    before = client.get('/api/assets').json()
    response = client.post('/api/assets', content=b' ' * (2 * 1024 * 1024 + 1), headers={'Content-Type':'application/json'})
    assert response.status_code == 413
    assert client.get('/api/assets').json() == before
    assert client.get('/api/health').status_code == 200


def test_streamed_body_without_length_is_bounded():
    async def scenario():
        called = []
        async def app(scope, receive, send):
            called.append(True)
        frames = iter([{'type':'http.request','body':b'1234','more_body':True},
                       {'type':'http.request','body':b'5678','more_body':False}])
        async def receive():
            return next(frames)
        output = []
        async def send(message):
            output.append(message)
        await BodyLimitMiddleware(app,max_bytes=6)({'type':'http','headers':[]},receive,send)
        assert output[0]['status'] == 413
        assert called == []
    asyncio.run(scenario())


def test_tags_bounded_and_deduplicated(client):
    response = client.post('/api/assets',json={'name':'fixture','url':'https://example.invalid/','authorized':True,'tags':[' lab ','lab','']})
    assert response.status_code == 200
    assert response.json()['tags'] == ['lab']
    assert client.post('/api/assets',json={'name':'fixture2','url':'https://other.invalid/','authorized':True,'tags':['x'*81]}).status_code == 422


def test_incomplete_body_times_out_without_entering_app():
    async def scenario():
        called, output = [], []
        async def app(scope, receive, send):
            called.append(True)
        async def receive():
            await asyncio.sleep(1)
            return {'type':'http.request','body':b'','more_body':True}
        async def send(message):
            output.append(message)
        await BodyLimitMiddleware(app,read_timeout=.01)({'type':'http','headers':[]},receive,send)
        assert output[0]['status'] == 408
        assert called == []
    asyncio.run(scenario())


def test_concurrent_body_reads_reject_without_queue_and_recover():
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        calls, first, rejected, recovered = [], [], [], []
        async def app(scope, receive, send):
            calls.append((await receive())['body'])
        async def slow_receive():
            entered.set()
            await release.wait()
            return {'type': 'http.request', 'body': b'owned', 'more_body': False}
        async def ready_receive():
            return {'type': 'http.request', 'body': b'next', 'more_body': False}
        async def forbidden_receive():
            raise AssertionError('rejected request must not read its body')
        async def send_first(message): first.append(message)
        async def send_rejected(message): rejected.append(message)
        async def send_recovered(message): recovered.append(message)
        middleware = BodyLimitMiddleware(app, max_readers=1)
        scope = {'type': 'http', 'headers': []}
        running = asyncio.create_task(middleware(scope, slow_receive, send_first))
        await entered.wait()
        await middleware(scope, forbidden_receive, send_rejected)
        assert rejected[0]['status'] == 503
        assert (b'retry-after', b'1') in rejected[0]['headers']
        assert calls == []
        release.set()
        await running
        await middleware(scope, ready_receive, send_recovered)
        assert calls == [b'owned', b'next']
    asyncio.run(scenario())


def test_body_reader_permit_recovers_after_disconnect_timeout_and_cancellation():
    async def scenario():
        entered = asyncio.Event()
        calls, output = [], []
        async def app(scope, receive, send): calls.append((await receive())['body'])
        async def send(message): output.append(message)
        async def disconnected(): return {'type': 'http.disconnect'}
        async def slow():
            entered.set()
            await asyncio.Event().wait()
        async def ready(): return {'type': 'http.request', 'body': b'ok', 'more_body': False}
        middleware = BodyLimitMiddleware(app, max_readers=1, read_timeout=.01)
        scope = {'type': 'http', 'headers': []}
        await middleware(scope, disconnected, send)
        await middleware(scope, ready, send)
        await middleware(scope, slow, send)
        assert output[0]['status'] == 408
        await middleware(scope, ready, send)
        entered.clear()
        middleware.read_timeout = 30
        task = asyncio.create_task(middleware(scope, slow, send))
        await entered.wait()
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        else: raise AssertionError('cancellation must propagate')
        await middleware(scope, ready, send)
        assert calls == [b'ok', b'ok', b'ok']
    asyncio.run(scenario())


def test_streamed_oversize_releases_body_reader_for_next_request():
    async def scenario():
        calls, output = [], []
        async def app(scope, receive, send): calls.append((await receive())['body'])
        async def send(message): output.append(message)
        frames = iter([
            {'type': 'http.request', 'body': b'1234', 'more_body': True},
            {'type': 'http.request', 'body': b'5678', 'more_body': False},
        ])
        async def oversized(): return next(frames)
        async def ready(): return {'type': 'http.request', 'body': b'ok', 'more_body': False}
        middleware = BodyLimitMiddleware(app, max_bytes=6, max_readers=1)
        scope = {'type': 'http', 'headers': []}
        await middleware(scope, oversized, send)
        assert output[0]['status'] == 413
        assert calls == []
        await middleware(scope, ready, send)
        assert calls == [b'ok']
    asyncio.run(scenario())
