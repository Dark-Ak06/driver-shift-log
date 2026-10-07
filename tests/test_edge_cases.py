from datetime import datetime
from app.models import Trip, TripCreate, PaymentType
from app.service import ShiftService
from app.storage import TripStorage


def test_timezone_date_matching(tmp_path):
    """
    Поездка, совершенная ночью в часовом поясе +05:00 (например, 01:30 2 октября),
    должна относиться именно ко 2 октября, а не к 1 октября (как было бы в UTC).
    """
    storage = TripStorage(file_path=str(tmp_path / "tz_trips.json"))
    service = ShiftService(storage=storage)

    # 2026-10-02T01:30:00+05:00 -> в UTC это 2026-10-01T20:30:00Z
    storage.add_trip(TripCreate(
        id="tz_trip_1",
        start=datetime.fromisoformat("2026-10-02T01:30:00+05:00"),
        end=datetime.fromisoformat("2026-10-02T02:00:00+05:00"),
        amount=1000.0,
        payment=PaymentType.CARD,
        commission=150.0,
    ))

    # Запрос за 2026-10-02 должен найти поездку
    trips_oct2 = service.get_trips_for_day("2026-10-02")
    assert len(trips_oct2) == 1
    assert trips_oct2[0].id == "tz_trip_1"

    # Запрос за 2026-10-01 НЕ должен содержать эту поездку
    trips_oct1 = service.get_trips_for_day("2026-10-01")
    assert len(trips_oct1) == 0


def test_trip_model_properties():
    """Проверка вычисляемых свойств модели Trip (net_income, duration_minutes)."""
    trip = Trip(
        id="t_prop",
        start=datetime.fromisoformat("2026-10-01T10:00:00+05:00"),
        end=datetime.fromisoformat("2026-10-01T10:45:00+05:00"),
        amount=1500.0,
        payment=PaymentType.CASH,
        commission=225.0,
    )
    assert trip.duration_minutes == 45
    assert trip.net_income == 1275.0


def test_multiple_identical_requests_idempotency(tmp_path):
    """Многократная параллельная/последовательная отправка одного запроса не плодит дубликаты."""
    storage = TripStorage(file_path=str(tmp_path / "idemp.json"))
    trip_data = TripCreate(
        id="idem_1",
        start=datetime.fromisoformat("2026-10-01T15:00:00+05:00"),
        end=datetime.fromisoformat("2026-10-01T15:20:00+05:00"),
        amount=800.0,
        payment=PaymentType.CARD,
        commission=120.0,
    )

    for _ in range(5):
        storage.add_trip(trip_data)

    assert len(storage.get_all()) == 1
