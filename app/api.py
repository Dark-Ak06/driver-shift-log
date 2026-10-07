from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.models import DaySummary, Trip, TripAddResult, TripCreate
from app.service import ShiftService

router = APIRouter(prefix="/api", tags=["shifts"])


class ShiftDayResponse(BaseModel):
    date: str
    summary: DaySummary
    trips: List[Trip]
    available_dates: List[str]


def get_service() -> ShiftService:
    return ShiftService()


@router.get("/dates", response_model=List[str], summary="Список доступных дат со сменами")
def get_dates(service: ShiftService = Depends(get_service)):
    """Возвращает список всех дат (YYYY-MM-DD), за которые есть поездки."""
    return service.get_available_dates()


@router.get("/trips", response_model=List[Trip], summary="Список поездок за день")
def get_trips(
    date_str: Optional[str] = Query(
        None,
        alias="date",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Дата в формате YYYY-MM-DD (например, 2026-10-01)"
    ),
    service: ShiftService = Depends(get_service),
):
    """
    Возвращает список поездок за указанный день.
    Если дата не указана, выбирается последняя доступная дата или текущий день.
    """
    if not date_str:
        dates = service.get_available_dates()
        date_str = dates[-1] if dates else date.today().isoformat()

    try:
        return service.get_trips_for_day(date_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Некорректная дата: {str(e)}")


@router.get("/summary", response_model=DaySummary, summary="Сводка за день")
def get_summary(
    date_str: Optional[str] = Query(
        None,
        alias="date",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Дата в формате YYYY-MM-DD"
    ),
    service: ShiftService = Depends(get_service),
):
    """
    Возвращает сводку за день:
    - общее число поездок
    - общая выручка
    - общая комиссия
    - заработок «на руки»
    - разбивка: наличные (cash) / безналичные (card)
    """
    if not date_str:
        dates = service.get_available_dates()
        date_str = dates[-1] if dates else date.today().isoformat()

    try:
        return service.calculate_summary(date_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Некорректная дата: {str(e)}")


@router.get("/shift", response_model=ShiftDayResponse, summary="Полная информация о смене за день")
def get_shift(
    date_str: Optional[str] = Query(
        None,
        alias="date",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Дата в формате YYYY-MM-DD"
    ),
    service: ShiftService = Depends(get_service),
):
    """
    Универсальный эндпоинт для клиента:
    возвращает сразу сводку за день, список поездок и список доступных дат для переключения.
    """
    dates = service.get_available_dates()
    if not date_str:
        date_str = dates[-1] if dates else date.today().isoformat()

    try:
        trips = service.get_trips_for_day(date_str)
        summary = service.calculate_summary(date_str, trips=trips)
        return ShiftDayResponse(
            date=date_str,
            summary=summary,
            trips=trips,
            available_dates=dates,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Некорректная дата: {str(e)}")


@router.post(
    "/trips",
    response_model=TripAddResult,
    status_code=status.HTTP_201_CREATED,
    summary="Добавление поездки с проверкой данных и защитой от дублей"
)
def add_trip(
    trip_in: TripCreate,
    response: Response,
    service: ShiftService = Depends(get_service),
):
    """
    Добавляет поездку через API.
    Проверяет валидность данных:
    - сумма (amount) > 0
    - время окончания (end) строго позже времени начала (start)
    - способ оплаты (payment) 'cash' или 'card'
    - комиссия (commission) >= 0 и <= amount

    Защита от дублей:
    - Если поездка с таким же id уже существует, новая запись НЕ создается.
    - Если параметры поездки идентичны существующей, возвращается уже сохраненная
      поездка с флагом is_duplicate = true и HTTP 200 OK.
    """
    result = service.add_trip(trip_in)
    if result.is_duplicate:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED
    return result
