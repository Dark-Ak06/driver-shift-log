from datetime import datetime
import pytest
from pydantic import ValidationError
from app.models import TripCreate, PaymentType


def test_validation_valid_trip():
    """Корректные данные поездки должны успешно проходить валидацию."""
    trip = TripCreate(
        start=datetime.fromisoformat("2026-10-01T08:00:00+05:00"),
        end=datetime.fromisoformat("2026-10-01T08:30:00+05:00"),
        amount=1000.0,
        payment=PaymentType.CASH,
        commission=150.0,
    )
    assert trip.amount == 1000.0
    assert trip.payment == PaymentType.CASH


def test_validation_amount_must_be_greater_than_zero():
    """Сумма поездки (amount) должна быть строго больше 0."""
    # amount = 0
    with pytest.raises(ValidationError) as exc_info:
        TripCreate(
            start=datetime.fromisoformat("2026-10-01T08:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T08:30:00+05:00"),
            amount=0.0,
            payment=PaymentType.CARD,
            commission=0.0,
        )
    assert "amount" in str(exc_info.value)

    # amount < 0
    with pytest.raises(ValidationError) as exc_info:
        TripCreate(
            start=datetime.fromisoformat("2026-10-01T08:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T08:30:00+05:00"),
            amount=-500.0,
            payment=PaymentType.CARD,
            commission=0.0,
        )
    assert "amount" in str(exc_info.value)


def test_validation_end_must_be_later_than_start():
    """Окончание поездки (end) должно быть строго позже начала (start)."""
    # end == start
    with pytest.raises(ValidationError) as exc_info:
        TripCreate(
            start=datetime.fromisoformat("2026-10-01T08:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T08:00:00+05:00"),
            amount=500.0,
            payment=PaymentType.CASH,
            commission=50.0,
        )
    assert "Время окончания поездки" in str(exc_info.value)

    # end < start
    with pytest.raises(ValidationError) as exc_info:
        TripCreate(
            start=datetime.fromisoformat("2026-10-01T09:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T08:30:00+05:00"),
            amount=500.0,
            payment=PaymentType.CASH,
            commission=50.0,
        )
    assert "Время окончания поездки" in str(exc_info.value)


def test_validation_commission_cannot_exceed_amount():
    """Комиссия не может быть больше суммы поездки."""
    with pytest.raises(ValidationError) as exc_info:
        TripCreate(
            start=datetime.fromisoformat("2026-10-01T08:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T08:30:00+05:00"),
            amount=500.0,
            payment=PaymentType.CARD,
            commission=600.0,  # > amount
        )
    assert "Комиссия не может превышать" in str(exc_info.value)


def test_validation_invalid_payment_type():
    """Способ оплаты должен быть только cash или card."""
    with pytest.raises(ValidationError):
        TripCreate.model_validate({
            "start": "2026-10-01T08:00:00+05:00",
            "end": "2026-10-01T08:30:00+05:00",
            "amount": 500.0,
            "payment": "bitcoin",
            "commission": 50.0,
        })
