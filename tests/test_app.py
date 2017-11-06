from staging_service.app import app_factory
import pytest


@pytest.fixture
def cli(loop, test_client):
    app = app_factory()
    return loop.run_until_complete(test_client(app))


async def test_service(cli):
    resp = await cli.get('/test-service')
    assert resp.status == 200
    text = await resp.text()
    assert 'This is just a test. This is only a test.' in text
