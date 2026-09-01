"""CI 스모크 테스트: FastAPI 앱이 정상적으로 뜨고 /health가 200을 반환하는지 확인."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
