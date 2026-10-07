"""
Консольный клиент для работы с сервисом «Дневник смен водителя».
Поддерживает работу через CLI-аргументы и интерактивный режим.
"""

import argparse
import sys
from datetime import datetime
import requests

# Обеспечиваем корректный вывод UTF-8 в консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_SERVER_URL = "http://127.0.0.1:8000"


def format_currency(val: float) -> str:
    return f"{val:,.2f} ₸".replace(",", " ")


def print_summary(summary: dict):
    print("=" * 60)
    print(f"[ СВОДКА СМЕНЫ ЗА ДАТУ: {summary['date']} ]")
    print("=" * 60)
    print(f"  Всего поездок:         {summary['trips_count']}")
    print(f"  Общая выручка:         {format_currency(summary['revenue'])}")
    print(f"  Общая комиссия:        {format_currency(summary['commission'])}")
    print(f"  --> НА РУКИ (чистыми): {format_currency(summary['net_income'])}")
    print("-" * 60)
    print("  РАЗБИВКА ПО ОПЛАТЕ:")
    card = summary.get("card", {})
    cash = summary.get("cash", {})
    print(f"  [Карта]:     {card.get('trips_count', 0)} поездок | "
          f"Выручка: {format_currency(card.get('revenue', 0))} | "
          f"На руки: {format_currency(card.get('net_income', 0))}")
    print(f"  [Наличные]:  {cash.get('trips_count', 0)} поездок | "
          f"Выручка: {format_currency(cash.get('revenue', 0))} | "
          f"На руки: {format_currency(cash.get('net_income', 0))}")
    print("=" * 60)


def print_trips(trips: list):
    print("=" * 80)
    print(f"{'ID':<6} | {'Время':<20} | {'Оплата':<10} | {'Выручка':<14} | {'Комиссия':<12} | {'На руки':<12}")
    print("-" * 80)
    if not trips:
        print("  Поездок не найдено.")
    for t in trips:
        start_t = t['start'][11:16]
        end_t = t['end'][11:16]
        time_str = f"{start_t} - {end_t}"
        payment_str = "Карта" if t['payment'] == 'card' else "Наличные"
        net = round(t['amount'] - t['commission'], 2)
        print(f"{t['id']:<6} | {time_str:<20} | {payment_str:<10} | {format_currency(t['amount']):<14} | "
              f"{format_currency(t['commission']):<12} | {format_currency(net):<12}")
    print("=" * 80)


def cmd_summary(server_url: str, date_str: str = None):
    params = {"date": date_str} if date_str else {}
    resp = requests.get(f"{server_url}/api/summary", params=params)
    if resp.status_code == 200:
        print_summary(resp.json())
    else:
        print(f"Ошибка сервера ({resp.status_code}): {resp.text}")


def cmd_trips(server_url: str, date_str: str = None):
    params = {"date": date_str} if date_str else {}
    resp = requests.get(f"{server_url}/api/trips", params=params)
    if resp.status_code == 200:
        print_trips(resp.json())
    else:
        print(f"Ошибка сервера ({resp.status_code}): {resp.text}")


def cmd_add_trip(server_url: str, start: str, end: str, amount: float, payment: str, commission: float, trip_id: str = None):
    payload = {
        "start": start,
        "end": end,
        "amount": amount,
        "payment": payment,
        "commission": commission,
    }
    if trip_id:
        payload["id"] = trip_id

    resp = requests.post(f"{server_url}/api/trips", json=payload)
    if resp.status_code in (200, 201):
        data = resp.json()
        if data.get("is_duplicate"):
            print(f"[ЗАЩИТА ОТ ДУБЛЕЙ СРАБОТАЛА]: Поездка #{data['trip']['id']} уже существует! Запись не задвоена.")
        else:
            print(f"[УСПЕХ]: Поездка #{data['trip']['id']} успешно добавлена!")
    else:
        print(f"[ОШИБКА] ({resp.status_code}): {resp.text}")


