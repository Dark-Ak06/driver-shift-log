from datetime import datetime
from typing import List, Optional

from app.models import DaySummary, PaymentSummary, PaymentType, Trip, TripCreate, TripAddResult
from app.storage import TripStorage


class ShiftService:
    """Сервис бизнес-логики: фильтрация поездок, расчет сводок за день, валидация."""

    def __init__(self, storage: Optional[TripStorage] = None):
        self.storage = storage or TripStorage()

    def get_trips_for_day(self, date_str: str) -> List[Trip]:
        """
        Возвращает поездки за указанный день (формат YYYY-MM-DD),
        отсортированные по времени начала (start).
        """
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        all_trips = self.storage.get_all()

        day_trips = [
            t for t in all_trips
            if t.start.date() == target_date
        ]
        # Сортировка по времени начала
        day_trips.sort(key=lambda t: t.start)
        return day_trips

    def calculate_summary(self, date_str: str, trips: Optional[List[Trip]] = None) -> DaySummary:
        """
        Рассчитывает суточную сводку:
        - число поездок
        - общая выручка
        - общая комиссия
        - заработок «на руки»
        - детальная разбивка: наличные (cash) / карта (card)
        """
        if trips is None:
            trips = self.get_trips_for_day(date_str)

        total_trips = len(trips)
        total_revenue = round(sum(t.amount for t in trips), 2)
        total_commission = round(sum(t.commission for t in trips), 2)
        total_net = round(total_revenue - total_commission, 2)

        cash_trips = [t for t in trips if t.payment == PaymentType.CASH]
        cash_revenue = round(sum(t.amount for t in cash_trips), 2)
        cash_commission = round(sum(t.commission for t in cash_trips), 2)
        cash_net = round(cash_revenue - cash_commission, 2)

        card_trips = [t for t in trips if t.payment == PaymentType.CARD]
        card_revenue = round(sum(t.amount for t in card_trips), 2)
        card_commission = round(sum(t.commission for t in card_trips), 2)
        card_net = round(card_revenue - card_commission, 2)

        return DaySummary(
            date=date_str,
            trips_count=total_trips,
            revenue=total_revenue,
            commission=total_commission,
            net_income=total_net,
            cash=PaymentSummary(
                trips_count=len(cash_trips),
                revenue=cash_revenue,
                commission=cash_commission,
                net_income=cash_net,
            ),
            card=PaymentSummary(
                trips_count=len(card_trips),
                revenue=card_revenue,
                commission=card_commission,
                net_income=card_net,
            ),
        )

    def add_trip(self, trip_create: TripCreate) -> TripAddResult:
        """
        Добавляет поездку через хранилище с защитой от дублей.
        """
        trip, is_dup = self.storage.add_trip(trip_create)
        if is_dup:
            msg = f"Поездка с id='{trip.id}' уже существует. Дубликат не создан."
        else:
            msg = f"Поездка '{trip.id}' успешно сохранена."
        return TripAddResult(trip=trip, is_duplicate=is_dup, message=msg)

    def get_available_dates(self) -> List[str]:
        """Возвращает уникальные даты всех сохраненных смен, отсортированные хронологически."""
        all_trips = self.storage.get_all()
        dates = sorted({t.start.date().isoformat() for t in all_trips})
        return dates
