from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class PaymentType(str, Enum):
    CASH = "cash"
    CARD = "card"


class TripBase(BaseModel):
    start: datetime = Field(..., description="Время начала поездки (ISO 8601)")
    end: datetime = Field(..., description="Время окончания поездки (ISO 8601)")
    amount: float = Field(..., gt=0, description="Стоимость поездки, должна быть строго больше 0")
    payment: PaymentType = Field(..., description="Способ оплаты: 'cash' или 'card'")
    commission: float = Field(..., ge=0, description="Комиссия сервиса/парка, должна быть >= 0")

    @model_validator(mode="after")
    def validate_dates_and_commission(self) -> "TripBase":
        if self.end <= self.start:
            raise ValueError("Время окончания поездки (end) должно быть строго позже времени начала (start)")
        if self.commission > self.amount:
            raise ValueError("Комиссия не может превышать сумму поездки")
        return self


class TripCreate(TripBase):
    id: Optional[str] = Field(default=None, description="Опциональный уникальный идентификатор поездки")


class Trip(TripBase):
    id: str = Field(..., description="Уникальный идентификатор поездки")

    @property
    def net_income(self) -> float:
        """Сумма поездки «на руки» (выручка минус комиссия)"""
        return round(self.amount - self.commission, 2)

    @property
    def duration_minutes(self) -> int:
        """Длительность поездки в минутах"""
        return int((self.end - self.start).total_seconds() // 60)


class PaymentSummary(BaseModel):
    trips_count: int = Field(default=0, description="Число поездок данным способом оплаты")
    revenue: float = Field(default=0.0, description="Общая сумма (выручка)")
    commission: float = Field(default=0.0, description="Комиссия сервиса/парка")
    net_income: float = Field(default=0.0, description="Чистый доход «на руки»")


class DaySummary(BaseModel):
    date: str = Field(..., description="Дата смены (ГГГГ-ММ-ДД)")
    trips_count: int = Field(default=0, description="Общее число поездок за день")
    revenue: float = Field(default=0.0, description="Общая выручка за день")
    commission: float = Field(default=0.0, description="Общая комиссия за день")
    net_income: float = Field(default=0.0, description="Общий заработок «на руки» (выручка - комиссия)")
    cash: PaymentSummary = Field(default_factory=PaymentSummary, description="Показатели по наличным")
    card: PaymentSummary = Field(default_factory=PaymentSummary, description="Показатели по безналичным (карте)")


class TripAddResult(BaseModel):
    trip: Trip
    is_duplicate: bool = Field(default=False, description="Признак: была ли поездка уже сохранена ранее")
    message: str = Field(default="", description="Информационное сообщение")
