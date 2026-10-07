from datetime import datetime
from app.models import Trip, PaymentType
from app.service import ShiftService


def test_daily_summary_calculation_with_prompt_example():
    """
    Проверка расчета сводки на примере данных из ТЗ:
    t1: amount=2400, payment='card', commission=360
    t2: amount=1500, payment='cash', commission=225
    """
    service = ShiftService()
    test_trips = [
        Trip(
            id="t1",
            start=datetime.fromisoformat("2026-10-01T08:10:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T08:32:00+05:00"),
            amount=2400.0,
            payment=PaymentType.CARD,
            commission=360.0,
        ),
        Trip(
            id="t2",
            start=datetime.fromisoformat("2026-10-01T09:05:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T09:20:00+05:00"),
            amount=1500.0,
            payment=PaymentType.CASH,
            commission=225.0,
        ),
    ]

    summary = service.calculate_summary("2026-10-01", trips=test_trips)

    # 1. Общие показатели за день
    assert summary.date == "2026-10-01"
    assert summary.trips_count == 2
    assert summary.revenue == 3900.0  # 2400 + 1500
    assert summary.commission == 585.0  # 360 + 225
    assert summary.net_income == 3315.0  # 3900 - 585

    # 2. Разбивка по безналичным (карта)
    assert summary.card.trips_count == 1
    assert summary.card.revenue == 2400.0
    assert summary.card.commission == 360.0
    assert summary.card.net_income == 2040.0

    # 3. Разбивка по наличным
    assert summary.cash.trips_count == 1
    assert summary.cash.revenue == 1500.0
    assert summary.cash.commission == 225.0
    assert summary.cash.net_income == 1275.0

    # 4. Балансовое равенство
    assert round(summary.card.net_income + summary.cash.net_income, 2) == summary.net_income


def test_empty_day_summary():
    """Проверка расчета сводки для дня без поездок."""
    service = ShiftService()
    summary = service.calculate_summary("2026-10-05", trips=[])

    assert summary.trips_count == 0
    assert summary.revenue == 0.0
    assert summary.commission == 0.0
    assert summary.net_income == 0.0
    assert summary.cash.trips_count == 0
    assert summary.cash.revenue == 0.0
    assert summary.card.trips_count == 0
    assert summary.card.revenue == 0.0


def test_summary_with_only_cash_trips():
    """Проверка сводки, когда все поездки за наличные."""
    service = ShiftService()
    test_trips = [
        Trip(
            id="t1",
            start=datetime.fromisoformat("2026-10-01T10:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T10:20:00+05:00"),
            amount=500.0,
            payment=PaymentType.CASH,
            commission=75.0,
        ),
        Trip(
            id="t2",
            start=datetime.fromisoformat("2026-10-01T11:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T11:30:00+05:00"),
            amount=800.0,
            payment=PaymentType.CASH,
            commission=120.0,
        ),
    ]

    summary = service.calculate_summary("2026-10-01", trips=test_trips)
    assert summary.trips_count == 2
    assert summary.revenue == 1300.0
    assert summary.commission == 195.0
    assert summary.net_income == 1105.0

    assert summary.cash.trips_count == 2
    assert summary.cash.revenue == 1300.0
    assert summary.cash.net_income == 1105.0

    assert summary.card.trips_count == 0
    assert summary.card.revenue == 0.0
    assert summary.card.net_income == 0.0
