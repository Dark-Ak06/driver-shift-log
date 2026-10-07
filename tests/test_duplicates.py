from datetime import datetime
import pytest
from app.models import TripCreate, PaymentType
from app.storage import TripStorage


@pytest.fixture
def temp_storage(tmp_path):
    """Создает изолированное временное хранилище на время теста."""
    storage_file = tmp_path / "test_trips.json"
    return TripStorage(file_path=str(storage_file))


def test_duplicate_prevention_same_id(temp_storage):
    """
    Повторная отправка поездки с тем же id не должна создавать дубль.
    Число записей в хранилище должно оставаться равным 1.
    """
    trip_data = TripCreate(
        id="trip_dup_1",
        start=datetime.fromisoformat("2026-10-01T08:00:00+05:00"),
        end=datetime.fromisoformat("2026-10-01T08:25:00+05:00"),
        amount=1200.0,
        payment=PaymentType.CARD,
        commission=180.0,
    )

    # Первая отправка
    trip1, is_dup1 = temp_storage.add_trip(trip_data)
    assert is_dup1 is False
    assert trip1.id == "trip_dup_1"
    assert len(temp_storage.get_all()) == 1

    # Повторная отправка идентичной поездки с тем же ID
    trip2, is_dup2 = temp_storage.add_trip(trip_data)
    assert is_dup2 is True
    assert trip2.id == "trip_dup_1"
    # Записей в хранилище по-прежнему ровно 1
    assert len(temp_storage.get_all()) == 1


def test_duplicate_prevention_same_payload_without_id(temp_storage):
    """
    Повторная отправка поездки с теми же параметрами (но без явного id)
    не должна создавать дубль благодаря отпечатку (fingerprint).
    """
    trip_data = TripCreate(
        start=datetime.fromisoformat("2026-10-01T12:00:00+05:00"),
        end=datetime.fromisoformat("2026-10-01T12:30:00+05:00"),
        amount=2500.0,
        payment=PaymentType.CASH,
        commission=375.0,
    )

    # Первая отправка
    trip1, is_dup1 = temp_storage.add_trip(trip_data)
    assert is_dup1 is False
    assert trip1.id is not None
    assert len(temp_storage.get_all()) == 1

    # Вторая отправка того же самого запроса
    trip2, is_dup2 = temp_storage.add_trip(trip_data)
    assert is_dup2 is True
    assert trip2.id == trip1.id
    assert len(temp_storage.get_all()) == 1


def test_different_trips_are_both_saved(temp_storage):
    """Разные поездки должны успешно добавляться."""
    trip1_data = TripCreate(
        id="trip_a",
        start=datetime.fromisoformat("2026-10-01T14:00:00+05:00"),
        end=datetime.fromisoformat("2026-10-01T14:20:00+05:00"),
        amount=900.0,
        payment=PaymentType.CARD,
        commission=135.0,
    )
    trip2_data = TripCreate(
        id="trip_b",
        start=datetime.fromisoformat("2026-10-01T15:00:00+05:00"),
        end=datetime.fromisoformat("2026-10-01T15:40:00+05:00"),
        amount=1400.0,
        payment=PaymentType.CASH,
        commission=210.0,
    )

    trip1, is_dup1 = temp_storage.add_trip(trip1_data)
    trip2, is_dup2 = temp_storage.add_trip(trip2_data)

    assert is_dup1 is False
    assert is_dup2 is False
    assert len(temp_storage.get_all()) == 2
