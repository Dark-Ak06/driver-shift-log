from fastapi.testclient import TestClient
import pytest

from main import app
from app.storage import TripStorage
from app.service import ShiftService
from app.api import get_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_service(tmp_path):
    """Изолирует хранилище для каждого API теста."""
    test_storage = TripStorage(file_path=str(tmp_path / "api_trips.json"))
    test_service = ShiftService(storage=test_storage)
    app.dependency_overrides[get_service] = lambda: test_service
    yield test_service
    app.dependency_overrides.clear()


def test_api_add_and_get_trips(setup_test_service):
    """Проверка добавления поездки и последующего получения списка за день."""
    # Добавляем поездку
    payload = {
        "id": "t100",
        "start": "2026-10-01T08:10:00+05:00",
        "end": "2026-10-01T08:32:00+05:00",
        "amount": 2400.0,
        "payment": "card",
        "commission": 360.0
    }
    resp = client.post("/api/trips", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["trip"]["id"] == "t100"
    assert data["is_duplicate"] is False

    # Получаем поездки за этот день
    get_resp = client.get("/api/trips?date=2026-10-01")
    assert get_resp.status_code == 200
    trips = get_resp.json()
    assert len(trips) == 1
    assert trips[0]["id"] == "t100"


def test_api_duplicate_prevention(setup_test_service):
    """Повторный POST того же ID возвращает статус 200 и is_duplicate=True."""
    payload = {
        "id": "t101",
        "start": "2026-10-01T09:00:00+05:00",
        "end": "2026-10-01T09:30:00+05:00",
        "amount": 1500.0,
        "payment": "cash",
        "commission": 225.0
    }
    # 1. Первая отправка
    resp1 = client.post("/api/trips", json=payload)
    assert resp1.status_code == 201
    assert resp1.json()["is_duplicate"] is False

    # 2. Повторная отправка
    resp2 = client.post("/api/trips", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["is_duplicate"] is True
    assert resp2.json()["trip"]["id"] == "t101"

    # В списке поездок должна остаться только одна запись
    get_resp = client.get("/api/trips?date=2026-10-01")
    assert len(get_resp.json()) == 1


def test_api_validation_errors(setup_test_service):
    """Проверка отклонения некорректных данных со статусом 422."""
    # amount <= 0
    resp = client.post("/api/trips", json={
        "start": "2026-10-01T10:00:00+05:00",
        "end": "2026-10-01T10:20:00+05:00",
        "amount": 0,
        "payment": "cash",
        "commission": 0
    })
    assert resp.status_code == 422

    # end <= start
    resp2 = client.post("/api/trips", json={
        "start": "2026-10-01T10:20:00+05:00",
        "end": "2026-10-01T10:10:00+05:00",
        "amount": 500,
        "payment": "cash",
        "commission": 50
    })
    assert resp2.status_code == 422


def test_api_summary_endpoint(setup_test_service):
    """Проверка эндпоинта /api/summary."""
    # Добавляем 2 поездки из примера
    client.post("/api/trips", json={
        "id": "t1",
        "start": "2026-10-01T08:10:00+05:00",
        "end": "2026-10-01T08:32:00+05:00",
        "amount": 2400.0,
        "payment": "card",
        "commission": 360.0
    })
    client.post("/api/trips", json={
        "id": "t2",
        "start": "2026-10-01T09:05:00+05:00",
        "end": "2026-10-01T09:20:00+05:00",
        "amount": 1500.0,
        "payment": "cash",
        "commission": 225.0
    })

    resp = client.get("/api/summary?date=2026-10-01")
    assert resp.status_code == 200
    data = resp.json()

    assert data["trips_count"] == 2
    assert data["revenue"] == 3900.0
    assert data["commission"] == 585.0
    assert data["net_income"] == 3315.0
    assert data["card"]["net_income"] == 2040.0
    assert data["cash"]["net_income"] == 1275.0
