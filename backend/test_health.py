from fastapi.testclient import TestClient
from app.main import app


def test_health_shape():
    client = TestClient(app)
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    assert 'vision_ready' in data
    assert 'rag_ready' in data
