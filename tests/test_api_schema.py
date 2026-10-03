from fastapi.testclient import TestClient
from tests.test_validation import client, register
from tests.test_identity import add, login


def test_default_documentation_routes_are_disabled(client):
    with TestClient(client.app) as anonymous:
        for path in ('/docs', '/redoc', '/openapi.json', '/docs/oauth2-redirect'):
            assert anonymous.get(path).status_code == 404
        assert anonymous.get('/api/openapi.json').status_code == 401
        assert anonymous.get('/api/health').status_code == 200


def test_schema_requires_admin_and_contains_no_workspace_values(client):
    register(client, 'https://schema-fixture.invalid/', name='SCHEMA-PRIVATE-ASSET-SENTINEL')
    client.app.state.store.event(None, 'SCHEMA-PRIVATE-EVENT-SENTINEL')
    for role in ('operator', 'viewer'):
        add(client, role)
        with login(client.app, role) as other:
            assert other.get('/api/openapi.json').status_code == 403
    response = client.get('/api/openapi.json')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    schema = response.json()
    assert schema['info']['title'] == 'Open Aegis'
    assert '/api/assets' in schema['paths']
    assert '/api/tasks/{task_id}/approve' in schema['paths']
    assert '/api/openapi.json' not in schema['paths']
    assert 'SCHEMA-PRIVATE-' not in response.text
    assert 'schema-fixture.invalid' not in response.text
    assert client.get('/api/auth/status').json()['authenticated'] is True
    assert client.get('/docs').status_code == 404
