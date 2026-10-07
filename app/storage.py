import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union

from app.models import Trip, TripCreate, TripBase, PaymentType


class TripStorage:
    """Хранилище поездок на основе JSON-файла с потокобезопасностью и защитой от дублей."""

    def __init__(self, file_path: str = "data/trips.json"):
        self.file_path = Path(file_path)
        self._lock = threading.Lock()
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """Создает файл и директорию, если они не существуют."""
        if not self.file_path.parent.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _generate_fingerprint(self, trip: Union[Trip, TripCreate, TripBase]) -> str:
        """
        Формирует уникальный отпечаток поездки по её параметрам
        (start, end, amount, payment, commission) для дедупликации без id.
        Нормализует временные метки через timestamp, чтобы одинаковые моменты времени
        в разных форматах таймзон совпадали.
        """
        try:
            start_key = int(trip.start.timestamp())
            end_key = int(trip.end.timestamp())
        except Exception:
            start_key = trip.start.isoformat()
            end_key = trip.end.isoformat()

        payment_val = trip.payment.value if hasattr(trip.payment, "value") else str(trip.payment)
        return f"{start_key}|{end_key}|{round(trip.amount, 2)}|{payment_val}|{round(trip.commission, 2)}"

    def get_all(self) -> List[Trip]:
        """Возвращает все поездки из хранилища."""
        with self._lock:
            return self._load_trips_unlocked()

    def _load_trips_unlocked(self) -> List[Trip]:
        """Внутренняя загрузка поездок без захвата блокировки."""
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                trips = []
                for item in data:
                    trips.append(Trip(**item))
                return trips
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_trips_unlocked(self, trips: List[Trip]) -> None:
        """Внутреннее сохранение поездок в файл с атомарной записью."""
        temp_path = self.file_path.with_suffix(".tmp")
        data = [
            {
                "id": t.id,
                "start": t.start.isoformat(),
                "end": t.end.isoformat(),
                "amount": t.amount,
                "payment": t.payment.value if hasattr(t.payment, "value") else str(t.payment),
                "commission": t.commission,
            }
            for t in trips
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.file_path)

    def _generate_id(self, existing_trips: List[Trip]) -> str:
        """Генерирует следующий читаемый ID, например t1, t2, t3..."""
        max_id_num = 0
        for t in existing_trips:
            if t.id.startswith("t") and t.id[1:].isdigit():
                max_id_num = max(max_id_num, int(t.id[1:]))
        if max_id_num > 0:
            return f"t{max_id_num + 1}"
        return f"t_{uuid.uuid4().hex[:6]}"

    def add_trip(self, trip_create: TripCreate) -> Tuple[Trip, bool]:
        """
        Добавляет поездку с защитой от дублей.
        Возвращает кортеж (Trip, is_duplicate: bool).
        
        Если поездка с таким же id уже существует:
          -> возвращает существующую поездку, is_duplicate=True.
        Если параметры поездки (время, сумма, оплата, комиссия) идентичны существующей:
          -> возвращает существующую поездку, is_duplicate=True.
        Иначе:
          -> сохраняет новую поездку, возвращает её, is_duplicate=False.
        """
        with self._lock:
            existing_trips = self._load_trips_unlocked()

            # 1. Проверка по ID, если он передан
            if trip_create.id:
                for existing in existing_trips:
                    if existing.id == trip_create.id:
                        return existing, True

            # 2. Проверка по отпечатку (fingerprint) параметров поездки
            target_fingerprint = self._generate_fingerprint(trip_create)
            for existing in existing_trips:
                if self._generate_fingerprint(existing) == target_fingerprint:
                    return existing, True

            # 3. Назначение ID при отсутствии
            assigned_id = trip_create.id or self._generate_id(existing_trips)

            new_trip = Trip(
                id=assigned_id,
                start=trip_create.start,
                end=trip_create.end,
                amount=trip_create.amount,
                payment=trip_create.payment,
                commission=trip_create.commission,
            )

            existing_trips.append(new_trip)
            self._save_trips_unlocked(existing_trips)
            return new_trip, False

    def clear(self) -> None:
        """Очищает хранилище (используется в тестах)."""
        with self._lock:
            self._save_trips_unlocked([])