def run_interactive(server_url: str):
    print("\n=== ДНЕВНИК СМЕН ВОДИТЕЛЯ (CLI РЕЖИМ) ===\n")
    current_date = "2026-10-01"

    while True:
        print(f"\nТекущая выбранная дата: [{current_date}]")
        print("1. Показать сводку за день")
        print("2. Показать список поездок за день")
        print("3. Сменить дату")
        print("4. Добавить новую поездку")
        print("5. Проверить защиту от дубликатов (отправить t1 повторно)")
        print("0. Выход")
        choice = input("\nВыберите действие (0-5): ").strip()

        if choice == "1":
            cmd_summary(server_url, current_date)
        elif choice == "2":
            cmd_trips(server_url, current_date)
        elif choice == "3":
            new_date = input("Введите дату (YYYY-MM-DD): ").strip()
            if new_date:
                current_date = new_date
        elif choice == "4":
            print("\nДобавление поездки:")
            tid = input("ID (оставьте пустым для автогенерации): ").strip() or None
            s = input(f"Время начала [{current_date}T10:00:00+05:00]: ").strip() or f"{current_date}T10:00:00+05:00"
            e = input(f"Время окончания [{current_date}T10:30:00+05:00]: ").strip() or f"{current_date}T10:30:00+05:00"
            amt = float(input("Сумма поездки (тенге): ").strip() or "2000")
            comm = float(input(f"Комиссия (тенге) [по умолчанию {amt * 0.15:.0f}]: ").strip() or str(amt * 0.15))
            pay = input("Способ оплаты (card/cash) [card]: ").strip() or "card"
            cmd_add_trip(server_url, s, e, amt, pay, comm, tid)
        elif choice == "5":
            print("\nОтправка тестового запроса с существующим ID t1...")
            cmd_add_trip(
                server_url,
                "2026-10-01T08:10:00+05:00",
                "2026-10-01T08:32:00+05:00",
                2400.0,
                "card",
                360.0,
                trip_id="t1"
            )
        elif choice == "0":
            print("До свидания!")
            sys.exit(0)
        else:
            print("Неверный выбор, попробуйте снова.")


def main():
    parser = argparse.ArgumentParser(description="Консольный клиент «Дневник смен водителя»")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help="URL сервера (по умолчанию http://127.0.0.1:8000)")
    subparsers = parser.add_subparsers(dest="command")

    # summary command
    p_sum = subparsers.add_parser("summary", help="Получить сводку за день")
    p_sum.add_argument("--date", default=None, help="Дата (YYYY-MM-DD)")

    # trips command
    p_trips = subparsers.add_parser("trips", help="Получить список поездок за день")
    p_trips.add_argument("--date", default=None, help="Дата (YYYY-MM-DD)")

    # add command
    p_add = subparsers.add_parser("add", help="Добавить поездку")
    p_add.add_argument("--start", required=True, help="Время начала (ISO 8601)")
    p_add.add_argument("--end", required=True, help="Время окончания (ISO 8601)")
    p_add.add_argument("--amount", type=float, required=True, help="Сумма поездки (> 0)")
    p_add.add_argument("--payment", choices=["cash", "card"], required=True, help="Способ оплаты")
    p_add.add_argument("--commission", type=float, default=0.0, help="Комиссия (>= 0)")
    p_add.add_argument("--id", default=None, help="Опциональный ID")

    # interactive command
    subparsers.add_parser("interactive", help="Запустить интерактивное консольное меню")

    args = parser.parse_args()

    if args.command == "summary":
        cmd_summary(args.server, args.date)
    elif args.command == "trips":
        cmd_trips(args.server, args.date)
    elif args.command == "add":
        cmd_add_trip(args.server, args.start, args.end, args.amount, args.payment, args.commission, args.id)
    elif args.command == "interactive" or len(sys.argv) == 1:
        run_interactive(args.server)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
