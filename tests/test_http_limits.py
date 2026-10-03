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
