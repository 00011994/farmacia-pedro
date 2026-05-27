"""
Popula dados de demo para o sistema logístico de entregas.
Requer que seed_demo_db.py já tenha sido executado antes.

Uso:
    python scripts/seed_delivery_demo.py
"""
import os
import sys
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.core.db import get_conn
from src.core.config import load_settings

_settings = load_settings()
DB_PATH = _settings.db_path

try:
    import bcrypt as _bcrypt
    def _hash_pin(pin: str) -> str:
        return _bcrypt.hashpw(pin.encode(), _bcrypt.gensalt()).decode()
except ImportError:
    import hashlib, hmac as _hmac
    def _hash_pin(pin: str) -> str:
        return "sha256:" + _hmac.new(b"demo-key", pin.encode(), hashlib.sha256).hexdigest()


def seed_drivers(conn) -> list[int]:
    drivers = [
        ("João Delivery", _hash_pin("123456"), None, "on_route"),
        ("Maria Santos", _hash_pin("234567"), None, "on_route"),
        ("Carlos Moto", _hash_pin("345678"), None, "available"),
        ("Ana Riders", _hash_pin("456789"), None, "paused"),
    ]
    ids = []
    for name, pin_hash, photo, status in drivers:
        cur = conn.execute(
            "INSERT INTO drivers (name, pin_hash, photo_path, status) VALUES (?, ?, ?, ?)",
            (name, pin_hash, photo, status),
        )
        ids.append(cur.lastrowid)
    return ids


def seed_assignments(conn, driver_ids: list[int]) -> None:
    now = datetime.now(timezone.utc)

    # João em rota: pedido 1, destino Barra da Tijuca
    conn.execute(
        """INSERT INTO delivery_assignments
           (driver_id, order_id, status, tracking_token, eta_minutes,
            dest_lat, dest_lon, assigned_at, started_at, stopped_alert_min)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            driver_ids[0], 1, "in_progress", str(uuid.uuid4()), 8,
            -22.9985, -43.3650,
            (now - timedelta(minutes=12)).isoformat(),
            (now - timedelta(minutes=10)).isoformat(),
            5,
        ),
    )

    # Maria em rota: pedido 2, destino Recreio
    conn.execute(
        """INSERT INTO delivery_assignments
           (driver_id, order_id, status, tracking_token, eta_minutes,
            dest_lat, dest_lon, assigned_at, started_at, stopped_alert_min)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            driver_ids[1], 2, "in_progress", str(uuid.uuid4()), 15,
            -23.0157, -43.4468,
            (now - timedelta(minutes=20)).isoformat(),
            (now - timedelta(minutes=18)).isoformat(),
            5,
        ),
    )

    # Posições GPS demo para João
    locs_joao = [
        (-22.9920, -43.3580, -10),
        (-22.9945, -43.3600, -8),
        (-22.9960, -43.3620, -5),
        (-22.9970, -43.3635, -2),
    ]
    for lat, lon, delta_min in locs_joao:
        conn.execute(
            "INSERT INTO driver_locations (driver_id, order_id, lat, lon, recorded_at) VALUES (?, ?, ?, ?, ?)",
            (driver_ids[0], 1, lat, lon, (now + timedelta(minutes=delta_min)).isoformat()),
        )

    # Posições GPS demo para Maria
    locs_maria = [
        (-23.0020, -43.4100, -15),
        (-23.0060, -43.4200, -10),
        (-23.0100, -43.4320, -5),
    ]
    for lat, lon, delta_min in locs_maria:
        conn.execute(
            "INSERT INTO driver_locations (driver_id, order_id, lat, lon, recorded_at) VALUES (?, ?, ?, ?, ?)",
            (driver_ids[1], 2, lat, lon, (now + timedelta(minutes=delta_min)).isoformat()),
        )


if __name__ == "__main__":
    with get_conn(DB_PATH) as conn:
        # Limpa dados de delivery anteriores para idempotência
        conn.execute("DELETE FROM driver_locations")
        conn.execute("DELETE FROM delivery_assignments")
        conn.execute("DELETE FROM drivers")

        driver_ids = seed_drivers(conn)
        seed_assignments(conn, driver_ids)
        conn.commit()

    print("Entregadores demo criados:")
    print("  João Delivery   (id=1, PIN: 123456) — em rota, pedido #1")
    print("  Maria Santos    (id=2, PIN: 234567) — em rota, pedido #2")
    print("  Carlos Moto     (id=3, PIN: 345678) — disponível")
    print("  Ana Riders      (id=4, PIN: 456789) — pausada")
    print()
    print("Para verificar o tracking de um pedido:")
    with get_conn(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT order_id, tracking_token FROM delivery_assignments"
        ).fetchall()
        for row in rows:
            print(f"  http://localhost:8001/track/{row['order_id']}?token={row['tracking_token']}")
